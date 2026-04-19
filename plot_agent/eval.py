"""轻量级自动评测脚本

评测指标 (论文多级评测的极简版):
1. integrity: IR 一致性通过率
2. type_coverage: 必需的 node types 都出现
3. node_count_in_range: 节点数在期望区间
4. group_coverage: 必需的 group 都出现 (关键词模糊匹配)
5. architecture_type_match: LLM 识别的架构类型是否正确

用法:
    export OPENAI_API_KEY=sk-xxx
    python -m plot_agent.eval                    # 跑全部 benchmarks
    python -m plot_agent.eval --id web_frontend_backend   # 单条
    python -m plot_agent.eval --no-llm           # 只跑模板命中的样例
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent import ArchitectureAgent
from .ir import GraphIR
from .templates import match_template

BENCH_FILE = Path(__file__).parent / "data" / "benchmarks.json"


@dataclass
class SampleScore:
    sample_id: str
    integrity: float
    type_coverage: float
    node_count_in_range: float
    group_coverage: float
    architecture_type_match: float
    node_count: int
    edge_count: int
    group_count: int
    matched_template: str | None = None

    @property
    def overall(self) -> float:
        return (
            self.integrity
            + self.type_coverage
            + self.node_count_in_range
            + self.group_coverage
            + self.architecture_type_match
        ) / 5.0


def _score_sample(
    sample: dict[str, Any],
    ir: GraphIR,
    matched_template: str | None = None,
) -> SampleScore:
    expected = sample["expected"]

    # 1. integrity
    errs = ir.validate_integrity()
    integrity = 1.0 if not errs else 0.0

    # 2. type coverage
    actual_types = {n.type.value for n in ir.nodes}
    required_types = set(expected.get("required_node_types", []))
    hit = len(required_types & actual_types) / len(required_types) if required_types else 1.0
    type_coverage = hit

    # 3. node count
    n = len(ir.nodes)
    lo = expected.get("min_nodes", 0)
    hi = expected.get("max_nodes", 10_000)
    node_count_in_range = 1.0 if lo <= n <= hi else 0.0

    # 4. group coverage (模糊关键词匹配)
    required_groups = expected.get("required_groups", [])
    if required_groups:
        group_labels = " ".join(g.label for g in ir.groups)
        hits = sum(1 for k in required_groups if k in group_labels)
        group_coverage = hits / len(required_groups)
    else:
        group_coverage = 1.0

    # 5. architecture type match
    exp_type = expected.get("architecture_type")
    archtype_match = (1.0 if ir.architecture_type.value == exp_type else 0.0) if exp_type else 1.0

    return SampleScore(
        sample_id=sample["id"],
        integrity=integrity,
        type_coverage=type_coverage,
        node_count_in_range=node_count_in_range,
        group_coverage=group_coverage,
        architecture_type_match=archtype_match,
        node_count=n,
        edge_count=len(ir.edges),
        group_count=len(ir.groups),
        matched_template=matched_template,
    )


def evaluate(
    sample_id: str | None = None,
    use_llm: bool = True,
    enable_reflection: bool = False,
) -> list[SampleScore]:
    samples: list[dict[str, Any]] = json.loads(BENCH_FILE.read_text("utf-8"))
    if sample_id:
        samples = [s for s in samples if s["id"] == sample_id]

    results: list[SampleScore] = []

    agent = ArchitectureAgent(enable_reflection=enable_reflection) if use_llm else None

    for sample in samples:
        print(f"\n=== {sample['id']} ===")
        print(f"  prompt: {sample['prompt'][:80]}...")

        tpl = match_template(sample["prompt"])
        matched_name = tpl.name if tpl else None

        if use_llm and agent is not None:
            planning, tpl_name = agent.plan_with_template(sample["prompt"])
            ir = planning.ir
            matched_name = tpl_name or matched_name
        elif tpl is not None:
            ir = tpl.ir_builder()
        else:
            print("  [skip] 无 LLM 且无模板命中")
            continue

        score = _score_sample(sample, ir, matched_name)
        results.append(score)

        print(
            f"  nodes={score.node_count} edges={score.edge_count} "
            f"groups={score.group_count} tpl={matched_name}"
        )
        print(
            f"  scores: integrity={score.integrity:.2f} "
            f"type_cov={score.type_coverage:.2f} "
            f"count_ok={score.node_count_in_range:.2f} "
            f"group_cov={score.group_coverage:.2f} "
            f"arch_match={score.architecture_type_match:.2f} "
            f"| overall={score.overall:.2f}"
        )

    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", help="单条样本 id")
    ap.add_argument(
        "--no-llm",
        action="store_true",
        help="仅测试模板命中的样例 (不消耗 API)",
    )
    ap.add_argument(
        "--reflection",
        action="store_true",
        help="启用分层反射 (更慢)",
    )
    args = ap.parse_args()

    results = evaluate(
        sample_id=args.id,
        use_llm=not args.no_llm,
        enable_reflection=args.reflection,
    )

    if not results:
        print("\n(no results)")
        return

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    avg = {
        "integrity": sum(r.integrity for r in results) / len(results),
        "type_coverage": sum(r.type_coverage for r in results) / len(results),
        "node_count_in_range": sum(r.node_count_in_range for r in results)
        / len(results),
        "group_coverage": sum(r.group_coverage for r in results)
        / len(results),
        "architecture_type_match": sum(
            r.architecture_type_match for r in results
        )
        / len(results),
        "overall": sum(r.overall for r in results) / len(results),
    }
    for k, v in avg.items():
        print(f"  {k}: {v:.3f}")


if __name__ == "__main__":
    main()
