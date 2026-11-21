import io
import csv
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.app import exports
from backend.app.main import app
from backend.app.environment import Environment, MAX_SEED


def wait_for_job(client, key):
    for _ in range(400):
        data = client.get(f"/api/jobs/{key}").json()
        if data["state"] != "running":
            return data
        time.sleep(0.05)
    pytest.fail("worker timed out")


def test_comparison_validation_and_selective_exports(tmp_path, monkeypatch):
    monkeypatch.setattr(exports, "OUTPUT", tmp_path)
    env = Environment(size=20).model_dump(mode="json")
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ready"
        assert (
            client.post(
                "/api/generate", json={"environment": env, "count": 3}
            ).status_code
            == 422
        )
        key = client.post(
            "/api/jobs", json={"environment": env, "mode": "Comparison"}
        ).json()["id"]
        result = wait_for_job(client, key)
        assert result["state"] == "complete" and len(result["result"]) == 2
        path = f"/api/jobs/{key}"
        assert all(
            row["passed"] for row in client.post(path + "/validate", json=env).json()
        )
        assert (
            client.post(path + "/export/csv", json=env | {"seed": 3}).status_code == 409
        )
        assert client.post(path + "/export/json", json=env).status_code == 422
        assert not list(tmp_path.iterdir())
        for kind in ("csv", "pdf", "png"):
            data = client.post(path + "/export/" + kind, json=env).content
            file = tmp_path / exports.FILES[kind][0]
            assert data == file.read_bytes() and len(list(tmp_path.iterdir())) == 1
            if kind == "png":
                assert Image.open(io.BytesIO(data)).size == (1120, 864)
            elif kind == "csv":
                rows = list(csv.reader(io.StringIO(data.decode())))
                assert (
                    rows[0] == ["Metric", "GA", "MA"]
                    and int(rows[2][1]) == result["result"][0]["count"]
                )
            else:
                assert data.startswith(b"%PDF")
            file.unlink()
        assert client.post("/api/jobs/missing/export/csv", json=env).status_code == 404


def test_cancel_and_incomplete_export():
    env = Environment(size=20).model_dump(mode="json")
    with TestClient(app) as client:
        key = client.post(
            "/api/jobs", json={"environment": env, "mode": "Benchmark", "trials": 2}
        ).json()["id"]
        assert client.delete(f"/api/jobs/{key}").json()["state"] == "cancelled"
        assert client.get(f"/api/jobs/{key}").json()["state"] == "cancelled"
        assert client.post(f"/api/jobs/{key}/export/png", json=env).status_code == 409
        key = client.post("/api/jobs", json={"environment": env, "mode": "MA"}).json()[
            "id"
        ]
        assert wait_for_job(client, key)["state"] == "complete"
        assert client.post(f"/api/jobs/{key}/export/png", json=env).status_code == 409


def test_poll_simultaneous_searches():
    env = Environment(size=40, base=(20, 20)).model_dump(mode="json")
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=6) as readers:

        def poll(key):
            end = time.monotonic() + 60
            while time.monotonic() < end:
                reply = client.get(f"/api/jobs/{key}")
                reply.raise_for_status()
                data = reply.json()
                if data["state"] != "running":
                    assert data["state"] == "complete", data
                    return [r["algorithm"] for r in data["result"]]
                progress = data["progress"]
                if progress:
                    assert (
                        progress["label"] and 0 <= progress["done"] <= progress["total"]
                    )
                time.sleep(0.01)
            pytest.fail("worker timed out")

        observers = []
        for mode in ("GA", "MA", "Comparison"):
            reply = client.post("/api/jobs", json={"mode": mode, "environment": env})
            assert reply.status_code == 202
            key = reply.json()["id"]
            expected = ["GA", "MA"] if mode == "Comparison" else [mode]
            observers.extend((readers.submit(poll, key), expected) for _ in range(2))
        for observer, expected in observers:
            assert observer.result() == expected


def test_fresh_obstacles_and_seed_replay():
    env = Environment(size=40, base=(20, 20), base_margin=4, seed=MAX_SEED)
    with TestClient(app) as client:

        def generate(current, count, **options):
            response = client.post(
                "/api/generate",
                json={
                    "environment": current.model_dump(mode="json"),
                    "count": count,
                    **options,
                },
            )
            response.raise_for_status()
            return Environment.model_validate(response.json())

        layout = generate(env, 8, fresh=True)
        assert layout.seed == MAX_SEED
        for next_seed in (0, 1, 2):
            previous = layout
            layout = generate(previous, 8, fresh=True)
            assert len(layout.obstacles) == 8 and layout.seed == next_seed
            assert layout.obstacles != previous.obstacles
            assert generate(env.model_copy(update={"seed": next_seed}), 8) == layout
        expanded = generate(layout, 9, append=True)
        assert (
            expanded.obstacles[:-1] == layout.obstacles and expanded.seed == layout.seed
        )
        empty = generate(expanded, 0, fresh=True)
        assert not empty.obstacles and generate(empty, 0, fresh=True) == empty
