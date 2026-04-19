"""Global Critic - 从整体视角评估布局/风格/美学"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ir import GraphIR
from ..prompts import GLOBAL_CRITIC_SYSTEM, GLOBAL_CRITIC_USER_TEMPLATE
from .base import BaseCritic


class GlobalCritic(BaseCritic):
    def critique(
        self,
        user_prompt: str,
        ir: GraphIR,
        png_path: Path | None = None,
    ) -> dict[str, Any]:
        user = GLOBAL_CRITIC_USER_TEMPLATE.format(
            prompt=user_prompt,
            ir_json=ir.model_dump_json(indent=2),
        )
        return self._run(GLOBAL_CRITIC_SYSTEM, user, png_path)
