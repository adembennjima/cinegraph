"""Import MovieLens movies and genres into Neo4j."""

from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase

from app.config import Settings


IMPORT_QUERY = """
UNWIND $rows AS row
MERGE (m:Movie {movieId: row.movieId})
SET m.title = row.title,
    m.year = row.year
WITH m, row
UNWIND row.genres AS genre
MERGE (g:Genre {name: genre})
MERGE (m)-[:IN_GENRE]->(g)
"""


def main() -> None:
    """Import movies in batches without creating duplicates."""
    data_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "ml-latest-small"
        / "movies.csv"
    )
    movies = pd.read_csv(data_path)
    rows = []

    for movie in movies.itertuples(index=False):
        year_match = pd.Series([movie.title]).str.extract(
            r"\((\d{4})\)$"
        ).iloc[0, 0]

        rows.append(
            {
                "movieId": int(movie.movieId),
                "title": movie.title,
                "year": int(year_match) if pd.notna(year_match) else None,
                "genres": [
                    genre
                    for genre in movie.genres.split("|")
                    if genre != "(no genres listed)"
                ],
            }
        )

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
            for start in range(0, len(rows), 1000):
                batch = rows[start:start + 1000]
                session.run(IMPORT_QUERY, rows=batch).consume()
                print(f"Imported {start + len(batch):,}/{len(rows):,} movies")

            result = session.run(
                """
                MATCH (m:Movie)
                RETURN count(m) AS movies
                """
            ).single()

            print(f"\nMovies stored in Neo4j: {result['movies']:,}")


if __name__ == "__main__":
    main()
