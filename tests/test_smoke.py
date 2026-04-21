"""Smoke tests: the pipeline compiles, runs end-to-end against a stubbed LLM, and writes artifacts.

LLM calls are intercepted by the ``stub_llm`` fixture in ``conftest.py`` so no
``OPENAI_API_KEY`` is required.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage

from plot_agent import build_brd_to_mermaid_pipeline
from plot_agent.llm import LLMCallError
from plot_agent.memory import make_checkpointer, make_store


BRD_SAMPLE = """
Build a multi-tenant SaaS form platform:
- customers submit form data through the web
- the backend pushes data downstream via webhooks to a CRM
- per-tenant data isolation
- target deployment: Azure
"""


def _state(brd: str, out_dir: Path) -> dict:
    return {
        "brd": brd,
        "messages": [HumanMessage(content=brd)],
        "project_id": "demo",
        "out_dir": str(out_dir),
    }


def test_pipeline_runs_end_to_end(tmp_path):
    app = build_brd_to_mermaid_pipeline()
    out = app.invoke(_state(BRD_SAMPLE, tmp_path))

    assert out["plan"]["qa_chain"], "planner must produce QA chain"
    assert {"frontend", "backend", "data", "devops", "security"} <= set(out["designs"].keys())
    assert out["mermaid_code"].startswith("flowchart")
    assert "subgraph" in out["mermaid_code"]
    assert (tmp_path / "diagram.mmd").exists()
    assert (tmp_path / "summary.md").exists()


def test_pipeline_with_memory(tmp_path):
    app = build_brd_to_mermaid_pipeline(
        checkpointer=make_checkpointer(),
        store=make_store(),
    )
    cfg = {"configurable": {"thread_id": "t1"}}
    out = app.invoke(_state(BRD_SAMPLE, tmp_path), cfg)
    assert out["review"]["ok"] in (True, False)
    assert out.get("executor_turn", 0) >= 1
    assert len(out.get("trace", [])) > 0


def test_executor_interaction(tmp_path):
    """Executors leave notes for each other in ``exec_scratch``; this proves they interacted."""
    app = build_brd_to_mermaid_pipeline()
    out = app.invoke(_state(BRD_SAMPLE, tmp_path))
    scratch = out.get("exec_scratch", {})
    for role in ("frontend", "backend", "data", "devops", "security"):
        assert f"note_{role}" in scratch, f"missing scratch note for {role}"


def test_llm_error_propagates(tmp_path, monkeypatch):
    """When the LLM is fully unavailable the pipeline must raise ``LLMCallError``,
    never swallow it with a silent fallback."""

    def boom(*_a, **_kw):
        raise LLMCallError("simulated outage")

    monkeypatch.setattr("plot_agent.llm._invoke_llm", boom)
    app = build_brd_to_mermaid_pipeline()

    try:
        app.invoke(_state(BRD_SAMPLE, tmp_path))
    except LLMCallError:
        return
    except Exception as exc:
        if isinstance(exc.__cause__, LLMCallError) or "simulated outage" in str(exc):
            return
        raise
    raise AssertionError("expected LLMCallError to propagate")
