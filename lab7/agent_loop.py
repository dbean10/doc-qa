# lab7/agent_loop.py
"""
Python ReAct agent loop — Week 7.
Mirrors the TypeScript agent.ts implementation.

Used by:
  - test_agent.py (eval suite)
  - Direct CLI testing: uv run python lab7/agent_loop.py "your query"

Transport: calls tool implementations directly (in-process).
No HTTP — tools are imported and called as Python functions.
This is the test-safe path; production uses Next.js → HTTP → FastAPI.
"""

import os
import sys
import json
from pathlib import Path
from typing import TypedDict, Literal, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAX_AGENT_LOOPS = int(os.getenv("MAX_AGENT_LOOPS", "5"))

client = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# Tool implementations — imported directly, no HTTP needed for tests
# ---------------------------------------------------------------------------
from lab4.tools.weather import get_weather  # noqa: E402
from lab4.tools.reminder import create_reminder  # noqa: E402
from lab4.rag.retriever import search_docs  # noqa: E402

TOOL_REGISTRY = {
    "search_documents": lambda inp: search_docs(query=inp["query"]),
    "get_current_weather": lambda inp: get_weather(location=inp["location"]),
    "save_reminder": lambda inp: create_reminder(
        text=inp["text"], time=inp["time"]
    ),
}

# ---------------------------------------------------------------------------
# Tool schemas — same as tools.ts
# ---------------------------------------------------------------------------
AGENT_TOOLS = [
    {
        "name": "search_documents",
        "description": (
            "Search the company knowledge base using semantic similarity. "
            "The knowledge base contains company documents including refund "
            "policies, terms of service, and support documentation. "
            "Use for any question answerable by company documentation. "
            "Do NOT use for weather or reminder requests."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language question or keyword phrase",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_current_weather",
        "description": (
            "Get current weather conditions for a city or region. "
            "Use when the user asks about weather, temperature, or conditions. "
            "Do NOT use for document retrieval or reminders."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or region",
                }
            },
            "required": ["location"],
        },
    },
    {
        "name": "save_reminder",
        "description": (
            "Save a reminder with description and time. "
            "Use when the user asks to be reminded of something. "
            "Do NOT use for document retrieval or weather queries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "time": {"type": "string"},
            },
            "required": ["text", "time"],
        },
    },
]

SYSTEM_PROMPT = """You are a research assistant with access to tools.
Answer the user's question using available tools, then synthesize a response.

## Tool Failure Protocol

TIER 1 — CORE (search_documents):
If search_documents returns {"error": true}, immediately stop.
Do not fabricate. Respond: "I was unable to complete this research task.
The document search tool is currently unavailable."

TIER 2 — SUPPLEMENTARY (get_current_weather):
If get_current_weather returns {"error": true}, note limitation and continue.

TIER 3 — WRITE (save_reminder):
If save_reminder returns {"error": true}, complete task normally, note briefly.

Never present information as retrieved if it was not."""

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------
AgentStepType = Literal[
    "planning", "tool_call", "tool_result",
    "synthesizing", "complete", "loop_limit", "error"
]


class AgentStep(TypedDict, total=False):
    type: AgentStepType
    toolName: Optional[str]
    toolInput: Optional[dict]
    toolResult: Optional[dict]
    text: Optional[str]
    loopIndex: Optional[int]
    maxLoops: Optional[int]
    durationMs: Optional[int]


class AgentResult(TypedDict):
    steps: list[AgentStep]
    finalResponse: str
    loopsUsed: int
    maxLoops: int
    terminatedEarly: bool


# ---------------------------------------------------------------------------
# Tool executor — calls registry, never raises
# ---------------------------------------------------------------------------
def execute_tool(name: str, tool_input: dict) -> dict:
    if name not in TOOL_REGISTRY:
        return {
            "error": True,
            "message": f"Unknown tool: {name}",
        }
    try:
        return TOOL_REGISTRY[name](tool_input)
    except Exception as e:
        return {"error": True, "message": str(e)}


# ---------------------------------------------------------------------------
# ReAct loop
# ---------------------------------------------------------------------------
def run_agent(user_query: str, max_loops: int = MAX_AGENT_LOOPS) -> AgentResult:
    steps: list[AgentStep] = []
    messages = [{"role": "user", "content": user_query}]
    loops_used = 0
    terminated_early = False
    final_response = ""

    # Planning step
    steps.append({"type": "planning", "text": user_query})

    while loops_used < max_loops:
        loops_used += 1

        # Synthesizing indicator after first tool call
        has_tool_calls = any(s["type"] == "tool_call" for s in steps)
        if has_tool_calls:
            steps.append({
                "type": "synthesizing",
                "loopIndex": loops_used,
                "maxLoops": max_loops,
            })

        # Call Claude
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=AGENT_TOOLS,
            messages=messages,
        )

        # Add assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        # Case 1: done
        if response.stop_reason == "end_turn":
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            final_response = text
            steps.append({
                "type": "complete",
                "text": final_response,
                "loopIndex": loops_used,
            })
            break

        # Case 2: tool calls
        if response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                steps.append({
                    "type": "tool_call",
                    "toolName": block.name,
                    "toolInput": block.input,
                    "loopIndex": loops_used,
                })

                result = execute_tool(block.name, block.input)

                steps.append({
                    "type": "tool_result",
                    "toolName": block.name,
                    "toolResult": result,
                    "loopIndex": loops_used,
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

            messages.append({"role": "user", "content": tool_results})
            continue

        # Case 3: unexpected stop reason
        text = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
        final_response = text
        steps.append({"type": "complete", "text": final_response})
        break

    # Loop limit
    if loops_used >= max_loops and not final_response:
        terminated_early = True
        tool_results_text = "\n".join(
            json.dumps(s.get("toolResult", {}))
            for s in steps
            if s["type"] == "tool_result"
        )
        final_response = (
            f"Unable to complete within {max_loops} steps. "
            f"Partial results: {tool_results_text}"
        )
        steps.append({
            "type": "loop_limit",
            "text": final_response,
            "loopIndex": loops_used,
            "maxLoops": max_loops,
        })

    return {
        "steps": steps,
        "finalResponse": final_response,
        "loopsUsed": loops_used,
        "maxLoops": max_loops,
        "terminatedEarly": terminated_early,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or "What is the refund policy?"
    print(f"\nQuery: {query}\n")
    result = run_agent(query)
    print(f"Loops used: {result['loopsUsed']}/{result['maxLoops']}")
    print(f"Steps: {len(result['steps'])}")
    print(f"\nResponse:\n{result['finalResponse']}")
