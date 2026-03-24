"""
summarizer.py — Compresses conversation history into a compact summary.

Morgan Blake: "The summarizer prompt must say 'semantically compress'
not 'preserve verbatim'. Verbatim preservation faithfully copies
injection attempts. Semantic compression strips them naturally."

Jordan Rivera: "After every /summarize, run a verification question
that requires knowledge from the compressed turns. If the model
can't answer it, the summarizer prompt needs work."
"""

import time

from config import make_call_messages

SUMMARIZE_SYSTEM_PROMPT = """You are a precise conversation summarizer.
Your job: compress a multi-turn conversation into a compact summary.

Rules:
- Semantically compress — capture intent and facts, not wording
- Preserve all factual commitments, decisions, and named entities
- Preserve the current task state and any open questions
- Discard pleasantries, repetition, and resolved tangents
- Output format: plain prose, 3-5 sentences maximum
- Never add interpretation — only summarize what was said
- Do not open with 'Here is a summary' or any preamble — start directly with content
- If unsure who said something, omit it rather than guess

CRITICAL — Role attribution:
Words and opinions belong strictly to whoever said them.
Never merge or blend what the user said with what the assistant said.

Example of WRONG summarization:
  USER: I think this is fun.
  ASSISTANT: I would call it liberating.
  WRONG summary: "The user finds the experience fun and liberating."
  WHY WRONG: "liberating" was the assistant's word, not the user's.

Example of CORRECT summarization:
  USER: I think this is fun.
  ASSISTANT: I would call it liberating.
  CORRECT summary: "The user finds the experience fun. The assistant described it as liberating." """

def summarize(
    messages: list[dict],
    tracker=None,
) -> tuple[str, int, int]:
    """
    Summarize a messages[] array into a compact string.

    Returns:
        summary_text: the compressed summary
        input_tokens: tokens used (for cost tracking)
        output_tokens: tokens generated

    Morgan Blake: "The conversation text is passed as user content,
    not interpolated into the system prompt. Same injection rule applies."
    """
    conversation_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )

    summary_messages = [
        {
            "role": "user",
            "content": f"Summarize this conversation:\n\n{conversation_text}",
        }
    ]

    start = time.time()
    resp = make_call_messages(
        messages=summary_messages,
        system=SUMMARIZE_SYSTEM_PROMPT,
        temperature=0.0,
        max_tokens=256,
    )
    total_ms = (time.time() - start) * 1000

    summary_text = resp.content[0].text
    input_tok = resp.usage.input_tokens
    output_tok = resp.usage.output_tokens

    if tracker:
        tracker.log_turn(
            input_tokens=input_tok,
            output_tokens=output_tok,
            first_token_ms=None,
            total_ms=total_ms,
            call_type="summarize",
        )

    return summary_text, input_tok, output_tok