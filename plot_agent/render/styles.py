"""draw.io 样式映射 - 把 NodeType/EdgeType/GroupType 转换为 drawio 内置 style 字符串

参考 https://drawio-app.com/blog/custom-shape-libraries/
"""

from ..ir import EdgeType, GroupType, NodeType

# 基础文本/线颜色
PRIMARY_BLUE = "#1f77b4"
SOFT_BLUE_FILL = "#dae8fc"
SOFT_BLUE_STROKE = "#6c8ebf"
SOFT_GREEN_FILL = "#d5e8d4"
SOFT_GREEN_STROKE = "#82b366"
SOFT_ORANGE_FILL = "#ffe6cc"
SOFT_ORANGE_STROKE = "#d79b00"
SOFT_YELLOW_FILL = "#fff2cc"
SOFT_YELLOW_STROKE = "#d6b656"
SOFT_PURPLE_FILL = "#e1d5e7"
SOFT_PURPLE_STROKE = "#9673a6"
SOFT_GRAY_FILL = "#f5f5f5"
SOFT_GRAY_STROKE = "#666666"
SOFT_RED_FILL = "#f8cecc"
SOFT_RED_STROKE = "#b85450"


def _base(fill: str, stroke: str) -> str:
    return (
        f"rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={fill};strokeColor={stroke};"
        f"fontSize=12;fontColor=#333333;"
    )


NODE_STYLE_MAP: dict[NodeType, str] = {
    NodeType.SERVICE: _base(SOFT_BLUE_FILL, SOFT_BLUE_STROKE),
    NodeType.UI: _base(SOFT_GREEN_FILL, SOFT_GREEN_STROKE),
    NodeType.API: _base(SOFT_BLUE_FILL, SOFT_BLUE_STROKE),
    NodeType.DATABASE: (
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;"
        "backgroundOutline=1;size=15;"
        f"fillColor={SOFT_YELLOW_FILL};strokeColor={SOFT_YELLOW_STROKE};"
        "fontSize=12;fontColor=#333333;"
    ),
    NodeType.CACHE: (
        "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;"
        "backgroundOutline=1;size=15;"
        f"fillColor={SOFT_RED_FILL};strokeColor={SOFT_RED_STROKE};"
        "fontSize=12;fontColor=#333333;"
    ),
    NodeType.QUEUE: (
        "shape=mxgraph.flowchart.manual_input;html=1;whiteSpace=wrap;"
        f"fillColor={SOFT_ORANGE_FILL};strokeColor={SOFT_ORANGE_STROKE};"
        "fontSize=12;"
    ),
    NodeType.STORAGE: (
        "shape=mxgraph.aws4.simple_storage_service;html=1;"
        f"fillColor={SOFT_ORANGE_FILL};strokeColor={SOFT_ORANGE_STROKE};"
        "fontSize=12;verticalLabelPosition=bottom;verticalAlign=top;"
    ),
    NodeType.USER: (
        "shape=umlActor;verticalLabelPosition=bottom;labelBackgroundColor=none;"
        "verticalAlign=top;html=1;outlineConnect=0;"
        f"fillColor={SOFT_GRAY_FILL};strokeColor={SOFT_GRAY_STROKE};"
        "fontSize=12;"
    ),
    NodeType.EXTERNAL: _base(SOFT_GRAY_FILL, SOFT_GRAY_STROKE),
    NodeType.FUNCTION: (
        "rhombus;whiteSpace=wrap;html=1;"
        f"fillColor={SOFT_PURPLE_FILL};strokeColor={SOFT_PURPLE_STROKE};"
        "fontSize=12;"
    ),
    NodeType.CONTAINER: _base(SOFT_BLUE_FILL, SOFT_BLUE_STROKE),
    NodeType.MODEL: _base(SOFT_PURPLE_FILL, SOFT_PURPLE_STROKE),
    NodeType.GATEWAY: (
        "shape=mxgraph.networking.wireless_router;html=1;"
        f"fillColor={SOFT_ORANGE_FILL};strokeColor={SOFT_ORANGE_STROKE};"
        "fontSize=12;verticalLabelPosition=bottom;verticalAlign=top;"
    ),
    NodeType.LOAD_BALANCER: (
        "shape=ellipse;whiteSpace=wrap;html=1;"
        f"fillColor={SOFT_ORANGE_FILL};strokeColor={SOFT_ORANGE_STROKE};"
        "fontSize=12;"
    ),
    NodeType.CDN: (
        "ellipse;whiteSpace=wrap;html=1;"
        f"fillColor={SOFT_GREEN_FILL};strokeColor={SOFT_GREEN_STROKE};"
        "fontSize=12;"
    ),
    NodeType.COMPUTE: _base(SOFT_BLUE_FILL, SOFT_BLUE_STROKE),
    NodeType.NOTE: (
        "shape=note;whiteSpace=wrap;html=1;size=14;"
        f"fillColor={SOFT_YELLOW_FILL};strokeColor={SOFT_YELLOW_STROKE};"
        "fontSize=11;"
    ),
    NodeType.GENERIC: _base("#ffffff", "#999999"),
}


EDGE_STYLE_MAP: dict[EdgeType, str] = {
    EdgeType.SYNC: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;endArrow=classic;endFill=1;"
        "strokeColor=#555555;fontSize=11;"
    ),
    EdgeType.ASYNC: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        "jettySize=auto;html=1;endArrow=open;endFill=0;"
        "dashed=1;strokeColor=#888888;fontSize=11;"
    ),
    EdgeType.DATA_FLOW: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
        "endArrow=block;endFill=1;"
        "strokeColor=#2e7d32;strokeWidth=2;fontSize=11;"
    ),
    EdgeType.DEPENDENCY: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
        "endArrow=open;dashed=1;"
        "strokeColor=#555555;fontSize=11;"
    ),
    EdgeType.INHERITANCE: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
        "endArrow=block;endFill=0;"
        "strokeColor=#555555;fontSize=11;"
    ),
    EdgeType.BIDIRECTIONAL: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
        "endArrow=classic;startArrow=classic;"
        "strokeColor=#555555;fontSize=11;"
    ),
    EdgeType.CONTROL: (
        "edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
        "endArrow=classic;endFill=1;"
        "strokeColor=#b71c1c;strokeWidth=2;fontSize=11;"
    ),
}


GROUP_STYLE_MAP: dict[GroupType, str] = {
    GroupType.LAYER: (
        "rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;"
        "fillColor=#f5f5f5;strokeColor=#666666;fontSize=14;fontStyle=1;"
        "fontColor=#333333;"
    ),
    GroupType.ZONE: (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;"
        "fillColor=#e8f4fd;strokeColor=#1976d2;fontSize=14;fontStyle=1;"
        "fontColor=#0d47a1;dashed=0;"
    ),
    GroupType.CLUSTER: (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;"
        "fillColor=#fff3e0;strokeColor=#ef6c00;fontSize=14;fontStyle=1;"
        "fontColor=#e65100;dashed=1;"
    ),
    GroupType.NAMESPACE: (
        "rounded=0;whiteSpace=wrap;html=1;verticalAlign=top;dashed=1;"
        "fillColor=#f3e5f5;strokeColor=#7b1fa2;fontSize=14;fontStyle=1;"
        "fontColor=#4a148c;"
    ),
    GroupType.VPC: (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;dashed=1;"
        "fillColor=#e8f5e9;strokeColor=#2e7d32;fontSize=14;fontStyle=1;"
        "fontColor=#1b5e20;"
    ),
    GroupType.GENERIC: (
        "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;"
        "fillColor=#fafafa;strokeColor=#999999;fontSize=14;fontStyle=1;"
        "fontColor=#333333;"
    ),
}


def node_style(node_type: NodeType) -> str:
    return NODE_STYLE_MAP.get(node_type, NODE_STYLE_MAP[NodeType.GENERIC])


def edge_style(edge_type: EdgeType) -> str:
    return EDGE_STYLE_MAP.get(edge_type, EDGE_STYLE_MAP[EdgeType.SYNC])


def group_style(group_type: GroupType) -> str:
    return GROUP_STYLE_MAP.get(group_type, GROUP_STYLE_MAP[GroupType.GENERIC])
