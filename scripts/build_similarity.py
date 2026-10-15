"""Build and store movie similarities using Neo4j GDS."""

from neo4j import GraphDatabase

from app.config import Settings


PROJECTION_QUERY = """
MATCH (movie:Movie)
OPTIONAL MATCH (movie)<-[rating:RATED]-(user:User)
WHERE rating.rating >= 4

WITH gds.graph.project(
    'movie-audiences',
    movie,
    user,
    {
        sourceNodeLabels: labels(movie),
        targetNodeLabels: labels(user),
        relationshipType: 'LIKED_BY'
    }
) AS graph

RETURN graph.nodeCount AS nodes,
       graph.relationshipCount AS relationships
"""


SIMILARITY_QUERY = """
CALL gds.nodeSimilarity.write(
    'movie-audiences',
    {
        similarityMetric: 'JACCARD',
        degreeCutoff: 3,
        similarityCutoff: 0.1,
        topK: 10,
        concurrency: 2,
        writeRelationshipType: 'SIMILAR_TO',
        writeProperty: 'score'
    }
)
YIELD nodesCompared, relationshipsWritten
RETURN nodesCompared, relationshipsWritten
"""


def main() -> None:
    """Rebuild the projection and replace derived similarity links."""
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
                CALL gds.graph.exists('movie-audiences')
                YIELD exists
                RETURN exists
                """
            ).single()["exists"]

            if graph_exists:
                session.run(
                    "CALL gds.graph.drop('movie-audiences')"
                ).consume()

            projection = session.run(PROJECTION_QUERY).single()
            print(
                f"Projection ready: {projection['nodes']:,} nodes, "
                f"{projection['relationships']:,} relationships"
            )

            session.run(
                "MATCH (:Movie)-[r:SIMILAR_TO]->(:Movie) DELETE r"
            ).consume()

            result = session.run(SIMILARITY_QUERY).single()
            print(f"Nodes compared: {result['nodesCompared']:,}")
            print(
                "Similarity links stored: "
                f"{result['relationshipsWritten']:,}"
            )


if __name__ == "__main__":
    main()
