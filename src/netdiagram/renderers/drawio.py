"""Draw.io (mxGraph XML) renderer."""

from __future__ import annotations

from lxml import etree

from netdiagram.ir.models import LinkStyle, NodeType
from netdiagram.layout.types import LayoutedDiagram, PositionedNode, RoutedEdge

_STYLE_BY_TYPE: dict[NodeType, str] = {
    "router": "shape=mscae/router;html=1;whiteSpace=wrap;fillColor=#1B5E9E;fontColor=#FFFFFF;",
    "switch": "shape=mscae/switch;html=1;whiteSpace=wrap;fillColor=#0072C6;fontColor=#FFFFFF;",
    "firewall": "shape=cisco/firewall;html=1;whiteSpace=wrap;fillColor=#B0343C;fontColor=#FFFFFF;",
    "server": "shape=mscae/server;html=1;whiteSpace=wrap;fillColor=#5C8A3F;fontColor=#FFFFFF;",
    "load_balancer": "shape=mscae/load_balancer;html=1;whiteSpace=wrap;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "access_point": "shape=mscae/wireless_ap;html=1;whiteSpace=wrap;fillColor=#2C7873;fontColor=#FFFFFF;",
    "endpoint": "shape=mscae/workstation;html=1;whiteSpace=wrap;fillColor=#7A7A7A;fontColor=#FFFFFF;",
    "vpc": "shape=mscae/cloud;html=1;whiteSpace=wrap;fillColor=#D3E6F1;fontColor=#000000;",
    "cloud_lb": "shape=mscae/load_balancer;html=1;whiteSpace=wrap;fillColor=#7B5BA1;fontColor=#FFFFFF;",
    "cloud_db": "shape=mscae/database;html=1;whiteSpace=wrap;fillColor=#A44E8A;fontColor=#FFFFFF;",
    "internet_gateway": "shape=mscae/internet;html=1;whiteSpace=wrap;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "nat_gateway": "shape=mscae/nat_gateway;html=1;whiteSpace=wrap;fillColor=#3F7BC5;fontColor=#FFFFFF;",
    "security_group": "shape=mscae/security;html=1;whiteSpace=wrap;fillColor=#B0343C;fontColor=#FFFFFF;",
    "generic": "rounded=1;whiteSpace=wrap;html=1;fillColor=#E8E8E8;",
}

_EDGE_STYLE_BY_LINK_STYLE: dict[LinkStyle, str] = {
    "solid": "endArrow=none;html=1;rounded=0;",
    "dashed": "endArrow=none;html=1;rounded=0;dashed=1;",
    "dotted": "endArrow=none;html=1;rounded=0;dashed=1;dashPattern=1 4;",
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

        for pn in diagram.nodes:
            self._append_node(root, pn)

        for i, re in enumerate(diagram.edges):
            self._append_edge(root, re, edge_index=i)

        etree.indent(mxfile, space="  ")
        return etree.tostring(mxfile, xml_declaration=True, encoding="utf-8").decode("utf-8")

    def _append_node(self, root: etree._Element, pn: PositionedNode) -> None:
        style = _STYLE_BY_TYPE.get(pn.node.type, _STYLE_BY_TYPE["generic"])
        cell = etree.SubElement(
            root,
            "mxCell",
            id=f"node-{pn.node.id}",
            value=pn.node.label,
            style=style,
            vertex="1",
            parent="1",
        )
        geom = etree.SubElement(
            cell,
            "mxGeometry",
            x=str(pn.x),
            y=str(pn.y),
            width=str(pn.width),
            height=str(pn.height),
        )
        geom.set("as", "geometry")

    def _append_edge(self, root: etree._Element, re: RoutedEdge, edge_index: int) -> None:
        edge_id = f"edge-{edge_index}"
        style = _EDGE_STYLE_BY_LINK_STYLE[re.link.style]
        edge_cell = etree.SubElement(
            root,
            "mxCell",
            id=edge_id,
            value=re.link.label or "",
            style=style,
            edge="1",
            parent="1",
            source=f"node-{re.link.source.node}",
            target=f"node-{re.link.target.node}",
        )
        geom = etree.SubElement(edge_cell, "mxGeometry", relative="1")
        geom.set("as", "geometry")

        # Interface labels as child cells anchored to the edge.
        if re.link.source.interface:
            self._append_endpoint_label(
                root, parent_id=edge_id, label=re.link.source.interface, position=-0.7
            )
        if re.link.target.interface:
            self._append_endpoint_label(
                root, parent_id=edge_id, label=re.link.target.interface, position=0.7
            )

    def _append_endpoint_label(
        self, root: etree._Element, parent_id: str, label: str, position: float
    ) -> None:
        # In Draw.io, edge labels are child mxCells with a geometry x in [-1, 1]
        # representing position along the edge (-1 = source, 1 = target).
        cell = etree.SubElement(
            root,
            "mxCell",
            value=label,
            style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];",
            vertex="1",
            connectable="0",
            parent=parent_id,
        )
        geom = etree.SubElement(cell, "mxGeometry", x=str(position), y="0", relative="1")
        etree.SubElement(geom, "mxPoint").set("as", "offset")
        geom.set("as", "geometry")
