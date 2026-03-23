"""
config.py — The architectural contract for the entire course.

Alex Chen: "This file is not a convenience. It is the seam between
local development (zero cost) and production (real models, real cost).
Nothing outside this file should know which model is running."

Morgan Blake: "No API keys here. Ever. They come from the environment,
which in prod is Secret Manager, not .env files."

BUG FIX (Week 1): Original returned an openai.OpenAI client in local mode,
which has a different interface (.chat.completions) than the Anthropic client
(.messages). We now wrap both behind a unified make_call() helper so lab code
never touches the client directly — the architectural contract is preserved.
"""

import os
from typing import Final, Generator

# ─── Environment switch ───────────────────────────────────────────────────────
ENVIRONMENT: Final[str] = os.getenv("ENVIRONMENT", "local")

# ─── Model strings — always version-pinned ────────────────────────────────────
LOCAL_MODEL: Final[str] = "llama3.2"
PROD_MODEL: Final[str] = "claude-sonnet-4-6"

MODEL_STRING: Final[str] = LOCAL_MODEL if ENVIRONMENT == "local" else PROD_MODEL

# ─── Embedding model strings ──────────────────────────────────────────────────
LOCAL_EMBED: Final[str] = "nomic-embed-text"
PROD_EMBED: Final[str] = "text-embedding-3-large"

EMBED_MODEL: Final[str] = LOCAL_EMBED if ENVIRONMENT == "local" else PROD_EMBED

# ─── API base URLs ────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: Final[str] = "http://localhost:11434"


# ─── Unified response shape ───────────────────────────────────────────────────
# Alex Chen: "Both backends return different objects. We normalize here so
# nothing outside config.py ever branches on ENVIRONMENT."
class _Response:
    """Minimal response wrapper — mirrors the Anthropic SDK shape."""

    def __init__(self, text: str, input_tokens: int, output_tokens: int):
        self.content = [type("Block", (), {"text": text})()]
        self.usage = type(
            "Usage",
            (),
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )()


def make_call(
    system_prompt: str,
    user_message: str,
    temperature: float,
    max_tokens: int = 512,
) -> _Response:
    """
    Single entry point for all LLM calls in this course.

    Morgan Blake: "user_message is always kept separate from system_prompt.
    They are never concatenated. This is the first injection defense."

    Sam Park: "Call this instead of touching the client directly. Local hits
    Ollama; prod hits Anthropic. Same return shape either way."
    """
    if ENVIRONMENT == "local":
        return _call_ollama(system_prompt, user_message, temperature, max_tokens)
    return _call_anthropic(system_prompt, user_message, temperature, max_tokens)

def make_call_messages(
    messages: list[dict],
    system: str = "",
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> _Response:
    """
    Multi-turn variant of make_call().
    Takes a full messages[] array instead of a single user_message string.
    Used for: /summarize, any multi-turn non-streaming call.

    Alex Chen: "Same return shape as make_call(). Callers never branch on
    which variant they used — _Response is _Response."
    """
    if ENVIRONMENT == "local":
        return _call_ollama_messages(messages, system, temperature, max_tokens)
    return _call_anthropic_messages(messages, system, temperature, max_tokens)

def make_stream_call(
    messages: list[dict],
    system: str = "",
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> Generator[str, None, None]:
    """
    Streaming variant of make_call_messages().
    Yields text chunks as they arrive from the model.

    Sam Park: "flush=True on every print() that consumes this.
    Without it Python buffers stdout and you get the whole
    response at once — identical to non-streaming UX."

    Jordan Rivera: "Measure first-token latency at the call site,
    not inside this function. This function yields — the caller
    controls timing."
    """
    if ENVIRONMENT == "local":
        yield from _stream_ollama(messages, system, temperature, max_tokens)
    else:
        yield from _stream_anthropic(messages, system, temperature, max_tokens)

def _stream_ollama(
    messages: list[dict],
    system: str,
    temperature: float,
    max_tokens: int,
) -> Generator[str, None, None]:
    import openai

    client = openai.OpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",
    )
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    stream = client.chat.completions.create(
        model=MODEL_STRING,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=full_messages,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def _stream_anthropic(
    messages: list[dict],
    system: str,
    temperature: float,
    max_tokens: int,
) -> Generator[str, None, None]:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. In prod this must come from Secret Manager."
        )
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = dict(
        model=MODEL_STRING,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    if system:
        kwargs["system"] = system

    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield text

def _call_ollama(
    system_prompt: str,
    user_message: str,
    temperature: float,
    max_tokens: int,
) -> _Response:
    import openai

    client = openai.OpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",
    )
    resp = client.chat.completions.create(
        model=MODEL_STRING,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    text = resp.choices[0].message.content
    in_tok = getattr(resp.usage, "prompt_tokens", 0) or 0
    out_tok = getattr(resp.usage, "completion_tokens", 0) or 0
    return _Response(text, in_tok, out_tok)

def _call_ollama_messages(
    messages: list[dict],
    system: str,
    temperature: float,
    max_tokens: int,
) -> _Response:
    import openai

    client = openai.OpenAI(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",
    )
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    resp = client.chat.completions.create(
        model=MODEL_STRING,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=full_messages,
    )
    text = resp.choices[0].message.content
    in_tok = getattr(resp.usage, "prompt_tokens", 0) or 0
    out_tok = getattr(resp.usage, "completion_tokens", 0) or 0
    return _Response(text, in_tok, out_tok)

def _call_anthropic(
    system_prompt: str,
    user_message: str,
    temperature: float,
    max_tokens: int,
) -> _Response:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. In prod this must come from Secret Manager."
        )
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=MODEL_STRING,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return _Response(
        resp.content[0].text,
        resp.usage.input_tokens,
        resp.usage.output_tokens,
    )

def _call_anthropic_messages(
    messages: list[dict],
    system: str,
    temperature: float,
    max_tokens: int,
) -> _Response:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. In prod this must come from Secret Manager."
        )
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = dict(
        model=MODEL_STRING,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    if system:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    return _Response(
        resp.content[0].text,
        resp.usage.input_tokens,
        resp.usage.output_tokens,
    )

def count_tokens(
    messages: list[dict],
    system: str = "",
) -> int:
    """
    Returns input token count for a messages array without making
    a full inference call.

    Local mode: approximation only — Ollama has no count_tokens endpoint.
    GCP mode: exact count via Anthropic SDK.

    Alex Chen: "Use this to gate on TOKEN_BUDGET_WARNING before every
    send. Never let the context window fill up silently."
    """
    if ENVIRONMENT == "local":
        # Local approximation: ~3 characters per token.
        # Undercounts by ~30-50% on short conversational messages.
        # Acceptable for warning thresholds in local dev.
        # GCP mode returns exact counts via Anthropic SDK.
        # Taylor Nguyen (Week 6): treat local token counts as estimates only.
        total_chars = sum(len(m["content"]) for m in messages)
        if system:
            total_chars += len(system)
        return total_chars // 3

    import anthropic
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. In prod this must come from Secret Manager."
        )
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = dict(model=MODEL_STRING, messages=messages)
    if system:
        kwargs["system"] = system

    result = client.messages.count_tokens(**kwargs)
    return result.input_tokens
# ─── Quick verification ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"ENVIRONMENT:  {ENVIRONMENT}")
    print(f"MODEL_STRING: {MODEL_STRING}")
    print(f"EMBED_MODEL:  {EMBED_MODEL}")
    target = "Ollama (local, $0)" if ENVIRONMENT == "local" else "Anthropic API (prod, costs money)"
    print(f"Config OK — routing to {target}")
