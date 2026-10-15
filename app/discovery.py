"""Discover movies using communities learned from the graph."""

from fastapi import APIRouter, HTTPException, Path, Query, Request
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["Discovery"])


class DiscoveredMovie(BaseModel):
    """A movie discovered through a user's preferred communities."""

    movieId: int
    title: str
    communityId: int
    likedInCommunity: int
    exampleLikedMovies: list[str]
    pageRank: float


DISCOVERY_QUERY = """
MATCH (u:User {userId: $user_id})-[r:RATED]->(liked:Movie)
WHERE r.rating >= 4
  AND liked.communityId IS NOT NULL

WITH u, liked
ORDER BY liked.movieId

WITH u,
     liked.communityId AS communityId,
     count(liked) AS likedInCommunity,
     collect(liked.title)[..3] AS exampleLikedMovies
ORDER BY likedInCommunity DESC, communityId ASC
LIMIT 3

MATCH (candidate:Movie)
WHERE candidate.communityId = communityId
  AND NOT EXISTS {
    MATCH (u)-[:RATED]->(candidate)
  }

RETURN candidate.movieId AS movieId,
       candidate.title AS title,
       communityId,
       likedInCommunity,
       exampleLikedMovies,
       coalesce(candidate.pageRank, 0.0) AS pageRank
ORDER BY likedInCommunity DESC, pageRank DESC, movieId ASC
SKIP $offset
LIMIT $limit
"""


@router.get(
    "/users/{user_id}/discover",
    response_model=list[DiscoveredMovie],
)
def discover_movies(
    request: Request,
    user_id: int = Path(ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> list[DiscoveredMovie]:
    """Suggest unrated movies from the user's top three communities."""
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
                DISCOVERY_QUERY,
                user_id=user_id,
                limit=limit,
                offset=offset,
            )

            return [
                DiscoveredMovie(**record.data())
                for record in result
            ]
    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve community recommendations.",
        ) from error
