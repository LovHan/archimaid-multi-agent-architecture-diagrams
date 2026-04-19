"""使用 mock LLM 验证反射循环控制流 (不消耗 API)

运行:
    python -m plot_agent.tests.test_reflection_mock
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from ..examples.manual_ir_smoke import build_sample_ir
from ..layout import SimpleGridLayout
from ..refiner import Reflector


class MockLLM:
    """根据调用次数返回不同结果的 mock"""

    def __init__(self, critic_responses: list[dict[str, Any]]) -> None:
        self.critic_responses = critic_responses
        self.critic_call_count = 0
        self.refiner_call_count = 0

    # critic.base._run 会用 json_chat 或 vlm_chat
    def json_chat(
        self, system: str, user: str, **kwargs: Any
    ) -> dict[str, Any]:
        # Refiner 的 system 里有 "架构图的修复" 特征词
        if "修复" in system or "Refiner" in system:
            return self._refiner_response(user)

        # critic 调用
        if self.critic_call_count < len(self.critic_responses):
            resp = self.critic_responses[self.critic_call_count]
        else:
            resp = {"issues": []}
        self.critic_call_count += 1
        return resp

    def vlm_chat(
        self, system: str, user: str, image_paths: list, **kwargs: Any
    ) -> dict[str, Any]:
        return self.json_chat(system, user, **kwargs)

    def _refiner_response(self, user: str) -> dict[str, Any]:
        self.refiner_call_count += 1
        import json
        import re

        match = re.search(
            r"\[当前 IR\]\s*(\{.*?\})\s*\[需要应用的修复建议\]",
            user,
            re.DOTALL,
        )
        if match:
            return json.loads(match.group(1))
        return {}


def test_reflector_early_convergence() -> None:
    """当 critic 返回无 issue 时, 应在第一轮提前收敛"""
    ir = build_sample_ir()
    mock = MockLLM(
        critic_responses=[
            {"issues": [], "missing_nodes": []},
            {"issues": [], "moves": [], "add_edges": [], "remove_edges": []},
            {"issues": [], "scores": {"layout": 1.0}},
        ]
    )
    reflector = Reflector(llm=mock, levels=("local", "context", "global"))  # type: ignore
    engine = SimpleGridLayout()

    with patch.object(
        __import__("plot_agent.refiner.reflector", fromlist=["PngExporter"]),
        "PngExporter",
    ) as mock_png:
        mock_png.return_value.export.side_effect = RuntimeError("skip png")
        new_ir, trace, rounds = reflector.reflect(
            user_prompt="test",
            ir=ir,
            layout_engine=engine,
            max_rounds=3,
            work_dir="out/test_reflect",
        )

    assert rounds == 1, f"expected 1 round, got {rounds}"
    assert len(trace) == 1
    assert trace[0]["total_issues"] == 0
    print(f"  ✓ early convergence in {rounds} round")


def test_reflector_runs_max_rounds_when_issues_persist() -> None:
    """当 critic 持续报 issue 时, 应跑满 max_rounds"""
    ir = build_sample_ir()
    persistent_issue = {
        "issues": [
            {
                "dimension": "layout",
                "severity": "high",
                "issue": "fake",
                "fix": "fake",
            }
        ]
    }
    mock = MockLLM(critic_responses=[persistent_issue] * 30)
    reflector = Reflector(llm=mock, levels=("global",))  # type: ignore
    engine = SimpleGridLayout()

    with patch.object(
        __import__("plot_agent.refiner.reflector", fromlist=["PngExporter"]),
        "PngExporter",
    ) as mock_png:
        mock_png.return_value.export.side_effect = RuntimeError("skip")
        _, trace, rounds = reflector.reflect(
            user_prompt="test",
            ir=ir,
            layout_engine=engine,
            max_rounds=2,
            work_dir="out/test_reflect_persist",
        )

    assert rounds == 2, f"expected 2 rounds, got {rounds}"
    assert mock.refiner_call_count == 2
    print(f"  ✓ ran max rounds ({rounds}), refiner called {mock.refiner_call_count}x")


def run_all() -> None:
    print("Running reflection loop mock tests:")
    test_reflector_early_convergence()
    test_reflector_runs_max_rounds_when_issues_persist()
    print("\n✓ All reflection mock tests passed")


if __name__ == "__main__":
    run_all()
