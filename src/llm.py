"""Thin wrapper around the Anthropic SDK.

Two call shapes cover every agent in the system:
  - complete_text:       streamed free-text generation (Interviewer, Coach, Simulator)
  - complete_structured: schema-validated JSON via structured outputs (Planner, Evaluator)
"""

from typing import Callable, Optional, Type, TypeVar

import anthropic
from pydantic import BaseModel

from .config import MODEL

T = TypeVar("T", bound=BaseModel)

_client: Optional[anthropic.Anthropic] = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        import os

        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            raise MissingAPIKeyError
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client


class MissingAPIKeyError(RuntimeError):
    pass


def complete_text(
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
    on_text: Optional[Callable[[str], None]] = None,
    use_thinking: bool = False,
) -> str:
    """Stream a text completion. Calls on_text with each chunk if provided."""
    kwargs: dict = {}
    if use_thinking:
        kwargs["thinking"] = {"type": "adaptive"}
    with client().messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        # cache_control on the system block: the per-agent system prompt is
        # byte-stable across turns, so multi-turn agents (Interviewer) reuse it.
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
        **kwargs,
    ) as stream:
        for chunk in stream.text_stream:
            if on_text:
                on_text(chunk)
        final = stream.get_final_message()
    return "".join(block.text for block in final.content if block.type == "text")


def complete_structured(
    system: str,
    user_content: str,
    output_model: Type[T],
    max_tokens: int = 2048,
) -> T:
    """Single-shot call that returns a validated instance of output_model."""
    response = client().messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
        output_format=output_model,
    )
    if response.parsed_output is None:
        raise RuntimeError(
            f"Model returned no parseable {output_model.__name__} "
            f"(stop_reason={response.stop_reason})"
        )
    return response.parsed_output


def friendly_api_error(exc: Exception) -> str:
    """Map SDK exceptions to actionable messages for the CLI."""
    if isinstance(exc, MissingAPIKeyError):
        return (
            "No API key found. Set ANTHROPIC_API_KEY in your shell or in a .env file "
            "(see .env.example), then re-run."
        )
    if isinstance(exc, anthropic.AuthenticationError):
        return "Authentication failed. Set ANTHROPIC_API_KEY (see README → Setup)."
    if isinstance(exc, anthropic.RateLimitError):
        return "Rate limited by the API. Wait a minute and try again."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Could not reach the Anthropic API. Check your internet connection."
    if isinstance(exc, anthropic.APIStatusError):
        return f"API error {exc.status_code}: {exc.message}"
    return f"Unexpected error: {exc}"
