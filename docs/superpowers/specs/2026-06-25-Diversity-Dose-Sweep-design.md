# Design — Sweep dose de diversité (courbe diversité→apex)

Date : 2026-06-25

Trilogie champion close (EDR 097→102→103) : le déficit du champion est la MONOCULTURE, pas le génome
ni l'architecture ([[coop-competence-is-population-property]]). La compétence apex coopérative est une
propriété ÉMERGENTE de la diversité de population. Reste une seule piste du levier diversité : **doser**
la diversité — balayer la fraction de clones (0 % = soupe diverse → 100 % = monoculture) pour tracer la
courbe diversité→apex et localiser où la coordination du pack s'effondre.

## Question scientifique

Où la chasse coopérative apex s'effondre-t-elle quand on remplace progressivement une population diverse
par des clones d'un même génome ? Forme du collapse : **linéaire** (diversité = continuum dosable),
**seuil net** (fraction critique de diversité), ou **plateau-puis-chute** ?

## Contexte

`tools/target_competence_probe.py` a 3 modes (`tabula` soupe fraîche diverse, `champion` clones HoF,
`mono_fresh` clones d'UN génome frais), la métrique couche-2 réparée (`stoneage_competence` = fractions
de participation hunt/apex/lance, EDR 096) et la décompo `frac_apex`/`frac_tool`/`total_mammoth`/
`total_spears` par ère câblée. EDR 102 (agents aplatis) : tabula apex 0.211, mono_fresh 0.158 — ce sont
**exactement** les deux extrémités d'un balayage de fraction de clones d'un génome frais. Le knob
`CT_PRESERVE_DIMS` existe (`run_probe:65`, défaut OFF) et est un **no-op pour l'apex** (EDR 103) → reste
OFF pour ce sweep.

## Hypothèse

- **Collapse à seuil** → il existe une fraction critique de diversité en-deçà de laquelle la
  coordination du pack tient, au-delà elle s'effondre. Levier actionnable (« garder ≥ X % de diversité »).
- **Collapse linéaire/monotone** → la diversité est un continuum : chaque clone retiré coûte de l'apex.
- **Plateau-puis-chute** → robustesse jusqu'à une dose, puis effondrement rapide.

## Architecture — petit build + run

### Unité 1 — mode `mixture` + knob `CT_CLONE_FRAC` (build)

`tools/target_competence_probe.py`, en réutilisant tout l'existant (soupe, `from_genome`, décompo) :

- En-tête de `run_probe` (près de `preserve_dims`, `run_probe:65`) :
  `clone_frac = float(os.environ.get("CT_CLONE_FRAC", "0.0"))`.
- Nouvelle branche `elif mode == "mixture":` (entre `mono_fresh` et le `else` tabula) :
  - `genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
    keep_memory=False, shared_db=shared_db, config=config)` — soupe de N génomes frais (identique
    `tabula`/`mono_fresh`).
  - `n_clones = round(clone_frac * num_agents)` (clamp implicite : `clone_frac ∈ [0,1]` par convention
    d'appel ; `round` → entier).
  - `clone_g = genomes[0]` (source déterministe, appariable — comme `mono_fresh`).
  - Construire la population de taille EXACTEMENT `num_agents` :
    - `n_clones` agents : `a.from_genome(clone_g, preserve_dims=preserve_dims)`.
    - `num_agents - n_clones` agents diversifiés : itérer `genomes[1:]` (génomes frais distincts ≠ le
      clone) et, si la soupe est épuisée, reboucler sur `genomes[1:]` (garde-fou ; en pratique
      `num_agents - n_clones ≤ num_agents - 0 = N`, et on a N génomes, donc `genomes[1:1+(N-n_clones)]`
      suffit tant que `n_clones ≥ 1`. À `n_clones = 0`, utiliser `genomes[0:N]` entiers = tabula).
  - Chaque agent ajouté via `env.add_agent(a, energy=50.0)` (identique aux autres branches).
- Propriété d'identité (à vérifier au run, pas à coder en dur) : f=0 → 0 clone + N frais ≡ `tabula` ;
  f=1 → N clones + 0 frais ≡ `mono_fresh`. Un seul chemin de code génère toute la courbe.

Construction de population (pseudo, à adapter à l'indexation exacte) :

```python
elif mode == "mixture":
    genomes, _ntm = init_primordial_soup(num_agents=num_agents, import_agent_id=None,
                                         keep_memory=False, shared_db=shared_db, config=config)
    n_clones = round(clone_frac * num_agents)
    clone_g = genomes[0]
    n_diverse = num_agents - n_clones
    # diversifiés : génomes frais DISTINCTS du clone (genomes[1:]), rebouclage défensif
    diverse_pool = genomes[1:] if len(genomes) > 1 else genomes
    for j in range(n_clones):
        a = MambaAgent(); a.from_genome(clone_g, preserve_dims=preserve_dims)
        env.add_agent(a, energy=50.0)
    for j in range(n_diverse):
        g = diverse_pool[j % len(diverse_pool)]
        a = MambaAgent(); a.from_genome(g, preserve_dims=preserve_dims)
        env.add_agent(a, energy=50.0)
```

Note d'identité aux bouts : à f=0, `n_clones=0` → boucle clone vide, `n_diverse=N` → on tire
`genomes[1:]` rebouclé (N agents diversifiés mais le pool exclut `genomes[0]`). C'est ≈ tabula (N
génomes frais diversifiés) mais PAS strictement identique (genomes[0] absent du pool, un autre rebouclé).
Acceptable : le bras f=0 reste une soupe diverse de N génomes frais ; la cohérence avec tabula EDR 102 se
vérifie au régime absolu (~0.211), pas à l'identité bit-à-bit. Documenté comme garde-fou (voir
anti-théâtre).

### Unité 2 — run 5 points (pas de code)

5 invocations appariées, sweet spot, K=8, 40 agents, 300 ticks :

```
AGISEED_QUIET_LOG=1 CT_MODE=mixture CT_CLONE_FRAC=<f> CT_TARGET=stoneage \
  CT_K=8 CT_NUM_AGENTS=40 CT_MAX_TICKS=300 CT_METAB=0.25 CT_PAYOFF=3.0 \
  python -u tools/target_competence_probe.py
```

avec `f ∈ {0.0, 0.25, 0.5, 0.75, 1.0}` → `n_clones ∈ {0, 10, 20, 30, 40}`. Sauvegarder chaque JSON en
scratchpad entre les runs (ils s'écrasent, seed=0). Tracer `frac_apex` (et `median_competence`,
`frac_tool`) vs f. Comparer f=0 à tabula EDR 102 (0.211) et f=1 à mono_fresh (0.158).

## Garde-fous anti-théâtre

- **Régime absolu = le résultat** : tracer la COURBE `frac_apex` vs f (5 points), pas un verdict binaire.
  La forme (seuil / linéaire / plateau) EST le livrable.
- **Cohérence des bouts** : f=0 doit retomber sur tabula EDR 102 (~0.211) et f=1 sur mono_fresh (~0.158).
  Un écart > bruit inter-ère signale un changement de régime (ou le caveat d'identité f=0 ci-dessus) → le
  signaler explicitement.
- **Apparié** : même seed par ère (`SeedManager(i).seed_boundary(0)` déjà en place) → contrastes appariés
  par ère entre fractions adjacentes.
- **Décompo par ère, jamais le scalaire nu** : rapporter `frac_apex`/`frac_tool`/`total_mammoth` par ère
  pour chaque fraction.
- **Population = N exactement** : le smoke vérifie `n == num_agents` (pas de fuite de compte).

## Tests

- Smoke `slow` (`tests/sandbox/test_diversity_dose_probe.py`) :
  `run_probe("stoneage", k=1, num_agents=20, max_ticks=80, shared_db, mode="mixture")` avec
  `monkeypatch.setenv("CT_CLONE_FRAC","0.5")` + `CT_METAB=0.25` + `CT_PAYOFF=3.0` →
  tourne SANS erreur ; `per_era[0]["n"] == 20` (population exacte = N, garde-fou compte) ;
  `per_era[0]` a `frac_apex`/`frac_tool`/`total_mammoth`/`total_spears` ; `median_competence ∈ [0,1]`.
- Non-régression : `test_mono_fresh.py` + `test_live_harvest.py` (modes existants, sans `CT_CLONE_FRAC`)
  restent verts — le défaut `0.0` et la nouvelle branche n'altèrent pas `tabula`/`champion`/`mono_fresh`.

## Hors périmètre (YAGNI)

- Pas de wrapper de sweep (5 invocations, pattern EDR 102/103).
- Pas de clone-champion (option 2 = chantier suivant SI la forme du collapse justifie de vérifier
  l'indépendance au génome).
- Pas de modif de `from_genome` ni de `preserve_dims` (reste OFF, no-op EDR 103).
- Pas de grille plus fine que 5 points (raffiner seulement si un seuil net apparaît entre deux points).

## Suite (selon verdict)

- **Seuil net** → localiser la fraction critique de diversité (raffiner autour du point de bascule) ;
  levier de déploiement (« maintenir ≥ X % de diversité au transfert/RSI »).
- **Linéaire/monotone** → la diversité est un continuum dosable ; chaque clone coûte de l'apex.
- **Plateau-puis-chute** → robustesse jusqu'à une dose tolérable.
- Option 2 (sweep clone-champion) pour confirmer que la forme est indépendante du génome cloné.

## Variables d'expérience

`CT_CLONE_FRAC` (dose diversité→apex, AXE PRINCIPAL), génome cloné (frais [ce chantier] vs champion
[option 2]), `coop_reward` (ablation → l'écart diverse/mono disparaît-il ?), K ères/seeds (puissance ;
ici K=8). `preserve_dims` ignoré (no-op apex, EDR 103).
