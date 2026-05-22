import asyncio
import os
import re
import plotly.graph_objects as go
from google.adk.agents.llm_agent import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
# Load environment variable
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

async def main():
    # 1. Define the Remote Analyst (A2A Client)
    analyst_service = RemoteA2aAgent(
        name="remote_crewai_analyst",
        description="Agent that analyzes data and returns percentages.",
        agent_card="http://localhost:8002/.well-known/agent-card.json"
    )

    # 2. Define the Visualiser Agent
    visualiser = Agent(
        name="Visualiser",
        model="gemini-2.5-flash",
        instruction=(
            "You are a data visualization assistant. You take a user's topic, "
            "ask the 'remote_crewai_analyst' to research it, and then return "
            "exactly the text output provided by the analyst."
        ),
        sub_agents=[analyst_service]
    )

    topic = "AI Server Infrastructure Growth in 2026"
    print(f"[Visualiser] Delegating task to CrewAI Analyst for topic: '{topic}'...")

    # 3. Setup the ADK Session and Runner
    session_service = InMemorySessionService()
    session = await session_service.create_session(
        state={},
        app_name='visualiser_app',
        user_id='user_1'
    )
    
    runner = Runner(
        app_name='visualiser_app',
        agent=visualiser,
        session_service=session_service
    )

    # 4. Construct the formal ADK message type
    user_prompt = f"Please analyze {topic} using the remote_crewai_analyst."
    content = types.Content(
        role='user', 
        parts=[types.Part.from_text(text=user_prompt)]
    )

    # 5. Execute the agent programmatically
    print("[Visualiser] Waiting for agent execution and A2A response...")
    events_async = runner.run_async(
        session_id=session.id,
        user_id=session.user_id,
        new_message=content
    )
    
    # 6. Process the stream of events
    response_text = ""
    async for event in events_async:
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    print(f"\n--- Final Report Received via A2A ---\n{response_text}\n")

    # 7. Visualisation Logic
    print("[Visualiser] Extracting numbers for Plotly visualization...")
    
    # Clean the text of markdown bolding/italics that LLMs love to add
    clean_text = response_text.replace("*", "").replace("_", "")
    
    # More forgiving regex to catch percentages and labels
    numbers = re.findall(r"(\d+(?:\.\d+)?)%", clean_text)
    # Looks for anything between "Trend X:" and the dash, ignoring extra spaces
    labels = re.findall(r"Trend \d+:\s*(.*?)\s*-", clean_text)

    # Fallback: If the LLM gave numbers but completely ignored our label format
    if numbers and not labels:
        print("[Visualiser] Warning: LLM ignored label format. Using default labels.")
        labels = [f"Metric {i+1}" for i in range(len(numbers))]

    if numbers and labels:
        # Match lengths in case the LLM gave extra numbers somewhere
        min_len = min(len(labels), len(numbers))
        y_values = [float(n) for n in numbers[:min_len]]
        x_values = labels[:min_len]

        fig = go.Figure([go.Bar(x=x_values, y=y_values, marker_color='teal')])
        fig.update_layout(
            title=f"A2A Scraped Data: {topic}", 
            yaxis_title="Growth / Market Share (%)",
            template="plotly_dark"
        )
        fig.show() 
    else:
        print("Could not extract clean percentage metrics from the text.")
        print("Raw text to debug:\n", clean_text)

if __name__ == "__main__":
    asyncio.run(main())