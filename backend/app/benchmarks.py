"""Paired trials with fixed geometry, common seeds and the same evaluation cap."""

import argparse
import csv
import json
from pathlib import Path
from statistics import mean, stdev
from .environment import Environment, generate
from .evolution import Settings, optimize

CASES = {
    "scale20": (20, 1),
    "scale40": (40, 4),
    "scale60": (60, 9),
    "clear40": (40, 0),
    "dense40": (40, 10),
}


def scenario(name):
    size, count = CASES[name]
    return generate(Environment(size=size, base=(size // 2, size // 2), seed=42), count)


def benchmark(trials=10, progress=lambda *args: None):
    records = []
    for name in CASES:
        env = scenario(name)
        for seed in range(100, 100 + trials):
            settings = Settings(seed=seed, population=12, budget=100, generations=150)
            for algorithm in ("GA", "MA"):

                def update(generation, evaluations, cost):
                    progress(
                        len(records),
                        len(CASES) * trials * 2,
                        f"{name} · {algorithm} · seed {seed} · {evaluations} evaluations",
                    )

                result = optimize(env, settings, algorithm, update)
                record = {
                    key: result[key]
                    for key in (
                        "algorithm",
                        "seed",
                        "count",
                        "feasible",
                        "coverage",
                        "connectivity",
                        "seconds",
                        "evaluations",
                        "generations",
                        "initial_count",
                        "cost",
                        "history",
                        "local",
                        "positions",
                    )
                }
                record.update(
                    case=name,
                    environment_id=env.identifier(),
                    environment_seed=env.seed,
                    size=env.size,
                    obstacles=len(env.obstacles),
                    blocked_cells=sum(r.w * r.h for r in env.obstacles),
                    passed=result["audit"]["passed"],
                    disconnected=len(result["unreachable"]),
                    settings=settings.model_dump(),
                )
                records.append(record)
    summary = []
    for name in CASES:
        for algorithm in ("GA", "MA"):
            group = [
                r for r in records if (r["case"], r["algorithm"]) == (name, algorithm)
            ]
            valid = [r["count"] for r in group if r["passed"]]
            summary.append(
                dict(
                    case=name,
                    algorithm=algorithm,
                    runs=len(group),
                    valid=len(valid),
                    best=min(valid) if valid else None,
                    mean=mean(valid) if valid else None,
                    sd=stdev(valid) if len(valid) > 1 else None,
                    seconds=mean(r["seconds"] for r in group),
                    evaluations=mean(r["evaluations"] for r in group),
                    coverage=mean(r["coverage"] for r in group),
                    connectivity=mean(r["connectivity"] for r in group),
                )
            )
    return dict(records=records, summary=summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, choices=range(1, 11), default=10)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = benchmark(args.trials)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "trials.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf8"
    )
    with (args.out / "summary.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.DictWriter(stream, fieldnames=data["summary"][0])
        writer.writeheader()
        writer.writerows(data["summary"])
