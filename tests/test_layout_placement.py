import networkx as nx

from netdiagram.layout.placement import compute_initial_positions
from netdiagram.layout.topology import TopologyShape


def test_returns_position_for_each_node():
    g = nx.Graph()
    g.add_edges_from([("a", "b"), ("b", "c"), ("b", "d")])
    positions = compute_initial_positions(g, TopologyShape.TREE)
    assert set(positions.keys()) == {"a", "b", "c", "d"}
    for x, y in positions.values():
        assert isinstance(x, float)
        assert isinstance(y, float)


def test_single_node_position():
    g = nx.Graph()
    g.add_node("only")
    positions = compute_initial_positions(g, TopologyShape.TRIVIAL)
    assert positions == {"only": (0.0, 0.0)}


def test_ring_positions_are_circular():
    # All nodes should lie roughly on a circle (equal distance from centroid)
    g = nx.Graph()
    nodes = ["a", "b", "c", "d", "e"]
    g.add_edges_from([(nodes[i], nodes[(i + 1) % 5]) for i in range(5)])
    positions = compute_initial_positions(g, TopologyShape.RING)
    cx = sum(x for x, _ in positions.values()) / 5
    cy = sum(y for _, y in positions.values()) / 5
    distances = [((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 for x, y in positions.values()]
    avg = sum(distances) / len(distances)
    for d in distances:
        assert abs(d - avg) / avg < 0.05  # within 5% of the mean radius
