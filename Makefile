PYTHON=python
PACKAGE=sim_racecenter_agent

.PHONY: init-db agent chat-responder test format lint type

init-db:
	$(PYTHON) scripts/init_db.py

agent:
	$(PYTHON) scripts/run_agent.py

chat-responder:
	$(PYTHON) scripts/respond_chat.py

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
