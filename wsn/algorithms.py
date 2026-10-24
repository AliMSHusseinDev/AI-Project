"""A shared genetic search and a memetic search with local coordinate repair."""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass

import numpy as np

from .model import Problem


@dataclass(frozen=True)
class Settings:
    population: int = 36
    generations: int = 70
    max_sensors: int = 70
    mutation_rate: float = 0.85
    crossover_rate: float = 0.9
    elite: int = 2
    local_elites: int = 4
    local_steps: int = 2
    move_radius: int = 3
    evaluation_budget: int | None = None

    def __post_init__(self):
        for name in ('population', 'generations', 'max_sensors', 'elite',
                     'local_elites', 'local_steps', 'move_radius'):
            value = getattr(self, name)
            if type(value) is not int or value < (0 if name in ('generations', 'local_elites', 'local_steps') else 1):
                raise ValueError(f"Invalid {name}")
        if self.population < 4 or self.elite >= self.population:
            raise ValueError("Need population >= 4 and elite < population")
        if not (0 <= self.mutation_rate <= 1 and 0 <= self.crossover_rate <= 1):
            raise ValueError("Mutation and crossover rates must be in [0, 1]")
        if self.evaluation_budget is not None and (type(self.evaluation_budget) is not int or self.evaluation_budget < self.population):
            raise ValueError("Evaluation budget must be at least the population size")


def prune(problem, genes, max_nodes, rng=None, score=None):
    """Remove a sensor only if the complete layout remains feasible."""
    genes = tuple(sorted(genes))
    order = list(genes)
    if rng is not None:
        rng.shuffle(order)
    for sensor in order:
        candidate = tuple(i for i in genes if i != sensor)
        result = score(candidate) if score else problem.evaluate(candidate)
        if result.feasible:
            genes = candidate
    return genes


def greedy_layout(problem: Problem):
    """Greedy set cover, shortest paths to the base, then safe removal.

    This is an initial feasible solution and a baseline, not an optimal solver.
    """
    parent = problem.paths_from_base()
    if np.any(parent < 0):
        # An unreachable candidate can still be sensed by a reachable sensor.
        usable = parent >= 0
    else:
        usable = np.ones(problem.size, dtype=bool)
    if not problem.cover[usable].any(axis=0).all():
        raise ValueError("No connected deployment can cover all targets with these ranges/obstacles")
    uncovered = np.ones(problem.size, dtype=bool)
    chosen = set()
    while uncovered.any():
        gains = problem.cover[:, uncovered].sum(axis=1)
        gains[~usable] = -1
        sensor = int(np.argmax(gains))
        if gains[sensor] <= 0:
            raise ValueError("Uncoverable grid targets")
        chosen.add(sensor)
        uncovered &= ~problem.cover[sensor]
    # Paths include relay sensors; the base itself is not a sensing sensor unless selected.
    for sensor in list(chosen):
        step = int(parent[sensor])
        while step != problem.base_id:
            chosen.add(step)
            step = int(parent[step])
    return prune(problem, tuple(sorted(chosen)), problem.size)


class BudgetReached(Exception):
    pass


def optimise(problem: Problem, algorithm='ga', seed=0, settings=None, initial=None):
    if algorithm not in ('ga', 'ma'):
        raise ValueError("Algorithm must be ga or ma")
    settings = settings or Settings()
    rng = np.random.default_rng(seed)
    started = time.perf_counter()
    start_evaluations = problem.evaluations
    # Both algorithms use exactly the same seed solution and initial population.
    initial = tuple(initial) if initial is not None else greedy_layout(problem)
    problem.validate_genes(initial)
    if len(initial) > settings.max_sensors:
        raise ValueError(f"max_sensors={settings.max_sensors} is below greedy seed size {len(initial)}")
    # The shared seed construction is excluded from each search's evaluation budget.
    search_start = problem.evaluations
    cache = {}
    best_genes, best_eval = None, None

    def score(genes):
        nonlocal best_genes, best_eval
        genes = tuple(sorted(genes))
        if genes not in cache:
            if (settings.evaluation_budget is not None
                    and problem.evaluations - search_start >= settings.evaluation_budget):
                raise BudgetReached
            result = problem.evaluate(genes)
            cache[genes] = result
            if best_eval is None or result.fitness(settings.max_sensors) > best_eval.fitness(settings.max_sensors):
                best_genes, best_eval = genes, result
        return cache[genes]

    def fitness(genes):
        return score(genes).fitness(settings.max_sensors)

    population = [tuple(sorted(initial))]
    limit = min(settings.max_sensors, problem.size)
    for i in range(settings.population - 1):
        if i % 2 == 0:
            population.append(mutate(initial, problem, settings, rng))
        else:
            low = max(1, min(len(initial) // 2, limit))
            count = int(rng.integers(low, limit + 1))
            population.append(tuple(sorted(rng.choice(problem.size, count, replace=False).tolist())))
    for genes in population:
        score(genes)
    history = []
    stop = 'generations'
    try:
        for generation in range(settings.generations + 1):
            population.sort(key=fitness, reverse=True)
            history.append({"generation": generation, "evaluations": problem.evaluations - search_start,
                            "fitness": best_eval.fitness(settings.max_sensors), **best_eval.to_dict()})
            if generation == settings.generations:
                break
            children = population[:settings.elite]
            while len(children) < settings.population:
                def tournament():
                    options = rng.integers(0, len(population), size=3)
                    return max((population[int(i)] for i in options), key=fitness)
                a, b = tournament(), tournament()
                child = crossover(a, b, settings.max_sensors, rng) if rng.random() < settings.crossover_rate else a
                if rng.random() < settings.mutation_rate:
                    child = mutate(child, problem, settings, rng)
                score(child)
                children.append(child)
            if algorithm == 'ma':
                # Local repair affects offspring before the next evolutionary cycle.
                children.sort(key=fitness, reverse=True)
                for i in range(min(settings.local_elites, len(children))):
                    children[i] = local_search(problem, children[i], settings, rng, score)
            population = children
    except BudgetReached:
        stop = 'evaluation_budget'
        history.append({"generation": generation, "evaluations": problem.evaluations - search_start,
                        "fitness": best_eval.fitness(settings.max_sensors), **best_eval.to_dict()})
    return {"algorithm": algorithm, "seed": seed, "settings": asdict(settings),
            "terrain": problem.terrain.to_dict(), "coordinates": problem.coordinates(best_genes),
            "location_ids": list(best_genes), "metrics": best_eval.to_dict(), "history": history,
            "evaluations": problem.evaluations - search_start,
            "setup_evaluations": search_start - start_evaluations,
            "runtime_seconds": time.perf_counter() - started, "stop_reason": stop}


def crossover(a, b, limit, rng):
    common = set(a) & set(b)
    rest = sorted(set(a) ^ set(b))
    selected = [i for i in rest if rng.random() < 0.5]
    child = sorted(common | set(selected))
    if len(child) > limit:
        child = sorted(rng.choice(child, limit, replace=False).tolist())
    return tuple(child)


def mutate(genes, problem, settings, rng):
    child = set(genes)
    action = int(rng.integers(0, 3))
    if action == 0 and child:
        child.remove(int(rng.choice(sorted(child))))
    elif action == 1 and len(child) < min(settings.max_sensors, problem.size):
        available = sorted(set(range(problem.size)) - child)
        child.add(int(rng.choice(available)))
    elif child:
        old = int(rng.choice(sorted(child)))
        x, y = problem.points[old]
        dx, dy = rng.integers(-settings.move_radius, settings.move_radius + 1, size=2)
        target = problem.lookup.get((int(x + dx), int(y + dy)))
        if target is not None and target not in child:
            child.remove(old)
            child.add(target)
    return tuple(sorted(child))


def local_search(problem, genes, settings, rng, score):
    """Repair holes/isolated components by moving nodes a few grid units.

    Feasible layouts also try a compacting move and safe sensor deletion.
    Each trial is evaluated on the full network; accept strict improvement only.
    """
    genes = tuple(sorted(genes))
    for _ in range(settings.local_steps):
        current = score(genes)
        covered, reachable, _ = problem.state(genes)
        proposals = set()
        holes = np.flatnonzero(~covered)
        if len(holes):
            targets = rng.choice(holes, min(3, len(holes)), replace=False).tolist()
            sources = list(genes)
        elif not reachable.all():
            targets = list(np.asarray(genes)[~reachable])
            sources = list(np.asarray(genes)[reachable]) or [problem.base_id]
        else:
            targets = rng.choice(problem.size, min(3, problem.size), replace=False).tolist()
            sources = list(genes)
        # Also repair isolation even when coverage holes exist.
        if len(genes) and not reachable.all():
            for sensor in np.asarray(genes)[~reachable][:3]:
                connected = list(np.asarray(genes)[reachable]) + [problem.base_id]
                nearest = min(connected, key=lambda j: problem.distances[sensor, j])
                _propose_move(proposals, genes, int(sensor), int(nearest), problem, settings)
        for target in targets:
            nearest = sorted(sources, key=lambda j: problem.distances[j, target])[:3]
            for sensor in nearest:
                if sensor in genes:
                    _propose_move(proposals, genes, int(sensor), int(target), problem, settings)
        if current.feasible:
            for sensor in genes:
                proposals.add(tuple(i for i in genes if i != sensor))
        best = genes
        best_fitness = current.fitness(settings.max_sensors)
        # Sorting makes RNG-seeded runs reproducible regardless of hash order.
        for trial in sorted(proposals):
            result = score(trial)
            if result.fitness(settings.max_sensors) > best_fitness:
                best, best_fitness = trial, result.fitness(settings.max_sensors)
        if best == genes:
            break
        genes = best
    return genes


def _propose_move(proposals, genes, sensor, target, problem, settings):
    a, b = problem.points[sensor], problem.points[target]
    vector = b - a
    length = float(np.linalg.norm(vector))
    if length == 0:
        return
    step = vector / length
    for distance in range(1, settings.move_radius + 1):
        point = tuple(np.rint(a + step * distance).astype(int))
        dest = problem.lookup.get(point)
        if dest is not None and dest not in genes:
            proposals.add(tuple(sorted((set(genes) - {sensor}) | {dest})))
