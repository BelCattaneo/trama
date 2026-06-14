from fastapi.testclient import TestClient

from trama.main import app


def test_health_db_up():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "db": "ok"}
