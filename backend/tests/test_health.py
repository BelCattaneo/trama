from fastapi.testclient import TestClient

from trama import main as main_module
from trama.main import app


def test_health_db_up():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "ok"}


def test_health_db_down(monkeypatch):
    async def fake_db_ok():
        return False

    monkeypatch.setattr(main_module, "db_ok", fake_db_ok)
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.json() == {"status": "degraded", "db": "down"}
