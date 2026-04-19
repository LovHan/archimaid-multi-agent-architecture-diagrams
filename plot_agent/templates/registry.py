"""模板库 (方案 C fallback)

设计:
- 每个模板是一个 GraphIR 骨架 + 一组关键词
- 新 prompt 进来时, 先用关键词匹配, 命中则以该模板为种子调用 LocalPlanner 填充细节
- 未命中则走完整 global planner 流程
"""

from __future__ import annotations

from dataclasses import dataclass
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

TEMPLATES_DIR = Path(__file__).parent / "presets"


@dataclass
class Template:
    name: str
    architecture_type: ArchitectureType
    keywords: list[str]  # 任一命中即匹配
    ir_builder: callable[[], GraphIR]
    description: str = ""
    priority: int = 0  # 高优先级先命中


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: list[Template] = []

    def register(self, tpl: Template) -> None:
        self._templates.append(tpl)
        self._templates.sort(key=lambda t: -t.priority)

    def all(self) -> list[Template]:
        return list(self._templates)

    def match(self, prompt: str) -> Template | None:
        text = prompt.lower()
        for tpl in self._templates:
            if any(k.lower() in text for k in tpl.keywords):
                return tpl
        return None


# ---------------- Preset builders ----------------

def _web_3tier_template() -> GraphIR:
    return GraphIR(
        title="三层 Web 架构",
        architecture_type=ArchitectureType.WEB_3TIER,
        groups=[
            Group(id="presentation", label="展示层", type=GroupType.LAYER),
            Group(id="business", label="业务逻辑层", type=GroupType.LAYER),
            Group(id="persistence", label="数据持久层", type=GroupType.LAYER),
        ],
        nodes=[
            Node(id="user", label="用户", type=NodeType.USER),
            Node(id="web_ui", label="Web UI", type=NodeType.UI, group_id="presentation"),
            Node(id="app_server", label="应用服务器", type=NodeType.SERVICE, group_id="business"),
            Node(id="db", label="数据库", type=NodeType.DATABASE, group_id="persistence"),
        ],
        edges=[
            Edge(source="user", target="web_ui", label="访问"),
            Edge(source="web_ui", target="app_server", label="HTTP"),
            Edge(source="app_server", target="db", label="SQL", type=EdgeType.DATA_FLOW),
        ],
    )


def _microservices_template() -> GraphIR:
    return GraphIR(
        title="微服务架构",
        architecture_type=ArchitectureType.MICROSERVICES,
        groups=[
            Group(id="client", label="客户端", type=GroupType.LAYER),
            Group(id="edge", label="边缘层", type=GroupType.LAYER),
            Group(id="services", label="业务服务", type=GroupType.CLUSTER),
            Group(id="data", label="数据存储", type=GroupType.LAYER),
        ],
        nodes=[
            Node(id="web_client", label="Web Client", type=NodeType.UI, group_id="client"),
            Node(id="mobile_client", label="Mobile Client", type=NodeType.UI, group_id="client"),
            Node(id="api_gateway", label="API Gateway", type=NodeType.GATEWAY, group_id="edge"),
            Node(id="service_a", label="Service A", type=NodeType.SERVICE, group_id="services"),
            Node(id="service_b", label="Service B", type=NodeType.SERVICE, group_id="services"),
            Node(id="service_c", label="Service C", type=NodeType.SERVICE, group_id="services"),
            Node(id="db_a", label="DB A", type=NodeType.DATABASE, group_id="data"),
            Node(id="db_b", label="DB B", type=NodeType.DATABASE, group_id="data"),
            Node(id="mq", label="Message Queue", type=NodeType.QUEUE, group_id="services"),
        ],
        edges=[
            Edge(source="web_client", target="api_gateway", label="HTTPS"),
            Edge(source="mobile_client", target="api_gateway", label="HTTPS"),
            Edge(source="api_gateway", target="service_a", label="路由"),
            Edge(source="api_gateway", target="service_b", label="路由"),
            Edge(source="api_gateway", target="service_c", label="路由"),
            Edge(source="service_a", target="db_a", type=EdgeType.DATA_FLOW),
            Edge(source="service_b", target="db_b", type=EdgeType.DATA_FLOW),
            Edge(source="service_a", target="mq", label="publish", type=EdgeType.ASYNC),
            Edge(source="mq", target="service_c", label="consume", type=EdgeType.ASYNC),
        ],
    )


def _rag_template() -> GraphIR:
    return GraphIR(
        title="RAG 系统架构",
        architecture_type=ArchitectureType.RAG,
        groups=[
            Group(id="ingestion", label="文档摄入", type=GroupType.LAYER),
            Group(id="retrieval", label="检索", type=GroupType.LAYER),
            Group(id="generation", label="生成", type=GroupType.LAYER),
            Group(id="serving", label="服务层", type=GroupType.LAYER),
        ],
        nodes=[
            Node(id="docs", label="文档源", type=NodeType.STORAGE, group_id="ingestion"),
            Node(id="chunker", label="切片器", type=NodeType.FUNCTION, group_id="ingestion"),
            Node(id="embedder", label="Embedding Model", type=NodeType.MODEL, group_id="ingestion"),
            Node(id="vector_db", label="Vector DB", type=NodeType.DATABASE, group_id="retrieval"),
            Node(id="retriever", label="Retriever", type=NodeType.SERVICE, group_id="retrieval"),
            Node(id="reranker", label="Reranker", type=NodeType.MODEL, group_id="retrieval"),
            Node(id="llm", label="LLM", type=NodeType.MODEL, group_id="generation"),
            Node(id="prompt_builder", label="Prompt Builder", type=NodeType.SERVICE, group_id="generation"),
            Node(id="api", label="API", type=NodeType.API, group_id="serving"),
            Node(id="user", label="用户"),
        ],
        edges=[
            Edge(source="docs", target="chunker", type=EdgeType.DATA_FLOW),
            Edge(source="chunker", target="embedder", type=EdgeType.DATA_FLOW),
            Edge(source="embedder", target="vector_db", type=EdgeType.DATA_FLOW, label="索引"),
            Edge(source="user", target="api", label="query"),
            Edge(source="api", target="retriever"),
            Edge(source="retriever", target="vector_db", label="相似搜索"),
            Edge(source="retriever", target="reranker"),
            Edge(source="reranker", target="prompt_builder"),
            Edge(source="prompt_builder", target="llm"),
            Edge(source="llm", target="api", label="answer"),
        ],
    )


def _data_pipeline_template() -> GraphIR:
    return GraphIR(
        title="数据流水线",
        architecture_type=ArchitectureType.DATA_PIPELINE,
        groups=[
            Group(id="sources", label="数据源", type=GroupType.LAYER),
            Group(id="ingestion", label="采集", type=GroupType.LAYER),
            Group(id="processing", label="处理", type=GroupType.LAYER),
            Group(id="storage", label="存储", type=GroupType.LAYER),
            Group(id="consumers", label="消费方", type=GroupType.LAYER),
        ],
        nodes=[
            Node(id="app_logs", label="应用日志", type=NodeType.EXTERNAL, group_id="sources"),
            Node(id="db_source", label="业务数据库", type=NodeType.DATABASE, group_id="sources"),
            Node(id="kafka", label="Kafka", type=NodeType.QUEUE, group_id="ingestion"),
            Node(id="spark", label="Spark", type=NodeType.SERVICE, group_id="processing"),
            Node(id="dwh", label="数据仓库", type=NodeType.DATABASE, group_id="storage"),
            Node(id="lake", label="数据湖", type=NodeType.STORAGE, group_id="storage"),
            Node(id="bi", label="BI 看板", type=NodeType.UI, group_id="consumers"),
            Node(id="ml", label="ML 训练", type=NodeType.SERVICE, group_id="consumers"),
        ],
        edges=[
            Edge(source="app_logs", target="kafka", type=EdgeType.DATA_FLOW),
            Edge(source="db_source", target="kafka", type=EdgeType.DATA_FLOW, label="CDC"),
            Edge(source="kafka", target="spark", type=EdgeType.DATA_FLOW),
            Edge(source="spark", target="dwh", type=EdgeType.DATA_FLOW),
            Edge(source="spark", target="lake", type=EdgeType.DATA_FLOW),
            Edge(source="dwh", target="bi"),
            Edge(source="lake", target="ml"),
        ],
    )


def _frontend_backend_template() -> GraphIR:
    from ..examples.manual_ir_smoke import build_sample_ir

    return build_sample_ir()


DEFAULT_TEMPLATES: list[Template] = [
    Template(
        name="web_3tier",
        architecture_type=ArchitectureType.WEB_3TIER,
        keywords=["三层架构", "3层架构", "3-tier", "three tier", "展示层", "表现层"],
        ir_builder=_web_3tier_template,
        description="经典 3-tier: 展示/业务/持久",
        priority=5,
    ),
    Template(
        name="microservices",
        architecture_type=ArchitectureType.MICROSERVICES,
        keywords=["微服务", "microservice", "microservices"],
        ir_builder=_microservices_template,
        description="API Gateway + 多个业务服务 + 数据存储 + MQ",
        priority=8,
    ),
    Template(
        name="rag",
        architecture_type=ArchitectureType.RAG,
        keywords=["RAG", "检索增强", "retrieval augmented", "向量数据库", "vector db"],
        ir_builder=_rag_template,
        description="RAG: 摄入 → 向量检索 → 生成",
        priority=9,
    ),
    Template(
        name="data_pipeline",
        architecture_type=ArchitectureType.DATA_PIPELINE,
        keywords=["数据流水线", "ETL", "数据管道", "data pipeline", "kafka", "数据仓库", "数据湖"],
        ir_builder=_data_pipeline_template,
        description="源 → 消息队列 → 处理 → 仓库/湖 → BI/ML",
        priority=7,
    ),
    Template(
        name="frontend_backend",
        architecture_type=ArchitectureType.FRONTEND_BACKEND,
        keywords=["前后端分离", "SPA", "单页应用", "React", "Vue", "Angular"],
        ir_builder=_frontend_backend_template,
        description="React SPA + API + Redis + MySQL",
        priority=6,
    ),
]


def get_default_registry() -> TemplateRegistry:
    r = TemplateRegistry()
    for t in DEFAULT_TEMPLATES:
        r.register(t)
    return r


def match_template(prompt: str) -> Template | None:
    return get_default_registry().match(prompt)
