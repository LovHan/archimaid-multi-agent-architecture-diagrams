"""Reviewer 之后的条件路由：通过 → mermaid_maker；不通过 & 有额度 → 回 executor 子图。"""

from __future__ import annotations

from plot_agent.graph.nodes.reviewer import MAX_REVIEW_ROUNDS
from plot_agent.state import MultiAgentState


def route_after_review(state: MultiAgentState) -> str:
    review = state.get("review") or {}
    rounds = state.get("review_rounds", 0)
    if review.get("ok"):
        return "mermaid_maker"
    if rounds >= MAX_REVIEW_ROUNDS:
        return "mermaid_maker"
    return "executors"
