"""Cell (x, y) is centred on the integer pair. Rectangles occupy whole cells."""

import hashlib
import random

from pydantic import BaseModel, ConfigDict, Field, model_validator

Point = tuple[int, int]
AREA_PER_OBSTACLE = 150
MAX_BLOCKED_PERCENT = 15
MAX_SIDE = 12


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Obstacle(Model):
    id: str = Field(min_length=1, max_length=80)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=MAX_SIDE)
    h: int = Field(ge=1, le=MAX_SIDE)

    def contains(self, point):
        x, y = point
        return self.x <= x < self.x + self.w and self.y <= y < self.y + self.h

    def overlaps(self, other):
        return (
            self.x < other.x + other.w
            and other.x < self.x + self.w
            and self.y < other.y + other.h
            and other.y < self.y + self.h
        )


class Environment(Model):
    size: int = Field(default=30, ge=20, le=100)
    base: Point = (15, 15)
    sensing: float = Field(default=5.5, gt=0, le=30)
    communication: float = Field(default=8, gt=0, le=30)
    spacing: int = Field(default=2, ge=2, le=6)
    seed: int = Field(default=42, ge=0, le=2147483647)
    obstacles: list[Obstacle] = Field(default_factory=list)

    @property
    def obstacle_limit(self):
        return max(1, self.size**2 // AREA_PER_OBSTACLE)

    @model_validator(mode="after")
    def validate_layout(self):
        if not all(0 <= value < self.size for value in self.base):
            raise ValueError("Base station lies outside the grid.")
        if len(self.obstacles) > self.obstacle_limit:
            raise ValueError("Too many obstacles for this grid.")
        if (
            sum(r.w * r.h for r in self.obstacles) * 100
            > MAX_BLOCKED_PERCENT * self.size**2
        ):
            raise ValueError("Obstacles exceed the blocked-area limit.")
        if len({r.id for r in self.obstacles}) != len(self.obstacles):
            raise ValueError("Obstacle IDs must be unique.")
        for index, rect in enumerate(self.obstacles):
            if (
                rect.x + rect.w > self.size
                or rect.y + rect.h > self.size
                or rect.contains(self.base)
            ):
                raise ValueError("Obstacle crosses the grid edge or covers the base.")
            if any(rect.overlaps(other) for other in self.obstacles[:index]):
                raise ValueError("Obstacles overlap.")
        return self

    def identifier(self):
        data = self.model_dump_json()
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def monitoring_points(self):
        return [
            (x, y)
            for y in range(self.size)
            for x in range(self.size)
            if not any(rect.contains((x, y)) for rect in self.obstacles)
        ]

    def candidate_positions(self):
        return [
            p
            for p in self.monitoring_points()
            if p != self.base and all(v % self.spacing == 0 for v in p)
        ]


def generate(environment, count, append=False):
    if not 0 <= count <= environment.obstacle_limit:
        raise ValueError("Requested count exceeds the grid limit.")
    rectangles = list(environment.obstacles) if append else []
    rng = random.Random(environment.seed + (len(rectangles) * 7919 if append else 0))
    remaining_area = MAX_BLOCKED_PERCENT * environment.size**2 // 100 - sum(
        r.w * r.h for r in rectangles
    )
    if count < len(rectangles) or remaining_area < count - len(rectangles):
        raise ValueError("The requested obstacles do not fit in the remaining area.")
    for attempt in range(5000):
        if len(rectangles) == count:
            return Environment(**(environment.model_dump() | {"obstacles": rectangles}))
        side = min(MAX_SIDE, max(2, environment.size // 7))
        width, height = rng.randint(1, side), rng.randint(1, side)
        # Reserve one free cell of area budget for each later obstacle.
        available = remaining_area - (count - len(rectangles) - 1)
        width = min(width, available)
        height = min(height, available // width)
        rect = Obstacle(
            id=f"block-{attempt}",
            x=rng.randrange(environment.size - width + 1),
            y=rng.randrange(environment.size - height + 1),
            w=width,
            h=height,
        )
        if any(
            rect.id == r.id or rect.overlaps(r) for r in rectangles
        ) or rect.contains(environment.base):
            continue
        bx, by = environment.base
        exits = [(bx + 1, by), (bx - 1, by), (bx, by - 1), (bx, by + 1)]
        if not any(
            0 <= x < environment.size
            and 0 <= y < environment.size
            and not any(r.contains((x, y)) for r in [*rectangles, rect])
            for x, y in exits
        ):
            continue
        rectangles.append(rect)
        remaining_area -= width * height
    raise ValueError("Could not place all obstacles within the retry limit.")
