"""Minimal real smoke test for the GSL backend.

Runs the actual FastAPI app (real routers, real tool registry, real SQLite in a
temp file) and asserts:
  - health is public
  - the tool registry loads and is served
  - powerful/data endpoints reject unauthenticated access (401)
  - login with the configured credentials issues a working token
  - an authenticated request succeeds and command preview resolves for real

No external network or subprocess execution is performed.
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Configure auth deterministically BEFORE importing the app/config.
os.environ["GSL_AUTH_USERNAME"] = "tester"
os.environ["GSL_AUTH_PASSWORD"] = "smoke-test-pw"
# Keep the SPA mount out of the test app.
os.environ["GSL_STATIC_DIR"] = "/nonexistent-static-dir-for-tests"

# Use a throwaway DB so the test never touches the real gsl.db.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()

import app.database as database  # noqa: E402

database.DB_PATH = _tmp_db.name

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # triggers lifespan (auth.configure + init_db)
        yield c
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass


def _login(client) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": "tester", "password": "smoke-test-pw"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


def test_health_is_public(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_tools_require_auth(client):
    assert client.get("/api/tools").status_code == 401


def test_execute_requires_auth(client):
    resp = client.post(
        "/api/execute",
        json={"toolId": "nmap", "params": {}, "command": "echo hi"},
    )
    assert resp.status_code == 401


def test_login_rejects_bad_credentials(client):
    resp = client.post(
        "/api/auth/login", json={"username": "tester", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_tool_registry_loads_and_serves(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    tools = client.get("/api/tools", headers=headers)
    assert tools.status_code == 200
    data = tools.json()
    assert len(data) >= 80  # 83 tools ship in the registry
    assert any(t["id"] == "nmap" for t in data)


def test_command_preview_resolves(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/tools/nmap/preview-command",
        headers=headers,
        json={"params": {"target": "192.168.0.1", "scan_type": "-sV", "ports": "80"}},
    )
    assert resp.status_code == 200
    cmd = resp.json()["command"]
    assert cmd.startswith("nmap")
    assert "192.168.0.1" in cmd


def test_dashboard_summary_authenticated(client):
    token = _login(client)
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.get("/api/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalTools"] >= 80
    assert body["totalCategories"] >= 1
