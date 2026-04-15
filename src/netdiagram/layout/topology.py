"""Classify an undirected network topology to pick a layout algorithm."""

from __future__ import annotations

from enum import Enum

import networkx as nx


class TopologyShape(str, Enum):
    TRIVIAL = "trivial"        # 0 or 1 node
    TREE = "tree"              # acyclic, connected
    STAR = "star"              # one hub connected to all leaves
    RING = "ring"              # single cycle through all nodes
    MESH = "mesh"              # every node connected to every other
    HIERARCHICAL = "hierarchical"  # default fallback for anything else


def classify_topology(g: nx.Graph) -> TopologyShape:
    n = g.number_of_nodes()
    if n <= 1:
        return TopologyShape.TRIVIAL

    m = g.number_of_edges()

    # Tree: connected, m == n - 1 (acyclic, connected)
    if nx.is_connected(g) and m == n - 1:
        # Within trees, check for star pattern (one hub, all leaves)
        # Star requires at least 5 nodes to distinguish from simple trees
        degrees = sorted(d for _, d in g.degree())
        if n >= 5 and degrees[-1] == n - 1 and all(d == 1 for d in degrees[:-1]):
            return TopologyShape.STAR
        return TopologyShape.TREE

    # Ring: connected, every node degree 2, m == n
    if nx.is_connected(g) and m == n and all(d == 2 for _, d in g.degree()):
        return TopologyShape.RING

    # Mesh: complete graph
    if m == n * (n - 1) // 2:
        return TopologyShape.MESH

    return TopologyShape.HIERARCHICAL
