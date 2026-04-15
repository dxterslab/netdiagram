"""D2 (d2lang.com) renderer.

Unlike the Draw.io renderer, D2 has its own layout engine (ELK/Dagre), so we
emit declarative text and let D2 decide node placement. The `LayoutedDiagram`
positions are ignored — only the underlying IR is used.
"""

from __future__ import annotations

from netdiagram.ir.models import NodeType
from netdiagram.layout.types import LayoutedDiagram

# Map IR node types to D2 built-in shape names.
# D2 ships these shapes out of the box: rectangle, square, page, parallelogram,
# document, cylinder, queue, package, step, callout, stored_data, person,
# diamond, oval, circle, hexagon, cloud, text, code, class, image.
_SHAPE_BY_TYPE: dict[NodeType, str] = {
    "router": "hexagon",
    "switch": "rectangle",
    "firewall": "diamond",
    "server": "rectangle",
    "load_balancer": "hexagon",
    "access_point": "oval",
    "endpoint": "rectangle",
    "generic": "rectangle",
    # Cloud constructs
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

        for node in ir.nodes:
            lines.extend(self._render_node(node, indent=0))
            lines.append("")

        for link in ir.links:
            lines.extend(self._render_edge(link))
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _render_node(self, node, indent: int) -> list[str]:
        pad = "  " * indent
        shape = _SHAPE_BY_TYPE.get(node.type, _SHAPE_BY_TYPE["generic"])
        return [
            f'{pad}"{node.id}": {{',
            f'{pad}  shape: {shape}',
            f'{pad}  label: "{node.label}"',
            f'{pad}}}',
        ]

    def _render_edge(self, link) -> list[str]:
        # Base edge line: "a" -> "b" optionally with label.
        src_id = f'"{link.source.node}"'
        tgt_id = f'"{link.target.node}"'
        head = f"{src_id} -> {tgt_id}"
        if link.label:
            head = f'{head}: "{link.label}"'

        # Collect edge-body attributes (style, arrowhead labels).
        body: list[str] = []

        if link.style == "dashed":
            body.append("  style.stroke-dash: 5")
        elif link.style == "dotted":
            body.append("  style.stroke-dash: 2")
        # solid is default, no attribute needed

        if link.source.interface:
            body.append(f'  source-arrowhead.label: "{link.source.interface}"')
        if link.target.interface:
            body.append(f'  target-arrowhead.label: "{link.target.interface}"')

        if not body:
            return [head]

        return [f"{head} {{", *body, "}"]
