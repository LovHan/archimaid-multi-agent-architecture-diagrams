"""Executor 子图：多 role 轮询协作。

拓扑：
    START → frontend → backend → data → devops → security → turn_gate
    turn_gate: turn < MAX_TURNS → frontend（再跑一轮，此时每个 role 都能看到其他 role 上轮的结果）
                else → END

这就实现了"executors 相互交互"：顺序 + 多轮 + 共享 state.designs & exec_scratch。
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from plot_agent.graph.subgraphs.roles import ROLE_NODES
from plot_agent.state import MultiAgentState

MAX_EXECUTOR_TURNS = 2
_ROLE_ORDER = ("frontend", "backend", "data", "devops", "security")


def turn_gate_node(state: MultiAgentState) -> dict[str, Any]:
    turn = state.get("executor_turn", 0) + 1
    return {"executor_turn": turn, "trace": [f"executor_gate: finished turn {turn}"]}


def _route_after_gate(state: MultiAgentState) -> str:
    turn = state.get("executor_turn", 0)
    if turn >= MAX_EXECUTOR_TURNS:
        return END
    return _ROLE_ORDER[0]


def build_executor_subgraph():
    g = StateGraph(MultiAgentState)
    for name in _ROLE_ORDER:
        g.add_node(name, ROLE_NODES[name])
    g.add_node("turn_gate", turn_gate_node)

    g.add_edge(START, _ROLE_ORDER[0])
    for a, b in zip(_ROLE_ORDER, _ROLE_ORDER[1:]):
        g.add_edge(a, b)
    g.add_edge(_ROLE_ORDER[-1], "turn_gate")
    g.add_conditional_edges(
        "turn_gate",
        _route_after_gate,
        {_ROLE_ORDER[0]: _ROLE_ORDER[0], END: END},
    )
    return g.compile()
