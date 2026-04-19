"""Context Critic - 聚焦容器内部和跨容器关系的问题"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ir import GraphIR
from ..prompts import CONTEXT_CRITIC_SYSTEM, CONTEXT_CRITIC_USER_TEMPLATE
from .base import BaseCritic


class ContextCritic(BaseCritic):
    def critique(
        self,
        user_prompt: str,
        ir: GraphIR,
        png_path: Path | None = None,
    ) -> dict[str, Any]:
        user = CONTEXT_CRITIC_USER_TEMPLATE.format(
            prompt=user_prompt,
            ir_json=ir.model_dump_json(indent=2),
        )
        return self._run(CONTEXT_CRITIC_SYSTEM, user, png_path)
