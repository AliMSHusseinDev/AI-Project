"""Command line entry points. Run python -m wsn --help."""

import argparse
import json
from pathlib import Path

from .algorithms import Settings, optimise
from .model import Problem, Terrain
from .verify import verify_result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Wireless sensor placement using GA and MA')
    sub = parser.add_subparsers(dest='command', required=True)
    solve = sub.add_parser('solve', help='Optimise one terrain and save a checked layout')
    solve.add_argument('--terrain', default='data/two_walls.json')
    solve.add_argument('--algorithm', choices=['ga', 'ma'], default='ma')
    solve.add_argument('--seed', type=int, default=42)
    solve.add_argument('--population', type=int, default=36)
    solve.add_argument('--generations', type=int, default=70)
    solve.add_argument('--max-sensors', type=int, default=70)
    solve.add_argument('--evaluation-budget', type=int)
    solve.add_argument('--output', default='results/local/solution.json')
    solve.add_argument('--plot', help='Optional PNG output path')
    verify = sub.add_parser('verify', help='Recheck saved coordinates without cached geometry')
    verify.add_argument('result')
    serve = sub.add_parser('serve', help='Open the simple local demonstration app')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        if args.command == 'verify':
            print(json.dumps(verify_result(json.loads(Path(args.result).read_text())), indent=2))
        elif args.command == 'serve':
            from .web import serve as start_server
            start_server(args.host, args.port)
        else:
            settings = Settings(population=args.population, generations=args.generations,
                                max_sensors=args.max_sensors, evaluation_budget=args.evaluation_budget)
            result = optimise(Problem(Terrain.load(args.terrain)), args.algorithm, args.seed, settings)
            verify_result(result)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2) + '\n')
            if args.plot:
                from .plotting import draw_result
                draw_result(result, args.plot)
            print(json.dumps({**result['metrics'], 'evaluations': result['evaluations'],
                              'runtime_seconds': result['runtime_seconds'], 'output': str(output)}, indent=2))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
