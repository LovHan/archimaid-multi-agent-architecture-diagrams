"""离线测试: IR + layout + renderer (不依赖 LLM/docker)

运行: python -m plot_agent.tests.test_pipeline_offline
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from ..examples.manual_ir_smoke import build_sample_ir
from ..layout import SimpleGridLayout
from ..render import DrawioRenderer


def test_ir_integrity() -> None:
    ir = build_sample_ir()
    errs = ir.validate_integrity()
    assert errs == [], f"expected no errors, got {errs}"
    print("  ✓ IR integrity")


def test_simple_layout_fills_positions() -> None:
    ir = build_sample_ir()
    result = SimpleGridLayout().layout(ir)
    for n in ir.nodes:
        assert n.position is not None and n.size is not None, n.id
    for g in ir.groups:
        assert g.position is not None and g.size is not None, g.id
    assert result.canvas_width > 0 and result.canvas_height > 0
    print("  ✓ SimpleGridLayout fills all positions")


def test_render_valid_xml(tmp_path: Path) -> None:
    tmp_file = tmp_path / "render.drawio"
    ir = build_sample_ir()
    SimpleGridLayout().layout(ir)
    DrawioRenderer().write(ir, tmp_file)
    tree = ET.parse(tmp_file)
    root = tree.getroot()
    assert root.tag == "mxfile"
    cells = root.findall(".//mxCell")
    # 2 (0 and 1 baseline) + 4 groups + 9 nodes + 9 edges = 24
    assert len(cells) >= 24, f"got {len(cells)} cells"

    # 每个 node cell 都有 mxGeometry
    for cell in cells:
        if cell.attrib.get("vertex") == "1":
            assert cell.find("mxGeometry") is not None
    print(f"  ✓ DrawioRenderer produced valid XML with {len(cells)} cells")


def test_nested_parents() -> None:
    """node 在 group 内时, parent 应该是 group.id"""
    ir = build_sample_ir()
    SimpleGridLayout().layout(ir)
    xml = DrawioRenderer().render(ir)
    root = ET.fromstring(xml)
    cell = root.find(".//mxCell[@id='redis']")
    assert cell is not None
    assert cell.attrib["parent"] == "data", cell.attrib["parent"]
    print("  ✓ nested parent refs correct")


def run_all() -> None:
    print("Running offline pipeline tests:")
    tmp_dir = Path("out")
    tmp_dir.mkdir(exist_ok=True)
    test_ir_integrity()
    test_simple_layout_fills_positions()
    test_render_valid_xml(tmp_dir)
    test_nested_parents()
    print("\n✓ All offline tests passed")


if __name__ == "__main__":
    run_all()
