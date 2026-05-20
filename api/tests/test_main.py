from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError

import main
from main import app

client = TestClient(app)
VALID_EVENT = {
    "event_time": "2026-05-20T12:00:00Z",
    "src_ip": "203.0.113.44",
    "event_type": "cowrie.login.failed",
    "username": "root",
    "password": "password",
    "command": None,
    "raw_json": {"source": "pytest"},
}


def _database_available():
    try:
        with main.engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except SQLAlchemyError:
        return False


requires_database = pytest.mark.skipif(
    not _database_available(),
    reason="PostgreSQL de la demo no disponible para pruebas de integración",
)


@requires_database
def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200


def test_root_returns_status_message():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "API funcionando"}


@requires_database
def test_get_events_returns_shape():
    response = client.get("/events")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, dict)
    assert "events" in body
    assert isinstance(body["events"], list)


def test_get_events_rejects_too_large_limit():
    response = client.get("/events?limit=100000")
    assert response.status_code == 422


def test_get_events_rejects_limit_less_than_one():
    response = client.get("/events?limit=0")
    assert response.status_code == 422


def test_create_event_without_authorization_fails():
    response = client.post("/events", json=VALID_EVENT)
    assert response.status_code == 401


def test_create_event_with_wrong_token_fails():
    response = client.post(
        "/events",
        headers={"Authorization": "Bearer wrong-token"},
        json=VALID_EVENT,
    )
    assert response.status_code == 403


@requires_database
def test_create_event_with_valid_token_succeeds():
    response = client.post(
        "/events",
        headers={"Authorization": f"Bearer {main.SHIPPER_TOKEN}"},
        json=VALID_EVENT,
    )
    assert response.status_code == 200
    assert response.json() == {"message": "evento insertado"}


@requires_database
def test_stats_shape():
    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total_events" in body
    assert "top_ips" in body
    assert "top_event_types" in body
    assert "recent_24h" in body


@requires_database
def test_get_unknown_event_returns_404():
    response = client.get("/events/999999999")
    assert response.status_code == 404
