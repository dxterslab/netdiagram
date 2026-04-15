from netdiagram.ir.models import Diagram, Interface, Link, LinkEndpoint, Metadata, Node
from netdiagram.layout.engine import layout_diagram


def _simple_diagram() -> Diagram:
    return Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router", interfaces=[Interface(id="e0")]),
            Node(id="b", label="b", type="router", interfaces=[Interface(id="e0")]),
            Node(id="c", label="c", type="router", interfaces=[Interface(id="e0")]),
        ],
        links=[
            Link(source=LinkEndpoint(node="a", interface="e0"),
                 target=LinkEndpoint(node="b", interface="e0")),
            Link(source=LinkEndpoint(node="b", interface="e0"),
                 target=LinkEndpoint(node="c", interface="e0")),
        ],
    )


def test_layout_produces_position_for_every_node():
    d = _simple_diagram()
    laid = layout_diagram(d)
    assert {pn.node.id for pn in laid.nodes} == {"a", "b", "c"}


def test_layout_produces_edge_for_every_link():
    d = _simple_diagram()
    laid = layout_diagram(d)
    assert len(laid.edges) == 2
    for edge in laid.edges:
        assert len(edge.path) >= 2  # at least start and end


def test_layout_no_node_overlaps():
    d = _simple_diagram()
    laid = layout_diagram(d)
    nodes = laid.nodes
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            overlap_x = (a.x + a.width > b.x) and (b.x + b.width > a.x)
            overlap_y = (a.y + a.height > b.y) and (b.y + b.height > a.y)
            assert not (overlap_x and overlap_y), f"{a.node.id} overlaps {b.node.id}"


def test_canvas_encloses_all_nodes():
    d = _simple_diagram()
    laid = layout_diagram(d)
    for pn in laid.nodes:
        assert pn.x >= 0
        assert pn.y >= 0
        assert pn.x + pn.width <= laid.canvas_width
        assert pn.y + pn.height <= laid.canvas_height


def test_single_node_diagram_lays_out():
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[Node(id="only", label="only", type="server")],
    )
    laid = layout_diagram(d)
    assert len(laid.nodes) == 1
    assert laid.canvas_width > 0 and laid.canvas_height > 0


from netdiagram.ir.models import Group


def test_layout_includes_positioned_groups():
    d = Diagram(
        metadata=Metadata(title="T", type="logical"),
        groups=[Group(id="vlan100", label="VLAN 100", type="vlan")],
        nodes=[
            Node(id="sw1", label="sw1", type="switch", group="vlan100"),
            Node(id="sw2", label="sw2", type="switch", group="vlan100"),
        ],
    )
    laid = layout_diagram(d)
    assert len(laid.groups) == 1
    pg = laid.groups[0]
    # Group must enclose all its child nodes
    children = [pn for pn in laid.nodes if pn.node.group == "vlan100"]
    for pn in children:
        assert pn.x >= pg.x
        assert pn.y >= pg.y
        assert pn.x + pn.width <= pg.x + pg.width
        assert pn.y + pn.height <= pg.y + pg.height
