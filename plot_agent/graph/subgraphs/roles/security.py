from __future__ import annotations

from plot_agent.graph.subgraphs.roles._common import run_role
from plot_agent.state import MultiAgentState


def security_node(state: MultiAgentState):
    return run_role("security", state)
