# Synthetic simulation dataset

The five JSON files in `scenarios/` contain complete terrain inputs for AI Project. Choose **Load** in the studio to open one. They contain generated geometry. There are no field measurements or third-party data licenses.

| Field | Meaning |
|---|---|
| size | Number of cells along each side, from 20 to 100 |
| base | Collector cell [x, y]. Row zero is the top. |
| obstacles | Unique IDs and integer x, y, w, h. A rectangle starting at (x, y) blocks w columns and h rows. |
| base_margin | Half-width in cells around the base center. Defaults to 0 when loading older maps. |
| spacing | Both coordinates of each monitoring and candidate site must be multiples of this integer. |
| sensing, communication | Independent Euclidean radii, in cell widths |
| seed | Environment generator seed |

Every unblocked lattice point is monitored, including lattice points inside the station footprint. Sensor sites exclude that footprint. A rectangle occupies the closed area from (x − 0.5, y − 0.5) to (x + w − 0.5, y + h − 0.5). Touching the wall blocks a ray. Adjacent rectangles may share a physical boundary.

From the root, run `python -m Dataset.generate_dataset` with the project environment active to regenerate the five files. Recipes are in `backend/app/benchmarks.py`. The three scale maps have 1, 4 and 9 obstacles for sides 20, 40 and 60. The other maps use 0 and 10 blocks at side 40. All use seed 42. These files support the supplemental repeated benchmarks. The five GUI experiments use their own specified counts (0, 2, 0, 8, 18). Their exact environments are stored in Assessment/evidence/assessment_runs.json. The editor supports arbitrary valid maps. The JSON stores the actual coordinates so replay does not depend on a future version of the generator.
