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
      -[link:SIMILAR_TO]->(candidate:Movie)

RETURN candidate.movieId AS movieId,
       candidate.title AS title,
       COUNT {
           (source)<-[first:RATED]-(u:User)
           -[second:RATED]->(candidate)
           WHERE first.rating >= 4
             AND second.rating >= 4
       } AS commonLikers,
       round(link.score, 4) AS similarity
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
    limit: int = Query(default=10, ge=1, le=10),
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
class RankedMovie(BaseModel):
    """A movie ranked by centrality in the similarity network."""

    movieId: int
    title: str
    pageRank: float


@router.get(
    "/movies/trending",
    response_model=list[RankedMovie],
)
def ranked_movies(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> list[RankedMovie]:
    """Return historical network centrality, not real-time trends."""
    driver = request.app.state.neo4j_driver

    try:
        with driver.session(database="neo4j") as session:
            result = session.run(
                """
                MATCH (m:Movie)
                WHERE m.pageRank IS NOT NULL
                RETURN m.movieId AS movieId,
                       m.title AS title,
                       m.pageRank AS pageRank
                ORDER BY pageRank DESC, movieId ASC
                SKIP $offset
                LIMIT $limit
                """,
                offset=offset,
                limit=limit,
            )

            return [
                RankedMovie(**record.data())
                for record in result
            ]
    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve movie rankings.",
        ) from error
