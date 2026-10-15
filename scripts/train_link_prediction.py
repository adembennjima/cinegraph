"""Evaluate hidden user-movie links using a separate training graph."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler, normalize


ROOT = Path(__file__).resolve().parents[1]
SEED = 42


def sample_negatives(users, movie_count, excluded, rng):
    """Sample one distinct unrated movie per supplied user."""
    pairs = []

    for user in users:
        user = int(user)
        while True:
            movie = int(rng.integers(movie_count))
            pair = (user, movie)
            if pair not in excluded:
                excluded.add(pair)
                pairs.append(pair)
                break

    return np.asarray(pairs, dtype=int)


def make_features(pairs, graph, genre_matrix, path_counts):
    """Compute features exclusively from the fixed training graph."""
    users = pairs[:, 0]
    movies = pairs[:, 1]

    user_degree = np.asarray(graph.sum(axis=1)).ravel()
    movie_degree = np.asarray(graph.sum(axis=0)).ravel()

    # Genre profiles contain only movies liked in the training graph.
    user_profiles = normalize(graph @ genre_matrix)
    movie_profiles = normalize(genre_matrix)
    genre_affinity = np.asarray(
        user_profiles[users]
        .multiply(movie_profiles[movies])
        .sum(axis=1)
    ).ravel()

    # Paths: user -> liked movie -> other user -> candidate movie.
    paths = np.asarray(path_counts[users, movies]).ravel()

    return np.column_stack(
        [
            np.log1p(user_degree[users]),
            np.log1p(movie_degree[movies]),
            genre_affinity,
            np.log1p(paths),
        ]
    )


def evaluate(labels, scores):
    """Calculate ranking metrics on the held-out candidate pairs."""
    return {
        "roc_auc": float(roc_auc_score(labels, scores)),
        "average_precision": float(
            average_precision_score(labels, scores)
        ),
    }


def main():
    """Build the graph, fit the model, and save test metrics."""
    rng = np.random.default_rng(SEED)
    data_dir = ROOT / "data" / "ml-latest-small"

    ratings = pd.read_csv(data_dir / "ratings.csv")
    movies = pd.read_csv(data_dir / "movies.csv")

    user_ids = sorted(ratings["userId"].unique())
    movie_ids = movies["movieId"].tolist()

    user_index = {
        user_id: index for index, user_id in enumerate(user_ids)
    }
    movie_index = {
        movie_id: index for index, movie_id in enumerate(movie_ids)
    }

    ratings["u"] = ratings["userId"].map(user_index)
    ratings["m"] = ratings["movieId"].map(movie_index)

    positives = ratings.loc[
        ratings["rating"] >= 4, ["u", "m"]
    ].to_numpy(dtype=int)

    positives = positives[rng.permutation(len(positives))]
    first_cut = int(len(positives) * 0.6)
    second_cut = int(len(positives) * 0.8)

    graph_pairs = positives[:first_cut]
    train_positive = positives[first_cut:second_cut]
    test_positive = positives[second_cut:]

    # No supervised training or test link enters the feature graph.
    graph_set = set(map(tuple, graph_pairs))
    assert graph_set.isdisjoint(map(tuple, train_positive))
    assert graph_set.isdisjoint(map(tuple, test_positive))

    graph = csr_matrix(
        (
            np.ones(len(graph_pairs), dtype=np.float64),
            (graph_pairs[:, 0], graph_pairs[:, 1]),
        ),
        shape=(len(user_ids), len(movie_ids)),
    )

    # Use all recorded ratings only to avoid sampling known
    # interactions as negatives. They do not enter graph features.
    excluded = set(
        map(tuple, ratings[["u", "m"]].to_numpy(dtype=int))
    )

    train_negative = sample_negatives(
        train_positive[:, 0], len(movie_ids), excluded, rng
    )
    test_negative = sample_negatives(
        test_positive[:, 0], len(movie_ids), excluded, rng
    )

    train_pairs = np.vstack([train_positive, train_negative])
    test_pairs = np.vstack([test_positive, test_negative])

    train_labels = np.concatenate(
        [np.ones(len(train_positive)), np.zeros(len(train_negative))]
    )
    test_labels = np.concatenate(
        [np.ones(len(test_positive)), np.zeros(len(test_negative))]
    )

    assert set(map(tuple, train_pairs)).isdisjoint(
        map(tuple, test_pairs)
    )

    genre_lists = [
        [
            genre for genre in value.split("|")
            if genre != "(no genres listed)"
        ]
        for value in movies["genres"]
    ]
    genre_names = sorted(
        {genre for genres in genre_lists for genre in genres}
    )
    genre_index = {
        genre: index for index, genre in enumerate(genre_names)
    }

    genre_rows = []
    genre_columns = []
    for movie, genres in enumerate(genre_lists):
        for genre in genres:
            genre_rows.append(movie)
            genre_columns.append(genre_index[genre])

    genre_matrix = csr_matrix(
        (
            np.ones(len(genre_rows)),
            (genre_rows, genre_columns),
        ),
        shape=(len(movie_ids), len(genre_names)),
    )

    print(f"Feature graph: {len(graph_pairs):,} likes")
    print(f"Training examples: {len(train_pairs):,}")
    print(f"Test examples: {len(test_pairs):,}")
    print("Computing graph features...")

    shared_likes = graph @ graph.T
    shared_likes.setdiag(0)
    shared_likes.eliminate_zeros()
    path_counts = shared_likes @ graph

    train_features = make_features(
        train_pairs, graph, genre_matrix, path_counts
    )
    test_features = make_features(
        test_pairs, graph, genre_matrix, path_counts
    )

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, random_state=SEED),
    )
    model.fit(train_features, train_labels)
    predicted_scores = model.predict_proba(test_features)[:, 1]

    # Feature column 1 is log-transformed movie popularity.
    baseline_scores = test_features[:, 1]

    report = {
        "seed": SEED,
        "task": "Hidden positive-link recovery",
        "split": "60% feature graph / 20% training / 20% test",
        "graph_likes": len(graph_pairs),
        "training_examples": len(train_pairs),
        "test_examples": len(test_pairs),
        "negative_sampling": (
            "One unique unrated pair per positive; "
            "same user distribution in both classes"
        ),
        "features": [
            "user_like_degree",
            "movie_like_degree",
            "genre_affinity",
            "three_hop_path_count",
        ],
        "popularity_baseline": evaluate(
            test_labels, baseline_scores
        ),
        "logistic_regression": evaluate(
            test_labels, predicted_scores
        ),
        "limitations": [
            "Unrated movies are not confirmed dislikes.",
            "Random edge split does not measure future behavior.",
            "Balanced sampled candidates do not represent "
            "the full movie catalog.",
            "This experiment does not replace the API recommender.",
        ],
    }

    output_dir = ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "link_prediction_metrics.json"
    output_file.write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("\nHeld-out test results:")
    for name in ("popularity_baseline", "logistic_regression"):
        metrics = report[name]
        print(
            f"{name}: ROC-AUC={metrics['roc_auc']:.4f}, "
            f"AP={metrics['average_precision']:.4f}"
        )

    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
