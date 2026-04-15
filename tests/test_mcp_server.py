"""Unit tests for MCP server tool functions.

Tools are plain Python functions after FastMCP decoration, so tests call
them directly rather than going through the MCP protocol.
"""

from netdiagram.mcp_server import get_schema


def test_get_schema_returns_diagram_schema():
    s = get_schema()
    assert s["title"] == "Diagram"
    assert s["$schema"].startswith("https://json-schema.org/")
    assert "properties" in s
    assert "nodes" in s["properties"]
