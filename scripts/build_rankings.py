"""Compute movie centrality using GDS PageRank."""

from neo4j import GraphDatabase

from app.config import Settings


PROJECTION_QUERY = """
CALL gds.graph.project(
    'movie-network',
    'Movie',
    {
        SIMILAR_TO: {
            orientation: 'NATURAL',
            properties: ['score']
        }
    }
)
YIELD nodeCount, relationshipCount
RETURN nodeCount, relationshipCount
"""


PAGERANK_QUERY = """
CALL gds.pageRank.write(
    'movie-network',
    {
        relationshipWeightProperty: 'score',
        writeProperty: 'pageRank',
        maxIterations: 100,
        tolerance: 0.000001,
        dampingFactor: 0.85,
        concurrency: 2
    }
)
YIELD nodePropertiesWritten, ranIterations, didConverge
RETURN nodePropertiesWritten, ranIterations, didConverge
"""


def main() -> None:
    """Rebuild the movie projection and save PageRank scores."""
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
            graph_exists = session.run(
                """
                CALL gds.graph.exists('movie-network')
                YIELD exists
                RETURN exists
                """
            ).single()["exists"]

            if graph_exists:
                session.run(
                    """
                    CALL gds.graph.drop('movie-network')
                    YIELD graphName
                    RETURN graphName
                    """
                ).consume()

            projection = session.run(PROJECTION_QUERY).single()
            print(
                f"Movie network: {projection['nodeCount']:,} nodes, "
                f"{projection['relationshipCount']:,} links"
            )

            result = session.run(PAGERANK_QUERY).single()
            print(f"Scores saved: {result['nodePropertiesWritten']:,}")
            print(f"Iterations: {result['ranIterations']}")
            print(f"Converged: {result['didConverge']}")

            print("\nTop 5 movies by network centrality:")

            ranking = session.run(
                """
                MATCH (m:Movie)
                WHERE m.pageRank IS NOT NULL
                RETURN m.title AS title, m.pageRank AS score
                ORDER BY score DESC, m.movieId ASC
                LIMIT 5
                """
            )

            for record in ranking:
                print(f"{record['title']}: {record['score']:.4f}")


if __name__ == "__main__":
    main()