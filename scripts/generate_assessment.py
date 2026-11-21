"""Build the assessment from the five browser comparisons and the executed tests."""

import json
from xml.etree import ElementTree as ET
from reportlab.platypus import PageBreak
from report_layout import ROOT, paragraph as p, heading as h, save, table

folder = ROOT / "Assessment"
runs = json.loads((folder / "evidence/assessment_runs.json").read_text())
suite = ET.parse(folder / "evidence/tests.xml").find(".//testsuite")
browser = json.loads((folder / "evidence/browser.json").read_text())
specs = [(20, 0), (20, 2), (40, 0), (40, 8), (60, 18)]
questions = [
    "Check full coverage and a route for every sensor on an open terrain.",
    "Compare with 1. Do two obstacles remove sampled sites or change the count needed?",
    "Compare with 1. Keep the terrain clear and double the grid side.",
    "Compare with 3. Measure how eight obstacles change the monitored set and relay needs.",
    "Compare with 4. Test a larger area with more obstacles and the same two radii.",
]
assert len(runs) == len(specs) and len(browser) >= 5
settings = dict(seed=7, population=18, generations=40, budget=600, local_fraction=0.45)
inputs = [["No.", "Grid side", "Obstacle count", "Base X, Y", "What to examine"]]
metrics = [
    [
        "No.",
        "Method",
        "Sensors",
        "Coverage %",
        "Connected %",
        "Unique scores",
        "Full gens.",
        "Time (s)",
        "Audit",
    ]
]
for index, (entry, (size, count), question) in enumerate(
    zip(runs, specs, questions, strict=True), 1
):
    env = entry["environment"]
    assert (env["size"], len(env["obstacles"]), env["base"]) == (
        size,
        count,
        [size // 2, size // 2],
    )
    assert (
        env["spacing"],
        env["sensing"],
        env["communication"],
        env["seed"],
        env["base_margin"],
    ) == (2, 5.5, 8, 42, 0)
    inputs.append([index, size, count, f"{size // 2}, {size // 2}", question])
    assert [r["algorithm"] for r in entry["results"]] == ["GA", "MA"]
    for r, a in zip(entry["results"], entry["validation"], strict=True):
        assert r["settings"] == settings and a == r["audit"]
        metrics.append(
            [
                index,
                r["algorithm"],
                r["count"],
                f"{r['coverage']:.1f}",
                f"{r['connectivity']:.1f}",
                r["evaluations"],
                r["generations"],
                f"{r['seconds']:.4f}",
                "PASS" if a["passed"] else "FAIL",
            ]
        )

body = [
    h("1   How the project meets the criteria"),
    p(
        "Complexity and correctness: the Python search balances coverage, relays and sensor count. Experiment quality: five paired GUI runs save exact maps, seeds and measurements. Design: Documents 1, 2, 6 and 7 connect the five diagrams to the code. Implementation: backend/tests and scripts/check_browser.py check the calculations and the student workflow."
    ),
    h("2   Run these five experiments"),
    p(
        "Start the application with run.bat. Use a fresh page with the default one-cell station. In Environment select Automatic. Before each setup, set Obstacle count to 0 and click Generate obstacles. This clears the previous layout so it cannot block a grid change."
    ),
    table(
        [
            ["Common control", "Value", "Common control", "Value"],
            ["Sensing radius", "5.5", "Communication radius", "8"],
            ["Site spacing", "2", "Environment seed", "42"],
            ["Algorithm seed", "7", "Population", "18"],
            ["Generations", "40", "Evaluation budget", "600"],
            ["Run mode", "Comparison", "Local fraction", "0.45"],
        ],
        [125, 74, 155, 136],
    ),
    p(
        "For each row, enter Grid size and Base station X and Y. Confirm numeric fields with Enter. Set the common values and the row's Obstacle count. Click Generate obstacles once and check that Seed is 42. Repeated clicks on a nonempty generated map choose a new seed. Record the available monitoring points and blocked area."
    ),
    table(inputs, [32, 55, 72, 65, 266]),
    p(
        "Select Comparison and enter the common search values above. Click Run comparison. Wait for both runs. Click Validate Solution and record each audit. Open Results. Record sensor count, coverage, connectivity, time, unique scores, full generations and stop reason for both methods. Return to Environment for the next row."
    ),
    PageBreak(),
    h("3   Calculate the metrics"),
    p(
        "Coverage (%) = 100 × covered available points / available monitoring points. With spacing 2 on a 20 by 20 clear grid, each axis has ten sites. Covering all 100 sites gives 100%. Obstacle cells remove only the lattice sites they contain."
    ),
    p(
        "Connectivity (%) = 100 × sensors reachable from the station / active sensors. Eight reachable sensors out of eight gives 100%. A zero-sensor result reports zero connectivity. Radios need both range and a clear path on every hop."
    ),
    p(
        "One fitness evaluation is one new score for a unique set of sensor sites. A cached score is free. MA charges its local trials to its own budget of 600. A partial last generation can spend scores without counting as a completed generation."
    ),
    p(
        "For two feasible results, sensor reduction (%) = 100 × (GA sensors - MA sensors) / GA sensors. Positive means MA used fewer. Zero means a tie. Negative means GA used fewer. Time is elapsed seconds for geometry setup, search and final audit. A later button audit is separate."
    ),
    h("4   Actual browser results"),
    table(metrics, [27, 47, 46, 59, 61, 61, 49, 63, 47]),
    p(
        "All five GA runs stopped at the generation limit. Each MA run reached its evaluation budget. Equal caps allow different amounts of work. Timing can change on another computer."
    ),
    h("Reading the five pairs"),
]
for index, entry in enumerate(runs):
    ga, ma = entry["results"]
    blocked = sum(r["w"] * r["h"] for r in entry["environment"]["obstacles"])
    reduction = (
        f"Sensor reduction {100 * (ga['count'] - ma['count']) / ga['count']:.1f}%."
        if all(a["passed"] for a in entry["validation"])
        else "A failed audit prevents a feasible count comparison."
    )
    body.append(
        p(
            f"{index + 1}. {blocked} blocked cells; {ga['monitoring_count']} available sites. GA used {ga['count']} sensors and MA used {ma['count']}. {reduction}",
            "small",
        )
    )
body += [
    PageBreak(),
    h("5   Validation and testing"),
    p(
        "Validate Solution rebuilds the monitoring lattice and checks the current station footprint and obstacle layout. It checks unique, legal sensor positions, then uses its own sight-line test and walks the graph from the station. The report checks recorded values against this calculation. Every mandatory check must pass."
    ),
    p(
        f"The recorded pytest run executed {suite.attrib['tests']} cases with {suite.attrib['failures']} failures, {suite.attrib['errors']} errors and {suite.attrib['skipped']} skips. The suite includes collisions, monitoring counts, exhausted area, duplicate scores, budget stops, local moves, disconnected radios, false coverage claims, stale results and selective exports."
    ),
    h("Browser evidence"),
    *[p(line, "small") for line in browser],
    h("6   What the comparisons show"),
    p(
        "In experiments 1 and 2, the two small obstacles missed the sampled sites. The available count stayed at 100. Both algorithms still found routes and used the same counts as on the clear map. In experiment 3, doubling the grid side gave four times as many sites before blocking."
    ),
    p(
        "On the 40 by 40 map, eight blocks reduced the number of monitored sites from 400 to 384. Both methods nevertheless used more sensors than on the open map. The largest map needed the most sensors and took longest for each method. Every audit passed for the defined monitoring grid."
    ),
    p(
        "MA used fewer sensors in the two small cases. GA used fewer in the other three at these settings. Obstacles can remove targets and also cut sight lines. The five cases change shape, area and layout together. The results describe these searches and do not establish a global minimum."
    ),
    h("Reproduce the evidence"),
    p(
        "Assessment/evidence/assessment_runs.json records the five GUI pairs. With both servers running, scripts/run_assessment.py repeats them in Chromium. See README.md for the command. tests.xml and browser.json record the regression checks. The separate trials.json and summary.csv files contain supplemental repeated runs with a different budget and seeds. Document 6 reports those results.",
        "small",
    ),
]
save(
    folder / "Assessment Evidence and Experiments.pdf",
    "Assessment evidence and experiments",
    body,
    "Assessment",
)
