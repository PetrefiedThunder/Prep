.PHONY: run-% test format lint

run-%:
uvicorn apps.$*/main:app --reload

test:
pytest

format:
ruff format .

lint:
ruff check .
