"""Start Vite only after this launcher's API has answered on the expected port."""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from threading import Thread
import time
from urllib.request import build_opener, ProxyHandler
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def serve_api():
    import uvicorn

    sys.path.insert(0, str(ROOT))
    listener = socket.socket()
    try:
        listener.bind(("127.0.0.1", 8000))
    except OSError:
        listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    print(port, flush=True)
    # The first stdout line is the launcher handshake. Keep server logs on the console.
    sys.stdout = sys.stderr
    server = uvicorn.Server(uvicorn.Config("backend.app.main:app", port=port))

    def on_launcher_exit():
        sys.stdin.buffer.read(1)
        server.should_exit = True

    Thread(target=on_launcher_exit, daemon=True).start()
    with listener:
        server.run(sockets=[listener])


def main():
    instance = uuid4().hex
    api = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--api"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        cwd=ROOT,
        env=os.environ | {"AI_PROJECT_INSTANCE": instance},
    )
    try:
        line = api.stdout.readline().strip()
        if not line.isdigit():
            print("API startup failed. See the server error above.", file=sys.stderr)
            return 1
        origin = "http://127.0.0.1:" + line.decode("ascii")
        local = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if api.poll() is not None:
                break
            try:
                with local.open(origin + "/api/health", timeout=1) as reply:
                    health = json.load(reply)
                if health.get("instance") == instance and health.get("protocol") == 2:
                    print(
                        "The browser will open when Vite is ready. Press Ctrl+C here to stop.",
                        flush=True,
                    )
                    return subprocess.call(
                        [
                            shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                            "run",
                            "dev",
                            "--",
                            "--open",
                        ],
                        cwd=ROOT / "frontend",
                        env=os.environ | {"AI_PROJECT_API_ORIGIN": origin},
                    )
                break
            except (OSError, ValueError):
                time.sleep(0.1)
        print(
            "The API did not confirm readiness. See the server messages above.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        api.stdin.close()
        api.wait()


if __name__ == "__main__":
    if sys.argv[1:] == ["--api"]:
        serve_api()
    else:
        sys.exit(main())
