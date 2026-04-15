"""JSON Schema generation for the Diagram IR."""

from __future__ import annotations

from typing import Any

from netdiagram.ir.models import Diagram


def diagram_json_schema() -> dict[str, Any]:
    """Return a JSON Schema (draft 2020-12) for the Diagram IR."""
    schema = Diagram.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["title"] = "Diagram"
    return schema
