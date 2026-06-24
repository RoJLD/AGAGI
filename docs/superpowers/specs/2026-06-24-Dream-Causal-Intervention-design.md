# Design — Intervention causale du dreaming (Phase 2, balayage de profondeur)

Date : 2026-06-24
Trancher CAUSALEMENT le paradoxe Q2a (EDR 093/094). **Diagnostic d'abord**, mais cette fois par
manipulation : le corrélationnel a atteint sa limite.

## Contexte

EDR 093 : la population *portant* l'organe MCTS survit ~9% mieux (q2b 1.087) mais les agents qui
*rêvent* font marginalement pire (q2a −0.04). EDR 094 : le dreaming est une **conduite de minorité**
(l'agent médian ne rêve jamais) → tout agrégat observationnel est lavé/sous-puissant. **Seule une
manipulation exogène** peut trancher « rêver CAUSE un meilleur/pire sort » vs « rêver corrèle à la
détresse ».

Le dreaming est auto-sélectionné : `is_dreaming = has_mcts & (do_dream_logit>0.1) &
(surprise_momentum>0.05)` (`src/agents/mamba_agent.py:501-505`), profondeur
`K = clip(do_dream*8, 1, 8)` (`:507-511`). Pour casser l'auto-sélection, on **force** l'acte de rêver
et sa profondeur, à organe constant.

## Architecture — deux unités

### Unité 1 — hook moteur gated (`MambaBatchModel.FORCE_DREAM`)

`MambaBatchModel` porte déjà des flags de classe d'ablation (`ABLATE_THRESHOLDS`, `ABLATE_ROUTER`,
`:269-270`, EDR 032 : « neutraliser un gène câblé pour mesurer son apport »). On ajoute le MÊME
pattern : un flag de classe `FORCE_DREAM` (défaut `None`), lu là où `is_dreaming`/`K_individual` sont
calculés (`:501-511`) :

- `None` (défaut) → **comportement normal, prod inchangée** (`is_dreaming` auto-sélectionné, K = clip).
- `"off"` → `is_dreaming = zeros(B)` (personne ne rêve, organe et logit ignorés) → `K_individual = 0`.
- `int K` (≥1) → `is_dreaming = has_mcts_batch` (tous les porteurs d'organe rêvent) **et**
  `K_individual = where(is_dreaming, K, 0)` (profondeur FIXE K).

C'est la **première modification de `src/`** de ce fil — gated, défaut-off, pattern établi. Elle
exige son propre **test moteur** (off → 0 rêve même avec organe+logit hauts ; K → rêves forcés à
profondeur K ; None → inchangé).

### Unité 2 — sonde causale (`tools/dream_causal_probe.py`)

Dans le moule des sondes précédentes (déterministe, appariée seedée, provenance, quiet-log). Par
seed, à organe ON (100%, via `run_era_organ` organ_fraction=1.0) + sweet spot (0.25/3), balaye les
bras **{off, 1, 4, 8}** en posant `MambaBatchModel.FORCE_DREAM` AVANT l'ère et en le **réinitialisant
à None en `try/finally`** (anti-pollution, leçon des fuites d'état). Mesure la survie (`survival_
competence` = âge médian sur TOUS les agents, vivants+morts, EDR 092).

## Composants & interfaces

**Unité 1** (`src/agents/mamba_agent.py`) :
- Attribut de classe `MambaBatchModel.FORCE_DREAM = None`.
- Override dans la forward (`:501-511`) : un helper pur extractible
  `_resolve_dreaming(force_dream, has_mcts, do_dream, surprise, dream_thr, surprise_thr) ->
  (is_dreaming: np.ndarray, K_individual: np.ndarray)` — testable SANS instancier le batch model.

**Unité 2** (`tools/dream_causal_probe.py`, helpers PURS testables) :
- `dose_response_verdict(per_arm: dict[str|int, list[float]], eps: float = 0.02) -> dict` : reçoit
  `{arm: [survie par seed]}` pour arms `["off", 1, 4, 8]`. Le verdict s'ancre sur le **bras le plus
  profond** (max K) vs `off`, apparié par seed : `ratio = median(survie_Kmax_seed / survie_off_seed)`
  et `sign_p = _sign_test_p(#(ratio_seed>1 parmi ≠1), #≠1)`. Verdict : `CAUSE_BENEFIQUE`
  (`ratio > 1+eps ET sign_p < 0.1`), `CAUSE_NUISIBLE` (`ratio < 1−eps ET sign_p < 0.1`), `NEUTRE`
  sinon. Renvoie AUSSI `ratios_par_K` (ratio apparié médian de CHAQUE bras-K vs off) → la **courbe
  dose-réponse complète** pour l'interprétation (monotone croissante = la profondeur aide
  graduellement ; pic puis chute = profondeur optimale ; plat = neutre). Clés :
  `{ratio, sign_p, n_favorable, n, verdict, ratios_par_K}`.
- `run_causal(seeds, target, num_agents, max_ticks, shared_db, ks=(1,4,8)) -> dict` : pour chaque
  seed, pour chaque arm ∈ `["off", *ks]`, pose `FORCE_DREAM`, exécute `run_era_organ`
  (organ_fraction=1.0, sweet), `survival_competence` ; `finally: FORCE_DREAM = None`. Apparie par seed.
- `main()` : env knobs `DC_TARGET`/`DC_SEEDS`/`DC_KS`/`DC_NUM_AGENTS`/`DC_MAX_TICKS` ; quiet-log AVANT
  `start()` ; provenance `Harness.save`.

## Garde-fous anti-théâtre

- **Réinitialisation du flag en `finally`** : `FORCE_DREAM` est un état global de classe ; un bras qui
  oublie de le remettre à `None` polluerait les bras suivants ET la prod. `try/finally` obligatoire,
  testé.
- **Hook moteur testé** (pas seulement la sonde) : le helper `_resolve_dreaming` a son test unitaire
  (les 3 régimes), car il modifie le moteur.
- **Apparié** (même seed sur tous les bras), déterministe (memory_retriever neutralisé via
  `run_era_organ`), provenance ledger.
- **Courbe dose-réponse COMPLÈTE rapportée** (survie par bras-K, per-seed), jamais le label nu.
- Sous-puissance signalée (`sign_p`). Caveat assumé : organe forcé ON pour tous (on mesure l'effet du
  *rêve* à organe constant, pas l'effet de l'organe).

## Hors périmètre (YAGNI)

- Pas de balayage d'énergie/cible ici (stoneage + sweet spot fixes).
- Pas de modification du contenu du rêve (seulement l'acte + la profondeur).
- Le hook ne touche QUE `is_dreaming`/`K_individual` ; aucune autre logique moteur.

## Tests

- **Unité 1** `_resolve_dreaming` : `None` → reproduit `has_mcts & logit>thr & surprise>thr` ; `"off"`
  → tout False, K=0 ; `int K` → `is_dreaming == has_mcts`, `K_individual == K` sur les porteurs, 0
  sinon. (Pur, numpy, sans biosphère.)
- **Unité 2** `dose_response_verdict` : 3 cas (croissant → BENEFIQUE ; décroissant → NUISIBLE ; plat →
  NEUTRE) sur entrées synthétiques + sign_p.
- `run_causal` : smoke biosphère minimal (1 seed, ks=(1,), max_ticks court, marqué `slow`) — vérifie
  la forme du retour ET que `MambaBatchModel.FORCE_DREAM is None` APRÈS le run (réinit).
- `main` provenance : monkeypatch `run_causal` + async_logger + `_acquire_shared_db` ; vérifie
  `results/dream_causal_*.json` (verdict, commit, git_dirty) ; isole la fuite d'env
  (`monkeypatch.setenv("AGISEED_QUIET_LOG","0")` avant `main()`, leçon EDR 093).
