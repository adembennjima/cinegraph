"""Import MovieLens users and ratings into Neo4j."""

from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase

from app.config import Settings


IMPORT_QUERY = """
UNWIND $rows AS row
MATCH (m:Movie {movieId: row.movieId})
MERGE (u:User {userId: row.userId})
MERGE (u)-[r:RATED]->(m)
SET r.rating = row.rating,
    r.timestamp = row.timestamp
"""


def main() -> None:
    """Import ratings in batches without creating duplicates."""
    data_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "ml-latest-small"
        / "ratings.csv"
    )
    settings = Settings()
    imported = 0

    with GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(
            settings.neo4j_user,
            settings.neo4j_password.get_secret_value(),
        ),
    ) as driver:
        driver.verify_connectivity()

        with driver.session(database="neo4j") as session:
            for batch in pd.read_csv(data_path, chunksize=5000):
                rows = batch.to_dict(orient="records")
                session.run(IMPORT_QUERY, rows=rows).consume()

                imported += len(rows)
                print(f"Processed {imported:,} ratings")

            users = session.run(
                "MATCH (u:User) RETURN count(u) AS total"
            ).single()["total"]

            ratings = session.run(
                """
                MATCH (:User)-[r:RATED]->(:Movie)
                RETURN count(r) AS total
                """
            ).single()["total"]

            print(f"\nUsers stored: {users:,}")
            print(f"Ratings stored: {ratings:,}")


if __name__ == "__main__":
    main()