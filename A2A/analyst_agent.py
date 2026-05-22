import os
from fastapi import FastAPI, Request
from crewai import Agent, Task, Crew
import uvicorn
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# --- CrewAI Logic ---
def run_crewai_analysis(input_text):
    analyst = Agent(
        role='Data Analyst',
        goal='Analyze provided data and extract 3 key trends.',
        backstory='Expert in statistical analysis and pattern recognition.',
        verbose=True
    )
    
    task = Task(
        description=f"Analyze the following data and provide 3 trends: {input_text}",
        agent=analyst,
        expected_output="A bulleted list of 3 trends."
    )
    
    crew = Crew(agents=[analyst], tasks=[task])
    result = crew.kickoff()
    return str(result)

# --- A2A Protocol Endpoints ---

@app.get("/.well-known/agent-card.json")
async def agent_card():
    """A2A Discovery Endpoint"""
    return {
        "name": "crewai_analyst",
        "description": "An agent that analyzes data using CrewAI.",
        "capabilities": ["data_analysis"],
        "endpoint": "/execute"
    }

@app.post("/execute")
async def execute(request: Request):
    """A2A Execution Endpoint"""
    data = await request.json()
    # A2A usually passes content in a 'message' or 'input' field
    user_input = data.get("input", data.get("message", ""))
    
    analysis_result = run_crewai_analysis(user_input)
    
    return {
        "output": analysis_result,
        "status": "completed"
    }

if __name__ == "__main__":
    # Run on port 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)