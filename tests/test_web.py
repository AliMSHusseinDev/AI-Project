import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from wsn.verify import verify_result
from wsn.web import Handler, RUN_LOCK


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.root = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def post(self, data):
        request = urllib.request.Request(self.root + '/api/solve',
                                        data=json.dumps(data).encode(),
                                        headers={'Content-Type': 'application/json'})
        return urllib.request.urlopen(request, timeout=20)

    def test_home_page_and_health(self):
        with urllib.request.urlopen(self.root) as response:
            self.assertIn('Sensor Placement Lab', response.read().decode())
        with urllib.request.urlopen(self.root + '/api/health') as response:
            self.assertEqual(json.load(response)['status'], 'ok')

    def test_functional_solve(self):
        with self.post({'terrain': 'two_walls', 'algorithm': 'ma', 'seed': 42, 'generations': 5}) as response:
            result = json.load(response)
        self.assertTrue(verify_result(result)['feasible'])

    def test_bad_requests_are_rejected(self):
        for data in [[], {'terrain': '../private'}, {'generations': 0},
                     {'seed': -1}, {'seed': 1.2}, {'generations': True}, {'algorithm': 'unknown'}]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.post(data)
            self.assertEqual(error.exception.code, 400)

    def test_unknown_page_is_not_exposed(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.root + '/requirements.txt')
        self.assertEqual(error.exception.code, 404)

    def test_busy_server_returns_clear_error(self):
        RUN_LOCK.acquire()
        try:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.post({})
            self.assertEqual(error.exception.code, 409)
        finally:
            RUN_LOCK.release()


if __name__ == '__main__':
    unittest.main()
