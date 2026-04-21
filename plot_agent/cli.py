"""plot-agent CLI 入口。

子命令：
  generate  跑完整 pipeline：BRD(.pdf|.txt|.md) → planner → executors → reviewer → mermaid → PNG
  render    只把已有 .mmd 渲染成 PNG（kroki | mmdc）

示例：
  plot-agent generate samples/databricks_brd.txt
  plot-agent generate brd.pdf --out-dir out/ --no-png
  plot-agent render out/diagram.mmd --out out/diagram.png --backend kroki
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Sequence

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax


def _read_brd(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise SystemExit(
                "PDF 输入需要 pypdf:  poetry add pypdf   或改用 .txt/.md"
            ) from exc
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8")


def _pretty(value, console: Console, title: str) -> None:
    try:
        dumped = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        console.print(Panel(Syntax(dumped, "json", word_wrap=True), title=title, expand=False))
    except Exception:  # noqa: BLE001
        console.print(Panel(str(value), title=title, expand=False))


# ---------- subcommand: generate ----------
def cmd_generate(args: argparse.Namespace) -> int:
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        print("缺少 OPENAI_API_KEY，请在 .env 中配置。", file=sys.stderr)
        return 2

    console = Console()
    brd_path = Path(args.brd)
    brd_text = _read_brd(brd_path)
    console.rule("[bold cyan]Input BRD")
    console.print(brd_text.strip()[:1200] + ("..." if len(brd_text) > 1200 else ""))
    console.print(
        f"[dim]source={brd_path}, length={len(brd_text)} chars, "
        f"planner={os.environ.get('PLANNER_MODEL')} critic={os.environ.get('CRITIC_MODEL')}[/]"
    )

    from plot_agent import build_brd_to_mermaid_pipeline
    from plot_agent.memory import make_checkpointer, make_store

    app = build_brd_to_mermaid_pipeline(
        checkpointer=make_checkpointer(),
        store=make_store(),
    )

    init_state = {
        "brd": brd_text,
        "project_id": args.project_id,
        "out_dir": args.out_dir,
        "render_png": not args.no_png,
        "png_backend": args.png_backend,
    }
    cfg = {"configurable": {"thread_id": args.thread_id}, "recursion_limit": 50}

    for step in app.stream(init_state, cfg, stream_mode="updates"):
        for node, update in step.items():
            console.rule(f"[bold yellow]{node}")
            for key, value in update.items():
                if key == "messages":
                    for m in value:
                        name = getattr(m, "name", None) or m.__class__.__name__
                        console.print(f"[green]{name}[/]: {m.content}")
                elif key == "trace":
                    for line in value:
                        console.print(f"[dim]- {line}[/]")
                elif key in {"plan", "designs", "review", "mermaid_ir", "exec_scratch"}:
                    _pretty(value, console, key)
                elif key in {"mermaid_code", "summary_md"}:
                    console.print(Panel(value, title=key, expand=False))
                else:
                    console.print(f"{key}: {value}")

    out_dir = Path(args.out_dir)
    console.rule("[bold green]Done")
    console.print(f"[bold]Mermaid:[/] {out_dir / 'diagram.mmd'}")
    console.print(f"[bold]Summary:[/] {out_dir / 'summary.md'}")
    if not args.no_png:
        console.print(f"[bold]PNG:[/]     {out_dir / 'diagram.png'}")
    return 0


# ---------- subcommand: render ----------
def cmd_render(args: argparse.Namespace) -> int:
    from plot_agent.render import RenderError, render_png

    src = Path(args.mmd)
    if not src.exists():
        print(f"file not found: {src}", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else src.with_suffix(".png")
    text = src.read_text(encoding="utf-8")
    try:
        path = render_png(text, out, backend=args.backend)
    except RenderError as exc:
        print(f"render failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {path}")
    return 0


# ---------- entry ----------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plot-agent", description="BRD → Mermaid 多智能体 pipeline.")
    parser.add_argument("-v", "--verbose", action="store_true", help="启用 DEBUG 日志")
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="跑完整 pipeline 生成图与摘要")
    g.add_argument("brd", help="BRD 文件路径（.pdf/.txt/.md）")
    g.add_argument("--out-dir", default="out", help="输出目录（默认 out/）")
    g.add_argument("--thread-id", default="cli-run-1")
    g.add_argument("--project-id", default="default")
    g.add_argument("--no-png", action="store_true", help="不生成 PNG，仅产 .mmd 与 .md")
    g.add_argument(
        "--png-backend",
        choices=["auto", "kroki", "mmdc"],
        default="auto",
        help="PNG 渲染后端（默认 auto = kroki 失败回落 mmdc）",
    )
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("render", help="把已有的 .mmd 渲染成 PNG")
    r.add_argument("mmd", help="mermaid 源文件路径")
    r.add_argument("--out", help="PNG 输出路径（默认与源同名换 .png）")
    r.add_argument(
        "--backend",
        choices=["auto", "kroki", "mmdc"],
        default="auto",
    )
    r.set_defaults(func=cmd_render)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
