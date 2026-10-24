import itertools
import unittest

import numpy as np

from wsn.algorithms import Settings, crossover, greedy_layout, local_search, mutate, optimise
from wsn.model import Problem, Terrain
from wsn.verify import verify_result


class AlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.problem = Problem(Terrain('test', 9, 7, (0, 0), 2.5, 4))
        self.settings = Settings(population=12, generations=10, max_sensors=20)

    def test_greedy_returns_feasible_layout(self):
        genes = greedy_layout(self.problem)
        self.assertTrue(self.problem.evaluate(genes).feasible)

    def test_ga_and_ma_return_independently_valid_results(self):
        for method in ('ga', 'ma'):
            result = optimise(self.problem, method, 7, self.settings)
            self.assertTrue(verify_result(result)['feasible'])

    def test_same_seed_reproduces_coordinates_and_history(self):
        a = optimise(self.problem, 'ma', 42, self.settings)
        b = optimise(self.problem, 'ma', 42, self.settings)
        self.assertEqual(a['coordinates'], b['coordinates'])
        self.assertEqual(a['history'], b['history'])

    def test_zero_local_search_is_identical_to_ga(self):
        settings = Settings(population=12, generations=10, max_sensors=20, local_elites=0)
        a = optimise(self.problem, 'ga', 10, settings)
        b = optimise(self.problem, 'ma', 10, settings)
        self.assertEqual(a['coordinates'], b['coordinates'])
        self.assertEqual(a['history'], b['history'])

    def test_best_fitness_never_decreases(self):
        r = optimise(self.problem, 'ma', 3, self.settings)
        fitness = [step['fitness'] for step in r['history']]
        self.assertEqual(fitness, sorted(fitness))

    def test_genetic_operators_keep_valid_unique_locations(self):
        rng = np.random.default_rng(42)
        genes = greedy_layout(self.problem)
        for _ in range(100):
            child = mutate(genes, self.problem, self.settings, rng)
            self.problem.validate_genes(child)
            genes = crossover(genes, child, self.settings.max_sensors, rng)
            self.problem.validate_genes(genes)
            self.assertLessEqual(len(genes), self.settings.max_sensors)

    def test_local_search_repairs_a_coverage_hole(self):
        p = Problem(Terrain('line', 5, 1, (0, 0), 2, 10))
        genes = (0,)
        repaired = local_search(p, genes, self.settings, np.random.default_rng(1), p.evaluate)
        self.assertTrue(p.evaluate(repaired).feasible)
        self.assertNotEqual(genes, repaired)

    def test_local_search_repairs_an_isolated_sensor(self):
        p = Problem(Terrain('line', 6, 1, (0, 0), 10, 2))
        repaired = local_search(p, (4,), self.settings, np.random.default_rng(1), p.evaluate)
        self.assertEqual(p.evaluate(repaired).connected, 1)

    def test_local_search_removes_a_redundant_sensor(self):
        p = Problem(Terrain('tiny', 3, 1, (0, 0), 3, 3))
        repaired = local_search(p, (0, 1, 2), self.settings, np.random.default_rng(1), p.evaluate)
        self.assertLess(len(repaired), 3)
        self.assertTrue(p.evaluate(repaired).feasible)

    def test_exact_tiny_optimum_matches_search(self):
        p = Problem(Terrain('tiny', 3, 2, (0, 0), 3, 4))
        optimum = next(n for n in range(p.size+1)
                       if any(p.evaluate(genes).feasible for genes in itertools.combinations(range(p.size), n)))
        result = optimise(p, 'ma', 42, self.settings)
        self.assertEqual(result['metrics']['sensors'], optimum)
        self.assertEqual(optimum, 1)

    def test_impossible_connected_coverage_is_reported(self):
        p = Problem(Terrain('split', 7, 3, (0, 0), 1, 1, ((3, 0, 3, 2),)))
        with self.assertRaisesRegex(ValueError, 'No connected deployment'):
            greedy_layout(p)

    def test_unreachable_candidate_is_ok_if_reachable_nodes_cover_it(self):
        p = Problem(Terrain('small', 3, 1, (0, 0), 3, .5))
        self.assertTrue(p.evaluate(greedy_layout(p)).feasible)

    def test_budget_is_respected(self):
        settings = Settings(population=12, generations=500, max_sensors=20, evaluation_budget=80)
        result = optimise(self.problem, 'ma', 1, settings)
        self.assertEqual(result['evaluations'], 80)
        self.assertEqual(result['stop_reason'], 'evaluation_budget')
        self.assertTrue(verify_result(result)['feasible'])

    def test_too_small_sensor_limit_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'below greedy seed'):
            optimise(self.problem, 'ga', 1, Settings(max_sensors=1))

    def test_settings_reject_bad_rates_and_sizes(self):
        for kwargs in [{'population': 2}, {'mutation_rate': 2}, {'elite': 36},
                       {'generations': -1}, {'evaluation_budget': 1}, {'move_radius': 0}]:
            with self.assertRaises(ValueError):
                Settings(**kwargs)


if __name__ == '__main__':
    unittest.main()
