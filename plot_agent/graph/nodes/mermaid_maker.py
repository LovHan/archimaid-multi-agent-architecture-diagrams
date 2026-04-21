"""MermaidMaker Agent：plan + designs → MermaidIR（结构化 JSON）。

为什么拆成 IR 而不是直接出 mermaid 文本？
- IR 可 schema 校验、可 diff、可被其他后端（graphviz、excalidraw）复用；
- 文本生成放在 schemas.MermaidIR.to_mermaid()，单一职责。
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from plot_agent.llm import call_structured
from plot_agent.schemas import MermaidIR
from plot_agent.state import MultiAgentState

AGENT_NAME = "mermaid_maker"

SYSTEM_PROMPT = """Convert the plan and component designs into a Mermaid flowchart IR.
- Each component becomes a node; group nodes by role using `subgraphs`.
- Edges come from interfaces / depends_on relationships.
- Use diamond shape for decision points and cyl for databases.

Respond with ONLY a single JSON object, NO prose, matching EXACTLY:
{
  "direction": "LR",
  "nodes":    [{"id": "frontend", "label": "React SPA", "shape": "rect"}],
  "edges":    [{"src": "user", "dst": "frontend", "label": "request", "style": "solid"}],
  "subgraphs": {"frontend_group": ["frontend"], "backend_group": ["backend"]}
}
Node ids MUST be short alphanumeric identifiers (no spaces). Shapes: rect|round|diamond|cyl|cloud."""


def mermaid_maker_node(state: MultiAgentState) -> dict[str, Any]:
    plan = state.get("plan", {})
    designs = state.get("designs", {})
    ir = call_structured(
        MermaidIR,
        SYSTEM_PROMPT,
        f"Plan:\n{plan}\n\nDesigns:\n{designs}",
        model_env="PLANNER_MODEL",
    )
    msg = AIMessage(
        content=f"[{AGENT_NAME}] IR ready: {len(ir.nodes)} nodes / {len(ir.edges)} edges",
        name=AGENT_NAME,
    )
    return {
        "mermaid_ir": ir.model_dump(),
        "messages": [msg],
        "trace": [f"{AGENT_NAME}: nodes={len(ir.nodes)} edges={len(ir.edges)}"],
    }
