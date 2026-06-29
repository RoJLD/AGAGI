# EDR multi-lentilles — interprétations disciplinaires en fin de run — Design

**Date** : 2026-06-25
**Type** : outillage d'analyse (orthogonal au substrat — zéro collision avec les sessions science/survie).
**Statut** : design validé (brainstorm), prêt pour plan.

## Objectif

À la clôture d'un run / d'un finding EDR, générer des **interprétations disciplinaires multiples**
(éthologue, biologiste-évolutionniste, neuroscientifique, anthropologue…) du comportement/résultat
observé, puis une **synthèse générative** qui fait émerger de **nouvelles hypothèses falsifiables** —
pour « chercher plus loin ». Transforme un finding clos en carburant à futures expériences EDR.

## Contexte (grounded)

- **110 docs EDR** (`docs/EDR/NNN_Titre.md`) = la prose-finding est l'artefact PRIMAIRE (vs 12 JSON de
  résultats). L'outil interprète donc le **doc EDR** (+ JSON optionnel).
- Le projet a déjà l'abstraction `llm_fn(prompt:str)->str` (`src/metaprog/llm_proposer_fn.py`) :
  - `scripted_llm_fn(prompt)->str` : déterministe, sûr, **testable sans API** (c'est directement un `llm_fn`).
  - `anthropic_llm_fn(model=…, max_tokens=…)` : **fabrique** gatée `ANTHROPIC_API_KEY` (lève sans clé).
  - `local_llm_fn(base_url=…, …)` : **fabrique** LM Studio/Ollama.
- Précédent : `src/graph_rag/sociologist.py` génère déjà des analyses d'expériences (KuzuDB) — on ne le
  réutilise PAS (couplé KuzuDB, narrow) mais il valide le principe « analyse LLM des expériences ».

## Principe & garde-fous

- **CLI manuel** sur un doc EDR fini (pas de hook auto : la plupart des runs ne sont pas des EDR, et un
  EDR est une synthèse manuelle). Invoqué « en fin de run » au gré de l'utilisateur.
- **Défaut sûr** : `llm_fn = scripted_llm_fn` (zéro appel API, CI verte) ; `--live` arme
  `anthropic_llm_fn(...)` (gaté clé) ou `local_llm_fn(...)`.
- **Sortie en FICHIER SÉPARÉ** `docs/EDR/lenses/NNN_lenses.md` — on **ne mute jamais** le doc EDR canonique
  (mémoire : `docs/EDR/` sensible, `parity_check` en dépend). Sortie étiquetée **« interprétations
  spéculatives / pistes »**, pas des findings.
- Le code écrit UNIQUEMENT sous `docs/EDR/lenses/` ; il LIT le doc EDR et le JSON.

## Composants (responsabilité unique, testables)

### A — `build_lens_prompt(lens: dict, edr_text: str, results_json: str|None) -> str` (PUR)
Construit le prompt d'une lentille : persona disciplinaire + le finding (texte EDR tronqué à une borne)
+ JSON optionnel + consigne de finir par **1-2 hypothèses FALSIFIABLES pour CE substrat** (idiome EDR).

### B — `LENSES` (config extensible)
Liste de dicts `{key, title, persona}`. Défauts : **éthologue** (comportement animal : forage,
navigation, coopération), **biologiste-évolutionniste** (sélection, fitness, adaptation, substrat),
**neuroscientifique** (connectome, plasticité, circuits de navigation/apprentissage), **anthropologue**
(culture, outils, coopération, langage référentiel). Extensible via `EDR_LENSES` (env, clés séparées
par virgule) ou un arg CLI.

### C — `run_lenses(edr_text, results_json, llm_fn, lenses) -> list[dict]`
Pour chaque lentille : `llm_fn(build_lens_prompt(...))` → `{key, title, interpretation}`. Séquentiel
(robuste, peu de lentilles). Une lentille qui lève → interprétation = message d'erreur capturé (n'avorte
pas le run).

### D — `synthesize(interpretations, edr_text, llm_fn) -> str`
Passe finale : prompt qui reçoit les N interprétations + demande **(a)** les convergences inter-lentilles,
**(b)** les tensions/désaccords, **(c)** 2-3 **hypothèses/expériences EDR nouvelles** priorisées
(« chercher plus loin »). C'est le livrable à plus forte valeur.

### E — `render_markdown(edr_name, interpretations, synthesis) -> str` (PUR)
Assemble : en-tête + bandeau « ⚠️ interprétations spéculatives, non des findings » + 1 section/lentille +
section Synthèse. Déterministe.

### F — CLI `main`
`python tools/edr_lenses.py docs/EDR/NNN_*.md [results/xxx.json] [--live] [--local] [--lenses a,b,c]`.
Défaut scripted ; écrit `docs/EDR/lenses/NNN_lenses.md` (crée le dossier). Affiche le chemin écrit.

## Flux de données

`doc EDR (+ JSON) → build_lens_prompt × N → llm_fn → interprétations → synthesize → render_markdown → docs/EDR/lenses/NNN_lenses.md`

## Tests / non-régression

- **Unitaires (PUR, sans API)** : `build_lens_prompt` inclut persona + finding + consigne hypothèses ;
  `render_markdown` produit toutes les sections + le bandeau spéculatif ; `LENSES` défaut non vide.
- **Intégration avec `scripted_llm_fn`** : `run_lenses` + `synthesize` + `render_markdown` produisent un
  markdown bien formé (toutes lentilles présentes + synthèse) — **déterministe, zéro API**.
- **Robustesse** : un `llm_fn` qui lève sur une lentille → capturé, les autres aboutissent.
- **N'altère aucun fichier existant** : écrit seulement sous `docs/EDR/lenses/`.
- CI : défaut scripted → aucun appel réseau.

## Risques

1. **Coût / hallucination LLM** → gaté (`--live` opt-in, clé requise), manuel, sortie étiquetée
   spéculative + fichier séparé (jamais le doc canonique).
2. **Qualité scripted** : `scripted_llm_fn` produit du texte factice → les tests vérifient la STRUCTURE,
   pas le fond (le fond n'a de sens qu'en `--live`).
3. **Dérive de périmètre** : 4 lentilles par défaut (YAGNI), extension par config seulement.

## Hors-périmètre

- Hook automatique en fin de chaque run (rejeté : sur-déclenche, coût).
- Mutation des docs EDR canoniques (interdit).
- Réutilisation/extension du `Sociologist` KuzuDB.
- Indexation/recherche des interprétations (futur éventuel ; YAGNI).
