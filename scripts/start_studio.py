"""Serve the packaged studio and API together on a single local socket."""

import asyncio
import json
from pathlib import Path
import socket
import sys
from urllib.request import ProxyHandler, build_opener
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def verify_site(url):
    local = build_opener(ProxyHandler({}))
    with local.open(url + "/api/health", timeout=10) as response:
        if json.load(response).get("protocol") != 2:
            raise RuntimeError("Unexpected API version")
    with local.open(url + "/", timeout=10) as response:
        if b'id="root"' not in response.read():
            raise RuntimeError("Studio homepage is missing")


async def main():
    import uvicorn
    from fastapi.staticfiles import StaticFiles

    sys.path.insert(0, str(ROOT))
    from backend.app.main import app

    site = ROOT / "studio"
    if not (site / "index.html").is_file():
        raise RuntimeError("Missing studio/index.html. Extract the entire project ZIP.")
    app.mount("/", StaticFiles(directory=site, html=True))
    with socket.socket() as listener:
        if sys.platform == "win32":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            listener.bind(("127.0.0.1", 5173))
        except OSError:
            listener.bind(("127.0.0.1", 0))
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        server = uvicorn.Server(uvicorn.Config(app, access_log=False))
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("The local server stopped during startup.")
                await asyncio.sleep(0.05)
            await asyncio.to_thread(verify_site, url)
            print(f"Website ready: {url}\nKeep this window open. Press Ctrl+C to stop.", flush=True)
            await asyncio.to_thread(webbrowser.open, url)
            await task
        finally:
            server.should_exit = True
            await task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
