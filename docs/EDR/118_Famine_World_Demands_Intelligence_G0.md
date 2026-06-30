---
id: EDR-118
type: EDR
title: FamineWorld EXIGE l'intelligence (G0) — 2e monde reel distinct, mais la demande mesuree est le TRANSFERT de competence generale, pas le stockage
status: accepted
gate: G0
tests: [SDR-G0]
verdict: EXIGE
---

# EDR 118 : FamineWorld EXIGE l'intelligence (G0)

## Contexte

Le fil directeur AGI a un verrou **surdéterminé par 6 chemins** : le répertoire-monde / substrat est le
goulot (EDR 105/108/110/113 + transfert direct NEUTRE EDR-116). G0 (EDR-112) avait validé que stoneage et
soup EXIGENT l'intelligence, mais aussi que le répertoire du curriculum est **dégénéré** : agricultural
VOID, industrial = stoneage byte-déguisé → **soup et stoneage sont les seuls mondes réels, et ils
partagent le moteur** (soup = stoneage features OFF). Pivot acté : **construire un 2ᵉ monde GENUINEMENT
distinct** (causalité différente, même contrat I/O 59/108) PUIS re-mesurer le transfert G1.

`FamineWorld` (spec 2026-06-30) est ce monde : pénurie **cyclique** (abondance ↔ famine, régén nourriture
gelée en famine) + **stockage à coût** (cache d'inventaire auto-consommé à la disette). Succès = **acte
présent → bénéfice futur** (gratification différée), une compétence que stoneage **n'exige ni n'enseigne**
(forage immédiat). Cet EDR consigne la **1ʳᵉ porte** : le monde exige-t-il l'intelligence (G0) ?

## Méthode

Instrument préexistant `tools/s2_demand.py` (FamineWorld câblé dans `WORLDS`, commit du chantier). Champion
**#1 du HoF** (génome évolué *en stoneage*, le seul HoF disponible) cloné, contre 4 baselines
(random_genome, random_action, reflex_naive, reflex_prudent). Survie individuelle agrégée par ère, médiane
par ère = unité d'appariement ; verdict = test de cohérence life_score (IUT, le champion doit battre le
meilleur baseline sur sa fitness d'entraînement, sinon VOID) PUIS demande sur survie (Cliff δ + p, Holm).
Powered (K via analyse de puissance), `with_db=False`. **Répliqué sur 2 seeds** (2026, 7).

`benchmark_mode=True` (cohorte fixe, **pas de reproduction/mutation**), `night_enabled=False` (le harnais
S2 coupe la nuit uniformément sur TOUS les mondes — équitable), `current_era=10_000` (scaffolds OFF).

## Constat — EXIGE (robuste sur 2 seeds)

| seed | verdict | p_monde (Holm) | Cliff δ (vs random_action) | ratio survie | life_p (cohérence) | censuré |
|---|---|---|---|---|---|---|
| 2026 | **EXIGE** | 0.003 | +0.92 | [3.74, 4.67] | 0.011 | 0% |
| 7 | **EXIGE** | 0.003 | +0.924 | [4.08, 4.96] | 0.005 | 0% |

Diagnostic survie médiane (n_eras=3, 200 ticks, seed 2026) : **champion 23.0** vs random_genome 5.5 vs
random_action 6.0 → **~4×**. **0% censuré** = tout le monde meurt avant max_ticks → la famine **mord**
réellement (pas un monde indolore), et le champion stoneage **domine** nettement.

**FamineWorld EXIGE l'intelligence** : un champion HoF survit ~4× un agent aléatoire, effet large
(δ≈0.92), significatif (p=0.003), cohérent sur le life_score (life_p<0.05), sans artefact de censure.

## Investigation d'un red flag (anti-théâtre)

Au seed 2026, les chiffres affichés (δ=0.92, ratio[3.74,4.67], p=0.003) étaient **byte-identiques à
stoneage** (EDR-112) — le motif exact qui avait révélé « industrial = stoneage déguisé ». Vérifié :
1. L'affichage **n'est pas hardcodé** (`_print_table` lit `s['cliff']`/`ratio_lo`/`ratio_hi` calculés).
2. Le diagnostic prouve que famine **diffère** de stoneage en **absolu** (champion 23 ticks, très court —
   la famine gèle 40% des ticks).
3. Au **seed 7**, les bornes **bougent** ([4.08, 4.96] ≠ [3.74, 4.67]) et life_p bouge (0.005 ≠ 0.011)
   → bootstrap **réel**, seed-dépendant.

**Résolu** : le match était une **coïncidence** — le δ **sature** (~0.92, proche du max) et p atteint un
**plancher** (0.003) dès qu'un avantage champion est massif dans N'IMPORTE quel monde létal ; seul le
ratio (qui bouge entre seeds) est discriminant. Pas de délégation cachée.

## Caveats (honnêteté — ce que cet EXIGE NE dit PAS)

1. **⭐ La demande mesurée est le TRANSFERT de compétence générale, PAS le stockage.** Le champion est
   évolué *en stoneage*, jamais *en famine*. Son avantage ~4× vient de compétences générales (forage en
   abondance, gestion d'énergie) qui **transfèrent** et confèrent un edge de survie — **PAS** de l'usage
   de la mécanique de stockage. La gratification différée que le monde est *conçu* pour exiger **n'est pas
   démontrée évolvable ici**.
2. **La mécanique de stockage est RÉELLE mais INERTE dans ce banc.** Distinctness prouvée en test unitaire
   (stockeur **55 ticks** vs non-stockeur **24**, coût honnête = portage `carry_weight×0.5/tick` +
   péremption `SPOIL_RATE=0.1`), MAIS aucune des 5 conditions S2 ne **stocke délibérément** (et
   `benchmark_mode` interdit l'évolution) → le cache ne différencie personne dans S2. La distinctness
   causale existe ; elle ne se manifeste que sous un agent *qui apprend à stocker*.
3. **VOID→EXIGE sous puissance** : le smoke K=2 donnait VOID (cohérence life_score, life_p=0.371) ; le run
   powered donne EXIGE (life_p<0.05). Smoke **sous-puissant**, pas un faux signal — motif « signal sous
   puissance » dans le sens **bénin** (le powered confirme, il ne dégonfle pas).
4. **Harnais** : `benchmark_mode` (pas de repro), nuit OFF (harnais, uniforme tous mondes), KuzuDB ambiant
   actif (erreurs de clé dupliquée = corruption **logging seul** ; intégrité sim conservée, précédent EDR
   113/095) → déterminisme partiel, même caveat qu'EDR-112.

## Conséquences

- **G0-famine FRANCHIE** : `FamineWorld` est un monde **réel, létal, exigeant l'intelligence**, et
  **causalement distinct** (mécanique de stockage prouvée), câblé dans les instruments G0
  (`s2_demand.WORLDS`) et G1 (`WORLD_FACTORY`). **1ᵉʳ vrai 2ᵉ monde** du répertoire (vs agri VOID,
  indus = clone stoneage). Le pivot « enrichir une affordance » a produit un monde qui **passe la porte
  de validité**.
- **Mais la porte franchie est la DEMANDE GÉNÉRALE, pas la demande SPÉCIFIQUE (stockage).** Ce qui reste
  ouvert et à plus fort levier : **la gratification différée est-elle ÉVOLVABLE dans ce substrat ?**
- **Prochain sous-chantier** (spec §9, ordre) : (1) **évoluer un champion DANS FamineWorld** (`WORLD_FACTORY`
  câblé) → le stockage émerge-t-il ? = test direct de l'évolvabilité du report ; (2) **G1 transfert**
  stoneage/soup → famine, apparié, n≥8 (`curriculum_transfer.py`). Si le stockage **n'émerge pas** sous
  évolution → finding **substrat** (la gratification différée n'est pas évolvable à bon marché),
  convergeant avec le verrou substrat (EDR 105/108/110/113/116) et l'axe gradient/torch (EDR-117 : les
  deux substrats échouent le means→ends compositionnel à ~5 caches). Si elle **émerge** → FamineWorld
  débloque une **vraie** mesure G1 (transfert d'une compétence que stoneage n'enseigne pas).

> Lecture stratégique : G0-famine confirme qu'on sait **construire** un monde distinct qui exige
> l'intelligence. La question AGI-critique se déplace d'un cran — non plus « a-t-on un monde distinct ? »
> (oui) mais « le substrat peut-il **apprendre** la compétence nouvelle que ce monde exige ? ».
