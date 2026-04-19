"""GraphIR - 架构图的中间表示

设计原则:
1. LLM 唯一产物就是 GraphIR, 不处理像素坐标
2. Position/Size 由布局引擎在后续阶段填入
3. 所有可选视觉属性都给默认值, 规划阶段 LLM 可以不填
4. Node/Edge/Group 形成一棵容器树 (group 可嵌套, node 必须属于某个 group 或顶层)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ArchitectureType(str, Enum):
    """常见架构类型, 帮助 Task Planner 快速定位模板"""

    WEB_3TIER = "web_3tier"
    MICROSERVICES = "microservices"
    FRONTEND_BACKEND = "frontend_backend"
    DATA_PIPELINE = "data_pipeline"
    ML_SYSTEM = "ml_system"
    RAG = "rag"
    SERVERLESS = "serverless"
    EVENT_DRIVEN = "event_driven"
    CLOUD_NATIVE = "cloud_native"
    MONOLITH = "monolith"
    CUSTOM = "custom"


class NodeType(str, Enum):
    """节点类型 - 决定 shape & 图标"""

    SERVICE = "service"
    UI = "ui"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    USER = "user"
    EXTERNAL = "external"
    FUNCTION = "function"
    CONTAINER = "container"
    MODEL = "model"
    GATEWAY = "gateway"
    LOAD_BALANCER = "load_balancer"
    CDN = "cdn"
    COMPUTE = "compute"
    NOTE = "note"
    GENERIC = "generic"


class EdgeType(str, Enum):
    """边类型 - 决定线型"""

    SYNC = "sync"
    ASYNC = "async"
    DATA_FLOW = "data_flow"
    DEPENDENCY = "dependency"
    INHERITANCE = "inheritance"
    BIDIRECTIONAL = "bidirectional"
    CONTROL = "control"


class GroupType(str, Enum):
    """容器/分组类型"""

    LAYER = "layer"
    ZONE = "zone"
    CLUSTER = "cluster"
    NAMESPACE = "namespace"
    VPC = "vpc"
    GENERIC = "generic"


class Position(BaseModel):
    x: float = 0.0
    y: float = 0.0


class Size(BaseModel):
    width: float = 120.0
    height: float = 60.0


class Node(BaseModel):
    """架构图中的一个节点 (组件/服务/数据库...)"""

    id: str = Field(..., description="唯一 ID, 建议 snake_case, 如 'api_gateway'")
    label: str = Field(..., description="显示文本")
    type: NodeType = NodeType.GENERIC
    group_id: str | None = Field(None, description="所属 group 的 id, None 表示顶层")
    description: str | None = None
    icon: str | None = Field(
        None, description="可选 shape 名, 如 'mscae/compute/virtual_machine'"
    )
    color: str | None = Field(None, description="填充色, hex 或预定义如 'primary'")
    position: Position | None = Field(None, description="布局引擎填充, LLM 不应输出")
    size: Size | None = Field(None, description="布局引擎填充, LLM 不应输出")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Node.id 不能为空")
        return v.strip()


class Edge(BaseModel):
    """连接两个节点的边"""

    id: str | None = None
    source: str = Field(..., description="起点 node id")
    target: str = Field(..., description="终点 node id")
    label: str | None = None
    type: EdgeType = EdgeType.SYNC
    description: str | None = None
    style: str | None = Field(None, description="自定义 drawio style 覆盖")

    def __init__(self, **data: Any) -> None:
        if data.get("id") is None:
            src = data.get("source", "")
            tgt = data.get("target", "")
            data["id"] = f"e_{src}__{tgt}"
        super().__init__(**data)


class Group(BaseModel):
    """容器/分组 - 如'前端层''后端服务''AWS VPC'"""

    id: str
    label: str
    type: GroupType = GroupType.GENERIC
    parent_id: str | None = Field(None, description="父 group id, 支持嵌套")
    description: str | None = None
    color: str | None = None
    position: Position | None = None
    size: Size | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphIR(BaseModel):
    """完整架构图 IR - 整个 agent 管线的单一数据载体"""

    title: str = "Architecture Diagram"
    architecture_type: ArchitectureType = ArchitectureType.CUSTOM
    description: str | None = None
    groups: list[Group] = Field(default_factory=list)
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ------- 查询帮助 -------

    def node_by_id(self, node_id: str) -> Node | None:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def group_by_id(self, group_id: str) -> Group | None:
        for g in self.groups:
            if g.id == group_id:
                return g
        return None

    def nodes_in_group(self, group_id: str) -> list[Node]:
        return [n for n in self.nodes if n.group_id == group_id]

    def child_groups(self, group_id: str | None) -> list[Group]:
        return [g for g in self.groups if g.parent_id == group_id]

    # ------- 一致性校验 -------

    def validate_integrity(self) -> list[str]:
        """返回所有违反一致性的 error message 列表, 空列表表示 OK"""
        errors: list[str] = []
        node_ids = {n.id for n in self.nodes}
        group_ids = {g.id for g in self.groups}

        if len(node_ids) != len(self.nodes):
            errors.append("存在重复 Node.id")
        if len(group_ids) != len(self.groups):
            errors.append("存在重复 Group.id")

        for n in self.nodes:
            if n.group_id and n.group_id not in group_ids:
                errors.append(f"Node '{n.id}' 引用了不存在的 group '{n.group_id}'")

        for g in self.groups:
            if g.parent_id and g.parent_id not in group_ids:
                errors.append(
                    f"Group '{g.id}' 的 parent '{g.parent_id}' 不存在"
                )
            if g.parent_id == g.id:
                errors.append(f"Group '{g.id}' 不能是自己的父容器")

        for e in self.edges:
            if e.source not in node_ids:
                errors.append(f"Edge {e.id}: source '{e.source}' 不存在")
            if e.target not in node_ids:
                errors.append(f"Edge {e.id}: target '{e.target}' 不存在")

        return errors
