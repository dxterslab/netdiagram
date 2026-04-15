"""Layout output types shared between the layout engine and renderers."""

from __future__ import annotations

from dataclasses import dataclass, field

from netdiagram.ir.models import Diagram, Group, Link, Node


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class PositionedNode:
    node: Node
    x: float
    y: float
    width: float
    height: float


@dataclass
class PositionedGroup:
    group: Group
    x: float
    y: float
    width: float
    height: float


@dataclass
class RoutedEdge:
    link: Link
    path: list[Point]  # Start, optional waypoints, end. Phase 1: just [start, end].
    source_label_pos: Point | None = None
    target_label_pos: Point | None = None


@dataclass
class LayoutedDiagram:
    diagram: Diagram
    nodes: list[PositionedNode] = field(default_factory=list)
    groups: list[PositionedGroup] = field(default_factory=list)
    edges: list[RoutedEdge] = field(default_factory=list)
    canvas_width: float = 0.0
    canvas_height: float = 0.0

    def node_by_id(self, nid: str) -> PositionedNode:
        for pn in self.nodes:
            if pn.node.id == nid:
                return pn
        raise KeyError(nid)
