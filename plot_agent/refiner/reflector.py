"""Reflector - 分层反射协调器

流程:
  for round in 1..max_rounds:
    1. 布局 + 渲染 drawio
    2. 导出 PNG
    3. 依次跑 local / context / global critic, 收集 feedback
    4. 若无任何 issue, 提前收敛退出
    5. 否则调 Refiner 修改 IR, 进入下一轮
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ir import GraphIR
from ..layout import LayoutEngine
from ..llm import LLMClient
from ..render import DrawioRenderer, PngExporter
from .refiner import Refiner


class Reflector:
    def __init__(
        self,
        llm: LLMClient | None = None,
        levels: tuple[str, ...] = ("local", "context", "global"),
    ) -> None:
        self.llm = llm or LLMClient()
        self.levels = levels
        self.refiner = Refiner(self.llm)
        self._critics: dict[str, Any] = {}

    def _load_critics(self) -> None:
        """延迟导入, 避免循环依赖和不必要加载"""
        if self._critics:
            return
        from ..critic import ContextCritic, GlobalCritic, LocalCritic

        self._critics = {
            "local": LocalCritic(self.llm),
            "context": ContextCritic(self.llm),
            "global": GlobalCritic(self.llm),
        }

    def reflect(
        self,
        user_prompt: str,
        ir: GraphIR,
        layout_engine: LayoutEngine,
        direction: str = "TB",
        max_rounds: int = 3,
        work_dir: str | Path = "out/reflect",
    ) -> tuple[GraphIR, list[dict], int]:
        self._load_critics()
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)

        trace: list[dict] = []
        rounds_done = 0

        for r in range(1, max_rounds + 1):
            # 1. 布局
            layout_engine.layout(ir, direction=direction)

            # 2. 渲染 + 截图
            drawio_path = work_dir / f"round_{r}.drawio"
            DrawioRenderer().write(ir, drawio_path)
            png_path: Path | None = None
            try:
                png_path = PngExporter().export(drawio_path)
            except Exception as e:
                print(f"[reflect] round {r}: PNG 导出失败, 仅文本反射: {e}")

            # 3. 跑 critics
            round_feedback: dict[str, Any] = {}
            total_issues = 0
            for level in self.levels:
                critic = self._critics[level]
                fb = critic.critique(user_prompt, ir, png_path=png_path)
                round_feedback[level] = fb
                total_issues += self._count_issues(fb)

            trace.append(
                {
                    "round": r,
                    "drawio": str(drawio_path),
                    "png": str(png_path) if png_path else None,
                    "feedback": round_feedback,
                    "total_issues": total_issues,
                }
            )

            rounds_done = r

            # 4. 收敛?
            if total_issues == 0:
                print(f"[reflect] round {r}: 无问题, 提前收敛")
                break

            # 5. 应用 refiner
            ir = self.refiner.apply(user_prompt, ir, round_feedback)

        return ir, trace, rounds_done

    @staticmethod
    def _count_issues(fb: Any) -> int:
        if not isinstance(fb, dict):
            return 0
        return (
            len(fb.get("issues", []))
            + len(fb.get("missing_nodes", []))
            + len(fb.get("moves", []))
            + len(fb.get("add_edges", []))
            + len(fb.get("remove_edges", []))
        )
