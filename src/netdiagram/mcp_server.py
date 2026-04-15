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

from mcp.server.fastmcp import FastMCP

from netdiagram.ir.schema import diagram_json_schema

app = FastMCP("netdiagram")


@app.tool()
def get_schema() -> dict:
    """Return the JSON Schema (draft 2020-12) describing the netdiagram IR.

    The LLM should consult this schema when constructing IR objects to pass
    to validate_diagram or render_diagram.
    """
    return diagram_json_schema()


def main() -> None:
    """Entry point for the `netdiagram-mcp` console script."""
    app.run()


if __name__ == "__main__":
    main()
