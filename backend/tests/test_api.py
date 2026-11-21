import io
import csv
import time
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.app import exports
from backend.app.main import app
from backend.app.environment import Environment


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
            row["passed"]
            for row in client.post(path + "/validate?fine=true", json=env).json()
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
                assert Image.open(io.BytesIO(data)).size == (1120, 720)
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
