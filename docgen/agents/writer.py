"""The writer agent: produce a cited README draft from facts."""

from __future__ import annotations

from ..llm.base import ModelAdapter
from ..trace import Trace
from .base import WriterAgent, load_prompt


def build_writer(adapter: ModelAdapter, trace: Trace) -> WriterAgent:
    """Create the single-shot Markdown writer."""

    return WriterAgent(
        adapter=adapter,
        system_prompt=load_prompt("writer.md"),
        trace=trace,
    )
