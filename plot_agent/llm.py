"""LLM call wrapper (the harness layer).

Responsibilities:
- ``call_structured``: LLM -> JSON -> Pydantic schema; on parse failure run a repair loop;
  on transient network errors retry with exponential backoff.
- If still failing, raise ``LLMCallError`` and let the caller (node / runner) decide.
  **No hard-coded business fallbacks live in this package.**
- Each agent picks its model via ``model_env`` pointing at an env var key
  (``PLANNER_MODEL`` / ``CRITIC_MODEL`` / ...).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger("plot_agent.llm")

T = TypeVar("T", bound=BaseModel)

_DEFAULT_MODEL_ENV = "PLANNER_MODEL"
_NETWORK_RETRIES = 3
_NETWORK_BACKOFF = 2.0


class LLMCallError(RuntimeError):
    """The LLM call or schema parsing ultimately failed."""


def _resolve_model(model_env: str) -> str:
    model = (
        os.environ.get(model_env)
        or os.environ.get("PLANNER_MODEL")
        or os.environ.get("OPENAI_MODEL")
    )
    if not model:
        raise LLMCallError(
            f"No model configured. Set {model_env} or PLANNER_MODEL or OPENAI_MODEL."
        )
    return model


def _invoke_llm(system: str, user: str, *, model_env: str = _DEFAULT_MODEL_ENV) -> str:
    """Call OpenAI Chat Completions, ask for JSON, retry on transient network errors."""
    from openai import APIConnectionError, APITimeoutError, BadRequestError, OpenAI, RateLimitError

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMCallError("OPENAI_API_KEY not set.")

    client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL") or None)
    model = _resolve_model(model_env)

    messages = [
        {"role": "system", "content": system + "\nYou MUST reply with a single valid JSON object only."},
        {"role": "user", "content": user},
    ]

    last_err: Exception | None = None
    for attempt in range(_NETWORK_RETRIES):
        try:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    response_format={"type": "json_object"},
                    messages=messages,
                )
            except BadRequestError as exc:
                log.warning("model %s rejected response_format=json_object (%s); retry without", model, exc)
                resp = client.chat.completions.create(model=model, messages=messages)
            return resp.choices[0].message.content or ""
        except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
            last_err = exc
            wait = _NETWORK_BACKOFF * (2**attempt)
            log.warning("LLM network error (%s), retry %d/%d after %.1fs", exc, attempt + 1, _NETWORK_RETRIES, wait)
            time.sleep(wait)

    raise LLMCallError(f"LLM unavailable after {_NETWORK_RETRIES} retries: {last_err}")


def call_structured(
    schema: type[T],
    system_prompt: str,
    user_prompt: str,
    *,
    max_repair: int = 2,
    model_env: str = _DEFAULT_MODEL_ENV,
) -> T:
    """LLM -> JSON -> schema.  Retries up to ``max_repair`` times, otherwise raises ``LLMCallError``."""
    last_err: Exception | None = None
    attempt_prompt = user_prompt
    for attempt in range(max_repair + 1):
        raw = _invoke_llm(system_prompt, attempt_prompt, model_env=model_env)
        try:
            return schema.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            last_err = exc
            log.warning("call_structured repair %d/%d: %s", attempt + 1, max_repair + 1, exc)
            attempt_prompt = (
                f"{user_prompt}\n\nPrevious reply failed schema validation: {exc!s}. "
                "Return ONLY valid JSON matching the schema."
            )

    raise LLMCallError(
        f"{schema.__name__}: schema parse failed after {max_repair + 1} attempts: {last_err}"
    )
