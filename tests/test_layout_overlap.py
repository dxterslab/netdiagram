from netdiagram.ir.models import Node
from netdiagram.layout.overlap import resolve_overlaps
from netdiagram.layout.types import PositionedNode


def _pn(nid: str, x: float, y: float, w: float = 100, h: float = 60) -> PositionedNode:
    return PositionedNode(
        node=Node(id=nid, label=nid, type="router"), x=x, y=y, width=w, height=h
    )


def _overlap(a: PositionedNode, b: PositionedNode) -> bool:
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )


def test_no_overlap_unchanged():
    nodes = [_pn("a", 0, 0), _pn("b", 200, 0)]
    resolved = resolve_overlaps(nodes, padding=10)
    # Coordinates should be identical
    assert resolved[0].x == 0 and resolved[0].y == 0
    assert resolved[1].x == 200 and resolved[1].y == 0


def test_two_overlapping_nodes_separated():
    nodes = [_pn("a", 0, 0), _pn("b", 20, 20)]
    resolved = resolve_overlaps(nodes, padding=10)
    assert not _overlap(resolved[0], resolved[1])


def test_chain_of_overlaps_resolves():
    nodes = [_pn(f"n{i}", i * 5, 0) for i in range(5)]
    resolved = resolve_overlaps(nodes, padding=5)
    for i in range(len(resolved)):
        for j in range(i + 1, len(resolved)):
            assert not _overlap(resolved[i], resolved[j]), f"{i} overlaps {j}"


def test_padding_enforced():
    nodes = [_pn("a", 0, 0), _pn("b", 20, 0)]
    resolved = resolve_overlaps(nodes, padding=30)
    # Horizontal gap between rightmost of first and leftmost of second >= 30
    a, b = sorted(resolved, key=lambda p: p.x)
    gap = b.x - (a.x + a.width)
    assert gap >= 30
