from math import dist
import numpy as np


def visible_endpoints(origin, endpoints, obstacles):
    """Slab clipping. Equal entry and exit times mean a blocked corner touch."""
    visible = np.ones(len(endpoints), dtype=bool)
    delta = endpoints - origin
    for rect in obstacles:
        low = np.array([rect.x - 0.5, rect.y - 0.5])
        high = low + [rect.w, rect.h]
        if np.any(np.maximum(endpoints.max(axis=0), origin) < low) or np.any(
            np.minimum(endpoints.min(axis=0), origin) > high
        ):
            continue
        enter = np.zeros(len(endpoints))
        leave = np.ones(len(endpoints))
        for axis in (0, 1):
            step = delta[:, axis]
            parallel = step == 0
            divisor = np.where(parallel, 1, step)
            first = (low[axis] - origin[axis]) / divisor
            last = (high[axis] - origin[axis]) / divisor
            outside = not low[axis] <= origin[axis] <= high[axis]
            enter = np.maximum(
                enter,
                np.where(
                    parallel, np.inf if outside else -np.inf, np.minimum(first, last)
                ),
            )
            leave = np.minimum(
                leave, np.where(parallel, np.inf, np.maximum(first, last))
            )
        visible &= enter > leave
    return visible


def has_line_of_sight(start, end, obstacles):
    return bool(visible_endpoints(start, np.asarray([end]), obstacles)[0])


def calculate_euclidean_distance(start, end):
    return dist(start, end)
