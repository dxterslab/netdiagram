"""Compute initial 2D coordinates for nodes given the topology shape."""

from __future__ import annotations

import math

import networkx as nx

from netdiagram.layout.topology import TopologyShape

# Algorithm selection per topology. Graphviz engines:
#   dot   -> hierarchical (best for trees, hierarchies)
#   neato -> force-directed (general)
#   twopi -> radial (good for stars)
#   circo -> circular (not always round for rings)
_ENGINE_BY_SHAPE = {
    TopologyShape.TREE: "dot",
    TopologyShape.STAR: "twopi",
    TopologyShape.HIERARCHICAL: "dot",
    TopologyShape.MESH: "neato",
}


def compute_initial_positions(
    g: nx.Graph, shape: TopologyShape
) -> dict[str, tuple[float, float]]:
    """Return a mapping of node id -> (x, y) coordinates."""
    if shape is TopologyShape.TRIVIAL:
        return dict.fromkeys(g.nodes(), (0.0, 0.0))

    if shape is TopologyShape.RING:
        return _ring_positions(g)

    engine = _ENGINE_BY_SHAPE.get(shape, "dot")
    return _graphviz_positions(g, engine)


def _ring_positions(g: nx.Graph) -> dict[str, tuple[float, float]]:
    # Walk the single cycle to order the nodes, then place around a circle.
    nodes = list(g.nodes())
    ordered = _walk_ring(g, nodes[0])
    n = len(ordered)
    radius = max(120.0, n * 40.0)
    out: dict[str, tuple[float, float]] = {}
    for i, nid in enumerate(ordered):
        angle = 2 * math.pi * i / n
        out[nid] = (radius * math.cos(angle), radius * math.sin(angle))
    return out


def _walk_ring(g: nx.Graph, start: str) -> list[str]:
    ordered = [start]
    prev: str | None = None
    cur = start
    while True:
        neighbors = [n for n in g.neighbors(cur) if n != prev]
        if not neighbors:
            break
        nxt = neighbors[0]
        if nxt == start:
            break
        ordered.append(nxt)
        prev, cur = cur, nxt
    return ordered


def _graphviz_positions(g: nx.Graph, engine: str) -> dict[str, tuple[float, float]]:
    # Use networkx's graphviz_layout helper (requires pygraphviz).
    # Graphviz returns coordinates in points; we scale to pixels (1 pt = 1 px
    # is fine for our purposes — the overlap pass will re-space as needed).
    from networkx.drawing.nx_agraph import graphviz_layout

    pos = graphviz_layout(g, prog=engine)
    return {n: (float(x), float(y)) for n, (x, y) in pos.items()}
