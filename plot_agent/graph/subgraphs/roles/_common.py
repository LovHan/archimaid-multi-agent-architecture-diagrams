"""Role executor 的公共 helper：构建 prompt / 组装 context / 调 LLM / 统一返回。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from plot_agent.llm import call_structured
from plot_agent.schemas import ComponentDesign
from plot_agent.state import MultiAgentState

SYSTEM_TEMPLATE = """You are the {role} architect in a multi-agent design team.
Read the plan and the other roles' current designs, then update only your role.
- Reference other roles by name in `depends_on` and `interfaces`.
- If the reviewer left feedback for you, address its issues first.
- Be concrete: database name, api contract, resource type, IaC tool, etc.

Respond with ONLY a single JSON object, NO prose, matching EXACTLY:
{{
  "role": "{role}",
  "decisions": {{"key": "string value", "...": "..."}},
  "interfaces": ["exposes REST /api/v1/...", "publishes event X"],
  "depends_on": ["backend", "security"],
  "notes": "plain text"
}}
All values in `decisions` MUST be plain strings (not nested objects)."""


def _role_context(state: MultiAgentState, role: str) -> str:
    plan = state.get("plan", {})
    designs = state.get("designs", {}) or {}
    peers = {k: v for k, v in designs.items() if k != role}
    scratch = state.get("exec_scratch", {}) or {}
    review = state.get("review", {}) or {}
    feedback = ""
    if review.get("target_role") == role and not review.get("ok", True):
        feedback = f"\nReviewer feedback (must address):\n{review.get('issues', [])}\n"
    return (
        f"Role: {role}\n"
        f"Plan:\n{plan}\n\n"
        f"Peer designs:\n{peers}\n\n"
        f"Shared scratchpad:\n{scratch}\n"
        f"{feedback}"
    )


def run_role(role: str, state: MultiAgentState) -> dict[str, Any]:
    design = call_structured(
        ComponentDesign,
        SYSTEM_TEMPLATE.format(role=role),
        _role_context(state, role),
        model_env="PLANNER_MODEL",
    )
    if design.role != role:
        design.role = role

    note = design.notes or f"{role} updated in turn {state.get('executor_turn', 0)}"
    msg = AIMessage(content=f"[{role}] {note[:80]}", name=role)
    return {
        "designs": {role: design.model_dump()},
        "exec_scratch": {f"note_{role}": note},
        "messages": [msg],
        "trace": [f"executor:{role} turn={state.get('executor_turn', 0)} depends_on={design.depends_on}"],
    }
