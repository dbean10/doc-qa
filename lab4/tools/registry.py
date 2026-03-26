"""
lab4/tools/registry.py

Single source of truth for all tools.

Public interface (the only two things chatbot.py imports from this module):
    get_tool_schemas() -> list[dict]   — pass to Anthropic tools= parameter
    dispatch(name, input) -> str       — execute a tool, always returns JSON

Adding a new tool:
    1. Create lab4/tools/my_tool.py with a function that returns dict
    2. Import it here
    3. Add one entry to REGISTRY
    Done. chatbot.py is untouched.

MCP portability note:
    list_tools() and call_tool() in a Week 7 MCP server are direct
    replacements for get_tool_schemas() and dispatch(). The REGISTRY dict
    and tool implementation files are reused unchanged.
"""

from __future__ import annotations

import json

from lab4.tools.weather import get_weather
from lab4.tools.reminder import create_reminder

# search_docs is imported after the RAG stack is built (lab4/rag/retriever.py).
# Uncomment when retriever.py exists:
from lab4.rag.retriever import search_docs


# ---------------------------------------------------------------------------
# Registry — schema + callable co-located per tool
# ---------------------------------------------------------------------------

REGISTRY: dict[str, dict] = {

    "get_weather": {
        "schema": {
            "name": "get_weather",
            "description": (
                "Get current weather conditions for a city. "
                "Use when the user asks about weather, temperature, forecast, "
                "humidity, or outdoor conditions in any specific location. "
                "Do not use for historical weather or general climate questions."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": (
                            "City name, e.g. 'Denver' or 'Paris, France'. "
                            "Use the most specific name the user provided."
                        ),
                    },
                },
                "required": ["location"],
            },
        },
        "fn": get_weather,
    },

    "create_reminder": {
        "schema": {
            "name": "create_reminder",
            "description": (
                "Create a reminder for the user at a specific future time. "
                "Use only when the user explicitly asks to be reminded about "
                "something. Do not use for general notes or tasks without a "
                "stated time."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "What to remind the user about.",
                    },
                    "time": {
                        "type": "string",
                        "description": (
                            "When to trigger the reminder in natural language, "
                            "e.g. 'tomorrow at 9am' or 'in 2 hours'. "
                            "Preserve the user's exact phrasing."
                        ),
                    },
                },
                "required": ["text", "time"],
            },
        },
        "fn": create_reminder,
    },

    "search_docs": {
        "schema": {
            "name": "search_docs",
            "description": (
                "Search the internal knowledge base for relevant documents. "
                "Use when the user asks a question that might be answered by "
                "stored documentation, guides, or reference material. "
                "Do not use for real-time data, weather, or reminders."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "The search query. Use the user's natural language "
                            "question directly — do not rephrase."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return. Default 3, max 10.",
                    },
                },
                "required": ["query"],
            },
        },
        "fn": search_docs,
    },
}


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_tool_schemas() -> list[dict]:
    """
    Return the list of tool schema dicts to pass to the Anthropic tools= parameter.

    Example:
        response = client.messages.create(
            model=config.MODEL,
            tools=get_tool_schemas(),
            messages=messages,
        )
    """
    return [entry["schema"] for entry in REGISTRY.values()]


def dispatch(tool_name: str, tool_input: dict) -> str:
    """
    Execute a tool by name with the given input dict.

    Always returns a JSON string — the format Anthropic's tool_result expects.
    Never raises — all errors are returned as JSON with {"error": True, ...}.

    Security: tool_name is validated against the REGISTRY allowlist before
    any execution. Unknown tool names are rejected — they cannot be executed
    even if the model hallucinates a plausible-sounding name.

    Args:
        tool_name:  Name of the tool to call (must be a key in REGISTRY).
        tool_input: Dict of arguments generated by the model.

    Returns:
        JSON string. Always. Even on error.
    """
    # --- Allowlist check — unknown tools are rejected, not executed ---
    if tool_name not in REGISTRY:
        return json.dumps({
            "error": True,
            "message": f"Unknown tool '{tool_name}'. "
                       f"Available: {list(REGISTRY.keys())}",
        })

    fn = REGISTRY[tool_name]["fn"]

    try:
        result = fn(**tool_input)
        return json.dumps(result)

    except TypeError as exc:
        # Model passed wrong argument names or missing required args.
        # Return as data so the model can explain the issue to the user.
        return json.dumps({
            "error": True,
            "message": f"Invalid arguments for '{tool_name}': {exc}",
        })

    except Exception as exc:  # noqa: BLE001
        # Unexpected error in tool implementation.
        # Log in production; return safe message to model.
        return json.dumps({
            "error": True,
            "message": f"Tool '{tool_name}' failed unexpectedly: {exc}",
        })
