"""Inspect the MovieLens dataset before importing it."""

from pathlib import Path

import pandas as pd


def main() -> None:
    """Display dataset counts and check for invalid records."""
    data_dir = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "ml-latest-small"
    )

    movies = pd.read_csv(data_dir / "movies.csv")
    ratings = pd.read_csv(data_dir / "ratings.csv")

    print(f"Movies: {len(movies):,}")
    print(f"Ratings: {len(ratings):,}")
    print(f"Users: {ratings['userId'].nunique():,}")

    print("\nFirst 5 movies:")
    print(movies.head().to_string(index=False))

    print("\nData checks:")
    print(f"Missing movie values: {movies.isna().sum().sum()}")
    print(f"Missing rating values: {ratings.isna().sum().sum()}")
    print(f"Duplicate movie IDs: {movies['movieId'].duplicated().sum()}")
    print(
        "Duplicate user/movie pairs:",
        ratings.duplicated(["userId", "movieId"]).sum(),
    )
    print(
        "Ratings referencing unknown movies:",
        (~ratings["movieId"].isin(movies["movieId"])).sum(),
    )
    print(
        f"Rating range: "
        f"{ratings['rating'].min()} to {ratings['rating'].max()}"
    )


if __name__ == "__main__":
    main()
