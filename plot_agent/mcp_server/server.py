"""MCP Server - 把 plot_agent 的核心能力暴露为 MCP tools

启动:
    python -m plot_agent.mcp_server          # stdio 模式 (给 Cursor 用)

在 Cursor 的 ~/.cursor/mcp.json 里注册:
    {
      "mcpServers": {
        "plot_agent": {
          "command": "python",
          "args": ["-m", "plot_agent.mcp_server"],
          "env": {"OPENAI_API_KEY": "sk-..."}
        }
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..agent import ArchitectureAgent
from ..ir import GraphIR
from ..render import DrawioRenderer, PngExporter

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "mcp 未安装, 请 pip install mcp"
    ) from e


def build_server(
    output_root: str = "./plot_agent_output",
) -> FastMCP:
    """构造 MCP server (可被外部复用/测试)"""
    mcp = FastMCP("plot_agent")
    output_dir = Path(output_root).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    def _new_agent(enable_reflection: bool = True) -> ArchitectureAgent:
        return ArchitectureAgent(enable_reflection=enable_reflection)

    @mcp.tool()
    def generate_diagram(
        prompt: str,
        name: str = "diagram",
        direction: str = "TB",
        enable_reflection: bool = False,
        max_rounds: int = 2,
        export_png: bool = True,
    ) -> dict[str, Any]:
        """根据自然语言描述生成架构图 (.drawio + 可选 PNG)。

        Args:
            prompt: 架构描述 (自然语言, 中英文均可)
            name:   输出文件名前缀
            direction: 布局方向 TB/LR/BT/RL
            enable_reflection: 是否启用分层反射 (慢但质量高)
            max_rounds: 反射最大轮数
            export_png: 是否导出 PNG 预览

        Returns:
            { drawio_path, png_path, ir_summary, node_count, edge_count, group_count }
        """
        agent = _new_agent(enable_reflection=enable_reflection)
        agent.max_reflection_rounds = max_rounds

        target_dir = output_dir / name
        result = agent.generate(
            prompt,
            output_dir=str(target_dir),
            name=name,
            direction=direction,
            export_png=export_png,
        )

        ir_file = target_dir / f"{name}.ir.json"
        ir_file.write_text(
            result.ir.model_dump_json(indent=2), encoding="utf-8"
        )

        return {
            "drawio_path": str(result.drawio_path),
            "png_path": str(result.png_path) if result.png_path else None,
            "ir_path": str(ir_file),
            "node_count": len(result.ir.nodes),
            "edge_count": len(result.ir.edges),
            "group_count": len(result.ir.groups),
            "reflection_rounds": result.reflection_rounds,
            "title": result.ir.title,
            "architecture_type": result.ir.architecture_type.value,
        }

    @mcp.tool()
    def plan_architecture(prompt: str) -> dict[str, Any]:
        """只做三层规划, 返回 GraphIR JSON (不渲染, 快速, 用于预览)。"""
        agent = _new_agent(enable_reflection=False)
        result = agent.plan(prompt)
        return {
            "task_plan": {
                "architecture_type": result.task_plan.architecture_type.value,
                "estimated_nodes": result.task_plan.estimated_nodes,
                "title": result.task_plan.title,
                "core_intent": result.task_plan.core_intent,
                "focus": result.task_plan.focus,
            },
            "ir": json.loads(result.ir.model_dump_json()),
            "integrity_errors": result.integrity_errors,
        }

    @mcp.tool()
    def refine_diagram(
        ir_path: str,
        feedback: str,
        name: str = "diagram_refined",
        direction: str = "TB",
    ) -> dict[str, Any]:
        """基于已有 IR + 人类反馈做一次修改, 重新渲染。

        Args:
            ir_path: 之前 generate_diagram 返回的 ir_path
            feedback: 自然语言反馈 (如 "把 Redis 移到数据层")
            name:    输出文件名
            direction: 布局方向
        """
        ir = GraphIR.model_validate_json(Path(ir_path).read_text("utf-8"))
        agent = _new_agent(enable_reflection=False)
        target_dir = output_dir / name
        result = agent.refine(
            ir=ir,
            user_prompt="根据反馈修改现有架构图",
            feedback=feedback,
            output_dir=str(target_dir),
            name=name,
            direction=direction,
        )

        ir_file = target_dir / f"{name}.ir.json"
        ir_file.write_text(
            result.ir.model_dump_json(indent=2), encoding="utf-8"
        )

        return {
            "drawio_path": str(result.drawio_path),
            "ir_path": str(ir_file),
            "node_count": len(result.ir.nodes),
            "edge_count": len(result.ir.edges),
        }

    @mcp.tool()
    def render_ir(
        ir_json: str,
        name: str = "from_ir",
        direction: str = "TB",
        export_png: bool = True,
    ) -> dict[str, Any]:
        """直接把一段 GraphIR JSON 渲染为 .drawio, 不走 LLM。

        用于已有模板/手工编写的 IR。
        """
        ir = GraphIR.model_validate_json(ir_json)
        from ..layout import get_layout_engine

        engine = get_layout_engine(prefer="auto")
        engine.layout(ir, direction=direction)

        target_dir = output_dir / name
        target_dir.mkdir(parents=True, exist_ok=True)
        drawio_path = target_dir / f"{name}.drawio"
        DrawioRenderer().write(ir, drawio_path)

        png_path: str | None = None
        if export_png:
            try:
                p = PngExporter().export(drawio_path)
                png_path = str(p)
            except Exception as e:
                png_path = f"(failed: {e})"

        return {
            "drawio_path": str(drawio_path),
            "png_path": png_path,
            "node_count": len(ir.nodes),
            "edge_count": len(ir.edges),
        }

    @mcp.tool()
    def check_environment() -> dict[str, Any]:
        """检测运行环境: LLM 配置, 布局引擎, PNG 导出后端是否就绪。"""
        import os

        from ..layout import get_layout_engine

        engine = type(get_layout_engine(prefer="auto")).__name__

        png_exp = PngExporter()
        png_ok, png_method = png_exp.available()

        return {
            "llm": {
                "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
                "base_url": os.getenv("OPENAI_BASE_URL") or "default (openai)",
                "planner_model": os.getenv("PLANNER_MODEL", "gpt-4o"),
                "vlm_model": os.getenv("VLM_MODEL", "gpt-4o"),
            },
            "layout_engine": engine,
            "png_export": {
                "available": png_ok,
                "method": png_method,
                "local_drawio": PngExporter.find_local_drawio(),
                "docker": PngExporter.has_docker(),
            },
            "output_root": str(output_dir),
        }

    return mcp


def run() -> None:
    mcp = build_server()
    mcp.run()


if __name__ == "__main__":
    run()
