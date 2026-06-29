# Design — Métrique de diversité comportementale (clore issue 1 vs 2 d'EDR 108)

Date : 2026-06-25

## Question scientifique

EDR 108 : la sélection diverse (tournoi) ne rescousse PAS l'apex (NS, sign_p 0.110), MAIS le garde-fou
`genome_diversity = std(genome.W.mean())` était **au plancher pour les DEUX bras** (~0.001, ratio 1.07) →
trop grossier pour confirmer que le bras `diverse` a réellement préservé plus de diversité. Sans une vraie
mesure de diversité COMPORTEMENTALE, on ne peut pas trancher : **le bras `diverse` est-il vraiment plus
divers comportementalement ?** La réponse clôt issue 1 vs 2 :
- diverse plus divers ET apex plat → **issue 2 (répertoire-monde = verrou) CLOSE net, sélection
  innocentée** ;
- diverse PAS plus divers → le tournoi n'empêche pas l'effondrement comportemental intra-ère → la
  sélection telle que bâtie est un levier insuffisant.

Indice qui motive : la population diffère en fin d'ère (diverse n~72 vs elitist n~55), donc une vraie
différence de dynamique existe — mais `genome_diversity` ne la voit pas.

## Contexte (vérité terrain)

- `tools/evolve_ceiling_probe.py` : `run_evolution(..., select, n_carry, tournament_size, pop_cap)`.
  `_agent_stats(all_agents)` collecte DÉJÀ par agent : `age`, `energy`, `preys_eaten`, `altars_solved`,
  `total_dreams`, `mammoth_kills`, `spears_crafted`. Le `row` par ère contient déjà `frac_apex`,
  `genome_diversity`, `mean_nodes`, etc.
- Piège métrique (leçon EDR 108) : descripteurs à échelles très différentes (`age` ~0-300 vs
  `mammoth_kills` ~0-2). Une std brute serait dominée par `age` (survie, pas stratégie) → **normaliser par
  dimension** avant d'agréger.

## Hypothèse (3 issues)

1. **`behavioral_diversity` PLUS HAUTE sous diverse (métrique sensible, pas au plancher) ET apex plat
   (reproduit EDR 108)** → diversité comportementale préservée mais apex ne monte pas → **issue 2
   (répertoire-monde) CLOSE, sélection innocentée**.
2. **`behavioral_diversity` PAS plus haute sous diverse** → le tournoi ne préserve pas la diversité
   comportementale (effondrement intra-ère) → la sélection est un levier insuffisant → re-designer
   (niching/MAP-Elites/nouveauté) ou acter.
3. (garde-fou métrique) **`behavioral_diversity` au plancher pour les DEUX bras** → re-spécifier la
   métrique (peu probable : descripteurs stratégiques discrets `preys`/`mammoth`/`spears`).

## Architecture — 1 ajout à `tools/evolve_ceiling_probe.py` (DRY)

### Unité 1 — métrique `behavioral_diversity` par ère (build)

Dans `run_evolution`, près du calcul de `genome_diversity` (avant le dict `row`), ajouter une fonction de
diversité comportementale et l'appeler sur `all_agents` (model-bearing) :

```python
        # Diversité COMPORTEMENTALE (EDR 109) : std inter-agents de descripteurs NORMALISÉS par dimension
        # (sinon age domine). Décompo par descripteur -> stratégie (preys/mammoth/spears) vs survie (age).
        DESCRIPTORS = ("preys_eaten", "mammoth_kills", "spears_crafted", "age")
        bdiv = {}
        for d in DESCRIPTORS:
            vals = [s[d] for s in stats]
            vmax = max(vals) if vals else 0
            norm = [v / vmax for v in vals] if vmax > 0 else [0.0 for _ in vals]
            bdiv[d] = statistics.pstdev(norm) if len(norm) > 1 else 0.0
        behavioral_diversity = round(statistics.mean(bdiv.values()), 4) if bdiv else 0.0
```

(`stats` est la liste de dicts déjà produite par `_agent_stats(all_agents)` ; chaque dict a les clés
descripteurs. Normalisation min-max simplifiée = division par le max de l'ère, borne [0,1].)

Ajouter au dict `row` :

```python
            "behavioral_diversity": behavioral_diversity,
            "bdiv_preys": round(bdiv["preys_eaten"], 4),
            "bdiv_mammoth": round(bdiv["mammoth_kills"], 4),
            "bdiv_spears": round(bdiv["spears_crafted"], 4),
            "bdiv_age": round(bdiv["age"], 4),
```

(`genome_diversity` reste — on garde les deux pour comparer le grossier au fin.) Optionnel : ajouter
`behavioral_diversity` à la ligne de log (`bdiv=%.4f`).

### Unité 2 — re-run A/B (pas de code)

Mêmes params qu'EDR 108 (déterministe → apex reproduit EDR 108 exactement = 3ᵉ contrôle de cohérence) :

```
AGISEED_QUIET_LOG=1 EVP_SELECT={elitist,diverse} EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage \
  EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 \
  CT_METAB=0.25 CT_PAYOFF=3.0 EXPERIMENT_SEED=<s> python -u tools/evolve_ceiling_probe.py
```

× 3 seeds × 2 bras. **Détection de succès par code de sortie python** (PAS un grep sur un log redirigé —
piège EDR 108 : `2>/dev/null` avale les logs cherchés par grep → faux échec → JSON non copié). Capturer
la sortie en fichier, copier le JSON sur exit 0.

## Garde-fous anti-théâtre

- **Sensibilité de la métrique vérifiée** : `behavioral_diversity` doit être > plancher (sinon issue 3).
- **Décompo par descripteur** : distinguer diversité de STRATÉGIE (preys/mammoth/spears) vs SURVIE (age) —
  c'est le cœur du raffinement vs `genome_diversity`.
- **Cohérence** : l'apex DOIT reproduire EDR 108 (mêmes seeds/params) → si écart, signaler (non-repro).
- **A/B apparié** par seed ; trajectoire par ère ; régime absolu.
- **Détection de succès robuste** (exit code, pas grep sur stderr redirigé).

## Tests

- Smoke `slow` (`tests/sandbox/test_behavioral_diversity.py`) :
  `run_evolution("stoneage", k_eras=2, num_agents=12, max_ticks=60, shared_db, preserve_dims=True,
  node_cap=512, select="diverse", n_carry=6, tournament_size=3, pop_cap=40)` → `per_era[0]` a
  `behavioral_diversity` ET les 4 `bdiv_*` ; tous ∈ [0,1] ; `median_competence ∈ [0,1]`.
- Non-régression : `test_diverse_selection.py` + `test_evolve_ceiling_probe.py` (l'ajout d'une clé au row
  n'altère pas les modes/verdicts existants ; `genome_diversity` reste présent).

## Hors périmètre (YAGNI)

- Pas de distance pairwise O(n²) ni de binning de niches (la std normalisée par dimension suffit).
- Pas de nouvelle collecte par agent (descripteurs déjà dans `_agent_stats`).
- Pas de re-design de la sélection (ce chantier MESURE ; re-designer serait l'issue 2 suivante).
- Stoneage seul (zéro collision Lewis/sessions //).

## Suite (selon issue)

- **Issue 1 (diverse plus divers, apex plat)** : répertoire-monde CONFIRMÉ comme verrou → passer à
  l'enrichissement d'affordance (piste 2 d'EDR 108, diagnostic coverage `map_elites_compare` d'abord).
- **Issue 2 (diverse pas plus divers)** : le tournoi sur carry ne maintient pas la diversité → intervention
  de diversité plus forte (niching / MAP-Elites / nouveauté) si on veut épuiser le levier — rendement
  décroissant (104/108).

## Variables d'expérience

Définition de `behavioral_diversity` (descripteurs inclus, normalisation), `select` (elitist/diverse),
décompo par descripteur (stratégie vs survie). Réutilise tous les autres knobs (n_carry, tournament_size,
pop_cap, preserve_dims) d'EDR 108.
