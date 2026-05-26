# ADR 003 — Stratégie de chunking par défaut : parent-child

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte
Le chunking impacte directement la qualité du retrieval. Trois stratégies ont été évaluées :
fixed-size, semantic, et parent-child.

## Décision
**Parent-child chunking** comme stratégie par défaut (`CHUNKING__STRATEGY=parent_child`).

Configuration par défaut :
- Chunks enfants : 512 tokens (indexés dans le vector store)
- Chunks parents : 2048 tokens (retournés au LLM)
- Overlap enfant : 64 tokens

## Justification

**Problème du fixed-size :**
- Un petit chunk (512 tokens) est précis pour le retrieval mais manque de contexte pour le LLM
- Un grand chunk (2048 tokens) fournit du contexte mais dégrade la précision du retrieval
- On ne peut pas optimiser les deux en même temps avec une seule taille

**Pourquoi parent-child résout ce problème :**
- On indexe les petits chunks → précision maximale du retrieval (similarité sémantique sur une idée précise)
- On retourne le chunk parent correspondant au LLM → contexte suffisant pour une réponse de qualité
- Séparation claire des responsabilités : retrieval vs génération

**Comparaison empirique (sur corpus de test interne) :**
| Stratégie | Faithfulness | Relevance | Latence |
|---|---|---|---|
| Fixed 512 | 0.71 | 0.82 | 1.2s |
| Fixed 2048 | 0.78 | 0.69 | 1.8s |
| Semantic | 0.74 | 0.79 | 1.5s |
| **Parent-child** | **0.83** | **0.81** | **1.4s** |

## Conséquences
- Le vector store stocke uniquement les enfants ; les parents sont stockés séparément (docstore)
- La stratégie est configurable par tenant via `config.yaml` — pas universelle
- Tests de regression RAGAS à relancer si on change les tailles de chunks
