# EDR 061 : Le #8 entièrement développé — mesure puissante branchée, armable en 1 ligne

## Contexte

EDR 059 : `LLMProposer` rendu armable (LLM injecté comme `llm_fn`). Restait le **2ᵉ prérequis
d'armement** : que la boucle MESURE de façon *puissante* (sinon elle classe le bruit, EDR 051).
Fait ici, en parallèle de la spéciation (code pur + tests à mock, sans DB).

## Fait

- **`make_powered_measure(run_seed_fn, seeds)`** (`rsi_loop.py`) : fabrique un `measure_fn` qui évalue
  chaque demande en **MULTI-SEED via le harnais** (EDR 052) — moyenne ± σ sur seeds — au lieu d'un run
  unique. World-agnostique (`run_seed_fn` injecté) → **testé au mock** (agrège bien 3 seeds).
- **`tools/rsi_demand_loop.py`** : la boucle #8 **COMPLÈTE** —
  `Proposer -> measure PUISSANTE -> rsi_demand_step (ontologie) -> context.accumule(résultats)`.
  Le `context` nourrit le prochain tour (les échecs passés mesurés) — ce que le LLM lira.
- 13 tests (rsi_loop) verts ; 138 au total.

## Le #8 : ce qui est branché, ce qui reste

| Brique | État |
|---|---|
| Cage (sandbox AST, 035) | ✅ |
| Yeux (superviseur réflexif, 036) | ✅ |
| Mémoire / ontologie (032/034) | ✅ |
| Périmètre `world_demand` + catalogue (051) | ✅ |
| Proposer LLM injectable (059) | ✅ armable |
| **Mesure PUISSANTE (harnais en measure_fn, 061)** | ✅ **branchée** |
| Boucle complète propose→mesure→enregistre→itère | ✅ |
| **Conteneur jetable** | ⏳ **décision outillage/sécurité (seul reste)** |

> **Armer = une seule ligne** : `WorldDemandProposer()` → `LLMProposer(llm_fn=<appel LLM en conteneur
> jetable>)`. La mesure puissante, l'ontologie, le catalogue, la cage : déjà branchés. Le #8 est
> *prêt* ; il reste **désarmé** par sécurité (pas de conteneur ici — règle EDR 044, je ne fais pas
> d'appels externes en douce).

## La boucle armée (cible)

```
DÉTECTER (036) -> LLMProposer.propose(context = tendance + échecs passés mesurés)
  -> demande de monde -> measure PUISSANTE (harnais multi-seed, 052/061) -> score FIABLE
  -> garder si > meilleur ; ENREGISTRER (ontologie 032) -> nourrit le prochain context
  -> répéter (des centaines de demandes, là où la main en a fait ~6 et a échoué — EDR 057)
```

## Pourquoi ça compte (lien EDR 057)

6 mécanismes de langage à la main, zéro qui fiabilise (045-057). L'espace des *demandes de monde* est
trop grand et trop bruité pour la main. Le #8 — proposer en masse, **mesurer puissamment**, lire les
échecs — est la seule approche systématique. On vient de **brancher la mesure puissante** : sans elle,
un itérateur amplifierait le bruit ; avec elle, il converge.

## Statut

- #8 **entièrement développé et testé**, **armable en 1 ligne**, **désarmé** (conteneur manquant).
- Prochaine étape d'armement : décision *outillage/sécurité* de l'utilisateur (conteneur + `llm_fn`).

## Variables d'expérience

Nb de seeds par évaluation (puissance vs coût), modèle LLM, format du `context`, périmètre des params.
