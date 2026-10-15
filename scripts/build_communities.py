"""Group connected movies into communities using GDS Louvain."""

from neo4j import GraphDatabase

from app.config import Settings


PROJECTION_QUERY = """
MATCH (a:Movie)-[r:SIMILAR_TO]->(b:Movie)

WITH
    CASE WHEN a.movieId < b.movieId THEN a ELSE b END AS source,
    CASE WHEN a.movieId < b.movieId THEN b ELSE a END AS target,
    max(r.score) AS weight

WITH gds.graph.project(
    'movie-communities',
    source,
    target,
    {
        sourceNodeLabels: 'Movie',
        targetNodeLabels: 'Movie',
        relationshipProperties: {score: weight}
    },
    {
        undirectedRelationshipTypes: ['*']
    }
) AS graph

RETURN graph.nodeCount AS nodes,
       graph.relationshipCount AS relationships
"""


COMMUNITY_QUERY = """
CALL gds.louvain.write(
    'movie-communities',
    {
        relationshipWeightProperty: 'score',
        writeProperty: 'communityId',
        concurrency: 1
    }
)
YIELD communityCount, modularity, nodePropertiesWritten
RETURN communityCount, modularity, nodePropertiesWritten
"""


def main() -> None:
    """Rebuild movie communities and save their identifiers."""
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
                CALL gds.graph.exists('movie-communities')
                YIELD exists
                RETURN exists
                """
            ).single()["exists"]

            if graph_exists:
                session.run(
                    """
                    CALL gds.graph.drop('movie-communities')
                    YIELD graphName
                    RETURN graphName
                    """
                ).consume()

            projection = session.run(PROJECTION_QUERY).single()
            print(
                f"Community graph: {projection['nodes']:,} movies, "
                f"{projection['relationships']:,} projected links"
            )

            session.run(
                "MATCH (m:Movie) REMOVE m.communityId"
            ).consume()

            result = session.run(COMMUNITY_QUERY).single()
            print(f"Communities found: {result['communityCount']}")
            print(f"Modularity: {result['modularity']:.4f}")
            print(
                "Movies assigned a community: "
                f"{result['nodePropertiesWritten']:,}"
            )


if __name__ == "__main__":
    main()
