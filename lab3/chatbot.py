"""
chatbot.py — Stateful CLI chatbot with streaming, summarization, and cost tracking.

Sam Park: "This is the consumer of everything built this week.
It never touches a client directly. Every external call goes through
config.py. Every state change goes through MessageHistory."

Alex Chen: "The main loop is deliberately thin. Business logic lives
in the supporting classes. If this file grows beyond ~100 lines,
something that belongs in a class has leaked into the loop."
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import make_stream_call, count_tokens
from lab3.message_history import MessageHistory
from lab3.summarizer import summarize
from lab3.token_tracker import TokenTracker

# ─── Constants ────────────────────────────────────────────────────────────────
TOKEN_BUDGET_WARNING: int = 1500   # soft warn — suggest /summarize
TOKEN_BUDGET_HARD: int = 3000      # hard limit — auto-summarize

SYSTEM_PROMPT = """You are a helpful, concise assistant.
You have access to a conversation history.
When the history contains a [Conversation summary] block, treat it as accurate context.
Never repeat information the user has already provided.
If asked to perform a task you cannot complete, say so explicitly."""


# ─── Warmup ───────────────────────────────────────────────────────────────────
def _warmup() -> None:
    """
    Fire one throwaway call to load the model into memory.
    Sam Park: "Cold start is 10-15x slower than warm inference.
    Always drain it before the user sees the first prompt."
    """
    print("Warming up...", end="", flush=True)
    for _ in make_stream_call(
        [{"role": "user", "content": "hi"}],
        system="",
        max_tokens=8,
    ):
        pass
    print(" ready\n")


# ─── Stream one response ──────────────────────────────────────────────────────
def _stream_response(
    history: MessageHistory,
    tracker: TokenTracker,
) -> str:
    """
    Stream the next assistant response.
    Measures first-token latency and total time.
    Returns the fully assembled response string.
    """
    messages = history.get_messages()

    # Approximate input tokens — exact in GCP, estimate locally
    input_tokens = count_tokens(messages, system=SYSTEM_PROMPT)

    chunks = []
    first_token_ms = None
    start = time.time()

    for chunk in make_stream_call(
        messages,
        system=SYSTEM_PROMPT,
        temperature=0.7,
        max_tokens=512,
    ):
        if first_token_ms is None:
            first_token_ms = (time.time() - start) * 1000
        print(chunk, end="", flush=True)
        chunks.append(chunk)

    print()  # newline after stream ends
    total_ms = (time.time() - start) * 1000

    full_response = "".join(chunks)

    # Approximate output tokens
    output_tokens = len(full_response) // 3

    log = tracker.log_turn(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        first_token_ms=first_token_ms,
        total_ms=total_ms,
        call_type="chat",
    )

    # Jordan's gate: warn if first-token exceeds 500ms
    if first_token_ms and first_token_ms > 500:
        print(f"⚠️  First-token latency: {first_token_ms:.0f}ms (gate: 500ms)")

    tracker.print_turn_summary(log)
    return full_response


# ─── Handle /summarize ────────────────────────────────────────────────────────
def _do_summarize(
    history: MessageHistory,
    tracker: TokenTracker,
) -> None:
    """
    Compress history and replace it with a summary + recent turns.
    Jordan Rivera: "After every /summarize, note the token count
    before and after. If reduction is less than 50%, the conversation
    was too short to summarize — not a bug, just timing."
    """
    tokens_before = count_tokens(history.get_messages(), system=SYSTEM_PROMPT)
    print(f"Summarizing {len(history)} messages (~{tokens_before} tokens)...")

    summary_text, in_tok, out_tok = summarize(history.get_messages(), tracker)
    history.replace_with_summary(summary_text)

    tokens_after = count_tokens(history.get_messages(), system=SYSTEM_PROMPT)
    reduction = round((1 - tokens_after / tokens_before) * 100) if tokens_before else 0

    print(f"✓ Compressed to {len(history)} messages (~{tokens_after} tokens) — {reduction}% reduction")
    print(f"  Summary: {summary_text[:120]}{'...' if len(summary_text) > 120 else ''}\n")


# ─── Main loop ────────────────────────────────────────────────────────────────
def main() -> None:
    history = MessageHistory()
    tracker = TokenTracker(log_dir="lab3/results")

    _warmup()

    print("Chatbot ready.")
    print("Commands: /summarize  /cost  /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        # ── Commands ──
        if user_input == "/quit":
            break

        if user_input == "/cost":
            tracker.print_session_summary()
            continue

        if user_input == "/summarize":
            if len(history) < 4:
                print("Not enough history to summarize yet.\n")
                continue
            _do_summarize(history, tracker)
            continue

        # ── Token budget check ──
        current_tokens = count_tokens(history.get_messages(), system=SYSTEM_PROMPT)
        if current_tokens >= TOKEN_BUDGET_HARD:
            print(f"⚠️  Context at {current_tokens} tokens — auto-summarizing...\n")
            _do_summarize(history, tracker)
        elif current_tokens >= TOKEN_BUDGET_WARNING:
            print(f"⚠️  Context: ~{current_tokens} tokens. Consider /summarize\n")

        # ── Normal turn ──
        history.add_user(user_input)
        response = _stream_response(history, tracker)
        history.add_assistant(response)

    tracker.print_session_summary()


if __name__ == "__main__":
    main()