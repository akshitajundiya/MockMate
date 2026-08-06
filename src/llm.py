"""Thin wrapper around the Google Gen AI SDK (Gemini Interactions API).

Two call shapes cover every agent in the system:
  - stream_turn:         streamed generation; returns (text, interaction_id) so
                         multi-turn agents chain via previous_interaction_id
  - complete_structured: schema-validated JSON via response_format (Planner, Evaluator)

Three Gemini-specific details drive the shape of this module:

1. `max_output_tokens` is a *combined* budget for thinking tokens plus visible
   output on Gemini 3 models, and `thinking_level` defaults to "high". Budgets
   here are therefore generous, and agents that don't need deliberation ask for
   "low" explicitly.
2. Conversation state lives server-side: `previous_interaction_id` chains turns
   instead of us replaying the history. The id arrives on the terminal
   `interaction.completed` stream event.
3. The stream carries several delta kinds (`text`, `thought_summary`, tool calls…);
   only `text` deltas are the candidate-visible answer.
"""

from typing import Callable, Optional, Type, TypeVar

from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError

from .config import MODEL

T = TypeVar("T", bound=BaseModel)

_client: Optional[genai.Client] = None


class MissingAPIKeyError(RuntimeError):
    pass


def client() -> genai.Client:
    global _client
    if _client is None:
        try:
            _client = genai.Client()  # reads GEMINI_API_KEY from the environment
        except Exception as exc:
            raise MissingAPIKeyError from exc
    return _client


def _generation_config(max_tokens: int, thinking: str) -> dict:
    return {"max_output_tokens": max_tokens, "thinking_level": thinking}


def stream_turn(
    system: str,
    user_content: str,
    max_tokens: int,
    thinking: str = "low",
    previous_id: Optional[str] = None,
    on_text: Optional[Callable[[str], None]] = None,
) -> tuple[str, Optional[str]]:
    """Stream one turn. Returns (text, interaction_id).

    Pass the returned id back as `previous_id` next turn to keep the history.
    `on_text` receives each chunk as it arrives.
    """
    kwargs = {}
    if previous_id:
        kwargs["previous_interaction_id"] = previous_id

    stream = client().interactions.create(
        model=MODEL,
        system_instruction=system,
        input=user_content,
        generation_config=_generation_config(max_tokens, thinking),
        stream=True,
        **kwargs,
    )

    pieces: list[str] = []
    interaction_id: Optional[str] = None

    for event in stream:
        event_type = getattr(event, "event_type", None)

        if event_type == "interaction.completed":
            interaction = getattr(event, "interaction", None)
            interaction_id = getattr(interaction, "id", None)
            continue

        if event_type != "step.delta":
            continue

        delta = getattr(event, "delta", None)
        # Skip thought summaries and tool-call deltas — only visible text counts.
        if delta is None or getattr(delta, "type", None) != "text":
            continue

        piece = getattr(delta, "text", "") or ""
        if not piece:
            continue
        pieces.append(piece)
        if on_text:
            on_text(piece)

    return "".join(pieces).strip(), interaction_id


def complete_structured(
    system: str,
    user_content: str,
    output_model: Type[T],
    max_tokens: int = 4096,
    thinking: str = "low",
) -> T:
    """Single-shot call that returns a validated instance of output_model."""
    interaction = client().interactions.create(
        model=MODEL,
        system_instruction=system,
        input=user_content,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": _inline_refs(output_model.model_json_schema()),
        },
        generation_config=_generation_config(max_tokens, thinking),
    )
    raw = (interaction.output_text or "").strip()
    if not raw:
        raise RuntimeError(
            f"Model returned an empty response instead of {output_model.__name__}. "
            "This usually means the token budget was exhausted by thinking — retry, "
            "or raise the budget in src/config.py."
        )
    try:
        return output_model.model_validate_json(raw)
    except ValidationError as exc:
        raise RuntimeError(
            f"Model returned JSON that does not match {output_model.__name__}: {exc}"
        ) from exc


def _inline_refs(schema: dict) -> dict:
    """Resolve $ref/$defs into one self-contained schema.

    Pydantic emits nested models ($defs + $ref); inlining them keeps the schema
    portable across providers that don't dereference. Assumes no recursive
    models — none of ours are.
    """
    defs = dict(schema.pop("$defs", {}))

    def resolve(node):
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                target = defs[ref.rsplit("/", 1)[-1]]
                overrides = {k: v for k, v in node.items() if k != "$ref"}
                return resolve({**target, **overrides})
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(schema)


def friendly_api_error(exc: Exception) -> str:
    """Map SDK exceptions to actionable messages for the CLI."""
    if isinstance(exc, MissingAPIKeyError):
        return (
            "No API key found. Set GEMINI_API_KEY in your shell or in a .env file "
            "(see .env.example), then re-run."
        )
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)
        message = getattr(exc, "message", str(exc))
        if code in (401, 403):
            return "Authentication failed. Check GEMINI_API_KEY (see README → Setup)."
        if code == 429:
            return "Rate limited or out of quota. Wait a minute and try again."
        if code == 404:
            return (
                f"Model '{MODEL}' was not found for this key. Set GEMINI_MODEL in .env "
                "to a model your account can access."
            )
        if code == 400:
            return f"Bad request: {message}"
        if isinstance(code, int) and code >= 500:
            return f"Gemini service error ({code}). Wait a moment and try again."
        return f"API error {code}: {message}"
    return f"Unexpected error: {exc}"
