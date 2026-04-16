"""D2 (d2lang.com) renderer.

Unlike the Draw.io renderer, D2 has its own layout engine (ELK/Dagre), so we
emit declarative text and let D2 decide node placement. The `LayoutedDiagram`
positions are ignored — only the underlying IR is used.
"""

from __future__ import annotations

from netdiagram.ir.models import Diagram, Group, Link, Node, NodeType
from netdiagram.layout.types import LayoutedDiagram

_SHAPE_BY_TYPE: dict[NodeType, str] = {
    "router": "hexagon",
    "switch": "rectangle",
    "firewall": "diamond",
    "server": "rectangle",
    "load_balancer": "hexagon",
    "access_point": "oval",
    "endpoint": "rectangle",
    "generic": "rectangle",
    "vpc": "cloud",
    "cloud_lb": "hexagon",
    "cloud_db": "cylinder",
    "internet_gateway": "cloud",
    "nat_gateway": "hexagon",
    "security_group": "diamond",
}


class D2Renderer:
    format = "d2"
    extension = ".d2"

    def render(self, diagram: LayoutedDiagram) -> str:
        ir = diagram.diagram
        lines: list[str] = []

        if ir.metadata.title:
            lines.append(f"# {ir.metadata.title}")
            lines.append("")

        # Index data for fast lookup while walking the hierarchy.
        children_of: dict[str | None, list[Group]] = {}
        for g in ir.groups:
            children_of.setdefault(g.parent, []).append(g)
        nodes_in_group: dict[str | None, list[Node]] = {}
        for n in ir.nodes:
            nodes_in_group.setdefault(n.group, []).append(n)

        # Render top-level groups (those without a parent) recursively.
        for grp in children_of.get(None, []):
            lines.extend(
                self._render_group(grp, children_of, nodes_in_group, indent=0)
            )
            lines.append("")

        # Render ungrouped nodes at top level.
        for node in nodes_in_group.get(None, []):
            lines.extend(self._render_node(node, indent=0))
            lines.append("")

        # Build edges (with container-aware paths).
        path_of_node = _node_paths(ir)
        for link in ir.links:
            lines.extend(self._render_edge(link, path_of_node))
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _render_group(
        self,
        group: Group,
        children_of: dict[str | None, list[Group]],
        nodes_in_group: dict[str | None, list[Node]],
        indent: int,
    ) -> list[str]:
        pad = "  " * indent
        inner_pad = "  " * (indent + 1)
        lines: list[str] = [
            f'{pad}"{group.id}": {{',
            f'{inner_pad}label: "{group.label}"',
            f"{inner_pad}label.near: bottom-center",
        ]
        # Nested groups first, then member nodes.
        for child_group in children_of.get(group.id, []):
            lines.extend(
                self._render_group(child_group, children_of, nodes_in_group, indent + 1)
            )
        for node in nodes_in_group.get(group.id, []):
            lines.extend(self._render_node(node, indent + 1))
        lines.append(f"{pad}}}")
        return lines

    def _render_node(self, node: Node, indent: int) -> list[str]:
        pad = "  " * indent
        shape = _SHAPE_BY_TYPE.get(node.type, _SHAPE_BY_TYPE["generic"])
        return [
            f'{pad}"{node.id}": {{',
            f'{pad}  shape: {shape}',
            f'{pad}  label: "{node.label}"',
            f'{pad}}}',
        ]

    def _render_edge(self, link: Link, path_of_node: dict[str, str]) -> list[str]:
        src = path_of_node[link.source.node]
        tgt = path_of_node[link.target.node]
        head = f"{src} -> {tgt}"
        if link.label:
            head = f'{head}: "{link.label}"'

        body: list[str] = []
        if link.style == "dashed":
            body.append("  style.stroke-dash: 5")
        elif link.style == "dotted":
            body.append("  style.stroke-dash: 2")

        if link.source.interface:
            body.append(f'  source-arrowhead.label: "{link.source.interface}"')
        if link.target.interface:
            body.append(f'  target-arrowhead.label: "{link.target.interface}"')

        if not body:
            return [head]
        return [f"{head} {{", *body, "}"]


def _node_paths(ir: Diagram) -> dict[str, str]:
    """Build node-id -> D2 reference path, e.g. '"vlan100"."sw1"' for grouped
    nodes, '"fw1"' for top-level nodes. D2 uses dot notation to reach nodes
    inside containers."""
    group_parent: dict[str, str | None] = {g.id: g.parent for g in ir.groups}
    paths: dict[str, str] = {}
    for node in ir.nodes:
        segments: list[str] = []
        cur: str | None = node.group
        while cur is not None:
            segments.append(cur)
            cur = group_parent.get(cur)
        segments.reverse()
        segments.append(node.id)
        paths[node.id] = ".".join(f'"{s}"' for s in segments)
    return paths
