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
 
Week 4 update: make_call_messages() now accepts an optional tools= parameter.
_call_anthropic_messages() passes tools to the Anthropic API and returns the
full response object (not wrapped in _Response) so tool_use blocks are
preserved. _call_ollama_messages() ignores tools — Ollama does not support
the Anthropic tool use protocol.
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
class _Response:
    """
    Minimal response wrapper — mirrors the Anthropic SDK shape.
 
    Week 4 addition: content is now a list of blocks. Each block has a type
    attribute. Text blocks have .text. Tool use blocks have .type == 'tool_use',
    .name, .input, and .id. This mirrors the real Anthropic SDK exactly so
    chatbot.py can iterate response.content without branching on ENVIRONMENT.
    """
 
    def __init__(self, text: str, input_tokens: int, output_tokens: int):
        self.content = [_TextBlock(text)]
        self.stop_reason = "end_turn"
        self.usage = type(
            "Usage",
            (),
            {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        )()
 
 
class _TextBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text
 
 
# ─── Public API ───────────────────────────────────────────────────────────────
 
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
    max_tokens: int = 1024,
    tools: list[dict] | None = None,
):
    """
    Multi-turn variant of make_call().
    Takes a full messages[] array instead of a single user_message string.
 
    When tools is provided and ENVIRONMENT == 'production', returns the raw
    Anthropic SDK response object so tool_use content blocks are preserved.
    When tools is None or ENVIRONMENT == 'local', returns _Response as before.
 
    Alex Chen: "The tool loop in chatbot.py calls response.content and
    response.stop_reason — both exist on the real SDK object and on _Response.
    The contract holds either way."
    """
    if ENVIRONMENT == "local":
        # Ollama does not support Anthropic-style tool use.
        # Tool calls will not be exercised in local mode — use prod for tool testing.
        return _call_ollama_messages(messages, system, temperature, max_tokens)
    return _call_anthropic_messages(messages, system, temperature, max_tokens, tools)
 
 
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
 
 
# ─── Internal implementations ─────────────────────────────────────────────────
 
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
    tools: list[dict] | None = None,
):
    """
    Returns the raw Anthropic SDK response when tools are present so that
    tool_use content blocks are accessible to the caller. Returns _Response
    when tools is None (backward compatible with all Week 1-3 callers).
    """
    import anthropic
 
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. In prod this must come from Secret Manager."
        )
    client = anthropic.Anthropic(api_key=api_key)
    kwargs: dict = dict(
        model=MODEL_STRING,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
 
    resp = client.messages.create(**kwargs)
 
    # With tools: return raw SDK response — content blocks may include tool_use
    if tools:
        return resp
 
    # Without tools: return _Response for backward compatibility
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
    Production mode: exact count via Anthropic SDK.
 
    Alex Chen: "Use this to gate on TOKEN_BUDGET_WARNING before every
    send. Never let the context window fill up silently."
    """
    if ENVIRONMENT == "local":
        total_chars = sum(len(m["content"]) for m in messages if isinstance(m.get("content"), str))
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
    kwargs: dict = dict(model=MODEL_STRING, messages=messages)
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