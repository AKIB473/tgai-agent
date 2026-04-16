.PHONY: install dev lint fmt test cov clean docker-build docker-up

# ── Setup ──────────────────────────────────────────────────────────────────────
install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install
	@echo "✅ Dev environment ready"

# ── Quality ────────────────────────────────────────────────────────────────────
lint:
	ruff check src/ tests/
	mypy src/

fmt:
	black src/ tests/
	ruff check --fix src/ tests/

# ── Tests ──────────────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

cov:
	pytest tests/ --cov=src/tgai_agent --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"


# ── Docker ─────────────────────────────────────────────────────────────────────
docker-build:
	docker build -t tgai-agent:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# ── Database ───────────────────────────────────────────────────────────────────
init-db:
	tgai-agent --init-db

# ── Cleanup ────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	rm -rf dist/ build/ .eggs/ *.egg-info/ htmlcov/ .coverage coverage.xml .pytest_cache/
	@echo "✅ Cleaned"
