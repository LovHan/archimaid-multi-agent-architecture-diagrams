"""简易网格布局 - 无依赖 fallback

策略:
1. 容器按 direction (TB/LR) 依次排列
2. 每个容器内部的 node 网格排列 (每行 4 个)
3. 嵌套容器暂不支持, 统一拍扁到顶层
"""

from __future__ import annotations

from ..ir import GraphIR, Position, Size
from .base import LayoutEngine, LayoutResult

NODE_W = 160.0
NODE_H = 60.0
NODE_GAP_X = 40.0
NODE_GAP_Y = 40.0
GROUP_PAD = 30.0
GROUP_HEADER = 30.0
GROUP_GAP = 60.0
CANVAS_MARGIN = 40.0


class SimpleGridLayout(LayoutEngine):
    def __init__(self, nodes_per_row: int = 4) -> None:
        self.nodes_per_row = nodes_per_row

    def layout(self, ir: GraphIR, direction: str = "TB") -> LayoutResult:
        # 顶层 groups (parent_id 为 None)
        top_groups = [g for g in ir.groups if not g.parent_id]
        orphan_nodes = [n for n in ir.nodes if not n.group_id]

        cursor_x = CANVAS_MARGIN
        cursor_y = CANVAS_MARGIN
        max_x = cursor_x
        max_y = cursor_y

        for g in top_groups:
            w, h = self._layout_group(ir, g.id, cursor_x, cursor_y)
            g_obj = ir.group_by_id(g.id)
            if g_obj:
                g_obj.position = Position(x=cursor_x, y=cursor_y)
                g_obj.size = Size(width=w, height=h)

            if direction in ("TB", "BT"):
                cursor_y += h + GROUP_GAP
                max_x = max(max_x, cursor_x + w)
                max_y = cursor_y
            else:  # LR / RL
                cursor_x += w + GROUP_GAP
                max_x = cursor_x
                max_y = max(max_y, cursor_y + h)

        # 孤儿节点放在下方
        if orphan_nodes:
            if direction in ("TB", "BT"):
                row_x = CANVAS_MARGIN
                row_y = max_y + GROUP_GAP
            else:
                row_x = max_x + GROUP_GAP
                row_y = CANVAS_MARGIN

            for i, n in enumerate(orphan_nodes):
                col = i % self.nodes_per_row
                row = i // self.nodes_per_row
                x = row_x + col * (NODE_W + NODE_GAP_X) + NODE_W / 2
                y = row_y + row * (NODE_H + NODE_GAP_Y) + NODE_H / 2
                n.position = Position(x=x, y=y)
                n.size = Size(width=NODE_W, height=NODE_H)
                max_x = max(max_x, x + NODE_W / 2 + CANVAS_MARGIN)
                max_y = max(max_y, y + NODE_H / 2 + CANVAS_MARGIN)

        return LayoutResult(
            ir=ir,
            direction=direction,
            canvas_width=max_x + CANVAS_MARGIN,
            canvas_height=max_y + CANVAS_MARGIN,
        )

    def _layout_group(
        self,
        ir: GraphIR,
        group_id: str,
        origin_x: float,
        origin_y: float,
    ) -> tuple[float, float]:
        """把该 group 内的 nodes + 子 group 网格排布, 返回 (width, height)"""
        nodes = ir.nodes_in_group(group_id)
        child_groups = ir.child_groups(group_id)

        inner_x = origin_x + GROUP_PAD
        inner_y = origin_y + GROUP_PAD + GROUP_HEADER

        cur_x = inner_x
        cur_y = inner_y

        # 排 nodes (网格)
        for i, n in enumerate(nodes):
            col = i % self.nodes_per_row
            row = i // self.nodes_per_row
            x = inner_x + col * (NODE_W + NODE_GAP_X) + NODE_W / 2
            y = inner_y + row * (NODE_H + NODE_GAP_Y) + NODE_H / 2
            n.position = Position(x=x, y=y)
            n.size = Size(width=NODE_W, height=NODE_H)
            cur_x = max(cur_x, x + NODE_W / 2)
            cur_y = max(cur_y, y + NODE_H / 2)

        # 排子容器 (放在 nodes 下方)
        next_y = cur_y + NODE_GAP_Y if nodes else inner_y
        for cg in child_groups:
            sub_w, sub_h = self._layout_group(ir, cg.id, inner_x, next_y)
            cg_obj = ir.group_by_id(cg.id)
            if cg_obj:
                cg_obj.position = Position(x=inner_x, y=next_y)
                cg_obj.size = Size(width=sub_w, height=sub_h)
            next_y += sub_h + GROUP_GAP / 2
            cur_x = max(cur_x, inner_x + sub_w)
            cur_y = max(cur_y, next_y)

        width = max(cur_x - origin_x + GROUP_PAD, 200.0)
        height = max(cur_y - origin_y + GROUP_PAD, 100.0)
        return width, height
