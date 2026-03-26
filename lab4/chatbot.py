"""
lab4/chatbot.py

Week 4 chatbot — Week 3 shell + tool use loop.

What changed from Week 3:
  - run_tool_loop() wraps every API call — handles tool_use stop_reason
  - get_tool_schemas() from registry feeds the tools= parameter
  - dispatch() from registry executes tool calls
  - /reminders command shows reminders created this session
  - System prompt updated to describe available tools

What did NOT change:
  - MessageHistory  — untouched import from lab3
  - TokenTracker    — untouched import from lab3
  - Summarizer      — untouched import from lab3
  - config.py       — untouched, ENVIRONMENT switch still governs model
  - Streaming       — still used for final text responses
  - /summarize      — still works as before

Alex's note: this is what clean architecture buys you. Three weeks of
prior work are reused without modification. New capability layers on top.
"""

from __future__ import annotations

import sys
from pathlib import Path

# --- resolve imports whether running as script or module ---
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from lab3.message_history import MessageHistory
from lab3.token_tracker import TokenTracker
from lab3.summarizer import summarize
from lab4.tools.registry import get_tool_schemas, dispatch
from lab4.tools.reminder import get_all_reminders


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a helpful assistant with access to three tools:

1. get_weather(location) — get current weather for any city
2. create_reminder(text, time) — create a reminder at a specific time
3. search_docs(query) — search the internal knowledge base

Use tools when the user's request clearly calls for real-time data,
reminder creation, or document lookup. For general conversation,
reasoning, and questions you can answer from your own knowledge,
respond directly without calling a tool.

When search_docs returns results, ground your answer in the retrieved
content and mention the source document. If the results don't answer
the question, say so — do not fabricate information.

If a tool returns an error, acknowledge it clearly and offer to help
another way. Never silently ignore a tool error."""


# ---------------------------------------------------------------------------
# Tool execution loop
# ---------------------------------------------------------------------------

def run_tool_loop(messages: list[dict], tracker: TokenTracker) -> str:
    """
    Run the full tool execution loop for one user turn.

    Calls the API repeatedly until stop_reason == "end_turn".
    Handles multiple tool calls per response (model can request > 1 tool).

    Args:
        messages:  Full conversation history (will be mutated in place).
        tracker:   TokenTracker to record each API call.

    Returns:
        Final text response from the model.
    """
    while True:
        response = config.make_call_messages(
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=get_tool_schemas(),
        )

        # Record token usage for this call
        tracker.log_turn(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            first_token_ms=None,
            total_ms=0.0,
        )

        # ── Done — extract final text ────────────────────────────────────
        if response.stop_reason == "end_turn":
            return _extract_text(response)

        # ── Tool use — execute and loop ──────────────────────────────────
        if response.stop_reason == "tool_use":
            # Append the assistant's tool_use block to history
            messages.append({
                "role": "assistant",
                "content": response.content,
            })

            # Execute every tool call in this response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n  [tool] {block.name}({block.input})")
                    result_json = dispatch(block.name, block.input)
                    print(f"  [tool] → {result_json[:120]}{'...' if len(result_json) > 120 else ''}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_json,
                    })

            # Append all tool results as a single user turn
            messages.append({
                "role": "user",
                "content": tool_results,
            })
            # Loop — model now sees results and continues

        else:
            # Unexpected stop_reason — return whatever text exists
            return _extract_text(response)


def _extract_text(response) -> str:
    """Extract the text content from a response object."""
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return ""


# ---------------------------------------------------------------------------
# Streaming wrapper for final responses
# ---------------------------------------------------------------------------

def stream_response(text: str) -> None:
    """Print response text with a simulated stream feel."""
    # In a full streaming implementation this would use make_stream_call().
    # For the tool loop, we use make_call_messages() (non-streaming) because
    # streaming and tool use require careful interleaving. Week 5 addresses
    # this when we move to the web frontend with SSE.
    print(f"\nAssistant: {text}\n")


# ---------------------------------------------------------------------------
# Main chat loop
# ---------------------------------------------------------------------------

def main() -> None:
    history = MessageHistory()
    tracker = TokenTracker()

    print("Week 4 Chatbot — Tools: weather · reminders · search_docs")
    print("Commands: /summarize  /reminders  /tokens  /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        # ── Slash commands ───────────────────────────────────────────────
        if user_input == "/quit":
            print("Goodbye.")
            break

        if user_input == "/tokens":
            tracker.print_session_summary()
            continue

        if user_input == "/summarize":
            messages = history.get_messages()
            if len(messages) < 4:
                print("Not enough history to summarise yet.\n")
                continue
            summary = summarize(messages)
            history.replace_with_summary(summary)
            print(f"\n[Summarized {len(messages)} messages → 1 summary block]\n")
            continue

        if user_input == "/reminders":
            reminders = get_all_reminders()
            if not reminders:
                print("\nNo reminders created this session.\n")
            else:
                print(f"\nReminders ({len(reminders)}):")
                for r in reminders:
                    print(f"  [{r['id']}] {r['time']} — {r['text']}")
                print()
            continue

        # ── Normal turn ──────────────────────────────────────────────────
        history.add_user(user_input)
        messages = history.get_messages()

        # Summarize if approaching token budget
        if tracker.session_input_tokens > 15_000:
            summary = summarize(messages)
            history.replace_with_summary(summary)
            messages = history.get_messages()

        try:
            response_text = run_tool_loop(messages, tracker)
        except Exception as exc:  # noqa: BLE001
            print(f"\n[Error] {exc}\n")
            history.messages.pop()  # remove the failed user turn
            continue

        history.add_assistant(response_text)
        stream_response(response_text)


if __name__ == "__main__":
    main()
