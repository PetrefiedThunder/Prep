.PHONY: run-% test format lint setup policy.build opa.up db.migrate codex-verify etl.validate

run-%:
	uvicorn apps.$*/main:app --reload

test:
	pytest -q || (docker logs prep-opa; exit 1)

format:
	ruff format .

lint:
	ruff check .

setup:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pip install pytest requests pydantic sqlalchemy psycopg2-binary opentelemetry-sdk

policy.build:
	python apps/policy/compile.py

opa.up:
	docker run --rm -d --name prep-opa -p 8181:8181 -v "$(PWD)/apps/policy/bundles:/policy" openpolicyagent/opa:latest run --server /policy

db.migrate:
	alembic upgrade head

codex-verify:
	python codex/eval/verify_readiness.py

etl.validate:
	python tools/fee_validate.py
