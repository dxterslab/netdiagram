"""D2 renderer tests. D2 is text-based, so tests assert substring presence rather
than structure-parsing like the drawio tests do."""

from netdiagram.ir.models import Diagram, Interface, Link, LinkEndpoint, Metadata, Node
from netdiagram.layout import layout_diagram
from netdiagram.renderers.d2 import D2Renderer


def _render(diagram: Diagram) -> str:
    return D2Renderer().render(layout_diagram(diagram))


def test_renders_title_as_comment():
    d = Diagram(
        metadata=Metadata(title="Test Topology", type="physical"),
        nodes=[Node(id="r1", label="r1", type="router")],
    )
    out = _render(d)
    assert "# Test Topology" in out


def test_each_node_becomes_declaration_block():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="r1", label="Router One", type="router"),
            Node(id="s1", label="Switch One", type="switch"),
        ],
    )
    out = _render(d)
    # Each node declared as: "<id>": { ... } with label inside
    assert '"r1": {' in out
    assert '"s1": {' in out
    assert 'label: "Router One"' in out
    assert 'label: "Switch One"' in out


def test_node_type_maps_to_d2_shape():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="r1", label="r1", type="router"),
            Node(id="fw", label="fw", type="firewall"),
            Node(id="s1", label="s1", type="server"),
            Node(id="c1", label="c1", type="vpc"),
        ],
    )
    out = _render(d)
    # Routers render as hexagons, firewalls as diamonds, servers as rectangles,
    # VPCs as clouds. These mappings are chosen for D2's built-in shape set.
    assert "shape: hexagon" in out
    assert "shape: diamond" in out
    assert "shape: rectangle" in out
    assert "shape: cloud" in out


def test_ids_with_special_characters_are_quoted():
    # Hyphens are allowed in D2 but we quote everything for consistency
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="core-sw-01", label="core-sw-01", type="switch")],
    )
    out = _render(d)
    assert '"core-sw-01"' in out


def test_single_ungrouped_node_renders():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="only", label="only", type="generic")],
    )
    out = _render(d)
    assert '"only": {' in out
    assert "shape: rectangle" in out  # generic falls back to rectangle


def test_each_link_becomes_edge():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a"),
                target=LinkEndpoint(node="b"),
                label="uplink",
            )
        ],
    )
    out = _render(d)
    assert '"a" -> "b": "uplink"' in out


def test_edge_without_label_omits_label():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[Link(source=LinkEndpoint(node="a"), target=LinkEndpoint(node="b"))],
    )
    out = _render(d)
    assert '"a" -> "b"' in out
    # Must not add a stray empty-string label like `"a" -> "b": ""`
    assert '"a" -> "b": ""' not in out


def test_dashed_style_sets_stroke_dash():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a"),
                target=LinkEndpoint(node="b"),
                style="dashed",
            )
        ],
    )
    out = _render(d)
    assert "style.stroke-dash: 5" in out


def test_dotted_style_sets_smaller_dash():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a"),
                target=LinkEndpoint(node="b"),
                style="dotted",
            )
        ],
    )
    out = _render(d)
    assert "style.stroke-dash: 2" in out


def test_interface_labels_become_arrowhead_labels():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(
                id="a",
                label="a",
                type="router",
                interfaces=[Interface(id="gi0/1")],
            ),
            Node(
                id="b",
                label="b",
                type="router",
                interfaces=[Interface(id="gi0/2")],
            ),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a", interface="gi0/1"),
                target=LinkEndpoint(node="b", interface="gi0/2"),
            )
        ],
    )
    out = _render(d)
    # D2 uses source-arrowhead.label and target-arrowhead.label for port annotations
    assert 'source-arrowhead.label: "gi0/1"' in out
    assert 'target-arrowhead.label: "gi0/2"' in out
