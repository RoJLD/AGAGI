# EDR 100 — TARIF=METABOLISME : le drain biologie est le métabolisme du phénotype évolué

## Contexte

EDR 099 a décomposé le drain intrinsèque de Lewis (~12/tick, famine au tick 5, à `N_APEX=0`) et nommé la phase
**biologie** comme coupable (90% du drain). EDR 100 **sous-décompose** cette phase pour cibler le sous-poste —
première intervention chirurgicale de la chaîne, après six diagnostics. Instrumentation : 6 sous-captures opt-in
dans `_resolve_biology` (réutilise `trace_energy_sinks`), décomposant la phase biologie en
`metab / terrain / carry / autres`. Pré-enregistrement :
`docs/superpowers/specs/2026-06-24-EDR100-Biology-Subdecomposition-design.md`.

## Le verdict : TARIF=METABOLISME

Le **métabolisme** écrase les autres sous-postes de la phase biologie.

| sous-poste | énergie/tick/agent (magnitude brute) | poste |
|---|---|---|
| **métabolisme** | **13.47** | `base_metabolism(0.25) × phenotype_energy_drain` (l.637) |
| terrain | 0.23 | drain de biome (l.640) |
| carry | 0.28 | `carry_weight × 0.5` (l.651) |
| autres (gains) | −2.78 | approach_reward + forage Fruit (+20) + jump/heal/hunt |

(R=4, n_eval=8, seed=100, n=1453, commit `3fdf18e`. Cohérence : 13.47+0.23+0.28−2.78 = 11.20 = phase biologie
d'EDR 099.) **Le métabolisme est ~50× le terrain et le carry.**

> **Discipline de lecture (imposée par la revue) :** on rapporte les **magnitudes brutes** (/tick), pas les
> parts en %. Le % du métabolisme « dépasse 100% » du drain biologie (120.3%) **uniquement** parce que les gains
> de forage (`autres` = −2.78) rétrécissent le dénominateur net. Le verdict ne tient **pas** à cette arithmétique
> de parts fragile — il tient à un écart de **magnitude ×50** entre le métabolisme et les autres sinks bruts.

## Le mécanisme : un trait métabolique ÉVOLUÉ, pas un paramètre de monde

`metab = base_metabolism × phenotype_energy_drain`. À `N_APEX=0` (nuit OFF, donc pas de modulateur), le bucket
métabolisme est **pur** (vérifié : la branche nuit est morte). Avec `base_metabolism = 0.25` (la valeur config)
et `metab = 13.47/tick`, on déduit :

> **`phenotype_energy_drain ≈ 54`.**

Or `phenotype_energy_drain` est un **trait évolué du génome** (phénotype), **pas** un knob de monde. Le mur de
Lewis n'est donc pas un paramètre mal réglé : c'est que **le phénotype des champions, forgé en *stoneage*, est
intrinsèquement trop gourmand en énergie** pour l'économie de forage de Lewis. `base_metabolism` (0.25) n'est
qu'un petit multiplicateur ; le coût réel vient du trait évolué (~54).

C'est l'aboutissement de la chaîne. Les six EDR convergent :

| EDR | Levier | Verdict |
|---|---|---|
| 090 | létalité | NÉGATIF PROFOND (pas de barreau ; « adapter le substrat AVANT de durcir ») |
| 093 | revenu | inerte |
| 094 | densité apex | inerte → MUR INTRINSÈQUE |
| 098 | brain_cost/surprise | inerte (clampé) |
| 099 | décomposition | phase **biologie** 90% |
| **100** | sous-décomposition | **métabolisme** = `base × phenotype_energy_drain ≈ 54` |

Le mur de Lewis est un **trait métabolique évolué inadapté**. Cela rejoint EDR 090 (« adapter le substrat
AVANT de durcir ») et les findings de la session NAS (le goulot est le **substrat**, pas la recherche/sélection).

## Le vrai levier (re-pointé) : le trait métabolique du substrat

EDR 100 localise le drain au **métabolisme phénotypique évolué**. Deux leviers, à mesurer en EDR 101 :

- **rescale monde** : `base_metabolism` (0.25) multiplie le trait — le baisser réduit le drain linéairement.
  MAIS il multiplie un trait de ~54 : même `base_metabolism = 0.05` laisse ~2.7/tick. Tester si un rescale
  suffit à débloquer la survie (sweep `base_metabolism`, même harnais que 093/094/098).
- **adapter le substrat** : mesurer la distribution de `phenotype_energy_drain` dans les champions (uniforme ~54 ?
  variable ?), puis **évoluer en Lewis** des champions à métabolisme plus sobre (sélection sur la survie en
  Lewis, pas en stoneage). C'est le levier d'amont que 090 désignait : adapter le phénotype au monde-cible.

Si un rescale `base_metabolism` suffit → le mur était un mismatch d'échelle réparable par config. Si non → il
faut ré-évoluer le substrat pour Lewis (mismatch de trait profond, cohérent NAS).

## Honnêteté & méthode

- **Mesure, pas supposition (×3).** La chaîne 098→099→100 a vaincu l'intuition trois fois : heal (faux),
  brain_cost (faux), throw (faux, 6%). La sous-décomposition nomme le coupable : le métabolisme phénotypique.
- **Couverture & cohérence vérifiées.** Les 4 sous-postes télescopent exactement vers la phase biologie d'EDR
  099 (13.47+0.23+0.28−2.78 = 11.20, à ~1e-15 par agent). Le bucket métabolisme est **propre** à `N_APEX=0`
  (branche nuit morte → isole `base × phenotype_energy_drain`).
- **Robustesse du verdict.** Il repose sur un écart de magnitude ×50, pas sur la part en % (dont le dénominateur
  est gonflé par les gains de forage négatifs — caveat documenté ci-dessus).
- **Instrumentation inerte.** Les 6 sous-captures sont gardées par `trace_energy_sinks` (défaut OFF) → zéro
  impact sur 087-099 et les sessions parallèles (non-régression : 23 tests verts, flag jamais posé hors mesure).
- **Reproductibilité.** `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ; lecture `_e_bio`
  read-only ; normalisation par âge.
- **Limite connue.** La sous-décomposition s'arrête au sous-poste métabolisme (`base × phenotype_energy_drain`) ;
  le partage exact entre le knob `base_metabolism` et le trait `phenotype_energy_drain` (≈54) est déduit, pas
  mesuré poste-à-poste — mais le trait domine clairement (base=0.25 fixe).

## Variables d'expérience

Sous-poste **métabolisme** (le coupable) → **`base_metabolism`** (rescale monde, sweepable) et
**`phenotype_energy_drain`** (trait évolué ~54 — mesurer sa distribution ; ré-évoluer en Lewis). Outils :
`tools/lewis_survival_sweep.py` (`main_decompose`, `_measure_drain` clés `bio_*`, `_verdict_bio`),
`src/worlds/world_1_stoneage.py` (sous-hooks opt-in `_e_bio`). Provenance : `results/lewis_drain_decompose_100.json`
(R=4, n_eval=8, TARIF=METABOLISME). Lignée : 090→093→094→098→099→**100**.
