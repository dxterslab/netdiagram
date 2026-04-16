from netdiagram.ir.models import Diagram, Group, Interface, Link, LinkEndpoint, Metadata, Node
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
    # Group must not extend above or left of canvas
    assert pg.x >= 0
    assert pg.y >= 0
    # Group must enclose all its child nodes
    children = [pn for pn in laid.nodes if pn.node.group == "vlan100"]
    for pn in children:
        assert pn.x >= pg.x
        assert pn.y >= pg.y
        assert pn.x + pn.width <= pg.x + pg.width
        assert pn.y + pn.height <= pg.y + pg.height


def test_parallel_edges_have_distinct_endpoints():
    """Two links between the same pair of nodes should not produce identical paths."""
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router",
                 interfaces=[Interface(id="e0"), Interface(id="e1")]),
            Node(id="b", label="b", type="router",
                 interfaces=[Interface(id="e0"), Interface(id="e1")]),
        ],
        links=[
            Link(source=LinkEndpoint(node="a", interface="e0"),
                 target=LinkEndpoint(node="b", interface="e0")),
            Link(source=LinkEndpoint(node="a", interface="e1"),
                 target=LinkEndpoint(node="b", interface="e1")),
        ],
    )
    laid = layout_diagram(d)
    assert len(laid.edges) == 2
    start_a = (laid.edges[0].path[0].x, laid.edges[0].path[0].y)
    start_b = (laid.edges[1].path[0].x, laid.edges[1].path[0].y)
    assert start_a != start_b, "parallel edges must fan out at the source endpoint"
    end_a = (laid.edges[0].path[-1].x, laid.edges[0].path[-1].y)
    end_b = (laid.edges[1].path[-1].x, laid.edges[1].path[-1].y)
    assert end_a != end_b, "parallel edges must fan out at the target endpoint"


def test_edge_routes_around_intermediate_node():
    """Place three nodes in a line. The edge from left to right must route
    around the center node rather than straight through it."""
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="left", label="left", type="router"),
            Node(id="middle", label="middle", type="router"),
            Node(id="right", label="right", type="router"),
        ],
        links=[
            # Only link is left<->right; the center node is in the way but not
            # connected.
            Link(source=LinkEndpoint(node="left"),
                 target=LinkEndpoint(node="right")),
        ],
    )
    laid = layout_diagram(d)
    # Path must exist and must not pierce the middle node's bounding box.
    edge = laid.edges[0]
    assert len(edge.path) >= 2
    middle = next(pn for pn in laid.nodes if pn.node.id == "middle")
    for p in edge.path:
        inside_x = middle.x < p.x < middle.x + middle.width
        inside_y = middle.y < p.y < middle.y + middle.height
        assert not (inside_x and inside_y), (
            f"edge path point ({p.x}, {p.y}) pierces 'middle' node"
        )
