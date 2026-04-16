"""D2 renderer tests. D2 is text-based, so tests assert substring presence rather
than structure-parsing like the drawio tests do."""

from netdiagram.ir.models import Diagram, Group, Interface, Link, LinkEndpoint, Metadata, Node
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


def test_interface_labels_consolidated_into_edge_label():
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
    # Interface names are consolidated into the edge label (no separate arrowhead labels)
    assert "gi0/1" in out
    assert "gi0/2" in out
    assert '"a" -> "b": "gi0/1' in out  # both in a single label string


def test_group_containing_nodes_becomes_nested_container():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[Group(id="vlan100", label="VLAN 100", type="vlan")],
        nodes=[
            Node(id="sw1", label="sw1", type="switch", group="vlan100"),
            Node(id="sw2", label="sw2", type="switch", group="vlan100"),
        ],
    )
    out = _render(d)
    # Group declared as container
    assert '"vlan100": {' in out
    # Group has its label
    assert 'label: "VLAN 100"' in out
    # Member nodes appear nested inside (indented)
    assert '  "sw1": {' in out
    assert '  "sw2": {' in out


def test_nested_groups_produce_nested_containers():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[
            Group(id="vpc1", label="VPC 1", type="vpc"),
            Group(id="subnet1", label="Subnet", type="subnet", parent="vpc1"),
        ],
        nodes=[Node(id="srv", label="srv", type="server", group="subnet1")],
    )
    out = _render(d)
    # Outer VPC, inner subnet, server inside the subnet
    assert '"vpc1": {' in out
    assert '  "subnet1": {' in out
    assert '    "srv": {' in out


def test_cross_group_edge_uses_dotted_path():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[Group(id="vlan100", label="VLAN 100", type="vlan")],
        nodes=[
            Node(id="fw1", label="fw1", type="firewall"),
            Node(id="sw1", label="sw1", type="switch", group="vlan100"),
        ],
        links=[
            Link(source=LinkEndpoint(node="fw1"), target=LinkEndpoint(node="sw1"))
        ],
    )
    out = _render(d)
    # Edge target references the grouped node via container-dot-node path
    assert '"fw1" -> "vlan100"."sw1"' in out


def test_ungrouped_nodes_appear_at_top_level():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[Group(id="vlan100", label="VLAN 100", type="vlan")],
        nodes=[
            Node(id="free", label="free", type="router"),
            Node(id="grouped", label="grouped", type="switch", group="vlan100"),
        ],
    )
    out = _render(d)
    # Top-level "free" block is not indented
    lines = out.splitlines()
    free_line = next(ln for ln in lines if '"free": {' in ln)
    assert free_line.startswith('"free"')  # no leading indent
    # Grouped node is nested (indented)
    grouped_line = next(ln for ln in lines if '"grouped": {' in ln)
    assert grouped_line.startswith("  ")
