"""Task Planner - 识别架构类型, 给出整体意图摘要"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..ir import ArchitectureType
from ..llm import LLMClient
from ..prompts import TASK_PLANNER_SYSTEM, TASK_PLANNER_USER_TEMPLATE


class TaskPlan(BaseModel):
    architecture_type: ArchitectureType = ArchitectureType.CUSTOM
    estimated_nodes: int = 10
    title: str = "Architecture Diagram"
    core_intent: str = ""
    focus: list[str] = Field(default_factory=list)


class TaskPlanner:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def plan(self, user_prompt: str) -> TaskPlan:
        user = TASK_PLANNER_USER_TEMPLATE.format(prompt=user_prompt)
        raw = self.llm.json_chat(TASK_PLANNER_SYSTEM, user)

        # 兜底: 非法枚举时 fallback 到 custom
        arch = raw.get("architecture_type", "custom")
        try:
            arch_enum = ArchitectureType(arch)
        except ValueError:
            arch_enum = ArchitectureType.CUSTOM

        return TaskPlan(
            architecture_type=arch_enum,
            estimated_nodes=int(raw.get("estimated_nodes", 10)),
            title=str(raw.get("title", "Architecture Diagram")),
            core_intent=str(raw.get("core_intent", "")),
            focus=list(raw.get("focus", [])),
        )
