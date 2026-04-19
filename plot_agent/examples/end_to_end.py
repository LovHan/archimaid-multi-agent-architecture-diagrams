"""端到端 pipeline smoke test (需要 OPENAI_API_KEY)

运行:
    export OPENAI_API_KEY=sk-xxx
    python -m plot_agent.examples.end_to_end

输出:
    out/e2e.drawio
    out/e2e.png (若 docker + drawio headless 镜像可用)
"""

from __future__ import annotations

from pathlib import Path

from ..agent import ArchitectureAgent

DEFAULT_PROMPT = (
    "我要一个典型的前后端分离 Web 应用: "
    "浏览器访问 React SPA (走 CDN), 后端是 Flask API Gateway 路由到 "
    "两个 Python 微服务 (Auth, Order), 使用 Redis 缓存 session 和热数据, "
    "持久化用 MySQL。请画出组件和数据流向。"
)


def main(prompt: str = DEFAULT_PROMPT) -> None:
    print("=" * 60)
    print("plot_agent end-to-end demo")
    print("=" * 60)
    print(f"用户需求: {prompt}\n")

    agent = ArchitectureAgent(enable_reflection=False)
    result = agent.generate(prompt, output_dir="out/e2e", name="e2e")

    print("\n== 产物 ==")
    print(f"  drawio: {result.drawio_path}")
    if result.png_path:
        print(f"  png:    {result.png_path}")
    print(
        f"\n  stats: {len(result.ir.nodes)} nodes, "
        f"{len(result.ir.edges)} edges, "
        f"{len(result.ir.groups)} groups"
    )
    ir_dump = Path("out/e2e/e2e.ir.json")
    ir_dump.write_text(
        result.ir.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"  ir:     {ir_dump}")


if __name__ == "__main__":
    main()
