"""共享图状态（BRD → Mermaid pipeline）。

Harness 原则：state 是所有节点的单一事实源；每个字段都有明确 owner。
- brd：输入业务需求文档。
- plan：PlannerAgent 产出的 TechPlan dict（含 self-Q&A CoT）。
- designs：role -> ComponentDesign dict，由 executors 迭代更新。
- exec_scratch：executors 子图内的共享便签，用于角色之间互相看到对方的 note。
- review：ReviewReport dict。review_rounds：已进行的审阅轮数。
- mermaid_ir / mermaid_code / summary_md：最终产物。
- trace：可观测性日志行（append-only）。
- thread_id / project_id：memory 维度（thread=单次对话，project=跨会话长期记忆）。
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def _merge_dict(old: dict | None, new: dict | None) -> dict:
    """Reducer：浅合并 designs / scratchpad 等字典字段。"""
    return {**(old or {}), **(new or {})}


def _append_list(old: list | None, new: list | None) -> list:
    return (old or []) + (new or [])


class MultiAgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]

    brd: str
    plan: dict[str, Any]
    designs: Annotated[dict[str, dict[str, Any]], _merge_dict]
    exec_scratch: Annotated[dict[str, Any], _merge_dict]

    review: dict[str, Any]
    review_rounds: int
    executor_turn: int

    mermaid_ir: dict[str, Any]
    mermaid_code: str
    summary_md: str

    trace: Annotated[list[str], _append_list]

    thread_id: str
    project_id: str
    out_dir: str
    render_png: bool
    png_backend: str
