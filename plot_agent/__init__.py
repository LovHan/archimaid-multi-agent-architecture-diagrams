"""plot_agent：BRD → Mermaid 多智能体 pipeline（LangGraph）。"""

from plot_agent.graph.builder import (
    build_brd_to_mermaid_pipeline,
    build_multi_agent_graph,
)

__all__ = [
    "build_brd_to_mermaid_pipeline",
    "build_multi_agent_graph",
    "__version__",
]

__version__ = "0.2.0"
