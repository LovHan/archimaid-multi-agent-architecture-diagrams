"""Critic 基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..ir import GraphIR
from ..llm import LLMClient


class BaseCritic(ABC):
    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm or LLMClient()

    @abstractmethod
    def critique(
        self,
        user_prompt: str,
        ir: GraphIR,
        png_path: Path | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def _run(
        self,
        system: str,
        user: str,
        png_path: Path | None,
    ) -> dict[str, Any]:
        """根据是否有 png 决定用 vlm_chat 还是纯文本"""
        if png_path and Path(png_path).exists():
            try:
                result = self.llm.vlm_chat(
                    system=system,
                    user=user,
                    image_paths=[png_path],
                    as_json=True,
                    temperature=0.2,
                )
                if isinstance(result, dict):
                    return result
            except Exception as e:
                print(f"[critic] VLM 调用失败, 降级为纯文本: {e}")

        return self.llm.json_chat(system, user, temperature=0.2)
