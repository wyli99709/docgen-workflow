"""Configuration loading without third-party dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Load simple ``KEY=VALUE`` pairs; existing environment variables win."""

    env_path = Path(path) if path else PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


@dataclass
class ModelConfig:
    """Connection settings for an OpenAI-compatible chat endpoint."""

    base_url: str
    api_key: str = field(repr=False)
    model: str
    temperature: float = 0.2
    timeout: int = 120
    max_tokens: int = 4000

    @classmethod
    def from_env(cls) -> "ModelConfig":
        base_url = (
            os.environ.get("LLM_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or ""
        ).strip()
        api_key = (
            os.environ.get("LLM_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        ).strip()
        model = (
            os.environ.get("LLM_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or ""
        ).strip()
        missing = [
            name
            for name, value in (
                ("LLM_BASE_URL", base_url),
                ("LLM_API_KEY", api_key),
                ("LLM_MODEL", model),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                "缺少模型配置: " + ", ".join(missing) + "。请参考 .env.example 填写 .env。"
            )
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=float(os.environ.get("LLM_TEMPERATURE", "0.2")),
            timeout=int(os.environ.get("LLM_TIMEOUT", "120")),
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", "4000")),
        )
