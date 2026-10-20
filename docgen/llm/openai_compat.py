"""OpenAI-compatible chat completions over the standard library."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from ..config import ModelConfig
from .base import LLMError, ModelAdapter


class OpenAICompatibleAdapter(ModelAdapter):
    """Call ``/chat/completions`` on any OpenAI-compatible endpoint."""

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self._last_usage: dict[str, Any] | None = None

    @property
    def last_usage(self) -> dict[str, Any] | None:
        return self._last_usage

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        agent: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": (
                self.config.temperature if temperature is None else temperature
            ),
            "max_tokens": self.config.max_tokens if max_tokens is None else max_tokens,
            "stream": False,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        request = self._build_request(payload)

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.config.timeout
                ) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                data = json.loads(raw)
                return self._extract_text(data)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:800]
                last_error = LLMError(
                    f"模型接口返回 HTTP {exc.code}（agent={agent}）: {detail}"
                )
                if exc.code in {400, 422} and "response_format" in detail.lower():
                    # Older OpenAI-compatible servers may not know JSON mode.
                    payload.pop("response_format", None)
                    json_mode = False
                    request = self._build_request(payload)
                    continue
                if exc.code in {400, 401, 403, 404}:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = LLMError(f"模型调用失败（agent={agent}）: {exc}")
            except LLMError as exc:
                # Empty or malformed content can happen transiently on some
                # providers; retry the same request instead of failing the run.
                last_error = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))

        raise last_error or LLMError("模型调用失败：未知错误")

    def _build_request(self, payload: dict[str, Any]) -> urllib.request.Request:
        return urllib.request.Request(
            self._endpoint(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )

    def _extract_text(self, data: dict[str, Any]) -> str:
        self._last_usage = data.get("usage")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LLMError(f"模型响应缺少 choices: {json.dumps(data)[:500]}")
        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
        if not isinstance(content, str) or not content.strip():
            finish_reason = choices[0].get("finish_reason")
            raise LLMError(
                "模型响应内容为空: "
                f"finish_reason={finish_reason!r}, "
                f"usage={data.get('usage')!r}"
            )
        return content
