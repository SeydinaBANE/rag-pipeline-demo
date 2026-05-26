# ADR 001 — Choix du vector store : Chroma (dev) / pgvector (prod)

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte
Le pipeline RAG nécessite un vector store pour stocker et interroger les embeddings.
Plusieurs options ont été évaluées : Pinecone, Weaviate, Chroma, pgvector, Qdrant.

## Décision
- **Dev local** : ChromaDB (in-process, zéro infra)
- **Prod** : pgvector sur RDS Aurora PostgreSQL

## Justification

**Pourquoi pgvector en prod :**
- Pas de vendor lock-in (contrairement à Pinecone)
- Requêtes hybrides SQL + vecteur dans la même transaction
- Metadata filtering natif avec WHERE SQL — plus flexible que les filtres propriétaires
- Backup/restore standard PostgreSQL (RDS automated snapshots)
- Multi-tenancy par schéma ou namespace sans coût supplémentaire
- Équipe déjà familière avec PostgreSQL

**Pourquoi Chroma en dev :**
- Zéro configuration — `chromadb.Client()` suffit
- Même interface abstraite que pgvector via `BaseVectorStore`
- Suffisant pour développer et tester localement

**Alternatives rejetées :**
- Pinecone : vendor lock-in, coût élevé à grande échelle, latence réseau
- Weaviate : plus complexe à opérer, moins mature sur AWS
- Qdrant : bonne option mais équipe sans expérience dessus

## Conséquences
- Interface `BaseVectorStore` obligatoire pour que le swap Chroma → pgvector soit transparent
- Les tests d'intégration doivent tourner contre Chroma (pas de mock)
- `VECTORSTORE__PROVIDER` dans `.env` contrôle le provider actif
