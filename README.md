# AI Project · Wireless sensor network deployment optimization

A Python implementation of Genetic Algorithm (GA) and Memetic Algorithm (MA) sensor placement for **AI310 / CS361, Fall 2026**. Build a terrain in the browser, run either search, and inspect whether each available monitoring site is covered and each sensor can send data to the base. The search minimizes active sensors among feasible deployments.

## Start on Windows

Install **Python 3.12** with the Windows Python launcher, extract the entire ZIP, and double-click **run.bat**. The launcher opens a persistent console and installs Python requirements on first use or when they change. One local server hosts both the API and the packaged website. It verifies the homepage and API over HTTP before opening your browser. The console prints the actual URL. Keep it open while using the site. Node.js is only needed for frontend development. To refresh the packaged website after editing its source, run `npm --prefix frontend run build:studio`.

For a manual setup, run these PowerShell commands from the project root.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix frontend ci
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000
```

In another PowerShell window, from the same project root:

```powershell
npm --prefix frontend run dev -- --host 127.0.0.1
```

On Linux, use `python3.12 -m venv .venv`, then `.venv/bin/python` for Python commands. Install the frontend with `npm --prefix frontend ci`. The server processes use ports 8000 and 5173. A single API server owns its job records. Keep it running while inspecting or exporting results.

A previous API (commit `74596e6`) replaced a temporary `pending` file with `progress` on every progress callback. Job state now passes through a multiprocessing manager. The launcher verifies the live API and homepage after Uvicorn starts listening. The browser checks the API protocol. Unexpected worker failures log the job ID and traceback in the API console. The original Windows lock owner is unknown. The regression suite exercises 20 GA, 20 MA and 20 Comparison jobs across two API lifespans and tests file-replacement denial. See `Assessment/evidence/progress-diagnostic.txt` for the historical fault injection.

## Use the studio

1. **Design the terrain.** Set a square grid from 20 to 100 cells per side. Set the independent sensing and communication radii. The visible terrain parameters control station coordinates, site spacing and environment seed.
2. **Automatic placement.** Set the obstacle count and click **Generate obstacles**. Each click replaces the obstacles at the selected count. If the entered seed would reproduce the current nonempty layout, the app advances the seed until the layout changes. The field and map show the seed actually used. To reproduce an earlier layout, enter its seed with the same grid, station and count. A count of zero clears the map. Obstacles stay clear of each other and the station and cover at most 15% of the grid.
3. **Manual obstacle placement.** Hover over a free grid cell and press **O** to place one cell-sized block there, or choose **Add (O)** and click the cell. Click and drag a block to move it. To resize, select it, hover over it, press **R**, then drag an edge or corner. Click empty ground to deselect. In either mode you can drag the station or select it, hover, press **R** and drag an edge or corner to resize around the same center. **Delete** removes the selected obstacle or manual point. **Ctrl+Z** and **Ctrl+Y** undo and redo edits. Save environment downloads JSON. Load accepts saved layouts and the supplied scenario files.
4. **Monitoring points.** Automatic mode uses the unblocked monitoring lattice. Choose **Manual** under **Monitoring points**, press **Add points** and click the desired free cells. Press **Escape** to finish. Select and drag a point to move it. At least one is required to run. Switching back preserves the points. A grid resize commits on release and keeps the last valid map if any saved object would stop fitting.
5. **Optimize.** Select GA, MA or Comparison and click Run. Visible optimization settings include the algorithm seed, population, generation limit, unique-score budget and fraction of MA children that receive local search. Comparison independently runs both on the same terrain. Cancel stops a pending run. The map selector chooses which result is drawn.
6. **Inspect and validate.** Read the four cards and toggle map layers. Blue circles mark maximum communication range. Red circles mark maximum sensing range. The purple diamond marks the station center inside its footprint. Actual links require clear sight. **Validate Solution** rebuilds coverage and routes. It independently checks site placement and environment integrity as well. A failed check lists the violated conditions.
7. **Compare and export.** Open Results to see the table and convergence curves. After Comparison, select exactly one format and click **Download Comparison**. The browser downloads that file and Python stores a copy in `outputs/`. The PNG contains the table alone. Repeated exports replace that format's file. The folder begins empty and is created on demand in a fresh checkout.
8. **Repeat the five assessment experiments.** Use the exact settings in `Assessment/Assessment Evidence and Experiments.pdf` and run each in Comparison mode. The separate automated benchmark is available from the command line. Changing geometry clears previous results.

## What the algorithms measure

The integer pair (x, y) is the center of a cell, with y increasing down the map. In Automatic mode monitoring sites start at (0,0) and repeat every Site spacing units on both axes. Available points are total lattice sites minus those inside obstacle cells. Manual mode uses only the saved cell centers as targets. Candidate sensors still use the configured lattice. Sensor sites also exclude the station footprint. Its odd square side is 1 + 2 × base_margin cells (1 to 11). It prevents physical overlap. The center is the radio endpoint. Sites inside the footprint still require sensing. Touching an obstacle edge or corner blocks a sight line.

A new obstacle can be as small as one cell. Additional capacity is the least of remaining count slots, remaining area budget in whole cells, and free cells outside all blocks, saved manual points and the station. With whole-cell aligned rectangles, every such free cell fits a minimum-size block. Automatic generation replaces the layout on request and may use up to the absolute count cap. Manual additions preserve existing blocks.

The search precomputes visible cells and radio neighbors. A breadth-first tree from the base identifies all sites capable of routing data. If their combined sensing masks leave a hole, no subset can meet both goals on these sites. A greedy cover and its relay paths supply the initial reference deployment. A chromosome stores a set of distinct sites.

GA uses tournaments of three, geographic crossover (85%), move/add/remove mutation (80%, equally split), and two elites. A score is `(holes + 5 * disconnected) * (candidate_count + 1) + active_count`. Lower is better. MA runs the same evolution and on selected children tries short moves toward uncovered points or across gaps between components. Each local round tries at most eight neighbors. Feasible children may lose redundant sensors. All new scores count toward the same budget. Independent checks use a different line intersection method and graph traversal.

A successful run demonstrates full **discrete** coverage and connectivity under this model. It gives a best found sensor count. It does not certify a global minimum or continuous coverage. A manual coverage percentage refers to the selected targets. See the algorithm report for complexity, stopping rules and experiment results.

## Reproduce the evidence

From the project root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend/tests
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m Dataset.generate_dataset
.\.venv\Scripts\python.exe -m backend.app.benchmarks --trials 10 --out Assessment/repeat
.\.venv\Scripts\python.exe -m scripts.verify_project --replay
```

The supplemental automated benchmark uses five synthetic terrains, environment seed 42, and paired algorithm seeds 100 through 109. Each method receives up to 100 distinct scores. The trial JSON stores coordinates, generations, local-search statistics and convergence. Runtime depends on the machine. The original summaries use sample standard deviations across repeated algorithm seeds.

For optional browser QA, install Playwright into the same environment and run `python -m playwright install chromium`. With both servers running and an empty exports folder, run `python scripts/check_browser.py`. The script uses a temporary browser profile and removes its own verified test download. Use `--chromium PATH` to select a system Chromium. To regenerate the recorded evidence intentionally, pass `--evidence Assessment/evidence/browser.json`, use `--junitxml=Assessment/evidence/tests.xml` with pytest, and use `--out Assessment/evidence` with the ten-trial benchmark. Use `python scripts/run_assessment.py --out Assessment/evidence/assessment_runs.json` to exercise the five specified comparisons in the live browser. Then run `python scripts/generate_documentation.py` and `python scripts/generate_assessment.py`.

## Submission guide

| Location | Contents |
|---|---|
| backend/app | Environment, geometry, shared fitness, search, independent audit, API workers and exports |
| backend/tests | Geometry, model, algorithms, validation, cancellation and export tests |
| frontend/src | React controls, Canvas interaction, comparison table and convergence chart |
| Dataset | Reproducible synthetic environments and generation rules |
| Documentation | Six numbered course reports including five design diagrams |
| Documentation/Literature Review | Six original reviews with links to journal full texts and one page of team allocations |
| Assessment | Assessment Evidence and Experiments.pdf, trial records, summaries and test evidence |
| TEAM_CONTRIBUTIONS.md | Editable six-member contribution record |
| outputs | Explicit comparison downloads only |

The recorded build, tests and browser checks used Linux, Python 3.12 and Chromium. Native Windows execution remains to be verified. Enter the registered team names, IDs and actual contributions before submission.
