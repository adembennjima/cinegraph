"""Validate AI-generated Cypher against approved read queries."""

from app.movies import SIMILAR_MOVIES_QUERY
from app.recommendations import RECOMMENDATIONS_QUERY


APPROVED_QUERIES = {
    "recommendations": RECOMMENDATIONS_QUERY,
    "similar_movies": SIMILAR_MOVIES_QUERY,
}

IDENTIFIER_PARAMETERS = {
    "recommendations": "user_id",
    "similar_movies": "movie_id",
}


def normalize_query(query: str) -> str:
    """Normalize whitespace for comparison."""
    return " ".join(query.split())


def validate_query(
    cypher: str,
    parameters: dict,
) -> tuple[str, str, dict[str, int]]:
    """Return an approved query and parameters, or reject the request."""
    for name, approved in APPROVED_QUERIES.items():
        if normalize_query(cypher) != normalize_query(approved):
            continue

        identifier = IDENTIFIER_PARAMETERS[name]
        expected = {identifier, "limit"}

        if set(parameters) != expected:
            raise ValueError("Missing or unexpected query parameters.")

        identifier_value = parameters[identifier]
        limit = parameters["limit"]

        if type(identifier_value) is not int or identifier_value < 1:
            raise ValueError("The identifier must be a positive integer.")

        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("The limit must be between 1 and 10.")

        return name, approved, parameters.copy()

    raise ValueError("The generated query is not approved.")