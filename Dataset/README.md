# Synthetic simulation dataset

The five JSON files in `scenarios/` contain complete terrain inputs for Fieldlab. Choose **Load** in the studio to open one. They contain generated geometry. There are no field measurements or third-party data licenses.

| Field | Meaning |
|---|---|
| size | Number of cells along each side, from 20 to 100 |
| base | Collector cell [x, y]. Row zero is the top. |
| obstacles | Unique IDs and integer x, y, w, h. A rectangle starting at (x, y) blocks w columns and h rows. |
| spacing | Both candidate coordinates must be multiples of this integer. |
| sensing, communication | Independent Euclidean radii, in cell widths |
| seed | Environment generator seed |

Every free cell center is a monitoring point. Candidate sites exclude the base. A rectangle occupies the closed area from (x − 0.5, y − 0.5) to (x + w − 0.5, y + h − 0.5). Touching the wall blocks a ray. Adjacent rectangles may share a physical boundary. Fine verification places four extra samples at offsets ±0.25 from each free center.

From the root, run `python -m Dataset.generate_dataset` with the project environment active to regenerate the five files. Recipes are in `backend/app/benchmarks.py`. The three scale maps have 1, 4 and 9 obstacles for sides 20, 40 and 60. The other maps use 0 and 10 blocks at side 40. All use seed 42. These are examples for paired tests. The editor supports arbitrary valid maps. The JSON stores the actual coordinates so replay does not depend on a future version of the generator.
