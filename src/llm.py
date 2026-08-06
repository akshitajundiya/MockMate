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

import re
import time
from typing import Callable, Optional, Type, TypeVar

import httpx
from google import genai
from pydantic import BaseModel, ValidationError

from .config import MAX_RETRIES, MODEL

T = TypeVar("T", bound=BaseModel)

_client: Optional[genai.Client] = None

# The CLI registers a callback here so waits are visible instead of looking like a hang.
_retry_notifier: Optional[Callable[[float, Optional[int]], None]] = None

_RETRY_HINT = re.compile(r"retry in ([0-9.]+)s")

# Networking failures surface from several layers (httpx, its httpcore backend,
# raw sockets, TLS), and streaming can leak the lower-level ones straight
# through, so match on origin rather than on one library's exception tree.
_TRANSPORT_MODULES = frozenset({"httpx", "httpcore", "ssl", "socket", "anyio", "h11", "h2"})

# Last resort: the SDK can wrap a socket failure in its own error class, which
# hides both the type and the module. The wording still gives it away.
_TRANSPORT_TEXT = re.compile(
    r"winerror 100(53|54|60)|connection (aborted|reset|refused|closed)"
    r"|server disconnected|remote end closed|timed out|broken pipe",
    re.IGNORECASE,
)


def _is_transport_error(exc: BaseException) -> bool:
    """True for dropped connections, timeouts and TLS faults — not for our own bugs.

    Walks the __cause__/__context__ chain, because the SDK re-raises the
    interesting failure wrapped inside its own exception type.
    """
    seen: set[int] = set()
    current: Optional[BaseException] = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        # OSError covers the socket family, including WinError 10053
        # ("connection aborted by the software in your host machine").
        if isinstance(current, (OSError, TimeoutError)):
            return True
        if type(current).__module__.split(".")[0] in _TRANSPORT_MODULES:
            return True
        if _TRANSPORT_TEXT.search(str(current)):
            return True
        current = current.__cause__ or current.__context__
    return False


def set_retry_notifier(fn: Optional[Callable[[float, Optional[int]], None]]) -> None:
    global _retry_notifier
    _retry_notifier = fn


def _status_code(exc: Exception) -> Optional[int]:
    """HTTP status from an SDK exception, whichever attribute it uses.

    The Interactions API raises GenAiError (`.status_code`) while the older
    surface raises APIError (`.code`), so match on the value rather than on a
    class — the private module path behind GenAiError is not a stable contract.
    """
    for attr in ("status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Honour the server's own "please retry in Ns" hint when it gives one."""
    match = _RETRY_HINT.search(str(getattr(exc, "message", "")) or str(exc))
    if match:
        return min(float(match.group(1)) + 1.0, 90.0)
    return float(min(2 ** attempt, 60))


def _call_with_retry(fn: Callable[[], object]) -> object:
    """Retry rate limits and transient server errors with backoff.

    A full session is ~23 requests, which comfortably exceeds a 20-per-minute
    free-tier allowance, so this is the difference between a session finishing
    and dying halfway through.
    """
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except Exception as exc:
            code = _status_code(exc)
            # Transport failures are checked regardless of status code: the SDK
            # sometimes wraps a dropped connection in an error object that
            # carries one, which would otherwise mask it. Bugs in our own code
            # have neither a retryable status nor a transport origin.
            retryable = (
                code == 429
                or (code is not None and code >= 500)
                or _is_transport_error(exc)
            )
            if code is None and retryable:
                code = None  # keep the notifier's "connection dropped" wording
            if not retryable or attempt == MAX_RETRIES - 1:
                raise
            delay = _retry_delay(exc, attempt)
            if _retry_notifier:
                _retry_notifier(delay, code)
            time.sleep(delay)
    raise RuntimeError("unreachable")  # pragma: no cover


class MissingAPIKeyError(RuntimeError):
    pass


class StreamError(RuntimeError):
    """An error the API reported as a stream event rather than raising.

    Carries `status_code` so it flows through the same retry/friendly-message
    path as a normal API failure.
    """

    def __init__(self, message: str, code: object = None):
        super().__init__(message)
        self.message = message
        # The event's code may be an int status or a slug like "too_many_requests".
        if isinstance(code, int):
            self.status_code = code
        elif isinstance(code, str) and code.isdigit():
            self.status_code = int(code)
        elif isinstance(code, str) and "too_many_requests" in code:
            self.status_code = 429
        else:
            self.status_code = None


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

    def once() -> tuple[str, Optional[str]]:
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

            # A failure mid-stream arrives as an event, not an exception. Left
            # unhandled it just ends the loop and looks like an empty answer.
            if event_type == "error":
                error = getattr(event, "error", None)
                raise StreamError(
                    getattr(error, "message", None) or "stream failed",
                    getattr(error, "code", None),
                )

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

    # The rate limit can surface either on create or mid-iteration, so the whole
    # consume loop is what gets retried.
    return _call_with_retry(once)


def complete_structured(
    system: str,
    user_content: str,
    output_model: Type[T],
    max_tokens: int = 4096,
    thinking: str = "low",
) -> T:
    """Single-shot call that returns a validated instance of output_model."""
    def once():
        return client().interactions.create(
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

    interaction = _call_with_retry(once)
    raw = (interaction.output_text or "").strip()
    if not raw:
        raise RuntimeError(
            f"Model returned an empty response instead of {output_model.__name__}. "
            "This usually means the token budget was exhausted by thinking — retry, "
            "or raise the budget in src/config.py."
        )
    raw = _strip_code_fence(raw)
    try:
        return output_model.model_validate_json(raw)
    except ValidationError as exc:
        if not raw.startswith(("{", "[")):
            # Not every model honours response_format — some just write prose.
            raise RuntimeError(
                f"Model '{MODEL}' ignored the JSON schema and returned prose instead "
                f"of {output_model.__name__}. Structured outputs need a Gemini 3.x "
                f"model — set GEMINI_MODEL in .env. Response began: {raw[:100]!r}"
            ) from exc
        raise RuntimeError(
            f"Model returned JSON that does not match {output_model.__name__}: {exc}"
        ) from exc


def _strip_code_fence(text: str) -> str:
    """Drop a ```json ... ``` wrapper if the model added one."""
    if not text.startswith("```"):
        return text
    body = text.split("\n", 1)[-1] if "\n" in text else ""
    if body.rstrip().endswith("```"):
        body = body.rstrip()[:-3]
    return body.strip()


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
    code = _status_code(exc)
    if code is not None:
        message = getattr(exc, "message", str(exc))
        if code in (401, 403):
            return "Authentication failed. Check GEMINI_API_KEY (see README, Setup)."
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
    if _is_transport_error(exc):
        return (
            f"The network connection kept failing ({type(exc).__name__}: {exc}). "
            "Check your connection — a VPN, proxy or firewall can abort long "
            "streaming requests — then re-run."
        )
    # Name the class: an unrecognised error is far easier to diagnose with it.
    return f"Unexpected error ({type(exc).__module__}.{type(exc).__name__}): {exc}"
