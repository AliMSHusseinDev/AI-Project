"""Independent audit using separating axes and a depth-first graph walk."""

from math import dist
import numpy as np


def clear_paths(start, targets, obstacles):
    # A segment and a box separate on a box axis or the segment normal.
    clear = np.ones(len(targets), dtype=bool)
    for box in obstacles:
        center = np.array([box.x + (box.w - 1) / 2, box.y + (box.h - 1) / 2])
        half = (targets - start) / 2
        middle = start + half - center
        box_overlap = (abs(middle[:, 0]) <= box.w / 2 + abs(half[:, 0])) & (
            abs(middle[:, 1]) <= box.h / 2 + abs(half[:, 1])
        )
        cross = abs(middle[:, 0] * half[:, 1] - middle[:, 1] * half[:, 0])
        clear &= ~(
            box_overlap
            & (cross <= box.w / 2 * abs(half[:, 1]) + box.h / 2 * abs(half[:, 0]))
        )
    return clear


def coverage_mask(environment, sensors, points):
    covered = np.zeros(len(points), dtype=bool)
    for position in sensors:
        near = np.flatnonzero(
            ~covered
            & (np.sum((points - position) ** 2, axis=1) <= environment.sensing**2)
        )
        covered[near[clear_paths(position, points[near], environment.obstacles)]] = True
    return covered


def validate(environment, result):
    try:
        type(environment).model_validate(environment.model_dump())
    except ValueError:
        return dict(
            passed=False,
            checks={"Environment integrity": False},
            coverage=0,
            connectivity=0,
        )
    sensors = [tuple(p) for p in result["positions"]]
    # Build the audit domain from occupied cells, independently of the search masks.
    blocked = {
        (x, y)
        for r in environment.obstacles
        for y in range(r.y, r.y + r.h)
        for x in range(r.x, r.x + r.w)
    }
    lattice = [
        (x, y)
        for y in range(0, environment.size, environment.spacing)
        for x in range(0, environment.size, environment.spacing)
        if (x, y) not in blocked
    ]
    footprint = environment.base_footprint
    allowed = {point for point in lattice if not footprint.contains(point)}
    valid = len(sensors) == len(set(sensors)) and all(p in allowed for p in sensors)
    points = np.array(
        environment.manual_points
        if environment.monitoring_mode == "manual"
        else lattice
    ).reshape(-1, 2)
    mask = coverage_mask(environment, sensors, points)
    positions = np.array([environment.base, *sensors])
    pending, reached = [0], {0}
    while pending:
        origin = positions[pending.pop()]
        near = [
            i
            for i, target in enumerate(positions)
            if i not in reached and dist(origin, target) <= environment.communication
        ]
        for index in np.array(near, dtype=int)[
            clear_paths(origin, positions[near], environment.obstacles)
        ]:
            pending.append(index)
            reached.add(index)
    connected = len(reached) - 1
    coverage = 100 * int(mask.sum()) / len(points) if len(points) else 0
    connectivity = 100 * connected / len(sensors) if sensors else 0
    holes = {tuple(p) for p in points[~mask].tolist()}
    unreachable = {sensors[i - 1] for i in range(1, len(positions)) if i not in reached}
    checks = {
        "Environment integrity": True,
        "Environment identity": environment.identifier() == result["environment_id"],
        "Unique legal coordinates": valid,
        "Active count": result["count"] == len(sensors),
        "Coverage record": abs(coverage - result["coverage"]) < 1e-8
        and holes == set(map(tuple, result["holes"]))
        and result.get("monitoring_mode", environment.monitoring_mode)
        == environment.monitoring_mode
        and result.get("monitoring_count", len(points)) == len(points),
        "Connectivity record": abs(connectivity - result["connectivity"]) < 1e-8
        and unreachable == set(map(tuple, result["unreachable"])),
        "All monitoring points covered": bool(len(points)) and not holes,
        "Every sensor can route to base": bool(sensors) and connected == len(sensors),
        "Feasibility record": result["feasible"]
        == (valid and not holes and bool(sensors) and not unreachable),
    }
    report = dict(
        passed=all(checks.values()),
        checks=checks,
        coverage=coverage,
        connectivity=connectivity,
    )
    return report
