from lxml import etree

from netdiagram.ir.models import Diagram, Interface, Link, LinkEndpoint, Metadata, Node
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


def test_each_link_becomes_edge_cell():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router", interfaces=[Interface(id="e0")]),
            Node(id="b", label="b", type="router", interfaces=[Interface(id="e0")]),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a", interface="e0"),
                target=LinkEndpoint(node="b", interface="e0"),
                label="uplink",
            )
        ],
    )
    root = _parse(_render(d))
    edges = [c for c in root.findall(".//mxCell") if c.get("edge") == "1"]
    assert len(edges) == 1
    e = edges[0]
    assert e.get("source") == "node-a"
    assert e.get("target") == "node-b"
    assert e.get("value") == "uplink"


def test_edge_has_interface_labels_as_child_cells():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router", interfaces=[Interface(id="gi0/1")]),
            Node(id="b", label="b", type="router", interfaces=[Interface(id="gi0/2")]),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a", interface="gi0/1"),
                target=LinkEndpoint(node="b", interface="gi0/2"),
            )
        ],
    )
    root = _parse(_render(d))
    edge = next(c for c in root.findall(".//mxCell") if c.get("edge") == "1")
    edge_id = edge.get("id")
    # Interface labels are child cells whose parent is the edge
    label_cells = [c for c in root.findall(".//mxCell") if c.get("parent") == edge_id]
    values = {c.get("value") for c in label_cells}
    assert "gi0/1" in values
    assert "gi0/2" in values


def test_edge_style_reflects_link_style():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[
            Link(source=LinkEndpoint(node="a"), target=LinkEndpoint(node="b"), style="dashed")
        ],
    )
    root = _parse(_render(d))
    edge = next(c for c in root.findall(".//mxCell") if c.get("edge") == "1")
    assert "dashed=1" in (edge.get("style") or "")
