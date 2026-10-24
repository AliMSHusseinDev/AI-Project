"""A local demonstration UI using Python's standard HTTP server."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .algorithms import Settings, optimise
from .model import Problem, Terrain
from .verify import verify_result

ROOT = Path(__file__).resolve().parents[1]
TERRAINS = ('open_field', 'two_walls', 'courtyard')
RUN_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, content, mime='application/json'):
        body = content.encode()
        self.send_response(status)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/':
            self.reply(200, (ROOT / 'web/index.html').read_text(), 'text/html')
        elif self.path == '/api/health':
            self.reply(200, json.dumps({'status': 'ok', 'terrains': list(TERRAINS)}))
        else:
            self.reply(404, json.dumps({'error': 'Page not found'}))

    def do_POST(self):
        if self.path != '/api/solve':
            self.reply(404, json.dumps({'error': 'Page not found'}))
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8192:
                raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Request must be a JSON object')
            terrain = data.get('terrain', 'two_walls')
            algorithm = data.get('algorithm', 'ma')
            if terrain not in TERRAINS or algorithm not in ('ga', 'ma'):
                raise ValueError('Choose one of the listed terrains and algorithms')
            generations, seed = data.get('generations', 50), data.get('seed', 42)
            if type(generations) is not int or not 1 <= generations <= 150:
                raise ValueError('Generations must be an integer from 1 to 150')
            if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
                raise ValueError('Seed must be an integer from 0 to 4294967295')
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.reply(400, json.dumps({'error': str(exc)}))
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.reply(409, json.dumps({'error': 'A run is already in progress. Please wait.'}))
            return
        try:
            problem = Problem(Terrain.load(ROOT / f'data/{terrain}.json'))
            result = optimise(problem, algorithm, seed, Settings(generations=generations))
            verify_result(result)
            self.reply(200, json.dumps(result))
        except ValueError as exc:
            self.reply(400, json.dumps({'error': str(exc)}))
        finally:
            RUN_LOCK.release()


def serve(host='127.0.0.1', port=8000):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f'Sensor placement demo is listening on {host}, port {server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
