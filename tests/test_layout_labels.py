"""Unit tests for label bounding-box computation and collision resolution."""

from netdiagram.ir.models import Link, LinkEndpoint
from netdiagram.layout.labels import LabelBox, detect_collisions, resolve_collisions
from netdiagram.layout.types import Point, RoutedEdge


def _edge(src_iface: str | None, tgt_iface: str | None) -> RoutedEdge:
    """Create a horizontal edge from (0,100) to (300,100) with optional interfaces."""
    return RoutedEdge(
        link=Link(
            source=LinkEndpoint(node="a", interface=src_iface),
            target=LinkEndpoint(node="b", interface=tgt_iface),
        ),
        path=[Point(0, 100), Point(300, 100)],
    )


def test_label_box_from_edge_source():
    from netdiagram.layout.labels import compute_label_boxes

    edges = [_edge("gi0/1", None)]
    boxes = compute_label_boxes(edges)
    assert len(boxes) == 1
    b = boxes[0]
    assert b.text == "gi0/1"
    assert b.width > 0
    assert b.height > 0
    # Source label sits near the source end of the edge
    assert b.x < 150  # closer to x=0 than to x=300


def test_label_box_from_edge_both_endpoints():
    from netdiagram.layout.labels import compute_label_boxes

    edges = [_edge("e0", "e1")]
    boxes = compute_label_boxes(edges)
    assert len(boxes) == 2
    src_box = next(b for b in boxes if b.text == "e0")
    tgt_box = next(b for b in boxes if b.text == "e1")
    # Source is near x=0, target near x=300
    assert src_box.x < tgt_box.x


def test_no_collisions_when_labels_far_apart():
    b1 = LabelBox(text="a", x=0, y=0, width=40, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="b", x=200, y=0, width=40, height=16, edge_index=1, role="source")
    assert detect_collisions([b1, b2]) == []


def test_collision_detected_when_overlapping():
    b1 = LabelBox(text="a", x=10, y=90, width=40, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="b", x=20, y=92, width=40, height=16, edge_index=1, role="source")
    collisions = detect_collisions([b1, b2])
    assert len(collisions) >= 1
    assert (0, 1) in collisions or (1, 0) in collisions


def test_resolve_collisions_separates_overlapping_labels():
    b1 = LabelBox(text="swp37", x=10, y=90, width=50, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="swp38", x=15, y=92, width=50, height=16, edge_index=1, role="source")
    b3 = LabelBox(text="swp40", x=12, y=91, width=50, height=16, edge_index=2, role="source")
    resolved = resolve_collisions([b1, b2, b3])
    # After resolution, no pair should overlap
    for i in range(len(resolved)):
        for j in range(i + 1, len(resolved)):
            a, b = resolved[i], resolved[j]
            overlap_x = a.x + a.width > b.x and b.x + b.width > a.x
            overlap_y = a.y + a.height > b.y and b.y + b.height > a.y
            assert not (overlap_x and overlap_y), (
                f"labels '{a.text}' and '{b.text}' still overlap after resolution"
            )


def test_resolve_no_ops_when_no_collisions():
    b1 = LabelBox(text="a", x=0, y=0, width=40, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="b", x=200, y=0, width=40, height=16, edge_index=1, role="source")
    resolved = resolve_collisions([b1, b2])
    # Positions should be unchanged
    assert resolved[0].y == 0
    assert resolved[1].y == 0
