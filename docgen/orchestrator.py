"""A tiny explicit workflow engine: nodes, edges and conditional routing."""

from __future__ import annotations

import time
from typing import Callable

from .state import RunState
from .trace import Trace

Node = Callable[[RunState], None]
Router = Callable[[RunState], str | None]


class WorkflowError(RuntimeError):
    """The workflow graph is invalid or exceeded its step budget."""


class Workflow:
    """Sequential execution with explicit conditional edges.

    The graph is intentionally small and visible: adding an agent means
    registering a node and one edge, not rewriting the control flow.
    """

    def __init__(self, trace: Trace, max_steps: int = 30) -> None:
        self.trace = trace
        self.max_steps = max_steps
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, str | None] = {}
        self.routers: dict[str, Router] = {}
        self.entry: str | None = None

    def add_node(self, name: str, node: Node) -> None:
        if name in self.nodes:
            raise WorkflowError(f"节点重复: {name}")
        self.nodes[name] = node

    def set_entry(self, name: str) -> None:
        if name not in self.nodes:
            raise WorkflowError(f"入口节点不存在: {name}")
        self.entry = name

    def add_edge(self, source: str, target: str | None) -> None:
        if source not in self.nodes:
            raise WorkflowError(f"边起点不存在: {source}")
        if target is not None and target not in self.nodes:
            raise WorkflowError(f"边终点不存在: {target}")
        self.edges[source] = target

    def add_conditional(self, source: str, router: Router) -> None:
        if source not in self.nodes:
            raise WorkflowError(f"条件边起点不存在: {source}")
        self.routers[source] = router

    def run(self, state: RunState) -> None:
        """Execute from the entry node until a node routes to ``None``."""

        if self.entry is None:
            raise WorkflowError("工作流没有入口节点")
        current: str | None = self.entry

        for _ in range(self.max_steps):
            if current is None:
                return
            node = self.nodes.get(current)
            if node is None:
                raise WorkflowError(f"未知节点: {current}")

            state.add_event("node_start", node=current)
            self.trace.emit("node_start", node=current)
            started = time.monotonic()
            node(state)
            duration_ms = int((time.monotonic() - started) * 1000)
            self.trace.emit("node_end", node=current, duration_ms=duration_ms)
            state.add_event("node_end", node=current, duration_ms=duration_ms)

            if current in self.routers:
                target = self.routers[current](state)
                self.trace.emit(
                    "route",
                    node=current,
                    summary=str(target),
                    target=target,
                )
                state.add_event("route", node=current, target=target)
            else:
                target = self.edges.get(current)

            current = target

        raise WorkflowError(f"工作流超过最大步数 {self.max_steps}，可能存在无限循环")
