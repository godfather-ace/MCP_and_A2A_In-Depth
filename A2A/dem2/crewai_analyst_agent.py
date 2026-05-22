import os
from crewai import Agent as CrewAgent, Task, Crew, Process, LLM
from crewai.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from google.adk.agents.llm_agent import Agent as AdkAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
import uvicorn
from dotenv import load_dotenv
load_dotenv()

# 1. Setup Gemini Model using CrewAI's native LLM class
gemini_llm = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.3
)

# 2. Safely wrap the LangChain tool using CrewAI's @tool decorator
@tool("Web Search Tool")
def search_tool(query: str) -> str:
    """Searches the web for recent data and trends."""
    search = DuckDuckGoSearchRun()
    return search.run(query)

# 3. Define the core CrewAI Logic
def scrape_and_analyze(topic: str) -> str:
    """Scrapes the web for data on the topic and returns 3 key percentage metrics."""
    scraper = CrewAgent(
        role='Market Researcher',
        goal=f'Scrape and find real-time 2025/2026 data about {topic}',
        backstory='Expert at finding the latest tech trends using web search.',
        tools=[search_tool],
        llm=gemini_llm,
        verbose=True
    )

    analyst = CrewAgent(
        role='Data Quant',
        goal='Summarize findings into exactly 3 key numerical trends for plotting.',
        backstory='Expert in converting research into data-driven insights. Always extract explicit percentage numbers.',
        llm=gemini_llm,
        verbose=True
    )

    task1 = Task(
        description=f"Search the web for recent growth statistics regarding {topic}.",
        agent=scraper,
        expected_output="A summary of raw data found from search results."
    )

    task2 = Task(
        description="Based on the research, provide exactly 3 growth metrics with estimated percentages.",
        agent=analyst,
        expected_output="Trend 1: [Name] - [Value]%, Trend 2: [Name] - [Value]%, Trend 3: [Name] - [Value]%",
        context=[task1]
    )

    crew = Crew(agents=[scraper, analyst], tasks=[task1, task2], process=Process.sequential)
    result = crew.kickoff()
    return str(result.raw) if hasattr(result, 'raw') else str(result)

# 4. Wrap CrewAI logic in a Google ADK Agent
analyst_adk = AdkAgent(
    name="crewai_analyst",
    description="I scrape the web and analyze market trends.",
    model="gemini-2.5-flash",
    instruction="When asked to analyze a topic, use the scrape_and_analyze tool to generate a data-rich report.",
    tools=[scrape_and_analyze]
)

# 5. Expose as an A2A Protocol Server
app = to_a2a(analyst_adk, port=8002)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)