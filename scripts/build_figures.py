"""Build editable SVG and printable PNG design diagrams."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wsn.plotting import plt
from matplotlib.patches import FancyBboxPatch


def box(ax, y, text, x=.5, width=.75, height=.105):
    ax.add_patch(FancyBboxPatch((x-width/2, y-height/2), width, height,
                               boxstyle='round,pad=0.012', linewidth=1.3,
                               edgecolor='#23877b', facecolor='#edf7f4'))
    ax.text(x, y, text, ha='center', va='center', fontsize=10.5, color='#173c4d')


def arrow(ax, a, b):
    ax.annotate('', xy=b, xytext=a, arrowprops={'arrowstyle': '->', 'lw': 1.5, 'color': '#466a78'})


def vertical(name, title, labels):
    fig, ax = plt.subplots(figsize=(7, 6.5))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    ys = [.88 - i * .15 for i in range(len(labels))]
    for y, text in zip(ys, labels):
        box(ax, y, text)
    for a, b in zip(ys, ys[1:]):
        arrow(ax, (.5, a-.063), (.5, b+.063))
    ax.set_title(title, fontsize=15, color='#173c4d', pad=12)
    fig.tight_layout()
    for suffix in ('svg', 'png'):
        fig.savefig(ROOT / f'docs/figures/{name}.{suffix}', dpi=160, bbox_inches='tight')
    plt.close(fig)


def main():
    (ROOT / 'docs/figures').mkdir(parents=True, exist_ok=True)
    vertical('system', 'System data flow', [
        'Terrain JSON + seed + search settings',
        'Validate terrain; prepare distances and visibility',
        'Run the shared GA core or MA with local search',
        'Verify exported coordinates independently',
        'JSON results + browser map + plots + report'])
    vertical('ma', 'MA local phase: before the next generation', [
        'Rank offspring; choose up to four layouts',
        'Find coverage holes and disconnected sensors',
        'Try short moves; test deletion if feasible',
        'Evaluate the complete candidate network',
        'Keep strict improvement; repeat up to two steps',
        'Continue the next evolutionary cycle'])
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis('off')
    labels = ['Greedy seed + shared initial population', 'Evaluate and rank layouts',
              'Generation / evaluation limit reached?', 'Keep elites; tournament selection',
              'Set crossover; add / delete / move mutation', 'Evaluate offspring; replace population']
    ys = [.91, .75, .59, .43, .27, .11]
    for y, text in zip(ys, labels):
        box(ax, y, text, x=.43, width=.67, height=.09)
    for a, b in zip(ys, ys[1:]):
        arrow(ax, (.43, a-.055), (.43, b+.055))
    ax.text(.46, .505, 'No', fontsize=9)
    ax.annotate('', xy=(.085, .75), xytext=(.43, .055),
                arrowprops={'arrowstyle': '->', 'color': '#466a78', 'lw': 1.3,
                            'connectionstyle': 'angle,angleA=180,angleB=-90,rad=12'})
    box(ax, .59, 'Return\nbest layout', x=.9, width=.15, height=.13)
    arrow(ax, (.78, .59), (.81, .59))
    ax.text(.79, .66, 'Yes', fontsize=9)
    ax.set_title('Genetic Algorithm flow', fontsize=15, color='#173c4d')
    fig.tight_layout()
    for suffix in ('svg', 'png'):
        fig.savefig(ROOT / f'docs/figures/ga.{suffix}', dpi=160, bbox_inches='tight')
    plt.close(fig)
    print('Built system, GA, and MA diagrams as SVG and PNG.')


if __name__ == '__main__':
    main()
