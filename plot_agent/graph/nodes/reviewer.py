"""Reviewer agent: check the overall feasibility of plan + designs."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from plot_agent.llm import call_structured
from plot_agent.schemas import ReviewReport
from plot_agent.state import MultiAgentState

AGENT_NAME = "reviewer"
MAX_REVIEW_ROUNDS = 2

SYSTEM_PROMPT = """You are a principal architect reviewing a multi-agent solution design.
Check consistency between plan and each component design:
- Do interfaces (REST/webhook/queue) match between frontend/backend/data?
- Are devops & security realistic for the deployment target?
- Are depends_on relationships closed (no dangling references)?

Respond with ONLY a single JSON object, NO prose:
{
  "ok": true | false,
  "score": 0.0-1.0,
  "issues": ["..."],
  "suggestions": ["..."],
  "target_role": null | "frontend" | "backend" | "data" | "devops" | "security"
}"""


def reviewer_node(state: MultiAgentState) -> dict[str, Any]:
    plan = state.get("plan", {})
    designs = state.get("designs", {})
    report = call_structured(
        ReviewReport,
        SYSTEM_PROMPT,
        f"Plan:\n{plan}\n\nDesigns:\n{designs}",
        model_env="CRITIC_MODEL",
    )
    rounds = state.get("review_rounds", 0) + 1
    msg = AIMessage(
        content=f"[{AGENT_NAME}] ok={report.ok} score={report.score:.2f} issues={len(report.issues)}",
        name=AGENT_NAME,
    )
    return {
        "review": report.model_dump(),
        "review_rounds": rounds,
        "messages": [msg],
        "trace": [f"{AGENT_NAME}: round={rounds} ok={report.ok}"],
    }
