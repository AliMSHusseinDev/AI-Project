from collections import deque
from dataclasses import dataclass
import numpy as np
from .geometry import visible_endpoints

HOLE_WEIGHT = 1
DISCONNECTED_WEIGHT = 5


def flood(start, remaining, neighbors):
    reached = {start}
    queue = deque([start])
    while queue:
        for node in neighbors[queue.popleft()] & remaining:
            remaining.remove(node)
            reached.add(node)
            queue.append(node)
    return reached


@dataclass(frozen=True)
class Score:
    cost: int
    holes: int
    disconnected: int


class Terrain:
    """Build geometry once per environment. Each bit represents one available monitoring site."""

    def __init__(self, environment):
        self.env = environment
        self.points = environment.monitoring_points()
        if not self.points:
            raise ValueError(
                "Add at least one required monitoring point before running."
            )
        self.sites = environment.candidate_positions()
        self.base = len(self.sites)
        self.positions = self.sites + [environment.base]
        self.index = {point: i for i, point in enumerate(self.sites)}
        self.full = (1 << len(self.points)) - 1
        self.masks = []
        self.neighbors = []
        targets = np.asarray(self.points)
        nodes = np.asarray(self.positions)
        for index, position in enumerate(self.positions):
            if index != self.base:
                hits = self.visible_indices(position, targets, environment.sensing)
                mask = np.zeros(len(targets), dtype=np.uint8)
                mask[hits] = 1
                self.masks.append(
                    int.from_bytes(
                        np.packbits(mask, bitorder="little").tobytes(), "little"
                    )
                )
            neighbors = self.visible_indices(position, nodes, environment.communication)
            self.neighbors.append(set(neighbors.tolist()) - {index})
        # Only the base component of the full candidate graph can supply relays.
        self.parent = {}
        queue = deque([self.base])
        while queue:
            parent = queue.popleft()
            for site in sorted(self.neighbors[parent]):
                if site != self.base and site not in self.parent:
                    self.parent[site] = parent
                    queue.append(site)

    def visible_indices(self, position, targets, radius):
        delta = targets - position
        near = np.flatnonzero(np.einsum("ij,ij->i", delta, delta) <= radius**2)
        if len(near) and self.env.obstacles:
            near = near[visible_endpoints(position, targets[near], self.env.obstacles)]
        return near

    def covered(self, deployment):
        mask = 0
        for site in deployment:
            mask |= self.masks[site]
        return mask

    def components(self, deployment):
        remaining = set(deployment)
        connected = flood(self.base, remaining, self.neighbors)
        islands = []
        while remaining:
            start = min(remaining)
            remaining.remove(start)
            islands.append(flood(start, remaining, self.neighbors))
        return connected, islands


class Evaluator:
    """Integer cost preserves the order (feasibility, weighted violations, count)."""

    def __init__(self, terrain, budget):
        self.terrain = terrain
        self.cache = {}
        self.budget = budget

    def evaluate(self, deployment):
        if deployment not in self.cache:
            if len(self.cache) >= self.budget:
                raise ValueError("Evaluation budget exhausted")
            terrain = self.terrain
            holes = len(terrain.points) - terrain.covered(deployment).bit_count()
            reachable = flood(terrain.base, set(deployment), terrain.neighbors)
            disconnected = len(deployment) + 1 - len(reachable)
            violations = HOLE_WEIGHT * holes + DISCONNECTED_WEIGHT * disconnected
            cost = violations * (len(terrain.sites) + 1) + len(deployment)
            self.cache[deployment] = Score(cost, holes, disconnected)
        return self.cache[deployment]
