# rag-pipeline-demo — Contexte projet pour Claude Code

## Vue d'ensemble
Pipeline RAG industrialisé, 100% local en dev (Ollama + Chroma), déployable sur AWS en prod.
Construit pour démontrer les pratiques senior : hybrid search, reranking, multi-tenancy,
évaluation RAGAS, A/B testing, observabilité LangFuse.

## Stack technique
| Couche | Dev | Prod |
|---|---|---|
| LLM | Ollama Mistral 7B Instruct | AWS Bedrock |
| Embedding | Ollama nomic-embed-text (768 dim) | AWS Bedrock |
| Vector store | ChromaDB | RDS PostgreSQL 15 + pgvector |
| Cache | Redis local | ElastiCache Redis 7 |
| Backend | FastAPI + uvicorn | ECS Fargate (ALB) |
| Worker | Python process | ECS Fargate + SQS |
| Frontend | Next.js 14 dev server | CloudFront + ECS |
| Observabilité | LangFuse local + Prometheus | LangFuse cloud + CloudWatch |
| Infra | Docker Compose | AWS CDK (4 stacks) |

## Commandes essentielles
```bash
# Setup
make install              # venv + pip + hooks pre-commit
cp .env.example .env      # puis ajuster au besoin

# Dev
make docker-up            # démarre Ollama + Chroma + Redis + LangFuse
make api                  # FastAPI hot-reload → http://localhost:8000
make frontend-dev         # Next.js dev server → http://localhost:3001
make index                # ingère data/docs/ dans le vector store

# Tests
make test                 # unit + integration
make test-unit            # unit seulement (pas besoin de docker)
make test-integration     # nécessite docker-up
make test-cov             # rapport de couverture HTML (htmlcov/index.html)
.venv/bin/pytest tests/unit/test_chunking.py -v   # test fichier unique

# Qualité
make lint                 # ruff check + ruff format --check + mypy
make lint-fix             # correction automatique ruff

# Évaluation
make eval                 # RAGAS sur data/eval/golden_dataset.jsonl
make ab-report            # rapport A/B testing

# Frontend
make frontend-install     # npm install
make frontend-test        # Vitest
make frontend-lint        # ESLint + Prettier
```

## Architecture des modules
```
src/
├── config.py           # Source de vérité de toute la config (Pydantic Settings)
├── ingestion/          # Loaders → dédup SHA-256 → PII filter (Presidio) → versioning
├── chunking/           # fixed | semantic | parent_child (défaut)
├── embedding/          # OllamaEmbedder + batch (taille 32 par défaut)
├── vectorstore/        # Chroma (dev) / pgvector (prod) — interface BaseVectorStore commune
├── retrieval/          # hybrid BM25+vector → RRF (k=60) → reranker → semantic cache Redis
├── generation/         # LCEL chain → prompts versionnés (v1/v2) → guardrails I/O
├── evaluation/         # RAGAS (faithfulness, relevancy, precision) + ExperimentTracker + FeedbackStore
├── ab_testing/         # Router SHA-256 sticky + impressions/conversions par variant
├── analytics/          # Prometheus metrics + QueryTracker JSONL + LangFuseTracer
├── api/                # FastAPI : /query /ingest /feedback + JWT auth + rate limit sliding window
└── workers/            # SQS consumer + SIGTERM handling pour indexation async
```

### Pipeline d'exécution RAGChain (`src/generation/chain.py`)
Pour chaque requête : **InputGuardrail → SemanticCache (get) → QueryTransformer → HybridRetriever → Reranker → LLM → OutputGuardrail → SemanticCache (set)**

Points non-évidents :
- `RAGChain.stream()` ne lit **pas** le cache et n'écrit **pas** dans le cache.
- Les index BM25 sont **per-tenant, en mémoire, construits lazily** via `HybridRetriever.build_bm25_index()`. Ils sont perdus au redémarrage du processus.
- `get_settings()` et `get_rag_chain()` sont tous les deux `lru_cache(maxsize=1)`. Dans les tests : utiliser `app.dependency_overrides[get_rag_chain]` pour la chain, et `get_settings.cache_clear()` si les vars d'env changent entre les tests.
- Le reranker utilise le modèle `ms-marco-MiniLM-L-6-v2` (téléchargé à la première utilisation).

## Conventions
- **Config** : toujours via `get_settings()` depuis `src/config.py`. Jamais de valeurs hardcodées.
- **Interfaces** : chaque couche a une classe `Base*` abstraite. Swap de provider = changer l'implémentation, pas le code appelant.
- **Tenancy** : chaque requête porte un `tenant_id`. Le vector store isole par namespace Chroma / schéma pgvector.
- **Logging** : `structlog` uniquement, format JSON en prod. Pas de `print()`.
- **Async** : toutes les routes FastAPI et les accès DB/Redis sont async. Pas de `time.sleep()`.
- **Types** : mypy strict sur tout `src/`. Toute nouvelle fonction doit être entièrement annotée.
- **Tests** : mocks uniquement aux boundaries externes (Ollama, Redis, Chroma). Pas de mock interne.
- **Couverture** : seuil minimum 80% (`fail_under = 80` dans `pyproject.toml`). Un PR qui fait baisser la couverture en dessous sera rejeté par CI.
- **Secrets** : jamais dans le code. `.env` local, AWS Secrets Manager en prod.

## Fichiers clés
| Fichier | Rôle |
|---|---|
| `src/config.py` | Toute la configuration typée — 12 sous-modèles imbriqués |
| `src/api/deps.py` | Injection de dépendances FastAPI (Chain, CurrentUser, RateLimiter) |
| `config.yaml` | Valeurs par défaut (chargées avant le `.env`) |
| `.env.example` | Template variables d'environnement |
| `docker-compose.yml` | Stack dev complète |
| `Makefile` | Toutes les commandes du projet |
| `docs/adr/` | Décisions d'architecture justifiées (ADR 001–008) |
| `data/eval/golden_dataset.jsonl` | Dataset de référence RAGAS (7 paires Q/R) |

## Décisions d'architecture
Voir `docs/adr/` pour le détail. En résumé :
- **pgvector > Pinecone** : self-hosted, pas de vendor lock-in, SQL natif pour metadata filtering
- **Ollama > vLLM** en dev : zéro friction, pas besoin de GPU dédié
- **parent-child chunking** par défaut : petits chunks pour le retrieval, grands pour le contexte LLM
- **Async indexation (SQS)** : évite les timeouts HTTP sur les gros documents
- **Namespace isolation** pour multi-tenancy : plus simple que des DB séparées, assez sûr

## Variables d'environnement importantes
Format : double underscore `__` comme séparateur de section (ex. `LLM__BASE_URL`).
Copier `.env.example` → `.env` et ajuster :
- `API__SECRET_KEY` : obligatoire en prod (chaîne aléatoire longue)
- `LLM__BASE_URL` : `http://localhost:11434` en local, `http://ollama:11434` dans Docker
- `MONITORING__LANGFUSE_ENABLED` : mettre à `true` pour activer le tracing

## Ports locaux
| Service | Port |
|---|---|
| FastAPI | 8000 |
| Next.js frontend | 3001 |
| LangFuse | 3000 |
| Streamlit démo | 8501 |
| ChromaDB | 8001 |
| Ollama | 11434 |
| Redis | 6379 |
