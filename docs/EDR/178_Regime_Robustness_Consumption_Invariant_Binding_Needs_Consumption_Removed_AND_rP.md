---
id: EDR-178
type: EDR
title: Robustesse aux régimes — la consommation est le verrou maître INVARIANT ; F2/F4 n'émergent PAS sous stress ; le binding in-world exige DEUX conditions (consommation-retirée ET r·P suffisant) — unifie EDR-176+177
status: accepted
gate: G1
verdict: CONSOMMATION_INVARIANTE_F2F4_INERTES_BINDING_A_DEUX_CONDITIONS
---

# EDR-178 : le binding in-world = consommation-retirée ET r·P suffisant (unifie 176+177)

> Territoire BIND/torch. Suites d'EDR-177 (robustesse aux régimes). Driver `tools/factorial_regime_sweep.py`
> (rejoue `compare_factorial` en 3 régimes). **Réfute 2 prédictions d'émergence ; unifie EDR-176 et EDR-177.**

## Contexte

EDR-177 a établi la structure de facteurs du binding in-world **dans un seul régime** (couche-1 neutralisée,
payoff modéré) : `no_consume` domine (+0.465), `weightless` (F2) et `conditional_credit` (F4) inertes. Ce
chantier teste si cette structure est **invariante au régime** via deux prédictions falsifiables : (P2) F2
émerge sous survie contrainte ; (P3) F4 émerge sous payoff rare (et la cellule propre binde-t-elle encore ?).

## Méthode

`factorial_regime_sweep.py` : rejoue le factoriel 2⁴ (`compare_factorial`, EDR-177) dans 3 régimes ×
K=12 seeds, compare les 4 effets principaux (`_factorial_effects`, poolés sur 8 cellules/niveau) + le
verdict cellule-0 par régime (garde-fou power-evaporation K≥12). Régimes **calibrés empiriquement** (sonde
survie+kills, 3 tours) :

- **neutralisé** = baseline EDR-177 (energy=250, bm=0.05, night=False, prey 15/300, fp=3).
- **létal** = tampon d'énergie RÉDUIT (energy=150). **Découverte de calibration** : `night=True` extermine la
  cohorte (survivants 0-3/30, confond #1 d'EDR-172), car **le drain-énergie des throws eux-mêmes** (chaque
  throw −5 à −10, cohorte no_consume throw beaucoup) plafonne la survie ; toute pression AJOUTÉE tue. Le
  levier propre = réduire le tampon → NWDK (portage exempté) survit 6.5 vs N-heavy (porte) 3.0 = **gap de
  survie F2 2×** observé.
- **rare** = proies rares (prey 3/6, kills ~2-5) + survie soutenue (fp=6, energy=800) — sinon famine (la
  proie est cible ET nourriture).

## Résultat (K=12)

**Effets principaux (diff propre − confond) par régime :**

| facteur | neutralisé | létal | rare |
|---|---|---|---|
| **no_consume** | **+0.465** | **+0.396** | **+0.247** |
| weightless (F2) | +0.014 | +0.009 | −0.006 |
| dense (F3) | +0.168 | +0.139 | −0.048 |
| conditional_credit (F4) | +0.008 | −0.004 | −0.007 |

**Cellule-0 (tout-propre) par régime :**

| régime | diff | kills | verdict | sign_p |
|---|---|---|---|---|
| neutralisé | +0.348 | 346 | GRADIENT_GAGNE (BINDE) | 5e-4 |
| létal | +0.333 | 426 | GRADIENT_GAGNE (BINDE) | 5e-4 |
| rare | +0.005 | 8 | NEUTRE (PLAT) | 0.125 |

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT (P1 — consommation invariante) : `no_consume` est le facteur DOMINANT dans les 3 régimes**
  (+0.465 / +0.396 / +0.247) — toujours largement le plus gros effet. La cellule propre binde sous survie
  contrainte (létal +0.333, K≥12) exactement comme au repos.
- **FAIT (P2 RÉFUTÉE) : F2 (weightless) n'émerge PAS sous survie contrainte** (+0.009 en létal ≈ +0.014 au
  repos), MALGRÉ un gap de survie 2× (NWDK vs N-heavy) à la calibration. L'avantage de survie du portage
  exempté ne se TRADUIT PAS en avantage de binding.
- **FAIT (P3 RÉFUTÉE, double) : F4 (conditional_credit) n'émerge PAS sous rareté** (−0.007) ET **la cellule
  propre S'EFFONDRE** en rare (NEUTRE, +0.005, kills=8).
- **INTERPRÉTATION — le binding in-world exige DEUX conditions nécessaires, ce qui UNIFIE EDR-176 et 177.**
  En rare, `no_consume` garde le plus gros effet (+0.247) TANDIS QUE la cellule propre est plate : les
  cellules consommatrices anti-bindent encore (l'artefact mécanique opère), mais retirer la consommation ne
  fait qu'ANNULER l'anti-bind sans CRÉER le positif — car `r·P` (kills=8) est sous le plancher de rétention
  (EDR-176). Donc : **(i) consommation-retirée** (EDR-177, tue l'anti-bind mécanique) **ET (ii) r·P suffisant**
  (EDR-176, fournit le signal) sont TOUTES DEUX nécessaires. Neutralisé/létal ont les deux → bindent ; rare a
  (i) mais pas (ii) → plat.
- **INTERPRÉTATION — modèle causal SIMPLIFIÉ et durci** : le binding in-world est gouverné par exactement deux
  leviers — la **consommation** (mécanique, maître, régime-invariant) et la **densité de payoff `r·P`**
  (nécessaire). Le **coût-portage (F2) et la conditionnalité du crédit (F4) sont GÉNUINEMENT inertes**
  in-world, même sous leur stresseur prédit. C'est un modèle plus fort que « 4 facteurs qui pourraient
  compter ». La survie contrainte NE casse PAS le binding ; la rareté du payoff, OUI.

## Portée / Bornage (honnêteté)

1. **Colonne `dense` non-comparable entre régimes** : neutralisé/létal contrastent prey 300-vs-15, rare
   contraste 6-vs-3 (les deux rares). Le `dense` en rare (−0.048) est un contraste faible/bruité, à ne PAS
   sur-lire ; seuls no_consume/weightless/conditional_credit se comparent proprement en colonnes.
2. **Survie fine sous stress** (létal ~3-6 vivants, rare ~9) → estimations de binding plus bruitées dans ces
   régimes. Le SIGNE et l'ordre des effets sont robustes (no_consume dominant partout ; verdicts cellule-0
   nets : BINDE létal K≥12, NEUTRE rare) ; les magnitudes exactes moins.
3. **Le régime « létal » propre = tampon réduit, pas la nuit** — `night=True` était inutilisable
   (extinction). C'est une contrainte structurelle (drain-throw ↔ survie), pas un choix libre. « Survie
   contrainte » ici = énergie basse, pas mortalité nocturne.
4. **P2/P3 réfutées à K=12** : F2/F4 n'émergent pas DANS CES régimes calibrés. Un stress plus extrême mais
   survivable (introuvable ici à cause du drain-throw) pourrait en principe les réveiller ; le fait empirique
   reste qu'aucun régime survivable testé ne les fait émerger.

## Suite

- **CLÔT la robustesse-aux-régimes** avec un modèle causal à DEUX leviers : binding in-world ⇔
  consommation-retirée (EDR-177) ET `r·P` suffisant (EDR-176). F2/F4 inertes confirmés.
- **Leçon générale** : pour faire binder une action outil in-world, il faut (i) qu'elle ne consomme pas son
  indice-contexte ET (ii) que son payoff soit assez dense (`r·P` au-dessus du plancher). Ni le coût-portage
  ni la conditionnalité du crédit ne comptent — les régler est un NON-LEVIER.
- **Découverte réutilisable** : dans cette biosphère, le drain-énergie du geste étudié couple survie et
  comportement → un régime « létal survivable » est difficile à cadrer ; réduire le tampon d'énergie est le
  levier de pression le moins destructeur.
- Ouvertures : un banc où `r·P` et la survie sont découplés proprement (nourriture ≠ cible) permettrait de
  pousser le stress sans famine.

Lignée : **UNIFIE [[torch-inworld-integration-plan]] (EDR-176 r·P + EDR-177 consommation)** — binding =
2 conditions nécessaires. Réfute mes prédictions F2/F4. Confirme [[decisive-substrate-thesis-test]] (substrat
capable, verrou = structure de tâche : consommation + densité). Applique [[power-evaporation-guardrail]]
(K≥12, rare NEUTRE non forcé positif).
