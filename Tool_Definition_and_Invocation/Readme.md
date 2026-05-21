# MCP — Tool Definition & Invocation Lifecycle
---

## Overview

| Lab | Topic | File |
|-----|-------|------|
| **1** | Tool Definition & Registry | `01_define_tools.py` |
| **2** | The Full Invocation Lifecycle | `02_lifecycle.py` |
| **3** | Advanced: Multi-Tool, Validation, Middleware | `03_advanced.py` |
| — | Review & Discussion | 

---

## Prerequisites

```bash
python --version   # 3.10+
# No external dependencies required for Labs 1–3
# Optional (Lab 3-D stretch): pip install mcp
```

---

## The 7-Phase MCP Lifecycle (Mental Model)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  1. DEFINE    Server declares tools with JSON Schema     │
│       ↓                                                  │
│  2. DISCOVER  Client calls tools/list → receives schemas │
│       ↓                                                  │
│  3. SELECT    Model reads schemas, decides which to call │
│       ↓                                                  │
│  4. INVOKE    Model emits a tool_use block in response   │
│       ↓                                                  │
│  5. EXECUTE   Server finds handler, runs it safely       │
│       ↓                                                  │
│  6. RETURN    Server wraps output in a tool_result block │
│       ↓                                                  │
│  7. CONTINUE  Model reads result, completes its reply    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Lab 1 — Tool Definition 

**Run:**
```bash
python 01_define_tools.py
```

**Key concepts:**
- Every tool = `{ name, description, inputSchema }`
- `inputSchema` is a JSON Schema object (type, properties, required)
- The **description** is the model's only guide — write it well
- Parameters can be: `string`, `number`, `integer`, `boolean`, `array`, `object`
- `required: [...]` lists mandatory parameters; omitted = optional

**What to look for in the output:**
- The raw JSON Schema a model actually sees
- The `tools/list` response payload
- How `required` differs from optional fields

---

## Lab 2 — The Invocation Lifecycle

**Run:**
```bash
python 02_lifecycle.py
```

**Key concepts:**
- `tools/list` → discovery (Phases 1–2)
- `tool_use` block → what the model emits (Phases 3–4)
- `call_tool()` → server execution (Phase 5)
- `tool_result` block → what the server returns (Phase 6)
- Model reads result, continues its reply (Phase 7)

**Observe:**
- The unique `id` / `tool_use_id` linking call ↔ result
- How errors are structured (same shape, `is_error: true`)
- Three scenarios: success, computation, deliberate error

---

## Lab 3 — Advanced Patterns

**Run:**
```bash
python 03_advanced.py
```

**Part 3-A — Parallel tool calls:**
- One model turn can emit *multiple* `tool_use` blocks
- Client must collect *all* results before continuing
- Results go back as a single user message with a list of `tool_result` blocks

**Part 3-B — Input validation:**
- Validate before dispatching to protect handlers
- Check: required fields, types, enum membership, min/max
- In production: use `jsonschema` library

**Part 3-C — Middleware:**
- Wrap handlers for logging, retry, caching, timeout
- Middleware is transparent to the MCP protocol layer

**Part 3-D — SDK mapping:**
- Study the printed table mapping your manual code → real SDK types
- The concepts are identical; only the async wiring differs

---

## Exercise Quick-Reference

| Exercise | Skill Practiced |
|----------|----------------|
| 1-A | Define a new tool schema from scratch |
| 1-B | Add optional boolean parameters |
| 1-C | Write a schema validator function |
| 2-A | Register a handler with the decorator API |
| 2-B | Chain multiple tool calls |
| 2-C | Add pre-dispatch argument validation |
| 3-A | Estimate conversation context size |
| 3-B | Implement caching middleware |
| 3-C | Integrate validation into MCPServer |
| 3-D ⭐ | Port to the real `mcp` SDK |

---

## Key Takeaways

1. **The schema IS the API contract** — the model can only use what you document.
2. **tool_use_id** is the critical linking field between call and result.
3. **Errors are first-class** — always return a `tool_result` (never raise into the protocol).
4. **Parallel calls** are normal — design handlers to be stateless and concurrent-safe.
5. **Middleware** belongs outside the MCP protocol layer — keep handlers pure.
6. **The real SDK** is just an async wrapper around the same JSON protocol you built here.

---

## Further Reading

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Anthropic Tool Use Docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)