"""Top-level layout pipeline.

Pipeline stages:
1. Build a networkx graph from the IR.
2. Classify the topology to pick a layout algorithm.
3. Compute initial coordinates.
4. Compute node dimensions.
5. Resolve node overlaps.
6. Normalize coordinates so the canvas origin is (0, 0) with margin.
7. Route edges as straight line segments between node centers (Phase 1).
"""

from __future__ import annotations

import networkx as nx

from netdiagram.ir.models import Diagram
from netdiagram.layout.dimensions import compute_node_size
from netdiagram.layout.overlap import resolve_overlaps
from netdiagram.layout.placement import compute_initial_positions
from netdiagram.layout.topology import classify_topology
from netdiagram.layout.types import LayoutedDiagram, Point, PositionedNode, RoutedEdge

_MARGIN = 40.0
_NODE_PADDING = 20.0


def layout_diagram(diagram: Diagram) -> LayoutedDiagram:
    g = _build_graph(diagram)
    shape = classify_topology(g)
    raw_positions = compute_initial_positions(g, shape)

    # Create PositionedNode objects with real dimensions.
    positioned: list[PositionedNode] = []
    for node in diagram.nodes:
        x, y = raw_positions.get(node.id, (0.0, 0.0))
        w, h = compute_node_size(node)
        # Graphviz coords reference node centers; convert to top-left.
        positioned.append(PositionedNode(node=node, x=x - w / 2, y=y - h / 2, width=w, height=h))

    positioned = resolve_overlaps(positioned, padding=_NODE_PADDING)

    # Normalize so the minimum x/y is at `_MARGIN`.
    positioned = _normalize(positioned, margin=_MARGIN)

    canvas_w, canvas_h = _canvas_bounds(positioned, margin=_MARGIN)

    laid = LayoutedDiagram(
        diagram=diagram, nodes=positioned, canvas_width=canvas_w, canvas_height=canvas_h
    )
    laid.edges = _route_edges(diagram, laid)
    return laid


def _build_graph(diagram: Diagram) -> nx.Graph:
    g = nx.Graph()
    for n in diagram.nodes:
        g.add_node(n.id)
    for link in diagram.links:
        g.add_edge(link.source.node, link.target.node)
    return g


def _normalize(nodes: list[PositionedNode], margin: float) -> list[PositionedNode]:
    if not nodes:
        return nodes
    min_x = min(pn.x for pn in nodes)
    min_y = min(pn.y for pn in nodes)
    dx = margin - min_x
    dy = margin - min_y
    for pn in nodes:
        pn.x += dx
        pn.y += dy
    return nodes


def _canvas_bounds(nodes: list[PositionedNode], margin: float) -> tuple[float, float]:
    if not nodes:
        return (2 * margin, 2 * margin)
    max_x = max(pn.x + pn.width for pn in nodes)
    max_y = max(pn.y + pn.height for pn in nodes)
    return (max_x + margin, max_y + margin)


def _route_edges(diagram: Diagram, laid: LayoutedDiagram) -> list[RoutedEdge]:
    """Phase 1: straight-line edges between node centers."""
    by_id = {pn.node.id: pn for pn in laid.nodes}
    out: list[RoutedEdge] = []
    for link in diagram.links:
        s = by_id[link.source.node]
        t = by_id[link.target.node]
        start = Point(s.x + s.width / 2, s.y + s.height / 2)
        end = Point(t.x + t.width / 2, t.y + t.height / 2)
        out.append(RoutedEdge(link=link, path=[start, end]))
    return out
