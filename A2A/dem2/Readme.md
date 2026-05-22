# 🤖 Demo 2 — A2A Protocol with Google ADK + CrewAI + Live Web Scraping

This demo takes A2A interoperability to the next level — combining **Google's Agent Development Kit (ADK)**, **CrewAI's multi-agent pipeline**, and **live web scraping** to produce a real-time, data-driven Plotly visualization. Two agents from completely different frameworks collaborate seamlessly over the A2A protocol.

---

## 📌 What This Demo Does

A two-agent system spans two separate processes and two different frameworks:

| Agent | File | Framework | Role |
|---|---|---|---|
| **CrewAI Analyst Agent** | `crewai_analyst_agent.py` | CrewAI + Google ADK | Scrapes the web for live data, extracts 3 key percentage metrics, serves as an A2A server |
| **ADK Visualiser Agent** | `adk_visualiser_agent.py` | Google ADK | Delegates research via A2A to the Analyst, parses the output, renders an interactive chart |

**The Flow:**

```
User Prompt (topic)
        │
        ▼
ADK Visualiser Agent
        │  Discovers Analyst via agent-card.json
        │  Delegates task via A2A (RemoteA2aAgent)
        ▼
CrewAI Analyst Agent  ──► Scraper (DuckDuckGo web search)
        │                       │
        │               ◄───────┘  raw search results
        │
        ▼
CrewAI Analyst Agent  ──► Data Quant (Gemini 2.5 Flash)
        │                       │
        │               ◄───────┘  "Trend 1: X - 42%, Trend 2: ..."
        │
        ▼
ADK Visualiser Agent
        │  Parses percentages & labels
        ▼
Interactive Plotly Bar Chart (Dark Theme, Browser)
```

---

## 🧠 Key Concepts Demonstrated

### 1. Google ADK as the A2A Bridge
The Analyst Agent is built with CrewAI internally but **exposed to the outside world as a Google ADK A2A server** using `to_a2a()`. This means any ADK-compatible client can call it without knowing anything about CrewAI.

```python
analyst_adk = AdkAgent(
    name="crewai_analyst",
    tools=[scrape_and_analyze]   # CrewAI crew wrapped as a plain tool
)
app = to_a2a(analyst_adk, port=8002)  # Expose as A2A server
```

### 2. Agent Discovery via Agent Card
The server auto-exposes a discovery endpoint at:

```
GET http://localhost:8002/.well-known/agent-card.json
```

The Visualiser uses this URL directly in `RemoteA2aAgent` to discover and connect — no hardcoded contracts:

```python
analyst_service = RemoteA2aAgent(
    name="remote_crewai_analyst",
    agent_card="http://localhost:8002/.well-known/agent-card.json"
)
```

### 3. Cross-Framework Agent Delegation
The Visualiser wraps the remote analyst as a **sub-agent**. From the Visualiser's perspective, it's just another agent in its team — despite the analyst running in a separate process on a different framework entirely.

```python
visualiser = Agent(
    name="Visualiser",
    model="gemini-2.5-flash",
    sub_agents=[analyst_service]   # RemoteA2aAgent over HTTP
)
```

### 4. Live Web Scraping inside the CrewAI Pipeline
The Analyst Agent runs a **two-agent sequential CrewAI crew**:
- A **Market Researcher** that searches the web using DuckDuckGo
- A **Data Quant** that converts raw results into exactly 3 structured percentage metrics

```
Task 1 (Scraper) → raw web data
Task 2 (Analyst, with Task 1 as context) → "Trend 1: X - 42%, Trend 2: Y - 67%, Trend 3: Z - 85%"
```

---

## 🗂️ File Structure

```
dem2/
├── crewai_analyst_agent.py   # A2A Server — CrewAI crew exposed via Google ADK (port 8002)
├── adk_visualiser_agent.py   # A2A Client — ADK agent that delegates and visualizes
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- Google API Key (Gemini 2.5 Flash access)
- Internet connection (for DuckDuckGo live scraping)

### 1. Clone the Repository

```bash
git clone https://github.com/godfather-ace/MLDS-2026-AgenticAI-Workshop.git
cd MLDS-2026-AgenticAI-Workshop/workshop-2-protocols/A2A/dem2
```

### 2. Install Dependencies

```bash
pip install crewai crewai-tools langchain-community google-adk google-genai plotly uvicorn python-dotenv duckduckgo-search
```

### 3. Configure Environment Variables

Create a `.env` file in the demo directory:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

> **Note:** The Gemini model is used by both agents. Ensure your API key has access to `gemini-2.5-flash`.

---

## 🚀 Running the Demo

### Step 1 — Start the CrewAI Analyst Agent (A2A Server)

Open a terminal and run:

```bash
python crewai_analyst_agent.py
```

The server starts on **http://localhost:8002**. Verify it's live:

```
http://localhost:8002/.well-known/agent-card.json
```

You should see the agent card JSON describing the analyst's capabilities.

### Step 2 — Run the ADK Visualiser Agent (A2A Client)

Open a **second terminal** and run:

```bash
python adk_visualiser_agent.py
```

The Visualiser will:
1. Discover the Analyst Agent via its agent card
2. Delegate the research task over A2A
3. Wait for the CrewAI crew to scrape the web and analyze results
4. Parse the structured percentage output
5. Open an **interactive Plotly bar chart** in your browser

---

## 📊 Expected Output

### Console Output

```
[Visualiser] Delegating task to CrewAI Analyst for topic: 'AI Server Infrastructure Growth in 2026'...
[Visualiser] Waiting for agent execution and A2A response...

--- Final Report Received via A2A ---
Trend 1: GPU Cluster Deployments - 78%
Trend 2: Edge AI Infrastructure - 54%
Trend 3: Hyperscaler AI Spend - 91%

[Visualiser] Extracting numbers for Plotly visualization...
```

### Chart Output

An interactive dark-themed Plotly bar chart (teal bars) with:
- **X-axis**: Trend names extracted from the analyst's report
- **Y-axis**: Growth / Market Share (%)
- **Title**: `A2A Scraped Data: AI Server Infrastructure Growth in 2026`

> The actual values will vary since the Scraper agent pulls **live data** from the web on each run.

---

## 🔍 Architecture Deep Dive

```
┌──────────────────────────────────────────────────────────┐
│                   adk_visualiser_agent.py                │
│                                                          │
│  Runner + InMemorySessionService                         │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Visualiser (ADK Agent, gemini-2.5-flash)        │    │
│  │  sub_agents=[RemoteA2aAgent → localhost:8002]    │    │
│  └──────────────────────────────────────────────────┘    │
│                         │ A2A HTTP                       │
└─────────────────────────┼────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│                crewai_analyst_agent.py                   │
│                                                          │
│  Google ADK (to_a2a wrapper)                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │  AdkAgent (crewai_analyst, gemini-2.5-flash)     │    │
│  │  tools=[scrape_and_analyze]                      │    │
│  │         │                                        │    │
│  │         ▼  CrewAI Sequential Crew                │    │
│  │  ┌─────────────────────────────────────────┐     │    │
│  │  │ Task 1: Market Researcher               │     │    │
│  │  │         DuckDuckGoSearchRun (live web)  │     │    │
│  │  │                 │                       │     │    │
│  │  │ Task 2: Data Quant (context = Task 1)   │     │    │
│  │  │         → "Trend 1: X - 42%, ..."       │     │    │
│  │  └─────────────────────────────────────────┘     │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 🔄 Comparison: Demo 1 vs Demo 2

| Feature | Demo 1 | Demo 2 |
|---|---|---|
| **A2A Server Framework** | FastAPI (manual) | Google ADK (`to_a2a`) |
| **A2A Client Framework** | `requests` (plain HTTP) | Google ADK (`RemoteA2aAgent`) |
| **LLM** | OpenAI (via CrewAI default) | Gemini 2.5 Flash |
| **Data Source** | Mock / static data | Live web (DuckDuckGo) |
| **CrewAI Agents** | 1 (Analyst) | 2 (Scraper + Data Quant, sequential) |
| **Session Management** | None | ADK `InMemorySessionService` |
| **Output Parsing** | None needed | Regex extraction from LLM text |

---

## 🧩 Key Dependencies

| Library | Purpose |
|---|---|
| `crewai` | Multi-agent orchestration framework |
| `crewai-tools` | CrewAI's `@tool` decorator for wrapping tools |
| `langchain-community` | `DuckDuckGoSearchRun` for live web search |
| `google-adk` | ADK `Agent`, `RemoteA2aAgent`, `Runner`, `to_a2a` |
| `google-genai` | `types.Content` / `types.Part` for ADK messages |
| `plotly` | Interactive charting |
| `uvicorn` | ASGI server to host the A2A server |
| `python-dotenv` | Environment variable loading |

---

## 🐛 Troubleshooting

**Chart shows "Could not extract clean percentage metrics"**
The LLM may not have followed the `Trend 1: [Name] - [Value]%` format. The Visualiser includes a fallback that uses generic labels (`Metric 1`, `Metric 2`, etc.) if label parsing fails but numbers are found. You can re-run as results vary with live data.

**DuckDuckGo rate limiting**
If you see search errors, wait 30–60 seconds before retrying. DuckDuckGo may throttle rapid repeated requests.

**`google.adk` import errors**
Ensure you are using the correct package: `pip install google-adk`. The ADK package name changed during its preview period.

**Port 8002 already in use**
Kill any existing process on that port:
```bash
lsof -ti:8002 | xargs kill -9
```

---

## 📚 Learning Objectives

After completing this demo, you will understand:

- ✅ How to **wrap a CrewAI crew as a callable tool** and expose it via Google ADK
- ✅ How **`to_a2a()`** auto-generates an A2A-compliant FastAPI server from an ADK Agent
- ✅ How **`RemoteA2aAgent`** enables one ADK agent to treat a remote service as a sub-agent
- ✅ How to build a **sequential CrewAI pipeline** with shared task context
- ✅ How to handle **non-deterministic LLM output** with robust regex parsing and fallbacks
- ✅ How **Google ADK's Runner and SessionService** manage stateful async agent execution

---
