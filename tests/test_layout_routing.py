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
