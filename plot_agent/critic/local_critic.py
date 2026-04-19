"""Local Critic - 聚焦单个节点的语义/类型/标签问题"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ir import GraphIR
from ..prompts import LOCAL_CRITIC_SYSTEM, LOCAL_CRITIC_USER_TEMPLATE
from .base import BaseCritic


class LocalCritic(BaseCritic):
    def critique(
        self,
        user_prompt: str,
        ir: GraphIR,
        png_path: Path | None = None,
    ) -> dict[str, Any]:
        user = LOCAL_CRITIC_USER_TEMPLATE.format(
            prompt=user_prompt,
            ir_json=ir.model_dump_json(indent=2),
        )
        return self._run(LOCAL_CRITIC_SYSTEM, user, png_path)
