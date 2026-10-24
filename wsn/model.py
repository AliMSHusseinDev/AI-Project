"""Terrain, exact line-of-sight on the grid, and network evaluation."""

from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Terrain:
    name: str
    width: int
    height: int
    base: tuple[int, int]
    sensing_range: float
    communication_range: float
    obstacles: tuple[tuple[float, float, float, float], ...] = ()

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Terrain needs a nonempty name")
        if any(type(v) is not int or v < 1 for v in (self.width, self.height)):
            raise ValueError("Width and height must be positive integers")
        if any(not math.isfinite(v) or v <= 0 for v in
               (self.sensing_range, self.communication_range)):
            raise ValueError("Signal ranges must be positive and finite")
        for rect in self.obstacles:
            if len(rect) != 4 or not all(math.isfinite(v) for v in rect):
                raise ValueError("An obstacle needs four finite coordinates")
            x0, y0, x1, y1 = rect
            if not (0 <= x0 <= x1 < self.width and 0 <= y0 <= y1 < self.height):
                raise ValueError("Obstacle is outside terrain or has reversed corners")
        if (len(self.base) != 2 or any(type(v) is not int for v in self.base)
                or not self.free(self.base)):
            raise ValueError("Base must be on a free integer grid point")

    def free(self, point):
        x, y = point
        return (0 <= x < self.width and 0 <= y < self.height
                and not any(a <= x <= c and b <= y <= d
                            for a, b, c, d in self.obstacles))

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text())
        data["base"] = tuple(data["base"])
        data["obstacles"] = tuple(tuple(r) for r in data.get("obstacles", []))
        return cls(**data)

    def to_dict(self):
        return {"name": self.name, "width": self.width, "height": self.height,
                "base": list(self.base), "sensing_range": self.sensing_range,
                "communication_range": self.communication_range,
                "obstacles": [list(r) for r in self.obstacles]}


def line_of_sight(a, b, obstacles):
    """A closed rectangle blocks even a tangent or corner-touching segment."""
    for x0, y0, x1, y1 in obstacles:
        low, high = 0.0, 1.0
        for start, end, lower, upper in ((a[0], b[0], x0, x1),
                                          (a[1], b[1], y0, y1)):
            delta = end - start
            if delta == 0:
                if not lower <= start <= upper:
                    low, high = 1.0, 0.0
                    break
            else:
                left, right = (lower - start) / delta, (upper - start) / delta
                low = max(low, min(left, right))
                high = min(high, max(left, right))
        if low <= high:
            return False
    return True


@dataclass(frozen=True)
class Evaluation:
    sensors: int
    covered: int
    total: int
    connected: int
    components: int  # Includes the component containing the base.

    @property
    def coverage(self):
        return self.covered / self.total

    @property
    def connectivity(self):
        return self.connected / self.sensors if self.sensors else 1.0

    @property
    def feasible(self):
        return self.covered == self.total and self.connected == self.sensors

    def fitness(self, max_nodes):
        # Every feasible layout outranks every infeasible layout.
        if self.feasible:
            return 10.0 + 1.0 - self.sensors / max_nodes
        return 4.0 * self.coverage + 2.0 * self.connectivity - 0.1 * self.sensors / max_nodes

    def to_dict(self):
        return {"sensors": self.sensors, "covered": self.covered, "total": self.total,
                "coverage": self.coverage, "connected": self.connected,
                "connectivity": self.connectivity, "components": self.components,
                "feasible": self.feasible}


class Problem:
    """All free integer points are both targets and legal sensor locations.

    Precompute O(N^2) geometry once. A chromosome stores unique location IDs,
    so changing an ID changes the sensor's (x, y) coordinate.
    """

    def __init__(self, terrain):
        self.terrain = terrain
        self.points = np.array([(x, y) for y in range(terrain.height)
                                for x in range(terrain.width) if terrain.free((x, y))], dtype=int)
        self.lookup = {tuple(p): i for i, p in enumerate(self.points)}
        self.base_id = self.lookup[terrain.base]
        self.size = len(self.points)
        # Refuse a huge dense allocation before it exhausts the machine.
        if self.size > 5000:
            raise ValueError("This teaching implementation supports at most 5000 free points")
        delta = self.points[:, None, :].astype(float) - self.points[None, :, :]
        squared = np.sum(delta * delta, axis=2)
        visible = np.ones((self.size, self.size), dtype=bool)
        # Vectorised slab intersection, using the same closed-box rule as above.
        for x0, y0, x1, y1 in terrain.obstacles:
            low = np.zeros_like(squared)
            high = np.ones_like(squared)
            for axis, lower, upper in ((0, x0, x1), (1, y0, y1)):
                start = self.points[:, axis, None]
                step = self.points[None, :, axis] - start
                parallel = step == 0
                safe_step = np.where(parallel, 1, step)
                left, right = (lower - start) / safe_step, (upper - start) / safe_step
                low = np.maximum(low, np.where(parallel, -np.inf, np.minimum(left, right)))
                high = np.minimum(high, np.where(parallel, np.inf, np.maximum(left, right)))
                outside = parallel & ((start < lower) | (start > upper))
                high = np.where(outside, -np.inf, high)
            visible &= low > high
        self.cover = visible & (squared <= terrain.sensing_range ** 2 + 1e-12)
        self.links = visible & (squared <= terrain.communication_range ** 2 + 1e-12)
        self.base_links = self.links[self.base_id]
        self.distances = np.sqrt(squared)
        self.evaluations = 0

    def validate_genes(self, genes):
        if (len(set(genes)) != len(genes)
                or any(not isinstance(i, (int, np.integer)) or not 0 <= i < self.size for i in genes)):
            raise ValueError("Sensor locations must be unique valid grid IDs")

    def state(self, genes):
        ids = np.asarray(genes, dtype=int)
        covered = self.cover[ids].any(axis=0) if len(ids) else np.zeros(self.size, dtype=bool)
        reachable = self.base_links[ids].copy()
        edges = self.links[np.ix_(ids, ids)]
        while reachable.any():
            expanded = reachable | edges[reachable].any(axis=0)
            if np.array_equal(expanded, reachable):
                break
            reachable = expanded
        return covered, reachable, edges

    def evaluate(self, genes):
        self.validate_genes(genes)
        self.evaluations += 1
        covered, reachable, edges = self.state(genes)
        seen = reachable.copy()
        components = 1
        for node in range(len(genes)):
            if seen[node]:
                continue
            components += 1
            stack = [node]
            seen[node] = True
            while stack:
                neighbours = np.flatnonzero(edges[stack.pop()] & ~seen)
                seen[neighbours] = True
                stack.extend(neighbours.tolist())
        return Evaluation(len(genes), int(covered.sum()), self.size,
                          int(reachable.sum()), components)

    def paths_from_base(self):
        parent = np.full(self.size, -1, dtype=int)
        parent[self.base_id] = self.base_id
        queue = deque([self.base_id])
        while queue:
            node = queue.popleft()
            for nxt in np.flatnonzero(self.links[node] & (parent == -1)):
                parent[nxt] = node
                queue.append(int(nxt))
        return parent

    def coordinates(self, genes):
        return self.points[list(genes)].tolist()
