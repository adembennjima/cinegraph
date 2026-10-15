"""Find similar movies using shared positive ratings."""

from fastapi import APIRouter, HTTPException, Path, Query, Request
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["Movies"])


class SimilarMovie(BaseModel):
    """A similar movie with evidence from shared audiences."""

    movieId: int
    title: str
    commonLikers: int
    similarity: float


SIMILAR_MOVIES_QUERY = """
MATCH (source:Movie {movieId: $movie_id})
WITH source,
     COUNT {
         (source)<-[rating:RATED]-(:User)
         WHERE rating.rating >= 4
     } AS sourceLikers

MATCH (source)<-[first:RATED]-(u:User)
      -[second:RATED]->(candidate:Movie)
WHERE first.rating >= 4
  AND second.rating >= 4
  AND candidate <> source

WITH candidate, sourceLikers, count(DISTINCT u) AS commonLikers
WHERE commonLikers >= 3

WITH candidate, sourceLikers, commonLikers,
     COUNT {
         (candidate)<-[rating:RATED]-(:User)
         WHERE rating.rating >= 4
     } AS candidateLikers

RETURN candidate.movieId AS movieId,
       candidate.title AS title,
       commonLikers,
       round(
           1.0 * commonLikers /
           (sourceLikers + candidateLikers - commonLikers),
           4
       ) AS similarity
ORDER BY similarity DESC, commonLikers DESC, movieId ASC
LIMIT $limit
"""


@router.get(
    "/movies/{movie_id}/similar",
    response_model=list[SimilarMovie],
)
def similar_movies(
    request: Request,
    movie_id: int = Path(ge=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[SimilarMovie]:
    """Find movies with overlapping audiences using Jaccard similarity."""
    driver = request.app.state.neo4j_driver

    try:
        with driver.session(database="neo4j") as session:
            movie = session.run(
                "MATCH (m:Movie {movieId: $movie_id}) RETURN m.movieId AS id",
                movie_id=movie_id,
            ).single()

            if movie is None:
                raise HTTPException(
                    status_code=404,
                    detail="Movie not found.",
                )

            result = session.run(
                SIMILAR_MOVIES_QUERY,
                movie_id=movie_id,
                limit=limit,
            )

            return [
                SimilarMovie(**record.data())
                for record in result
            ]
    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve similar movies from the database.",
        ) from error