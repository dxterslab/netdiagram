"""Load and validate diagram IR from YAML or JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from netdiagram.ir.models import Diagram


class LoaderError(Exception):
    """Raised when a diagram cannot be loaded or validated."""


def load_diagram(path: str | Path) -> Diagram:
    """Load a diagram IR from a YAML or JSON file. Raises LoaderError on any failure."""
    p = Path(path)
    if not p.exists():
        raise LoaderError(f"file not found: {p}")

    raw = p.read_text(encoding="utf-8")

    try:
        data = _parse(raw, p.suffix.lower())
    except yaml.YAMLError as e:
        raise LoaderError(f"YAML parse error in {p}: {e}") from e
    except json.JSONDecodeError as e:
        raise LoaderError(f"JSON parse error in {p}: {e}") from e

    try:
        return Diagram.model_validate(data)
    except ValidationError as e:
        raise LoaderError(_format_validation_error(p, e)) from e


def _parse(raw: str, suffix: str) -> Any:
    if suffix == ".json":
        return json.loads(raw)
    # Default to YAML for .yaml, .yml, or unknown extensions
    return yaml.safe_load(raw)


def _format_validation_error(path: Path, err: ValidationError) -> str:
    lines = [f"validation errors in {path}:"]
    for e in err.errors():
        loc = ".".join(str(x) for x in e["loc"]) or "<root>"
        lines.append(f"  {loc}: {e['msg']}")
    return "\n".join(lines)
