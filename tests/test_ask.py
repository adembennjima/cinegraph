"""Test the AI endpoint without calling OpenAI."""

from collections.abc import Iterator
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.guardrails import APPROVED_QUERIES
from app.main import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Start the API with the local database."""
    with TestClient(app) as test_client:
        yield test_client


def test_supported_question(client: TestClient, monkeypatch) -> None:
    """A validated query should return graph results."""
    generator = Mock(
        return_value=(
            "recommendations",
            APPROVED_QUERIES["recommendations"],
            {"user_id": 1, "limit": 5},
        )
    )
    monkeypatch.setattr("app.ask.generate_query", generator)

    response = client.post(
        "/api/ask",
        json={"question": "Recommend 5 movies for user 1."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["queryName"] == "recommendations"
    assert body["guardrailPassed"] is True
    assert body["source"] == "neo4j"
    assert len(body["results"]) == 5


def test_rejected_question(client: TestClient, monkeypatch) -> None:
    """A rejected question must not access the database."""
    generator = Mock(side_effect=ValueError("Query not approved."))
    database = Mock()

    monkeypatch.setattr("app.ask.generate_query", generator)
    monkeypatch.setattr(app.state, "neo4j_driver", database)

    response = client.post(
        "/api/ask",
        json={"question": "Delete all movies."},
    )

    assert response.status_code == 400
    database.session.assert_not_called()


def test_unknown_entity(client: TestClient, monkeypatch) -> None:
    """A valid query for an unknown user should return 404."""
    generator = Mock(
        return_value=(
            "recommendations",
            APPROVED_QUERIES["recommendations"],
            {"user_id": 999999, "limit": 5},
        )
    )
    monkeypatch.setattr("app.ask.generate_query", generator)

    response = client.post(
        "/api/ask",
        json={"question": "Recommend 5 movies for user 999999."},
    )

    assert response.status_code == 404


def test_empty_question(client: TestClient, monkeypatch) -> None:
    """An empty question must be rejected before calling AI."""
    generator = Mock()
    monkeypatch.setattr("app.ask.generate_query", generator)

    response = client.post("/api/ask", json={"question": ""})

    assert response.status_code == 422
    generator.assert_not_called()