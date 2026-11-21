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


def test_independent_audit_tampering_and_fine_grid():
    env = Environment(size=20)
    result = optimize(env, Settings(), "MA")
    fine = validate(env, result, True)
    assert (
        fine["passed"]
        and fine["fine"]["total"] == 1600
        and fine["fine"]["covered"] <= 1600
    )
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


def test_fine_sampling_reveals_gap():
    env = Environment(size=20, base=(2, 2), sensing=26.88, communication=4)
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
    report = validate(env, result, fine=True)
    assert report["passed"] and report["fine"]["percent"] < 100
