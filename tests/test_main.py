
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base, get_db
from app.models import IncidentAnalysis


@pytest.fixture
def client():
    # Use a separate in-memory database for every test.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=test_engine)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main_module.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main_module.app) as test_client:
        yield test_client

    main_module.app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture
def fake_analysis():
    return IncidentAnalysis(
        severity="HIGH",
        summary="Database connection failed.",
        root_cause="PostgreSQL is unreachable.",
        possible_causes=[
            "Database service is down.",
            "Network connection is blocked.",
        ],
        recommended_actions=[
            "Check PostgreSQL status.",
            "Verify network connectivity.",
        ],
        confidence=0.90,
    )


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_analyze_log_and_save_incident(
    client, monkeypatch, fake_analysis
):
    monkeypatch.setattr(
        main_module,
        "analyze_log",
        lambda log: fake_analysis,
    )

    response = client.post(
        "/analyze-log",
        json={"log": "ERROR: PostgreSQL connection failed"},
    )

    assert response.status_code == 200
    assert response.json()["severity"] == "HIGH"

    # Confirm the analysis was saved to the test database.
    incidents = client.get("/incidents")
    assert incidents.status_code == 200
    assert len(incidents.json()) == 1

    incident_id = incidents.json()[0]["id"]

    detail = client.get(f"/incidents/{incident_id}")
    assert detail.status_code == 200
    assert detail.json()["root_cause"] == (
        "PostgreSQL is unreachable."
    )


def test_list_incidents_empty(client):
    response = client.get("/incidents")

    assert response.status_code == 200
    assert response.json() == []


def test_incident_not_found(client):
    response = client.get("/incidents/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found."


def test_analyze_file_and_save_incident(
    client, monkeypatch, fake_analysis
):
    monkeypatch.setattr(
        main_module,
        "analyze_log",
        lambda log: fake_analysis,
    )

    response = client.post(
        "/analyze-file",
        files={
            "file": (
                "test.log",
                b"ERROR: Database connection failed",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["severity"] == "HIGH"

    incidents = client.get("/incidents")
    assert len(incidents.json()) == 1
    assert incidents.json()[0]["log"] == (
        "ERROR: Database connection failed"
    )


def test_analyze_empty_file(client):
    response = client.post(
        "/analyze-file",
        files={
            "file": (
                "empty.log",
                b"",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Log file is empty."
