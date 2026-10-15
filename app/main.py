"""Main entry point for the movie recommendation API."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError

from app.config import Settings
from app.recommendations import router as recommendations_router
from app.movies import router as movies_router

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Open the database connection and close it on shutdown."""
    settings = Settings()

    with GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(
            settings.neo4j_user,
            settings.neo4j_password.get_secret_value(),
        ),
    ) as driver:
        driver.verify_connectivity()
        application.state.neo4j_driver = driver
        yield


app = FastAPI(
    title="Movie Recommender",
    description="Movie recommendations using a Neo4j graph.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Check that the API is running."""
    return {"status": "ok"}


@app.get("/health/database", tags=["System"])
def database_health(request: Request) -> dict[str, str]:
    """Check the database connection and GDS availability."""
    driver = request.app.state.neo4j_driver

    try:
        with driver.session(database="neo4j") as session:
            record = session.run(
                "RETURN gds.version() AS version"
            ).single()

            return {
                "status": "ok",
                "database": "neo4j",
                "gds_version": record["version"],
            }
    except (DriverError, Neo4jError) as error:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        ) from error
app.include_router(recommendations_router)
app.include_router(movies_router)