"""Test question-to-Cypher generation without executing the query."""

from app.ai import generate_query


def main() -> None:
    """Generate and display one validated query."""
    name, cypher, parameters = generate_query(
        "Recommend 5 movies for user 1."
    )

    print(f"Approved query: {name}")
    print(f"Parameters: {parameters}")
    print("\nCypher:")
    print(cypher)


if __name__ == "__main__":
    main()
