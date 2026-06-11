# EDR 065 : Le #8 ARMÉ POUR DE VRAI — LLM local dans la boucle, en sécurité, sans conteneur

## Contexte

Le #8 était développé et *armable en une ligne* (EDR 059/061). L'utilisateur a signalé un **LLM
LOCAL** disponible (Gemma-12B via LM Studio, + Ollama : qwen2.5, deepseek-r1, glm-4.7…). Cela lève
les deux verrous — et permet d'**armer pour de vrai, en sécurité.**

## Pourquoi c'est SÛR sans conteneur (l'argument, pas un contournement)

La règle EDR 044 (conteneur jetable) visait le kind **`activation`** — où le LLM génère du **code
exécuté** (d'où la sandbox AST). Le périmètre **`world_demand`** est *fondamentalement différent* :

1. **LLM local** → zéro appel externe, zéro coût, zéro clé (machine de l'utilisateur).
2. **Aucun code généré/exécuté** : le LLM ne renvoie qu'un JSON de **paramètres de monde**.
3. **Frontière de sûreté** : `sanitize_demand_params` (allow-list `{lewis, referential_scale,
   speaker_reward, align_selection, transient_apex}`, typée + clampée) — **tout le reste est REJETÉ**
   (testé : `os_system`, `energy_max`, valeurs hors borne → écartés/clampés).

> **Surface d'attaque nulle** : au pire un réglage inutile, jamais un risque. Le conteneur reste requis
> pour `activation`/code ; il ne l'est pas pour `world_demand` borné. Argumenté, pas contourné.

## Fait

- `llm_proposer_fn.local_llm_fn(base_url, model)` : connecteur LLM local (API OpenAI-compatible,
  LM Studio/Ollama). + `anthropic_llm_fn` (gated, pour un cloud en conteneur) + `scripted_llm_fn`
  (test). 141 tests verts (dont la frontière de sûreté).

## Démonstration LIVE (Gemma-12B)

**Appel unique** — Gemma a lu le contexte (résultats passés mesurés), **raisonné** sur l'échec de
`speaker_reciprocity`, et proposé une demande NEUVE (`transient_apex` + `referential_scale`, hors
catalogue), correctement sanitisée.

**Boucle complète** (`rsi_demand_loop` + `LLMProposer(local_llm_fn())`, 4 itérations × 2 seeds,
mesure puissante) :

| Demande proposée par Gemma | gain (n=2) |
|---|---|
| Cross-Entity_State_Synchronization | **+0.0142** |
| Relational_Dependency_Tracing | +0.0092 |
| Temporal_Consistency_Audit | −0.0060 |

> **La boucle d'auto-amélioration est VIVANTE** : un vrai LLM propose des demandes de monde, le
> harnais les mesure (multi-seed), l'ontologie enregistre, et le LLM relit pour itérer. Le #8 n'est
> plus un *seam*, c'est une **boucle live et sûre**.

## Honnêteté (les limites)

1. **Régime cible faible** : les gains restent ~0.01 (n=2) — cohérent avec EDR 057 : *la frontière du
   langage est barren*, il n'y a pas de demande FORTE à trouver. Le #8 itère correctement, mais ne
   peut pas percer un mur qu'on a prouvé sans solution dans cet espace.
2. **Modèle 12B** : Gemma a *répété* une demande (diversité limitée). Un modèle plus fort (deepseek-r1
   :32b, qwen2.5:14b via Ollama) ou un meilleur prompt aiderait.
3. **n=2** : démonstration, pas verdict (la puissance coûte ; EDR 052).

## Ce que ça débloque (et ce qu'il reste)

- **Acquis** : le #8 fonctionne, en sécurité, avec un LLM local. La graine se propose ses propres
  mondes et les mesure honnêtement.
- **Pour le rendre PRODUCTIF** : (a) **élargir l'espace d'action** (plus de mécanismes de monde ; ou
  le kind `activation`/architecture *avec* conteneur) ; (b) le pointer sur une frontière aux effets
  plus francs ; (c) un modèle plus fort + plus de seeds. Le mécanisme est prêt ; sa valeur dépend
  désormais de ce qu'on lui donne à explorer.

## Statut

- **#8 ARMÉ, LIVE, SÛR** (LLM local + params bornés + sanitizer). `local_llm_fn` / `anthropic_llm_fn`
  / `scripted_llm_fn` disponibles. La boucle complète tourne.
- C'est l'aboutissement de l'arc RSI (035→065) : cage → yeux → mémoire → boucle → mesure puissante →
  **générateur vivant**.

## Variables d'expérience

Modèle local (Gemma/qwen/deepseek), température, espace d'action (params/mécanismes/`activation`),
nb de seeds, frontière cible, prompt.
