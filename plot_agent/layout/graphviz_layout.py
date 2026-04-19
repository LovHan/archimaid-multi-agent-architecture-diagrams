"""使用 pygraphviz 的 dot 引擎布局, 支持 cluster 分组

说明:
- 每个 group 渲染为 `cluster_<id>` 子图
- 嵌套 group 通过子图嵌套实现
- 返回的 position 是 node 中心点坐标, size 来自 width/height
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from ..ir import GraphIR, Group, Position, Size
from .base import LayoutEngine, LayoutResult

if TYPE_CHECKING:
    import pygraphviz as pgv  # noqa: F401

DEFAULT_NODE_WIDTH = 140
DEFAULT_NODE_HEIGHT = 60


class GraphvizLayout(LayoutEngine):
    """使用 graphviz dot 布局 (需系统装 graphviz + pygraphviz)"""

    def __init__(self, node_sep: float = 0.5, rank_sep: float = 0.6) -> None:
        self.node_sep = node_sep
        self.rank_sep = rank_sep

    def layout(self, ir: GraphIR, direction: str = "TB") -> LayoutResult:
        try:
            import pygraphviz as pgv
        except ImportError as e:
            raise ImportError(
                "pygraphviz 未安装, 请先安装系统 graphviz (brew install graphviz) "
                "再 pip install pygraphviz; 或使用 SimpleGridLayout"
            ) from e

        G = pgv.AGraph(
            directed=True,
            rankdir=direction,
            nodesep=self.node_sep,
            ranksep=self.rank_sep,
            compound=True,
        )

        # 1. 添加所有 group 为 cluster 子图, 保持嵌套
        cluster_map: dict[str, pgv.AGraph] = {}
        for g in self._topo_sort_groups(ir.groups):
            parent = (
                cluster_map[g.parent_id]
                if g.parent_id and g.parent_id in cluster_map
                else G
            )
            sub = parent.add_subgraph(
                name=f"cluster_{g.id}",
                label=g.label,
                style="rounded,filled",
                fillcolor="#f5f5f5",
                color="#999999",
                fontcolor="#333333",
                fontsize=14,
            )
            cluster_map[g.id] = sub

        # 2. 添加 node 到对应 cluster
        for n in ir.nodes:
            target = cluster_map.get(n.group_id) if n.group_id else G
            if target is None:
                target = G
            target.add_node(
                n.id,
                label=n.label,
                shape="box",
                style="rounded,filled",
                fillcolor="#ffffff",
                width=DEFAULT_NODE_WIDTH / 72,  # graphviz 用英寸
                height=DEFAULT_NODE_HEIGHT / 72,
                fixedsize=True,
            )

        # 3. 添加 edges
        for e in ir.edges:
            G.add_edge(e.source, e.target, label=e.label or "")

        # 4. 执行布局
        G.layout(prog="dot")

        # 5. 读取坐标回填到 IR
        self._extract_positions(G, ir, cluster_map)

        # 6. 估算画布大小
        w, h = self._estimate_canvas(ir)
        return LayoutResult(
            ir=ir, direction=direction, canvas_width=w, canvas_height=h
        )

    @staticmethod
    def _topo_sort_groups(groups: list[Group]) -> list[Group]:
        """保证父 group 在子 group 之前创建"""
        by_id = {g.id: g for g in groups}
        result: list[Group] = []
        visited: set[str] = set()

        def visit(g: Group) -> None:
            if g.id in visited:
                return
            if g.parent_id and g.parent_id in by_id:
                visit(by_id[g.parent_id])
            visited.add(g.id)
            result.append(g)

        for g in groups:
            visit(g)
        return result

    def _extract_positions(
        self,
        G: pgv.AGraph,
        ir: GraphIR,
        cluster_map: dict[str, pgv.AGraph],
    ) -> None:
        for n in ir.nodes:
            try:
                gn = G.get_node(n.id)
                pos_str = gn.attr.get("pos", "")
                if pos_str:
                    x_str, y_str = pos_str.split(",")
                    # graphviz y 轴向上, drawio y 轴向下, 需要翻转
                    n.position = Position(x=float(x_str), y=-float(y_str))
                    n.size = Size(
                        width=DEFAULT_NODE_WIDTH, height=DEFAULT_NODE_HEIGHT
                    )
            except Exception:
                n.position = Position(x=0, y=0)
                n.size = Size(width=DEFAULT_NODE_WIDTH, height=DEFAULT_NODE_HEIGHT)

        # 计算每个 group 的 bounding box
        self._compute_group_bbox(ir)

        # 归一化到正坐标
        self._normalize_coords(ir)

    @staticmethod
    def _compute_group_bbox(ir: GraphIR) -> None:
        """根据 group 内部所有 node 的 position, 估算 group 的 bbox

        为嵌套 group 也要考虑子 group 的 bbox
        """
        padding = 30.0
        header = 30.0  # group label 高度

        # 先统计所有 group 下的 nodes (递归)
        children_of: dict[str, list[str]] = defaultdict(list)
        for g in ir.groups:
            if g.parent_id:
                children_of[g.parent_id].append(g.id)

        def compute(group_id: str) -> tuple[float, float, float, float]:
            """返回 group 的 (min_x, min_y, max_x, max_y)"""
            xs: list[float] = []
            ys: list[float] = []
            for n in ir.nodes_in_group(group_id):
                if n.position and n.size:
                    xs.extend(
                        [
                            n.position.x - n.size.width / 2,
                            n.position.x + n.size.width / 2,
                        ]
                    )
                    ys.extend(
                        [
                            n.position.y - n.size.height / 2,
                            n.position.y + n.size.height / 2,
                        ]
                    )
            for child_id in children_of.get(group_id, []):
                if (bbox := compute(child_id)) is not None:
                    xs.extend([bbox[0], bbox[2]])
                    ys.extend([bbox[1], bbox[3]])

            if not xs or not ys:
                return (0.0, 0.0, 200.0, 100.0)

            min_x, max_x = min(xs) - padding, max(xs) + padding
            min_y, max_y = min(ys) - padding - header, max(ys) + padding
            g_obj = ir.group_by_id(group_id)
            if g_obj:
                g_obj.position = Position(x=min_x, y=min_y)
                g_obj.size = Size(
                    width=max_x - min_x, height=max_y - min_y
                )
            return (min_x, min_y, max_x, max_y)

        # 从叶子往根: 先处理深度最大的
        for g in ir.groups:
            compute(g.id)

    @staticmethod
    def _normalize_coords(ir: GraphIR) -> None:
        """把坐标平移到 (0, 0) 起点"""
        all_x: list[float] = []
        all_y: list[float] = []
        for n in ir.nodes:
            if n.position and n.size:
                all_x.append(n.position.x - n.size.width / 2)
                all_y.append(n.position.y - n.size.height / 2)
        for g in ir.groups:
            if g.position:
                all_x.append(g.position.x)
                all_y.append(g.position.y)

        if not all_x or not all_y:
            return

        min_x = min(all_x)
        min_y = min(all_y)
        offset = 40.0

        dx = -min_x + offset
        dy = -min_y + offset

        for n in ir.nodes:
            if n.position:
                n.position.x += dx
                n.position.y += dy
        for g in ir.groups:
            if g.position:
                g.position.x += dx
                g.position.y += dy

    @staticmethod
    def _estimate_canvas(ir: GraphIR) -> tuple[float, float]:
        max_x = 1200.0
        max_y = 800.0
        for n in ir.nodes:
            if n.position and n.size:
                max_x = max(max_x, n.position.x + n.size.width / 2 + 40)
                max_y = max(max_y, n.position.y + n.size.height / 2 + 40)
        for g in ir.groups:
            if g.position and g.size:
                max_x = max(max_x, g.position.x + g.size.width + 40)
                max_y = max(max_y, g.position.y + g.size.height + 40)
        return max_x, max_y
