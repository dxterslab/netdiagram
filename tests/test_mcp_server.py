"""Unit tests for MCP server tool functions.

Tools are plain Python functions after FastMCP decoration, so tests call
them directly rather than going through the MCP protocol.
"""

from netdiagram.mcp_server import get_schema, list_types, validate_diagram


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


def _minimal_valid_ir() -> dict:
    return {
        "version": "1.0",
        "metadata": {"title": "T", "type": "physical"},
        "nodes": [{"id": "r1", "label": "r1", "type": "router"}],
    }


def test_validate_diagram_accepts_valid_ir():
    result = validate_diagram(_minimal_valid_ir())
    assert result == {"valid": True, "errors": []}


def test_validate_diagram_rejects_invalid_and_reports_errors():
    ir = _minimal_valid_ir()
    ir["links"] = [
        {"source": {"node": "r1"}, "target": {"node": "ghost"}}
    ]
    result = validate_diagram(ir)
    assert result["valid"] is False
    assert len(result["errors"]) >= 1
    # Each error is {"loc": "...", "msg": "..."}
    for err in result["errors"]:
        assert "loc" in err and "msg" in err
    # The message for an unknown-node link should surface in at least one error
    joined = " ".join(err["msg"] for err in result["errors"])
    assert "ghost" in joined


def test_validate_diagram_rejects_unknown_node_type():
    ir = _minimal_valid_ir()
    ir["nodes"][0]["type"] = "toaster"
    result = validate_diagram(ir)
    assert result["valid"] is False
