"""Personalized recommendations based on shared movie preferences."""

from fastapi import APIRouter, HTTPException, Path, Query, Request
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["Recommendations"])


class Recommendation(BaseModel):
    """A recommended movie and its supporting evidence."""

    movieId: int
    title: str
    supportingUsers: int
    averageRating: float
    score: int


RECOMMENDATIONS_QUERY = """
MATCH (u:User {userId: $user_id})-[r1:RATED]->(shared:Movie)
      <-[r2:RATED]-(other:User)
WHERE other <> u
  AND r1.rating >= 4
  AND r2.rating >= 4

WITH u, other, count(shared) AS sharedLikes
WHERE sharedLikes >= 3
ORDER BY sharedLikes DESC, other.userId ASC
LIMIT 20

MATCH (other)-[r:RATED]->(candidate:Movie)
WHERE r.rating >= 4
  AND NOT EXISTS {
    MATCH (u)-[:RATED]->(candidate)
  }

WITH candidate,
     count(other) AS supportingUsers,
     avg(r.rating) AS averageRating,
     sum(sharedLikes) AS score

RETURN candidate.movieId AS movieId,
       candidate.title AS title,
       supportingUsers,
       round(averageRating, 2) AS averageRating,
       score
ORDER BY score DESC, supportingUsers DESC, movieId ASC
LIMIT $limit
"""


@router.get(
    "/users/{user_id}/recommendations",
    response_model=list[Recommendation],
)
def recommend_movies(
    request: Request,
    user_id: int = Path(ge=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[Recommendation]:
    """Recommend unrated movies using users with shared likes."""
    driver = request.app.state.neo4j_driver

    try:
        with driver.session(database="neo4j") as session:
            user = session.run(
                "MATCH (u:User {userId: $user_id}) RETURN u.userId AS id",
                user_id=user_id,
            ).single()

            if user is None:
                raise HTTPException(
                    status_code=404,
                    detail="User not found.",
                )

            result = session.run(
                RECOMMENDATIONS_QUERY,
                user_id=user_id,
                limit=limit,
            )

            return [
                Recommendation(**record.data())
                for record in result
            ]
    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve recommendations from the database.",
        ) from error
class RecommendationEvidence(BaseModel):
    """Graph evidence supporting a recommendation."""

    supportingUserId: int
    sharedLikes: int
    sharedMovies: list[str]
    recommendedMovieRating: float


EXPLANATION_QUERY = """
MATCH (u:User {userId: $user_id})-[r1:RATED]->(shared:Movie)
      <-[r2:RATED]-(other:User)
WHERE other <> u
  AND r1.rating >= 4
  AND r2.rating >= 4

WITH u, other, shared
ORDER BY shared.movieId

WITH u, other,
     count(shared) AS sharedLikes,
     collect(shared.title) AS sharedMovies
WHERE sharedLikes >= 3
ORDER BY sharedLikes DESC, other.userId ASC
LIMIT 20

MATCH (other)-[r:RATED]->(candidate:Movie {movieId: $movie_id})
WHERE r.rating >= 4
  AND NOT EXISTS {
    MATCH (u)-[:RATED]->(candidate)
  }

RETURN other.userId AS supportingUserId,
       sharedLikes,
       sharedMovies[..5] AS sharedMovies,
       r.rating AS recommendedMovieRating
ORDER BY sharedLikes DESC, supportingUserId ASC
"""


@router.get(
    "/users/{user_id}/recommendations/{movie_id}/why",
    response_model=list[RecommendationEvidence],
)
def explain_recommendation(
    request: Request,
    user_id: int = Path(ge=1),
    movie_id: int = Path(ge=1),
) -> list[RecommendationEvidence]:
    """Show supporting users and up to five shared liked movies per user."""
    driver = request.app.state.neo4j_driver

    try:
        with driver.session(database="neo4j") as session:
            entities = session.run(
                """
                RETURN
                    EXISTS {
                        MATCH (:User {userId: $user_id})
                    } AS userExists,
                    EXISTS {
                        MATCH (:Movie {movieId: $movie_id})
                    } AS movieExists
                """,
                user_id=user_id,
                movie_id=movie_id,
            ).single()

            if not entities["userExists"]:
                raise HTTPException(
                    status_code=404,
                    detail="User not found.",
                )

            if not entities["movieExists"]:
                raise HTTPException(
                    status_code=404,
                    detail="Movie not found.",
                )

            result = session.run(
                EXPLANATION_QUERY,
                user_id=user_id,
                movie_id=movie_id,
            )

            return [
                RecommendationEvidence(**record.data())
                for record in result
            ]
    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve recommendation evidence.",
        ) from error
