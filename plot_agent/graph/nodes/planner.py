"""Planner agent: BRD -> Self-Q&A chain-of-thought -> TechPlan."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from plot_agent.llm import call_structured
from plot_agent.schemas import TechPlan, plan_to_dict
from plot_agent.state import MultiAgentState

AGENT_NAME = "planner"

SYSTEM_PROMPT = """You are a senior solution architect. Turn the BRD into a concise technology plan.
You MUST produce a self-questioning chain-of-thought in `qa_chain`, covering at minimum:
frontend / backend / runtime (AKS vs App Service vs serverless) / integration (API or webhook) /
deployment target / secret management / database / open questions.

Respond with ONLY a single JSON object, NO prose, matching EXACTLY this shape (all string fields are plain strings, not nested objects):
{
  "summary": "<one sentence tech solution>",
  "qa_chain": [
    {"question": "What is the frontend?", "answer": "..."},
    {"question": "Backend?", "answer": "..."}
  ],
  "frontend": "<plain text>",
  "backend":  "<plain text>",
  "devops":   "<plain text>",
  "data":     "<plain text>",
  "security": "<plain text>",
  "deployment": "<plain text>",
  "integrations": ["..."],
  "open_questions": ["..."]
}"""


def planner_node(state: MultiAgentState) -> dict[str, Any]:
    brd = state.get("brd", "")
    plan = call_structured(
        TechPlan,
        SYSTEM_PROMPT,
        f"BRD:\n{brd}",
        model_env="PLANNER_MODEL",
    )
    msg = AIMessage(content=f"[{AGENT_NAME}] plan ready: {plan.summary}", name=AGENT_NAME)
    return {
        "plan": plan_to_dict(plan),
        "messages": [msg],
        "trace": [f"{AGENT_NAME}: produced TechPlan with {len(plan.qa_chain)} QA steps"],
    }
