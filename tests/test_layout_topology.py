import networkx as nx

from netdiagram.layout.topology import TopologyShape, classify_topology


def _graph(edges: list[tuple[str, str]], nodes: list[str] | None = None) -> nx.Graph:
    g = nx.Graph()
    if nodes:
        g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    return g


def test_single_node_is_trivial():
    g = _graph([], nodes=["a"])
    assert classify_topology(g) == TopologyShape.TRIVIAL


def test_tree_detected():
    # a-b, b-c, b-d (no cycles)
    g = _graph([("a", "b"), ("b", "c"), ("b", "d")])
    assert classify_topology(g) == TopologyShape.TREE


def test_star_detected():
    # one hub, many leaves
    g = _graph([("hub", "a"), ("hub", "b"), ("hub", "c"), ("hub", "d")])
    assert classify_topology(g) == TopologyShape.STAR


def test_ring_detected():
    g = _graph([("a", "b"), ("b", "c"), ("c", "d"), ("d", "a")])
    assert classify_topology(g) == TopologyShape.RING


def test_mesh_detected():
    # Every node connected to every other (K4)
    nodes = ["a", "b", "c", "d"]
    edges = [(u, v) for i, u in enumerate(nodes) for v in nodes[i + 1 :]]
    assert classify_topology(_graph(edges)) == TopologyShape.MESH


def test_hierarchical_fallback():
    # A graph with cycles that isn't a ring/star/mesh
    g = _graph(
        [("core", "dist1"), ("core", "dist2"), ("dist1", "acc1"),
         ("dist1", "acc2"), ("dist2", "acc3"), ("acc1", "acc2")]
    )
    assert classify_topology(g) == TopologyShape.HIERARCHICAL
