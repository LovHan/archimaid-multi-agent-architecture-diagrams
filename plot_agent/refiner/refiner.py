"""Refiner - 根据 critic 反馈修改 IR (对应 MM-WebAgent 的 refiner)"""

from __future__ import annotations

import json
from typing import Any

from ..ir import GraphIR
from ..llm import LLMClient
from ..prompts import REFINER_SYSTEM, REFINER_USER_TEMPLATE


class Refiner:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    def apply(
        self,
        user_prompt: str,
        ir: GraphIR,
        feedbacks: Any,
    ) -> GraphIR:
        """根据 feedbacks 对 IR 做一轮修改, 返回新的 IR"""
        if isinstance(feedbacks, dict | list):
            feedback_text = json.dumps(feedbacks, ensure_ascii=False, indent=2)
        else:
            feedback_text = str(feedbacks)

        user = REFINER_USER_TEMPLATE.format(
            prompt=user_prompt,
            ir_json=ir.model_dump_json(indent=2),
            feedbacks=feedback_text,
        )
        raw = self.llm.json_chat(REFINER_SYSTEM, user, temperature=0.1)

        try:
            new_ir = GraphIR.model_validate(raw)
        except Exception as e:
            print(f"[refiner] 返回 IR 格式错误, 保留原 IR: {e}")
            return ir

        # 清理 LLM 可能填的 position/size 以免干扰布局
        for n in new_ir.nodes:
            n.position = None
            n.size = None
        for g in new_ir.groups:
            g.position = None
            g.size = None

        # 轻量一致性修复
        from ..planners.pipeline import PlanningPipeline

        errs = new_ir.validate_integrity()
        if errs:
            new_ir = PlanningPipeline._auto_fix(new_ir, errs)

        return new_ir
