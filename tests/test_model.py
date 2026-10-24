import itertools
import unittest

import numpy as np

from wsn.model import Evaluation, Problem, Terrain, line_of_sight
from wsn.verify import verify_result


class GeometryTests(unittest.TestCase):
    def test_clear_segment(self):
        self.assertTrue(line_of_sight((0, 0), (6, 0), [(2, 2, 4, 4)]))

    def test_crossing_segment(self):
        self.assertFalse(line_of_sight((0, 3), (6, 3), [(2, 2, 4, 4)]))

    def test_corner_touch_blocks(self):
        self.assertFalse(line_of_sight((0, 4), (4, 0), [(2, 2, 3, 3)]))

    def test_edge_touch_blocks(self):
        self.assertFalse(line_of_sight((0, 2), (6, 2), [(2, 2, 4, 4)]))

    def test_parallel_outside_does_not_block(self):
        self.assertTrue(line_of_sight((1, 0), (1, 6), [(2, 2, 4, 4)]))

    def test_inside_endpoint_blocks(self):
        self.assertFalse(line_of_sight((3, 3), (6, 6), [(2, 2, 4, 4)]))

    def test_zero_length_free_segment(self):
        self.assertTrue(line_of_sight((1, 1), (1, 1), [(2, 2, 4, 4)]))

    def test_vector_geometry_matches_scalar_for_all_pairs(self):
        terrain = Terrain('small', 7, 6, (0, 0), 3, 4, ((2, 1, 3, 3), (4, 4, 5, 4)))
        problem = Problem(terrain)
        for i, a in enumerate(problem.points):
            for j, b in enumerate(problem.points):
                visible = line_of_sight(a, b, terrain.obstacles)
                distance = np.linalg.norm(a-b)
                self.assertEqual(bool(problem.cover[i, j]), visible and distance <= 3+1e-12)
                self.assertEqual(bool(problem.links[i, j]), visible and distance <= 4+1e-12)


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.problem = Problem(Terrain('line', 7, 1, (0, 0), 1, 2))

    def test_relay_path_to_base(self):
        result = self.problem.evaluate((2, 4, 6))
        self.assertEqual(result.connected, 3)
        self.assertEqual(result.components, 1)

    def test_connected_to_sensor_but_not_base(self):
        result = self.problem.evaluate((4, 6))
        self.assertEqual(result.connected, 0)
        self.assertEqual(result.components, 2)

    def test_empty_layout_does_not_cover(self):
        result = self.problem.evaluate(())
        self.assertEqual(result.covered, 0)
        self.assertFalse(result.feasible)

    def test_range_boundary_included(self):
        result = self.problem.evaluate((2,))
        self.assertEqual(result.connected, 1)
        self.assertEqual(result.covered, 3)

    def test_duplicate_sensor_rejected(self):
        with self.assertRaises(ValueError):
            self.problem.evaluate((1, 1))

    def test_invalid_id_rejected(self):
        for genes in [(-1,), (7,), (1.5,)]:
            with self.assertRaises(ValueError):
                self.problem.evaluate(genes)

    def test_obstacle_blocks_communication_and_sensing(self):
        p = Problem(Terrain('wall', 7, 5, (0, 2), 10, 10, ((3, 1, 3, 3),)))
        a, b = p.lookup[(1, 2)], p.lookup[(5, 2)]
        self.assertFalse(p.cover[a, b])
        self.assertFalse(p.links[a, b])
        self.assertEqual(p.evaluate((b,)).connected, 0)

    def test_feasible_always_beats_infeasible(self):
        good = Evaluation(70, 100, 100, 70, 1)
        bad = Evaluation(1, 99, 100, 1, 1)
        self.assertGreater(good.fitness(70), bad.fitness(70))

    def test_independent_verifier_detects_tampering(self):
        genes = (0, 2, 4, 6)
        r = {'terrain': self.problem.terrain.to_dict(),
             'coordinates': self.problem.coordinates(genes),
             'metrics': self.problem.evaluate(genes).to_dict()}
        self.assertTrue(verify_result(r)['feasible'])
        r['metrics']['covered'] = 0
        with self.assertRaises(ValueError):
            verify_result(r)

    def test_invalid_terrain_rejected(self):
        for width, base, sensing, rects in [(0, (0, 0), 1, ()), (3, (9, 0), 1, ()),
                                           (3, (0, 0), 0, ()), (3, (0, 0), 1, ((1, 1, 4, 4),)),
                                           (3, (1, 1), 1, ((1, 1, 2, 2),))]:
            with self.assertRaises(ValueError):
                Terrain('invalid', width, 3, base, sensing, 1, rects)


if __name__ == '__main__':
    unittest.main()
