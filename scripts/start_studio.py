"""Start Vite only after this launcher's API has answered on the expected port."""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from threading import Thread
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def serve_api():
    import uvicorn

    sys.path.insert(0, str(ROOT))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    ready_pipe = sys.stdout
    sys.stdout = sys.stderr

    class StudioServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            if self.started:
                print(port, file=ready_pipe, flush=True)

    server = StudioServer(uvicorn.Config("backend.app.main:app", port=port))

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
        print("The API is ready. Open the Local URL printed by Vite.", flush=True)
        return subprocess.call(
            [shutil.which("npm.cmd" if os.name == "nt" else "npm"), "run", "dev", "--", "--open"],
            cwd=ROOT / "frontend",
            env=os.environ | {"AI_PROJECT_API_ORIGIN": origin},
        )
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
