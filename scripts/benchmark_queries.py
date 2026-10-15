"""Compare equivalent scan and indexed movie lookups."""

import json
from pathlib import Path
from statistics import median
from time import perf_counter

from neo4j import GraphDatabase

from app.config import Settings


ROOT = Path(__file__).resolve().parents[1]
REPEATS = 20

SCAN_QUERY = """
MATCH (m:Movie)
USING SCAN m:Movie
WHERE m.movieId = $movie_id
RETURN m.movieId AS movieId, m.title AS title
LIMIT $limit
"""

INDEX_QUERY = """
MATCH (m:Movie)
USING INDEX m:Movie(movieId)
WHERE m.movieId = $movie_id
RETURN m.movieId AS movieId, m.title AS title
LIMIT $limit
"""


def execute_query(session, query, parameters):
    """Execute and fully consume a query, measuring client elapsed time."""
    started = perf_counter()
    result = session.run(query, parameters)
    rows = [record.data() for record in result]
    result.consume()
    elapsed_ms = (perf_counter() - started) * 1000
    return rows, elapsed_ms


def total_db_hits(plan):
    """Sum database hits across all operators in a profiled plan."""
    return int(plan.get("dbHits", 0)) + sum(
        total_db_hits(child) for child in plan.get("children", [])
    )


def operator_names(plan):
    """Collect operator names from a query plan."""
    names = [plan.get("operatorType", "unknown")]
    for child in plan.get("children", []):
        names.extend(operator_names(child))
    return names


def inspect_plan(session, query, parameters):
    """Capture EXPLAIN and PROFILE information separately from timing."""
    explained = session.run("EXPLAIN " + query, parameters)
    explain_summary = explained.consume()

    profiled = session.run("PROFILE " + query, parameters)
    rows = [record.data() for record in profiled]
    profile_summary = profiled.consume()

    return {
        "rows": rows,
        "explain_operators": operator_names(explain_summary.plan),
        "profile_operators": operator_names(profile_summary.profile),
        "total_db_hits": total_db_hits(profile_summary.profile),
        "profile": profile_summary.profile,
    }


def benchmark(session):
    """Compare identical results over alternating warmed executions."""
    queries = {"scan": SCAN_QUERY, "index": INDEX_QUERY}
    parameters = {"movie_id": 999999999, "limit": 1}

    expected, _ = execute_query(session, INDEX_QUERY, parameters)
    movie_count = session.run(
        "MATCH (m:Movie) RETURN count(m) AS count"
    ).single()["count"]
    if movie_count == 0:
        raise RuntimeError("Import MovieLens before benchmarking.")
    if expected:
        raise RuntimeError("Choose a movie ID absent from the dataset.")

    # Warm both execution plans and database caches.
    for _ in range(3):
        for query in queries.values():
            rows, _ = execute_query(session, query, parameters)
            if rows != expected:
                raise RuntimeError("The queries returned different results.")

    timings = {"scan": [], "index": []}

    # Alternate order to reduce a consistent first-query advantage.
    for iteration in range(REPEATS):
        order = ("scan", "index") if iteration % 2 == 0 else ("index", "scan")
        for name in order:
            rows, elapsed = execute_query(
                session, queries[name], parameters
            )
            if rows != expected:
                raise RuntimeError("The queries returned different results.")
            timings[name].append(elapsed)

    measurements = {}
    for name, query in queries.items():
        plan = inspect_plan(session, query, parameters)
        if plan["rows"] != expected:
            raise RuntimeError("The profiled query returned different results.")

        measurements[name] = {
            "query": query.strip(),
            "median_elapsed_ms": median(timings[name]),
            "min_elapsed_ms": min(timings[name]),
            "max_elapsed_ms": max(timings[name]),
            "samples_ms": timings[name],
            **plan,
        }

    return {
        "experiment": "Forced label scan versus existing movieId index",
        "parameters": parameters,
        "repeats_per_query": REPEATS,
        "identical_results": True,
        "measurements": measurements,
        "limitations": [
            "Both queries run against the same already-indexed database.",
            "The scan hint simulates lookup without using that index.",
            "Warm-cache client timings include driver and network overhead.",
            "This small lookup does not measure whole-app performance.",
        ],
    }


def main():
    """Run the benchmark and save its timings and execution plans."""
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
            report = benchmark(session)

    output_dir = ROOT / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "query_benchmark.json"
    output_file.write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("Both queries returned identical results.")
    for name, measurement in report["measurements"].items():
        print(
            f"{name}: median={measurement['median_elapsed_ms']:.3f} ms, "
            f"DB hits={measurement['total_db_hits']}"
        )
        print("Operators:", ", ".join(measurement["profile_operators"]))

    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    main()
