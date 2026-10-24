# Testing and known limits

## Validated environment

- Python 3.12.14 on Linux.
- NumPy 2.3.5 and Matplotlib 3.10.8.
- Core and transitive packages are pinned in `requirements-lock.txt`.
- No GPU, API key, database, sensor device, or external runtime service is needed.

The project requires Python 3.12 or newer because the locked ContourPy version requires it. The prepared instance was tested on 3.12. A GitHub Actions job is configured for 3.12 and 3.13. Remote outcomes must be read from Actions; the workflow file alone is not proof of a passing remote run.

## Automated tests

```bash
python -m unittest discover -s tests -v
```

**Recorded outcome: 38 tests passed.** No failed, skipped, or expected-failure tests. The suite covers:

- Segment crossings, tangent and corner touches, parallel segments, and range boundaries.
- Vectorised visibility against scalar visibility for every pair in a small obstacle map.
- Paths through relay sensors, sensor groups without a base path, and empty layouts.
- Invalid terrain values, duplicate sensors, invalid IDs, and infeasible maps.
- Valid GA/MA results, deterministic seeds, and genetic operator validity.
- Local repair of a hole, repair of an isolated sensor, and removal of redundancy.
- A tiny exhaustive optimum check, evaluation budget limits, and best-so-far progress.
- HTTP health, home page, actual solve, input rejection, busy response, and file exposure rejection.

## Result verification

```bash
python scripts/check_results.py
```

This checks all 75 exported layouts using coordinates instead of cached matrices. It compares the metrics with the CSV, checks summary means, checks all five GA/no-local-MA pairs and equal budgets, and reruns the declared seed-11 GA/MA pair. Timing is not compared because it varies by machine.

The main comparison has 30 feasible GA/MA runs, 15 feasible greedy records, and 15 failed random records. Ten equal-budget runs and five no-local runs are feasible. The deterministic greedy records are repeated for table alignment; they are not independent trials.

## Functional checks

The prepared instance ran both CLI algorithms, saved JSON and a plot, and ran the independent `verify` command. It also served the browser page, returned a healthy status, and completed a real MA request.

A Playwright smoke test used installed system Chromium. It ran GA and MA with Two walls, seed 11, and 70 generations, checked the displayed sensor counts, downloaded and independently checked both JSON files, checked widths of 1440, 768, and 390 pixels, and found no JavaScript errors. The screenshot is `docs/figures/demo-desktop.png`.

To rerun this optional check, install `requirements-browser.txt`, have Chromium installed, start `python -m wsn serve`, then run:

```bash
python scripts/browser_smoke.py --screenshot results/local/demo.png
```

If no system browser is present, Playwright needs its documented browser installation step. During this task, downloading Playwright's own browser was denied by network policy. The already-installed system Chromium was used successfully. The application itself does not need Playwright.

## Rebuild the report

```bash
python -m pip install -r requirements-docs.txt
python scripts/build_figures.py
python scripts/build_docs.py
```

The PDF and Word files include the report, assessment checklist, role plan, and discussion guide. They are generated from Markdown. Names and IDs remain blank. PDF text is checked for expected content after generation. A font installed on the system may change the exact page layout. The reference PDF was 19 pages in the prepared environment.

## Limits

Coverage is checked at free integer grid points, not throughout continuous space. The sensing model is a fixed radius with perfect yes/no visibility. The maps are synthetic, small, static, and rectangular. There is no energy, interference, packet-loss, elevation, or moving-sensor model.

Both searches begin with a feasible greedy seed. The experiment does not measure feasibility discovery from a fully random population. Five seeds and three maps are limited evidence. The equal-evaluation test covers only Two walls. No global optimum or broad statistical significance is claimed.

Precomputation takes memory proportional to `N²` for `N` free points. The implementation rejects more than 5,000 free points, but that upper cap is not a promise that every allowed size fits every computer. The included maps have at most 433 free points. A sparse or on-demand geometry model would be needed for large maps.

Local search accepts only strict improvements. It may stop at a plateau and does not guarantee that every proposed repair succeeds. The best-so-far record and elitism retain the feasible initial solution. The browser server is a local demo and has no public-service authentication or deployment features.

The six papers' metadata is verified, but full papers were not accessible in this environment. Detailed source-reading work remains for the team. Real contributions, course approval, group registration, and final submission cannot be completed by the assistant.
