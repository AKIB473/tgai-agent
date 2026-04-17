.PHONY: install lint fmt test cov build clean run init-db

install:
	pip install -e ".[dev]"

lint:
	ruff check src/ tests/
	mypy src/

fmt:
	black src/ tests/
	ruff check --fix src/ tests/

test:
	pytest tests/ -v --tb=short

cov:
	pytest tests/ --cov=src/tgai_agent --cov-report=term-missing --cov-report=html

build:
	python -m build

clean:
	find . -type d -name __pycache__ | xargs rm -rf
	find . -type f -name "*.pyc" -delete
	rm -rf dist/ build/ *.egg-info .coverage htmlcov/

run:
	tgai-agent

init-db:
	tgai-agent --init-db
