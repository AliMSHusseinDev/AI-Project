from math import dist
import random
from time import perf_counter
from typing import Literal
from pydantic import Field
from .environment import Model
from .fitness import Terrain, Evaluator
from .validation import validate


class Settings(Model):
    population: int = Field(default=18, ge=4, le=80)
    generations: int = Field(default=40, ge=1, le=300)
    budget: int = Field(default=300, ge=80, le=5000)
    seed: int = Field(default=7, ge=0, le=2147483647)
    local_fraction: float = Field(default=0.45, ge=0, le=1)


def connected_seed(terrain):
    """Greedy coverage followed by parent paths in a base-rooted BFS tree."""
    missing = terrain.full
    selected = set()
    while missing and terrain.parent:
        site = max(
            terrain.parent, key=lambda i: (terrain.masks[i] & missing).bit_count()
        )
        if not terrain.masks[site] & missing:
            break
        while site != terrain.base and site not in selected:
            selected.add(site)
            missing &= ~terrain.masks[site]
            site = terrain.parent[site]
    return frozenset(selected), not missing


def select_parent(population, evaluator, rng):
    return min(
        rng.sample(population, 3), key=lambda child: evaluator.evaluate(child).cost
    )


def geographic_crossover(first, second, terrain, rng):
    axis = rng.randrange(2)
    split = rng.randrange(1, terrain.env.size)
    return frozenset(
        [i for i in first if terrain.sites[i][axis] < split]
        + [i for i in second if terrain.sites[i][axis] >= split]
    )


def mutate(child, terrain, rng, operation=None):
    operation = operation or rng.choice(("move", "add", "remove"))
    sites = set(child)
    if operation in ("move", "remove") and sites:
        old = rng.choice(sorted(sites))
        sites.remove(old)
    if operation in ("move", "add"):
        available = sorted(set(range(len(terrain.sites))) - child)
        if available:
            sites.add(rng.choice(available))
        elif operation == "move":
            return child
    return frozenset(sites)


def directed_moves(child, terrain, rng):
    connected, islands = terrain.components(child)
    targets = []
    for island in islands:
        source, anchor = min(
            ((source, anchor) for source in island for anchor in connected),
            key=lambda pair: dist(
                terrain.positions[pair[0]], terrain.positions[pair[1]]
            ),
        )
        targets.append((source, terrain.positions[anchor]))
        if anchor != terrain.base:
            targets.append((anchor, terrain.positions[source]))
    missing = terrain.full ^ terrain.covered(child)
    if missing and child:
        holes = [
            point for index, point in enumerate(terrain.points) if missing >> index & 1
        ]
        for point in rng.sample(holes, min(3, len(holes))):
            source = min(child, key=lambda site: dist(terrain.sites[site], point))
            targets.append((source, point))
    step = terrain.env.spacing
    for source, target in targets:
        x, y = terrain.sites[source]
        nearby = [
            (x + dx, y + dy) for dx in (-step, 0, step) for dy in (-step, 0, step)
        ]
        for point in sorted(nearby, key=lambda p: dist(p, target)):
            site = terrain.index.get(point)
            if site is not None and site not in child:
                yield (child - {source}) | {site}


def improve_deployment_with_local_search(child, evaluator, rng, stats):
    stats["attempts"] += 1
    before = len(evaluator.cache)
    for _ in range(2):
        score = evaluator.evaluate(child)
        if score.holes or score.disconnected:
            neighbors = directed_moves(child, evaluator.terrain, rng)
        else:
            order = sorted(child)
            rng.shuffle(order)
            neighbors = (child - {site} for site in order)
        best = child
        for number, neighbor in enumerate(neighbors):
            if number >= 8 or len(evaluator.cache) >= evaluator.budget:
                break
            if evaluator.evaluate(neighbor).cost < evaluator.evaluate(best).cost:
                best = neighbor
        if best == child:
            break
        stats["improvements"] += 1
        child = best
    stats["evaluations"] += len(evaluator.cache) - before
    return child


def optimize(
    environment, settings, algorithm: Literal["GA", "MA"], progress=lambda *args: None
):
    started = perf_counter()
    terrain = Terrain(environment)
    evaluator = Evaluator(terrain, settings.budget)
    rng = random.Random(settings.seed)
    initial, possible = connected_seed(terrain)
    population = [initial]
    for _ in range(settings.population - 1):
        child = initial
        for _ in range(rng.randint(1, 5)):
            child = mutate(child, terrain, rng)
        population.append(child)
    best = min(population, key=lambda child: evaluator.evaluate(child).cost)
    history = []
    local = dict(attempts=0, improvements=0, evaluations=0)
    for generation in range(settings.generations + 1):
        cost = evaluator.evaluate(best).cost
        history.append(
            dict(
                generation=generation,
                evaluations=len(evaluator.cache),
                cost=cost,
                sensors=len(best),
            )
        )
        progress(generation, len(evaluator.cache), cost)
        if (
            generation == settings.generations
            or len(evaluator.cache) >= settings.budget
            or not possible
        ):
            break
        children = sorted(population, key=lambda p: evaluator.evaluate(p).cost)[:2]
        while (
            len(children) < settings.population
            and len(evaluator.cache) < settings.budget
        ):
            child = select_parent(population, evaluator, rng)
            if rng.random() < 0.85:
                child = geographic_crossover(
                    child, select_parent(population, evaluator, rng), terrain, rng
                )
            if rng.random() < 0.8:
                child = mutate(child, terrain, rng)
            evaluator.evaluate(child)
            if algorithm == "MA" and rng.random() < settings.local_fraction:
                child = improve_deployment_with_local_search(
                    child, evaluator, rng, local
                )
            children.append(child)
        population = children
        best = min(children, key=lambda child: evaluator.evaluate(child).cost)
    score = evaluator.evaluate(best)
    connected, islands = terrain.components(best)
    mask = terrain.covered(best)
    deployed = sorted(best)
    result = dict(
        algorithm=algorithm,
        positions=[terrain.sites[i] for i in deployed],
        count=len(best),
        coverage=100 * (len(terrain.points) - score.holes) / len(terrain.points),
        connectivity=100 * (len(best) - score.disconnected) / len(best) if best else 0,
        holes=[p for i, p in enumerate(terrain.points) if not mask >> i & 1],
        unreachable=[terrain.sites[i] for i in deployed if i not in connected],
        links=[
            [terrain.positions[i], terrain.positions[j]]
            for i in deployed
            for j in sorted(terrain.neighbors[i] & (best | {terrain.base}))
            if j > i
        ],
        feasible=not score.holes and not score.disconnected and bool(best),
        possible=possible,
        initial_count=len(initial),
        monitoring_count=len(terrain.points),
        cost=score.cost,
        generations=generation,
        evaluations=len(evaluator.cache),
        history=history,
        local=local,
        seed=settings.seed,
        settings=settings.model_dump(),
        environment_id=environment.identifier(),
    )
    result["audit"] = validate(environment, result)
    result["seconds"] = perf_counter() - started
    return result
