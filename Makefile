.PHONY: test lint run-ingest run-thinking init-db

test:
	PYTHONPATH=src python -m pytest -q

run-ingest:
	PYTHONPATH=src python -m assistant.interfaces.cli.app ingest "Call Sarah about the Q3 budget next Monday"

run-thinking:
	PYTHONPATH=src python -m assistant.interfaces.cli.app thinking-run

init-db:
	PYTHONPATH=src python scripts/init_db.py
