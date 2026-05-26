# rag-pipeline-demo — Contexte projet pour Claude Code

## Vue d'ensemble
Pipeline RAG industrialisé, 100% local en dev (Ollama + Chroma), déployable sur AWS en prod.
Construit pour démontrer les pratiques senior : hybrid search, reranking, multi-tenancy,
évaluation RAGAS, A/B testing, observabilité LangFuse.

## Stack technique
| Couche | Dev | Prod |
|---|---|---|
| LLM | Ollama Mistral 7B | AWS Bedrock |
| Embedding | Ollama nomic-embed-text | AWS Bedrock |
| Vector store | ChromaDB | RDS pgvector |
| Cache | Redis local | ElastiCache |
| Backend | FastAPI + uvicorn | ECS Fargate |
| Worker | Python process | ECS + SQS |
| Frontend | Next.js dev server | CloudFront + ECS |
| Observabilité | LangFuse local | LangFuse cloud |

## Commandes essentielles
```bash
make install        # Setup complet (venv + pre-commit)
make docker-up      # Stack locale (Ollama + Chroma + Redis + LangFuse)
make api            # FastAPI en hot-reload (port 8000)
make run            # Streamlit démo (port 8501)
make test           # pytest unit + integration
make lint           # ruff + mypy
make eval           # RAGAS sur golden dataset
make index          # Indexe data/docs/
```

## Architecture des modules
```
src/
├── config.py           # Source de vérité de toute la config (Pydantic Settings)
├── ingestion/          # Loaders → dedup → PII filter → versioning
├── chunking/           # fixed | semantic | parent_child (défaut)
├── embedding/          # OllamaEmbeddings + batch
├── vectorstore/        # Chroma (dev) / pgvector (prod) — interface commune
├── retrieval/          # hybrid BM25+vector → reranker → semantic cache
├── generation/         # LCEL chain → prompts versionnés → guardrails
├── evaluation/         # RAGAS + experiment tracking + feedback loop
├── ab_testing/         # Router trafic + collecte métriques par variant
├── analytics/          # Query tracking + topic clustering
├── api/                # FastAPI : /query /ingest /feedback + middlewares
└── workers/            # SQS consumer pour indexation async
```

## Conventions
- **Config** : toujours via `get_settings()` depuis `src/config.py`. Jamais de valeurs hardcodées.
- **Interfaces** : chaque couche a une classe `Base*` abstraite. Swap de provider = changer l'implémentation, pas le code appelant.
- **Tenancy** : chaque requête porte un `tenant_id`. Le vector store isole par namespace.
- **Logging** : `structlog` uniquement, format JSON en prod. Pas de `print()`.
- **Async** : toutes les routes FastAPI et les accès DB/Redis sont async. Pas de `time.sleep()`.
- **Tests** : mocks uniquement aux boundaries externes (Ollama, Redis, Chroma). Pas de mock interne.
- **Secrets** : jamais dans le code. `.env` local, AWS Secrets Manager en prod.

## Fichiers clés
| Fichier | Rôle |
|---|---|
| `src/config.py` | Toute la configuration typée |
| `config.yaml` | Valeurs par défaut |
| `.env.example` | Template variables d'environnement |
| `docker-compose.yml` | Stack dev complète |
| `Makefile` | Toutes les commandes du projet |
| `docs/adr/` | Décisions d'architecture justifiées |
| `data/eval/golden_dataset.jsonl` | Dataset de référence RAGAS |

## Décisions d'architecture
Voir `docs/adr/` pour le détail. En résumé :
- **pgvector > Pinecone** : self-hosted, pas de vendor lock-in, SQL natif pour metadata filtering
- **Ollama > vLLM** en dev : zéro friction, pas besoin de GPU dédié
- **parent-child chunking** par défaut : meilleure précision retrieval + contexte suffisant au LLM
- **Async indexation (SQS)** : évite les timeouts HTTP sur les gros documents
- **Namespace isolation** pour multi-tenancy : plus simple que des DB séparées, assez sûr

## Variables d'environnement importantes
Copier `.env.example` → `.env` et ajuster :
- `API__SECRET_KEY` : obligatoire en prod (chaîne aléatoire longue)
- `LLM__BASE_URL` : `http://localhost:11434` en local, `http://ollama:11434` dans Docker
- `MONITORING__LANGFUSE_ENABLED` : mettre à `true` pour activer le tracing

## Ports locaux
| Service | Port |
|---|---|
| FastAPI | 8000 |
| Streamlit | 8501 |
| Next.js frontend | 3001 |
| LangFuse | 3000 |
| ChromaDB | 8001 |
| Ollama | 11434 |
| Redis | 6379 |
