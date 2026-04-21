"""Conditional routing after the reviewer.

- ok=true                                        -> mermaid_maker
- ok=false & review_rounds < MAX_REVIEW_ROUNDS   -> back to the executor subgraph
- ok=false & budget exhausted                    -> mermaid_maker (forward anyway)
"""

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
