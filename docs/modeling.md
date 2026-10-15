# Graph modeling decisions

## Purpose

CineGraph connects viewers, movies, and genres to support personalized recommendations, audience similarity, and explainable discovery.

The model uses three node labels and three relationship types.

## Implemented schema

| Pattern | Meaning |
|---|---|
| `(User)-[:RATED]->(Movie)` | A viewer rated a movie |
| `(Movie)-[:IN_GENRE]->(Genre)` | A movie belongs to a genre |
| `(Movie)-[:SIMILAR_TO]->(Movie)` | Two movies share a similar positive-rating audience |

`RATED` stores `rating` and `timestamp`.
`SIMILAR_TO` stores the derived similarity `score`.

## Why these choices?

### Genres as nodes

Movies can belong to several genres. Separate Genre nodes provide shared identities and explicit membership relationships.

This supports traversals such as finding movies in a shared genre and combining genre information with audience relationships.

Genre properties on movies would also be reasonable for a simpler application. Nodes were chosen because genre membership is part of the graph structure and can support future filtering.

### Ratings as relationships

A rating belongs to a specific user–movie pair. Its value and timestamp therefore belong on the RATED relationship.

Creating a separate Rating node would add complexity without helping the current queries. It could become useful if the application needed multiple rating events, reviews, or provenance records.

### Stable business identifiers

Users and movies retain their MovieLens identifiers. The API does not expose Neo4j internal node identifiers.

Uniqueness constraints on User.userId, Movie.movieId, and Genre.name prevent duplicate identities during repeated imports.

### Materialized movie similarity

Computing audience overlap during every request would repeatedly traverse ratings.

GDS computes similarity in a batch, and the application stores the selected results as SIMILAR_TO relationships. API queries can then retrieve those links directly.

The tradeoff is freshness: after changing ratings, the similarity graph and downstream algorithms must be rebuilt.

### Derived node properties

PageRank and community identifiers are stored on Movie nodes for retrieval by the API.

These are computed outputs rather than original MovieLens attributes. PageRank measures centrality in the selected similarity network. Community identifiers describe algorithmic group membership and have no intrinsic genre meaning.

## Anti-genericity appendix

### Illustrative AI-generated baseline

For comparison, the assistant proposes this deliberately minimal schema:

- User nodes with userId.
- Movie nodes with movieId, title, and a genres property.
- RATED relationships with rating.

This is an illustrative baseline generated for this appendix, not an independently evaluated alternative implementation.

It supports basic collaborative recommendation queries, but does not explicitly represent genres or precomputed movie similarity.

### Comparison with the implemented model

| Design aspect | Minimal baseline | CineGraph |
|---|---|---|
| Genres | List property on Movie | Shared Genre nodes and IN_GENRE relationships |
| Audience similarity | Computed during retrieval | GDS-derived SIMILAR_TO links |
| Interaction information | Rating value | Rating value and source timestamp |
| Centrality | Not represented | Derived PageRank property |
| Communities | Not represented | Derived Louvain communityId |
| Integrity | No constraints specified | Three uniqueness constraints |
| Retrieval indexes | None specified | Constraint-backed ID indexes and title index |

### What makes the implementation specific?

The model is tied to concrete retrieval behavior:

- Positive interactions use ratings of at least 4.
- Personalized recommendations exclude every movie already rated by the target user.
- Supporting viewers must share at least three positive ratings.
- The recommendation score aggregates shared-like counts from up to 20 supporting users.
- Similarity uses Jaccard audience overlap with explicit degree, score, and top-K thresholds.
- Explanations expose the supporting users and shared movie examples.
- Community discovery combines liked-community counts with PageRank.

These decisions determine how the application behaves. They are more specific than naming generic entities and relationships.

## Tradeoffs and boundaries

- Stored top-K similarity links can be directed even though Jaccard similarity is symmetric.
- PageRank runs on that directed network.
- Louvain uses a separate undirected projection.
- Movies with insufficient positive ratings may have no similarity links or community assignment.
- Community discovery can favor one community rather than guarantee diversity.
- The separate ML evaluation constructs its features from a partial graph to keep held-out links out of the feature calculations.
- The current model represents one imported rating per user–movie pair; it is not a rating-event history.