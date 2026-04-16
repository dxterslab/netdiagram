"""Label bounding-box computation and collision resolution.

Given a list of RoutedEdges, this module:
1. Computes the pixel bounding box of each interface label at its default
   position along the edge path.
2. Detects overlapping label pairs.
3. Nudges colliding labels perpendicular to their edge direction until
   no overlaps remain (up to a max iteration cap).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from netdiagram.layout.types import Point, RoutedEdge

# Approximate character metrics (same constants as dimensions.py).
_CHAR_WIDTH_PX = 7.0
_LABEL_PADDING_PX = 8.0
_LABEL_HEIGHT_PX = 16.0

# Default fraction along the edge where labels sit (matching drawio ±0.7
# mapped to 0..1 range: source at 0.15, target at 0.85).
_SOURCE_FRACTION = 0.15
_TARGET_FRACTION = 0.85

_NUDGE_STEP_PX = 20.0
_MAX_ITERATIONS = 50


@dataclass
class LabelBox:
    text: str
    x: float
    y: float
    width: float
    height: float
    edge_index: int
    role: str  # "source" or "target"


def compute_label_boxes(edges: list[RoutedEdge]) -> list[LabelBox]:
    """Compute a LabelBox for every interface label in the edge list."""
    out: list[LabelBox] = []
    for i, edge in enumerate(edges):
        if edge.link.source.interface:
            pos = point_along_path(edge.path, _SOURCE_FRACTION)
            w = _label_width(edge.link.source.interface)
            out.append(
                LabelBox(
                    text=edge.link.source.interface,
                    x=pos.x - w / 2,
                    y=pos.y - _LABEL_HEIGHT_PX / 2,
                    width=w,
                    height=_LABEL_HEIGHT_PX,
                    edge_index=i,
                    role="source",
                )
            )
        if edge.link.target.interface:
            pos = point_along_path(edge.path, _TARGET_FRACTION)
            w = _label_width(edge.link.target.interface)
            out.append(
                LabelBox(
                    text=edge.link.target.interface,
                    x=pos.x - w / 2,
                    y=pos.y - _LABEL_HEIGHT_PX / 2,
                    width=w,
                    height=_LABEL_HEIGHT_PX,
                    edge_index=i,
                    role="target",
                )
            )
    return out


def detect_collisions(boxes: list[LabelBox]) -> list[tuple[int, int]]:
    """Return index pairs of overlapping label boxes."""
    collisions: list[tuple[int, int]] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _overlap(boxes[i], boxes[j]):
                collisions.append((i, j))
    return collisions


def resolve_collisions(boxes: list[LabelBox]) -> list[LabelBox]:
    """Nudge overlapping labels apart by shifting them vertically.

    Returns a new list of LabelBox with adjusted y positions."""
    work = [
        LabelBox(
            text=b.text, x=b.x, y=b.y, width=b.width, height=b.height,
            edge_index=b.edge_index, role=b.role,
        )
        for b in boxes
    ]
    for _ in range(_MAX_ITERATIONS):
        pairs = detect_collisions(work)
        if not pairs:
            break
        for i, j in pairs:
            a, b = work[i], work[j]
            # Push the later label downward (or the earlier upward)
            a.y -= _NUDGE_STEP_PX / 2
            b.y += _NUDGE_STEP_PX / 2
    return work


def point_along_path(path: list[Point], fraction: float) -> Point:
    """Return the point at the given fraction (0..1) along a polyline path."""
    if len(path) < 2:
        return path[0] if path else Point(0, 0)

    # Compute total length and walk segments.
    segments: list[tuple[float, int]] = []  # (cumulative_length, segment_index)
    total = 0.0
    for k in range(len(path) - 1):
        dx = path[k + 1].x - path[k].x
        dy = path[k + 1].y - path[k].y
        seg_len = math.hypot(dx, dy)
        total += seg_len
        segments.append((total, k))

    if total == 0:
        return path[0]

    target_dist = fraction * total
    for cum_len, k in segments:
        seg_start_dist = cum_len - math.hypot(
            path[k + 1].x - path[k].x, path[k + 1].y - path[k].y
        )
        if cum_len >= target_dist:
            seg_len = cum_len - seg_start_dist
            if seg_len == 0:
                return path[k]
            t = (target_dist - seg_start_dist) / seg_len
            x = path[k].x + t * (path[k + 1].x - path[k].x)
            y = path[k].y + t * (path[k + 1].y - path[k].y)
            return Point(x, y)

    return path[-1]


def _label_width(text: str) -> float:
    return len(text) * _CHAR_WIDTH_PX + _LABEL_PADDING_PX


def _overlap(a: LabelBox, b: LabelBox) -> bool:
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )
