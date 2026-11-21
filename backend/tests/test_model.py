import numpy as np
import pytest
from pydantic import ValidationError
from backend.app.environment import Environment, Obstacle, generate
from backend.app.geometry import calculate_euclidean_distance, has_line_of_sight
from backend.app.validation import clear_paths
from backend.app.fitness import Terrain, Evaluator

BLOCK = Obstacle(id="wall", x=5, y=5, w=2, h=3)


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ((1, 1), (4, 5), 5),
        ((1, 1), (1, 1), 0),
        ((1, 2), (1, 4), 2),
        ((2, 4), (7, 4), 5),
    ],
)
def test_euclidean_distance(start, end, expected):
    assert calculate_euclidean_distance(start, end) == expected


@pytest.mark.parametrize(
    "start,end,clear",
    [
        ((0, 5), (10, 5), False),
        ((5, 1), (5, 9), False),
        ((0, 4), (9, 4), True),
        ((4, 5), (5, 4), False),
        ((4.5, 4.5), (4.5, 7.5), False),
        ((5, 5), (5, 5), False),
        ((4, 5), (4, 5), True),
        ((6, 8), (7, 8), True),
    ],
)
def test_closed_obstacle_geometry(start, end, clear):
    assert has_line_of_sight(start, end, [BLOCK]) is clear
    assert bool(clear_paths(start, np.array([end]), [BLOCK])[0]) is clear


@pytest.mark.parametrize(
    "size,limit", [(20, 2), (30, 6), (40, 10), (60, 24), (80, 42), (100, 66)]
)
def test_obstacle_limits_and_seed(size, limit):
    env = Environment(size=size, base=(2, 2))
    assert env.obstacle_limit == limit
    generated = generate(env, limit)
    assert len(generated.obstacles) == limit
    assert generated == generate(env, limit)
    assert len(generate(env, 0).obstacles) == 0
    assert sum(r.w * r.h for r in generated.obstacles) <= 0.15 * size**2


@pytest.mark.parametrize(
    "patch",
    [
        {"size": 19},
        {"size": 101},
        {"base": (-1, 0)},
        {"spacing": 0},
        {"sensing": 0},
        {"obstacles": [BLOCK, BLOCK]},
        {"base": (5, 5), "obstacles": [BLOCK]},
        {"obstacles": [BLOCK, BLOCK.model_copy(update={"x": 6, "id": "other"})]},
        {"size": 20, "obstacles": [BLOCK.model_copy(update={"x": 19})]},
        {"size": 20, "obstacles": [BLOCK.model_copy(update={"w": 10, "h": 10})]},
    ],
)
def test_invalid_environment_rejected(patch):
    with pytest.raises(ValidationError):
        Environment(**patch)


def test_candidates_and_monitoring_domain():
    env = Environment(size=20, base=(2, 2), obstacles=[BLOCK])
    points = set(env.monitoring_points())
    sites = set(env.candidate_positions())
    assert len(points) == 99 and env.base in points and env.base not in sites
    assert (4, 4) in sites and (3, 3) not in sites and (6, 6) not in points


def test_visibility_blocks_both_radio_and_sensing():
    env = Environment(
        size=20, base=(8, 6), obstacles=[BLOCK], sensing=6, communication=6
    )
    terrain = Terrain(env)
    site = terrain.index[(4, 6)]
    assert terrain.base not in terrain.neighbors[site]
    for point, expected in [((8, 6), 0), ((2, 6), 1), ((18, 18), 0)]:
        assert (terrain.masks[site] >> terrain.points.index(point)) & 1 == expected


def test_routes_components_and_zero_sensors():
    terrain = Terrain(Environment(size=20, base=(0, 0), communication=2))
    positions = [(2, 0), (4, 0), (6, 0), (14, 14), (16, 14), (0, 18)]
    deployment = frozenset(terrain.index[p] for p in positions)
    connected, islands = terrain.components(deployment)
    assert {terrain.positions[i] for i in connected} == {(0, 0), (2, 0), (4, 0), (6, 0)}
    assert sorted(map(len, islands)) == [1, 2]
    evaluator = Evaluator(terrain, 10)
    assert evaluator.evaluate(deployment).disconnected == 3
    empty = evaluator.evaluate(frozenset())
    assert empty.holes == 100 and empty.disconnected == 0


def test_fitness_order_and_cache():
    terrain = Terrain(Environment(size=20, base=(0, 0), sensing=30, communication=30))
    evaluator = Evaluator(terrain, 3)
    single, pair = frozenset([0]), frozenset([0, 1])
    assert (
        evaluator.evaluate(single).cost
        < evaluator.evaluate(pair).cost
        < evaluator.evaluate(frozenset()).cost
    )
    assert evaluator.evaluate(single).holes == 0 and len(evaluator.cache) == 3
    assert evaluator.evaluate(frozenset()).cost == 100 * (len(terrain.sites) + 1)


def test_area_and_geometry_capacity_after_edits():
    full = Obstacle(id="wide", x=0, y=0, w=10, h=6)
    env = Environment(size=20, obstacles=[full])
    assert len(env.monitoring_points()) == 85 and env.additional_capacity == 0
    with pytest.raises(ValueError):
        generate(env, 2, append=True)
    smaller = Environment(size=20, obstacles=[full.model_copy(update={"w": 8})])
    assert len(smaller.monitoring_points()) == 88 and smaller.additional_capacity == 1
    assert len(generate(smaller, 2, append=True).obstacles) == 2
    clear = Environment(size=20)
    assert len(clear.monitoring_points()) == 100 and clear.additional_capacity == 2


def test_station_footprint_keeps_center_and_ranges():
    env = Environment(size=20, base=(10, 10), base_margin=2)
    assert env.base in env.monitoring_points()
    assert (8, 8) not in env.candidate_positions()
    assert env.communication == Environment().communication
    for patch in (
        {"base": (1, 1)},
        {"obstacles": [Obstacle(id="edge", x=12, y=12, w=1, h=1)]},
    ):
        with pytest.raises(ValidationError):
            Environment(**(env.model_dump() | patch))
    assert Environment.model_validate({"size": 20}).base_margin == 0


def test_order_independent_cache_and_last_evaluation():
    evaluator = Evaluator(Terrain(Environment(size=20)), 2)
    first = evaluator.evaluate(frozenset([2, 3]))
    assert evaluator.evaluate(frozenset([3, 2])) is first and len(evaluator.cache) == 1
    evaluator.evaluate(frozenset([2]))
    with pytest.raises(ValueError):
        evaluator.evaluate(frozenset([4]))
    assert evaluator.evaluate(frozenset([2, 3])) is first and len(evaluator.cache) == 2
