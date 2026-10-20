"""Model adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMError(RuntimeError):
    """A model call failed after retries or returned an unusable response."""


class ModelAdapter(ABC):
    """Minimal interface shared by the real and scripted model adapters."""

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        agent: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        """Return the assistant text for one chat completion.

        ``json_mode`` asks the provider to constrain the response to a JSON
        object. Providers without support may ignore or reject it; the real
        adapter falls back to plain chat completions when rejected.
        """

    @property
    def last_usage(self) -> dict[str, Any] | None:
        """Token usage for the most recent call, when the provider reports it."""

        return None
