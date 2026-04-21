"""测试固件：拦截 `plot_agent.llm._invoke_llm`，按 schema 路由返回预置 JSON。

这样 CI 无需 OPENAI_API_KEY，也不会把任何业务偏见硬编码进生产代码路径。
"""

from __future__ import annotations

import json
from typing import Any

import pytest


_PLAN_JSON: dict[str, Any] = {
    "summary": "test plan",
    "qa_chain": [
        {"question": "frontend?", "answer": "stub"},
        {"question": "backend?", "answer": "stub"},
    ],
    "frontend": "f",
    "backend": "b",
    "devops": "d",
    "data": "x",
    "security": "s",
    "deployment": "dep",
    "integrations": ["rest"],
    "open_questions": ["q?"],
}


def _design_json(role: str) -> dict[str, Any]:
    return {
        "role": role,
        "decisions": {"k": f"v-{role}"},
        "interfaces": [f"{role}-iface"],
        "depends_on": [],
        "notes": f"{role} stub",
    }


_REVIEW_JSON: dict[str, Any] = {
    "ok": True,
    "score": 0.9,
    "issues": [],
    "suggestions": [],
    "target_role": None,
}


_IR_JSON: dict[str, Any] = {
    "direction": "LR",
    "nodes": [
        {"id": "user", "label": "User", "shape": "round"},
        {"id": "frontend", "label": "Frontend", "shape": "rect"},
        {"id": "backend", "label": "Backend", "shape": "rect"},
        {"id": "data", "label": "Data", "shape": "cyl"},
        {"id": "devops", "label": "DevOps", "shape": "rect"},
        {"id": "security", "label": "Security", "shape": "rect"},
    ],
    "edges": [{"src": "user", "dst": "frontend", "label": "use"}],
    "subgraphs": {
        "fe": ["frontend"],
        "be": ["backend"],
        "dt": ["data"],
        "dv": ["devops"],
        "sc": ["security"],
    },
}


def _fake_invoke_llm(system: str, user: str, *, model_env: str = "PLANNER_MODEL") -> str:
    """根据 system prompt 里的关键词判断轮到哪个 agent，返回对应 JSON 字符串。"""
    s = system.lower()
    if "turn the brd into" in s:
        return json.dumps(_PLAN_JSON)
    if "principal architect reviewing" in s:
        return json.dumps(_REVIEW_JSON)
    if "mermaid flowchart ir" in s:
        return json.dumps(_IR_JSON)
    # executor role：prompt 里包含 "you are the {role} architect"
    for role in ("frontend", "backend", "data", "devops", "security"):
        if f"you are the {role} architect" in s:
            return json.dumps(_design_json(role))
    raise AssertionError(f"unexpected LLM call; system preview: {system[:200]}")


@pytest.fixture(autouse=True)
def stub_llm(monkeypatch):
    """默认给所有测试打上 LLM stub；需要真实 LLM 的测试可用 monkeypatch.undo。"""
    monkeypatch.setattr("plot_agent.llm._invoke_llm", _fake_invoke_llm)
    yield
