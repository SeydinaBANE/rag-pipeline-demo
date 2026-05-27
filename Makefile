.PHONY: help install run api docker-up docker-down test test-smoke test-unit test-integration \
        load-test eval ab-report index lint audit infra-diff infra-deploy \
        backup-check cost-report clean frontend-install frontend-dev frontend-build \
        frontend-test frontend-e2e frontend-lint

VENV       := .venv
PYTHON     := $(VENV)/bin/python
PIP        := $(VENV)/bin/pip
PYTEST     := $(VENV)/bin/pytest
RUFF       := $(VENV)/bin/ruff
MYPY       := $(VENV)/bin/mypy

help:  ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────────────
install:  ## Crée le venv, installe les dépendances et les hooks pre-commit
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	$(VENV)/bin/pre-commit install
	@echo "✓ Installation terminée. Active le venv : source $(VENV)/bin/activate"

# ── Run ──────────────────────────────────────────────────────────────────────
run:  ## Lance l'interface Streamlit (démo locale)
	$(VENV)/bin/streamlit run app.py

api:  ## Lance le serveur FastAPI en dev (hot-reload)
	$(VENV)/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir src

# ── Docker ───────────────────────────────────────────────────────────────────
docker-up:  ## Démarre la stack locale complète (Ollama + Chroma + Redis + LangFuse + API)
	docker compose up -d
	@echo "Services disponibles :"
	@echo "  API        → http://localhost:8000"
	@echo "  Streamlit  → http://localhost:8501"
	@echo "  LangFuse   → http://localhost:3000"
	@echo "  Chroma     → http://localhost:8001"

docker-down:  ## Arrête tous les services
	docker compose down

docker-logs:  ## Affiche les logs de tous les services
	docker compose logs -f

docker-rebuild:  ## Rebuild les images et redémarre
	docker compose up -d --build

# ── Tests ────────────────────────────────────────────────────────────────────
test:  ## Lance tous les tests (unit + integration)
	$(PYTEST) tests/unit tests/integration

test-unit:  ## Lance uniquement les tests unitaires
	$(PYTEST) tests/unit -v

test-integration:  ## Lance les tests d'intégration (nécessite docker-up)
	$(PYTEST) tests/integration -v

test-smoke:  ## Tests post-deploy (smoke tests)
	$(PYTEST) tests/smoke -v

test-cov:  ## Tests avec rapport de couverture HTML
	$(PYTEST) tests/unit tests/integration --cov-report=html
	@echo "Rapport disponible : htmlcov/index.html"

# ── Load testing ─────────────────────────────────────────────────────────────
load-test:  ## Lance Locust contre l'API locale
	$(VENV)/bin/locust -f tests/load/locustfile.py --host http://localhost:8000

load-test-headless:  ## Load test sans UI (CI)
	$(VENV)/bin/locust -f tests/load/locustfile.py \
		--host http://localhost:8000 \
		--headless -u 50 -r 5 -t 60s \
		--html tests/load/report.html

# ── Évaluation & A/B ─────────────────────────────────────────────────────────
eval:  ## Lance l'évaluation RAGAS sur le golden dataset
	$(PYTHON) -m src.evaluation.ragas_eval

ab-report:  ## Affiche le rapport A/B des dernières expériences
	$(PYTHON) -m src.ab_testing.router --report

# ── Indexation ───────────────────────────────────────────────────────────────
index:  ## Ingère et indexe les documents dans data/docs/
	$(PYTHON) -m scripts.index_documents

index-reset:  ## Réinitialise le vector store et ré-indexe
	$(PYTHON) -m scripts.index_documents --reset

# ── Qualité de code ───────────────────────────────────────────────────────────
lint:  ## Lint (ruff) + type checking (mypy)
	$(RUFF) check src tests
	$(RUFF) format --check src tests
	$(MYPY) src

lint-fix:  ## Corrige automatiquement les erreurs de lint
	$(RUFF) check --fix src tests
	$(RUFF) format src tests

audit:  ## Audit sécurité (pip-audit + detect-secrets)
	$(VENV)/bin/pip-audit -r requirements.txt
	$(VENV)/bin/detect-secrets scan > .secrets.baseline

# ── Infrastructure AWS ────────────────────────────────────────────────────────
infra-diff:  ## Affiche le diff CDK (staging)
	cd infra && $(VENV)/bin/cdk diff --profile staging

infra-deploy:  ## Deploy l'infrastructure sur staging
	cd infra && $(VENV)/bin/cdk deploy --profile staging --require-approval broadening

# ── Monitoring ────────────────────────────────────────────────────────────────
backup-check:  ## Vérifie la dernière backup pgvector
	@aws rds describe-db-snapshots \
		--query 'DBSnapshots[-1].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
		--output table 2>/dev/null || echo "AWS non configuré"

cost-report:  ## Coût du jour par tenant (nécessite docker-up + LangFuse)
	$(PYTHON) -m src.analytics.query_tracker --cost-report

# ── Frontend Next.js ──────────────────────────────────────────────────────────
frontend-install:  ## Installe les dépendances Node.js
	cd frontend && npm install

frontend-dev:  ## Lance le serveur Next.js en dev
	cd frontend && npm run dev

frontend-build:  ## Build Next.js pour la production
	cd frontend && npm run build

frontend-test:  ## Lance les tests Vitest
	cd frontend && npm run test

frontend-e2e:  ## Lance les tests Playwright E2E
	cd frontend && npx playwright test

frontend-lint:  ## Lint ESLint + Prettier
	cd frontend && npm run lint

# ── Nettoyage ─────────────────────────────────────────────────────────────────
clean:  ## Supprime les fichiers temporaires et caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml .coverage
	rm -rf .chroma
	@echo "✓ Nettoyage terminé"

clean-all: clean  ## Supprime aussi le venv et les données Docker
	rm -rf $(VENV)
	docker compose down -v
	@echo "✓ Nettoyage complet terminé"
