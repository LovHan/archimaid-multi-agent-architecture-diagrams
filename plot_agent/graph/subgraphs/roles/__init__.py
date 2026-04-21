"""Executor role 节点集合。每个 role 都是 (state) -> {designs: {<role>: {...}}, exec_scratch: {...}}。

Harness：
- 每个 role 都读取 **全量** designs + plan + exec_scratch，这样能看到其他 role 已经做的决定 → 相互交互；
- 输出只写自己那一块，防止写冲突；
- 输出经 ComponentDesign schema 约束。
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
