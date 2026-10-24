"""Plots saved on disk; works on a server without a desktop."""

import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/wsn-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
import numpy as np

from .model import Problem, Terrain


def draw_result(result, path):
    data = result['terrain'].copy()
    data['base'] = tuple(data['base'])
    data['obstacles'] = tuple(tuple(r) for r in data['obstacles'])
    problem = Problem(Terrain(**data))
    genes = tuple(problem.lookup[tuple(p)] for p in result['coordinates'])
    covered, reachable, edges = problem.state(genes)
    fig, ax = plt.subplots(figsize=(9, 7))
    pts = problem.points
    ax.scatter(pts[covered, 0], pts[covered, 1], c='#b8dfce', s=12, label='Covered target')
    ax.scatter(pts[~covered, 0], pts[~covered, 1], c='#cf3948', marker='x', s=22, label='Coverage hole')
    for x0, y0, x1, y1 in problem.terrain.obstacles:
        ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, color='#404650', alpha=.9))
    coords = problem.points[list(genes)]
    for i, (x, y) in enumerate(coords):
        ax.add_patch(Circle((x, y), problem.terrain.sensing_range, color='#2482aa', alpha=.045))
        if problem.base_links[genes[i]]:
            ax.plot([x, problem.terrain.base[0]], [y, problem.terrain.base[1]], color='#529787', lw=.9)
        for j in range(i):
            if edges[i, j]:
                ax.plot([x, coords[j, 0]], [y, coords[j, 1]], color='#529787', lw=.9, alpha=.65)
    if len(coords):
        ax.scatter(coords[reachable, 0], coords[reachable, 1], color='#176d9c', s=52, label='Connected sensor')
        ax.scatter(coords[~reachable, 0], coords[~reachable, 1], color='#e58024', s=52, label='Disconnected sensor')
    ax.scatter(*problem.terrain.base, color='#f6b331', edgecolor='black', marker='*', s=220, label='Base station', zorder=5)
    m = result['metrics']
    ax.set(title=f"{result['algorithm'].upper()} | {problem.terrain.name} | {m['sensors']} sensors\n"
                 f"Coverage {m['coverage']:.1%} | Connected {m['connectivity']:.1%}",
           xlabel='x (grid units)', ylabel='y (grid units)',
           xlim=(-1, problem.terrain.width), ylim=(-1, problem.terrain.height))
    ax.set_aspect('equal')
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=8)
    ax.text(0, -.13, 'Circles show range only. The green targets include obstacle blocking.', transform=ax.transAxes, fontsize=8)
    fig.tight_layout()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches='tight')
    plt.close(fig)


def draw_history(results, path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for result in results:
        h = result['history']
        ax.step([x['evaluations'] for x in h], [x['sensors'] for x in h], where='post',
                label=f"{result['algorithm'].upper()} (seed {result['seed']})")
    ax.set(xlabel='Unique fitness evaluations', ylabel='Best feasible sensor count', title='Search progress')
    ax.legend()
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_comparison(rows, path):
    names = sorted({r['terrain'] for r in rows if r['suite'] == 'main'})
    methods = ['random', 'greedy', 'ga', 'ma']
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    width = .19
    x = np.arange(len(names))
    for j, method in enumerate(methods):
        values = [[r for r in rows if r['suite'] == 'main' and r['terrain'] == n and r['algorithm'] == method] for n in names]
        feasible = [[r['sensors'] for r in group if r['feasible']] for group in values]
        means = [np.mean(v) if v else np.nan for v in feasible]
        std = [np.std(v, ddof=1) if len(v) > 1 else 0 for v in feasible]
        axes[0].bar(x+(j-1.5)*width, means, width, yerr=std, label=method.upper(), capsize=2)
        axes[1].bar(x+(j-1.5)*width, [np.mean([r['feasible'] for r in g])*100 for g in values], width, label=method.upper())
    axes[0].set(title='Sensor count on feasible runs only', ylabel='Mean sensors (error bar = sample SD)')
    axes[1].set(title='Success rate', ylabel='Feasible runs (%)', ylim=(0, 105))
    for ax in axes:
        ax.set_xticks(x, names)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
