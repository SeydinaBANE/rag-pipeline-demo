# ADR 004 — Multi-tenancy : namespace isolation

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte
Le système doit servir plusieurs clients (tenants) avec isolation complète des données.
Trois approches ont été évaluées : base de données séparée, schéma séparé, namespace/collection séparé.

## Décision
**Namespace isolation** : chaque tenant a sa propre collection dans le vector store,
préfixée par `{collection_prefix}_{tenant_id}`.

## Justification

**Option 1 — DB séparée par tenant :**
- Isolation maximale mais coût infra prohibitif (N instances RDS)
- Opérations complexes (N connexions à gérer, N backups)
- Réservé aux clients avec exigences de compliance très strictes

**Option 2 — Schéma PostgreSQL séparé :**
- Bonne isolation, même instance RDS
- Complexité des migrations (N schémas à migrer en même temps)
- Pas disponible avec Chroma (dev)

**Option 3 — Namespace/collection séparé (retenu) :**
- Fonctionne identiquement sur Chroma et pgvector
- Isolation suffisante pour la plupart des cas d'usage
- Opérations simples : créer/supprimer une collection = créer/supprimer un tenant
- Pas de surcoût infra
- Migration facile vers l'option 1 si un client l'exige

**Invariant de sécurité :**
Le `tenant_id` est extrait du JWT (signé côté serveur), jamais du body de la requête.
Le middleware `tenant.py` l'injecte dans le contexte — aucune route ne peut le contourner.

## Conséquences
- Toutes les opérations vectorstore prennent un `tenant_id` obligatoire
- Les tests doivent vérifier qu'un tenant A ne peut pas accéder aux données du tenant B
- Nommage des collections : `rag_{tenant_id}` (ex: `rag_acme`, `rag_contoso`)
- Backup : un snapshot RDS couvre tous les tenants — à affiner si isolation légale requise
