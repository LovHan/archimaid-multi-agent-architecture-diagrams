"""Local Planner - 为每个容器填充节点和边"""

from __future__ import annotations

import json
from typing import Any

from ..ir import Edge, EdgeType, GraphIR, Node, NodeType
from ..llm import LLMClient
from ..prompts import LOCAL_PLANNER_SYSTEM, LOCAL_PLANNER_USER_TEMPLATE
from .global_planner import GlobalPlan
from .task_planner import TaskPlan


class LocalPlanner:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def plan(
        self,
        user_prompt: str,
        task_plan: TaskPlan,
        global_plan: GlobalPlan,
    ) -> GraphIR:
        task_plan_summary = {
            "architecture_type": task_plan.architecture_type.value,
            "estimated_nodes": task_plan.estimated_nodes,
            "title": task_plan.title,
            "core_intent": task_plan.core_intent,
            "focus": task_plan.focus,
        }
        global_plan_summary = {
            "groups": [g.model_dump() for g in global_plan.groups],
            "cross_group_intents": global_plan.cross_group_intents,
        }

        user = LOCAL_PLANNER_USER_TEMPLATE.format(
            prompt=user_prompt,
            task_plan=json.dumps(task_plan_summary, ensure_ascii=False, indent=2),
            global_plan=json.dumps(global_plan_summary, ensure_ascii=False, indent=2),
        )
        raw: dict[str, Any] = self.llm.json_chat(LOCAL_PLANNER_SYSTEM, user)

        nodes = self._parse_nodes(raw.get("nodes", []))
        edges = self._parse_edges(raw.get("edges", []))

        return GraphIR(
            title=task_plan.title,
            architecture_type=task_plan.architecture_type,
            description=task_plan.core_intent,
            groups=[g.to_ir_group() for g in global_plan.groups],
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _parse_nodes(raw: list[dict[str, Any]]) -> list[Node]:
        result: list[Node] = []
        for n in raw:
            try:
                ntype = NodeType(n.get("type", "generic"))
            except ValueError:
                ntype = NodeType.GENERIC
            result.append(
                Node(
                    id=str(n["id"]),
                    label=str(n.get("label", n["id"])),
                    type=ntype,
                    group_id=n.get("group_id"),
                    description=n.get("description"),
                    icon=n.get("icon"),
                    color=n.get("color"),
                )
            )
        return result

    @staticmethod
    def _parse_edges(raw: list[dict[str, Any]]) -> list[Edge]:
        result: list[Edge] = []
        for e in raw:
            try:
                etype = EdgeType(e.get("type", "sync"))
            except ValueError:
                etype = EdgeType.SYNC
            result.append(
                Edge(
                    source=str(e["source"]),
                    target=str(e["target"]),
                    label=e.get("label"),
                    type=etype,
                    description=e.get("description"),
                )
            )
        return result
