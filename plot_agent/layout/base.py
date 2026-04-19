"""布局引擎基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..ir import GraphIR


@dataclass
class LayoutResult:
    ir: GraphIR  # 已填充 position/size 的 IR
    direction: str = "TB"  # TB / LR / BT / RL
    canvas_width: float = 1200.0
    canvas_height: float = 800.0


class LayoutEngine(ABC):
    @abstractmethod
    def layout(self, ir: GraphIR, direction: str = "TB") -> LayoutResult:
        """为 IR 填充 position/size, 返回 LayoutResult"""
        raise NotImplementedError
