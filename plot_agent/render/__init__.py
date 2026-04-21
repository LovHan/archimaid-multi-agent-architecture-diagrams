"""图片渲染后端：把 mermaid 文本变成 PNG。"""

from plot_agent.render.png import RenderError, render_png

__all__ = ["render_png", "RenderError"]
