import json
from types import SimpleNamespace

import pytest

from app import ai_analyzer


def test_analyze_log_rejects_empty_input():
    with pytest.raises(ValueError, match="Log content cannot be empty"):
        ai_analyzer.analyze_log("")


def test_analyze_log_rejects_whitespace():
    with pytest.raises(ValueError, match="Log content cannot be empty"):
        ai_analyzer.analyze_log("   \n  ")


def test_analyze_log_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not configured"):
        ai_analyzer.analyze_log("ERROR: Database connection failed")


def test_analyze_log_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

    response_data = {
        "severity": "HIGH",
        "summary": "Database connection failed",
        "root_cause": "The database refused the connection",
        "possible_causes": ["Database unavailable", "Incorrect port"],
        "recommended_actions": ["Check database status", "Verify port settings"],
        "confidence": 0.95,
    }

    fake_response = SimpleNamespace(text=json.dumps(response_data))
    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: fake_response
        )
    )

    monkeypatch.setattr(
        ai_analyzer.genai, "Client", lambda **kwargs: fake_client
    )

    result = ai_analyzer.analyze_log("ERROR: Connection refused by database")

    assert result.severity == "HIGH"
    assert result.summary == "Database connection failed"
    assert result.confidence == 0.95
    assert len(result.recommended_actions) == 2


def test_analyze_log_rejects_empty_gemini_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")

    fake_client = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: SimpleNamespace(text="")
        )
    )

    monkeypatch.setattr(
        ai_analyzer.genai, "Client", lambda **kwargs: fake_client
    )

    with pytest.raises(RuntimeError, match="Gemini returned an empty response"):
        ai_analyzer.analyze_log("ERROR: Database connection failed")
