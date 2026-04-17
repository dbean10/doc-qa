# lab7/mcp_server.py
"""
MCP Server — Week 7
Exposes three tools over stdio (local) or SSE (production).
Transport selected via MCP_TRANSPORT env var (default: stdio).
Tool implementations reused unchanged from lab4.

Architecture:
  registry.py pattern → FastMCP decorator pattern
  get_tool_schemas()  → @mcp.tool() (schema auto-generated from type hints)
  dispatch()          → FastMCP handles routing
  Tool files          → unchanged (weather.py, reminder.py, retriever.py)
"""

import os
import sys
from pathlib import Path
from typing import Final

# Make lab4 importable from lab7
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp import FastMCP

from lab4.tools.weather import get_weather
from lab4.tools.reminder import create_reminder
from lab4.rag.retriever import search_docs
from config import ENVIRONMENT

# ---------------------------------------------------------------------------
# Transport config — mirrors the ENVIRONMENT switch pattern from config.py
# MCP_TRANSPORT=stdio  → local dev, Claude Desktop, test harness
# MCP_TRANSPORT=sse    → production, Cloud Run, HTTP long-running process
# ---------------------------------------------------------------------------
MCP_TRANSPORT: Final[str] = os.getenv("MCP_TRANSPORT", "stdio")

# ---------------------------------------------------------------------------
# Server definition
# ---------------------------------------------------------------------------
mcp = FastMCP(
    name="doc-qa-mcp",
    instructions=(
        "You are a research assistant with access to three tools. "
        "Use search_docs to retrieve information from the knowledge base. "
        "Use get_weather to retrieve weather for a location. "
        "Use create_reminder to save reminders for the user. "
        "\n\n"
        "## Tool Failure Protocol\n\n"
        "Tools are tiered by criticality:\n\n"
        "TIER 1 — CORE (search_docs):\n"
        "If search_docs returns an error, immediately stop the research "
        "task. Do not attempt other tools as a substitute. Do not fabricate "
        "information that would have come from search. Respond: "
        "'I was unable to complete this research task. The document search "
        "tool is currently unavailable. Please try again later.'\n\n"
        "TIER 2 — SUPPLEMENTARY (get_weather):\n"
        "If get_weather returns an error, note the limitation and continue. "
        "Include in your response: 'Note: weather data was unavailable.'\n\n"
        "TIER 3 — WRITE (create_reminder):\n"
        "If create_reminder returns an error, complete the task as normal "
        "and note the failure briefly.\n\n"
        "In all cases: never present information as retrieved if it was not. "
        "An honest partial result is always preferred over a complete "
        "fabricated result."
    ),
)


# ---------------------------------------------------------------------------
# Tool registrations
# FastMCP generates the JSON schema automatically from type hints + docstring.
# The underlying functions (weather.py, reminder.py, retriever.py) are
# unchanged — same Morgan four-checks, same never-raises contract.
# ---------------------------------------------------------------------------

@mcp.tool()
def search_documents(query: str) -> dict:
    """
    Search the document knowledge base using semantic similarity.
    Use this tool when the user asks a question that requires retrieving
    information from stored documents, policies, or knowledge base content.
    Do NOT use for weather, reminders, or general knowledge questions.

    Returns numbered results with source attribution, or an error dict
    if the knowledge base is unavailable.
    """
    return search_docs(query=query)


@mcp.tool()
def get_current_weather(location: str) -> dict:
    """
    Get the current weather for a location.
    Use this tool when the user asks about weather conditions in a city or region.
    Do NOT use for document retrieval or reminder creation.

    Returns temperature, conditions, and humidity, or an error dict
    if the weather service is unavailable.
    """
    return get_weather(location=location)


@mcp.tool()
def save_reminder(text: str, time: str) -> dict:
    """
    Save a reminder with a description and time.
    Use this tool when the user asks to be reminded of something.
    Do NOT use for document retrieval or weather queries.

    Returns a confirmation with the reminder ID, or an error dict
    if the reminder service is unavailable.
    """
    return create_reminder(text=text, time=time)


# ---------------------------------------------------------------------------
# Entry point — transport switch mirrors config.py ENVIRONMENT pattern
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[mcp_server] Starting — transport={MCP_TRANSPORT} env={ENVIRONMENT}", 
          file=sys.stderr)

    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    elif MCP_TRANSPORT == "sse":
        port = int(os.getenv("PORT", "8080"))
        mcp.run(transport="sse", port=port)
    else:
        raise ValueError(
            f"Unknown MCP_TRANSPORT: {MCP_TRANSPORT!r}. "
            "Valid values: 'stdio', 'sse'"
        )