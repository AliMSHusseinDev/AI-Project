# Dataset card

This project uses three small synthetic maps. They are included as JSON so anyone can run the same tests. They were created for this project. They are not measured data, a downloaded benchmark, or a claim about a real site.

| File | Grid size | Free targets | Blocked grid points | Obstacles |
|---|---|---:|---:|---:|
| `open_field.json` | 20 × 16 | 320 | 0 | 0 |
| `two_walls.json` | 24 × 18 | 372 | 60 | 2 |
| `courtyard.json` | 26 × 20 | 433 | 87 | 3 |

## Format

Each terrain has a name, integer width and height, base coordinate, sensing range, communication range, and obstacle list.

- Coordinates are `(x, y)`, starting at `(0, 0)`. One unit is the distance between neighbouring grid points.
- Legal target and sensor positions are all free integer grid points.
- The base is at `(0, 0)` on all three maps.
- Sensing range is 4.5 units. Communication range is 7 units.
- An obstacle is `[left, bottom, right, top]`. The rectangle and its boundary block signals and cannot contain sensors or targets.
- The obstacle interiors also block a segment that passes between grid points. We use geometric intersection, not just a check at the endpoints.
- A sensor may be placed at the base's coordinate as separate sensing hardware. The base alone does not count as a sensor or provide sensing coverage.

## Why these maps?

The open field is a simple reference. Two walls tests blocked signals and paths around walls. Courtyard adds a narrow opening and several edges that make placement harder.

Using small maps makes repeated trials easy to run and explain. Obstacles are static and axis-aligned. There is no elevation, noise, battery drain, movement, or packet loss. These limits are part of the model.

## Make another map

Copy one JSON file, change its values, and run:

```bash
python -m wsn solve --terrain data/your_map.json --algorithm ma
```

The base must be free. Use positive finite ranges. Very large maps need a different storage approach; this teaching implementation precomputes dense matrices and limits the number of free points to 5,000. Some maps cannot be fully covered by a connected deployment; the program reports this instead of reporting false success.

A public real-world benchmark is a possible future extension. The course prefers a public dataset but does not require one. Check with the TA if a real-world dataset is required for this group.
