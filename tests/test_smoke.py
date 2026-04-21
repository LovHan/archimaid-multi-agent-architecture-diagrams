"""冒烟测试：pipeline 可编译、走 stubbed LLM 跑完整条链、产物写到 out_dir。

LLM 调用由 conftest.py 的 stub_llm fixture 拦截——不需要 OPENAI_API_KEY。
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage

from plot_agent import build_brd_to_mermaid_pipeline
from plot_agent.llm import LLMCallError
from plot_agent.memory import make_checkpointer, make_store


BRD_SAMPLE = """
做一个多租户 SaaS 表单平台：
- 客户通过 Web 提交表单数据
- 后端需要 webhook 推送到下游 CRM
- 每个租户数据隔离
- 上线在 Azure
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
    """executors 之间通过 exec_scratch 互相留 note，说明交互发生了。"""
    app = build_brd_to_mermaid_pipeline()
    out = app.invoke(_state(BRD_SAMPLE, tmp_path))
    scratch = out.get("exec_scratch", {})
    for role in ("frontend", "backend", "data", "devops", "security"):
        assert f"note_{role}" in scratch, f"missing scratch note for {role}"


def test_llm_error_propagates(tmp_path, monkeypatch):
    """LLM 彻底不可用时必须抛 LLMCallError，不再有静默 fallback。"""

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
