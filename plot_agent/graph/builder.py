"""BRD → Mermaid pipeline 主图组装。

拓扑：
    START
      │
      ▼
    planner ──▶ executors(subgraph) ──▶ reviewer
                     ▲                      │
                     └──── not ok & retry ──┘
                                            │ ok | 超过额度
                                            ▼
                                      mermaid_maker ──▶ mermaid_renderer ──▶ END

Memory：
- checkpointer：thread 内断点续跑；可选。
- store：跨 thread 长期记忆（项目级），通过 MultiAgentState.project_id 访问。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from plot_agent.graph.nodes.mermaid_maker import mermaid_maker_node
from plot_agent.graph.nodes.mermaid_renderer import mermaid_renderer_node
from plot_agent.graph.nodes.planner import planner_node
from plot_agent.graph.nodes.reviewer import reviewer_node
from plot_agent.graph.nodes.routing import route_after_review
from plot_agent.graph.subgraphs.executors import build_executor_subgraph
from plot_agent.state import MultiAgentState


def build_brd_to_mermaid_pipeline(*, checkpointer=None, store=None):
    """返回已 compile 的 pipeline graph。

    用法：
        from plot_agent import build_brd_to_mermaid_pipeline
        from plot_agent.memory import make_checkpointer, make_store

        app = build_brd_to_mermaid_pipeline(
            checkpointer=make_checkpointer(),
            store=make_store(),
        )
        out = app.invoke(
            {"brd": "我们要做一个多租户 SaaS..."},
            {"configurable": {"thread_id": "t1"}},
        )
        print(out["mermaid_code"])
    """
    executor_subgraph = build_executor_subgraph()

    g = StateGraph(MultiAgentState)
    g.add_node("planner", planner_node)
    g.add_node("executors", executor_subgraph)
    g.add_node("reviewer", reviewer_node)
    g.add_node("mermaid_maker", mermaid_maker_node)
    g.add_node("mermaid_renderer", mermaid_renderer_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "executors")
    g.add_edge("executors", "reviewer")
    g.add_conditional_edges(
        "reviewer",
        route_after_review,
        {"executors": "executors", "mermaid_maker": "mermaid_maker"},
    )
    g.add_edge("mermaid_maker", "mermaid_renderer")
    g.add_edge("mermaid_renderer", END)

    return g.compile(checkpointer=checkpointer, store=store)


# 向后兼容别名
build_multi_agent_graph = build_brd_to_mermaid_pipeline
