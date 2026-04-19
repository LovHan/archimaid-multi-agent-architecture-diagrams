"""MCP server - 把 plot_agent 暴露给 Cursor/IDE

注: 导入 build_server / run 时才会真正加载 mcp 依赖, 保证主包无 mcp 也能用。
"""


def build_server(*args, **kwargs):  # type: ignore[no-untyped-def]
    from .server import build_server as _build

    return _build(*args, **kwargs)


def run() -> None:
    from .server import run as _run

    _run()


__all__ = ["build_server", "run"]
