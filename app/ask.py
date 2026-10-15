"""Answer natural-language questions using validated graph queries."""

from fastapi import APIRouter, HTTPException, Request
from neo4j import Query
from neo4j.exceptions import DriverError, Neo4jError
from openai import OpenAIError
from pydantic import BaseModel, Field, JsonValue

from app.ai import generate_query

router = APIRouter(prefix="/api", tags=["AI"])


class AskRequest(BaseModel):
    """A question about recommendations or similar movies."""

    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    """Graph results together with the query used to retrieve them."""

    queryName: str
    cypher: str
    parameters: dict[str, int]
    guardrailPassed: bool
    source: str
    results: list[dict[str, JsonValue]]


@router.post("/ask", response_model=AskResponse)
def ask_graph(payload: AskRequest, request: Request) -> AskResponse:
    """Generate, validate, and execute an approved read query."""
    try:
        name, cypher, parameters = generate_query(payload.question)
    except OpenAIError as error:
        raise HTTPException(
            status_code=502,
            detail="The AI service could not process the question.",
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=503,
            detail="The AI connection is not configured.",
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    driver = request.app.state.neo4j_driver

    try:
        with driver.session(
            database="neo4j",
            default_access_mode="READ",
        ) as session:
            if name == "recommendations":
                entity_query = """
                MATCH (u:User {userId: $user_id})
                RETURN u.userId AS id
                """
                entity_parameters = {"user_id": parameters["user_id"]}
            else:
                entity_query = """
                MATCH (m:Movie {movieId: $movie_id})
                RETURN m.movieId AS id
                """
                entity_parameters = {"movie_id": parameters["movie_id"]}

            entity = session.run(
                entity_query,
                entity_parameters,
            ).single()

            if entity is None:
                raise HTTPException(
                    status_code=404,
                    detail="The requested user or movie does not exist.",
                )

            result = session.run(
                Query(cypher, timeout=10.0),
                parameters,
            )
            rows = [record.data() for record in result]

        return AskResponse(
            queryName=name,
            cypher=cypher,
            parameters=parameters,
            guardrailPassed=True,
            source="neo4j",
            results=rows,
        )

    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve results from the graph.",
        ) from error
