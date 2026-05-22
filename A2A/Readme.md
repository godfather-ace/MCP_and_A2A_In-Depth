# 🤝 Demo 1 — Agent-to-Agent (A2A) Protocol with CrewAI

> **MLDS 2026 AgenticAI Workshop | Workshop 2: Agentic Protocols**

This demo illustrates the **Agent-to-Agent (A2A) Protocol** in action — a lightweight HTTP-based standard that allows independent AI agents to discover each other, communicate, and collaborate without being coupled to the same framework or codebase.

---

## 📌 What This Demo Does

Two agents work together across separate processes:

| Agent | File | Role |
|---|---|---|
| **Analyst Agent** | `analyst_agent.py` | A **CrewAI-powered** FastAPI server that analyzes text input and returns 3 key trends |
| **Visualiser Agent** | `visualiser_agent.py` | A standalone client that calls the Analyst via A2A and renders an interactive Plotly chart |

**The Flow:**

```
User Prompt
    │
    ▼
Visualiser Agent
    │  HTTP POST /execute  (A2A call)
    ▼
Analyst Agent (CrewAI)
    │  Returns 3 trends
    ▼
Visualiser Agent
    │  Renders Interactive Chart
    ▼
Browser Window (Plotly Dark Theme)
```

---

## 🧠 A2A Protocol — Key Concepts Demonstrated

### 1. Agent Discovery via Agent Card
The Analyst Agent exposes a **well-known discovery endpoint** at:

```
GET /.well-known/agent-card.json
```

This returns metadata about the agent — its name, description, capabilities, and execution endpoint — allowing any other agent to discover and integrate with it dynamically.

```json
{
  "name": "crewai_analyst",
  "description": "An agent that analyzes data using CrewAI.",
  "capabilities": ["data_analysis"],
  "endpoint": "/execute"
}
```

### 2. Agent Execution via Standard HTTP
Any agent (regardless of framework) can invoke the Analyst by posting to:

```
POST /execute
Content-Type: application/json

{ "input": "Analyze the growth of Generative AI in 2025." }
```

This decoupling is the heart of A2A — **the caller doesn't need to know or care that CrewAI is running underneath**.

---

## 🗂️ File Structure

```
dem1/
├── analyst_agent.py      # A2A Server — CrewAI Data Analyst (FastAPI, port 8001)
├── visualiser_agent.py   # A2A Client — Calls analyst and renders Plotly chart
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.12
- An OpenAI API key (used by CrewAI under the hood)

### 1. Clone the Repository

```bash
git clone https://github.com/godfather-ace/MLDS-2026-AgenticAI-Workshop.git
cd MLDS-2026-AgenticAI-Workshop/workshop-2-protocols/A2A/dem1
```

### 2. Install Dependencies

```bash
pip install fastapi uvicorn crewai plotly requests python-dotenv
```

### 3. Configure Environment Variables

Create a `.env` file in the `dem1/` directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

---

## 🚀 Running the Demo

### Step 1 — Start the Analyst Agent (A2A Server)

Open a terminal and run:

```bash
python analyst_agent.py
```

The Analyst Agent will start on **http://localhost:8001**.

You can verify it's running by visiting:
```
http://localhost:8001/.well-known/agent-card.json
```

### Step 2 — Run the Visualiser Agent (A2A Client)

Open a **second terminal** and run:

```bash
python visualiser_agent.py
```

The Visualiser will:
1. Call the Analyst Agent via the A2A `/execute` endpoint
2. Print the trend analysis to the console
3. Open an **interactive Plotly chart** in your browser

---

## 📊 Expected Output

### Console Output

```
[Visualiser] Calling CrewAI Analyst via A2A...

--- Analyst Report ---
• Rapid expansion of multimodal AI models across industry verticals
• Increased enterprise adoption driven by cost reduction and automation
• Emergence of agentic frameworks enabling autonomous decision-making

[Visualiser] Generating Interactive Chart...
```

### Chart Output

An interactive dark-themed Plotly chart showing two area traces:
- **Industry Adoption (%)** — 45% → 70% → 95%
- **Model Sophistication** — 30% → 65% → 90%

across the years 2024, 2025, and 2026 (projected).

---

## 🔍 How the A2A Protocol Works Here

```
┌─────────────────────────────────────┐
│         Visualiser Agent            │
│  (Plain Python — no AI framework)   │
│                                     │
│  POST http://localhost:8001/execute │
│  { "input": "..." }                 │
└────────────────┬────────────────────┘
                 │ HTTP
                 ▼
┌─────────────────────────────────────┐
│          Analyst Agent              │
│  (FastAPI + CrewAI under the hood)  │
│                                     │
│  /execute  ──► CrewAI Crew runs    │
│  Returns: { "output": "...",        │
│             "status": "completed" } │
└─────────────────────────────────────┘
```

The Visualiser agent is **completely framework-agnostic** — it only knows the A2A contract (an HTTP endpoint that accepts `input` and returns `output`). You could swap CrewAI for LangChain, AutoGen, or any other framework on the server side and the client would not need to change at all.

---

## 🧩 Key Dependencies

| Library | Purpose |
|---|---|
| `fastapi` | Web framework for the A2A server |
| `uvicorn` | ASGI server to run FastAPI |
| `crewai` | Multi-agent orchestration framework |
| `plotly` | Interactive charting |
| `requests` | HTTP client for A2A calls |
| `python-dotenv` | Environment variable management |

---

## 📚 Learning Objectives

After completing this demo, you will understand:

- ✅ What the **A2A Protocol** is and why it matters for agent interoperability
- ✅ How to expose an agent as an **A2A-compliant server** using FastAPI
- ✅ How to implement **agent discovery** via the `/.well-known/agent-card.json` standard
- ✅ How to build an **A2A client** that calls a remote agent over HTTP
- ✅ How CrewAI agents can be **wrapped and exposed** as protocol-compliant services

---