# Advanced Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Phase 1 straight-line edge routing with (1) parallel-edge fan-out and (2) orthogonal A* routing around node obstacles, then emit the resulting waypoints into Draw.io so MLAG bonds and busy topologies stay readable.

**Architecture:** A new `src/netdiagram/layout/routing.py` module owns obstacle-grid construction and A* pathfinding. `layout/engine.py` calls it from `_route_edges`, falling back to straight lines if A* fails. `renderers/drawio.py` emits the multi-point path as `<Array as="points">` inside `mxGeometry` so Draw.io honors our routing instead of running its own.

**Tech Stack:** Pure Python, stdlib `heapq` for A*. No new runtime dependencies. Existing stack.

**Spec reference:** `docs/superpowers/specs/2026-04-14-network-diagram-design.md` (§Layout Engine — "Edge routing with obstacle avoidance", "parallel edges get spacing").

**Out of scope (future phases):**
- Label collision resolution (punt until we see routing alone fix most cases)
- Group-boundary-aware routing (A* treats groups as non-obstacles; label strips remain a known limitation)
- Visibility-graph or libavoid-based routing (A* on grid is the first iteration)

---

## File Structure

```
src/netdiagram/layout/
  routing.py          # NEW — Grid, obstacles, A* pathfinder, path simplification
  engine.py           # Modify — _route_edges uses routing.py, adds parallel fan-out
src/netdiagram/renderers/
  drawio.py           # Modify — emit <Array as="points"> waypoints per edge
tests/
  test_layout_routing.py   # NEW — grid, A*, simplification unit tests
  test_layout_engine.py    # Modify — add routing/fan-out assertions
  test_renderer_drawio.py  # Modify — waypoint emission assertion
  test_end_to_end.py       # Modify — branch_office edge-geometry sanity check
```

**Why a separate `routing.py` file:** A* and grid math are pure and testable in isolation. Keeping them out of `engine.py` prevents the engine from growing unwieldy and makes future algorithm swaps (libavoid, visibility graph) low-friction.

---

## Task 1: Parallel-edge fan-out

**Files:**
- Modify: `src/netdiagram/layout/engine.py`
- Modify: `tests/test_layout_engine.py`

Problem: when two or more links connect the same `(source_node, target_node)` pair (e.g., spine peerlinks on swp50 AND swp52, or bond members), their paths currently overlap exactly. This task offsets each parallel edge's endpoint perpendicular to the connecting vector so they fan out visibly.

- [ ] **Step 1: Add failing test**

Append to `tests/test_layout_engine.py`:

```python
def test_parallel_edges_have_distinct_endpoints():
    """Two links between the same pair of nodes should not produce identical paths."""
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router",
                 interfaces=[Interface(id="e0"), Interface(id="e1")]),
            Node(id="b", label="b", type="router",
                 interfaces=[Interface(id="e0"), Interface(id="e1")]),
        ],
        links=[
            Link(source=LinkEndpoint(node="a", interface="e0"),
                 target=LinkEndpoint(node="b", interface="e0")),
            Link(source=LinkEndpoint(node="a", interface="e1"),
                 target=LinkEndpoint(node="b", interface="e1")),
        ],
    )
    laid = layout_diagram(d)
    assert len(laid.edges) == 2
    start_a = (laid.edges[0].path[0].x, laid.edges[0].path[0].y)
    start_b = (laid.edges[1].path[0].x, laid.edges[1].path[0].y)
    assert start_a != start_b, "parallel edges must fan out at the source endpoint"
    end_a = (laid.edges[0].path[-1].x, laid.edges[0].path[-1].y)
    end_b = (laid.edges[1].path[-1].x, laid.edges[1].path[-1].y)
    assert end_a != end_b, "parallel edges must fan out at the target endpoint"
```

- [ ] **Step 2: Verify it fails**

Run: `uv run pytest tests/test_layout_engine.py::test_parallel_edges_have_distinct_endpoints -v`
Expected: FAIL — both edges produce identical `path[0]` and `path[-1]` at the node centers.

- [ ] **Step 3: Implement fan-out in engine**

Modify `src/netdiagram/layout/engine.py`. Replace `_route_edges` and add a helper `_fan_out_offset`. Keep everything else. The full replacement body for those two functions:

```python
def _route_edges(diagram: Diagram, laid: LayoutedDiagram) -> list[RoutedEdge]:
    """Phase 2 routing: straight lines between endpoints, but fan parallel
    edges out perpendicular to the connecting vector so they don't overlap."""
    import math

    by_id = {pn.node.id: pn for pn in laid.nodes}

    # Group links by unordered node pair so peer peerlinks (a<->b and b<->a)
    # fan out together.
    pair_counts: dict[tuple[str, str], int] = {}
    for link in diagram.links:
        pair = tuple(sorted((link.source.node, link.target.node)))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    pair_index: dict[tuple[str, str], int] = dict.fromkeys(pair_counts, 0)

    out: list[RoutedEdge] = []
    for link in diagram.links:
        pair = tuple(sorted((link.source.node, link.target.node)))
        idx = pair_index[pair]
        total = pair_counts[pair]
        pair_index[pair] += 1

        s = by_id[link.source.node]
        t = by_id[link.target.node]
        sx, sy = s.x + s.width / 2, s.y + s.height / 2
        tx, ty = t.x + t.width / 2, t.y + t.height / 2

        dx_off, dy_off = _fan_out_offset(sx, sy, tx, ty, idx, total)
        start = Point(sx + dx_off, sy + dy_off)
        end = Point(tx + dx_off, ty + dy_off)
        out.append(RoutedEdge(link=link, path=[start, end]))
    return out


def _fan_out_offset(
    sx: float, sy: float, tx: float, ty: float, idx: int, total: int
) -> tuple[float, float]:
    """Return a perpendicular offset so the i-th of `total` parallel edges
    sits on its own line. Spacing is 14px between adjacent edges."""
    import math

    if total <= 1:
        return (0.0, 0.0)

    dx, dy = tx - sx, ty - sy
    length = math.hypot(dx, dy) or 1.0
    # Unit perpendicular.
    px, py = -dy / length, dx / length
    # Center the fan: edges at indices 0..total-1 map to offsets spread
    # around zero so the group stays visually centered on the node-to-node
    # line.
    spacing = 14.0
    offset = (idx - (total - 1) / 2.0) * spacing
    return (px * offset, py * offset)
```

Add `import math` at the top of the file alongside existing imports (or inline inside the function — either is fine; module-level is cleaner).

- [ ] **Step 4: Run the new test**

Run: `uv run pytest tests/test_layout_engine.py::test_parallel_edges_have_distinct_endpoints -v`
Expected: PASS.

- [ ] **Step 5: Run full layout tests**

Run: `uv run pytest tests/test_layout_engine.py -v`
Expected: all previously-passing tests still pass (the fan-out offset is `(0, 0)` for single edges, so non-parallel cases are untouched).

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/layout/engine.py tests/test_layout_engine.py
git commit -m "feat(layout): fan out parallel edges perpendicular to connecting vector"
```

---

## Task 2: Obstacle grid + A* pathfinder

**Files:**
- Create: `src/netdiagram/layout/routing.py`
- Create: `tests/test_layout_routing.py`

This task is standalone — `routing.py` is pure logic with no dependency on the engine. Task 3 wires it in.

- [ ] **Step 1: Write failing tests**

Create `tests/test_layout_routing.py`:

```python
"""Unit tests for the obstacle grid and A* pathfinder in routing.py."""

from netdiagram.layout.routing import (
    Obstacle,
    ObstacleGrid,
    find_path,
    simplify_path,
)


def test_grid_marks_obstacle_as_blocked():
    g = ObstacleGrid(width=100, height=100, cell_size=10)
    g.add_obstacle(Obstacle(x=40, y=40, width=20, height=20))
    # A cell squarely inside the obstacle is blocked
    assert g.is_blocked(45, 45) is True
    # A cell far from the obstacle is free
    assert g.is_blocked(5, 5) is False


def test_grid_respects_padding_around_obstacle():
    g = ObstacleGrid(width=100, height=100, cell_size=10, padding=10)
    g.add_obstacle(Obstacle(x=40, y=40, width=20, height=20))
    # Cell 10px outside the obstacle's right edge is still blocked due to padding
    assert g.is_blocked(65, 50) is True
    # Cell 25px outside is free
    assert g.is_blocked(85, 50) is False


def test_find_path_direct_when_no_obstacles():
    g = ObstacleGrid(width=200, height=100, cell_size=10)
    path = find_path(g, (10, 50), (190, 50))
    assert path is not None
    assert path[0] == (10, 50)
    assert path[-1] == (190, 50)
    # Direct path stays on roughly the same y
    ys = {y for _, y in path}
    assert max(ys) - min(ys) <= g.cell_size


def test_find_path_routes_around_obstacle():
    g = ObstacleGrid(width=200, height=100, cell_size=10)
    g.add_obstacle(Obstacle(x=80, y=40, width=40, height=20))
    path = find_path(g, (10, 50), (190, 50))
    assert path is not None
    # Path must not pass through the obstacle rectangle (interior)
    for x, y in path:
        inside_x = 80 < x < 120
        inside_y = 40 < y < 60
        assert not (inside_x and inside_y), f"path point ({x},{y}) pierces obstacle"


def test_find_path_returns_none_when_boxed_in():
    g = ObstacleGrid(width=60, height=60, cell_size=10)
    # Surround the target with obstacles
    g.add_obstacle(Obstacle(x=30, y=20, width=20, height=5))
    g.add_obstacle(Obstacle(x=30, y=35, width=20, height=5))
    g.add_obstacle(Obstacle(x=50, y=20, width=5, height=25))
    g.add_obstacle(Obstacle(x=25, y=20, width=5, height=25))
    path = find_path(g, (5, 30), (40, 30))
    assert path is None


def test_simplify_path_collapses_collinear_points():
    # Path: straight east, then straight east, then a corner north, then north
    raw = [(0, 0), (10, 0), (20, 0), (30, 0), (30, 10), (30, 20)]
    simplified = simplify_path(raw)
    assert simplified == [(0, 0), (30, 0), (30, 20)]


def test_simplify_path_preserves_corners():
    raw = [(0, 0), (10, 0), (10, 10), (20, 10)]
    simplified = simplify_path(raw)
    assert simplified == [(0, 0), (10, 0), (10, 10), (20, 10)]


def test_simplify_path_single_segment_unchanged():
    assert simplify_path([(0, 0), (100, 0)]) == [(0, 0), (100, 0)]


def test_simplify_path_empty_or_single():
    assert simplify_path([]) == []
    assert simplify_path([(5, 5)]) == [(5, 5)]
```

- [ ] **Step 2: Verify tests fail**

Run: `uv run pytest tests/test_layout_routing.py -v`
Expected: `ImportError: No module named 'netdiagram.layout.routing'`

- [ ] **Step 3: Implement routing module**

Create `src/netdiagram/layout/routing.py`:

```python
"""Orthogonal A* edge routing with obstacle avoidance.

Usage:
    grid = ObstacleGrid(width=1000, height=600, cell_size=10, padding=20)
    for pn in positioned_nodes:
        grid.add_obstacle(Obstacle(pn.x, pn.y, pn.width, pn.height))
    path = find_path(grid, (sx, sy), (tx, ty))
    if path:
        path = simplify_path(path)
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field

Point2D = tuple[int, int]


@dataclass(frozen=True)
class Obstacle:
    x: float
    y: float
    width: float
    height: float


@dataclass
class ObstacleGrid:
    """Square-cell grid that marks obstacle footprints as blocked.

    Coordinates passed to `is_blocked` / `find_path` are in the same pixel
    space as the node positions; the grid snaps them to cell centers
    internally."""

    width: float
    height: float
    cell_size: float = 10.0
    padding: float = 20.0
    _blocked: set[Point2D] = field(default_factory=set)

    def add_obstacle(self, obs: Obstacle) -> None:
        """Mark all cells overlapping (obs + padding) as blocked."""
        x0 = obs.x - self.padding
        y0 = obs.y - self.padding
        x1 = obs.x + obs.width + self.padding
        y1 = obs.y + obs.height + self.padding
        for cx, cy in self._cells_in_rect(x0, y0, x1, y1):
            self._blocked.add((cx, cy))

    def is_blocked(self, x: float, y: float) -> bool:
        return self._snap(x, y) in self._blocked

    # --- Helpers -----------------------------------------------------

    def _snap(self, x: float, y: float) -> Point2D:
        cs = self.cell_size
        return (int(x // cs) * int(cs), int(y // cs) * int(cs))

    def _cells_in_rect(
        self, x0: float, y0: float, x1: float, y1: float
    ) -> list[Point2D]:
        cs = self.cell_size
        out: list[Point2D] = []
        sx = int(x0 // cs) * int(cs)
        sy = int(y0 // cs) * int(cs)
        ex = int(x1 // cs) * int(cs)
        ey = int(y1 // cs) * int(cs)
        for cx in range(sx, ex + int(cs), int(cs)):
            for cy in range(sy, ey + int(cs), int(cs)):
                out.append((cx, cy))
        return out

    def _neighbors(self, p: Point2D) -> list[Point2D]:
        cs = int(self.cell_size)
        x, y = p
        candidates = [(x - cs, y), (x + cs, y), (x, y - cs), (x, y + cs)]
        return [
            c
            for c in candidates
            if 0 <= c[0] <= self.width
            and 0 <= c[1] <= self.height
            and c not in self._blocked
        ]


def find_path(
    grid: ObstacleGrid, start: tuple[float, float], end: tuple[float, float]
) -> list[Point2D] | None:
    """Compute an orthogonal path from start to end avoiding blocked cells.

    Returns None if the target cell is unreachable. The start and end cells
    are themselves forced-free (caller's responsibility to place endpoints
    on node boundaries rather than inside node footprints)."""
    s = grid._snap(*start)
    e = grid._snap(*end)

    # Ensure endpoints are reachable even if the snap landed inside padding.
    blocked_snapshot = grid._blocked
    grid._blocked = blocked_snapshot - {s, e}

    try:
        return _astar(grid, s, e)
    finally:
        grid._blocked = blocked_snapshot


def simplify_path(points: list[Point2D]) -> list[Point2D]:
    """Remove interior points that don't change direction."""
    if len(points) < 3:
        return list(points)
    out = [points[0]]
    for i in range(1, len(points) - 1):
        prev = out[-1]
        cur = points[i]
        nxt = points[i + 1]
        if _direction(prev, cur) == _direction(cur, nxt):
            continue  # cur is collinear; skip it
        out.append(cur)
    out.append(points[-1])
    return out


# --- A* internals ---------------------------------------------------

def _astar(grid: ObstacleGrid, start: Point2D, goal: Point2D) -> list[Point2D] | None:
    open_heap: list[tuple[float, int, Point2D]] = []
    counter = 0
    heapq.heappush(open_heap, (0.0, counter, start))
    came_from: dict[Point2D, Point2D] = {}
    g_score: dict[Point2D, float] = {start: 0.0}

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            return _reconstruct(came_from, current)
        for neighbor in grid._neighbors(current):
            tentative = g_score[current] + 1.0
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                f = tentative + _manhattan(neighbor, goal)
                counter += 1
                heapq.heappush(open_heap, (f, counter, neighbor))
    return None


def _manhattan(a: Point2D, b: Point2D) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _reconstruct(came_from: dict[Point2D, Point2D], end: Point2D) -> list[Point2D]:
    out = [end]
    while out[-1] in came_from:
        out.append(came_from[out[-1]])
    out.reverse()
    return out


def _direction(a: Point2D, b: Point2D) -> tuple[int, int]:
    dx = 0 if b[0] == a[0] else (1 if b[0] > a[0] else -1)
    dy = 0 if b[1] == a[1] else (1 if b[1] > a[1] else -1)
    return (dx, dy)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_layout_routing.py -v`
Expected: all 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/netdiagram/layout/routing.py tests/test_layout_routing.py
git commit -m "feat(layout): obstacle grid + A* pathfinder with path simplification"
```

---

## Task 3: Wire A* routing into the engine

**Files:**
- Modify: `src/netdiagram/layout/engine.py`
- Modify: `tests/test_layout_engine.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_layout_engine.py`:

```python
def test_edge_routes_around_intermediate_node():
    """Place three nodes in a line. The edge from left to right must route
    around the center node rather than straight through it."""
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="left", label="left", type="router"),
            Node(id="middle", label="middle", type="router"),
            Node(id="right", label="right", type="router"),
        ],
        links=[
            # Only link is left<->right; the center node is in the way but not
            # connected.
            Link(source=LinkEndpoint(node="left"),
                 target=LinkEndpoint(node="right")),
        ],
    )
    laid = layout_diagram(d)
    # Path must exist and must not pierce the middle node's bounding box.
    edge = laid.edges[0]
    assert len(edge.path) >= 2
    middle = next(pn for pn in laid.nodes if pn.node.id == "middle")
    for p in edge.path:
        inside_x = middle.x < p.x < middle.x + middle.width
        inside_y = middle.y < p.y < middle.y + middle.height
        assert not (inside_x and inside_y), (
            f"edge path point ({p.x}, {p.y}) pierces 'middle' node"
        )
```

- [ ] **Step 2: Verify it fails**

Run: `uv run pytest tests/test_layout_engine.py::test_edge_routes_around_intermediate_node -v`
Expected: FAIL — current straight-line routing sends the edge through `middle`.

(In some layouts the auto-placed middle node may not actually sit between left and right. If so, the test passes trivially but the next task step still adds real routing. Check `laid.nodes` positions if this triggers.)

- [ ] **Step 3: Use routing in `_route_edges`**

Modify `src/netdiagram/layout/engine.py`. Update the imports to include the routing module:

```python
from netdiagram.layout.routing import Obstacle, ObstacleGrid, find_path, simplify_path
```

Replace `_route_edges` (defined in Task 1) with the routed version:

```python
def _route_edges(diagram: Diagram, laid: LayoutedDiagram) -> list[RoutedEdge]:
    """Route each edge orthogonally around node obstacles. Parallel edges
    fan out at endpoints. Falls back to a straight line if A* can't find
    a path (should not happen for well-formed diagrams)."""
    by_id = {pn.node.id: pn for pn in laid.nodes}

    # Build the obstacle grid from every positioned node.
    grid = ObstacleGrid(
        width=laid.canvas_width,
        height=laid.canvas_height,
        cell_size=10.0,
        padding=15.0,
    )
    for pn in laid.nodes:
        grid.add_obstacle(Obstacle(pn.x, pn.y, pn.width, pn.height))

    # Pre-count parallel edges per pair for fan-out.
    pair_counts: dict[tuple[str, str], int] = {}
    for link in diagram.links:
        pair = tuple(sorted((link.source.node, link.target.node)))
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    pair_index: dict[tuple[str, str], int] = dict.fromkeys(pair_counts, 0)

    out: list[RoutedEdge] = []
    for link in diagram.links:
        pair = tuple(sorted((link.source.node, link.target.node)))
        idx = pair_index[pair]
        total = pair_counts[pair]
        pair_index[pair] += 1

        s = by_id[link.source.node]
        t = by_id[link.target.node]
        sx, sy = s.x + s.width / 2, s.y + s.height / 2
        tx, ty = t.x + t.width / 2, t.y + t.height / 2

        dx_off, dy_off = _fan_out_offset(sx, sy, tx, ty, idx, total)
        start_pt = (sx + dx_off, sy + dy_off)
        end_pt = (tx + dx_off, ty + dy_off)

        raw = find_path(grid, start_pt, end_pt)
        if raw is None:
            # Fallback: straight line with fan-out offset.
            path_points = [Point(*start_pt), Point(*end_pt)]
        else:
            simplified = simplify_path(raw)
            path_points = [Point(x, y) for x, y in simplified]

        out.append(RoutedEdge(link=link, path=path_points))
    return out
```

`_fan_out_offset` remains as implemented in Task 1.

- [ ] **Step 4: Run the new test**

Run: `uv run pytest tests/test_layout_engine.py::test_edge_routes_around_intermediate_node -v`
Expected: PASS.

- [ ] **Step 5: Run full suite**

Run: `uv run pytest`
Expected: all tests still pass. The earlier `test_layout_produces_edge_for_every_link` asserted `len(edge.path) >= 2`, which still holds with routed paths. The parallel fan-out test from Task 1 still passes (fan-out happens before A*).

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/layout/engine.py tests/test_layout_engine.py
git commit -m "feat(layout): route edges orthogonally around node obstacles via A*"
```

---

## Task 4: Emit waypoints in the Draw.io renderer

**Files:**
- Modify: `src/netdiagram/renderers/drawio.py`
- Modify: `tests/test_renderer_drawio.py`

Draw.io uses `<Array as="points">` inside `<mxGeometry>` to store explicit edge waypoints. When present, Draw.io routes the edge through those points rather than running its own edge router.

- [ ] **Step 1: Write failing test**

Append to `tests/test_renderer_drawio.py`:

```python
def test_edge_geometry_includes_waypoints_when_path_has_intermediate_points():
    """A routed edge with 4 path points [start, mid1, mid2, end] should produce
    an mxGeometry containing <Array as="points"> with the two interior points."""
    d = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="obstacle", label="obstacle", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[
            Link(source=LinkEndpoint(node="a"), target=LinkEndpoint(node="b")),
        ],
    )
    root = _parse(_render(d))
    edges = [c for c in root.findall(".//mxCell") if c.get("edge") == "1"]
    assert len(edges) == 1
    geom = edges[0].find("mxGeometry")
    assert geom is not None
    arr = geom.find("Array")
    # Array is optional if the path is straight, but for a routed path with
    # intermediate points it must be present with as="points".
    if arr is not None:
        assert arr.get("as") == "points"
        pts = arr.findall("mxPoint")
        # At minimum one intermediate waypoint
        assert len(pts) >= 1
```

- [ ] **Step 2: Verify**

Run: `uv run pytest tests/test_renderer_drawio.py::test_edge_geometry_includes_waypoints_when_path_has_intermediate_points -v`
Expected: PASS only if the layout actually routes around the obstacle (producing interior points). If the auto-placement doesn't put 'obstacle' between 'a' and 'b', the Array element may be absent — the test's `if arr is not None` branch handles that case and remains green. The test's real job is to fail loudly if we emit an Array with the wrong structure.

You should additionally add a stricter regression test that uses known positions. Append:

```python
def test_routed_edge_with_explicit_waypoints_emits_mxpoint_elements(monkeypatch):
    """Forge a RoutedEdge with explicit path points and verify the renderer
    emits them as mxPoint children inside <Array as=\"points\">."""
    from netdiagram.ir.models import Diagram, Link, LinkEndpoint, Metadata, Node
    from netdiagram.layout.types import (
        LayoutedDiagram,
        Point,
        PositionedNode,
        RoutedEdge,
    )

    diagram = Diagram(
        metadata=Metadata(title="T", type="physical"),
        nodes=[
            Node(id="a", label="a", type="router"),
            Node(id="b", label="b", type="router"),
        ],
        links=[Link(source=LinkEndpoint(node="a"), target=LinkEndpoint(node="b"))],
    )
    pn_a = PositionedNode(node=diagram.nodes[0], x=40, y=40, width=100, height=60)
    pn_b = PositionedNode(node=diagram.nodes[1], x=400, y=40, width=100, height=60)
    edge = RoutedEdge(
        link=diagram.links[0],
        path=[Point(90, 70), Point(200, 70), Point(200, 150), Point(450, 150)],
    )
    laid = LayoutedDiagram(
        diagram=diagram,
        nodes=[pn_a, pn_b],
        edges=[edge],
        canvas_width=600,
        canvas_height=300,
    )
    xml = DrawioRenderer().render(laid)
    root = _parse(xml)
    e_cell = next(c for c in root.findall(".//mxCell") if c.get("edge") == "1")
    arr = e_cell.find("mxGeometry/Array")
    assert arr is not None
    assert arr.get("as") == "points"
    pts = arr.findall("mxPoint")
    # Two interior points (path has 4 total; start and end are source/target)
    assert len(pts) == 2
    xs = [float(p.get("x")) for p in pts]
    ys = [float(p.get("y")) for p in pts]
    assert xs == [200.0, 200.0]
    assert ys == [70.0, 150.0]
```

- [ ] **Step 3: Run failing test**

Run: `uv run pytest tests/test_renderer_drawio.py::test_routed_edge_with_explicit_waypoints_emits_mxpoint_elements -v`
Expected: FAIL — current renderer doesn't emit Array/mxPoint for edges.

- [ ] **Step 4: Emit waypoints in `_append_edge`**

Modify `src/netdiagram/renderers/drawio.py`. Find the `_append_edge` method. After the `geom = etree.SubElement(edge_cell, "mxGeometry", relative="1")` line and before `geom.set("as", "geometry")`, add:

```python
        # Emit interior waypoints from the routed path, if any.
        # Path[0] and path[-1] are implicit (source/target endpoints); only
        # intermediate points become <mxPoint> entries inside <Array as="points">.
        if len(re.path) > 2:
            arr = etree.SubElement(geom, "Array")
            arr.set("as", "points")
            for point in re.path[1:-1]:
                etree.SubElement(arr, "mxPoint", x=str(point.x), y=str(point.y))
```

The final `_append_edge` body should look like:

```python
    def _append_edge(self, root: etree._Element, re: RoutedEdge, edge_index: int) -> None:
        edge_id = f"edge-{edge_index}"
        style = _EDGE_STYLE_BY_LINK_STYLE[re.link.style]
        edge_cell = etree.SubElement(
            root,
            "mxCell",
            id=edge_id,
            value=re.link.label or "",
            style=style,
            edge="1",
            parent="1",
            source=f"node-{re.link.source.node}",
            target=f"node-{re.link.target.node}",
        )
        geom = etree.SubElement(edge_cell, "mxGeometry", relative="1")

        if len(re.path) > 2:
            arr = etree.SubElement(geom, "Array")
            arr.set("as", "points")
            for point in re.path[1:-1]:
                etree.SubElement(arr, "mxPoint", x=str(point.x), y=str(point.y))

        geom.set("as", "geometry")

        if re.link.source.interface:
            self._append_endpoint_label(
                root,
                parent_id=edge_id,
                label=re.link.source.interface,
                position=-0.7,
                cell_id=f"{edge_id}-src-label",
            )
        if re.link.target.interface:
            self._append_endpoint_label(
                root,
                parent_id=edge_id,
                label=re.link.target.interface,
                position=0.7,
                cell_id=f"{edge_id}-tgt-label",
            )
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_renderer_drawio.py -v`
Expected: all tests pass (including both new ones).

- [ ] **Step 6: Commit**

```bash
git add src/netdiagram/renderers/drawio.py tests/test_renderer_drawio.py
git commit -m "feat(renderer): emit routed edge waypoints as Array of mxPoint in drawio"
```

---

## Task 5: End-to-end validation + regression guard

**Files:**
- Modify: `tests/test_end_to_end.py`

- [ ] **Step 1: Append end-to-end test**

Add to `tests/test_end_to_end.py`:

```python
def test_branch_office_edges_avoid_node_interiors(fixtures_dir: Path) -> None:
    """Routed edges in the branch office topology must not pierce node bodies."""
    diagram = load_diagram(fixtures_dir / "branch_office.yaml")
    laid = layout_diagram(diagram)

    # For every edge, check no interior path point sits inside any node bbox
    # (other than the endpoint nodes — those are endpoint-connected, not pierced).
    endpoint_node_ids = {pn.node.id for pn in laid.nodes}
    for edge in laid.edges:
        s_id = edge.link.source.node
        t_id = edge.link.target.node
        # Interior path points are path[1:-1]
        for p in edge.path[1:-1]:
            for pn in laid.nodes:
                if pn.node.id in (s_id, t_id):
                    continue
                inside_x = pn.x < p.x < pn.x + pn.width
                inside_y = pn.y < p.y < pn.y + pn.height
                assert not (inside_x and inside_y), (
                    f"edge {s_id}->{t_id} pierces node {pn.node.id} "
                    f"at interior point ({p.x}, {p.y})"
                )
    # Sanity: endpoint-node ids are actually in the layout
    assert endpoint_node_ids
```

- [ ] **Step 2: Run e2e tests**

Run: `uv run pytest tests/test_end_to_end.py -v`
Expected: all tests pass.

- [ ] **Step 3: Final full suite + lint**

Run:
```bash
uv run pytest
uv run ruff check src tests
```

Expected: full suite green (should be 88 Phase 2b + 11 new = ~99), ruff clean.

- [ ] **Step 4: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "test(layout): regression guard — routed edges never pierce node interiors"
```

---

## Wrap-Up

- [ ] **Manual verification (author responsibility)**

1. Render the full YYC topology with advanced routing:
   ```bash
   PYTHONPATH=src uv run netdiagram render \
     /Users/dexter/Documents/dev/yyc-network-revamp/yyc-topology.yaml \
     --output /tmp/yyc-routed.drawio
   ```
2. Open `/tmp/yyc-routed.drawio` in Draw.io Desktop or app.diagrams.net.
3. Compare side-by-side with a pre-advanced-layout snapshot (e.g., `yyc-network-revamp/yyc-topology.drawio` from an earlier commit).
4. Check specifically:
   - MLAG bond members (FW bond11, leaf bond31-34) should visibly fan out rather than stacking
   - Edges from spine to distant nodes (leaves on the far side) should route around the nearer nodes
   - Parallel peerlinks (swp50 + swp52 between the two spines) should not overlap
5. Note any remaining visual issues — e.g., labels still colliding on dense fans — for the next advanced-layout plan.

- [ ] **Tag**

```bash
git tag phase-2c-advanced-layout
```
