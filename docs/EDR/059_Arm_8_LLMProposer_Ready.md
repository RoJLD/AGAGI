# EDR 059 : Préparer le #8 — `LLMProposer` armable (injection), testé, non armé

## Contexte

Le #8 (générateur LLM dans la boucle RSI) est *empiriquement justifié* (EDR 057 : 6 mécanismes à la
main, zéro qui fiabilise). On le rend **armable** — sans appel externe (pas de conteneur/clé ici,
règle EDR 044). Fait en parallèle du NAS (code pur + tests à mock, aucun conflit DB).

## Fait (`src/metaprog/rsi_loop.py`)

- **`LLMProposer(llm_fn=None)`** : le LLM est injecté comme une **fonction** `llm_fn(prompt)->str`.
  - `llm_fn=None` (défaut) → `propose` lève `NotImplementedError` → repli sur `TemplateProposer`
    (**verrou EDR 044 préservé** : aucun risque, aucun appel).
  - `llm_fn` fournie → `propose` construit le prompt, appelle, parse la réponse en `Proposal`.
- **`build_demand_prompt(context)`** : injecte la tendance + **les demandes déjà essayées et leurs
  scores MESURÉS** (via l'ontologie) → le LLM lit les échecs passés et ne se répète pas. Énonce le
  principe (demande ciblée + survivable) et les params de monde disponibles.
- **`parse_demand_response(text)`** : extrait le JSON (tolère la prose autour) → `Proposal`
  world_demand ; `ValueError` si pas de JSON.
- **5 tests** (mock LLM) : armé→Proposal valide, non armé→NotImplementedError, parse prose/garbage,
  prompt liste les échecs passés. (137 tests au total.)

## Armer le #8 = 2 branchements (et 2 seulement)

1. **Fournir `llm_fn`** : une fonction qui appelle un vrai LLM **dans un conteneur jetable** (clé API,
   isolation OS — prérequis EDR 035/044). `LLMProposer(llm_fn=ma_fn)`.
2. **Mesurer PUISSAMMENT** : brancher le **harnais** (EDR 052, multi-seed) comme `measure_fn` du
   `rsi_demand_step` — sinon la boucle optimise le bruit (EDR 051, démontré). C'est non négociable.

> Tout le reste est prêt : la cage (035), les yeux (036), la mémoire/ontologie (032/034), le
> catalogue `world_demand` (051), le harnais (052), et maintenant le **proposer LLM injectable**. Le
> #8 est **armable en une ligne** — mais reste *délibérément désarmé* tant que conteneur + harnais
> branché ne sont pas réunis.

## Boucle armée (cible, une fois les 2 branchements faits)

```
DÉTECTER (036) -> LLMProposer.propose(context=tendance+échecs passés) -> demande de monde
  -> ÉVALUER via le HARNAIS (052, multi-seed) -> score fiable
  -> garder si > meilleur connu ; ENREGISTRER (ontologie 032) -> nourrit le prochain `context`
  -> répéter (des centaines de fois là où la main en a fait ~6)
```

## Statut

- `LLMProposer` : **armable, testé, NON armé** (llm_fn=None par défaut).
- Prochaine étape réelle d'armement : un conteneur jetable + une `llm_fn` + le harnais en `measure_fn`.
  Décision utilisateur, délibérée.

## Note de prudence (inchangée)

Armer = un système qui se ré-écrit/re-conçoit ses propres demandes. Conteneur jetable obligatoire ;
falsification systématique (le harnais) ; périmètre borné (`ALLOWED_KINDS`, params de monde connus).
