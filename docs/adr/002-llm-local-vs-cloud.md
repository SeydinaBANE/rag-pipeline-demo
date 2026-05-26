# ADR 002 — LLM : Ollama (dev) / AWS Bedrock (prod)

**Statut** : Accepté
**Date** : 2026-05-26

## Contexte
Le projet doit fonctionner sans clé API externe en développement, tout en étant
déployable en production avec un LLM managé et scalable.

## Décision
- **Dev** : Ollama avec Mistral 7B Instruct + nomic-embed-text
- **Prod** : AWS Bedrock (Mistral ou Claude selon les contraintes client)

## Justification

**Ollama en dev :**
- Zéro coût, zéro clé API, zéro latence réseau
- Mistral 7B tourne sur 8GB RAM (MacBook standard)
- Interface OpenAI-compatible — même code que pour Bedrock
- `nomic-embed-text` : embedding de qualité, 768 dimensions, gratuit

**Bedrock en prod :**
- Pas de GPU à gérer, scaling automatique
- Conforme aux exigences de sécurité AWS (VPC, IAM, CloudTrail)
- Facturation à l'usage — pas de coût fixe de GPU idle
- Support multi-modèles (Claude, Mistral, Llama) sans changer l'infra

**Pourquoi pas OpenAI directement :**
- Données client envoyées hors du périmètre AWS
- Coût imprévisible à grande échelle
- Certains clients exigent le cloud souverain (Bedrock en eu-west-1)

## Conséquences
- `LLMSettings.provider` contrôle le provider — changement de config, pas de code
- Les prompts sont testés sur Mistral 7B local ; comportement légèrement différent sur Bedrock
- Prévoir un test de régression des prompts lors du switch vers Bedrock
