.PHONY: install dev test lint format typecheck migrate revision seed docker-up docker-down db-up ci docker-build dashboard

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app/

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python -m scripts.seed_db

docker-up:
	docker compose up -d

docker-down:
	docker compose down

db-up:
	docker compose up -d postgres redis

ci:
	ruff check . && mypy app/ && pytest -v

docker-build:
	docker build -t multi-model-router:latest .

dashboard:
	streamlit run dashboard/app.py --server.port 8501
