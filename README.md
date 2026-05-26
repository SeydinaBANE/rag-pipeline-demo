# rag-pipeline-demo

Pipeline RAG industrialisé — 100 % local en dev, déployable AWS en prod.

Construit pour démontrer les pratiques senior : hybrid search, reranking,
multi-tenancy, évaluation RAGAS, A/B testing, observabilité LangFuse, CDK, CI/CD.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Next.js 14  (port 3001)                                            │
│  Chat · Documents · Analytics · Feedback                            │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────────────┐
│  FastAPI  (port 8000)                                               │
│  JWT auth · Rate limit · /query · /ingest · /feedback · /metrics   │
└──────┬─────────────┬──────────────────────┬──────────────┬──────────┘
       │             │                      │              │
  ┌────▼────┐  ┌─────▼──────┐  ┌───────────▼───┐  ┌──────▼──────┐
  │Retrieval│  │ Generation │  │  Observability│  │   Workers   │
  │BM25+vec │  │LCEL chain  │  │Prometheus     │  │SQS consumer │
  │RRF+rerank│ │Prompts v1/2│  │LangFuse       │  │(Fargate)    │
  │Sem.cache│  │Guardrails  │  │QueryTracker   │  └─────────────┘
  └────┬────┘  └────────────┘  └───────────────┘
       │
  ┌────▼───────────────────────────────────────┐
  │  ChromaDB (dev)  /  pgvector + RDS (prod)  │
  │  Redis semantic cache                      │
  └────────────────────────────────────────────┘
```

---

## Stack

| Couche         | Dev                          | Prod                        |
|----------------|------------------------------|-----------------------------|
| LLM            | Ollama Mistral 7B Instruct   | AWS Bedrock                 |
| Embedding      | Ollama nomic-embed-text      | AWS Bedrock                 |
| Vector store   | ChromaDB                     | RDS PostgreSQL 15 + pgvector|
| Cache          | Redis local                  | ElastiCache Redis 7         |
| Backend        | FastAPI + uvicorn            | ECS Fargate (ALB)           |
| Worker         | Python process               | ECS Fargate + SQS           |
| Frontend       | Next.js 14 dev server        | CloudFront + ECS            |
| Observabilité  | LangFuse local + Prometheus  | LangFuse cloud + CloudWatch |
| Infra          | Docker Compose               | AWS CDK (4 stacks)          |
| CI/CD          | pre-commit                   | GitHub Actions (OIDC)       |

---

## Démarrage rapide

### Prérequis

- Python 3.11+
- Docker + Docker Compose
- Node.js 20+ (frontend)
- Ollama (optionnel — téléchargé automatiquement via Docker)

### Installation

```bash
# 1. Cloner et créer l'environnement Python
make install

# 2. Copier la configuration
cp .env.example .env          # ajuster les valeurs si besoin

# 3. Démarrer la stack locale (Ollama + Chroma + Redis + LangFuse)
make docker-up
# Les modèles Ollama se téléchargent au premier démarrage (~5 GB)

# 4. Indexer les documents d'exemple
make index

# 5. Lancer l'API
make api
# → http://localhost:8000/docs

# 6. Lancer le frontend
make frontend-install && make frontend-dev
# → http://localhost:3001
```

### Services disponibles en local

| Service        | URL                          |
|----------------|------------------------------|
| API FastAPI    | http://localhost:8000        |
| API Docs       | http://localhost:8000/docs   |
| Prometheus     | http://localhost:8000/metrics|
| Frontend       | http://localhost:3001        |
| Streamlit démo | http://localhost:8501        |
| LangFuse       | http://localhost:3000        |
| ChromaDB       | http://localhost:8001        |
| Ollama         | http://localhost:11434       |
| Redis          | localhost:6379               |

---

## Commandes make

```bash
# Setup
make install          # venv + dépendances + hooks pre-commit

# Développement
make api              # FastAPI hot-reload (port 8000)
make docker-up        # Stack complète en arrière-plan
make docker-down      # Arrêter tous les conteneurs

# Tests
make test             # unit + integration
make test-unit        # uniquement les tests unitaires
make test-integration # tests d'intégration (nécessite docker-up)
make test-smoke       # smoke tests post-deploy

# Qualité
make lint             # ruff + mypy
make lint-fix         # correction automatique
make audit            # pip-audit + detect-secrets

# Évaluation
make eval             # RAGAS sur golden dataset (data/eval/)
make ab-report        # rapport A/B testing

# Load testing
make load-test        # Locust avec UI
make load-test-headless  # Locust headless (CI)

# Indexation
make index            # ingère data/docs/
make index-reset      # reset + ré-indexe

# Frontend
make frontend-install # npm install
make frontend-dev     # Next.js dev (port 3001)
make frontend-build   # build production
make frontend-test    # Vitest
make frontend-e2e     # Playwright

# Infrastructure
make infra-diff       # cdk diff staging
make infra-deploy     # cdk deploy staging

# Maintenance
make clean            # caches + artefacts temporaires
make clean-all        # + venv + volumes Docker
```

---

## API

```
POST /api/v1/query          Requête RAG (JSON)
POST /api/v1/query/stream   Requête RAG en streaming SSE
POST /api/v1/ingest/upload  Upload de fichier (multipart)
POST /api/v1/feedback       Feedback utilisateur (rating 1/-1)
GET  /health                Health check
GET  /metrics               Métriques Prometheus
GET  /docs                  Swagger UI
```

Toutes les routes (sauf `/health` et `/metrics`) nécessitent un Bearer JWT.

### Générer un token de test

```python
from jose import jwt
token = jwt.encode(
    {"sub": "user-1", "tenant_id": "acme"},
    "change-me-in-production",
    algorithm="HS256",
)
```

---

## Structure du projet

```
src/
├── config.py               # Source de vérité de toute la config (Pydantic Settings)
├── ingestion/              # Loaders → dedup → PII filter → versioning
├── chunking/               # fixed | semantic | parent_child (défaut)
├── embedding/              # OllamaEmbeddings + batch
├── vectorstore/            # Chroma (dev) / pgvector (prod)
├── retrieval/              # hybrid BM25+vector → RRF → reranker → semantic cache
├── generation/             # LCEL chain → prompts versionnés → guardrails
├── evaluation/             # RAGAS + experiment tracking + feedback loop
├── ab_testing/             # Router trafic SHA-256 sticky + impression/conversion
├── analytics/              # Prometheus metrics + QueryTracker JSONL + LangFuse
├── api/                    # FastAPI : routes + auth JWT + rate limit + schemas
└── workers/                # SQS consumer pour indexation asynchrone

cdk/
├── app.py                  # Point d'entrée CDK
└── stacks/
    ├── vpc_stack.py        # VPC 2-AZ + flow logs
    ├── data_stack.py       # RDS + ElastiCache + SQS + DLQ
    ├── security_stack.py   # WAF + Secrets Manager
    └── compute_stack.py    # ECR + ECS Fargate API + Worker

frontend/
├── app/                    # Next.js App Router
│   ├── chat/               # Interface de chat + sources + feedback thumbs
│   ├── documents/          # Upload drag-and-drop
│   ├── analytics/          # Health + métriques Prometheus
│   └── feedback/           # Historique des ratings
├── components/             # Sidebar, MessageBubble, QueryInput, SourceCard…
├── hooks/useChat.ts        # État du chat + sendMessage + sendFeedback
└── lib/api.ts              # Client API (queryRAG, streamQuery, ingestFile…)

.github/workflows/
├── ci.yml                  # Lint + tests + coverage (chaque push)
├── eval.yml                # RAGAS hebdo + sur changements évaluation
├── cd-staging.yml          # Build ECR + deploy ECS (push main, OIDC)
├── cd-prod.yml             # Promotion image + deploy prod (tag v*, approbation manuelle)
└── load-test.yml           # Locust headless (hebdo + déclenchement manuel)

tests/
├── unit/                   # Tests unitaires (fakeredis, mocks)
├── integration/            # Tests pipeline complet (Chroma local)
├── smoke/                  # Smoke tests post-deploy
└── load/locustfile.py      # Scénarios Locust (RAGUser)
```

---

## Déploiement AWS

### Prérequis

- AWS CLI configuré + CDK installé (`npm install -g aws-cdk`)
- Compte AWS avec permissions CloudFormation, ECS, RDS, ElastiCache, SQS, WAF

```bash
# Installer les dépendances CDK
pip install -r cdk/requirements.txt

# Premier déploiement (bootstrap si nécessaire)
cdk bootstrap aws://ACCOUNT_ID/us-east-1 --app "python3 cdk/app.py"

# Déployer toutes les stacks
CDK_ACCOUNT=123456789012 CDK_REGION=us-east-1 \
  cdk deploy --all --app "python3 cdk/app.py" --require-approval broadening
```

Les stacks se déploient dans l'ordre de dépendance :
`RagVpc` → `RagData` + `RagSecurity` → `RagCompute`

### Après le déploiement

1. Activer l'extension pgvector sur RDS :
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Mettre à jour les secrets LangFuse dans Secrets Manager
3. Configurer GitHub OIDC + IAM roles pour CI/CD (voir `.github/workflows/`)

---

## Évaluation RAGAS

Le dataset golden (`data/eval/golden_dataset.jsonl`) contient 7 paires Q/R de référence.

```bash
make eval   # lance l'évaluation complète
```

Métriques calculées : `faithfulness`, `answer_relevancy`, `context_precision`.
Les résultats sont sauvegardés dans `data/experiments/` au format JSON.

---

## Documentation

| Fichier | Contenu |
|---------|---------|
| [`CLAUDE.md`](CLAUDE.md) | Contexte et conventions pour Claude Code |
| [`docs/adr/`](docs/adr/) | Décisions d'architecture (ADR 001–008) |
| [`TODO.md`](TODO.md) | Suivi des phases de développement |
| `http://localhost:8000/docs` | Documentation API interactive (Swagger) |
