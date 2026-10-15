"""Check the Python connection to Neo4j."""

from neo4j import GraphDatabase

from app.config import Settings


def main() -> None:
    """Connect to Neo4j and check the GDS version."""
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
            record = session.run(
                "RETURN gds.version() AS version"
            ).single()

            print("Python connected to Neo4j successfully.")
            print(f"GDS version: {record['version']}")


if __name__ == "__main__":
    main()