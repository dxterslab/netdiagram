# Label Collision Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect and resolve overlapping interface labels on edges so port annotations (e.g., `swp37`, `gi0/1`) don't pile on top of each other when many edges converge on the same node.

**Architecture:** A new `src/netdiagram/layout/labels.py` module computes absolute pixel positions for every edge label, detects bounding-box collisions, and nudges colliding labels perpendicular to their edge. The engine calls this after edge routing. The Draw.io renderer reads the computed positions from `RoutedEdge.source_label_pos` / `target_label_pos` (existing fields, currently `None`) and emits absolute `mxGeometry` when set, falling back to the current relative `±0.7` when `None`.

**Tech Stack:** Pure Python. No new deps. Uses `dimensions._CHAR_WIDTH_PX` for label width estimation.

**Spec reference:** `docs/superpowers/specs/2026-04-14-network-diagram-design.md` (§Layout Engine — "Label placement — position interface labels and link annotations so they don't overlap nodes or other labels").

---

## File Structure

```
src/netdiagram/layout/
  labels.py           # NEW — label bbox computation, collision detection, resolution
  engine.py           # Modify — call label placement after edge routing
src/netdiagram/renderers/
  drawio.py           # Modify — use absolute label positions when set
tests/
  test_layout_labels.py  # NEW — unit tests for label collision logic
  test_renderer_drawio.py # Modify — test label offset emission
```

---

## Task 1: Label bounding box computation + collision detection + resolution

**Files:**
- Create: `src/netdiagram/layout/labels.py`
- Create: `tests/test_layout_labels.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_labels.py`:

```python
"""Unit tests for label bounding-box computation and collision resolution."""

from netdiagram.layout.labels import LabelBox, detect_collisions, resolve_collisions
from netdiagram.layout.types import Point, RoutedEdge
from netdiagram.ir.models import Link, LinkEndpoint


def _edge(src_iface: str | None, tgt_iface: str | None) -> RoutedEdge:
    """Create a horizontal edge from (0,100) to (300,100) with optional interfaces."""
    return RoutedEdge(
        link=Link(
            source=LinkEndpoint(node="a", interface=src_iface),
            target=LinkEndpoint(node="b", interface=tgt_iface),
        ),
        path=[Point(0, 100), Point(300, 100)],
    )


def test_label_box_from_edge_source():
    from netdiagram.layout.labels import compute_label_boxes

    edges = [_edge("gi0/1", None)]
    boxes = compute_label_boxes(edges)
    assert len(boxes) == 1
    b = boxes[0]
    assert b.text == "gi0/1"
    assert b.width > 0
    assert b.height > 0
    # Source label sits near the source end of the edge
    assert b.x < 150  # closer to x=0 than to x=300


def test_label_box_from_edge_both_endpoints():
    from netdiagram.layout.labels import compute_label_boxes

    edges = [_edge("e0", "e1")]
    boxes = compute_label_boxes(edges)
    assert len(boxes) == 2
    src_box = next(b for b in boxes if b.text == "e0")
    tgt_box = next(b for b in boxes if b.text == "e1")
    # Source is near x=0, target near x=300
    assert src_box.x < tgt_box.x


def test_no_collisions_when_labels_far_apart():
    b1 = LabelBox(text="a", x=0, y=0, width=40, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="b", x=200, y=0, width=40, height=16, edge_index=1, role="source")
    assert detect_collisions([b1, b2]) == []


def test_collision_detected_when_overlapping():
    b1 = LabelBox(text="a", x=10, y=90, width=40, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="b", x=20, y=92, width=40, height=16, edge_index=1, role="source")
    collisions = detect_collisions([b1, b2])
    assert len(collisions) >= 1
    assert (0, 1) in collisions or (1, 0) in collisions


def test_resolve_collisions_separates_overlapping_labels():
    b1 = LabelBox(text="swp37", x=10, y=90, width=50, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="swp38", x=15, y=92, width=50, height=16, edge_index=1, role="source")
    b3 = LabelBox(text="swp40", x=12, y=91, width=50, height=16, edge_index=2, role="source")
    resolved = resolve_collisions([b1, b2, b3])
    # After resolution, no pair should overlap
    for i in range(len(resolved)):
        for j in range(i + 1, len(resolved)):
            a, b = resolved[i], resolved[j]
            overlap_x = a.x + a.width > b.x and b.x + b.width > a.x
            overlap_y = a.y + a.height > b.y and b.y + b.height > a.y
            assert not (overlap_x and overlap_y), (
                f"labels '{a.text}' and '{b.text}' still overlap after resolution"
            )


def test_resolve_no_ops_when_no_collisions():
    b1 = LabelBox(text="a", x=0, y=0, width=40, height=16, edge_index=0, role="source")
    b2 = LabelBox(text="b", x=200, y=0, width=40, height=16, edge_index=1, role="source")
    resolved = resolve_collisions([b1, b2])
    # Positions should be unchanged
    assert resolved[0].y == 0
    assert resolved[1].y == 0
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest tests/test_layout_labels.py -v`
Expected: `ImportError: No module named 'netdiagram.layout.labels'`

- [ ] **Step 3: Implement labels module**

Create `src/netdiagram/layout/labels.py`:

```python
"""Label bounding-box computation and collision resolution.

Given a list of RoutedEdges, this module:
1. Computes the pixel bounding box of each interface label at its default
   position along the edge path.
2. Detects overlapping label pairs.
3. Nudges colliding labels perpendicular to their edge direction until
   no overlaps remain (up to a max iteration cap).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from netdiagram.layout.types import Point, RoutedEdge

# Approximate character metrics (same constants as dimensions.py).
_CHAR_WIDTH_PX = 7.0
_LABEL_PADDING_PX = 8.0
_LABEL_HEIGHT_PX = 16.0

# Default fraction along the edge where labels sit (matching drawio ±0.7
# mapped to 0..1 range: source at 0.15, target at 0.85).
_SOURCE_FRACTION = 0.15
_TARGET_FRACTION = 0.85

_NUDGE_STEP_PX = 20.0
_MAX_ITERATIONS = 50


@dataclass
class LabelBox:
    text: str
    x: float
    y: float
    width: float
    height: float
    edge_index: int
    role: str  # "source" or "target"


def compute_label_boxes(edges: list[RoutedEdge]) -> list[LabelBox]:
    """Compute a LabelBox for every interface label in the edge list."""
    out: list[LabelBox] = []
    for i, edge in enumerate(edges):
        if edge.link.source.interface:
            pos = _point_along_path(edge.path, _SOURCE_FRACTION)
            w = _label_width(edge.link.source.interface)
            out.append(
                LabelBox(
                    text=edge.link.source.interface,
                    x=pos.x - w / 2,
                    y=pos.y - _LABEL_HEIGHT_PX / 2,
                    width=w,
                    height=_LABEL_HEIGHT_PX,
                    edge_index=i,
                    role="source",
                )
            )
        if edge.link.target.interface:
            pos = _point_along_path(edge.path, _TARGET_FRACTION)
            w = _label_width(edge.link.target.interface)
            out.append(
                LabelBox(
                    text=edge.link.target.interface,
                    x=pos.x - w / 2,
                    y=pos.y - _LABEL_HEIGHT_PX / 2,
                    width=w,
                    height=_LABEL_HEIGHT_PX,
                    edge_index=i,
                    role="target",
                )
            )
    return out


def detect_collisions(boxes: list[LabelBox]) -> list[tuple[int, int]]:
    """Return index pairs of overlapping label boxes."""
    collisions: list[tuple[int, int]] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _overlap(boxes[i], boxes[j]):
                collisions.append((i, j))
    return collisions


def resolve_collisions(boxes: list[LabelBox]) -> list[LabelBox]:
    """Nudge overlapping labels apart by shifting them vertically.

    Returns a new list of LabelBox with adjusted y positions."""
    work = [
        LabelBox(
            text=b.text, x=b.x, y=b.y, width=b.width, height=b.height,
            edge_index=b.edge_index, role=b.role,
        )
        for b in boxes
    ]
    for _ in range(_MAX_ITERATIONS):
        pairs = detect_collisions(work)
        if not pairs:
            break
        for i, j in pairs:
            a, b = work[i], work[j]
            # Push the later label downward (or the earlier upward)
            a.y -= _NUDGE_STEP_PX / 2
            b.y += _NUDGE_STEP_PX / 2
    return work


def _label_width(text: str) -> float:
    return len(text) * _CHAR_WIDTH_PX + _LABEL_PADDING_PX


def _overlap(a: LabelBox, b: LabelBox) -> bool:
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )


def _point_along_path(path: list[Point], fraction: float) -> Point:
    """Return the point at the given fraction (0..1) along a polyline path."""
    if len(path) < 2:
        return path[0] if path else Point(0, 0)

    # Compute total length and walk segments.
    segments: list[tuple[float, int]] = []  # (cumulative_length, segment_index)
    total = 0.0
    for k in range(len(path) - 1):
        dx = path[k + 1].x - path[k].x
        dy = path[k + 1].y - path[k].y
        seg_len = math.hypot(dx, dy)
        total += seg_len
        segments.append((total, k))

    if total == 0:
        return path[0]

    target_dist = fraction * total
    for cum_len, k in segments:
        seg_start_dist = cum_len - math.hypot(
            path[k + 1].x - path[k].x, path[k + 1].y - path[k].y
        )
        if cum_len >= target_dist:
            seg_len = cum_len - seg_start_dist
            if seg_len == 0:
                return path[k]
            t = (target_dist - seg_start_dist) / seg_len
            x = path[k].x + t * (path[k + 1].x - path[k].x)
            y = path[k].y + t * (path[k + 1].y - path[k].y)
            return Point(x, y)

    return path[-1]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_layout_labels.py -v`
Expected: all 7 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/layout/labels.py tests/test_layout_labels.py
git commit -m "feat(layout): label bbox computation + collision detection and resolution"
```

---

## Task 2: Wire label placement into the engine

**Files:**
- Modify: `src/netdiagram/layout/engine.py`
- Modify: `tests/test_layout_engine.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_layout_engine.py`:

```python
def test_parallel_edges_get_non_overlapping_label_positions():
    """When two parallel edges have source interface labels, the computed
    label positions should not overlap."""
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router",
                 interfaces=[Interface(id="swp50"), Interface(id="swp52")]),
            Node(id="b", label="b", type="router",
                 interfaces=[Interface(id="swp50"), Interface(id="swp52")]),
        ],
        links=[
            Link(source=LinkEndpoint(node="a", interface="swp50"),
                 target=LinkEndpoint(node="b", interface="swp50")),
            Link(source=LinkEndpoint(node="a", interface="swp52"),
                 target=LinkEndpoint(node="b", interface="swp52")),
        ],
    )
    laid = layout_diagram(d)
    # Both edges should have non-None source_label_pos
    for edge in laid.edges:
        assert edge.source_label_pos is not None
        assert edge.target_label_pos is not None
    # The source label positions should differ (collision resolved)
    sp0 = laid.edges[0].source_label_pos
    sp1 = laid.edges[1].source_label_pos
    assert (sp0.x, sp0.y) != (sp1.x, sp1.y), "source labels must not overlap"
```

- [ ] **Step 2: Verify it fails**

Run: `uv run pytest tests/test_layout_engine.py::test_parallel_edges_get_non_overlapping_label_positions -v`
Expected: FAIL — `source_label_pos` is `None` (never populated).

- [ ] **Step 3: Call label placement in `layout_diagram`**

Modify `src/netdiagram/layout/engine.py`. Add import:

```python
from netdiagram.layout.labels import compute_label_boxes, resolve_collisions
```

In `layout_diagram`, after `laid.edges = _route_edges(diagram, laid)`, add:

```python
    # Resolve label collisions and store computed positions on each edge.
    _place_labels(laid)
```

Then add the helper function at module level:

```python
def _place_labels(laid: LayoutedDiagram) -> None:
    """Compute collision-free positions for interface labels on edges."""
    boxes = compute_label_boxes(laid.edges)
    if not boxes:
        return
    resolved = resolve_collisions(boxes)
    # Map resolved boxes back to their edges.
    for box in resolved:
        edge = laid.edges[box.edge_index]
        pos = Point(box.x + box.width / 2, box.y + box.height / 2)
        if box.role == "source":
            edge.source_label_pos = pos
        else:
            edge.target_label_pos = pos
```

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_layout_engine.py::test_parallel_edges_get_non_overlapping_label_positions -v`
Expected: PASS.

- [ ] **Step 5: Run full suite**

Run: `uv run pytest`
Expected: all tests pass. Existing tests don't assert `source_label_pos is None` so populating it is backward-compatible.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/layout/engine.py tests/test_layout_engine.py
git commit -m "feat(layout): wire label collision resolution into engine pipeline"
```

---

## Task 3: Draw.io renderer uses computed label positions

**Files:**
- Modify: `src/netdiagram/renderers/drawio.py`
- Modify: `tests/test_renderer_drawio.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_renderer_drawio.py`:

```python
def test_label_uses_computed_position_when_set():
    """When source_label_pos is set on a RoutedEdge, the renderer should
    emit the label with the computed y offset instead of the default y=0."""
    from netdiagram.layout.types import (
        LayoutedDiagram,
        Point,
        PositionedNode,
        RoutedEdge,
    )

    diagram = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router",
                 interfaces=[Interface(id="gi0/1")]),
            Node(id="b", label="b", type="router",
                 interfaces=[Interface(id="gi0/2")]),
        ],
        links=[
            Link(
                source=LinkEndpoint(node="a", interface="gi0/1"),
                target=LinkEndpoint(node="b", interface="gi0/2"),
            )
        ],
    )
    pn_a = PositionedNode(node=diagram.nodes[0], x=40, y=40, width=100, height=60)
    pn_b = PositionedNode(node=diagram.nodes[1], x=400, y=40, width=100, height=60)
    edge = RoutedEdge(
        link=diagram.links[0],
        path=[Point(90, 70), Point(450, 70)],
        source_label_pos=Point(90, 50),   # shifted up from default
        target_label_pos=Point(450, 90),  # shifted down from default
    )
    laid = LayoutedDiagram(
        diagram=diagram,
        nodes=[pn_a, pn_b],
        edges=[edge],
        canvas_width=600,
        canvas_height=200,
    )
    xml = DrawioRenderer().render(laid)
    root = _parse(xml)

    # Find the source label cell (parent = edge, value = "gi0/1")
    edge_cell = next(c for c in root.findall(".//mxCell") if c.get("edge") == "1")
    edge_id = edge_cell.get("id")
    label_cells = [
        c for c in root.findall(".//mxCell") if c.get("parent") == edge_id
    ]
    src_label = next(c for c in label_cells if c.get("value") == "gi0/1")
    tgt_label = next(c for c in label_cells if c.get("value") == "gi0/2")

    # Source label should have an offset reflecting the computed position
    src_geom = src_label.find("mxGeometry")
    tgt_geom = tgt_label.find("mxGeometry")

    # The offset mxPoint should exist and have non-zero values
    src_offset = src_geom.find("mxPoint")
    tgt_offset = tgt_geom.find("mxPoint")
    assert src_offset is not None
    assert tgt_offset is not None
    # Source was shifted up (y=50 vs default ~70), so offset.y should be negative
    src_offset_y = float(src_offset.get("y", "0"))
    tgt_offset_y = float(tgt_offset.get("y", "0"))
    assert src_offset_y < 0, f"source label should be shifted up, got offset y={src_offset_y}"
    assert tgt_offset_y > 0, f"target label should be shifted down, got offset y={tgt_offset_y}"
```

- [ ] **Step 2: Verify it fails**

Run: `uv run pytest tests/test_renderer_drawio.py::test_label_uses_computed_position_when_set -v`
Expected: FAIL — current renderer ignores `source_label_pos` and always emits `y="0"`.

- [ ] **Step 3: Update `_append_edge` to pass computed positions**

Modify `src/netdiagram/renderers/drawio.py`. In `_append_edge`, update the calls to `_append_endpoint_label` to pass the edge's computed label position:

Replace the interface-label block at the end of `_append_edge`:

```python
        if re.link.source.interface:
            self._append_endpoint_label(
                root,
                parent_id=edge_id,
                label=re.link.source.interface,
                position=-0.7,
                cell_id=f"{edge_id}-src-label",
                label_pos=re.source_label_pos,
                path=re.path,
                fraction=0.15,
            )
        if re.link.target.interface:
            self._append_endpoint_label(
                root,
                parent_id=edge_id,
                label=re.link.target.interface,
                position=0.7,
                cell_id=f"{edge_id}-tgt-label",
                label_pos=re.target_label_pos,
                path=re.path,
                fraction=0.85,
            )
```

Then update `_append_endpoint_label` to compute a perpendicular `y` offset when `label_pos` is set:

```python
    def _append_endpoint_label(
        self,
        root: etree._Element,
        parent_id: str,
        label: str,
        position: float,
        cell_id: str,
        label_pos: Point | None = None,
        path: list[Point] | None = None,
        fraction: float = 0.5,
    ) -> None:
        cell = etree.SubElement(
            root,
            "mxCell",
            id=cell_id,
            value=label,
            style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];",
            vertex="1",
            connectable="0",
            parent=parent_id,
        )
        # Compute perpendicular offset from the computed absolute label position.
        y_offset = 0.0
        if label_pos is not None and path and len(path) >= 2:
            default_pos = _point_along_path(path, fraction)
            y_offset = label_pos.y - default_pos.y

        geom = etree.SubElement(
            cell, "mxGeometry", x=str(position), y="0", relative="1"
        )
        offset_pt = etree.SubElement(geom, "mxPoint", x="0", y=str(y_offset))
        offset_pt.set("as", "offset")
        geom.set("as", "geometry")
```

Also add the `_point_along_path` helper at module level (import from labels or copy):

```python
from netdiagram.layout.labels import _point_along_path
```

Wait — `_point_along_path` is private (underscore). Better to make it importable. Add to `src/netdiagram/layout/labels.py` a clean public name by aliasing it:

Actually, just import it — Python doesn't enforce the underscore convention. Add at the top of `drawio.py`:

```python
from netdiagram.layout.labels import _point_along_path as _point_along_path
```

Or cleaner: rename it to `point_along_path` (no underscore) in `labels.py` and import as `from netdiagram.layout.labels import point_along_path`. Do this rename in `labels.py` first — it's only used internally there plus now from `drawio.py`.

Also add the `Point` import to drawio.py if not already there:

```python
from netdiagram.layout.types import LayoutedDiagram, Point, PositionedNode, RoutedEdge
```

(Check if `Point` is already imported — it may be from the waypoints task.)

- [ ] **Step 4: Run the test**

Run: `uv run pytest tests/test_renderer_drawio.py::test_label_uses_computed_position_when_set -v`
Expected: PASS.

- [ ] **Step 5: Run full suite**

Run: `uv run pytest`
Expected: all tests pass. Existing tests that check for label cells should still work because the mxPoint offset with `y="0"` is structurally identical to the current output when `source_label_pos is None`.

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/layout/labels.py src/netdiagram/renderers/drawio.py tests/test_renderer_drawio.py
git commit -m "feat(renderer): emit computed label offsets in Draw.io to avoid collisions"
```

---

## Wrap-Up

- [ ] **Final full suite + lint**

Run:
```bash
uv run pytest
uv run ruff check src tests
```

Expected: all tests pass, ruff clean.

- [ ] **Manual verification**

1. Render the Qumulo-to-spines diagram (5 storage nodes with port labels converging on spine-sw01):
   ```bash
   PYTHONPATH=src uv run netdiagram render \
     /Users/dexter/Documents/dev/yyc-network-revamp/diagrams/qumulo-to-spines.yaml \
     --output /tmp/qumulo-labels.drawio
   ```
2. Open in Draw.io and check:
   - `swp37`, `swp38`, `swp40`, `swp41`, `swp42` labels on the spine side should NOT stack on top of each other
   - `nic1`, `nic2` labels on the Qumulo side should be visible and distinct
3. Compare with the pre-label-collision version to see the improvement.

- [ ] **Tag**

```bash
git tag phase-2d-label-collision
```
