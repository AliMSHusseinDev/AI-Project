"""Independent, slower checks on exported coordinates (no cached matrices)."""

from collections import deque
from math import dist

from .model import Terrain, line_of_sight


def verify_result(result):
    data = result['terrain'].copy()
    data['base'] = tuple(data['base'])
    data['obstacles'] = tuple(tuple(r) for r in data.get('obstacles', []))
    terrain = Terrain(**data)
    sensors = [tuple(p) for p in result['coordinates']]
    if len(sensors) != len(set(sensors)):
        raise ValueError('Duplicate sensors in saved result')
    for p in sensors:
        if len(p) != 2 or any(type(v) is not int for v in p) or not terrain.free(p):
            raise ValueError('Invalid sensor coordinate')
    covered = total = 0
    for y in range(terrain.height):
        for x in range(terrain.width):
            point = (x, y)
            if not terrain.free(point):
                continue
            total += 1
            covered += any(dist(point, sensor) <= terrain.sensing_range + 1e-12
                           and line_of_sight(point, sensor, terrain.obstacles) for sensor in sensors)
    visited = {i for i, p in enumerate(sensors)
               if dist(p, terrain.base) <= terrain.communication_range + 1e-12
               and line_of_sight(p, terrain.base, terrain.obstacles)}
    queue = deque(visited)
    while queue:
        node = queue.popleft()
        for i, other in enumerate(sensors):
            if (i not in visited and dist(sensors[node], other) <= terrain.communication_range + 1e-12
                    and line_of_sight(sensors[node], other, terrain.obstacles)):
                visited.add(i)
                queue.append(i)
    # Count sensor components outside the base's connected component too.
    seen = set(visited)
    components = 1
    for node in range(len(sensors)):
        if node in seen:
            continue
        components += 1
        queue = deque([node])
        seen.add(node)
        while queue:
            current = queue.popleft()
            for i, other in enumerate(sensors):
                if (i not in seen and dist(sensors[current], other) <= terrain.communication_range + 1e-12
                        and line_of_sight(sensors[current], other, terrain.obstacles)):
                    seen.add(i)
                    queue.append(i)
    actual = {'sensors': len(sensors), 'covered': covered, 'total': total,
              'coverage': covered / total, 'connected': len(visited),
              'connectivity': len(visited) / len(sensors) if sensors else 1.0,
              'components': components,
              'feasible': covered == total and len(visited) == len(sensors)}
    for key, value in actual.items():
        if result['metrics'].get(key) != value:
            raise ValueError(f'Saved metric {key} is wrong: {result["metrics"].get(key)} != {value}')
    return actual
