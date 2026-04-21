"""Memory wiring: short-term (within a thread) + long-term (across threads).

- checkpointer: ``InMemorySaver`` by default; swap in ``SqliteSaver`` / ``PostgresSaver`` in production.
- store:        ``InMemoryStore`` by default; holds project-level long-term memory
                (past BRDs, lessons learned, naming conventions).

Usage:
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
