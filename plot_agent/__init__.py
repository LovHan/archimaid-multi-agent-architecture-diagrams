"""plot_agent: a LangGraph multi-agent pipeline that turns a BRD into a Mermaid diagram."""

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
