"""Pydantic schemas：harness 层对 LLM 输出的强约束，但对"结构更丰富的合理输出"做了软化。

策略：
- 字段优先字符串；若 LLM 返回 dict/list，用 field_validator 做无损的 JSON 序列化保留原信息。
- qa_chain 子项接受 QAPair / dict / 纯字符串，自动归一化。
- summary 缺省也能容忍（repair 阶段模型经常忘写）。
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


def _stringify(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except TypeError:
        return str(v)


# ---------- Planner ----------
class QAPair(BaseModel):
    question: str
    answer: str

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, v: Any) -> Any:
        if isinstance(v, str):
            if ":" in v:
                q, a = v.split(":", 1)
                return {"question": q.strip(), "answer": a.strip()}
            if "?" in v:
                q, _, a = v.partition("?")
                return {"question": q.strip() + "?", "answer": a.strip()}
            return {"question": v.strip(), "answer": ""}
        return v


class TechPlan(BaseModel):
    summary: str = ""
    qa_chain: list[QAPair] = Field(default_factory=list)
    frontend: str = ""
    backend: str = ""
    devops: str = ""
    data: str = ""
    security: str = ""
    deployment: str = ""
    integrations: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @field_validator("frontend", "backend", "devops", "data", "security", "deployment", mode="before")
    @classmethod
    def _coerce_scalar(cls, v: Any) -> str:
        return _stringify(v)

    @field_validator("integrations", "open_questions", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [_stringify(x) for x in v]
        return [_stringify(v)]


# ---------- Executors ----------
class ComponentDesign(BaseModel):
    role: str
    decisions: dict[str, str] = Field(default_factory=dict)
    interfaces: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("decisions", mode="before")
    @classmethod
    def _coerce_decisions(cls, v: Any) -> dict[str, str]:
        if v is None:
            return {}
        if isinstance(v, list):
            return {f"item_{i}": _stringify(x) for i, x in enumerate(v)}
        if isinstance(v, dict):
            return {k: _stringify(val) for k, val in v.items()}
        return {"value": _stringify(v)}

    @field_validator("interfaces", "depends_on", mode="before")
    @classmethod
    def _coerce_str_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [_stringify(x) for x in v]
        return [_stringify(v)]

    @field_validator("notes", mode="before")
    @classmethod
    def _coerce_notes(cls, v: Any) -> str:
        return _stringify(v)


# ---------- Reviewer ----------
class ReviewReport(BaseModel):
    ok: bool = True
    score: float = 0.0
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    target_role: str | None = None

    @field_validator("issues", "suggestions", mode="before")
    @classmethod
    def _coerce_str_list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [_stringify(x) for x in v]
        return [_stringify(v)]

    @field_validator("ok", mode="before")
    @classmethod
    def _coerce_ok(cls, v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "yes", "1", "ok", "pass")
        return bool(v)


# ---------- Mermaid IR ----------
class MermaidNode(BaseModel):
    id: str
    label: str
    shape: str = "rect"


class MermaidEdge(BaseModel):
    src: str
    dst: str
    label: str | None = None
    style: str = "solid"

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, v: Any) -> Any:
        if isinstance(v, dict):
            if "src" not in v and "from" in v:
                v["src"] = v.pop("from")
            if "dst" not in v and "to" in v:
                v["dst"] = v.pop("to")
        return v


class MermaidIR(BaseModel):
    direction: str = "LR"
    nodes: list[MermaidNode] = Field(default_factory=list)
    edges: list[MermaidEdge] = Field(default_factory=list)
    subgraphs: dict[str, list[str]] = Field(default_factory=dict)

    def to_mermaid(self) -> str:
        shape_fmt = {
            "rect": "{id}[{label}]",
            "round": "{id}({label})",
            "diamond": "{id}{{{label}}}",
            "cyl": "{id}[({label})]",
            "cloud": "{id}>{label}]",
        }
        lines = [f"flowchart {self.direction}"]
        in_group: set[str] = set()
        for grp, ids in self.subgraphs.items():
            safe_grp = grp.replace(" ", "_")
            lines.append(f"  subgraph {safe_grp}")
            for n in self.nodes:
                if n.id in ids:
                    tpl = shape_fmt.get(n.shape, shape_fmt["rect"])
                    lines.append("    " + tpl.format(id=n.id, label=n.label))
                    in_group.add(n.id)
            lines.append("  end")
        for n in self.nodes:
            if n.id in in_group:
                continue
            tpl = shape_fmt.get(n.shape, shape_fmt["rect"])
            lines.append("  " + tpl.format(id=n.id, label=n.label))
        for e in self.edges:
            arrow = "-->" if e.style == "solid" else "-.->"
            if e.label:
                lines.append(f"  {e.src} {arrow}|{e.label}| {e.dst}")
            else:
                lines.append(f"  {e.src} {arrow} {e.dst}")
        return "\n".join(lines)


__all__ = [
    "QAPair",
    "TechPlan",
    "ComponentDesign",
    "ReviewReport",
    "MermaidNode",
    "MermaidEdge",
    "MermaidIR",
]


def plan_to_dict(p: TechPlan) -> dict[str, Any]:
    return p.model_dump()


def design_to_dict(d: ComponentDesign) -> dict[str, Any]:
    return d.model_dump()
