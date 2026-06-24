# Design — Sonde funnel autel/outil (barreau 0 de l'EDR 014)

Date : 2026-06-24

Diagnostiquer le goulot d'exploration EDR 014 (couche 2 de compétence) sur stoneage, au sweet spot
énergie. **Observationnel d'abord** : où, dans le pathway outil, les agents décrochent-ils — et l'autel
est-il bien structurellement mort ? Le verdict détermine quel levier bâtir (et lequel ne sert à rien).

## Contexte

EDR 095 vient de **réfuter l'approche A** (organe MCTS comme levier d'exploration : forcer le rêve
RÉDUIT la survie). La survie couche-1 de stoneage est résolue au sweet spot (~25 ticks médians,
EDR 085). Le mur restant = couche 2 (autels/outils), goulot EDR 014.

L'exploration du code révèle que « autels/outils » sont **deux histoires opposées** :

- **Autels = structurellement morts.** Aucun code de résolution d'autel dans `world_1_stoneage.py`
  (le mécanisme du monde Soup, ~lignes 541-553, est absent). `altars_solved` est initialisé à 0
  (`world_1_stoneage.py:338`) et **jamais incrémenté**. Or `stoneage_competence` pondère
  `altars_solved` à **0.6** (`src/curriculum/competence.py:45-58`) → la métrique couche-2 mesure une
  variable morte → elle s'effondre à `0.4 × chasse`. Gap STRUCTUREL, pas d'exploration : la nouveauté
  n'y peut rien.
- **Outils (lance) = mécanique complète et récompensée.** Craft rock+stick → `spears_crafted`
  (`:339`, incrémenté `:1210`, log `SPEAR_CRAFTED`). Gradient moyens→fins fort : tuer le mammouth
  (+énergie, `mammoth_kills` `:337`, incrémenté `:718/723`) **exige** la lance (mains nues : 10 dégâts
  vs riposte 50). Le pathway a un vrai gradient ; la question est si les agents l'empruntent.

## Périmètre

**Décomposé, observationnel.** (1) Confirmer EMPIRIQUEMENT que l'autel est mort (`altars_solved`
jamais > 0 sur un run réel — anti-théâtre : ne pas croire la lecture de code seule). (2) Mesurer le
funnel outil (craft → usage mammouth) sur **tous** les agents. Le point de décrochage localise le gap.

**Hors périmètre (YAGNI).** Pas d'intervention gated « force-spear » (devient barreau 1 SI le funnel
montre que l'usage est le mur). Pas de balayage d'énergie (sweet spot fixe). Pas de modification de
`src/` (sonde pure lecture).

## Architecture — approche A (era-runner + agrégateur pur)

Moule des sondes précédentes (`dreaming_probe`/`dream_causal_probe`) : déterministe, appariée seedée,
provenance, quiet-log. Lit les **champs d'agent** (source de vérité), pas le log d'événements (lacunaire
sous quiet-log). Nouveau fichier `tools/altar_tool_funnel_probe.py`, trois unités.

### Unité 1 — `run_era_funnel`

`run_era_funnel(seed, metab, payoff, num_agents, max_ticks, shared_db) -> list[dict]` : exécute UNE ère
stoneage. Renvoie, pour **tous** les agents (vivants + morts, `env.agents + env.dead_agents`,
EDR 092) : `{age, preys_eaten, spears_crafted, mammoth_kills, altars_solved}`. Structuré comme
`run_era_organ` (`tools/dreaming_probe.py`) mais **sans semis d'organe** (on ne teste pas le dreaming)
et en récoltant les champs du funnel. Sibling dédié (pas de réutilisation de `run_era_organ`, qui sème
l'organe).

### Unité 2 — `funnel_verdict` (helper PUR)

`funnel_verdict(per_seed_agents: dict, eps: float = 0.02) -> dict`. Reçoit `{seed: [agents]}`. Calcule,
sur tous les agents poolés (rare-event-aware, JAMAIS la médiane) :

- `frac_hunt` = fraction avec `preys_eaten ≥ 1` (sanity couche-1)
- `frac_craft` = fraction avec `spears_crafted ≥ 1` (acquisition)
- `frac_apex` = fraction avec `mammoth_kills ≥ 1` (usage : le mammouth exige la lance)
- `total_spears`, `total_mammoth_kills`, `n_agents`
- `altars_solved_max` = max(`altars_solved`) sur tous

**Verdict autel** : `AUTEL_MORT` si `altars_solved_max == 0` ; sinon `AUTEL_VIVANT` (contredirait la
lecture de code → à signaler).

**Verdict funnel** (1ᵉʳ étage qui s'effondre sous `eps`) :
- `frac_craft < eps` → `GAP_ACQUISITION` (jamais de craft : mur amont récolte/`do_rub`)
- `frac_craft ≥ eps` ET `frac_apex < eps` → `GAP_USAGE` (craft OK, jamais d'escalade mammouth)
- `frac_apex ≥ eps` → `PATHWAY_VIVANT` (le gradient tire ; couche-2 outil atteignable)

Retour : `{verdict_autel, verdict_funnel, frac_hunt, frac_craft, frac_apex, total_spears,
total_mammoth_kills, altars_solved_max, n_agents, par_seed}`. `par_seed[seed]` porte les mêmes fractions
+ totaux par seed → **courbe funnel complète rapportée**, jamais le label nu. `eps=0.02` ≈ 1 agent /50
(seuil anti-bruit, paramètre signalé).

### Unité 3 — `main`

Knobs d'env `AF_SEEDS`/`AF_NUM_AGENTS`/`AF_MAX_TICKS` (sweet spot `metab=0.25`/`payoff=3.0` fixe).
`os.environ["AGISEED_QUIET_LOG"]="1"` AVANT `async_logger.start()`. Boucle seeds → `run_era_funnel` →
`funnel_verdict`. Provenance `Harness(name="altar_tool_funnel").save(...)`.

## Garde-fous anti-théâtre

- **Tous les agents** (vivants + morts) — extinction 100 % rendrait `env.agents` vide (EDR 092).
- **Fractions, pas médianes** — craft/mammouth sont des événements rares (EDR 094 : la médiane les lave).
- **Confirmation empirique de la mort de l'autel** — le smoke ET le run réel assertent
  `altars_solved_max == 0` ; on ne se fie pas à la seule lecture statique.
- **Décomposition par seed rapportée** — jamais le verdict nu.
- **Quiet-log posé AVANT l'import/`start`** (leçon de vitesse + anti-segfault) ; provenance test isole
  la fuite d'env (`monkeypatch.setenv("AGISEED_QUIET_LOG","0")` avant `main()`, EDR 093).

## Tests

- **`funnel_verdict` (pur)** : `GAP_ACQUISITION` (chasse mais 0 craft) ; `GAP_USAGE` (craft mais 0
  mammouth) ; `PATHWAY_VIVANT` (≥1 mammouth) ; autel `AUTEL_MORT` (tous 0) vs `AUTEL_VIVANT` (un >0) ;
  cas vide `{}` sans crash ; `par_seed` porte la décomposition.
- **`run_era_funnel` (smoke, `slow`)** : 1 seed, ticks courts → liste de dicts aux 5 champs ; couvre
  vivants + morts (non vide sous extinction) ; `max(altars_solved) == 0` (confirmation empirique).
- **`main` provenance (monkeypatch)** : `run_era_funnel` + `async_logger` + `_acquire_shared_db`
  monkeypatchés → `results/altar_tool_funnel_*.json` avec `verdict_funnel`, `verdict_autel`, `commit`,
  `git_dirty` ; isole la fuite d'env (`monkeypatch.setenv("AGISEED_QUIET_LOG","0")` avant `main()`).

## Suites possibles (selon le verdict)

- `AUTEL_MORT` (attendu) → **acter l'artefact métrique** : `stoneage_competence` mesure du vide à 0.6.
  Soit implémenter la résolution d'autel sur stoneage, soit re-pondérer la couche-2 sur un signal vivant
  (`spears_crafted`/`mammoth_kills`). EDR.
- `GAP_ACQUISITION` → le mur est en amont du craft (récolte rock+stick / action `do_rub`) → levier
  nouveauté ou scaffold de craft.
- `GAP_USAGE` → barreau 1 = intervention gated « force-spear » pour trancher can't-use vs won't-use.
- `PATHWAY_VIVANT` → la couche-2 outil n'est PAS le goulot ; le mur EDR 014 est l'autel (structurel) →
  pivot vers l'implémentation/repondération.
