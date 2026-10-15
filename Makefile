.DEFAULT_GOAL := help
PYTHON ?= python

.PHONY: help install run docker-run docker-stop test lint ml clean

help:
	@echo "make setup-data   Download, import and build the graph"
	@echo "make benchmark    Compare scan and index performance"
	@echo "make install      Install Python dependencies"
	@echo "make run          Run FastAPI locally"
	@echo "make docker-run   Build and start all three services"
	@echo "make docker-stop  Stop the Docker services"
	@echo "make test         Run tests with backend coverage"
	@echo "make lint         Check Python code quality"
	@echo "make ml           Run the link-prediction experiment"
	@echo "make clean        Remove generated Python caches and coverage"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.main:app --reload

docker-run:
	docker compose build api
	docker compose up -d

docker-stop:
	docker compose stop

test:
	$(PYTHON) -m pytest tests --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=60

lint:
	$(PYTHON) -m pylint app scripts ui --fail-under=9.5

ml:
	$(PYTHON) -m scripts.train_link_prediction

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; roots = [Path(p) for p in ('app', 'scripts', 'ui', 'tests')]; [shutil.rmtree(p) for root in roots for p in root.rglob('__pycache__')]; [shutil.rmtree(p) for p in (Path('.pytest_cache'), Path('htmlcov')) if p.exists()]; Path('.coverage').unlink(missing_ok=True)"

.PHONY: setup-data benchmark

setup-data:
	$(PYTHON) -m scripts.download_data
	$(PYTHON) -m scripts.create_schema
	$(PYTHON) -m scripts.import_movies
	$(PYTHON) -m scripts.import_ratings
	$(PYTHON) -m scripts.build_similarity
	$(PYTHON) -m scripts.build_rankings
	$(PYTHON) -m scripts.build_communities

benchmark:
	$(PYTHON) -m scripts.benchmark_queries
