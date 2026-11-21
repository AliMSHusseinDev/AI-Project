"""Compose the assessment only from completed run and test records."""

import json
import xml.etree.ElementTree as ET
from reportlab.platypus import PageBreak
from generate_documentation import results_table
from report_layout import (
    ROOT,
    heading as h,
    paragraph as p,
    table,
    save,
    convergence,
    scale_chart,
)

folder = ROOT / "Assessment"
data = json.loads((folder / "evidence/trials.json").read_text())
records = data["records"]
summary = data["summary"]
suite = ET.parse(folder / "evidence/tests.xml").find(".//testsuite")
cases = suite.findall("testcase")
browser = json.loads((folder / "evidence/browser.json").read_text())
if len(records) != 100 or len(cases) != int(suite.attrib["tests"]):
    raise ValueError("Assessment requires complete trial and test records.")
valid = sum(r["passed"] for r in records)
example = next(
    r
    for r in records
    if (r["case"], r["algorithm"], r["seed"]) == ("scale40", "GA", 100)
)
initial, final = example["initial_count"], example["count"]
rows = [["Check and purpose", "Expected behavior", "Actual outcome"]]
categories = [
    (
        "test_euclidean_distance",
        "Distance",
        "Match known axis, diagonal and zero distances.",
    ),
    (
        "test_closed_obstacle_geometry",
        "Line of sight",
        "Both geometry methods block crossings and touches.",
    ),
    (
        "test_obstacle_limits_and_seed",
        "Generation",
        "Replay the same map at the maximum count.",
    ),
    (
        "test_invalid_environment_rejected",
        "Input errors",
        "Reject invalid dimensions, overlaps and limits.",
    ),
    (
        "test_candidates_and_monitoring_domain",
        "Domain",
        "Exclude blockers and keep the base off the site list.",
    ),
    (
        "test_visibility_blocks_both_radio_and_sensing",
        "Coverage and links",
        "A wall hides a nearby point and blocks a radio edge.",
    ),
    (
        "test_routes_components_and_zero_sensors",
        "Network",
        "Find a relay chain and two separate islands.",
    ),
    (
        "test_fitness_order_and_cache",
        "Fitness",
        "Feasible wins. A repeated score consumes no budget.",
    ),
    (
        "test_seed_and_spatial_operators",
        "GA operators",
        "Use a spatial split, tournament and legal mutations.",
    ),
    (
        "test_targeted_local_search",
        "MA repair",
        "Move toward a hole or island, keep improvements and stop.",
    ),
    (
        "test_evolution_reproducible_elitism_budget",
        "Evolution",
        "Repeat the seeded layout. Best cost never rises.",
    ),
    (
        "test_proven_infeasibility_and_audit",
        "Impossible terrain",
        "Tiny ranges give an infeasible result and failed audit.",
    ),
    (
        "test_independent_audit_tampering_and_fine_grid",
        "Validation",
        "Reject altered metrics and coordinates. Count fine samples.",
    ),
    (
        "test_fine_sampling_reveals_gap",
        "Finite sampling",
        "Fine samples reveal a gap despite full center coverage.",
    ),
    (
        "test_comparison_validation_and_selective_exports",
        "Comparison API",
        "Run both methods. Emit only the selected file.",
    ),
    (
        "test_cancel_and_incomplete_export",
        "Job lifecycle",
        "Stop a benchmark and reject unusable exports.",
    ),
]
for prefix, name, expected in categories:
    matches = [case for case in cases if case.attrib["name"].split("[")[0] == prefix]
    if not matches:
        raise ValueError("Missing test evidence for " + prefix)
    failures = sum(
        any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        for case in matches
    )
    outcome = (
        f"{len(matches) - failures}/{len(matches)} PASS"
        if not failures
        else f"{failures} failed or skipped"
    )
    rows.append([name, expected, outcome])


def experiment_detail():
    result = []
    for name in ["scale20", "scale40", "scale60", "clear40", "dense40"]:
        group = [r for r in records if r["case"] == name]
        first = group[0]
        result.append(
            [
                name,
                first["size"],
                first["obstacles"],
                first["blocked_cells"],
                f"{100 * first['blocked_cells'] / first['size'] ** 2:.2f}%",
            ]
        )
    return result


body = [
    h("1   Problem complexity and algorithm correctness"),
    p(
        "Choose the smallest sensor set found that meets both goals. Every free cell center needs a visible sensor in range. Every deployed sensor needs a clear radio route to the base. A relay may keep a distant group connected even when its own sensing area is already covered."
    ),
    p(
        "For K possible sites there are 2 to the power K subsets. Testing them all quickly becomes too expensive. The GA uses three-way tournaments, geographic crossover, move/add/remove mutation and two elites. MA uses the same search and spends some evaluations on short local moves."
    ),
    table(
        [
            ["Quantity", "Calculation or decision"],
            [
                "Coverage (%)",
                "100 × covered monitoring points / all monitoring points.",
            ],
            [
                "Connectivity (%)",
                "100 × reachable sensors / active sensors. With zero active sensors the app reports zero.",
            ],
            [
                "Cost",
                "(holes + 5 × disconnected sensors) × (K + 1) + active sensors. Minimize this value.",
            ],
            [
                "Feasibility",
                "All free cell centers covered, all deployed sensors reachable, and every site legal.",
            ],
        ],
        [127, 363],
    ),
    h("Checks against wrong answers"),
    p(
        "The optimizer clips line segments against closed rectangles and uses BFS for routes. The auditor tests separating axes and uses a depth-first walk. Both include corner touches. The tests include an impossible input. Its expected result is a failed solution audit."
    ),
    h("2   Experiment design"),
    p(
        "Question A: How does grid size affect cost? Question B: What changes across obstacle layouts? Question C: Does the local search help under the same evaluation limit?"
    ),
    p(
        "Use the five saved environments in Dataset/scenarios. Fix environment seed 42, sensing radius 5.5, radio radius 8 and spacing 2. Use population 12, at most 150 generations, and a budget of 100 distinct scores. Run GA and MA separately for seeds 100 to 109. Each pair starts with the same input. Timing covers geometry setup, search and audit."
    ),
    table(
        [["Scenario", "Grid side", "Blocks", "Blocked cells", "Area blocked"]]
        + experiment_detail(),
        [105, 90, 85, 104, 106],
    ),
    PageBreak(),
    h("2   Measured results"),
    results_table(summary),
    p(
        f"Both methods used 100 distinct scores per run. Feasible run rate = {valid}/{len(records)} × 100 = {100 * valid / len(records):.0f}%. Every recorded coverage and connectivity value was 100%. Each reported layout had zero disconnected sensors. The feasible starting layout makes a high success rate easier to achieve."
    ),
    h("A. Grid size"),
    p(
        "From side 20 to 60, the free domain grew and both methods needed more sensors and time. The number and shapes of blocks also changed. The three recipes keep the count of obstacles per grid area equal."
    ),
    h("B. Obstacle layouts"),
    p(
        "At side 40, the clear terrain had the lowest mean sensor count for both methods. The ten-block terrain did not always require more sensors than the four-block terrain. New blocks can hide points, remove points from the domain, or change the greedy start. These trials repeat algorithm seeds on fixed maps."
    ),
    h("C. Equal-budget comparison"),
    p(
        "MA used fewer sensors on average on the smallest terrain. GA used fewer on average on the other four. Local moves can repair a child but leave fewer evaluations for later offspring. Runtime includes setup, so it need not follow the number of generations."
    ),
    h("Worked reduction"),
    p(
        f"On scale40 with algorithm seed 100, the connected greedy start used {initial} sensors. GA ended with {final}. Sensor reduction = ({initial} - {final}) / {initial} × 100 = {100 * (initial - final) / initial:.1f}%. This reference is a starting layout on the same terrain."
    ),
    p(
        "Source: Assessment/evidence/trials.json records each layout, seed, time and history. summary.csv gives group means. SD uses n - 1 in the denominator. Timing varies by machine.",
        "small",
    ),
    PageBreak(),
    h("Best cost during one paired run"),
    convergence(records),
    p(
        "This chart uses scale40 and algorithm seed 100. It samples best cost at each completed generation. The horizontal axis counts unique scores, including local trials. The known feasible start keeps the best cost equal to its active sensor count."
    ),
    h("Mean sensor count by grid size"),
    scale_chart(summary),
    h("3   Analysis and diagram checks"),
    table(
        [
            ["Diagram and document", "Match to the implementation"],
            [
                "Level 0 data flow / Document 1",
                "main.py validates the request. Workers compute layouts. A job record supplies Results and export.",
            ],
            [
                "Use cases / Document 2",
                "App.tsx exposes editing, saving, both runs, comparison, validation and downloads. Browser checks exercise these paths.",
            ],
            [
                "GA flow / Document 6",
                "evolution.py initializes, scores, checks the stop rule, keeps elites and fills a generation. The retained best goes to the auditor.",
            ],
            [
                "MA flow / Document 6",
                "The same loop calls improve_deployment_with_local_search on selected children. Every trial uses the same evaluator.",
            ],
            [
                "Architecture / Document 7",
                "The browser calls FastAPI. Workers call geometry and search. A separate validator rebuilds the result. Exports read the stored pair.",
            ],
        ],
        [152, 338],
    ),
    PageBreak(),
    h("4   Implementation checks"),
    p(
        f"pytest recorded {len(cases)} test cases. Failures: {suite.attrib['failures']}. Errors: {suite.attrib['errors']}. Skipped: {suite.attrib['skipped']}. The expected behavior in each row is checked by assertions."
    ),
    table(rows, [116, 270, 104]),
    h("Scope of the evidence"),
    p(
        "Five synthetic maps test discrete coverage. Extra samples can expose small gaps. The experiments give best found layouts on these sites. A proof of minimum sensor count would need a separate exact search or a matching lower bound."
    ),
    p(
        "To repeat, run python -m backend.app.benchmarks --trials 10 --out Assessment/repeat in the project environment. Rebuild the tables from the trial records. Keep the original evidence for comparison."
    ),
    h("Browser checks"),
    p(
        "Chromium exercised the editor at both grid limits, both single runs, a paired run, fine sampling, selective download and the benchmark table. The detailed checks are in evidence/browser.json. The browser run completed without an uncaught page error."
    ),
    p(
        "Evidence: tests.xml, browser.json, backend/tests and scripts/check_browser.py. Run the commands in README.md to reproduce the checks.",
        "small",
    ),
]
save(
    folder / "Assessment Evidence and Experiments.pdf",
    "Assessment evidence and experiments",
    body,
    "Assessment",
)
