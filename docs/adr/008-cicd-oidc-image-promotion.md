# ADR 008 — CI/CD : OIDC AWS + promotion d'image sans rebuild

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte

Deux contraintes guidaient la conception du pipeline CI/CD :

1. **Sécurité** : éviter de stocker des credentials AWS long-lived dans les secrets GitHub
2. **Fiabilité** : garantir que l'image déployée en prod est exactement celle testée en staging

## Décision

### Auth AWS via OIDC (pas de secrets long-lived)

Chaque workflow CD configure AWS via `aws-actions/configure-aws-credentials@v4`
avec `role-to-assume`. GitHub Actions obtient un jeton OIDC signé par GitHub
et échange directement contre des credentials temporaires AWS.

### Promotion d'image (pas de rebuild)

```
CI          → build image tag :SHA → push ECR
cd-staging  → déploie :SHA sur staging
cd-prod     → pull :SHA, retag :prod, déploie :prod
```

L'image déployée en prod est bit-for-bit identique à celle testée en staging.
Il n'y a jamais de second `docker build`.

### Pinning par SHA, alias par environnement

- Le tag `:SHA` (git commit hash) est immuable
- Le tag `:staging` / `:prod` est un alias mis à jour à chaque déploiement
- La task definition ECS référence le tag `:SHA` pour que les rollbacks soient déterministes

## Justification

### OIDC vs secrets statiques

| Critère           | Secrets statiques | OIDC             |
|-------------------|-------------------|------------------|
| Rotation          | Manuelle          | Automatique (15min TTL)|
| Surface d'attaque | Secret stocké dans GitHub | Pas de secret permanent|
| Révocation        | Supprimer le secret | Modifier la trust policy|
| Audit             | Difficile         | CloudTrail complet|

### Promotion vs rebuild

Un rebuild en prod introduit des risques invisibles :
- Dépendances externes (PyPI, npm) peuvent avoir changé entre le build staging et prod
- Le contexte Docker peut inclure des fichiers locaux non versionnés
- Si le build échoue en prod, on se retrouve bloqué au moment critique

La promotion garantit le principe **"ce que vous testez est ce que vous déployez"**.

### Approval gate sur production

Le workflow `cd-prod.yml` est associé à un **GitHub Environment** `production`
qui requiert une approbation manuelle. Cela ajoute un sas humain sans ralentir
le déploiement staging (entièrement automatique sur merge dans `main`).

## Conséquences

- Nécessite de configurer un IAM Identity Provider GitHub dans le compte AWS et deux rôles IAM (`AWS_OIDC_ROLE_STAGING`, `AWS_OIDC_ROLE_PROD`)
- Les secrets GitHub suivants sont nécessaires : `ECR_API_REPO`, `ECR_WORKER_REPO`, `STAGING_API_URL`, `PROD_API_URL`
- Le smoke test (`/health` → 200) bloque le déploiement si l'API ne démarre pas correctement
- Les rollbacks se font en redéployant un tag SHA antérieur via `workflow_dispatch`
