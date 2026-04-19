"""三层规划流水线: task → global → local → GraphIR"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..ir import GraphIR
from ..llm import LLMClient
from .global_planner import GlobalPlan, GlobalPlanner
from .local_planner import LocalPlanner
from .task_planner import TaskPlan, TaskPlanner


@dataclass
class PlanningResult:
    task_plan: TaskPlan
    global_plan: GlobalPlan
    ir: GraphIR
    integrity_errors: list[str] = field(default_factory=list)


class PlanningPipeline:
    """串联三层规划, 返回可渲染的 GraphIR"""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()
        self.task_planner = TaskPlanner(self.llm)
        self.global_planner = GlobalPlanner(self.llm)
        self.local_planner = LocalPlanner(self.llm)

    def run(self, user_prompt: str) -> PlanningResult:
        task_plan = self.task_planner.plan(user_prompt)
        global_plan = self.global_planner.plan(user_prompt, task_plan)
        ir = self.local_planner.plan(user_prompt, task_plan, global_plan)

        errors = ir.validate_integrity()
        if errors:
            ir = self._auto_fix(ir, errors)
            errors = ir.validate_integrity()

        return PlanningResult(
            task_plan=task_plan,
            global_plan=global_plan,
            ir=ir,
            integrity_errors=errors,
        )

    @staticmethod
    def _auto_fix(ir: GraphIR, errors: list[str]) -> GraphIR:
        """轻量级一致性修复: 丢弃无效引用"""
        group_ids = {g.id for g in ir.groups}
        node_ids = {n.id for n in ir.nodes}

        # 1. 无效 group_id 置 None
        for n in ir.nodes:
            if n.group_id and n.group_id not in group_ids:
                n.group_id = None

        # 2. 无效 parent_id 置 None
        for g in ir.groups:
            if g.parent_id and g.parent_id not in group_ids:
                g.parent_id = None
            if g.parent_id == g.id:
                g.parent_id = None

        # 3. 丢弃引用不存在 node 的 edge
        ir.edges = [
            e for e in ir.edges if e.source in node_ids and e.target in node_ids
        ]

        # 4. 去重 id (保留首个)
        seen: set[str] = set()
        unique_nodes = []
        for n in ir.nodes:
            if n.id not in seen:
                seen.add(n.id)
                unique_nodes.append(n)
        ir.nodes = unique_nodes

        seen = set()
        unique_groups = []
        for g in ir.groups:
            if g.id not in seen:
                seen.add(g.id)
                unique_groups.append(g)
        ir.groups = unique_groups

        return ir
