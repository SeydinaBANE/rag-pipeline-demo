# ADR 006 — Stack d'observabilité : Prometheus + LangFuse + QueryTracker

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte

Un pipeline RAG expose plusieurs couches à monitorer :
- **Performance système** : latence, throughput, taux d'erreur
- **Qualité des réponses** : faithfulness, answer relevancy, cache hit rate
- **Traces LLM** : tokens consommés, prompt/completion, coût par requête

Il fallait choisir une stack qui couvre ces trois niveaux sans ajouter une dépendance critique en dev local.

## Décision

Trois couches complémentaires :

1. **Prometheus** (`src/analytics/prometheus.py`) — métriques temps réel exposées via `GET /metrics`
2. **LangFuse** (`src/analytics/langfuse.py`) — traces LLM avec graceful degradation
3. **QueryTracker** (`src/analytics/tracker.py`) — historique JSONL par tenant

## Justification

### Prometheus pour les métriques système

- Standard de facto, compatible Grafana, AlertManager, CloudWatch Metrics
- Métriques clés : `rag_query_total` (labels: tenant, cached, prompt_version) et `rag_query_latency_seconds` (histogram avec buckets adaptés aux temps de réponse RAG)
- Pas de dépendance externe en dev — collecte en mémoire

### LangFuse pour les traces LLM

- UI locale via Docker pour le dev (port 3000)
- Capture query, answer, latency, nombre de sources, prompt version
- Désactivable par config (`MONITORING__LANGFUSE_ENABLED=false`) sans aucun changement de code
- **Pattern Callable** : le tracer stocke une closure `_fn` plutôt qu'une référence directe au client — mypy reste satisfait et la dégradation est transparente si LangFuse est indisponible

### QueryTracker pour l'historique tenant

- JSONL append-only — pas de dépendance externe, survit à un restart
- Permet de calculer cache hit rate et latence moyenne par tenant sans Prometheus
- Données brutes exploitables pour RAGAS ou clustering de topics

### Ce qui a été rejeté

- **Datadog / New Relic** : trop chers pour un projet démo, vendor lock-in
- **OpenTelemetry complet** : over-engineering — trois points de collecte indépendants suffisent et sont plus simples à maintenir
- **Logging structuré seul** : structlog est utilisé mais ne permet pas d'agréger facilement des métriques numériques

## Conséquences

- `record_query()` est appelé dans chaque route `/query` après `chain.invoke()`
- En prod, LangFuse cloud remplace le conteneur local — seules les variables d'env changent
- Le `QueryTracker` écrit dans `data/analytics/<tenant_id>.jsonl` — prévoir une rotation ou un bucket S3 en prod
