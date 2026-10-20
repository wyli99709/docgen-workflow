"""Tests for the OpenAI-compatible adapter's retry behavior."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from docgen.config import ModelConfig
from docgen.llm.base import LLMError
from docgen.llm.openai_compat import OpenAICompatibleAdapter


class FakeResponse:
    def __init__(self, content: str) -> None:
        self._body = json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 1},
            }
        ).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _config() -> ModelConfig:
    return ModelConfig(
        base_url="https://example.invalid/v1",
        api_key="test-key",
        model="test-model",
    )


class AdapterRetryTest(unittest.TestCase):
    @patch("docgen.llm.openai_compat.time.sleep")
    @patch("docgen.llm.openai_compat.urllib.request.urlopen")
    def test_empty_content_is_retried(self, urlopen, _sleep) -> None:
        urlopen.side_effect = [FakeResponse("   "), FakeResponse('{"ok": true}')]
        adapter = OpenAICompatibleAdapter(_config())
        result = adapter.complete(
            [{"role": "user", "content": "hi"}], agent="test"
        )
        self.assertEqual(result, '{"ok": true}')
        self.assertEqual(urlopen.call_count, 2)

    @patch("docgen.llm.openai_compat.time.sleep")
    @patch("docgen.llm.openai_compat.urllib.request.urlopen")
    def test_empty_content_raises_after_retries(self, urlopen, _sleep) -> None:
        urlopen.side_effect = [FakeResponse("   ") for _ in range(3)]
        adapter = OpenAICompatibleAdapter(_config())
        with self.assertRaises(LLMError):
            adapter.complete([{"role": "user", "content": "hi"}], agent="test")
        self.assertEqual(urlopen.call_count, 3)


if __name__ == "__main__":
    unittest.main()
