# Project Guideline: MCP / A2A Code Solution

**Assessment Project | Individual Submission**

---

## Overview

This project requires you to design and implement a working code solution that leverages **Model Context Protocol (MCP)** and/or **Agent-to-Agent (A2A)** communication patterns. You will build an agentic system where AI models interact with tools, services, or other agents to complete a meaningful task.

---

## Objectives

- Demonstrate understanding of MCP and/or A2A architecture
- Build a functional, runnable solution with clear agent interactions
- Write clean, documented code that can be independently assessed
- Reflect on design decisions through documentation

---

## Background Concepts

### Model Context Protocol (MCP)
MCP is an open standard that allows AI models to interact with external tools and data sources through a structured client–server interface. An MCP server exposes *tools*, *resources*, and *prompts*; an MCP client (typically an AI host or agent) calls them.

### Agent-to-Agent (A2A)
A2A is a communication pattern where multiple AI agents coordinate with each other — delegating tasks, sharing results, and acting on each other's outputs — to solve problems that benefit from specialisation or parallelism.

---

## Project Requirements

### 1. Functional Scope
Your solution must include **at least one** of the following:

| Approach | Minimum Requirement |
|---|---|
| **MCP-only** | One working MCP server with ≥ 2 tools; one client agent that calls them |
| **A2A-only** | Two distinct agents that exchange messages to complete a task |
| **MCP + A2A** | At least one MCP server and two communicating agents |

### 2. Use Case
Choose a real-world or practical use case. Examples (you may define your own):

- Research assistant that queries a knowledge base and summarises results
- Code review agent that delegates sub-tasks to specialist agents
- Data pipeline where agents fetch, transform, and report data via MCP tools
- Customer support bot that routes queries between agents

### 3. Technical Requirements

- **Language**: Python
- **MCP SDK**: Use the official Anthropic MCP SDK or a compatible library
- **Agent model**: Use any LLM API 
- **Running locally**: The solution must run end-to-end on a local machine
- **No hardcoded secrets**: Use environment variables for all API keys

### 4. Code Quality

- Code must be readable and logically organised
- Functions/classes should have docstrings or JSDoc comments
- A `requirements.txt` or `package.json` must be included

---

## Deliverables

Submit the following in a single compressed folder or repository link:

```
project/
├── README.md              ← Setup & run instructions
├── DESIGN.md              ← Architecture decisions (see below)
├── src/
│   ├── server/            ← MCP server(s), if applicable
│   └── agents/            ← Agent definitions
├── tests/                 ← At least 2 test cases
├── .env.example           ← Template for required environment variables
└── requirements.txt       ← or package.json
```

### README.md must include:
- Project description (2–3 sentences)
- Prerequisites and installation steps
- How to run the solution
- A sample input/output or screenshot

---

## Assessment Criteria

| Criterion | Weight | Description |
|---|---|---|
| **Functionality** | 30% | Solution runs and produces correct output |
| **MCP / A2A Understanding** | 25% | Correct and meaningful use of the protocols |
| **Code Quality** | 20% | Readability, structure, error handling |
| **Documentation** | 15% | README, DESIGN.md, inline comments |
| **Creativity / Complexity** | 10% | Originality of use case or depth of implementation |

---

## Constraints & Rules

- This is an **individual** project — all code must be your own
- You may use open-source libraries, but cite any substantial reference implementations
- Do not share your solution with other participants before the submission deadline

---

## Submission

| Item | Detail |
|---|---|
| **Format** | public Git repository URL |

---
