# ADR 005 — Indexation asynchrone via SQS

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte
L'indexation d'un document (chargement → chunking → embedding → vectorstore) peut prendre
plusieurs secondes à plusieurs minutes selon la taille. Une approche synchrone (HTTP direct)
crée des timeouts et bloque les workers API.

## Décision
**Indexation async via SQS** : le endpoint `POST /ingest` enqueue un job dans SQS et retourne
immédiatement un `job_id`. Un worker séparé consomme la queue et indexe.

## Flow
```
Client → POST /ingest → API → SQS (enqueue job_id) → 202 Accepted + job_id
                                      ↓
                              Worker (SQS consumer)
                                      ↓
                         Chargement → Chunking → Embedding → VectorStore
                                      ↓
                              Redis (job status: pending → processing → done)

Client → GET /ingest/{job_id}/status → Redis → { status, progress, error? }
```

## Justification

**Problèmes de l'approche synchrone :**
- Timeout HTTP à 30s — insuffisant pour les gros PDF
- Un upload bloque un worker API entier pendant l'embedding
- Pas de retry en cas d'échec (connexion Ollama perdue)

**Avantages SQS :**
- Découplage total API / traitement
- Retry automatique (visibilité timeout + DLQ après N échecs)
- Scaling indépendant : plus de workers si la queue s'allonge
- Idempotence : `job_id` basé sur le hash du document — pas de double indexation

**Dead Letter Queue (DLQ) :**
- Après 3 échecs, le message va en DLQ
- Alerte CloudWatch sur la DLQ — intervention manuelle requise
- Le document est marqué `failed` dans Redis avec le message d'erreur

**En dev local :**
SQS remplacé par une queue Redis in-memory (`fakeredis` en tests).
Le worker tourne dans un thread séparé via `docker-compose.yml`.

## Conséquences
- L'API doit exposer `GET /ingest/{job_id}/status` pour le polling client
- Le frontend poll toutes les 2s jusqu'à `status=completed`
- Les tests d'intégration doivent couvrir les cas d'échec et de retry
- En prod : 1 SQS queue principale + 1 DLQ, visibilité timeout = 10 min
