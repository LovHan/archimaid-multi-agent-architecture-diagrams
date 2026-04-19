"""布局引擎工厂: 自动选择可用的引擎"""

from __future__ import annotations

from .base import LayoutEngine
from .simple_layout import SimpleGridLayout


def get_layout_engine(prefer: str = "auto") -> LayoutEngine:
    """
    prefer:
      - 'graphviz': 强制使用 graphviz (失败抛错)
      - 'simple': 强制使用简易网格
      - 'auto': 尝试 graphviz, 失败则 fallback 简易
    """
    if prefer == "simple":
        return SimpleGridLayout()

    if prefer == "graphviz":
        from .graphviz_layout import GraphvizLayout

        return GraphvizLayout()

    try:
        import pygraphviz  # noqa: F401

        from .graphviz_layout import GraphvizLayout

        return GraphvizLayout()
    except Exception:
        return SimpleGridLayout()
