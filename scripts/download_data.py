"""Download MovieLens small without replacing existing data."""

from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "ml-latest-small"
URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
FILES = ("movies.csv", "ratings.csv", "tags.csv", "links.csv", "README.txt")


def main():
    """Fetch missing dataset files from the official archive."""
    missing = [name for name in FILES if not (DATA_DIR / name).exists()]

    if not missing:
        print("MovieLens data already exists. Nothing downloaded.")
        return

    print("Downloading MovieLens small...")
    with urlopen(URL, timeout=60) as response:
        archive_bytes = response.read()

    with ZipFile(BytesIO(archive_bytes)) as archive:
        # Read only explicit filenames rather than extracting arbitrary paths.
        contents = {
            name: archive.read(f"ml-latest-small/{name}")
            for name in missing
        }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in contents.items():
        (DATA_DIR / name).write_bytes(content)
        print(f"Saved: {name}")

    print(f"Dataset ready: {DATA_DIR}")


if __name__ == "__main__":
    main()
