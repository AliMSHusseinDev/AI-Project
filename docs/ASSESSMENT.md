# Assessment and self-check

This checklist follows the criteria given in the course instructions. The instructor did not provide mark weights, so this file does not invent marks or promise a grade.

| Course criterion | Evidence in this project | What to explain in the discussion |
|---|---|---|
| Problem complexity and correct algorithms | Variable sensor count, obstacle geometry, coverage constraints, base reachability, GA and MA | Why covering the map alone is not enough; why an optimal minimum is difficult |
| Quality of experiments and documentation | Three maps, five seeds, random and greedy baselines, GA/MA, a budget check, and local-search removal test | Same generations cost different amounts of work; why a five-seed result is limited |
| Correct analysis and design diagrams | Use cases, data flow, data classes, and both algorithm flows in `DESIGN.md` | Trace one request from the screen to a saved layout and its verification |
| Implementation correctness | Geometry/network tests, independent layout checks, CLI and HTTP functional runs | Show a blocked link, a relay path, a repaired hole, and a detected impossible map |
| Individual discussion and contributions | Six role descriptions, shared work plan, and blank actual contribution log | Each member must explain the complete project and record actual work |

## Measured evidence

- 38 automated tests passed in the prepared Python 3.12 environment.
- 75 experiment run files were generated and checked using an independent coordinate-based verifier.
- All 30 GA/MA runs in the main comparison had 100% grid coverage and 100% base connectivity.
- All 10 equal-budget GA/MA runs were feasible and used exactly 3,000 unique fitness evaluations each.
- The five MA runs with local search disabled matched the paired GA layouts and histories.
- All 15 random baseline runs failed full coverage and/or full connectivity; they are reported as failures, not silently omitted.
- The greedy baseline is deterministic. Its repeated table rows are the same baseline, not five independent discoveries.
- A real HTTP request ran MA on Two walls and returned a feasible result; CLI save, plot, and verification also ran.

## Submission checklist

- [ ] Add six names, student IDs, group number, and programme.
- [ ] Register the group and obtain TA approval.
- [ ] Check the TA's rules for AI use and disclose the assistance provided.
- [ ] Each member reads their assigned paper and reviews the other summaries.
- [ ] Each member runs tests, checks a layout, and records their real contribution.
- [ ] Confirm that grid coverage and synthetic maps are acceptable for this assignment.
- [ ] Run the documented installation and experiment commands on the submission machine.
- [ ] Submit the code, documentation, dataset files, and experiment evidence through the course system.
- [ ] Confirm the Week 12/13 deadline and prepare all six members for the discussion.

These boxes describe real human actions. They remain unchecked because the assistant cannot register students, attend the discussion, approve its own academic use, or truthfully invent student contributions.
