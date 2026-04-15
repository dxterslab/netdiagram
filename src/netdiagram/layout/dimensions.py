"""Compute rendered dimensions for nodes based on label and type.

Returns pixel sizes that downstream renderers can use directly. The numbers
are calibrated for Draw.io's default font (Helvetica 12pt) — other renderers
may scale as needed.
"""

from __future__ import annotations

from netdiagram.ir.models import Node

# Approximate pixel width per character at 12pt Helvetica.
_CHAR_WIDTH_PX = 7.0
_LABEL_PADDING_PX = 24.0
_MIN_WIDTH_PX = 80.0
_MIN_HEIGHT_PX = 60.0

# Types that want a slightly larger default so icons read clearly.
_LARGE_TYPES = {"firewall", "load_balancer", "cloud_lb", "cloud_db"}


def compute_node_size(node: Node) -> tuple[float, float]:
    label_width = len(node.label) * _CHAR_WIDTH_PX + _LABEL_PADDING_PX
    min_w = 100.0 if node.type in _LARGE_TYPES else _MIN_WIDTH_PX
    min_h = 70.0 if node.type in _LARGE_TYPES else _MIN_HEIGHT_PX
    return max(min_w, label_width), min_h
