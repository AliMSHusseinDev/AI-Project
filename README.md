# Fieldlab · Wireless sensor network deployment optimization

A Python implementation of Genetic Algorithm (GA) and Memetic Algorithm (MA) sensor placement for **AI310 / CS361, Fall 2026**. Build a terrain in the browser, run either search, and inspect whether each free cell center is covered and each sensor can send data to the base. The search minimizes active sensors among feasible deployments.

## Start on Windows

Install **Python 3.12** with the Windows Python launcher and **Node.js 22 or 24** with npm. Extract the project into a writable folder. Double-click **run.bat** there. It installs dependencies, starts the API in a second window, and starts the frontend. Once Vite is ready, open **http://localhost:5173**. Close both process windows when finished. Package downloads require internet access on first installation. Running the installed simulator is local.

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

## Use the studio

1. **Design the terrain.** Set a square grid from 20 to 100 cells per side. Set the independent sensing and communication radii. Advanced settings control the base coordinates, candidate spacing and terrain seed.
2. **Automatic placement.** Choose the requested obstacle count, then **Generate obstacles**. This explicitly replaces the current obstacles using the seed. The count slider stages a request. The map heading shows the actual count. Up to 15% of cells may be blocked.
3. **Manual placement.** Press **O** to add one block. Click and drag a block to move it. To resize, select it, hover over it, press **R**, then drag a corner. Click empty ground to deselect. Use **Delete**, **Ctrl+Z**, and **Ctrl+Y** for edits. Save environment downloads JSON. Load accepts saved layouts and the supplied scenario files.
4. **Optimize.** Select GA, MA or Comparison and click Run. Search settings include the algorithm seed, population, generation limit, unique-score budget and fraction of MA children that receive local search. Comparison independently runs both on the same terrain. Cancel stops a pending run. The map selector chooses which result is drawn.
5. **Inspect and validate.** Read the four cards and toggle map layers. Blue circles mark maximum communication range. Red circles mark maximum sensing range. The purple diamond is the base. Actual links require clear sight. **Validate Solution** rebuilds coverage and routes. Check **Fine sampling** for four extra samples per free cell. A failed check lists the violated conditions.
6. **Compare and export.** Open Results to see the table and convergence curves. After Comparison, select exactly one format and click **Download Comparison**. The browser downloads that file and Python stores a copy in `outputs/`. The PNG contains the table alone. Repeated exports replace that format's file. The folder begins empty and is created on demand in a fresh checkout.
7. **Run experiments.** Open Experiments. Choose one to ten paired trials per scenario and run the benchmark. The summary and session history are available there. The command below also saves full trial records and histories. Stored API job IDs are temporary. Changing the environment clears old displayed results.

## What the algorithms measure

The integer pair (x, y) is the center of a cell, with y increasing down the map. Every free center must be sensed. Sites lie on a configurable lattice of free centers and exclude the base. Each rectangle occupies its closed physical footprint. Touching an edge or corner blocks a sight line. The base remains a monitoring point and contributes no sensing.

The search precomputes visible cells and radio neighbors. A breadth-first tree from the base identifies all sites capable of routing data. If their combined sensing masks leave a hole, no subset can meet both goals on these sites. A greedy cover and its relay paths supply the initial reference deployment. A chromosome stores a set of distinct sites.

GA uses tournaments of three, geographic crossover (85%), move/add/remove mutation (80%, equally split), and two elites. A score is `(holes + 5 * disconnected) * (candidate_count + 1) + active_count`. Lower is better. MA runs the same evolution and on selected children tries short moves toward uncovered points or across gaps between components. Each local round tries at most eight neighbors. Feasible children may lose redundant sensors. All new scores count toward the same budget. Independent checks use a different line intersection method and graph traversal.

A successful run demonstrates full **discrete** coverage and connectivity under this model. It gives a best found sensor count. It does not certify a global minimum or continuous coverage. See the algorithm report for complexity, stopping rules and experiment results.

## Reproduce the evidence

From the project root on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend/tests
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m Dataset.generate_dataset
.\.venv\Scripts\python.exe -m backend.app.benchmarks --trials 10 --out Assessment/repeat
.\.venv\Scripts\python.exe -m scripts.verify_project --replay
```

The supplied experiment uses five synthetic terrains, environment seed 42, and paired algorithm seeds 100 through 109. Each method receives up to 100 distinct scores. The trial JSON stores coordinates, generations, local-search statistics and convergence. Runtime depends on the machine. The original summaries use sample standard deviations across repeated algorithm seeds.

For optional browser QA, install Playwright into the same environment and run `python -m playwright install chromium`. With both servers running and an empty exports folder, run `python scripts/check_browser.py`. The script uses a temporary browser profile and removes its own verified test download. Use `--chromium PATH` to select a system Chromium. To regenerate the recorded evidence intentionally, pass `--evidence Assessment/evidence/browser.json`, use `--junitxml=Assessment/evidence/tests.xml` with pytest, and use `--out Assessment/evidence` with the ten-trial benchmark. Then run `python scripts/generate_documentation.py` and `python scripts/generate_assessment.py`.

## Submission guide

| Location | Contents |
|---|---|
| backend/app | Environment, geometry, shared fitness, search, independent audit, API workers and exports |
| backend/tests | Geometry, model, algorithms, validation, cancellation and export tests |
| frontend/src | React controls, Canvas interaction, comparison and benchmark tables |
| Dataset | Reproducible synthetic environments and generation rules |
| Documentation | Six numbered course reports including five design diagrams |
| Documentation/Literature Review | Six original reviews with links to journal full texts and one page of team allocations |
| Assessment | Assessment Evidence and Experiments.pdf, trial records, summaries and test evidence |
| TEAM_CONTRIBUTIONS.md | Editable six-member contribution record |
| outputs | Explicit comparison downloads only |

The recorded build, tests and browser checks used Linux, Python 3.12 and Chromium. Native Windows execution remains to be verified. Enter the registered team names, IDs and actual contributions before submission.
