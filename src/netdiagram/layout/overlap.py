"""Resolve node overlaps by iteratively pushing colliding nodes apart.

Algorithm: a simplified version of Dwyer's scan-line approach. For each pair
of overlapping rectangles, compute the minimum translation vector along the
axis of least penetration and apply half the displacement to each node. Iterate
until no overlaps remain or a max iteration cap is hit.
"""

from __future__ import annotations

from netdiagram.layout.types import PositionedNode

_MAX_ITERATIONS = 200


def resolve_overlaps(
    nodes: list[PositionedNode], padding: float = 10.0
) -> list[PositionedNode]:
    """Return a new list of PositionedNode with overlaps resolved."""
    # Work on mutable copies (dataclass is mutable by default here).
    work = [
        PositionedNode(node=pn.node, x=pn.x, y=pn.y, width=pn.width, height=pn.height)
        for pn in nodes
    ]

    for _ in range(_MAX_ITERATIONS):
        moved = False
        for i in range(len(work)):
            for j in range(i + 1, len(work)):
                if _push_apart(work[i], work[j], padding):
                    moved = True
        if not moved:
            break
    return work


def _push_apart(a: PositionedNode, b: PositionedNode, padding: float) -> bool:
    """If a and b overlap (including padding), move each by half the MTV.
    Returns True if a push happened.
    """
    a_right, a_bottom = a.x + a.width, a.y + a.height
    b_right, b_bottom = b.x + b.width, b.y + b.height

    # Raw overlaps (without padding) determine which axis has least penetration.
    raw_overlap_x = min(a_right, b_right) - max(a.x, b.x)
    raw_overlap_y = min(a_bottom, b_bottom) - max(a.y, b.y)

    # Effective overlaps include padding — used for the actual push distance.
    overlap_x = raw_overlap_x + padding
    overlap_y = raw_overlap_y + padding

    if overlap_x <= 0 or overlap_y <= 0:
        return False

    # Push along the axis of greatest raw penetration so nodes are moved apart
    # in the direction they are most deeply embedded into each other.
    if raw_overlap_x >= raw_overlap_y:
        dx = overlap_x / 2
        if a.x < b.x:
            a.x -= dx
            b.x += dx
        else:
            a.x += dx
            b.x -= dx
    else:
        dy = overlap_y / 2
        if a.y < b.y:
            a.y -= dy
            b.y += dy
        else:
            a.y += dy
            b.y -= dy
    return True
