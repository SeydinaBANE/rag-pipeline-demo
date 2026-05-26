# rag-pipeline-demo

Pipeline RAG industrialisé — 100% local en dev, déployable AWS en prod.

## Stack
- **LLM** : Ollama Mistral 7B (local) → AWS Bedrock (prod)
- **Embedding** : nomic-embed-text via Ollama
- **Vector store** : ChromaDB (local) → pgvector/RDS (prod)
- **Retrieval** : Hybrid BM25 + vector + reranking cross-encoder
- **Backend** : FastAPI + LangChain LCEL
- **Frontend** : Next.js 15 + TypeScript
- **Observabilité** : LangFuse + Prometheus/Grafana

## Démarrage rapide

### Prérequis
- Python 3.11+
- Docker + Docker Compose
- Node.js 20+ (frontend)

### Installation

```bash
# 1. Cloner et installer
make install

# 2. Copier et adapter la config
cp .env.example .env

# 3. Démarrer la stack complète (Ollama + Chroma + Redis + LangFuse)
make docker-up

# Les modèles Ollama se téléchargent automatiquement (~5GB, première fois)

# 4. Indexer les documents exemples
make index

# 5. Lancer l'API
make api
# → http://localhost:8000/docs

# 6. Lancer le frontend
make frontend-install && make frontend-dev
# → http://localhost:3001

# 7. (Optionnel) Démo Streamlit
make run
# → http://localhost:8501
```

### Services disponibles
| Service | URL |
|---|---|
| API FastAPI | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3001 |
| Streamlit démo | http://localhost:8501 |
| LangFuse | http://localhost:3000 |
| ChromaDB | http://localhost:8001 |

## Commandes utiles

```bash
make test          # Tests unitaires + intégration
make eval          # Évaluation RAGAS
make lint          # ruff + mypy
make load-test     # Tests de charge Locust
make docker-down   # Arrêter tous les services
make clean         # Nettoyer les caches
```

## Documentation
- [`CLAUDE.md`](CLAUDE.md) — Contexte projet pour Claude Code
- [`docs/adr/`](docs/adr/) — Décisions d'architecture
- [`TODO.md`](TODO.md) — Suivi des phases de développement
