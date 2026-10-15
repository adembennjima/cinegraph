"""Create Neo4j constraints and indexes."""

from neo4j import GraphDatabase

from app.config import Settings


SCHEMA_QUERIES = (
    """
    CREATE CONSTRAINT user_id_unique IF NOT EXISTS
    FOR (u:User) REQUIRE u.userId IS UNIQUE
    """,
    """
    CREATE CONSTRAINT movie_id_unique IF NOT EXISTS
    FOR (m:Movie) REQUIRE m.movieId IS UNIQUE
    """,
    """
    CREATE CONSTRAINT genre_name_unique IF NOT EXISTS
    FOR (g:Genre) REQUIRE g.name IS UNIQUE
    """,
    """
    CREATE INDEX movie_title IF NOT EXISTS
    FOR (m:Movie) ON (m.title)
    """,
)


def main() -> None:
    """Create the schema without duplicating existing rules."""
    settings = Settings()

    with GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(
            settings.neo4j_user,
            settings.neo4j_password.get_secret_value(),
        ),
    ) as driver:
        driver.verify_connectivity()

        with driver.session(database="neo4j") as session:
            for query in SCHEMA_QUERIES:
                session.run(query).consume()

        print("Schema ready: 3 uniqueness constraints and 1 title index.")


if __name__ == "__main__":
    main()