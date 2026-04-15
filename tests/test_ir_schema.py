import json

from netdiagram.ir.schema import diagram_json_schema


def test_schema_is_valid_json_schema():
    s = diagram_json_schema()
    assert s["$schema"].startswith("https://json-schema.org/")
    assert s["title"] == "Diagram"
    assert "properties" in s
    assert "nodes" in s["properties"]


def test_schema_includes_node_types_enum():
    s = diagram_json_schema()
    # Navigate to Node.type enum — Pydantic generates $defs with refs
    node_def = s["$defs"]["Node"]
    type_prop = node_def["properties"]["type"]
    assert "router" in type_prop["enum"]
    assert "vpc" in type_prop["enum"]


def test_schema_serializable():
    s = diagram_json_schema()
    # Must round-trip through JSON without loss
    json.dumps(s)
