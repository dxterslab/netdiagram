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

app = FastMCP("netdiagram")


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


def main() -> None:
    """Entry point for the `netdiagram-mcp` console script."""
    app.run()


if __name__ == "__main__":
    main()
