"""MermaidMaker agent: plan + designs -> MermaidIR (structured JSON).

Why an IR instead of emitting Mermaid text directly?
- The IR can be schema-validated, diffed, and reused by other backends (graphviz, excalidraw, ...).
- Text generation lives in ``schemas.MermaidIR.to_mermaid()``, keeping responsibilities single.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from plot_agent.llm import call_structured
from plot_agent.schemas import MermaidIR
from plot_agent.state import MultiAgentState

AGENT_NAME = "mermaid_maker"

SYSTEM_PROMPT = """Convert the plan and component designs into a Mermaid flowchart IR.
The goal is a clean, professional, colour-coded architecture diagram.

### Node modelling
- Each component is one node. Group nodes by owning role via `subgraphs` (e.g. "frontend", "backend", "data", "devops", "security", or "external").
- Put a dedicated "external" subgraph for anything outside the team's control
  (end users, SaaS APIs, partner systems, third-party webhooks).
- `shape`:
    rect     - services / apps / APIs (default)
    round    - end users / actors
    diamond  - decision points / gateways
    cyl      - databases / persistent stores
    cloud    - external / third-party / SaaS systems
- `style_class` (drives colour, pick ONE per node):
    external       - third-party / outside-org systems (CRM, SaaS, partner API, end user)
    internal       - our own services / custom code
    database       - OLTP / OLAP / document stores / lakehouse tables
    cache          - Redis / Memcached / in-memory caches
    queue          - Service Bus / Kafka / Event Grid / SQS
    compute        - hosted compute platforms (Databricks, AKS, Lambda, App Service, Functions)
    secret         - Key Vault / Secrets Manager / IAM / Auth
    observability  - Log Analytics / App Insights / OpenTelemetry / Grafana
    ai             - ML / LLM / model serving / vector DBs
- `icon` (OPTIONAL iconify key; use ONLY for well-known brands, omit otherwise).
  You MUST pick ONLY from this verified whitelist; do NOT invent keys:
    Databases / lake:
      simple-icons:databricks, logos:postgresql, logos:mysql, logos:mongodb,
      logos:redis, logos:snowflake-icon, simple-icons:googlebigquery
    Messaging:
      logos:kafka, logos:rabbitmq
    Compute / container / IaC:
      logos:kubernetes, logos:docker-icon,
      logos:terraform-icon, logos:ansible, logos:helm
    CI / VCS:
      logos:github-actions, logos:gitlab
    Cloud:
      logos:aws, logos:microsoft-azure, logos:google-cloud
    Languages / frameworks:
      logos:python, logos:nodejs-icon, logos:react, logos:vue,
      logos:fastapi-icon, logos:django-icon, logos:nginx
    Analytics / BI / ML:
      logos:microsoft-power-bi, logos:tableau-icon, simple-icons:mlflow
    Observability:
      logos:prometheus, logos:grafana
    SaaS / APIs:
      logos:openai-icon, logos:salesforce, logos:stripe, logos:twilio
  If the brand is not listed, omit `icon`; an uncoloured node with a meaningful
  `style_class` is better than a broken logo.

### Edge modelling
- Derive edges from `interfaces` and `depends_on`; keep the total under ~25.
- `label`: short verb phrase (<= 6 words), e.g. "reads/writes", "publishes event",
  "webhook push", "syncs nightly", "provisions".
- `style`:
    solid   - synchronous / primary data flow (default)
    thick   - critical / high-volume production path
    dashed  - asynchronous / event / webhook / fire-and-forget
    dotted  - logical or optional / future / non-runtime dependency

### Response
Respond with ONLY a single JSON object, NO prose, matching EXACTLY this shape:

{
  "direction": "LR",
  "nodes": [
    {"id": "user",  "label": "End User",    "shape": "round", "style_class": "external"},
    {"id": "fe",    "label": "React SPA",   "shape": "rect",  "style_class": "internal", "icon": "logos:react"},
    {"id": "api",   "label": "FastAPI",     "shape": "rect",  "style_class": "compute",  "icon": "logos:python"},
    {"id": "db",    "label": "PostgreSQL",  "shape": "cyl",   "style_class": "database", "icon": "logos:postgresql"},
    {"id": "bus",   "label": "Service Bus", "shape": "rect",  "style_class": "queue"},
    {"id": "crm",   "label": "Salesforce",  "shape": "cloud", "style_class": "external", "icon": "logos:salesforce"}
  ],
  "edges": [
    {"src": "user", "dst": "fe",  "label": "browses",      "style": "solid"},
    {"src": "fe",   "dst": "api", "label": "REST",         "style": "solid"},
    {"src": "api",  "dst": "db",  "label": "reads/writes", "style": "thick"},
    {"src": "api",  "dst": "bus", "label": "publishes",    "style": "dashed"},
    {"src": "bus",  "dst": "crm", "label": "webhook push", "style": "dashed"}
  ],
  "subgraphs": {
    "external": ["user", "crm"],
    "frontend": ["fe"],
    "backend":  ["api", "bus"],
    "data":     ["db"]
  }
}

Node ids MUST be short alphanumeric identifiers (no spaces, no punctuation).
Prefer 6-12 nodes; avoid duplicating the same concept."""


def mermaid_maker_node(state: MultiAgentState) -> dict[str, Any]:
    plan = state.get("plan", {})
    designs = state.get("designs", {})
    ir = call_structured(
        MermaidIR,
        SYSTEM_PROMPT,
        f"Plan:\n{plan}\n\nDesigns:\n{designs}",
        model_env="PLANNER_MODEL",
    )
    msg = AIMessage(
        content=f"[{AGENT_NAME}] IR ready: {len(ir.nodes)} nodes / {len(ir.edges)} edges",
        name=AGENT_NAME,
    )
    return {
        "mermaid_ir": ir.model_dump(),
        "messages": [msg],
        "trace": [f"{AGENT_NAME}: nodes={len(ir.nodes)} edges={len(ir.edges)}"],
    }
