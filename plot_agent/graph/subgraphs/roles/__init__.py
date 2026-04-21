"""Executor role nodes.  Each role has the signature
``(state) -> {designs: {<role>: {...}}, exec_scratch: {...}}``.

Harness rules:
- Every role reads the **full** designs + plan + exec_scratch, so it can see the
  decisions other roles already made -> this is the interaction surface.
- A role only writes back its own slot, avoiding write conflicts.
- Output is constrained by the ``ComponentDesign`` schema.
"""

from plot_agent.graph.subgraphs.roles.backend import backend_node
from plot_agent.graph.subgraphs.roles.data import data_node
from plot_agent.graph.subgraphs.roles.devops import devops_node
from plot_agent.graph.subgraphs.roles.frontend import frontend_node
from plot_agent.graph.subgraphs.roles.security import security_node

ROLE_NODES = {
    "frontend": frontend_node,
    "backend": backend_node,
    "data": data_node,
    "devops": devops_node,
    "security": security_node,
}

__all__ = ["ROLE_NODES"]
