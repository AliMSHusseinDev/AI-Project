"""Start Vite only after this launcher's API has answered on the expected port."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from threading import Thread
import time
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def serve_api():
    import uvicorn

    sys.path.insert(0, str(ROOT))
    server = uvicorn.Server(uvicorn.Config("backend.app.main:app", port=8000))

    def on_launcher_exit():
        sys.stdin.buffer.read(1)
        server.should_exit = True

    Thread(target=on_launcher_exit, daemon=True).start()
    server.run()


def main():
    instance = uuid4().hex
    api = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--api"],
        stdin=subprocess.PIPE,
        start_new_session=os.name != "nt",
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        cwd=ROOT,
        env=os.environ | {"AI_PROJECT_INSTANCE": instance},
    )
    try:
        for _ in range(100):
            if api.poll() is not None:
                break
            try:
                with urlopen("http://127.0.0.1:8000/api/health", timeout=0.4) as reply:
                    health = json.load(reply)
                if health.get("instance") == instance and health.get("protocol") == 2:
                    print(
                        "Open http://localhost:5173 when Vite is ready. Press Ctrl+C here to stop.",
                        flush=True,
                    )
                    return subprocess.call(
                        [
                            shutil.which("npm.cmd" if os.name == "nt" else "npm"),
                            "run",
                            "dev",
                        ],
                        cwd=ROOT / "frontend",
                    )
                break
            except (OSError, ValueError):
                time.sleep(0.1)
        print(
            "This copy of the API could not start on port 8000. Close the previous AI Project server and run again.",
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
