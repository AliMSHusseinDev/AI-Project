"""Check the delivery, or replay the recorded algorithms without overwriting evidence."""

import argparse
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from statistics import mean, stdev
from backend.app.benchmarks import CASES, scenario
from backend.app.environment import Environment, generate
from backend.app.evolution import Settings, optimize
from backend.app.validation import validate

ROOT = Path(__file__).resolve().parents[1]


def check(replay=False):
    evidence = ROOT / "Assessment/evidence"
    data = json.loads((evidence / "trials.json").read_text())
    records = data["records"]
    assert len(records) == 100 and len(data["summary"]) == 10
    keys = {(r["case"], r["algorithm"], r["seed"]) for r in records}
    assert keys == {
        (name, method, seed)
        for name in CASES
        for method in ("GA", "MA")
        for seed in range(100, 110)
    }
    for name in CASES:
        env = scenario(name)
        assert env.model_dump(mode="json") == json.loads(
            (ROOT / f"Dataset/scenarios/{name}.json").read_text()
        )
        for record in (r for r in records if r["case"] == name):
            assert record["environment_id"] == env.identifier()
            assert record["evaluations"] == record["history"][-1]["evaluations"] == 100
            assert record["cost"] == record["history"][-1]["cost"]
            # The submitted benchmark reports all runs feasible. Rebuild that claim.
            audited = validate(env, record | {"holes": [], "unreachable": []})
            assert audited["passed"] and record["passed"] and record["feasible"]
            if replay:
                result = optimize(
                    env, Settings(**record["settings"]), record["algorithm"]
                )
                for key in (
                    "positions",
                    "history",
                    "count",
                    "coverage",
                    "connectivity",
                    "evaluations",
                    "local",
                ):
                    assert json.loads(json.dumps(result[key])) == record[key], (
                        name,
                        record["seed"],
                        key,
                    )
    gui_runs = json.loads((evidence / "assessment_runs.json").read_text())
    designs = [(20, 0), (20, 2), (40, 0), (40, 8), (60, 18)]
    assert len(gui_runs) == len(designs)
    for entry, (size, count) in zip(gui_runs, designs, strict=True):
        env = generate(
            Environment(size=size, base=(size // 2, size // 2), seed=42), count
        )
        assert entry["environment"] == env.model_dump(mode="json")
        for result, audit in zip(entry["results"], entry["validation"], strict=True):
            assert validate(env, result) == audit == result["audit"]
            assert (
                audit["passed"]
                and result["settings"] == Settings(budget=600).model_dump()
            )
            assert result["evaluations"] <= 600
            if replay:
                replayed = optimize(
                    env, Settings(**result["settings"]), result["algorithm"]
                )
                for key in (
                    "positions",
                    "history",
                    "generations",
                    "evaluations",
                    "termination",
                    "local",
                ):
                    assert json.loads(json.dumps(replayed[key])) == result[key]
    with (evidence / "summary.csv").open() as stream:
        csv_rows = list(csv.DictReader(stream))
    for summary, csv_row in zip(data["summary"], csv_rows, strict=True):
        group = [
            r
            for r in records
            if r["case"] == summary["case"] and r["algorithm"] == summary["algorithm"]
        ]
        counts = [r["count"] for r in group if r["passed"]]
        for key, value in dict(
            mean=mean(counts),
            sd=stdev(counts),
            best=min(counts),
            valid=len(counts),
            seconds=mean(r["seconds"] for r in group),
        ).items():
            assert (
                abs(summary[key] - value) < 1e-9
                and abs(float(csv_row[key]) - value) < 1e-9
            )
    suite = ET.parse(evidence / "tests.xml").find(".//testsuite")
    assert len(suite.findall("testcase")) == int(suite.attrib["tests"]) > 0
    assert all(int(suite.attrib[k]) == 0 for k in ("failures", "skipped", "errors"))
    assert len(json.loads((evidence / "browser.json").read_text())) >= 5
    docs = ROOT / "Documentation"
    assert (
        len(list(docs.glob("*.pdf"))) == 6
        and len(list((docs / "Literature Review").glob("*.pdf"))) == 7
    )
    for path in [
        *docs.rglob("*.pdf"),
        ROOT / "Assessment/Assessment Evidence and Experiments.pdf",
    ]:
        assert path.read_bytes().startswith(b"%PDF"), path
    print(
        f"Verified five GUI comparisons and 50 supplemental pairs, 10 statistical summaries, {suite.attrib['tests']} test records, browser evidence and 14 PDFs."
    )
    if replay:
        print(
            "All 110 seeded searches reproduced their recorded coordinates, metrics, local-search counters and histories."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true")
    check(parser.parse_args().replay)
