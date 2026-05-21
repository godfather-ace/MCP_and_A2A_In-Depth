"""
============================================================
LAB 3: Advanced Patterns — Multi-Tool, Validation & SDK
============================================================

LEARNING OBJECTIVES:
    - Implement multi-turn / parallel tool-use conversation flows
    - Validate inputs against JSON Schema before execution
    - Build a reusable middleware layer (logging, retry, rate-limit)
    - Understand how the official 'mcp' Python SDK maps onto what
        you built manually in Labs 1 & 2

PARTS:
    3-A  Conversation state machine (multi-turn tool use)
    3-B  Schema-level input validation
    3-C  Middleware pipeline (logging, retry, timeout)
    3-D  SDK bridge — mapping concepts to the real mcp library
"""

import json
import time
import uuid
import random
import functools
from typing import Any, Callable
from datetime import datetime

# ─────────────────────────────────────────────
# PART 3-A: Multi-turn conversation state machine
# ─────────────────────────────────────────────
"""
A model response may contain MULTIPLE tool_use blocks.
The client must execute ALL of them, collect tool_results,
and send them back in a single follow-up message.

Message shape for multi-tool continuation:
    [
        { role: "user",      content: "<original user message>" },
        { role: "assistant", content: [tool_use_A, tool_use_B] },
        { role: "user",      content: [tool_result_A, tool_result_B] },
    ]
"""

class ConversationState:
    """Tracks the evolving message history across turns."""

    def __init__(self):
        self.messages: list[dict] = []
        self.turn = 0

    def add_user(self, text: str):
        self.messages.append({"role": "user", "content": text})
        self.turn += 1

    def add_assistant_with_tools(self, text: str, tool_uses: list[dict]):
        content = []
        if text:
            content.append({"type": "text", "text": text})
        content.extend(tool_uses)
        self.messages.append({"role": "assistant", "content": content})

    def add_tool_results(self, results: list[dict]):
        self.messages.append({"role": "user", "content": results})

    def add_final_reply(self, text: str):
        self.messages.append({"role": "assistant", "content": text})

    def print_thread(self):
        print("\n📜 Full Conversation Thread:")
        print("═" * 55)
        for i, msg in enumerate(self.messages):
            role = msg["role"].upper()
            content = msg["content"]
            print(f"\n  [{i}] {role}")
            if isinstance(content, str):
                print(f"      {content}")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        btype = block.get("type", "?")
                        if btype == "text":
                            print(f"      [text] {block['text'][:80]}")
                        elif btype == "tool_use":
                            print(f"      [tool_use] {block['name']} → {block['input']}")
                        elif btype == "tool_result":
                            txt = block["content"][0]["text"][:80]
                            err = "❌" if block.get("is_error") else "✅"
                            print(f"      [tool_result {err}] {txt}")
        print("\n" + "═" * 55)


def simulate_parallel_tool_calls():
    """
    Simulate a turn where the model decides to call two tools in parallel.
    Both results are collected before the model continues.
    """
    print("\n🔀 PART 3-A: Parallel / Multi-Tool Call Demo\n")

    conv = ConversationState()
    conv.add_user("What's the weather in London and Berlin, and what is 7! ?")

    # Model decides to call 3 tools in parallel
    tool_calls = [
        {"type": "tool_use", "id": "tu_001", "name": "get_weather", "input": {"city": "London"}},
        {"type": "tool_use", "id": "tu_002", "name": "get_weather", "input": {"city": "Berlin"}},
        {"type": "tool_use", "id": "tu_003", "name": "calculate",   "input": {"expression": "5040"}},
    ]
    conv.add_assistant_with_tools(
        "Let me look that up for you...",
        tool_calls
    )

    # Execute all tool calls (in a real client this would be concurrent)
    print("  Executing tool calls...")
    results = []
    fake_outputs = {
        "tu_001": '{"city": "London",  "temperature": "14°C", "condition": "Rainy"}',
        "tu_002": '{"city": "Berlin",  "temperature": "18°C", "condition": "Cloudy"}',
        "tu_003": "5040 = 5040",
    }
    for call in tool_calls:
        output = fake_outputs[call["id"]]
        results.append({
            "type":        "tool_result",
            "tool_use_id": call["id"],
            "content":     [{"type": "text", "text": output}],
            "is_error":    False,
        })
        print(f"    ✔ {call['name']}({call['input']}) → {output[:50]}")

    conv.add_tool_results(results)
    conv.add_final_reply(
        "London is 14°C and rainy, Berlin is 18°C and cloudy. "
        "And 7! (factorial of 7) = 5040."
    )

    conv.print_thread()


# ─────────────────────────────────────────────
# PART 3-B: Schema-level input validation
# ─────────────────────────────────────────────

class SchemaValidator:
    """
    Lightweight JSON Schema validator (subset).
    Covers: required fields, type checking, enum, min/max.
    Production code would use 'jsonschema' library instead.
    """

    TYPE_MAP = {
        "string":  str,
        "number":  (int, float),
        "integer": int,
        "boolean": bool,
        "array":   list,
        "object":  dict,
    }

    def validate(self, arguments: dict, schema: dict) -> list[str]:
        """Returns list of error strings; empty = valid."""
        errors = []
        props   = schema.get("properties", {})
        required = schema.get("required", [])

        # Check required fields
        for field in required:
            if field not in arguments:
                errors.append(f"Missing required field: '{field}'")

        # Check types, enums, ranges
        for key, value in arguments.items():
            if key not in props:
                continue                             # extra fields are ok
            spec = props[key]
            expected_type = spec.get("type")

            if expected_type and expected_type in self.TYPE_MAP:
                if not isinstance(value, self.TYPE_MAP[expected_type]):
                    errors.append(
                        f"Field '{key}': expected {expected_type}, "
                        f"got {type(value).__name__}"
                    )

            if "enum" in spec and value not in spec["enum"]:
                errors.append(
                    f"Field '{key}': value '{value}' not in {spec['enum']}"
                )

            if "minimum" in spec and isinstance(value, (int, float)):
                if value < spec["minimum"]:
                    errors.append(
                        f"Field '{key}': {value} < minimum {spec['minimum']}"
                    )

            if "maximum" in spec and isinstance(value, (int, float)):
                if value > spec["maximum"]:
                    errors.append(
                        f"Field '{key}': {value} > maximum {spec['maximum']}"
                    )

        return errors


def demo_validation():
    print("\n🛡️  PART 3-B: Input Validation Demo\n")

    validator = SchemaValidator()
    schema = {
        "type": "object",
        "properties": {
            "city":       {"type": "string"},
            "days":       {"type": "integer", "minimum": 1, "maximum": 14},
            "unit":       {"type": "string", "enum": ["metric", "imperial"]},
        },
        "required": ["city"],
    }

    test_cases = [
        # (arguments, label)
        ({"city": "Paris",  "days": 3,  "unit": "metric"},    "✅ Valid call"),
        ({"days": 3,        "unit": "metric"},                 "❌ Missing required 'city'"),
        ({"city": "Rome",   "days": 0,  "unit": "metric"},    "❌ days below minimum"),
        ({"city": "Berlin", "days": 5,  "unit": "kelvin"},    "❌ Invalid enum value"),
        ({"city": 42,       "days": 7,  "unit": "imperial"},  "❌ Wrong type for city"),
    ]

    for args, label in test_cases:
        errors = validator.validate(args, schema)
        status = "PASS" if not errors else "FAIL"
        print(f"  [{status}] {label}")
        if errors:
            for e in errors:
                print(f"         → {e}")


# ─────────────────────────────────────────────
# PART 3-C: Middleware pipeline
# ─────────────────────────────────────────────

ToolHandler = Callable[..., Any]

def logging_middleware(fn: ToolHandler) -> ToolHandler:
    """Log every call with timing."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        print(f"  [LOG] → Calling {fn.__name__}({kwargs})")
        try:
            result = fn(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            print(f"  [LOG] ← {fn.__name__} succeeded in {elapsed:.1f}ms")
            return result
        except Exception as exc:
            print(f"  [LOG] ✗ {fn.__name__} raised: {exc}")
            raise
    return wrapper


def retry_middleware(max_attempts: int = 3, delay: float = 0.1):
    """Retry transient failures up to max_attempts times."""
    def decorator(fn: ToolHandler) -> ToolHandler:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == max_attempts:
                        raise
                    print(f"  [RETRY] attempt {attempt} failed ({exc}), retrying...")
                    time.sleep(delay)
        return wrapper
    return decorator


def timeout_middleware(seconds: float):
    """Raise an error if execution takes too long (cooperative check)."""
    def decorator(fn: ToolHandler) -> ToolHandler:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            elapsed = time.perf_counter() - start
            if elapsed > seconds:
                raise TimeoutError(
                    f"{fn.__name__} took {elapsed:.2f}s > {seconds}s limit"
                )
            return result
        return wrapper
    return decorator


def demo_middleware():
    print("\n⚙️  PART 3-C: Middleware Pipeline Demo\n")

    call_count = [0]

    # Stack: logging → retry → actual handler
    @logging_middleware
    @retry_middleware(max_attempts=3, delay=0.05)
    def flaky_tool(city: str):
        """Simulates an unreliable external API."""
        call_count[0] += 1
        if call_count[0] < 3:      # fail the first two attempts
            raise ConnectionError("Network timeout")
        return f"Weather in {city}: Sunny, 22°C"

    print("  Calling flaky_tool (will fail twice, succeed on 3rd try):")
    result = flaky_tool(city="Madrid")
    print(f"\n  Final result: {result}")


# ─────────────────────────────────────────────
# PART 3-D: Mapping to the real MCP Python SDK
# ─────────────────────────────────────────────

SDK_MAPPING = """
╔═════════════════════════════════════════════════════════════╗
║          What we built  →  Real 'mcp' SDK equivalent        ║
╠═════════════════════════════════════════════════════════════╣
║                                                             ║
║  MCPServer class         →  mcp.server.Server               ║
║  @server.tool(...)       →  @server.list_tools()            ║
║                             @server.call_tool()             ║
║  make_tool(schema)       →  mcp.types.Tool(                 ║
║                               inputSchema=...)              ║
║  server.list_tools()     →  ListToolsResult(tools=[...])    ║
║  server.call_tool()      →  CallToolResult(content=[...])   ║
║  tool_use block          →  mcp.types.CallToolRequest       ║
║  tool_result block       →  mcp.types.CallToolResult        ║
║  ToolRegistry            →  Built into Server               ║
║  SchemaValidator         →  Handled by mcp + Pydantic       ║
║                                                             ║
║  Transport:                                                 ║
║    stdio (scripts)       →  StdioServerTransport            ║
║    HTTP/SSE (services)   →  SseServerTransport              ║
║                                                             ║
╚═════════════════════════════════════════════════════════════╝

REAL SDK EXAMPLE (runs with: pip install mcp):

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

app = Server("my-server")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_weather",
            description="Get the weather for a city",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_weather":
        return [TextContent(type="text", text=f"Sunny in {arguments['city']}")]

async def main():
    async with mcp.server.stdio.stdio_server() as (r, w):
        await app.run(r, w, app.create_initialization_options())

import asyncio
asyncio.run(main())
"""


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀 LAB 3 — Advanced MCP Patterns\n")

    simulate_parallel_tool_calls()
    demo_validation()
    demo_middleware()

    print("\n📚 PART 3-D: SDK Mapping Reference")
    print(SDK_MAPPING)


# ─────────────────────────────────────────────
# ✏️  EXERCISES
# ─────────────────────────────────────────────
"""
EXERCISE 3-A:
    Extend ConversationState.print_thread() to show a token count
    estimate (count words across all message strings). How does
    adding tool results grow the context?

EXERCISE 3-B:
    Add a caching_middleware that:
        - Stores results keyed by (function_name, frozenset(kwargs.items()))
        - Returns cached value on a cache hit (print "[CACHE HIT]")
        - Calls the real function on a miss (print "[CACHE MISS]")
    Apply it to 'flaky_tool' and verify the second call hits the cache.

EXERCISE 3-C:
    Combine SchemaValidator with the MCPServer from Lab 2:
        - Validate arguments BEFORE dispatching to the handler
        - If validation fails, return a structured tool_result error
        listing every validation error
    Test with: calculate(expression=42)  # wrong type

EXERCISE 3-D (Stretch — requires `pip install mcp`):
    Port the MCPServer from Lab 2 to the real SDK.
    Use StdioServerTransport and run it as a subprocess.
    Connect to it using the mcp Python client and list its tools.
"""