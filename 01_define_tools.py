"""
============================================================
LAB 1: Tool Definition in MCP
============================================================

LEARNING OBJECTIVES:
    - Understand how MCP tools are defined using JSON Schema
    - Learn required vs optional parameters
    - Explore different data types in tool schemas
    - Register multiple tools and inspect the registry

KEY CONCEPT:
    In MCP, a "tool" is a capability you expose to an AI model.
    The model reads the schema to understand what the tool does
    and how to call it — without seeing the implementation.

    Tool Definition = { name, description, inputSchema }
"""

import json

# ─────────────────────────────────────────────
# SECTION 1: The anatomy of a tool definition
# ─────────────────────────────────────────────

def make_tool(name: str, description: str, properties: dict, required: list = None) -> dict:
    """Helper to build a well-formed MCP tool definition."""
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


# ── Tool 1: Simple string input ──────────────────────────────────────────────
greet_tool = make_tool(
    name="greet_user",
    description="Greet a user by name with an optional custom message.",
    properties={
        "name": {
            "type": "string",
            "description": "The user's full name",
        },
        "message": {
            "type": "string",
            "description": "Optional custom greeting. Defaults to 'Hello'.",
        },
    },
    required=["name"],          # <-- 'message' is optional
)


# ── Tool 2: Numeric + enum inputs ────────────────────────────────────────────
calculator_tool = make_tool(
    name="calculate",
    description="Perform a basic arithmetic operation on two numbers.",
    properties={
        "a": {"type": "number", "description": "First operand"},
        "b": {"type": "number", "description": "Second operand"},
        "operation": {
            "type": "string",
            "enum": ["add", "subtract", "multiply", "divide"],
            "description": "The arithmetic operation to perform",
        },
    },
    required=["a", "b", "operation"],
)


# ── Tool 3: Array input ──────────────────────────────────────────────────────
search_tool = make_tool(
    name="search_records",
    description="Search a dataset using one or more keyword tags.",
    properties={
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of keyword tags to search for",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results to return (default: 10)",
            "minimum": 1,
            "maximum": 100,
        },
    },
    required=["tags"],
)


# ── Tool 4: Nested object input ──────────────────────────────────────────────
send_email_tool = make_tool(
    name="send_email",
    description="Send an email to a recipient.",
    properties={
        "recipient": {
            "type": "object",
            "description": "The email recipient",
            "properties": {
                "address": {"type": "string", "description": "Email address"},
                "name":    {"type": "string", "description": "Display name"},
            },
            "required": ["address"],
        },
        "subject": {"type": "string", "description": "Email subject line"},
        "body":    {"type": "string", "description": "Email body (plain text or HTML)"},
        "cc":      {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional CC email addresses",
        },
    },
    required=["recipient", "subject", "body"],
)


# ─────────────────────────────────────────────
# SECTION 2: A simple in-memory tool registry
# ─────────────────────────────────────────────

class ToolRegistry:
    """Mimics what an MCP server maintains internally."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, tool: dict):
        name = tool["name"]
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = tool
        print(f"  ✔  Registered tool: '{name}'")

    def list_tools(self) -> list[dict]:
        """Returns the tool list an MCP server sends to clients."""
        return list(self._tools.values())

    def get(self, name: str) -> dict:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: '{name}'")
        return self._tools[name]

    def pretty_print(self):
        print("\n📋 Registered Tools:")
        print("=" * 55)
        for tool in self._tools.values():
            schema = tool["inputSchema"]
            req    = schema.get("required", [])
            params = list(schema["properties"].keys())
            print(f"\n  🔧 {tool['name']}")
            print(f"     {tool['description']}")
            print(f"     Parameters : {params}")
            print(f"     Required   : {req}")
        print("=" * 55)


# ─────────────────────────────────────────────
# SECTION 3: Run it
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀 LAB 1 — Tool Definition\n")

    registry = ToolRegistry()
    print("Registering tools...")
    for t in [greet_tool, calculator_tool, search_tool, send_email_tool]:
        registry.register(t)

    registry.pretty_print()

    # ── Inspect a single tool's raw JSON Schema ──
    print("\n📄 Raw JSON Schema for 'calculate':")
    print(json.dumps(registry.get("calculate"), indent=2))

    # ── Simulate the MCP tools/list response ────
    print("\n📡 MCP tools/list payload (what the client receives):")
    tools_list_response = {"tools": registry.list_tools()}
    print(json.dumps(tools_list_response, indent=2))


# ─────────────────────────────────────────────
# ✏️  EXERCISES  (attempt before checking solutions)
# ─────────────────────────────────────────────
"""
EXERCISE 1-A:
    Define a new tool called "convert_currency" that:
        - Takes: amount (number, required), from_currency (string, required),
                to_currency (string, required), round_decimals (integer, optional)
        - Description: "Convert an amount between two currencies"
    Register it and verify it appears in list_tools().

EXERCISE 1-B:
    Add a "boolean" parameter called "include_metadata" to the search_records
    tool, and make it optional (default behaviour: exclude metadata).
    How does this change the JSON Schema?

EXERCISE 1-C (Stretch):
    Write a validate_tool_call() function that:
        - Accepts a tool name and a dict of arguments
        - Checks that all required parameters are present
        - Raises a descriptive ValueError if any are missing
    Test it with both valid and invalid calls to the 'send_email' tool.
"""