# Contributing to plot-agent

感谢你愿意贡献 plot-agent！本文档说明如何参与开发。

## 本地开发

```bash
git clone https://github.com/LovHan/plot_agent.git
cd plot_agent

# 安装所有依赖 (含 dev)
poetry install --all-extras --with dev

# 激活 virtualenv (可选, poetry run 也行)
poetry shell
```

## 代码风格

- **格式化 & lint**: `ruff`，配置在 `pyproject.toml`
- **类型检查**: `mypy`
- **缩进**: 4 空格
- **行宽**: 100

提交前跑：

```bash
poetry run ruff check plot_agent
poetry run ruff format --check plot_agent
poetry run mypy plot_agent
poetry run pytest
```

## 分支与提交

- 从 `main` 切出 feature/fix 分支，命名 `feat/xxx` / `fix/xxx` / `docs/xxx`
- Commit message 用 [Conventional Commits](https://www.conventionalcommits.org/)：
  - `feat: add ELK layout engine`
  - `fix: handle missing group_id in LocalPlanner`
  - `docs: update README install section`
  - `refactor: extract shape style into registry`
  - `test: add mock test for Reflector early convergence`

## 测试

- **离线测试**（不需要 API key / docker）：`poetry run pytest plot_agent/tests/test_pipeline_offline.py plot_agent/tests/test_reflection_mock.py`
- **端到端测试**（需要 `OPENAI_API_KEY`）：`poetry run plot-agent-eval`

加新功能时请：

1. 若涉及 IR/布局/渲染，加 **offline 单元测试**
2. 若涉及 agent 行为，加 **mock LLM 测试**（参考 `tests/test_reflection_mock.py`）
3. 若改动 prompt，跑一次 `plot-agent-eval` 对比分数

## PR checklist

- [ ] 代码通过 `ruff check` 和 `ruff format --check`
- [ ] `mypy` 无新 error
- [ ] 新增/修改的代码有对应单元测试
- [ ] 若行为可能变化，手动跑 `plot-agent smoke` 确认 drawio 仍可用
- [ ] 更新 README 或 docstring（如适用）
- [ ] 一个 PR 只做一件事

## 加新模板

在 `plot_agent/templates/registry.py` 的 `DEFAULT_TEMPLATES` 里新增一条：

```python
Template(
    name="your_template",
    architecture_type=ArchitectureType.XXX,
    keywords=["关键词1", "keyword2"],
    ir_builder=_your_template_builder,
    description="一句话描述",
    priority=5,
),
```

并在 `plot_agent/data/benchmarks.json` 加一条评测样本验证效果。

## 加新 shape style

在 `plot_agent/render/styles.py` 的 `NODE_STYLE_MAP` / `EDGE_STYLE_MAP` / `GROUP_STYLE_MAP` 加入新类型，同时更新 `plot_agent/ir/models.py` 里对应的 Enum。

## 报告 bug / 提 feature

打开 [GitHub Issues](https://github.com/LovHan/plot_agent/issues)，尽量提供：

- 触发的 prompt 原文
- 生成的 `.ir.json`
- 期望 vs 实际效果（有截图更好）
- Python / poetry / 操作系统版本
