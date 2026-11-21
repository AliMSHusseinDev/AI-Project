import json
from reportlab.platypus import PageBreak
from report_layout import (
    ROOT,
    paragraph as p,
    heading as h,
    table,
    save,
    flow,
    dfd,
    architecture,
    use_cases,
    convergence,
)
from literature import write_reviews, REVISION

DOC = ROOT / "Documentation"
DATA = json.loads((ROOT / "Assessment/evidence/trials.json").read_text())


def write(name, title, body):
    save(DOC / (name + ".pdf"), title, body)


def results_table(summary):
    return table(
        [["Terrain", "Method", "Valid", "Best", "Mean sensors", "Sample SD", "Mean s"]]
        + [
            [
                r["case"],
                r["algorithm"],
                f"{r['valid']}/{r['runs']}",
                r["best"],
                f"{r['mean']:.2f}",
                f"{r['sd']:.2f}",
                f"{r['seconds']:.3f}",
            ]
            for r in summary
        ],
        [78, 62, 48, 46, 90, 85, 70],
    )


def main():
    write(
        "1.Project idea in detail",
        "Wireless sensor network deployment",
        [
            p(
                "A field team wants to measure a region with as few sensors as possible. Each sensor observes nearby places and sends readings to a base station. Some readings need several wireless hops."
            ),
            h("Problem analysis"),
            p(
                "A wall can hide an unmeasured cell or cut a radio path. A relay may sense very few new cells yet keep a whole group connected. Removing it can break an otherwise good layout."
            ),
            h("Requirements analysis"),
            table(
                [
                    ["Input or rule", "Required output or behavior"],
                    [
                        "Grid, obstacles, base, two radii, candidate spacing",
                        "Show the terrain. Reject invalid geometry. Keep it fixed during a run.",
                    ],
                    [
                        "Search settings and random seeds",
                        "Run GA and MA separately. Return the best found coordinates and count.",
                    ],
                    [
                        "Full coverage and routes",
                        "Check every free cell center and every sensor. Show failures.",
                    ],
                    [
                        "Interactive work and repeated tests",
                        "Keep the editor responsive. Record settings and scores for replay.",
                    ],
                ],
                [190, 300],
            ),
            h("Mathematical analysis"),
            p(
                "Let S be the set of active sites. Minimize its size |S|. A point is covered when its Euclidean distance to a sensor is at most the sensing radius and their segment is clear. Distance is the square root of (change in x squared + change in y squared)."
            ),
            p(
                "Join two radios when distance is within communication range and the segment is clear. Every active sensor must be reachable from the base in this graph. The base is a radio node only. Free cell centers include the base cell."
            ),
            h("Level 0 data flow diagram"),
            dfd(),
            p(
                "Rectangles are external users. Rounded boxes process data. Parallel lines hold completed run records. The graph model uses fixed ranges and opaque walls. Cell-center coverage does not prove coverage between samples.",
                "small",
            ),
        ],
    )
    write(
        "2.Main functionalities",
        "Using the deployment studio",
        [
            p(
                "Load a saved environment or set the grid size, base, radii, spacing and seed. The count limit grows with grid area. Generate obstacles applies the current count and seed."
            ),
            h("Edit the terrain"),
            p(
                "In Manual mode press O to add one block. Click a block and drag to move it. Hover over the selected block and press R. Drag a corner to resize it. Use Delete, Ctrl+Z and Ctrl+Y to delete, undo and redo. A blocked move stops at the last legal cell."
            ),
            h("Run and inspect"),
            p(
                "Select GA, MA or Comparison and run it. The four cards show count, coverage, reachable sensors and time. In a comparison, switch the map between methods. Blue circles show radio range. Red circles show sensing range. Links show actual clear paths. Layers only change the drawing."
            ),
            p(
                "Validate Solution rechecks the current layouts. Fine sampling tests four extra points per free cell. Edits clear old results. Save environment stores a JSON layout. Load checks it before use."
            ),
            h("Use case diagram"),
            use_cases(),
            p(
                "The lines show actions available to the student. In Results, select CSV, PDF or PNG and click Download Comparison. PNG contains the table only. Experiments runs paired trials and keeps their summaries for the current browser session."
            ),
        ],
    )
    write(
        "3.Similar applications in the market",
        "Related tools",
        [
            p(
                "These are public research tools used to study sensor locations or networks. They answer different questions about a deployment."
            ),
            table(
                [
                    ["Tool", "Purpose and overlap", "Difference in scope"],
                    [
                        "Cooja",
                        "Simulates sensor networks. MSPSim can emulate an MSP430 sensor platform.",
                        "Cooja studies platform and network behavior. Fieldlab selects sensor sites under coverage and route constraints.",
                    ],
                    [
                        "ns-3",
                        "A discrete-event network simulator. Users can study how modeled network events unfold over time.",
                        "Our links are static range and visibility tests. We omit packet queues, timing and medium access.",
                    ],
                    [
                        "PySensors",
                        "Selects a sparse set of measurement sites. Both tools seek useful readings with fewer sensors.",
                        "PySensors uses data patterns for reconstruction or classification. Fieldlab checks grid coverage and radio paths.",
                    ],
                ],
                [81, 192, 217],
            ),
            h("Example choice"),
            p(
                "To ask whether a wall leaves a cell uncovered, use a placement model. To ask how much packet delay a working layout produces, use a network simulation with a traffic model."
            ),
            h("Checked sources"),
            p(
                '<link href="https://github.com/contiki-ng/cooja" color="#17674e"><u>Cooja official project and README</u></link>'
            ),
            p(
                '<link href="https://github.com/nsnam/ns-3-dev-git" color="#17674e"><u>ns-3 official GitHub mirror and project overview</u></link>'
            ),
            p(
                f'<link href="https://raw.githubusercontent.com/openjournals/joss-papers/{REVISION}/joss.02828/10.21105.joss.02828.pdf" color="#17674e"><u>PySensors publication in the journal archive</u></link>'
            ),
        ],
    )
    scenarios = []
    for path in sorted((ROOT / "Dataset/scenarios").glob("*.json")):
        env = json.loads(path.read_text())
        blocked = sum(r["w"] * r["h"] for r in env["obstacles"])
        scenarios.append(
            [
                path.stem,
                env["size"],
                len(env["obstacles"]),
                blocked,
                f"{100 * blocked / env['size'] ** 2:.2f}%",
            ]
        )
    write(
        "5.The Dataset employed",
        "Synthetic simulation dataset",
        [
            p(
                "The five JSON files describe generated environments. They support controlled tests without collecting field readings. Each file can be loaded in the studio."
            ),
            table(
                [
                    [
                        "Filename stem",
                        "Grid side",
                        "Obstacles",
                        "Blocked cells",
                        "Blocked area",
                    ]
                ]
                + scenarios,
                [107, 77, 96, 105, 105],
            ),
            h("Coordinate rules"),
            p(
                "Rows grow down from zero. Columns grow right. A monitoring point sits at each free cell center. Sites are free points whose two coordinates are multiples of the spacing. The base is excluded from candidate sites. The scenario files use spacing 2, sensing radius 5.5 and radio radius 8."
            ),
            h("Generation"),
            p(
                "The generator draws rectangle sizes and positions from a local random generator. It checks overlap, base clearance, area, count and boundaries. It reserves space in the area budget for later blocks and keeps a free exit beside the base. The generation seed is 42 in all five files."
            ),
            h("Validation and replay"),
            p(
                "From the repository root run python -m Dataset.generate_dataset. The scenario name selects the size and count. The saved JSON gives exact geometry. The search uses a separate seed. The initial graph tests whether connected sites can cover all required points."
            ),
            h("Limits of the data"),
            p(
                "The files describe flat terrain and ideal radios. A square cell has no measured physical scale. Obstacle shape and area vary between recipes. No public field measurements were used."
            ),
        ],
    )
    write(
        "6.Details of the algorithms",
        "The two search methods",
        [
            h("Representation and feasible start"),
            p(
                "A chromosome is a set of unique site indices. Each index maps to one legal coordinate. Breadth-first search (BFS) from the base marks sites that could relay data. Greedy seeding adds a site that sees the most missing points, then adds its parent path. If even the union of reachable sites misses a point, the full model cannot meet both goals. Copies with random changes form the rest of the population."
            ),
            h("One fitness rule"),
            p(
                "Let K count candidate sites, H count holes, D count disconnected sensors and N count active sensors. Cost = (H + 5D)(K + 1) + N. Lower is better. A feasible cost is at most K. One violation costs at least K + 1. Within the feasible group the smaller deployment wins."
            ),
            h("Genetic operators"),
            p(
                "Draw three population members and take the lowest cost. With probability 0.85, draw a second parent and split the grid by a random row or column. Copy opposite sides from the parents. With probability 0.80 mutate the child. Add, remove and move are equally likely. Sites stay unique. Preserve the two best parents each generation."
            ),
            h("Search cost"),
            p(
                "With K sites there are up to 2 to the power K subsets. Let P count free points and B count blocks. Geometry setup tests distances for each site against P points and K radios. Worst-case work grows as O((K P + K squared)(B + 1)). Cached masks can use O(K P) bits. Radio neighbor sets can have O(K squared) entries."
            ),
            p(
                "For N active sites, coverage combines N masks of P bits. BFS visits reachable sensors and tests neighbor sets. In the dense worst case that step takes O(N K). A repeated deployment reuses its score. A local round tries at most eight neighbors. The budget counts distinct computed scores. Geometry setup, seeding and the final audit add wall time outside this count."
            ),
            h("Independent check"),
            p(
                "A second module checks paths using a separating-axis test, then follows links with a depth-first walk. It checks the reported coordinates, counts, holes, reachability and percentages. Full grid coverage means all defined points were covered. Fine sampling is an extra check."
            ),
            PageBreak(),
            h("Genetic algorithm"),
            flow(False),
            p(
                "Stop at the last generation, at the score budget, or when the candidate model is proved infeasible. Record the best cost after each generation, including the final partial generation."
            ),
            PageBreak(),
            h("Memetic algorithm"),
            flow(True),
            p(
                "MA uses the same parents, crossover, mutation and elites. By default 45% of children enter local search. Find whole disconnected groups. For each group, find the closest pair across the gap to the base component. For holes, choose up to three missing cells and their nearest active sensors."
            ),
            p(
                "Try legal sites one candidate step away, including diagonals. Try sites toward the target first. Score the whole changed deployment and keep only a strict improvement. For a feasible child, try deleting a spare node. Limit the search to two rounds and the remaining budget."
            ),
            PageBreak(),
            h("Paired experiment results"),
            p(
                "Each row covers ten trials on one fixed terrain. Seeds 100 to 109 were shared within each GA and MA pair. Population was 12 and the cap was 100 scores. The clock includes terrain setup and the independent audit. SD is the sample standard deviation of feasible counts."
            ),
            results_table(DATA["summary"]),
            h("Convergence on scale40, seed 100"),
            convergence(DATA["records"]),
            p(
                "The seed already gives a feasible layout here. Each drop removes sensors while keeping both constraints. MA had a lower mean count on scale20. GA had a lower mean on the four other recipes. MA spent part of its budget scoring local moves. These five terrains and short budgets limit how far the result can be generalized."
            ),
        ],
    )
    write(
        "7.Development platform",
        "Development platform",
        [
            p(
                "Python 3.12 runs every search and every final check. A separate browser interface lets a student edit a map and watch progress while Python works."
            ),
            h("System architecture"),
            architecture(),
            p(
                "Arrows show calls or requests for data. The browser polls a job. FastAPI starts a separate worker process. Comparison runs each method from the same input. The validator rebuilds the answer from the returned positions."
            ),
            table(
                [
                    ["Location", "Role"],
                    [
                        "backend/app",
                        "Pydantic checks inputs. NumPy builds visibility masks. Python sets and queues represent the network.",
                    ],
                    [
                        "frontend/src",
                        "React and TypeScript manage controls. Canvas draws a scaled terrain. Recharts draws convergence. Vite serves the app.",
                    ],
                    [
                        "backend/tests and scripts",
                        "pytest checks the model, algorithms and API. Playwright exercises the browser. ReportLab draws the course PDFs.",
                    ],
                    [
                        "Dataset and Assessment",
                        "Scenario files define inputs. Trial records and test output support the assessment.",
                    ],
                    [
                        "outputs",
                        "One requested comparison export. CSV uses the standard library. ReportLab writes PDF and Pillow draws PNG.",
                    ],
                ],
                [135, 355],
            ),
            h("Start locally"),
            p(
                "Install Python 3.12 and Node.js 22 or newer. Follow the Windows commands in README.md or open run.bat. Start FastAPI on port 8000 and Vite on port 5173. The browser sends requests through Vite. Development checks were executed on Linux with Chromium."
            ),
        ],
    )
    write_reviews(DOC / "Literature Review")


if __name__ == "__main__":
    main()
