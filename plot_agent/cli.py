"""plot-agent CLI - 命令行入口

子命令:
    plot-agent generate "<prompt>"       直接生成图
    plot-agent plan "<prompt>"           只规划不渲染
    plot-agent render <ir.json>          从 IR 文件直接渲染
    plot-agent env                       检测环境
    plot-agent smoke                     跑离线 smoke test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _cmd_generate(args: argparse.Namespace) -> int:
    from .agent import ArchitectureAgent

    agent = ArchitectureAgent(
        enable_reflection=args.reflection,
        max_reflection_rounds=args.max_rounds,
    )
    result = agent.generate(
        user_prompt=args.prompt,
        output_dir=args.out,
        name=args.name,
        direction=args.direction,
        export_png=not args.no_png,
    )
    print(f"drawio: {result.drawio_path}")
    if result.png_path:
        print(f"png:    {result.png_path}")
    print(
        f"stats:  {len(result.ir.nodes)} nodes, "
        f"{len(result.ir.edges)} edges, "
        f"{len(result.ir.groups)} groups"
    )

    ir_path = Path(args.out) / f"{args.name}.ir.json"
    ir_path.write_text(result.ir.model_dump_json(indent=2), encoding="utf-8")
    print(f"ir:     {ir_path}")
    return 0


def _cmd_plan(args: argparse.Namespace) -> int:
    from .agent import ArchitectureAgent

    agent = ArchitectureAgent(enable_reflection=False)
    result = agent.plan(args.prompt)
    out = {
        "task_plan": {
            "architecture_type": result.task_plan.architecture_type.value,
            "title": result.task_plan.title,
            "core_intent": result.task_plan.core_intent,
            "focus": result.task_plan.focus,
        },
        "ir": json.loads(result.ir.model_dump_json()),
        "integrity_errors": result.integrity_errors,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    from .ir import GraphIR
    from .layout import get_layout_engine
    from .render import DrawioRenderer, PngExporter

    ir = GraphIR.model_validate_json(Path(args.ir_path).read_text("utf-8"))
    get_layout_engine(prefer="auto").layout(ir, direction=args.direction)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    drawio_path = out_dir / f"{args.name}.drawio"
    DrawioRenderer().write(ir, drawio_path)
    print(f"drawio: {drawio_path}")

    if not args.no_png:
        try:
            png_path = PngExporter().export(drawio_path)
            print(f"png:    {png_path}")
        except Exception as e:
            print(f"[warn] PNG 导出失败: {e}")
    return 0


def _cmd_env(_: argparse.Namespace) -> int:
    import os

    from .layout import get_layout_engine
    from .render import PngExporter

    engine = type(get_layout_engine(prefer="auto")).__name__
    png = PngExporter()
    png_ok, png_method = png.available()

    print("== plot_agent environment ==")
    print(f"  API key set:    {bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"  base URL:       {os.getenv('OPENAI_BASE_URL') or '(openai default)'}")
    print(f"  planner model:  {os.getenv('PLANNER_MODEL', 'gpt-4o')}")
    print(f"  vlm model:      {os.getenv('VLM_MODEL', 'gpt-4o')}")
    print(f"  layout engine:  {engine}")
    print(f"  PNG export:     {'yes' if png_ok else 'no'} ({png_method})")
    print(f"  local drawio:   {PngExporter.find_local_drawio() or '-'}")
    print(f"  docker:         {'yes' if PngExporter.has_docker() else 'no'}")
    return 0


def _cmd_smoke(_: argparse.Namespace) -> int:
    from .examples.manual_ir_smoke import main as smoke_main

    smoke_main()
    return 0


def _cmd_version(_: argparse.Namespace) -> int:
    from . import __version__

    print(f"plot-agent {__version__}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="plot-agent",
        description="Hierarchical multi-agent architecture diagram generator",
    )
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="根据自然语言生成架构图")
    g.add_argument("prompt", help="架构描述")
    g.add_argument("--out", default="out", help="输出目录")
    g.add_argument("--name", default="diagram", help="文件名前缀")
    g.add_argument("--direction", default="TB", choices=["TB", "LR", "BT", "RL"])
    g.add_argument("--reflection", action="store_true", help="启用分层反射")
    g.add_argument("--max-rounds", type=int, default=3)
    g.add_argument("--no-png", action="store_true", help="不导出 PNG")
    g.set_defaults(func=_cmd_generate)

    pl = sub.add_parser("plan", help="只规划不渲染")
    pl.add_argument("prompt")
    pl.set_defaults(func=_cmd_plan)

    r = sub.add_parser("render", help="从 IR JSON 文件直接渲染 drawio")
    r.add_argument("ir_path")
    r.add_argument("--out", default="out")
    r.add_argument("--name", default="from_ir")
    r.add_argument("--direction", default="TB")
    r.add_argument("--no-png", action="store_true")
    r.set_defaults(func=_cmd_render)

    e = sub.add_parser("env", help="检测运行环境")
    e.set_defaults(func=_cmd_env)

    s = sub.add_parser("smoke", help="跑离线 smoke test (无需 API key)")
    s.set_defaults(func=_cmd_smoke)

    v = sub.add_parser("version", help="打印版本号")
    v.set_defaults(func=_cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
