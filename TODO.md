# TODO — rag-pipeline-demo

## Phase 1 — Fondations ✅
- [x] Structure projet + dossiers
- [x] Config Pydantic Settings (`src/config.py`)
- [x] `config.yaml` + `.env.example`
- [x] `pyproject.toml` (ruff + mypy + pytest)
- [x] `requirements.txt` + `requirements-dev.txt`
- [x] `Dockerfile` + `Dockerfile.worker`
- [x] `docker-compose.yml` (Ollama + Chroma + Redis + LangFuse)
- [x] `.dockerignore`
- [x] `.pre-commit-config.yaml` (ruff, mypy, bandit, detect-secrets)
- [x] `Makefile` complet
- [x] `CLAUDE.md`
- [x] `TODO.md`
- [x] ADRs initiaux (5)
- [x] `README.md`

## Phase 2 — Ingestion & Indexation
- [ ] `src/ingestion/loaders.py` — PDF, TXT, MD (LangChain DocumentLoaders)
- [ ] `src/ingestion/deduplicator.py` — hash-based dedup
- [ ] `src/ingestion/versioning.py` — détection changement + upsert strategy
- [ ] `src/ingestion/pii_filter.py` — Presidio (détection + anonymisation PII)
- [ ] `src/chunking/base.py` — interface abstraite BaseChunker
- [ ] `src/chunking/fixed.py` — RecursiveCharacterTextSplitter
- [ ] `src/chunking/semantic.py` — semantic chunking
- [ ] `src/chunking/parent_child.py` — parent-child chunking
- [ ] `src/embedding/base.py` — interface abstraite BaseEmbedder
- [ ] `src/embedding/ollama.py` — OllamaEmbeddings (nomic-embed-text)
- [ ] `src/embedding/batch.py` — batch embedding
- [ ] `src/vectorstore/base.py` — interface abstraite BaseVectorStore
- [ ] `src/vectorstore/chroma.py` — ChromaDB local
- [ ] `src/vectorstore/tenant.py` — namespace isolation par tenant
- [ ] `scripts/index_documents.py` — script d'indexation CLI
- [ ] `tests/unit/test_ingestion.py`
- [ ] `tests/unit/test_chunking.py`
- [ ] `tests/unit/test_embedding.py`

## Phase 3 — Retrieval
- [ ] `src/retrieval/hybrid.py` — BM25 + vector + RRF fusion
- [ ] `src/retrieval/reranker.py` — cross-encoder reranking
- [ ] `src/retrieval/query_transform.py` — HyDE + Multi-Query Retriever
- [ ] `src/retrieval/cache.py` — Redis semantic cache
- [ ] `tests/unit/test_retrieval.py`
- [ ] `tests/integration/test_retrieval_pipeline.py`

## Phase 4 — Génération
- [ ] `src/generation/prompts.py` — templates versionnés
- [ ] `src/generation/chain.py` — LCEL chain (Retriever → Prompt → LLM → Parser)
- [ ] `src/generation/guardrails.py` — prompt injection + détection hors-scope
- [ ] `tests/unit/test_generation.py`

## Phase 5 — API & Workers
- [ ] `src/api/main.py` — FastAPI app + lifespan
- [ ] `src/api/schemas.py` — Pydantic models I/O
- [ ] `src/api/routes/query.py` — POST /query (SSE streaming)
- [ ] `src/api/routes/ingest.py` — POST /ingest (async)
- [ ] `src/api/routes/feedback.py` — POST /feedback
- [ ] `src/api/middleware/auth.py` — JWT + API key
- [ ] `src/api/middleware/rate_limit.py` — Redis-based
- [ ] `src/api/middleware/tenant.py` — résolution tenant_id
- [ ] `src/api/middleware/cost_tracker.py` — tokens par requête
- [ ] `src/workers/indexer.py` — SQS consumer
- [ ] `app.py` — Streamlit démo
- [ ] `tests/integration/test_api.py`
- [ ] `tests/smoke/test_endpoints.py`

## Phase 6 — Évaluation & A/B
- [ ] `data/eval/golden_dataset.jsonl` — dataset Q&A de référence
- [ ] `src/evaluation/dataset_gen.py` — génération synthétique
- [ ] `src/evaluation/ragas_eval.py` — pipeline RAGAS
- [ ] `src/evaluation/experiment.py` — tracking config → métriques
- [ ] `src/evaluation/feedback.py` — feedback utilisateurs → dataset
- [ ] `src/ab_testing/variants.py` — définition des variants
- [ ] `src/ab_testing/router.py` — routage trafic
- [ ] `src/ab_testing/collector.py` — collecte métriques

## Phase 7 — Observabilité
- [ ] Intégration LangFuse dans `src/generation/chain.py`
- [ ] `src/analytics/query_tracker.py` — log requêtes
- [ ] `src/analytics/topic_clustering.py` — clustering sujets
- [ ] `monitoring/prometheus/rules.yml` — alertes
- [ ] `monitoring/grafana/dashboards/rag_overview.json`
- [ ] `monitoring/grafana/dashboards/ab_testing.json`
- [ ] `monitoring/grafana/dashboards/cost.json`

## Phase 8 — Infra AWS (CDK)
- [ ] `infra/stacks/network.py` — VPC, subnets, SG
- [ ] `infra/stacks/compute.py` — ECS Fargate + auto-scaling
- [ ] `infra/stacks/storage.py` — RDS pgvector + ElastiCache + S3
- [ ] `infra/stacks/messaging.py` — SQS + DLQ
- [ ] `infra/stacks/security.py` — WAF + Secrets Manager + IAM
- [ ] `infra/stacks/monitoring.py` — CloudWatch + budgets
- [ ] `src/vectorstore/pgvector.py` — pgvector prod

## Phase 9 — CI/CD
- [ ] `.github/workflows/ci.yml` — lint + test + build + scan
- [ ] `.github/workflows/eval.yml` — RAGAS regression hebdo
- [ ] `.github/workflows/cd-staging.yml` — deploy auto staging
- [ ] `.github/workflows/cd-prod.yml` — deploy prod + approbation
- [ ] `.github/workflows/load-test.yml` — Locust hebdo
- [ ] `.github/dependabot.yml`

## Phase 10 — Load Testing
- [ ] `tests/load/locustfile.py` — scénarios de charge
- [ ] `tests/load/scenarios/query_burst.py`
- [ ] `tests/load/scenarios/ingestion_bulk.py`
- [ ] Rapport de capacité + tuning auto-scaling

## Phase 11 — Frontend Next.js
- [ ] Init Next.js 15 + TypeScript + Tailwind + shadcn/ui
- [ ] Auth NextAuth (JWT multi-tenant)
- [ ] Page Chat (`/chat`) — SSE streaming + sources + feedback
- [ ] Page Documents (`/documents`) — upload + indexing status
- [ ] Dashboard Admin (`/admin`) — métriques + A/B + coûts
- [ ] Page Feedback (`/feedback`) — historique + export RAGAS
- [ ] Tests Vitest + Playwright E2E
- [ ] CI frontend (lint + typecheck + test + build)
