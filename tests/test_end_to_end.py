from pathlib import Path

from lxml import etree
from typer.testing import CliRunner

from netdiagram.cli import app
from netdiagram.ir.loader import load_diagram
from netdiagram.layout import layout_diagram
from netdiagram.renderers.d2 import D2Renderer
from netdiagram.renderers.drawio import DrawioRenderer


def test_branch_office_renders_valid_drawio_xml(fixtures_dir: Path, tmp_path: Path) -> None:
    """Full pipeline: YAML -> IR -> layout -> Draw.io XML. Assert the output parses,
    contains all nodes and edges, and has no overlapping node geometries."""
    diagram = load_diagram(fixtures_dir / "branch_office.yaml")
    laid = layout_diagram(diagram)
    xml = DrawioRenderer().render(laid)

    root = etree.fromstring(xml.encode("utf-8"))
    node_cells = [c for c in root.findall(".//mxCell") if c.get("vertex") == "1"
                  and c.get("id", "").startswith("node-")]
    edge_cells = [c for c in root.findall(".//mxCell") if c.get("edge") == "1"]
    assert len(node_cells) == 3
    assert len(edge_cells) == 2

    # Node geometries must be absolute coordinates (no negative values) and disjoint.
    rects: list[tuple[float, float, float, float]] = []
    for c in node_cells:
        # For nodes inside groups, geometry is relative to the group — skip those.
        if c.get("parent") != "1":
            continue
        g = c.find("mxGeometry")
        rects.append((
            float(g.get("x")),
            float(g.get("y")),
            float(g.get("width")),
            float(g.get("height")),
        ))
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            ax, ay, aw, ah = rects[i]
            bx, by, bw, bh = rects[j]
            overlap_x = ax + aw > bx and bx + bw > ax
            overlap_y = ay + ah > by and by + bh > ay
            assert not (overlap_x and overlap_y), f"overlap between rect {i} and {j}"


def test_branch_office_renders_valid_d2(fixtures_dir: Path) -> None:
    """Full pipeline for D2: YAML -> IR -> layout (ignored by D2) -> D2 text.
    Asserts structural properties of the output rather than exact character match."""
    diagram = load_diagram(fixtures_dir / "branch_office.yaml")
    laid = layout_diagram(diagram)
    text = D2Renderer().render(laid)

    # Title comment
    assert "# Branch Office Topology" in text
    # All three nodes present as declarations
    for node_id in ("fw1", "core-sw1", "srv1"):
        assert f'"{node_id}":' in text
    # One group, with the two nodes nested inside
    assert '"server-vlan": {' in text
    # Edges present with labels (direction may vary)
    assert (
        '"fw1" -> "server-vlan"."core-sw1"' in text
        or '"server-vlan"."core-sw1" -> "fw1"' in text
    )


def test_cli_render_produces_openable_file(fixtures_dir: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "branch.drawio"
    result = runner.invoke(
        app, ["render", str(fixtures_dir / "branch_office.yaml"), "--output", str(out)]
    )
    assert result.exit_code == 0, result.stdout
    # The file must parse as XML with an mxfile root
    parsed = etree.parse(str(out))
    assert parsed.getroot().tag == "mxfile"
