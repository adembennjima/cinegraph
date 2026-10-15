"""Test AI query validation without making API calls."""

import pytest

from app.guardrails import APPROVED_QUERIES, validate_query


def test_valid_recommendations() -> None:
    """An approved recommendation query should pass."""
    name, query, parameters = validate_query(
        APPROVED_QUERIES["recommendations"],
        {"user_id": 1, "limit": 5},
    )

    assert name == "recommendations"
    assert query == APPROVED_QUERIES["recommendations"]
    assert parameters == {"user_id": 1, "limit": 5}


def test_valid_similar_movies() -> None:
    """An approved similarity query should pass."""
    name, _, parameters = validate_query(
        APPROVED_QUERIES["similar_movies"],
        {"movie_id": 1, "limit": 5},
    )

    assert name == "similar_movies"
    assert parameters["movie_id"] == 1


def test_write_query_rejected() -> None:
    """A query that deletes data must be rejected."""
    with pytest.raises(ValueError, match="not approved"):
        validate_query(
            "MATCH (n) DETACH DELETE n",
            {},
        )


def test_extra_parameter_rejected() -> None:
    """Unexpected parameters must be rejected."""
    with pytest.raises(ValueError, match="unexpected"):
        validate_query(
            APPROVED_QUERIES["recommendations"],
            {"user_id": 1, "limit": 5, "extra": "anything"},
        )


def test_excessive_limit_rejected() -> None:
    """The AI cannot request more than ten results."""
    with pytest.raises(ValueError, match="between 1 and 10"):
        validate_query(
            APPROVED_QUERIES["recommendations"],
            {"user_id": 1, "limit": 1000},
        )