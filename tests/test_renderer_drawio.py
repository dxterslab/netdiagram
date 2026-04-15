from lxml import etree

from netdiagram.ir.models import Diagram, Metadata, Node
from netdiagram.layout import layout_diagram
from netdiagram.renderers.drawio import DrawioRenderer


def _render(diagram: Diagram) -> str:
    return DrawioRenderer().render(layout_diagram(diagram))


def _parse(xml: str) -> etree._Element:
    return etree.fromstring(xml.encode("utf-8"))


def test_renders_valid_drawio_xml():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="a", label="a", type="router")],
    )
    xml = _render(d)
    root = _parse(xml)
    assert root.tag == "mxfile"
    # Must contain a diagram element
    assert root.find("diagram") is not None


def test_each_node_becomes_mxcell():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="switch"),
        ],
    )
    root = _parse(_render(d))
    cells = root.findall(".//mxCell")
    node_cells = [c for c in cells if c.get("vertex") == "1"]
    assert len(node_cells) == 2
    values = {c.get("value") for c in node_cells}
    assert values == {"a", "b"}


def test_node_type_determines_shape_style():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="r1", label="r1", type="router")],
    )
    root = _parse(_render(d))
    cell = next(c for c in root.findall(".//mxCell") if c.get("value") == "r1")
    style = cell.get("style") or ""
    # Style string should include "router" somewhere (via shape= attribute)
    assert "router" in style.lower()


def test_node_geometry_uses_layout_coordinates():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="a", label="a", type="router")],
    )
    root = _parse(_render(d))
    cell = next(c for c in root.findall(".//mxCell") if c.get("value") == "a")
    geom = cell.find("mxGeometry")
    assert geom is not None
    assert float(geom.get("width")) > 0
    assert float(geom.get("height")) > 0
