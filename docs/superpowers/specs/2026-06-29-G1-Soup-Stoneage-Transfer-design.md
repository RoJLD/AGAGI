# Design — G1 : la compétence GÉNÉRALISE-t-elle ? (transfert soup → stoneage, north-star)

> **Date** : 2026-06-29 · **Statut** : design validé (brainstorming), avant plan.
> **Porte** : G1 du [`FIL_DIRECTEUR_AGI`](../../roadmap/FIL_DIRECTEUR_AGI.md) (record `SDR-G1`), **north-star**.
> **Dépend de** : G0 (validité) — **franchie** (EDR 112 : stoneage + soup EXIGE).

---

## 1. Question falsifiable

**Évoluer en `soup` (monde simple, sensorimoteur) d'abord améliore-t-il la compétence finale en
`stoneage` (monde à outils) vs tabula-rasa-stoneage, à BUDGET COMPUTE ÉGAL ?** Si oui (`transfer_ratio`
> 1, test de signe significatif) → la compétence **généralise** à travers l'écart d'abstraction =
signature d'intelligence (vs mémorisation par-monde). C'est `SDR-G1`.

## 2. Pourquoi soup → stoneage (et pas le ladder par défaut)

G0 a révélé que le répertoire-monde du curriculum est dégénéré : `WORLD_FACTORY` = {stoneage,
agricultural, industrial} où **agricultural = VOID** (EDR 112) et **industrial = stoneage-déguisé**
(chiffres byte-identiques). Le ladder par défaut (stoneage→agri→indus) mesurerait du transfert à travers
un monde cassé + un clone → confondu. **Les seuls mondes réels, distincts et validés EXIGE sont soup et
stoneage.** soup → stoneage est donc la SEULE mesure de transfert propre disponible.

> **Caveat assumé** : `SoupWorld` hérite du moteur canonique `Biosphere3D` (soup = stoneage avec
> craft/gros-gibier OFF, pure survie). Le transfert traverse donc un **écart de features** (simple →
> complexe) au sein d'un moteur, pas deux moteurs indépendants. Mais G0 a prouvé des dynamiques de
> survie **distinctes** (soup δ=0.97/ratio~4.8 ; stoneage δ=0.92/ratio~4.2) → l'écart d'abstraction est
> réel et la mesure est légitime. Même I/O → transfert de champion sans incompatibilité de dimensions.

## 3. Ce que l'instrument mesure (exactement)

`tools/curriculum_transfer.py` (inchangé) compare **deux bras appariés par seed**, à budget égal :
- **curriculum** : `CurriculumRunner([soup, stoneage])` — graduation soup (plateau de maîtrise) → import
  du champion → stoneage → `C_curr` = compétence finale **stoneage** (dernier barreau).
- **tabula-rasa** : `CurriculumRunner([stoneage])` sur `total_eras` du curriculum (ne diplôme jamais,
  `c_floor=1.1`) → `C_tabula`.
- `ratio = C_curr / C_tabula` par seed → `compute_transfer_verdict` (test de signe) → **TRANSFERE /
  NEUTRE / NUIT**.

`metric="survival"` (`survival_competence`, médiane des âges — gradient réel au sweet spot EDR 085, le
signal autel/outil étant nul tant que le goulot d'exploration tient). `deterministic=True` →
`memory_retriever.stop()+clear()` AVANT la boucle (repro verrouillée, Dev #3) — **contrairement au run
G0**, G1 est exactement reproductible.

## 4. Extension minimale (la seule modif de code)

Ajouter `"soup": SoupWorld` à `WORLD_FACTORY` dans `main_curriculum.py` (+ import). **Additif,
non-régressif** : `DEFAULT_LADDER` inchangé, aucun chemin existant touché. `SoupWorld(config=None)`
accepte déjà `config` → compatible avec `WORLD_FACTORY[world_type](config)`. `_prepare_world` gère
`memory_retriever` de façon générique (SoupWorld en hérite).

## 5. Composants & flux

```
wire "soup" -> WORLD_FACTORY
pour seed in R:
  curriculum : run([soup, stoneage], deterministic) -> C_curr (stoneage final)
  tabula     : run([stoneage] x total_eras, deterministic) -> C_tabula
  ratio_seed = C_curr / C_tabula
verdict = sign_test({ratio_seed}) -> TRANSFERE/NEUTRE/NUIT
-> EDR (tests:[SDR-G1]) + SDR-G1 status + consolidate_records
```

## 6. Paramètres (variables d'expérience, loggés)

`CT_LADDER=soup,stoneage`, `CT_TARGET=stoneage`, `CT_METRIC=survival`, `R` seeds (défaut 0-4, étendre à
0-7 si le signe est marginal), `CT_MAX_ERAS` (12), `num_agents` (40), `max_ticks` (300), sweet-spot
énergie (`SWEET_METAB`/`SWEET_PAYOFF`, EDR 085).

## 7. Tests (TDD)

- **Câblage** : `WORLD_FACTORY["soup"] is SoupWorld` ; `_prepare_world("soup", cfg)` retourne une
  instance `SoupWorld` sans crash ; **non-régression** : `DEFAULT_LADDER == ["stoneage","agricultural",
  "industrial"]` inchangé, les clés existantes intactes.
- **Smoke transfert** : `run_transfer_experiment([0], ladder=["soup","stoneage"], target="stoneage")`
  avec un `run_era_fn` injecté (stub) retourne un verdict bien formé (réutilise les tests existants de
  `compute_transfer_verdict`, déjà purs/testés).
- Pas de re-test de `compute_transfer_verdict` (déjà couvert).

## 8. Garde-fous anti-théâtre

1. **Sanity avant verdict** : vérifier `C_tabula` (stoneage seul) **non-plancher** ET `C_curr`
   non-plancher — sinon le ratio est du bruit (cf. INCONCLUSIF de G0). Logger les deux compétences brutes.
2. **Budget égal** strict : le bras tabula tourne `total_eras` du curriculum (déjà géré par l'instrument).
3. **Repro** : `deterministic=True` ; mêmes seeds les deux bras (`seed_boundary(0)`).
4. **Caveat moteur partagé** (section 2) consigné dans l'EDR.

## 9. Périmètre & non-buts

- **Dans le périmètre** : câblage soup (1 ligne + import) + tests, **run réel** powered, **EDR**
  (verdict TRANSFERE/NEUTRE/NUIT) avec frontmatter `tests:[SDR-G1]`, MAJ `SDR-G1`, consolidate.
- **Hors périmètre (backlog)** : zéro-shot strict « premier contact » (sans entraînement sur la cible) ;
  stoneage→Lewis (EDR 090 penche négatif) ; mondes vraiment indépendants (= enrichir le répertoire-monde,
  la suite si NEUTRE/NUIT).

## 10. Interprétation (quel que soit le verdict)

- **TRANSFERE** : 1ʳᵉ preuve directe que la compétence généralise entre les 2 mondes réels → l'axe
  curriculum/Baldwin est vivant ; G1 franchie (sur la paire disponible).
- **NEUTRE/NUIT** : durcit le verrou répertoire-monde par **mesure de transfert directe** (et non plus
  par inférence comme EDR 105/108/110) → justifie scientifiquement le pivot « enrichir une affordance ».

## 11. Critères de succès du chantier

1. soup câblé, tests verts (câblage + non-régression).
2. Run réel : `transfer_ratio` médian + sign_p, compétences brutes non-plancher (sanity OK).
3. EDR consigné (`tests:[SDR-G1]`) → `tools/consolidate_records.py` peuple `tested_by[G1]`, graphe vert.
4. `SDR-G1` passé à `validated` (si TRANSFERE) ou annoté `refuted`/`open` (si NEUTRE/NUIT) selon le verdict.
