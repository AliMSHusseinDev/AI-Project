import random
import pytest
from backend.app.environment import Environment, generate
from backend.app.fitness import Terrain, Evaluator
from backend.app.evolution import (
    connected_seed,
    select_parent,
    geographic_crossover,
    mutate,
    improve_deployment_with_local_search,
    optimize,
    Settings,
)
from backend.app.validation import validate


def test_seed_and_spatial_operators():
    terrain = Terrain(generate(Environment(size=20), 2))
    seed, possible = connected_seed(terrain)
    evaluator = Evaluator(terrain, 100)
    assert possible and evaluator.evaluate(seed).cost == len(seed)
    child = geographic_crossover(seed, frozenset(), terrain, random.Random(10))
    rng = random.Random(10)
    axis, cut = rng.randrange(2), rng.randrange(1, 20)
    assert child == {i for i in seed if terrain.sites[i][axis] < cut}
    parents = [seed, frozenset(), frozenset([0])]
    assert select_parent(parents, evaluator, rng) == seed
    for operation, delta in [("move", 0), ("remove", -1), ("add", 1)]:
        child = mutate(seed, terrain, rng, operation)
        assert (
            len(child) == len(seed) + delta
            and child != seed
            and all(i < len(terrain.sites) for i in child)
        )


@pytest.mark.parametrize(
    "goal", ["connection", "coverage", "removal", "no_improvement"]
)
def test_targeted_local_search(goal):
    if goal in ("connection", "coverage"):
        env = Environment(
            size=20,
            base=(0, 0),
            sensing=30 if goal == "connection" else 4,
            communication=4 if goal == "connection" else 30,
        )
        terrain = Terrain(env)
        point = (6, 0) if goal == "connection" else (0, 2)
        deployment = frozenset([terrain.index[point]])
    else:
        terrain = Terrain(
            Environment(size=20, base=(0, 0), sensing=30, communication=30)
        )
        deployment = frozenset([0, 1] if goal == "removal" else [0])
    evaluator = Evaluator(terrain, 30)
    old = evaluator.evaluate(deployment)
    stats = dict(attempts=0, improvements=0, evaluations=0)
    improved = improve_deployment_with_local_search(
        deployment, evaluator, random.Random(1), stats
    )
    score = evaluator.evaluate(improved)
    assert stats["evaluations"] <= 16 and stats["attempts"] == 1
    if goal == "connection":
        assert old.disconnected == 1 and score.disconnected == 0 and len(improved) == 1
    if goal == "coverage":
        assert score.holes < old.holes and len(improved) == 1
    if goal == "removal":
        assert len(improved) == 1 and score.holes == score.disconnected == 0
    if goal == "no_improvement":
        assert deployment == improved and stats["improvements"] == 0


@pytest.mark.parametrize("method", ["GA", "MA"])
def test_evolution_reproducible_elitism_budget(method):
    env = generate(Environment(size=20), 2)
    settings = Settings(population=8, budget=80, seed=17)
    first, second = [optimize(env, settings, method) for _ in range(2)]
    assert (
        first["positions"] == second["positions"]
        and first["history"] == second["history"]
    )
    assert first["feasible"] and first["audit"]["passed"] and first["evaluations"] <= 80
    costs = [row["cost"] for row in first["history"]]
    assert costs == sorted(costs, reverse=True)
    assert (first["local"]["attempts"] > 0) == (method == "MA")


def test_proven_infeasibility_and_audit():
    env = Environment(size=20, base=(1, 1), communication=0.1, sensing=0.1)
    result = optimize(env, Settings(), "GA")
    assert (
        not result["possible"]
        and not result["feasible"]
        and not result["audit"]["passed"]
    )
    assert result["generations"] == 0


def test_independent_audit_detects_tampering():
    env = Environment(size=20)
    result = optimize(env, Settings(), "MA")
    assert validate(env, result)["passed"]
    for patch in (
        {"count": 99},
        {"coverage": 0},
        {"connectivity": 12},
        {"positions": [env.base]},
        {"positions": [(-2, 0)]},
        {"positions": result["positions"] * 2},
        {"holes": [(0, 0)]},
        {"environment_id": "obsolete"},
        {"feasible": False},
    ):
        assert not validate(env, result | patch)["passed"]


def test_grid_coverage_checks_every_available_site():
    env = Environment(size=20, base=(2, 2), sensing=25.5, communication=4)
    result = dict(
        positions=[(0, 0)],
        environment_id=env.identifier(),
        count=1,
        holes=[],
        unreachable=[],
        coverage=100,
        connectivity=100,
        feasible=True,
    )
    assert validate(env, result)["passed"]
    # (18,18) is just beyond the new radius. A nearby obstacle can hide it too.
    smaller = env.model_copy(update={"sensing": 25})
    audit = validate(smaller, result | {"environment_id": smaller.identifier()})
    assert not audit["passed"] and audit["coverage"] == 99
    isolated = env.model_copy(update={"communication": 1})
    assert not validate(isolated, result | {"environment_id": isolated.identifier()})[
        "checks"
    ]["Every sensor can route to base"]


def test_budget_stop_and_generation_stop():
    env = Environment(size=20)
    for method in ("GA", "MA"):
        one = optimize(env, Settings(generations=1, budget=600), method)
        assert (
            one["termination"] == "Generation limit"
            and one["generations"] == 1
            and one["evaluations"] < 600
        )
        short = optimize(env, Settings(generations=300, budget=80), method)
        assert (
            short["termination"] == "Evaluation budget" and short["evaluations"] == 80
        )
        assert short["generations"] <= short["history"][-1]["generation"]
    for fraction in (0, 1):
        result = optimize(
            env,
            Settings(population=8, generations=1, budget=600, local_fraction=fraction),
            "MA",
        )
        assert result["local"]["attempts"] == fraction * 6


def test_illegal_sensor_and_invalid_environment_fail_independently():
    env = generate(Environment(size=20), 2)
    result = optimize(env, Settings(), "GA")
    r = env.obstacles[0]
    assert not validate(env, result | {"positions": [(r.x, r.y)]})["checks"][
        "Unique legal coordinates"
    ]
    assert not validate(env.model_copy(update={"base": (-1, 0)}), result)["checks"][
        "Environment integrity"
    ]


@pytest.mark.parametrize("method", ["GA", "MA"])
def test_manual_targets_change_search_and_independent_audit(method):
    env = Environment(
        size=20, base=(10, 10), monitoring_mode="manual", manual_points=[(7, 7), (9, 9)]
    )
    result = optimize(env, Settings(), method)
    assert (
        result["monitoring_count"] == 2
        and result["count"] == 1
        and result["audit"]["passed"]
    )
    changed = env.model_copy(update={"manual_points": [(0, 0), (19, 19)]})
    audit = validate(changed, result)
    assert not audit["passed"] and audit["coverage"] < 100
    assert not validate(env, result | {"monitoring_count": 100})["passed"]
    assert not validate(env, result | {"monitoring_mode": "automatic"})["passed"]
    empty = env.model_copy(update={"manual_points": []})
    assert not validate(empty, result)["passed"]
    with pytest.raises(ValueError, match="at least one"):
        optimize(empty, Settings(), method)


def test_manual_point_behind_obstacle_fails_independent_audit():
    from backend.app.environment import Obstacle

    env = Environment(
        size=20,
        base=(0, 0),
        sensing=8,
        monitoring_mode="manual",
        manual_points=[(7, 1)],
        obstacles=[Obstacle(id="wall", x=5, y=0, w=1, h=4)],
    )
    result = optimize(env, Settings(), "GA")
    assert result["audit"]["passed"]
    tampered = result | {"positions": [(2, 2)], "count": 1}
    assert validate(env, tampered)["coverage"] == 0


def test_ma_repairs_off_lattice_manual_target():
    env = Environment(
        size=20,
        base=(0, 0),
        sensing=1.6,
        communication=8,
        monitoring_mode="manual",
        manual_points=[(5, 1)],
    )
    terrain = Terrain(env)
    evaluator = Evaluator(terrain, 30)
    child = frozenset([terrain.index[(2, 0)]])
    stats = dict(attempts=0, evaluations=0, improvements=0)
    assert evaluator.evaluate(child).holes == 1
    improved = improve_deployment_with_local_search(
        child, evaluator, random.Random(7), stats
    )
    assert evaluator.evaluate(improved).holes == 0 and stats["evaluations"] > 0
