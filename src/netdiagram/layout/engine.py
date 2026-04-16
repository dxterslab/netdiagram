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

import math

import networkx as nx

from netdiagram.ir.models import Diagram
from netdiagram.layout.dimensions import compute_node_size
from netdiagram.layout.overlap import resolve_overlaps
from netdiagram.layout.placement import compute_initial_positions
from netdiagram.layout.topology import classify_topology
from netdiagram.layout.types import (
    LayoutedDiagram,
    Point,
    PositionedGroup,
    PositionedNode,
    RoutedEdge,
)

_MARGIN = 40.0
_NODE_PADDING = 20.0
_GROUP_PADDING = 30.0
_GROUP_LABEL_HEIGHT = 28.0


def layout_diagram(diagram: Diagram) -> LayoutedDiagram:
    g = _build_graph(diagram)
    shape = classify_topology(g)
    raw_positions = compute_initial_positions(g, shape)

    positioned: list[PositionedNode] = []
    for node in diagram.nodes:
        x, y = raw_positions.get(node.id, (0.0, 0.0))
        w, h = compute_node_size(node)
        positioned.append(
            PositionedNode(node=node, x=x - w / 2, y=y - h / 2, width=w, height=h)
        )

    positioned = resolve_overlaps(positioned, padding=_NODE_PADDING)

    groups = _compute_group_bounds(diagram, positioned)

    # Normalize both nodes and groups together so nothing starts above/left of margin.
    _normalize_all(positioned, groups, margin=_MARGIN)

    canvas_w, canvas_h = _canvas_bounds_with_groups(positioned, groups, margin=_MARGIN)

    laid = LayoutedDiagram(
        diagram=diagram,
        nodes=positioned,
        groups=groups,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
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


def _normalize_all(
    nodes: list[PositionedNode], groups: list[PositionedGroup], margin: float
) -> None:
    """Shift nodes and groups together so the combined minimum x/y is at `margin`."""
    if not nodes and not groups:
        return
    xs = [pn.x for pn in nodes] + [pg.x for pg in groups]
    ys = [pn.y for pn in nodes] + [pg.y for pg in groups]
    if not xs:
        return
    dx = margin - min(xs)
    dy = margin - min(ys)
    for pn in nodes:
        pn.x += dx
        pn.y += dy
    for pg in groups:
        pg.x += dx
        pg.y += dy


def _compute_group_bounds(
    diagram: Diagram, positioned: list[PositionedNode]
) -> list[PositionedGroup]:
    """For each group, compute a bounding rectangle that encloses all its member
    nodes plus a padding allowance and label strip at the top."""
    by_id = {pn.node.id: pn for pn in positioned}
    out: list[PositionedGroup] = []
    for group in diagram.groups:
        members = [by_id[n.id] for n in diagram.nodes if n.group == group.id]
        if not members:
            # Empty group still gets a small placeholder rectangle near origin.
            out.append(
                PositionedGroup(group=group, x=0.0, y=0.0, width=200.0, height=80.0)
            )
            continue
        min_x = min(pn.x for pn in members) - _GROUP_PADDING
        min_y = min(pn.y for pn in members) - _GROUP_PADDING - _GROUP_LABEL_HEIGHT
        max_x = max(pn.x + pn.width for pn in members) + _GROUP_PADDING
        max_y = max(pn.y + pn.height for pn in members) + _GROUP_PADDING
        out.append(
            PositionedGroup(
                group=group, x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y
            )
        )
    return out


def _canvas_bounds_with_groups(
    nodes: list[PositionedNode], groups: list[PositionedGroup], margin: float
) -> tuple[float, float]:
    max_x = margin
    max_y = margin
    for pn in nodes:
        max_x = max(max_x, pn.x + pn.width)
        max_y = max(max_y, pn.y + pn.height)
    for pg in groups:
        max_x = max(max_x, pg.x + pg.width)
        max_y = max(max_y, pg.y + pg.height)
    return (max_x + margin, max_y + margin)


def _route_edges(diagram: Diagram, laid: LayoutedDiagram) -> list[RoutedEdge]:
    """Phase 2 routing: straight lines between endpoints, but fan parallel
    edges out perpendicular to the connecting vector so they don't overlap."""
    by_id = {pn.node.id: pn for pn in laid.nodes}

    # Group links by unordered node pair so peer peerlinks (a<->b and b<->a)
    # fan out together.
    pair_counts: dict[tuple[str, str], int] = {}
    for link in diagram.links:
        pair = tuple(sorted((link.source.node, link.target.node)))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    pair_index: dict[tuple[str, str], int] = dict.fromkeys(pair_counts, 0)

    out: list[RoutedEdge] = []
    for link in diagram.links:
        pair = tuple(sorted((link.source.node, link.target.node)))
        idx = pair_index[pair]
        total = pair_counts[pair]
        pair_index[pair] += 1

        s = by_id[link.source.node]
        t = by_id[link.target.node]
        sx, sy = s.x + s.width / 2, s.y + s.height / 2
        tx, ty = t.x + t.width / 2, t.y + t.height / 2

        dx_off, dy_off = _fan_out_offset(sx, sy, tx, ty, idx, total)
        start = Point(sx + dx_off, sy + dy_off)
        end = Point(tx + dx_off, ty + dy_off)
        out.append(RoutedEdge(link=link, path=[start, end]))
    return out


def _fan_out_offset(
    sx: float, sy: float, tx: float, ty: float, idx: int, total: int
) -> tuple[float, float]:
    """Return a perpendicular offset so the i-th of `total` parallel edges
    sits on its own line. Spacing is 14px between adjacent edges."""
    if total <= 1:
        return (0.0, 0.0)

    dx, dy = tx - sx, ty - sy
    length = math.hypot(dx, dy) or 1.0
    # Unit perpendicular.
    px, py = -dy / length, dx / length
    # Center the fan: edges at indices 0..total-1 map to offsets spread
    # around zero so the group stays visually centered on the node-to-node
    # line.
    spacing = 14.0
    offset = (idx - (total - 1) / 2.0) * spacing
    return (px * offset, py * offset)
