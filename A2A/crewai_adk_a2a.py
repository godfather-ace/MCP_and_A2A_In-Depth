import asyncio
import threading
import time
import uuid
import httpx
import uvicorn
import os 
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# ── CrewAI imports ─────────────────────────────────────────────────────────────
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# ── Google ADK imports ─────────────────────────────────────────────────────────
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types as genai_types


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 — Google ADK Agent (acts as A2A "server")
# ═══════════════════════════════════════════════════════════════════════════════

ADK_HOST = "127.0.0.1"
ADK_PORT = 8100
ADK_APP_NAME = "adk_worker"

# --- ADK tool: the actual capability exposed by this agent ---
def analyze_text(text: str) -> dict:
    """Analyze text and return word count, sentiment hint, and a short summary."""
    words = text.split()
    sentiment = "positive" if any(w in text.lower() for w in ["good","great","excellent","happy"]) \
                else "negative" if any(w in text.lower() for w in ["bad","poor","terrible","sad"]) \
                else "neutral"
    return {
        "word_count": len(words),
        "sentiment": sentiment,
        "summary": f"Text has {len(words)} words with {sentiment} tone.",
    }

# --- Build ADK agent ---
adk_agent = LlmAgent(
    name="TextAnalyzerAgent",
    model="gemini-2.0-flash",
    instruction=(
        "You are a text analysis specialist. "
        "When given text, call analyze_text and return the result as JSON."
    ),
    tools=[FunctionTool(analyze_text)],
)

session_service = InMemorySessionService()
adk_runner = Runner(
    agent=adk_agent,
    app_name=ADK_APP_NAME,
    session_service=session_service,
)

# --- A2A message schema (JSON-RPC style, aligned with Google A2A spec) ---
class A2ARequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str          # e.g. "tasks/send"
    params: dict

class A2AResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: dict | None = None
    error: dict | None = None

# --- FastAPI app wrapping the ADK agent ---
adk_app = FastAPI(title="ADK Worker — A2A Endpoint")

@adk_app.post("/a2a", response_model=A2AResponse)
async def handle_a2a(request: A2ARequest):
    """Receive a task from any A2A client (e.g. CrewAI), run ADK, return result."""
    try:
        user_message = request.params.get("message", "")
        session_id = request.params.get("session_id", str(uuid.uuid4()))

        # Create a fresh session for this request
        await session_service.create_session(
            app_name=ADK_APP_NAME,
            user_id="crewai_orchestrator",
            session_id=session_id,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )

        final_text = ""
        async for event in adk_runner.run_async(
            user_id="crewai_orchestrator",
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text += part.text

        return A2AResponse(
            id=request.id,
            result={"status": "completed", "output": final_text},
        )

    except Exception as exc:
        return A2AResponse(
            id=request.id,
            error={"code": -32000, "message": str(exc)},
        )

def run_adk_server():
    """Start the ADK FastAPI server in a background thread."""
    config = uvicorn.Config(adk_app, host=ADK_HOST, port=ADK_PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()


# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 — CrewAI Orchestrator (acts as A2A "client")
# ═══════════════════════════════════════════════════════════════════════════════

@tool("call_adk_agent")
def call_adk_agent(text: str) -> str:
    """
    Send text to the Google ADK agent via A2A protocol and return its analysis.
    Args:
        text: The text to analyze.
    Returns:
        Analysis result as a string.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/send",
        "params": {
            "message": f"Please analyze this text: {text}",
            "session_id": str(uuid.uuid4()),
        },
    }
    try:
        response = httpx.post(
            f"http://{ADK_HOST}:{ADK_PORT}/a2a",
            json=payload,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            return f"ADK error: {data['error']['message']}"
        return data["result"]["output"]
    except Exception as e:
        return f"Failed to reach ADK agent: {e}"


# --- CrewAI agents ---
orchestrator = Agent(
    role="Orchestrator",
    goal="Coordinate tasks by delegating text analysis to the ADK specialist agent.",
    backstory=(
        "You are a workflow orchestrator. You receive user requests and delegate "
        "analysis tasks to a specialized Google ADK agent via the A2A protocol."
    ),
    tools=[call_adk_agent],
    verbose=True,
)

summarizer = Agent(
    role="Report Writer",
    goal="Produce a concise final report from the analysis results.",
    backstory="You format raw analysis data into clean, human-readable summaries.",
    verbose=True,
)

# --- CrewAI tasks ---
analysis_task = Task(
    description=(
        "Use the call_adk_agent tool to analyze the following text:\n\n"
        "'The product launch was excellent! Sales exceeded all expectations "
        "and customer feedback has been overwhelmingly positive.'\n\n"
        "Return the full analysis result."
    ),
    expected_output="Raw analysis result from the ADK agent including sentiment and word count.",
    agent=orchestrator,
)

report_task = Task(
    description=(
        "Take the analysis result from the previous task and write a short "
        "executive summary (3-4 sentences) suitable for a manager."
    ),
    expected_output="A concise executive summary paragraph.",
    agent=summarizer,
)

crew = Crew(
    agents=[orchestrator, summarizer],
    tasks=[analysis_task, report_task],
    process=Process.sequential,
    verbose=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# PART 3 — Main: start ADK server, then run CrewAI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  A2A Demo: CrewAI <-> Google ADK")
    print("=" * 60)

    # 1. Start the ADK A2A server in the background
    print(f"\n[1] Starting ADK agent server on http://{ADK_HOST}:{ADK_PORT} ...")
    server_thread = threading.Thread(target=run_adk_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # wait for server to be ready
    print("    ADK server ready.")

    # 2. Run the CrewAI workflow (which calls the ADK server via A2A)
    print("\n[2] Launching CrewAI orchestration ...\n")
    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("  FINAL RESULT")
    print("=" * 60)
    print(result)