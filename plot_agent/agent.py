"""顶层 Agent 入口 - 把规划 + 布局 + 渲染 + 反射组装起来"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ir import GraphIR
from .layout import LayoutEngine, get_layout_engine
from .llm import LLMClient
from .planners import PlanningPipeline, PlanningResult
from .render import DrawioRenderer, PngExporter


@dataclass
class GenerationResult:
    ir: GraphIR
    drawio_path: Path
    png_path: Path | None = None
    planning: PlanningResult | None = None
    reflection_rounds: int = 0
    reflection_trace: list[dict] = field(default_factory=list)


class ArchitectureAgent:
    """端到端架构图 agent

    典型用法:
        agent = ArchitectureAgent()
        result = agent.generate("一个微服务系统...", output_dir="out", name="demo")
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        layout_engine: LayoutEngine | None = None,
        enable_reflection: bool = True,
        max_reflection_rounds: int = 3,
        reflection_levels: tuple[str, ...] = ("local", "context", "global"),
        use_templates: bool = True,
    ) -> None:
        self.llm = llm or LLMClient()
        self.layout_engine = layout_engine or get_layout_engine(prefer="auto")
        self.planner = PlanningPipeline(self.llm)
        self.enable_reflection = enable_reflection
        self.max_reflection_rounds = max_reflection_rounds
        self.reflection_levels = reflection_levels
        self.use_templates = use_templates
        self._reflector = None

    # ---------------- public API ----------------

    def plan(self, user_prompt: str) -> PlanningResult:
        """只做规划, 返回 IR (调试用)"""
        return self.planner.run(user_prompt)

    def plan_with_template(self, user_prompt: str) -> tuple[PlanningResult, str | None]:
        """优先匹配模板; 命中则把模板作为种子传给 LocalPlanner 精修。

        返回 (PlanningResult, 命中的模板名 or None)
        """
        if not self.use_templates:
            return self.planner.run(user_prompt), None

        from .templates import match_template

        tpl = match_template(user_prompt)
        if not tpl:
            return self.planner.run(user_prompt), None

        # 用模板直接做 seed, 跳过 task+global, 但仍让 LocalPlanner 按用户 prompt 调整
        # (这里简化为直接返回模板; 更严格可以让 LocalPlanner 修 IR)
        seed_ir = tpl.ir_builder()
        seed_ir.description = user_prompt
        from .planners import GlobalPlan, PlanningResult, TaskPlan

        return (
            PlanningResult(
                task_plan=TaskPlan(
                    architecture_type=tpl.architecture_type,
                    title=seed_ir.title,
                    core_intent=user_prompt,
                ),
                global_plan=GlobalPlan(
                    groups=[],
                    cross_group_intents=[],
                ),
                ir=seed_ir,
                integrity_errors=seed_ir.validate_integrity(),
            ),
            tpl.name,
        )

    def generate(
        self,
        user_prompt: str,
        output_dir: str | Path = "out",
        name: str = "diagram",
        direction: str = "TB",
        export_png: bool = True,
    ) -> GenerationResult:
        # 1. 规划
        planning = self.planner.run(user_prompt)
        ir = planning.ir

        # 2. 可选: 分层反射
        reflection_trace: list[dict] = []
        rounds = 0
        if self.enable_reflection:
            from .refiner import Reflector

            reflector = self._reflector or Reflector(
                self.llm, levels=self.reflection_levels
            )
            self._reflector = reflector
            ir, reflection_trace, rounds = reflector.reflect(
                user_prompt=user_prompt,
                ir=ir,
                layout_engine=self.layout_engine,
                direction=direction,
                max_rounds=self.max_reflection_rounds,
                work_dir=Path(output_dir) / f"{name}_reflect",
            )

        # 3. 最终布局
        self.layout_engine.layout(ir, direction=direction)

        # 4. 渲染 drawio
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        drawio_path = out_dir / f"{name}.drawio"
        DrawioRenderer().write(ir, drawio_path)

        # 5. 可选导 PNG
        png_path: Path | None = None
        if export_png:
            try:
                png_path = PngExporter().export(
                    drawio_path, out_dir / f"{name}.png"
                )
            except Exception as e:  # docker 不可用等
                print(f"[warn] PNG 导出跳过: {e}")

        return GenerationResult(
            ir=ir,
            drawio_path=drawio_path,
            png_path=png_path,
            planning=planning,
            reflection_rounds=rounds,
            reflection_trace=reflection_trace,
        )

    def refine(
        self,
        ir: GraphIR,
        user_prompt: str,
        feedback: str | dict,
        output_dir: str | Path = "out",
        name: str = "diagram_refined",
        direction: str = "TB",
    ) -> GenerationResult:
        """基于给定 IR + 用户/自动反馈做一次修复"""
        from .refiner import Refiner

        refiner = Refiner(self.llm)
        new_ir = refiner.apply(user_prompt, ir, feedback)

        self.layout_engine.layout(new_ir, direction=direction)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        drawio_path = out_dir / f"{name}.drawio"
        DrawioRenderer().write(new_ir, drawio_path)

        return GenerationResult(
            ir=new_ir,
            drawio_path=drawio_path,
            png_path=None,
            reflection_rounds=1,
        )
