"""Check the committed experiment evidence and reproduce a declared run pair."""

import csv
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wsn.algorithms import Settings, optimise
from wsn.model import Problem, Terrain
from wsn.verify import verify_result


def main():
    base = ROOT / 'results/reference'
    with (base / 'runs.csv').open() as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 75:
        raise ValueError(f'Expected 75 reference records, found {len(rows)}')
    runs = {}
    for row in rows:
        result = json.loads((base / row['result_file']).read_text())
        metrics = verify_result(result)
        for key in ('sensors', 'covered', 'total', 'connected', 'components'):
            if int(row[key]) != metrics[key]:
                raise ValueError(f'CSV mismatch in {row["result_file"]}: {key}')
        for key in ('coverage', 'connectivity'):
            if not math.isclose(float(row[key]), metrics[key]):
                raise ValueError(f'CSV mismatch in {row["result_file"]}: {key}')
        if (row['feasible'] == 'True') != metrics['feasible']:
            raise ValueError('CSV feasibility mismatch')
        identity = (row['suite'], row['terrain'], row['algorithm'], int(row['seed']))
        if identity in runs:
            raise ValueError('Duplicate experiment identity')
        runs[identity] = result
    for entry in json.loads((base / 'summary.json').read_text()):
        group = [r for key, r in runs.items() if key[:3] == (entry['suite'], entry['terrain'], entry['algorithm'])]
        values = [r['metrics']['sensors'] for r in group if r['metrics']['feasible']]
        expected = statistics.mean(values) if values else None
        if entry['runs'] != len(group) or entry['feasible_runs'] != len(values) or entry['mean_sensors_feasible'] != expected:
            raise ValueError('Summary does not match the individual runs')
    for seed in (11, 22, 33, 44, 55):
        ga = runs['main', 'two_walls', 'ga', seed]
        ablated = runs['no_local', 'two_walls', 'ma', seed]
        if ga['coordinates'] != ablated['coordinates'] or ga['history'] != ablated['history']:
            raise ValueError('No-local MA does not match the paired GA run')
        for method in ('ga', 'ma'):
            if runs['equal_budget', 'two_walls', method, seed]['evaluations'] != 3000:
                raise ValueError('Budget comparison does not use equal evaluations')
    problem = Problem(Terrain.load(ROOT / 'data/two_walls.json'))
    for method in ('ga', 'ma'):
        saved = runs['main', 'two_walls', method, 11]
        repeated = optimise(problem, method, 11, Settings(**saved['settings']))
        if repeated['coordinates'] != saved['coordinates'] or repeated['history'] != saved['history']:
            raise ValueError(f'{method.upper()} reference run did not reproduce')
    print('Verified 75 layouts, CSV metrics, summary means, five ablation pairs, equal budgets, and a reproduced GA/MA pair.')


if __name__ == '__main__':
    main()
