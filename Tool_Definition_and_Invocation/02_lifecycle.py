"""
============================================================
LAB 2: The Full Tool Invocation Lifecycle
============================================================

LEARNING OBJECTIVES:
    - Trace every phase: Definition → Discovery → Selection
        → Invocation → Execution → Result → Continuation
    - Build a minimal MCP-style server + client from scratch
    - Understand tool_use and tool_result message formats
    - Handle success and error results correctly

KEY CONCEPT — the lifecycle has 7 distinct steps:

    ┌─────────────────────────────────────────────────────────┐
    │  1. DEFINE    Server declares tools in a registry       │
    │  2. DISCOVER  Client calls tools/list → gets schemas    │
    │  3. SELECT    Model reads schemas, picks the right tool  │
    │  4. INVOKE    Model emits a tool_use block              │
    │  5. EXECUTE   Server runs the handler, captures output  │
    │  6. RETURN    Server sends back a tool_result block     │
    │  7. CONTINUE  Model reads result, completes its reply   │
    └─────────────────────────────────────────────────────────┘
"""

import json
import math
import uuid
from datetime import datetime
from typing import Any, Callable

# ─────────────────────────────────────────────
# PHASE 1 & 2 — DEFINE  +  DISCOVER
# ─────────────────────────────────────────────

class MCPServer:
    """
    A minimal, self-contained MCP server.
    Handles tool registration and dispatches calls.
    """

    def __init__(self, name: str):
        self.name = name
        self._tools: dict[str, dict]     = {}
        self._handlers: dict[str, Callable] = {}

    # ── Registration ────────────────────────────────────────────────────────

    def tool(self, name: str, description: str, schema: dict):
        """Decorator: register a function as an MCP tool."""
        def decorator(fn: Callable):
            self._tools[name] = {
                "name": name,
                "description": description,
                "inputSchema": schema,
            }
            self._handlers[name] = fn
            return fn
        return decorator

    # ── Discovery (MCP tools/list) ──────────────────────────────────────────

    def list_tools(self) -> dict:
        """Simulate the MCP tools/list RPC response."""
        return {"tools": list(self._tools.values())}

    # ── Execution (MCP tools/call) ──────────────────────────────────────────

    def call_tool(self, name: str, arguments: dict) -> dict:
        """
        Simulate the MCP tools/call RPC.
        Returns a well-formed tool_result message.
        """
        if name not in self._handlers:
            return self._error_result(name, f"Unknown tool '{name}'")

        try:
            output = self._handlers[name](**arguments)
            return {
                "type":    "tool_result",
                "tool_use_id": str(uuid.uuid4()),
                "content": [{"type": "text", "text": str(output)}],
                "is_error": False,
            }
        except Exception as exc:
            return self._error_result(name, str(exc))

    @staticmethod
    def _error_result(name: str, message: str) -> dict:
        return {
            "type":    "tool_result",
            "tool_use_id": str(uuid.uuid4()),
            "content": [{"type": "text", "text": f"[ERROR] {message}"}],
            "is_error": True,
        }


# ─────────────────────────────────────────────
# PHASE 1 — Register real tool implementations
# ─────────────────────────────────────────────

server = MCPServer("demo-server")

@server.tool(
    name="get_weather",
    description="Get the current weather for a city.",
    schema={
        "type": "object",
        "properties": {
            "city":   {"type": "string",  "description": "City name"},
            "metric": {"type": "boolean", "description": "True = Celsius, False = Fahrenheit"},
        },
        "required": ["city"],
    },
)
def get_weather(city: str, metric: bool = True) -> str:
    # Stub — real implementation would call a weather API
    import random
    temp  = random.randint(10, 35) if metric else random.randint(50, 95)
    unit  = "°C" if metric else "°F"
    conds = random.choice(["Sunny", "Cloudy", "Partly cloudy", "Rainy"])
    return json.dumps({
        "city": city,
        "temperature": f"{temp}{unit}",
        "condition": conds,
        "timestamp": datetime.utcnow().isoformat(),
    })


@server.tool(
    name="calculate",
    description="Evaluate a safe mathematical expression.",
    schema={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "A mathematical expression, e.g. '2 ** 10 + sqrt(16)'",
            }
        },
        "required": ["expression"],
    },
)
def calculate(expression: str) -> str:
    allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)   # nosec
        return f"{expression} = {result}"
    except Exception as exc:
        raise ValueError(f"Cannot evaluate '{expression}': {exc}") from exc


@server.tool(
    name="list_files",
    description="List files in a directory path (simulated).",
    schema={
        "type": "object",
        "properties": {
            "path":      {"type": "string", "description": "Directory path"},
            "extension": {"type": "string", "description": "Filter by extension, e.g. '.py'"},
        },
        "required": ["path"],
    },
)
def list_files(path: str, extension: str = None) -> str:
    # Stub filesystem
    fake_fs = {
        "/home/user": ["notes.txt", "script.py", "data.csv", "readme.md"],
        "/home/user/projects": ["app.py", "utils.py", "tests.py", "config.yaml"],
        "/tmp": ["cache.db", "log.txt"],
    }
    files = fake_fs.get(path, [])
    if extension:
        files = [f for f in files if f.endswith(extension)]
    return json.dumps({"path": path, "files": files, "count": len(files)})


# ─────────────────────────────────────────────
# PHASE 3–7 — The full lifecycle, step by step
# ─────────────────────────────────────────────

class LifecycleTracer:
    """Walks through all 7 lifecycle phases with verbose logging."""

    def __init__(self, server: MCPServer):
        self.server = server

    def _banner(self, phase: str, emoji: str = ""):
        print(f"\n{'─'*55}")
        print(f"  {emoji}  PHASE: {phase}")
        print(f"{'─'*55}")

    # ── PHASE 2: Discovery ───────────────────────────────────────────────────

    def discover(self) -> list[dict]:
        self._banner("DISCOVER  —  Client calls tools/list", "🔍")
        response = self.server.list_tools()
        tools    = response["tools"]
        print(f"\n  Server advertises {len(tools)} tool(s):\n")
        for t in tools:
            params = list(t["inputSchema"]["properties"].keys())
            req    = t["inputSchema"].get("required", [])
            print(f"    📦 {t['name']}")
            print(f"       {t['description']}")
            print(f"       params={params}  required={req}\n")
        return tools

    # ── PHASE 3 & 4: Model selects + emits tool_use ──────────────────────────

    def model_selects(self, tool_name: str, arguments: dict) -> dict:
        self._banner("SELECT + INVOKE  —  Model emits tool_use block", "🤖")
        tool_use_block = {
            "type":  "tool_use",
            "id":    f"toolu_{uuid.uuid4().hex[:12]}",
            "name":  tool_name,
            "input": arguments,
        }
        print("\n  Model chose to call:", tool_name)
        print("  tool_use block:\n")
        print(json.dumps(tool_use_block, indent=4))
        return tool_use_block

    # ── PHASE 5 & 6: Server executes + returns tool_result ───────────────────

    def server_executes(self, tool_use_block: dict) -> dict:
        self._banner("EXECUTE + RETURN  —  Server runs handler", "⚙️ ")
        name      = tool_use_block["name"]
        arguments = tool_use_block["input"]
        print(f"\n  Dispatching '{name}' with arguments: {arguments}")
        result = self.server.call_tool(name, arguments)
        result["tool_use_id"] = tool_use_block["id"]   # link back to the invocation
        print("\n  tool_result block:\n")
        print(json.dumps(result, indent=4))
        return result

    # ── PHASE 7: Model continues with result in context ──────────────────────

    def model_continues(self, tool_result: dict):
        self._banner("CONTINUE  —  Model generates final response", "💬")
        if tool_result["is_error"]:
            text = tool_result["content"][0]["text"]
            print(f"\n  ⚠️  Tool returned an error: {text}")
            print("  Model would now apologise or suggest an alternative.")
        else:
            text = tool_result["content"][0]["text"]
            print(f"\n  ✅ Tool result received:\n  {text}")
            print("\n  Model weaves result into its reply:")
            print("  ┌─────────────────────────────────────────────────┐")
            print(f"  │  Based on the tool output, here is your answer  │")
            print(f"  │  ...  (result text)  ...                        │")
            print("  └─────────────────────────────────────────────────┘")

    # ── Full end-to-end run ──────────────────────────────────────────────────

    def run(self, tool_name: str, arguments: dict):
        print(f"\n{'═'*55}")
        print(f"  🚦 FULL LIFECYCLE TRACE — '{tool_name}'")
        print(f"{'═'*55}")

        self.discover()
        tool_use    = self.model_selects(tool_name, arguments)
        tool_result = self.server_executes(tool_use)
        self.model_continues(tool_result)

        print(f"\n{'═'*55}")
        print("  ✔ Lifecycle complete")
        print(f"{'═'*55}\n")


# ─────────────────────────────────────────────
# MAIN — Run three different scenarios
# ─────────────────────────────────────────────

if __name__ == "__main__":
    tracer = LifecycleTracer(server)

    # Scenario A — success path
    tracer.run("get_weather", {"city": "Tokyo", "metric": True})

    # Scenario B — math expression
    tracer.run("calculate", {"expression": "sqrt(144) + 2 ** 8"})

    # Scenario C — error path (bad expression)
    tracer.run("calculate", {"expression": "import os; os.system('rm -rf /')"})


# ─────────────────────────────────────────────
# ✏️  EXERCISES
# ─────────────────────────────────────────────
"""
EXERCISE 2-A:
    Add a new tool "convert_units" to the server using the @server.tool
    decorator. It should convert between units of length (m, km, miles, feet).
    Trace its full lifecycle using the LifecycleTracer.

EXERCISE 2-B:
    The model may call MULTIPLE tools in sequence (chaining).
    Write a function run_chain(tracer, steps) where each step is
    (tool_name, arguments). Run it with:
        step 1 → list_files("/home/user/projects", ".py")
        step 2 → get_weather("Paris")
    Print the combined context the model would receive.

EXERCISE 2-C (Stretch):
    Add argument validation to MCPServer.call_tool():
        - Check that all "required" parameters are present before calling the handler
        - Return a structured error result if any are missing
        - Test with a deliberate missing-argument call.
"""