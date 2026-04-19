"""IR -> draw.io mxGraph XML 渲染器

坐标处理:
- IR 中 node.position 是**中心点**的绝对坐标
- IR 中 group.position 是**左上角**的绝对坐标
- 渲染时:
  - group 的 mxGeometry 使用绝对坐标 (parent=1)
  - node 在 group 内时, mxGeometry 使用 **相对于 group 左上角** 的左上角坐标
  - 顶层 node (group_id=None) 使用绝对左上角坐标
"""

from __future__ import annotations

import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

from ..ir import Edge, GraphIR, Group, Node
from .styles import edge_style, group_style, node_style


class DrawioRenderer:
    """把 GraphIR 转成 .drawio XML 文件"""

    def __init__(self, page_name: str = "Page-1") -> None:
        self.page_name = page_name

    def render(self, ir: GraphIR) -> str:
        """返回完整的 drawio XML 字符串"""
        mxfile = ET.Element(
            "mxfile",
            {
                "host": "plot_agent",
                "modified": "",
                "agent": "plot_agent",
                "version": "24.0.0",
                "type": "device",
            },
        )
        diagram = ET.SubElement(
            mxfile,
            "diagram",
            {"id": uuid.uuid4().hex[:10], "name": self.page_name},
        )

        model_attrs = {
            "dx": "1200",
            "dy": "800",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": "1600",
            "pageHeight": "1200",
            "math": "0",
            "shadow": "0",
        }
        model = ET.SubElement(diagram, "mxGraphModel", model_attrs)
        root = ET.SubElement(model, "root")

        ET.SubElement(root, "mxCell", {"id": "0"})
        ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

        # 1. 渲染 groups (嵌套顺序: 父先子后)
        group_order = self._topo_sort_groups(ir.groups)
        for g in group_order:
            self._render_group(root, g, ir)

        # 2. 渲染 nodes
        for n in ir.nodes:
            self._render_node(root, n, ir)

        # 3. 渲染 edges
        for e in ir.edges:
            self._render_edge(root, e)

        # Pretty print
        ET.indent(mxfile, space="  ")
        return ET.tostring(mxfile, encoding="unicode", xml_declaration=False)

    def write(self, ir: GraphIR, output_path: str | Path) -> Path:
        """渲染并写入磁盘"""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(ir), encoding="utf-8")
        return path

    # ---------- internals ----------

    @staticmethod
    def _topo_sort_groups(groups: list[Group]) -> list[Group]:
        by_id = {g.id: g for g in groups}
        visited: set[str] = set()
        order: list[Group] = []

        def visit(g: Group) -> None:
            if g.id in visited:
                return
            if g.parent_id and g.parent_id in by_id:
                visit(by_id[g.parent_id])
            visited.add(g.id)
            order.append(g)

        for g in groups:
            visit(g)
        return order

    def _render_group(self, root: ET.Element, g: Group, ir: GraphIR) -> None:
        if g.position is None or g.size is None:
            # 未布局, 跳过或给 fallback
            return

        parent_id = g.parent_id if g.parent_id else "1"
        # 如果 parent 是另一个 group, 使用相对坐标
        if g.parent_id:
            parent = ir.group_by_id(g.parent_id)
            if parent and parent.position:
                x = g.position.x - parent.position.x
                y = g.position.y - parent.position.y
            else:
                x = g.position.x
                y = g.position.y
        else:
            x = g.position.x
            y = g.position.y

        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": g.id,
                "value": g.label,
                "style": group_style(g.type),
                "vertex": "1",
                "parent": parent_id,
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": f"{x:.1f}",
                "y": f"{y:.1f}",
                "width": f"{g.size.width:.1f}",
                "height": f"{g.size.height:.1f}",
                "as": "geometry",
            },
        )

    def _render_node(self, root: ET.Element, n: Node, ir: GraphIR) -> None:
        if n.position is None or n.size is None:
            return

        parent_id = n.group_id if n.group_id else "1"

        # drawio 期望左上角坐标, IR 中 node.position 是中心点
        abs_left = n.position.x - n.size.width / 2
        abs_top = n.position.y - n.size.height / 2

        if n.group_id:
            parent_group = ir.group_by_id(n.group_id)
            if parent_group and parent_group.position:
                x = abs_left - parent_group.position.x
                y = abs_top - parent_group.position.y
            else:
                x = abs_left
                y = abs_top
                parent_id = "1"
        else:
            x = abs_left
            y = abs_top

        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": n.id,
                "value": n.label,
                "style": node_style(n.type),
                "vertex": "1",
                "parent": parent_id,
            },
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {
                "x": f"{x:.1f}",
                "y": f"{y:.1f}",
                "width": f"{n.size.width:.1f}",
                "height": f"{n.size.height:.1f}",
                "as": "geometry",
            },
        )

    @staticmethod
    def _render_edge(root: ET.Element, e: Edge) -> None:
        cell = ET.SubElement(
            root,
            "mxCell",
            {
                "id": e.id or f"e_{e.source}__{e.target}",
                "value": e.label or "",
                "style": e.style or edge_style(e.type),
                "edge": "1",
                "parent": "1",
                "source": e.source,
                "target": e.target,
            },
        )
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})


def render_to_drawio(ir: GraphIR, output_path: str | Path) -> Path:
    """便捷函数"""
    return DrawioRenderer().write(ir, output_path)
