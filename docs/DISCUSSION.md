# Discussion and demonstration guide

## A short opening

Our project places wireless sensors on a grid. Walls can block sensing and communication. We need to cover every free grid point and keep every sensor connected to the base. We compare GA with MA. MA adds a short local repair step. We try to reduce the number of sensors while keeping both rules satisfied.

## Suggested six-person presentation

| Speaker | Topic | Suggested time |
|---|---|---:|
| Member 1 | Problem, assumptions, terrain and obstacles | 1 minute |
| Member 2 | GA chromosome, fitness and genetic steps | 1 minute |
| Member 3 | MA hole repair, isolation repair and sensor removal | 1 minute |
| Member 4 | Tests, baselines, seeds and equal-budget comparison | 1 minute |
| Member 5 | Six-paper review, findings and limitations | 1 minute |
| Member 6 | Live demo, design flow and conclusion | 2 minutes |

All members should be ready to answer questions about the other parts too.

## Demo steps

1. Run `python -m unittest discover -s tests -v`.
2. Run `python -m wsn serve` from the project root.
3. In the local browser demo, choose Two walls, GA, seed 11, and 70 generations.
4. Show coverage, connectivity, obstacles, and links. Download the JSON result.
5. Run MA with the same map, seed, and generation count. Compare sensor counts.
6. Explain that MA used more evaluations. Show the equal-budget results in `results/reference/RESULTS.md`.
7. Show a saved layout plot and a test that checks a blocked link or repaired hole.

Do not promise an identical run time on another computer. With the pinned packages and same settings, coordinates and histories should repeat. The table uses seed 11 for its example plots, not a secretly selected best run.

## Questions and simple answers

**What is a chromosome?** A set of active sensor positions. Each stored ID refers to one free integer `(x, y)` coordinate.

**Why not just use a regular grid of sensors?** Walls can hide points and block links. A good layout must also connect back to the base. A regular pattern may use extra sensors or leave holes.

**What is fitness?** A number used to rank layouts. A feasible layout always wins over an infeasible one. Among feasible layouts, fewer sensors is better. Before feasibility, coverage and base connectivity improve the score.

**What makes MA different?** After the genetic steps, MA checks a few layouts locally. It nudges sensors towards holes or the connected network and tries removing redundant sensors.

**How do you check connectivity?** Start with sensors that can reach the base. Follow valid links until no more sensors can be reached. Every active sensor must be reached.

**Do obstacles block only communication?** No. They block both sensing and communication, including a signal that touches a wall boundary.

**What does 100% coverage mean?** Every free integer grid point is covered. It does not prove continuous coverage between the points.

**Is the smallest sensor count proven?** No. These are search algorithms. We report the best layouts found. A tiny exhaustive test checks a simple case, not a proof for the larger maps.

**Why compare equal budgets?** One MA generation includes local search, so the same number of generations does not mean the same amount of work. We also compare exactly 3,000 unique evaluations each.

**Can you claim MA is always better?** No. It did better on average in these small experiments. Different maps, ranges, seeds, or local-search settings could give a different result.

**Where did the data come from?** We created three synthetic JSON terrains. The maps are included and repeatable. They are not real sensor measurements or a public benchmark.

**What does turning off local search test?** It checks that MA uses the same GA core. With local search off, the paired results and histories match GA.

**What are the main limits?** Small static grids, simple signal ranges, rectangular walls, no energy or packet model, five seeds, and no proof of global optimality.

**What did each member actually do?** Answer using the real contribution log. The planned roles alone are not evidence of completed student work.
