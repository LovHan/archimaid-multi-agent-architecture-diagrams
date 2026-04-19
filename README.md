# plot-agent

> 用自然语言生成可编辑的架构图（draw.io）。把"一段话 → 分层 Agent 规划 → Graph IR → 自动布局 → draw.io XML → VLM 反射迭代"整条链路封装成一个 Python 包和 MCP server。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

中文 / [English](#english)

---

## 为什么又一个"AI 画图"项目

大部分 LLM 画图方案让模型**直接输出最终产物**（HTML/SVG/mxGraph XML），模型同时要背"规划 + 坐标 + 样式"，错误累积严重，一旦某个 `parent` 或 `<mxGeometry>` 漏了整张图就崩。

本项目参考 **MM-WebAgent**（*A Hierarchical Multimodal Web Agent for Webpage Generation*）的思路，做了四个改动：

1. **分层规划**：`TaskPlanner` 识别架构类型 → `GlobalPlanner` 输出顶层容器 + 约束 → `LocalPlanner` 填充节点和边
2. **Graph IR 解耦**：LLM 唯一产物是一个结构化 `GraphIR`（pydantic），**不处理像素坐标**
3. **自动布局**：坐标交给 Graphviz（dot 引擎）或简易网格算，LLM 不管
4. **分层反射**：`LocalCritic` / `ContextCritic` / `GlobalCritic` 三个 VLM 分别检查单点 / 容器内 / 全局，`Refiner` 改 IR，最多 3 轮收敛

论文消融实验显示这条管线把整体质量从 0.42 提到 0.75。

---

## 特性

- **端到端自然语言 → .drawio**：一句话出可编辑架构图
- **三层规划 + 三层反射**：每层职责单一，LLM 不 overload
- **布局自动化**：Graphviz dot 引擎优先，纯 Python `SimpleGridLayout` 作为 fallback，**不装 graphviz 也能跑**
- **draw.io 原生**：直接输出 mxGraph XML，拖进 [app.diagrams.net](https://app.diagrams.net/) 或 draw.io desktop 即可二次编辑
- **PNG 预览**：自动调本地 `draw.io.app` 或 `drawio-desktop-headless` Docker
- **MCP Server**：暴露 `generate_diagram` / `plan_architecture` / `refine_diagram` 等工具，Cursor/Claude Desktop/任何 MCP 客户端可直接调用
- **模板 fallback**：5 个内置架构模板（web_3tier / microservices / rag / data_pipeline / frontend_backend），命中关键词时跳过规划加速
- **类型安全**：全程 pydantic 模型 + `validate_integrity()` 自动修复悬挂引用

---

## 快速开始

### 安装

```bash
# 克隆
git clone https://github.com/LovHan/plot_agent.git
cd plot_agent

# 只装核心 (能跑 SimpleGridLayout fallback)
poetry install

# 推荐: 装所有可选依赖 (graphviz + mcp)
poetry install --all-extras
```

#### 可选依赖说明

| extra       | 命令                                  | 作用                           |
| ----------- | ------------------------------------- | ------------------------------ |
| `graphviz`  | `poetry install -E graphviz`          | 启用 Graphviz dot 自动布局     |
| `mcp`       | `poetry install -E mcp`               | 启用 MCP server 给 Cursor 用   |
| `all`       | `poetry install --all-extras`         | 全部                           |

**`pygraphviz` 需要系统 graphviz 库**：

```bash
# macOS
brew install graphviz

# Ubuntu / Debian
sudo apt-get install graphviz graphviz-dev

# 或 conda 用户最省事 (自带预编译)
conda install -c conda-forge pygraphviz
```

若 `pygraphviz` 安装失败也没关系，项目会自动 fallback 到 `SimpleGridLayout`。

### 配置 API Key

```bash
cp .env.example .env
# 编辑 .env, 填入:
#   OPENAI_API_KEY=sk-xxx
#   PLANNER_MODEL=gpt-4o
#   VLM_MODEL=gpt-4o
```

支持任何 OpenAI 兼容 API（Azure / DeepSeek / Moonshot / Claude via OpenAI proxy 等），通过 `OPENAI_BASE_URL` 指定。

### 跑 smoke test（不需要 API key）

```bash
poetry run plot-agent smoke
# 输出: out/manual_smoke.drawio (拖到 drawio 里看效果)
```

### 生成第一张图

```bash
poetry run plot-agent generate \
  "前后端分离 Web: React SPA 通过 Nginx 走 Python Flask API, Redis 缓存, MySQL 持久化" \
  --name my_first_diagram
```

启用分层反射（更慢但质量更高）：

```bash
poetry run plot-agent generate "<prompt>" --reflection --max-rounds 3
```

### 检测环境

```bash
poetry run plot-agent env
```

会打印 API key / 布局引擎 / PNG 导出后端是否就绪。

---

## Python API

```python
from plot_agent.agent import ArchitectureAgent

agent = ArchitectureAgent(enable_reflection=True, max_reflection_rounds=3)

result = agent.generate(
    prompt="微服务架构: API Gateway 接前端, 路由到用户/订单/支付服务, 各自有独立数据库, 用 Kafka 异步通信",
    output_dir="out",
    name="microservices_demo",
    direction="TB",  # TB / LR / BT / RL
)

print(result.drawio_path)       # ./out/microservices_demo.drawio
print(result.png_path)          # ./out/microservices_demo.png
print(len(result.ir.nodes))     # 节点数
print(result.reflection_rounds) # 实际反射轮数
```

### 直接操作 IR

```python
from plot_agent.ir import GraphIR, Node, Edge, Group, NodeType, EdgeType, GroupType
from plot_agent.layout import get_layout_engine
from plot_agent.render import DrawioRenderer

ir = GraphIR(
    title="Demo",
    groups=[Group(id="backend", label="后端", type=GroupType.LAYER)],
    nodes=[
        Node(id="api", label="API", type=NodeType.API, group_id="backend"),
        Node(id="db", label="PostgreSQL", type=NodeType.DATABASE, group_id="backend"),
    ],
    edges=[Edge(source="api", target="db", label="SQL", type=EdgeType.DATA_FLOW)],
)
get_layout_engine().layout(ir)
DrawioRenderer().write(ir, "out/manual.drawio")
```

---

## MCP Server (Cursor / Claude Desktop 集成)

启动 server：

```bash
poetry run plot-agent-mcp
```

在 Cursor 的 `~/.cursor/mcp.json` 添加：

```json
{
  "mcpServers": {
    "plot_agent": {
      "command": "poetry",
      "args": ["run", "plot-agent-mcp"],
      "cwd": "/path/to/plot-agent",
      "env": {
        "OPENAI_API_KEY": "sk-xxx"
      }
    }
  }
}
```

重启 Cursor 后即可：

> @plot_agent 帮我画一个 Kubernetes 集群架构, 一个 VPC 里两个 namespace，前端 nginx+react，后端 python-api + postgres

### 暴露的 tools

| Tool                 | 功能                                   |
| -------------------- | -------------------------------------- |
| `generate_diagram`   | NL → .drawio + PNG + IR                |
| `plan_architecture`  | 只规划不渲染，返回结构化 IR JSON       |
| `refine_diagram`     | 基于已有 IR + 人类反馈再改一版         |
| `render_ir`          | 直接把 IR JSON 渲染成 drawio，不走 LLM |
| `check_environment`  | 检测 API key / 布局 / PNG 后端状态     |

---

## 项目结构

```
plot_agent/
├── agent.py              顶层 ArchitectureAgent
├── cli.py                CLI 入口
├── llm.py                OpenAI 兼容客户端 (chat / json / vlm)
├── eval.py               自动评测脚本
├── shape_registry.json   drawio shape 白名单 (给 LLM)
├── ir/                   GraphIR pydantic 模型
├── planners/             task / global / local 三层规划
├── layout/               graphviz + simple_grid + factory
├── render/               drawio_renderer + png_exporter + styles
├── critic/               local / context / global critic (VLM)
├── refiner/              Refiner + Reflector (3 轮反射)
├── mcp_server/           MCP server
├── templates/            5 个内置架构模板
├── prompts/              各阶段 prompt 模板
├── examples/             手工 IR + 端到端 demo
├── data/                 benchmark 数据集
└── tests/                offline pipeline + reflection mock
```

---

## 架构概览

```
用户自然语言
    ↓
[Task Planner]     识别架构类型 (微服务/RAG/数据流水线/...)
    ↓
[Global Planner]   规划顶层容器 (前端层/后端/数据层) + 每容器约束
    ↓
[Local Planner]    填充节点 + 边 (含跨容器连接)
    ↓
[GraphIR]  ← agent 唯一产物 (pydantic, 类型安全)
    ↓
[Auto Layout]      Graphviz dot 或 SimpleGrid 填充坐标
    ↓
[DrawioRenderer]   IR → mxGraph XML
    ↓
[PngExporter]      drawio → PNG (本地 app / docker headless)
    ↓
[Hierarchical Critic]  VLM 看 PNG+IR, 三层反馈
    ├─ Local      单点错误 (type 错、缺节点)
    ├─ Context    容器内/跨容器 (放错容器、连线缺失)
    └─ Global     整体 (布局方向、风格一致性、美学)
    ↓
[Refiner]          改 IR, 最多 3 轮
    ↓
最终: .drawio + .png + .ir.json
```

---

## 评测

内置 6 个 benchmark，覆盖 web_3tier / microservices / rag / data_pipeline / serverless / k8s：

```bash
# 不消耗 API (只跑模板命中样例)
poetry run plot-agent-eval --no-llm

# 完整 LLM 评测
poetry run plot-agent-eval

# 单条
poetry run plot-agent-eval --id rag_chatbot
```

打分维度：`integrity` / `type_coverage` / `node_count_in_range` / `group_coverage` / `architecture_type_match`，各维度归一化后求均值。

---

## 开发

```bash
# 装开发依赖
poetry install --all-extras --with dev

# 格式化 + lint
poetry run ruff check plot_agent
poetry run ruff format plot_agent

# 类型检查
poetry run mypy plot_agent

# 跑测试
poetry run pytest
```

---

## 路线图

- [ ] 方案 B baseline：LLM 直出 XML 对比，量化 IR 解耦的增益
- [ ] 扩充模板到 20+（Lambda / ETL / Event-driven / AWS / GCP / Azure 典型）
- [ ] shape registry 对接 AWS/Azure/GCP 官方图标包
- [ ] 支持 ELK 布局引擎（复杂图的替代）
- [ ] 支持 mermaid / plantuml 作为输出目标
- [ ] 增量 refine（人类框选某区域 + 反馈，只改那部分）

---

## 参考文献

本项目借鉴 **MM-WebAgent: A Hierarchical Multimodal Web Agent for Webpage Generation** 的架构思想，特别是：

- §3.1 Hierarchical Planning and Generation（分层规划）
- §3.2 Hierarchical Self Reflection（三层反射）
- Table 3B / Table 4 消融实验
- Appendix B.1 Planner Prompt

---

## License

MIT © plot-agent contributors

---

## Contributing

欢迎 issue 和 PR。贡献前请看 [CONTRIBUTING.md](./CONTRIBUTING.md)。

---

<a name="english"></a>
## English (TL;DR)

`plot-agent` turns a natural-language description of a system architecture into an editable draw.io diagram. Inspired by **MM-WebAgent**, it uses **hierarchical planning** (task / global / local) + an explicit **Graph IR** (pydantic) + **automatic layout** (Graphviz) + **hierarchical self-reflection** (local / context / global VLM critics) to iteratively refine the diagram, instead of asking a single LLM to emit raw XML.

```bash
poetry install --all-extras
cp .env.example .env  # set OPENAI_API_KEY
poetry run plot-agent generate "microservices with API gateway, order service, payment service, MySQL, Kafka"
```

Outputs `.drawio` + `.png` + `.ir.json`. Also available as an MCP server for Cursor / Claude Desktop.
