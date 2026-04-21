"""Memory 装配：短期（thread 内）+ 长期（跨 thread）。

- checkpointer：InMemorySaver。生产可换 SqliteSaver / PostgresSaver。
- store：InMemoryStore。存"项目级"长期记忆（过往 BRD、lessons learned、命名规范）。

用法：
    from plot_agent.memory import make_checkpointer, make_store
    app = build_brd_to_mermaid_pipeline(checkpointer=make_checkpointer(), store=make_store())
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore


def make_checkpointer() -> InMemorySaver:
    return InMemorySaver()


def make_store() -> InMemoryStore:
    return InMemoryStore()


def project_namespace(project_id: str) -> tuple[str, ...]:
    return ("projects", project_id)


def remember(store: InMemoryStore, project_id: str, key: str, value: dict[str, Any]) -> None:
    store.put(project_namespace(project_id), key, value)


def recall(store: InMemoryStore, project_id: str, key: str) -> dict[str, Any] | None:
    item = store.get(project_namespace(project_id), key)
    return item.value if item else None
