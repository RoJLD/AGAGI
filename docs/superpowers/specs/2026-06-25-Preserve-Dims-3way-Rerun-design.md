# Design — Re-faire le 3-way champion/mono_fresh/tabula avec preserve_dims (caveat EDR 102)

Date : 2026-06-25

EDR 102 a conclu MONOCULTURE (champion ≈ mono_fresh < tabula) — mais sur agents APLATIS
(`from_genome` jetait l'architecture du génome, [[from-genome-flattens-architecture]]). Le fix gaté
`preserve_dims` est maintenant disponible (mergé depuis main). Re-faire le 3-way avec l'architecture
PRÉSERVÉE pour trancher le caveat : l'archi évoluée du champion confère-t-elle une compétence apex
masquée ?

## Contexte

`MambaAgent.from_genome(genome, preserve_dims=False)` (`src/agents/mamba_agent.py:136`) : `True` garde
l'architecture réelle du génome au lieu de l'aplatir. Le pattern établi câble ce flag via env :
`map_elites_compare.py:38,93` (`MEC_PRESERVE_DIMS`), `metabolic_cost_sweep.py:75,185`
(`MCS_PRESERVE_DIMS`). `tools/target_competence_probe.py` appelle `from_genome` SANS le param (3 sites :
`:75` champion, `:85` mono_fresh, `:92` tabula) → aplati. EDR 102 (aplati) : tabula apex 0.211,
champion 0.162, mono_fresh 0.158.

## Hypothèse

- **champion préservé > mono_fresh/tabula** → compétence apex **ARCHITECTURALE** : EDR 102 sous-estimait
  le génome (l'aplatissement masquait l'avantage du champion). Reframe.
- **champion ≈ mono_fresh** (encore) → **MONOCULTURE robuste** même avec l'architecture préservée :
  EDR 102 confirmé/renforcé (la diversité, pas l'archi individuelle, porte l'apex coop).

## Architecture — petit build + run

### Unité 1 — câbler `CT_PRESERVE_DIMS` (build)

`tools/target_competence_probe.py`, pattern identique à `MEC_/MCS_PRESERVE_DIMS` :
- En tête (près des autres lectures d'env) : `PRESERVE_DIMS = os.environ.get("CT_PRESERVE_DIMS", "") == "1"`.
- Aux 3 sites `from_genome` (champion `:75`, mono_fresh `:85`, tabula `:92`) :
  `a.from_genome(g, preserve_dims=PRESERVE_DIMS)`.
- Défaut OFF (`""`) → comportement actuel (aplati) STRICTEMENT inchangé.

### Unité 2 — run 3-way préservé (pas de code)

Re-lancer les 3 bras avec `CT_PRESERVE_DIMS=1`, même config (stoneage, sweet spot 0.25/3.0, CT_K=8,
40 agents, 300 ticks). Comparer aux chiffres aplatis d'EDR 102. Rapporter la décompo `frac_apex`/
`frac_tool` par ère, apparié par seed.

## Garde-fous anti-théâtre

- **Smoke = garde-fou du risque** : `preserve_dims=True` pourrait échouer si les dims du génome sont
  incompatibles avec l'env. Le smoke (mode champion, `CT_PRESERVE_DIMS=1`) le révèle (échec visible, pas
  silencieux).
- **Régime absolu rapporté** : si `preserve_dims` change la performance ABSOLUE des 3 bras (pas juste
  l'écart), le signaler — c'est un changement de régime.
- **Apparié** (même seed), décompo par ère, 3-way. Tout réutilisé (métrique vivante, modes, décompo).
- **Défaut OFF** : non-régressif (les runs aplatis d'EDR 102 restent reproductibles sans le flag).

## Tests

- Smoke `slow` : `run_probe("stoneage", k=1, num_agents=20, max_ticks=80, mode="champion")` avec
  `monkeypatch.setenv("CT_PRESERVE_DIMS","1")` → tourne sans erreur, `per_era[0]` a la décompo,
  `median_competence ∈ [0,1]`. (Valide le câblage ET le risque dims.)
- Non-régression : `test_mono_fresh.py` / `test_live_harvest.py` (sans le flag, défaut OFF) restent
  verts.

## Hors périmètre (YAGNI)

- Pas de modif de `from_genome` (le param existe).
- Pas de re-run des autres expériences (dreaming, funnel) sous preserve_dims.
- Pas de balayage (le flag est binaire ON/OFF ; un éventuel sweep archi est un chantier distinct).

## Suite (selon verdict)

- ARCHITECTURALE → re-questionner EDR 097/102 (le champion porte une compétence apex archi) ; le HoF
  redevient un réservoir pertinent SI déployé avec archi préservée + diversité.
- MONOCULTURE robuste → EDR 102 renforcé ; la diversité de population reste le levier (≠ archi
  individuelle). Piste suivante = dose de diversité (option 1).
