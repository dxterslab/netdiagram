"""Unit tests for MCP server tool functions.

Tools are plain Python functions after FastMCP decoration, so tests call
them directly rather than going through the MCP protocol.
"""

from netdiagram.mcp_server import get_schema, list_types


def test_get_schema_returns_diagram_schema():
    s = get_schema()
    assert s["title"] == "Diagram"
    assert s["$schema"].startswith("https://json-schema.org/")
    assert "properties" in s
    assert "nodes" in s["properties"]


def test_list_types_includes_physical_and_cloud_nodes():
    types = list_types()
    assert "node_types" in types
    assert "group_types" in types
    assert "router" in types["node_types"]
    assert "firewall" in types["node_types"]
    assert "vpc" in types["node_types"]
    assert "subnet" in types["group_types"]
    assert "availability_zone" in types["group_types"]


def test_list_types_values_are_string_lists():
    types = list_types()
    for nt in types["node_types"]:
        assert isinstance(nt, str)
    for gt in types["group_types"]:
        assert isinstance(gt, str)
