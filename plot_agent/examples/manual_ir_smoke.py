"""Smoke test (不需要 LLM): 手工构造 IR 验证 布局+渲染 管线

运行:
    python -m plot_agent.examples.manual_ir_smoke

输出:
    out/manual_smoke.drawio  (可拖到 app.diagrams.net 验证)
"""

from __future__ import annotations

from pathlib import Path

from ..ir import (
    ArchitectureType,
    Edge,
    EdgeType,
    GraphIR,
    Group,
    GroupType,
    Node,
    NodeType,
)
from ..layout import get_layout_engine
from ..render import DrawioRenderer


def build_sample_ir() -> GraphIR:
    """前后端分离 + Redis + MySQL 的样例架构"""
    return GraphIR(
        title="前后端分离 Web 应用",
        architecture_type=ArchitectureType.FRONTEND_BACKEND,
        description="React SPA + Flask API + Redis 缓存 + MySQL 存储",
        groups=[
            Group(id="client", label="客户端", type=GroupType.LAYER),
            Group(id="frontend", label="前端层", type=GroupType.LAYER),
            Group(id="backend", label="后端服务", type=GroupType.LAYER),
            Group(id="data", label="数据层", type=GroupType.LAYER),
        ],
        nodes=[
            Node(id="user", label="用户", type=NodeType.USER, group_id="client"),
            Node(
                id="browser",
                label="浏览器",
                type=NodeType.UI,
                group_id="client",
            ),
            Node(id="cdn", label="CDN", type=NodeType.CDN, group_id="frontend"),
            Node(
                id="web_app",
                label="React SPA",
                type=NodeType.UI,
                group_id="frontend",
            ),
            Node(
                id="api_gateway",
                label="API Gateway",
                type=NodeType.GATEWAY,
                group_id="backend",
            ),
            Node(
                id="auth_service",
                label="Auth Service",
                type=NodeType.SERVICE,
                group_id="backend",
            ),
            Node(
                id="order_service",
                label="Order Service",
                type=NodeType.SERVICE,
                group_id="backend",
            ),
            Node(
                id="redis",
                label="Redis",
                type=NodeType.CACHE,
                group_id="data",
            ),
            Node(
                id="mysql",
                label="MySQL",
                type=NodeType.DATABASE,
                group_id="data",
            ),
        ],
        edges=[
            Edge(source="user", target="browser", label="浏览", type=EdgeType.SYNC),
            Edge(source="browser", target="cdn", label="静态资源", type=EdgeType.SYNC),
            Edge(source="browser", target="web_app", label="加载", type=EdgeType.SYNC),
            Edge(
                source="web_app",
                target="api_gateway",
                label="HTTPS/REST",
                type=EdgeType.SYNC,
            ),
            Edge(
                source="api_gateway",
                target="auth_service",
                label="鉴权",
                type=EdgeType.SYNC,
            ),
            Edge(
                source="api_gateway",
                target="order_service",
                label="路由",
                type=EdgeType.SYNC,
            ),
            Edge(
                source="auth_service",
                target="redis",
                label="session",
                type=EdgeType.SYNC,
            ),
            Edge(
                source="order_service",
                target="redis",
                label="缓存",
                type=EdgeType.SYNC,
            ),
            Edge(
                source="order_service",
                target="mysql",
                label="读写",
                type=EdgeType.DATA_FLOW,
            ),
        ],
    )


def main() -> None:
    print("[1/4] 构造 IR...")
    ir = build_sample_ir()
    errs = ir.validate_integrity()
    print(f"  integrity errors: {errs or 'none'}")

    print("[2/4] 选择布局引擎...")
    engine = get_layout_engine(prefer="auto")
    print(f"  engine: {type(engine).__name__}")

    print("[3/4] 执行布局...")
    result = engine.layout(ir, direction="TB")
    print(
        f"  canvas: {result.canvas_width:.0f} x {result.canvas_height:.0f}, "
        f"direction={result.direction}"
    )

    print("[4/4] 渲染 drawio XML...")
    out_path = Path("out/manual_smoke.drawio")
    DrawioRenderer().write(ir, out_path)
    print(f"  written: {out_path.resolve()}")
    print("\n可拖到 https://app.diagrams.net/ 验证效果")


if __name__ == "__main__":
    main()
