"""Base protocol for diagram renderers."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from netdiagram.layout.types import LayoutedDiagram


@runtime_checkable
class Renderer(Protocol):
    format: str
    extension: str

    def render(self, diagram: LayoutedDiagram) -> str:
        """Render the laid-out diagram to the target format as a string."""
        ...
