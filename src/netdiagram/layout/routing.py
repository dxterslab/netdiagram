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
