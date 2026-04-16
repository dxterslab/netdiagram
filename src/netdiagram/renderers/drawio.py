"""Draw.io (mxGraph XML) renderer."""

from __future__ import annotations

from lxml import etree

from netdiagram.ir.models import Link, LinkStyle, NodeType
from netdiagram.layout.types import LayoutedDiagram, PositionedNode, RoutedEdge

_S = "html=1;whiteSpace=wrap;"
_STYLE_BY_TYPE: dict[NodeType, str] = {
    "router": _S + "shape=mscae/router;fillColor=#1B5E9E;fontColor=#FFFFFF;",
    "switch": _S + "shape=mscae/switch;fillColor=#0072C6;fontColor=#FFFFFF;",
    "firewall": _S + "shape=cisco/firewall;fillColor=#B0343C;fontColor=#FFFFFF;",
    "server": _S + "shape=mscae/server;fillColor=#5C8A3F;fontColor=#FFFFFF;",
    "load_balancer": _S + "shape=mscae/load_balancer;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "access_point": _S + "shape=mscae/wireless_ap;fillColor=#2C7873;fontColor=#FFFFFF;",
    "endpoint": _S + "shape=mscae/workstation;fillColor=#7A7A7A;fontColor=#FFFFFF;",
    "vpc": _S + "shape=mscae/cloud;fillColor=#D3E6F1;fontColor=#000000;",
    "cloud_lb": _S + "shape=mscae/load_balancer;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "cloud_db": _S + "shape=mscae/database;fillColor=#A44E8A;fontColor=#FFFFFF;",
    "internet_gateway": _S + "shape=mscae/internet;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "nat_gateway": _S + "shape=mscae/nat_gateway;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "security_group": _S + "shape=mscae/security;fillColor=#B0343C;fontColor=#FFFFFF;",
    "generic": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8E8E8;",
}

_EDGE_STYLE_BY_LINK_STYLE: dict[LinkStyle, str] = {
    "solid": "endArrow=none;html=1;rounded=0;",
    "dashed": "endArrow=none;html=1;rounded=0;dashed=1;",
    "dotted": "endArrow=none;html=1;rounded=0;dashed=1;dashPattern=1 4;",
}

_GS = "rounded=1;whiteSpace=wrap;html=1;verticalAlign=bottom;fontSize=12;"
_GROUP_STYLE_BY_TYPE: dict[str, str] = {
    "subnet": _GS + "fillColor=#F5F5F5;strokeColor=#9E9E9E;",
    "vlan": _GS + "fillColor=#FFF8E1;strokeColor=#F9A825;",
    "vpc": _GS + "fillColor=#E8F5E9;strokeColor=#2E7D32;",
    "availability_zone": _GS + "fillColor=#E3F2FD;strokeColor=#1565C0;dashed=1;",
    "region": _GS + "fillColor=#EDE7F6;strokeColor=#4527A0;",
    "zone": _GS + "fillColor=#F5F5F5;strokeColor=#9E9E9E;",
    "dmz": _GS + "fillColor=#FFEBEE;strokeColor=#C62828;",
}


class DrawioRenderer:
    format = "drawio"
    extension = ".drawio"

    def render(self, diagram: LayoutedDiagram) -> str:
        mxfile = etree.Element("mxfile", host="netdiagram")
        dia = etree.SubElement(
            mxfile, "diagram", id="main", name=diagram.diagram.metadata.title
        )
        model = etree.SubElement(
            dia,
            "mxGraphModel",
            dx=str(int(diagram.canvas_width)),
            dy=str(int(diagram.canvas_height)),
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(int(diagram.canvas_width)),
            pageHeight=str(int(diagram.canvas_height)),
            math="0",
            shadow="0",
        )
        root = etree.SubElement(model, "root")
        etree.SubElement(root, "mxCell", id="0")
        etree.SubElement(root, "mxCell", id="1", parent="0")

        # Emit groups first (ordered from outermost to innermost so children can reference parents).
        group_ids: set[str] = set()
        for pg in _order_groups(diagram):
            self._append_group(root, pg)
            group_ids.add(pg.group.id)

        for pn in diagram.nodes:
            parent = f"group-{pn.node.group}" if pn.node.group in group_ids else "1"
            self._append_node(root, pn, parent=parent)

        for i, re in enumerate(diagram.edges):
            self._append_edge(root, re, edge_index=i)

        etree.indent(mxfile, space="  ")
        return etree.tostring(mxfile, xml_declaration=True, encoding="utf-8").decode("utf-8")

    def _append_group(self, root: etree._Element, pg) -> None:
        style = _GROUP_STYLE_BY_TYPE.get(pg.group.type, _GROUP_STYLE_BY_TYPE["zone"])
        parent = f"group-{pg.group.parent}" if pg.group.parent else "1"
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"group-{pg.group.id}",
            value=pg.group.label,
            style=style,
            vertex="1",
            parent=parent,
        )
        geom = etree.SubElement(
            cell,
            "mxGeometry",
            x=str(pg.x),
            y=str(pg.y),
            width=str(pg.width),
            height=str(pg.height),
        )
        geom.set("as", "geometry")

    def _append_node(self, root: etree._Element, pn: PositionedNode, parent: str = "1") -> None:
        style = _STYLE_BY_TYPE.get(pn.node.type, _STYLE_BY_TYPE["generic"])
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"node-{pn.node.id}",
            value=pn.node.label,
            style=style,
            vertex="1",
            parent=parent,
        )
        # When nested inside a group, geometry is relative to the group origin.
        if parent.startswith("group-"):
            pg = next(g for g in root.findall(".//mxCell") if g.get("id") == parent)
            gx = float(pg.find("mxGeometry").get("x"))
            gy = float(pg.find("mxGeometry").get("y"))
            rel_x = pn.x - gx
            rel_y = pn.y - gy
        else:
            rel_x = pn.x
            rel_y = pn.y
        geom = etree.SubElement(
            cell,
            "mxGeometry",
            x=str(rel_x),
            y=str(rel_y),
            width=str(pn.width),
            height=str(pn.height),
        )
        geom.set("as", "geometry")

    def _append_edge(self, root: etree._Element, re: RoutedEdge, edge_index: int) -> None:
        edge_id = f"edge-{edge_index}"
        style = _EDGE_STYLE_BY_LINK_STYLE[re.link.style]

        # Build a single consolidated label from interface names + link label.
        # This replaces the old 3-label approach (edge value + 2 arrowhead labels)
        # which caused visual clutter with parallel MLAG bonds.
        edge_label = _consolidated_edge_label(re.link)

        edge_cell = etree.SubElement(
            root,
            "mxCell",
            id=edge_id,
            value=edge_label,
            style=style,
            edge="1",
            parent="1",
            source=f"node-{re.link.source.node}",
            target=f"node-{re.link.target.node}",
        )
        geom = etree.SubElement(edge_cell, "mxGeometry", relative="1")
        # Emit interior waypoints from the routed path, if any.
        if len(re.path) > 2:
            arr = etree.SubElement(geom, "Array")
            arr.set("as", "points")
            for point in re.path[1:-1]:
                etree.SubElement(arr, "mxPoint", x=str(point.x), y=str(point.y))
        geom.set("as", "geometry")

def _consolidated_edge_label(link: Link) -> str:
    """Build a single edge label from interface names + link label.

    Replaces the old 3-label approach (edge value + 2 arrowhead child cells).
    Each parallel edge gets a unique label because interface names differ.
    """
    src = link.source.interface
    tgt = link.target.interface
    lbl = link.label

    if src and tgt and lbl:
        return f"{src} — {lbl} — {tgt}"
    if src and tgt:
        return f"{src} ↔ {tgt}"
    if src and lbl:
        return f"{src} — {lbl}"
    if tgt and lbl:
        return f"{lbl} — {tgt}"
    if lbl:
        return lbl
    if src:
        return src
    if tgt:
        return tgt
    return ""


def _order_groups(diagram: LayoutedDiagram):
    """Yield PositionedGroup objects ordered outermost-first (parents before children)."""
    by_id = {pg.group.id: pg for pg in diagram.groups}
    ordered: list = []
    visited: set[str] = set()

    def visit(gid: str) -> None:
        if gid in visited:
            return
        pg = by_id[gid]
        if pg.group.parent:
            visit(pg.group.parent)
        visited.add(gid)
        ordered.append(pg)

    for gid in by_id:
        visit(gid)
    return ordered
