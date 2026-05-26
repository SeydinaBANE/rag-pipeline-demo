# ADR 007 — Structure CDK : 4 stacks indépendantes

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte

L'infrastructure AWS du pipeline couvre VPC, base de données, cache, messagerie,
sécurité et calcul. Plusieurs architectures CDK étaient possibles :

- Une stack monolithique
- Des stacks par domaine fonctionnel
- Des stacks par couche réseau/données/compute

## Décision

**4 stacks** avec dépendances explicites et outputs cross-stack :

```
RagVpc → RagData ──┐
         RagSecurity ──┤→ RagCompute
```

| Stack         | Responsabilité                                      |
|---------------|-----------------------------------------------------|
| `VpcStack`    | VPC 2-AZ, subnets public/private/isolated, flow logs|
| `DataStack`   | RDS PostgreSQL 15, ElastiCache Redis 7, SQS + DLQ   |
| `SecurityStack`| WAF (managed rules + rate limit), Secrets Manager  |
| `ComputeStack`| ECR, ECS Fargate API + Worker, ALB, SG rules        |

## Justification

### Découplage par domaine

- **VPC** : rarement mis à jour, cycle de vie très long
- **Data** : change avec les migrations schema, indépendant du calcul
- **Security** : cycle de vie propre (rotation de secrets, MAJ règles WAF)
- **Compute** : déployé à chaque release (plusieurs fois par jour en staging)

Séparer les stacks permet de déployer uniquement `RagCompute` pour une release
sans risquer de toucher à la base de données ou au WAF.

### Isolation des blast radii

- Un rollback de `RagCompute` ne touche pas les données persistantes
- `RagData` a `deletion_protection=True` et `backup_retention=7j` — protégé contre les suppressions accidentelles
- `RagSecurity` contient les secrets — on peut les faire tourner sans redeployer le compute

### Alternative rejetée : stack unique

Une stack monolithique aurait les inconvénients suivants :
- Déploiement plus long (tout CloudFormation en un seul changeset)
- Pas de possibilité d'avoir des permissions IAM différentes par domaine
- Risque plus élevé de rollback affectant la prod

### Alternative rejetée : 6+ stacks

Séparer Networking / Database / Cache / SQS / Security / Compute aurait ajouté
une complexité de gestion des outputs cross-stack disproportionnée pour ce projet.

## Conséquences

- `ComputeStack` reçoit `vpc`, `data_stack`, `security_stack` comme props — pas de `Fn::ImportValue`
- Les security groups sont ouverts dans `ComputeStack` quand les SG ECS sont connus (pas dans `DataStack`)
- L'authentification CI/CD utilise OIDC avec des rôles IAM séparés par stack (staging vs prod)
- `cdk/requirements.txt` est séparé de `requirements.txt` pour ne pas charger aws-cdk-lib dans le conteneur API
