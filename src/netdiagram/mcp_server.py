"""MCP server exposing the netdiagram pipeline to LLMs.

Launch via the `netdiagram-mcp` console script (stdio transport). The server
registers five tools:
    - get_schema: JSON Schema for the Diagram IR
    - list_types: supported node/group type literals
    - validate_diagram: validate an IR dict, return structured errors
    - render_diagram: full pipeline IR -> layout -> backend output
    - preview_layout: IR -> layout only, returns computed positions
"""

from __future__ import annotations

import typing as _t

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from netdiagram.ir.models import Diagram, GroupType, NodeType
from netdiagram.ir.schema import diagram_json_schema
from netdiagram.layout import layout_diagram
from netdiagram.renderers.d2 import D2Renderer
from netdiagram.renderers.drawio import DrawioRenderer

app = FastMCP("netdiagram")

_RENDERERS = {
    "drawio": DrawioRenderer(),
    "d2": D2Renderer(),
}


@app.tool()
def get_schema() -> dict:
    """Return the JSON Schema (draft 2020-12) describing the netdiagram IR.

    The LLM should consult this schema when constructing IR objects to pass
    to validate_diagram or render_diagram.
    """
    return diagram_json_schema()


@app.tool()
def list_types() -> dict:
    """Return the supported node and group type literals.

    Use this before constructing IR — each node and group must have a type
    drawn from these lists. Unknown types render as a neutral shape.
    """
    return {
        "node_types": list(_t.get_args(NodeType)),
        "group_types": list(_t.get_args(GroupType)),
    }


@app.tool()
def validate_diagram(ir: dict) -> dict:
    """Validate an IR dict against the Diagram schema.

    Returns {"valid": True, "errors": []} on success. On failure,
    {"valid": False, "errors": [{"loc": "field.path", "msg": "..."}]}.

    Use this before render_diagram so you can fix errors iteratively
    rather than seeing a render failure.
    """
    try:
        Diagram.model_validate(ir)
    except ValidationError as e:
        return {
            "valid": False,
            "errors": [
                {
                    "loc": ".".join(str(x) for x in err["loc"]) or "<root>",
                    "msg": err["msg"],
                }
                for err in e.errors()
            ],
        }
    return {"valid": True, "errors": []}


@app.tool()
def render_diagram(ir: dict, format: str = "drawio") -> dict:  # noqa: A002
    """Render an IR to a diagram file in the requested format.

    Returns {"format": ..., "filename": ..., "content": "..."} on success.
    On error, returns {"error": "message"}. Phase 1 supports only 'drawio'.
    """
    # Validate first so we fail fast with a clear message.
    try:
        diagram = Diagram.model_validate(ir)
    except ValidationError as e:
        return {
            "error": "validation failed",
            "errors": [
                {
                    "loc": ".".join(str(x) for x in err["loc"]) or "<root>",
                    "msg": err["msg"],
                }
                for err in e.errors()
            ],
        }

    renderer = _RENDERERS.get(format)
    if renderer is None:
        return {"error": f"unsupported format '{format}'. Available: {list(_RENDERERS)}"}

    try:
        laid = layout_diagram(diagram)
        content = renderer.render(laid)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"render failed: {exc}"}

    return {
        "format": format,
        "filename": f"{diagram.metadata.title.replace(' ', '-').lower()}{renderer.extension}",
        "content": content,
    }


@app.tool()
def preview_layout(ir: dict) -> dict:
    """Compute layout for an IR without rendering to a backend format.

    Returns positioned nodes, routed edges, and canvas bounds. Useful for
    reasoning about spacing before committing to a render.
    """
    try:
        diagram = Diagram.model_validate(ir)
    except ValidationError as e:
        return {
            "error": "validation failed",
            "errors": [
                {
                    "loc": ".".join(str(x) for x in err["loc"]) or "<root>",
                    "msg": err["msg"],
                }
                for err in e.errors()
            ],
        }

    try:
        laid = layout_diagram(diagram)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"layout failed: {exc}"}

    return {
        "canvas_width": laid.canvas_width,
        "canvas_height": laid.canvas_height,
        "nodes": [
            {
                "id": pn.node.id,
                "x": pn.x,
                "y": pn.y,
                "width": pn.width,
                "height": pn.height,
            }
            for pn in laid.nodes
        ],
        "edges": [
            {
                "source": routed.link.source.node,
                "target": routed.link.target.node,
                "path": [{"x": p.x, "y": p.y} for p in routed.path],
            }
            for routed in laid.edges
        ],
    }


def main() -> None:
    """Entry point for the `netdiagram-mcp` console script."""
    app.run()


if __name__ == "__main__":
    main()
