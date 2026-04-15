"""Typer-based CLI for netdiagram."""

from __future__ import annotations

import json
import typing as t
from pathlib import Path

import typer

from netdiagram.ir.loader import LoaderError, load_diagram
from netdiagram.ir.models import GroupType, NodeType
from netdiagram.ir.schema import diagram_json_schema
from netdiagram.layout import layout_diagram
from netdiagram.renderers.d2 import D2Renderer
from netdiagram.renderers.drawio import DrawioRenderer

app = typer.Typer(help="LLM-friendly network diagram tool.")

_RENDERERS = {
    "drawio": DrawioRenderer(),
    "d2": D2Renderer(),
}


@app.command()
def validate(
    path: Path = typer.Argument(..., exists=False, help="Path to a YAML or JSON diagram IR file."),
) -> None:
    """Validate a diagram file against the IR schema."""
    try:
        load_diagram(path)
    except LoaderError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)
    typer.echo(f"{path}: valid")


@app.command()
def render(
    path: Path = typer.Argument(..., help="Path to a YAML or JSON diagram IR file."),
    fmt: str = typer.Option(
        "drawio", "--format", "-f", help="Output format: drawio (more in later phases)."
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output file path. Defaults to <input>.<ext>."
    ),
) -> None:
    """Render a diagram file to the chosen format."""
    try:
        diagram = load_diagram(path)
    except LoaderError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)

    renderer = _RENDERERS.get(fmt)
    if renderer is None:
        typer.echo(f"Unknown format '{fmt}'. Supported: {', '.join(_RENDERERS)}")
        raise typer.Exit(code=2)

    try:
        laid = layout_diagram(diagram)
        content = renderer.render(laid)
    except Exception as e:  # noqa: BLE001
        typer.echo(f"render failed: {e}")
        raise typer.Exit(code=3)

    out = output or path.with_suffix(renderer.extension)
    out.write_text(content, encoding="utf-8")
    typer.echo(f"Wrote {out}")


@app.command()
def schema() -> None:
    """Print the JSON Schema for the Diagram IR."""
    typer.echo(json.dumps(diagram_json_schema(), indent=2))


@app.command("list-types")
def list_types() -> None:
    """List supported node and group types."""
    typer.echo("Node types:")
    for nt in t.get_args(NodeType):
        typer.echo(f"  - {nt}")
    typer.echo()
    typer.echo("Group types:")
    for gt in t.get_args(GroupType):
        typer.echo(f"  - {gt}")


if __name__ == "__main__":
    app()
