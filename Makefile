PYTHON=python
PACKAGE=sim_racecenter_agent

.PHONY: init-db run-mcp test format lint type dev

init-db:
	$(PYTHON) scripts/init_db.py

run-mcp:
	$(PYTHON) scripts/run_mcp.py

test:
	pytest

format:
	ruff format .
	ruff check . --fix
	isort .

lint:
	ruff check .
	mypy $(PACKAGE)

type:
	mypy $(PACKAGE)

dev: run-mcp