# TODO — rag-pipeline-demo

## Phase 1 — Fondations ✅
- [x] Structure projet + dossiers
- [x] Config Pydantic Settings (`src/config.py`) — tous les sous-modèles imbriqués
- [x] `config.yaml` + `.env.example`
- [x] `pyproject.toml` (ruff strict + mypy strict + pytest + bandit)
- [x] `requirements.txt` + `requirements-dev.txt`
- [x] `Dockerfile` (multi-stage, non-root) + `Dockerfile.worker`
- [x] `docker-compose.yml` (Ollama + Chroma + Redis + LangFuse)
- [x] `.pre-commit-config.yaml` (ruff, mypy, bandit, detect-secrets)
- [x] `Makefile` complet (30+ cibles)
- [x] `CLAUDE.md` + `TODO.md` + `README.md`
- [x] ADRs 001–005 (vectorstore, LLM, chunking, multi-tenancy, async indexation)

## Phase 2 — Ingestion & Indexation ✅
- [x] `src/ingestion/loaders.py` — PDF, TXT, MD (LangChain DocumentLoaders)
- [x] `src/ingestion/deduplicator.py` — dédup SHA-256
- [x] `src/ingestion/versioning.py` — détection changement + upsert
- [x] `src/ingestion/pii_filter.py` — Presidio (détection + anonymisation)
- [x] `src/chunking/base.py` — interface abstraite BaseChunker
- [x] `src/chunking/fixed.py` — RecursiveCharacterTextSplitter
- [x] `src/chunking/semantic.py` — semantic chunking
- [x] `src/chunking/parent_child.py` — parent-child (défaut)
- [x] `src/embedding/base.py` + `src/embedding/ollama.py` + batch
- [x] `src/vectorstore/base.py` + `src/vectorstore/chroma.py` + tenant isolation
- [x] `scripts/index_documents.py`
- [x] `tests/unit/test_ingestion.py` + `test_chunking.py` + `test_embedding.py`

## Phase 3 — Retrieval ✅
- [x] `src/retrieval/hybrid.py` — BM25 + vector + RRF fusion (RRF_K=60)
- [x] `src/retrieval/reranker.py` — cross-encoder ms-marco-MiniLM-L-6-v2
- [x] `src/retrieval/query_transform.py` — HyDE + Multi-Query Retriever
- [x] `src/retrieval/cache.py` — Redis semantic cache (cosine similarity)
- [x] `tests/unit/test_retrieval.py`
- [x] `tests/integration/test_retrieval_pipeline.py`

## Phase 4 — Génération ✅
- [x] `src/generation/prompts.py` — registry v1/v2
- [x] `src/generation/chain.py` — LCEL (Retriever → Prompt → LLM → Parser)
- [x] `src/generation/guardrails.py` — InputGuardrail + OutputGuardrail
- [x] `tests/unit/test_generation.py`

## Phase 5 — API & Workers ✅
- [x] `src/api/main.py` — FastAPI app (CORS + 5 routers)
- [x] `src/api/schemas.py` — Pydantic models I/O
- [x] `src/api/routes/query.py` — POST /query + /query/stream (SSE)
- [x] `src/api/routes/ingest.py` — POST /ingest/upload
- [x] `src/api/routes/feedback.py` — POST /feedback
- [x] `src/api/routes/health.py` — GET /health
- [x] `src/api/routes/metrics.py` — GET /metrics (Prometheus)
- [x] `src/api/middleware/auth.py` — JWT Bearer (python-jose)
- [x] `src/api/middleware/rate_limit.py` — sliding window, threading.Lock
- [x] `src/api/deps.py` — CurrentUser, Chain, RateLimiter (lru_cache)
- [x] `src/workers/indexer.py` — SQS consumer + SIGTERM handling
- [x] `tests/unit/test_api.py`

## Phase 6 — Évaluation & A/B ✅
- [x] `data/eval/golden_dataset.jsonl` — 7 paires Q/R de référence
- [x] `src/evaluation/ragas_eval.py` — EvalReport + RAGASEvaluator + _compute_ragas
- [x] `src/evaluation/experiment.py` — ExperimentTracker (save/load/compare/best)
- [x] `src/evaluation/feedback_store.py` — FeedbackStore JSONL par tenant
- [x] `src/ab_testing/router.py` — ABRouter (sticky SHA-256 + impressions + conversions)
- [x] `tests/unit/test_evaluation.py` + `tests/unit/test_ab_testing.py`

## Phase 7 — Observabilité ✅
- [x] `src/analytics/prometheus.py` — RAG_QUERIES, RAG_LATENCY, RAG_INGEST_JOBS
- [x] `src/analytics/tracker.py` — QueryTracker JSONL (record/recent/stats)
- [x] `src/analytics/langfuse.py` — LangFuseTracer (Callable, graceful degradation)
- [x] `src/api/routes/metrics.py` — GET /metrics (generate_latest)
- [x] `src/api/routes/query.py` — record_query() après chaque invoke
- [x] `tests/unit/test_analytics.py` — 17 tests (tracker + Prometheus + LangFuse)
- [x] ADR 006 — Observabilité : Prometheus + LangFuse + QueryTracker

## Phase 8 — Infra AWS (CDK) ✅
- [x] `cdk/stacks/vpc_stack.py` — VPC 2-AZ, 3 tiers de subnets, flow logs
- [x] `cdk/stacks/data_stack.py` — RDS PostgreSQL 15 multi-AZ + ElastiCache Redis 7 + SQS + DLQ
- [x] `cdk/stacks/security_stack.py` — WAF (AWS managed rules + rate limit IP) + Secrets Manager
- [x] `cdk/stacks/compute_stack.py` — ECR + ECS Fargate API (ALB) + Worker + SG rules
- [x] `cdk/app.py` — 4 stacks avec dépendances explicites
- [x] `cdk/requirements.txt` + `cdk/cdk.json`
- [x] ADR 007 — Structure CDK en 4 stacks

## Phase 9 — CI/CD ✅
- [x] `.github/workflows/ci.yml` — lint + pre-commit + unit tests + Codecov
- [x] `.github/workflows/eval.yml` — RAGAS hebdo + triggered sur changements
- [x] `.github/workflows/cd-staging.yml` — ECR push SHA + ECS deploy (OIDC, main)
- [x] `.github/workflows/cd-prod.yml` — promotion image + approval gate + release (tag v*)
- [x] `.github/workflows/load-test.yml` — Locust headless + rapport artefact
- [x] `tests/load/locustfile.py` — RAGUser (query 80%, health 20%, metrics 10%)
- [x] ADR 008 — CI/CD : OIDC AWS + promotion d'image sans rebuild

## Phase 10 — Frontend Next.js ✅
- [x] `frontend/` — Next.js 14, TypeScript, Tailwind CSS
- [x] `frontend/app/chat/page.tsx` — Chat complet (bubbles + sources + feedback + hints)
- [x] `frontend/app/documents/page.tsx` — Upload drag-and-drop + statut par fichier
- [x] `frontend/app/analytics/page.tsx` — Health check live + cards métriques
- [x] `frontend/app/feedback/page.tsx` — Ratings thumbs up/down + taux positif
- [x] `frontend/components/Sidebar.tsx` — Navigation + JWT token input
- [x] `frontend/components/chat/` — MessageBubble, QueryInput, SourceCard
- [x] `frontend/components/documents/UploadForm.tsx`
- [x] `frontend/lib/api.ts` — queryRAG, streamQuery, submitFeedback, ingestFile
- [x] `frontend/hooks/useChat.ts` — état chat + sendMessage + sendFeedback
- [x] `frontend/vitest.config.ts` + `__tests__/Sidebar.test.tsx`
