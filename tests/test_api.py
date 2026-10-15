"""Integration tests for the API against the local MovieLens database."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Start the API and its database connection for the tests."""
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    """The API should report that it is running."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommendation_evidence(client: TestClient) -> None:
    """Recommendation scores should match their supporting evidence."""
    response = client.get("/api/users/1/recommendations?limit=5")

    assert response.status_code == 200
    recommendations = response.json()
    assert len(recommendations) == 5

    first = recommendations[0]
    explanation = client.get(
        f"/api/users/1/recommendations/{first['movieId']}/why"
    )

    assert explanation.status_code == 200
    evidence = explanation.json()

    assert len(evidence) == first["supportingUsers"]
    assert sum(item["sharedLikes"] for item in evidence) == first["score"]

    with app.state.neo4j_driver.session(database="neo4j") as session:
        rated_ids = {
            record["movieId"]
            for record in session.run(
                """
                MATCH (:User {userId: 1})-[:RATED]->(m:Movie)
                RETURN m.movieId AS movieId
                """
            )
        }

    assert all(
        movie["movieId"] not in rated_ids
        for movie in recommendations
    )


def test_similar_movies(client: TestClient) -> None:
    """Similarities should be ordered, bounded, and exclude the source."""
    response = client.get("/api/movies/1/similar?limit=5")

    assert response.status_code == 200
    movies = response.json()
    assert len(movies) == 5
    assert all(movie["movieId"] != 1 for movie in movies)
    assert all(0 <= movie["similarity"] <= 1 for movie in movies)

    scores = [movie["similarity"] for movie in movies]
    assert scores == sorted(scores, reverse=True)


def test_unknown_user(client: TestClient) -> None:
    """An unknown user should produce a 404 response."""
    response = client.get("/api/users/999999/recommendations")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "/api/users/1/recommendations?limit=0",
        "/api/users/1/recommendations?limit=51",
        "/api/movies/1/similar?limit=11",
    ],
)
def test_invalid_limits(client: TestClient, url: str) -> None:
    """Invalid limits should be rejected before querying the graph."""
    response = client.get(url)

    assert response.status_code == 422