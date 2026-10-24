"""Reproduce the main comparison, equal-budget check, and MA ablation."""

import argparse
import csv
import json
import platform
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from wsn.algorithms import Settings, greedy_layout, optimise
from wsn.model import Problem, Terrain
from wsn.plotting import draw_comparison, draw_history, draw_result
from wsn.verify import verify_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='results/reference')
    parser.add_argument('--seeds', nargs='+', type=int, default=[11, 22, 33, 44, 55])
    parser.add_argument('--generations', type=int, default=70)
    parser.add_argument('--population', type=int, default=36)
    parser.add_argument('--budget', type=int, default=3000)
    args = parser.parse_args()
    if len(set(args.seeds)) != len(args.seeds):
        parser.error('Seeds must be distinct')
    out = Path(args.output)
    if out.exists() and any(out.iterdir()):
        parser.error('Output directory is not empty; choose a new path to preserve earlier evidence')
    out.mkdir(parents=True, exist_ok=True)
    settings = Settings(population=args.population, generations=args.generations)
    rows, saved = [], []
    started = time.perf_counter()

    def record(problem, result, suite):
        verify_result(result)
        result['suite'] = suite
        file = f"{suite}-{problem.terrain.name}-{result['algorithm']}-{result['seed']}.json"
        (out / file).write_text(json.dumps(result, indent=2) + '\n')
        rows.append({'suite': suite, 'terrain': problem.terrain.name,
                     'algorithm': result['algorithm'], 'seed': result['seed'],
                     **result['metrics'], 'evaluations': result['evaluations'],
                     'runtime_seconds': result['runtime_seconds'], 'result_file': file})
        saved.append(result)
        print(f"{suite:12s} {problem.terrain.name:12s} {result['algorithm']:6s} seed={result['seed']:2d} "
              f"nodes={result['metrics']['sensors']:2d} feasible={result['metrics']['feasible']} "
              f"evals={result['evaluations']}", flush=True)

    for name in ('open_field', 'two_walls', 'courtyard'):
        problem = Problem(Terrain.load(ROOT / f'data/{name}.json'))
        tick = time.perf_counter()
        before = problem.evaluations
        initial = greedy_layout(problem)
        greedy_seconds = time.perf_counter() - tick
        greedy_evals = problem.evaluations - before
        for seed in args.seeds:
            for method in ('greedy', 'random'):
                tick = time.perf_counter()
                genes = initial if method == 'greedy' else tuple(sorted(np.random.default_rng(seed).choice(problem.size, len(initial), replace=False).tolist()))
                metrics = problem.evaluate(genes)
                result = {'algorithm': method, 'seed': seed, 'terrain': problem.terrain.to_dict(),
                          'settings': {}, 'coordinates': problem.coordinates(genes),
                          'location_ids': list(genes), 'metrics': metrics.to_dict(), 'history': [],
                          'evaluations': greedy_evals if method == 'greedy' else 1,
                          'runtime_seconds': greedy_seconds if method == 'greedy' else time.perf_counter()-tick}
                record(problem, result, 'main')
            for method in ('ga', 'ma'):
                record(problem, optimise(problem, method, seed, settings, initial), 'main')
        # Plot a paired, predeclared seed rather than silently choosing the best run.
        pair = [r for r in saved if r['suite'] == 'main' and r['terrain']['name'] == name
                and r['seed'] == args.seeds[0] and r['algorithm'] in ('ga', 'ma')]
        for result in pair:
            draw_result(result, out / f"layout-{name}-{result['algorithm']}.png")
        draw_history(pair, out / f'progress-{name}.png')
        # Equal unique-evaluation budget: enough generations to hit the budget.
        if name == 'two_walls':
            budgeted = replace(settings, generations=10000, evaluation_budget=args.budget)
            for seed in args.seeds:
                for method in ('ga', 'ma'):
                    result = optimise(problem, method, seed, budgeted, initial)
                    if result['evaluations'] != args.budget:
                        raise RuntimeError('Equal-budget experiment did not use its full budget')
                    record(problem, result, 'equal_budget')
                # No local search uses the same RNG calls as GA: an identity check.
                ablated = replace(settings, local_elites=0)
                record(problem, optimise(problem, 'ma', seed, ablated, initial), 'no_local')

    with (out / 'runs.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for suite, terrain, algorithm in sorted({(r['suite'], r['terrain'], r['algorithm']) for r in rows}):
        group = [r for r in rows if (r['suite'], r['terrain'], r['algorithm']) == (suite, terrain, algorithm)]
        feasible = [r['sensors'] for r in group if r['feasible']]
        entry = {'suite': suite, 'terrain': terrain, 'algorithm': algorithm, 'runs': len(group),
                 'feasible_runs': len(feasible), 'success_rate': len(feasible)/len(group),
                 'mean_sensors_feasible': statistics.mean(feasible) if feasible else None,
                 'sd_sensors_feasible': statistics.stdev(feasible) if len(feasible)>1 else (0 if feasible else None),
                 'best_sensors_feasible': min(feasible) if feasible else None,
                 'mean_coverage': statistics.mean(r['coverage'] for r in group),
                 'mean_connectivity': statistics.mean(r['connectivity'] for r in group),
                 'mean_evaluations': statistics.mean(r['evaluations'] for r in group),
                 'mean_runtime_seconds': statistics.mean(r['runtime_seconds'] for r in group)}
        summary.append(entry)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    with (out / 'summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    import matplotlib
    metadata = {'python': platform.python_version(), 'numpy': np.__version__,
                'matplotlib': matplotlib.__version__, 'platform': platform.platform(),
                'seeds': args.seeds, 'settings': vars(args),
                'total_seconds': time.perf_counter()-started,
                'note': 'All exported layouts were checked using the independent scalar verifier.'}
    (out / 'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    draw_comparison(rows, out / 'comparison.png')
    lines = ['# Experiment results', '', 'Generated from the checked run files in this directory.', '',
             '| Suite | Terrain | Method | Success | Mean sensors ± sample SD (feasible) | Mean evaluations | Mean seconds |',
             '|---|---|---|---|---|---|---|']
    for r in summary:
        nodes = '—' if r['mean_sensors_feasible'] is None else f"{r['mean_sensors_feasible']:.2f} ± {r['sd_sensors_feasible']:.2f}"
        lines.append(f"| {r['suite']} | {r['terrain']} | {r['algorithm'].upper()} | {r['feasible_runs']}/{r['runs']} | {nodes} | {r['mean_evaluations']:.0f} | {r['mean_runtime_seconds']:.3f} |")
    (out / 'RESULTS.md').write_text('\n'.join(lines)+'\n')
    print(f'Finished {len(rows)} independently checked runs in {metadata["total_seconds"]:.1f}s', flush=True)


if __name__ == '__main__':
    main()
