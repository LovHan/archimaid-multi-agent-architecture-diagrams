"""Global Planner - 规划顶层容器结构"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..ir import Group, GroupType
from ..llm import LLMClient
from ..prompts import GLOBAL_PLANNER_SYSTEM, GLOBAL_PLANNER_USER_TEMPLATE
from .task_planner import TaskPlan


class GroupPlan(BaseModel):
    id: str
    label: str
    type: GroupType = GroupType.GENERIC
    parent_id: str | None = None
    description: str | None = None
    expected_node_count: int = 3
    expected_node_types: list[str] = Field(default_factory=list)

    def to_ir_group(self) -> Group:
        return Group(
            id=self.id,
            label=self.label,
            type=self.type,
            parent_id=self.parent_id,
            description=self.description,
        )


class GlobalPlan(BaseModel):
    groups: list[GroupPlan] = Field(default_factory=list)
    cross_group_intents: list[str] = Field(default_factory=list)


class GlobalPlanner:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def plan(self, user_prompt: str, task_plan: TaskPlan) -> GlobalPlan:
        user = GLOBAL_PLANNER_USER_TEMPLATE.format(
            prompt=user_prompt,
            architecture_type=task_plan.architecture_type.value,
            estimated_nodes=task_plan.estimated_nodes,
            title=task_plan.title,
            core_intent=task_plan.core_intent,
            focus=", ".join(task_plan.focus),
        )
        raw: dict[str, Any] = self.llm.json_chat(GLOBAL_PLANNER_SYSTEM, user)

        groups: list[GroupPlan] = []
        for g in raw.get("groups", []):
            try:
                gtype = GroupType(g.get("type", "generic"))
            except ValueError:
                gtype = GroupType.GENERIC
            groups.append(
                GroupPlan(
                    id=str(g["id"]),
                    label=str(g.get("label", g["id"])),
                    type=gtype,
                    parent_id=g.get("parent_id"),
                    description=g.get("description"),
                    expected_node_count=int(g.get("expected_node_count", 3)),
                    expected_node_types=list(g.get("expected_node_types", [])),
                )
            )

        return GlobalPlan(
            groups=groups,
            cross_group_intents=list(raw.get("cross_group_intents", [])),
        )
