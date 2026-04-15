"""Unit tests for MCP server tool functions.

Tools are plain Python functions after FastMCP decoration, so tests call
them directly rather than going through the MCP protocol.
"""

from netdiagram.mcp_server import (
    get_schema,
    list_types,
    preview_layout,
    render_diagram,
    validate_diagram,
)


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


def test_render_diagram_returns_drawio_xml():
    ir = _minimal_valid_ir()
    ir["nodes"].append({"id": "r2", "label": "r2", "type": "router"})
    ir["links"] = [{"source": {"node": "r1"}, "target": {"node": "r2"}}]

    result = render_diagram(ir, "drawio")
    assert result["format"] == "drawio"
    assert result["filename"].endswith(".drawio")
    assert "<mxfile" in result["content"]


def test_render_diagram_rejects_unknown_format():
    result = render_diagram(_minimal_valid_ir(), "mermaid")
    assert result["error"] is not None
    assert "unsupported format" in result["error"].lower()


def test_render_diagram_rejects_invalid_ir():
    ir = _minimal_valid_ir()
    ir["nodes"][0]["type"] = "not-a-real-type"
    result = render_diagram(ir, "drawio")
    assert result["error"] is not None
    assert "validation" in result["error"].lower() or "invalid" in result["error"].lower()


def test_preview_layout_returns_positioned_nodes_and_edges():
    ir = _minimal_valid_ir()
    ir["nodes"].append({"id": "r2", "label": "r2", "type": "router"})
    ir["links"] = [{"source": {"node": "r1"}, "target": {"node": "r2"}}]

    result = preview_layout(ir)
    assert "nodes" in result
    assert "edges" in result
    assert "canvas_width" in result
    assert "canvas_height" in result

    ids = {n["id"] for n in result["nodes"]}
    assert ids == {"r1", "r2"}
    for n in result["nodes"]:
        assert set(n.keys()) >= {"id", "x", "y", "width", "height"}
        assert n["width"] > 0 and n["height"] > 0

    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["source"] == "r1" and edge["target"] == "r2"
    assert len(edge["path"]) >= 2
    for point in edge["path"]:
        assert "x" in point and "y" in point


def test_preview_layout_rejects_invalid_ir():
    ir = _minimal_valid_ir()
    ir["nodes"][0]["type"] = "not-real"
    result = preview_layout(ir)
    assert "error" in result
