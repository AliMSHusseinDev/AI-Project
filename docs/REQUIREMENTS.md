# Course and project checklist

The course instructions were checked in two passes: first for deliverables and team rules, then for assessment and integrity. The project description was checked in three passes: modelling, GA, then MA and final validation.

## Course report requirements

| Requirement | Where it is covered | Status |
|---|---|---|
| Use Python | `wsn/`, `pyproject.toml` | Implemented and tested |
| Six team members | `docs/TEAM.md` and report role table | Blank names/IDs; proposed roles provided |
| TA approves registered group | Blank TA field in team record | Team must obtain approval |
| Explain project idea in detail | Report sections 1–3 | Written |
| Explain main functions | Report section 3 and README | Written and implemented |
| Similar market applications | Report section 4 | Comparison with related tools; no false claim of identical products |
| 4–6 relevant academic papers | Report section 5 and `docs/sources/` | Six real references; metadata checked |
| Describe dataset | `data/README.md` and report section 6 | Three included synthetic maps, honestly labelled |
| Algorithms and measured results | Report sections 7–9 and `results/reference/` | Implemented; 75 saved and checked runs |
| Development platform | Report section 10 and locked requirements | Python 3.12.14 on Linux validated |
| Analysis and design diagrams | `docs/DESIGN.md` and `docs/figures/` | Use cases, data flow, classes, GA and MA flows |
| Code and documentation submission | This repository and report files | Prepared; team handles course upload |
| Week 12/13 discussion | `docs/DISCUSSION.md` | Guide prepared; no exact date supplied by course |
| Each member works in every phase | Shared phase table and contribution log | Plan provided; actual contributions remain blank |
| Own work and academic integrity | `docs/ACADEMIC_INTEGRITY.md` | AI help disclosed; team must check permission |

## Technical project requirements

| Requirement | Implementation and check |
|---|---|
| 2D grid, terrain and obstacles | `Terrain`, three JSON maps, validation tests |
| Euclidean sensing and communication ranges | Distance matrices, exact boundary tests |
| Obstacles block sensing line-of-sight | Closed rectangle/segment checks and all-pairs oracle test |
| Obstacles block communication line-of-sight | Same geometry with a separate communication range |
| Cover every required point | All free integer grid points are checked; continuous coverage is outside the model |
| Every node can route to the base | Graph reachability through valid sensor-to-sensor links |
| Minimise active sensors | Variable-length chromosome, add/delete/move mutations, feasible fitness by count |
| Evolve sensor coordinates | IDs map to integer `(x, y)` positions; crossover and movement change coordinates |
| GA balances coverage, connectivity and cost | Feasibility-first weighted fitness, selection, crossover, mutation and elitism |
| MA repairs holes or isolated groups | Detect masks/components, move nearby sensors 1–3 units, evaluate full network |
| Local phase before next evolutionary cycle | Local search is applied to selected offspring every generation |
| Demonstrate implementation correctness | Unit tests, HTTP solve, CLI solve, independent saved-layout verifier |
| Compare GA and MA fairly | Same initial population and seeds; equal-generation and equal-evaluation tests |

## Assumptions to discuss with the TA

The project uses finite grid coverage, a fixed base, equal sensor ranges, static rectangular obstacles, and synthetic maps. A feasible layout has full coverage and every sensor connected. The search returns the best layout found; a global minimum is not proven. These assumptions are stated clearly so the team can explain exactly what was built.
