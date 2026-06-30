---
id: EDR-117
type: EDR
title: Learnabilité compositionnelle — les deux substrats échouent à ~5 cachés (Issue 2, taille requise)
status: validated
gate: null
verdict: NEUTRE (Issue 2 — TAILLE_REQUISE ; PAS issue 1 ni issue 3)
---

# EDR 117 : Learnabilité compositionnelle — Issue 2 (les deux bras échouent à ~5 cachés)

## Contexte

EDR 115 a établi le **barreau-0** : sur une tâche mono-contingence (obs fixe → action cible,
crédit immédiat), le substrat torch (autograd) bat le legacy hebbien/TD numpy de façon robuste
(médiane +0.358, 10/10 seeds, sign_p 0.002). La convergence EDR 104-113 a montré que le verrou
de l'apex craft→chasse est le **SUBSTRAT** (capacité d'apprentissage), pas le monde ni la sélection
ni la taille du réseau seule.

La question ici est le **barreau-1 compositionnel** : un substrat torch apprend-il une contingence
**2-étapes X-gate-Y** — faire X en S1 (récompense différée, nulle), puis Y en S2 récompensé SEULEMENT
si X a été fait — que le legacy ne peut pas ? C'est l'apex craft→chasse en miniature. L'observation S2
n'encode PAS `did_X` → l'agent doit MÉMORISER via la récurrence (vraie composition).

Lien **EDR 113** (γ-sweep horizon-crédit no-op, Issue 2) : si torch avait gagné ici, on aurait isolé
POURQUOI le γ-sweep n'a pas aidé — la règle d'apprentissage ne savait pas exploiter l'horizon, pas
« l'horizon est inutile ». EDR 117 répond différemment : ni le gradient ni l'horizon ne suffisent à
cette échelle, les deux bras sont bloqués par la taille/représentation.

## Méthode

- **Script** : `tools/substrate_ab_compositional.py` (Task 1, Session parallèle 2026-06-30, commit `fbec167`).
- **Tâche** : 2 étapes par trial. S1 : obs fixe `obs_a`, action X cible (`move=0`), reward=0 (différé).
  S2 : obs fixe `obs_b` (distinct de `obs_a`, n'encode pas `did_X`), action Y cible (`move=4`),
  reward=+1 SSI X fait en S1 ET Y correct en S2, sinon -1. Métrique = taux trials **pleinement corrects**
  (X-puis-Y, `hit`), début vs fin.
- **A/B apparié** : même seed, backends `legacy` vs `torch`. 5 seeds {0,1,2,3,4}, 150 trials, 8 agents.
- **Verdict** : `compute_ab_verdict` de `substrate_ab` (test de signe apparié, seuil band=0.05).
- Environnement : `AGISEED_QUIET_LOG=1 SABC_SEEDS=0,1,2,3,4 SABC_TRIALS=150 SABC_AGENTS=8`.

## Contrôle de dureté (anti-théâtre)

Avant de lire le verdict, le contrôle vérifie que la tâche compositionnelle est bien **plus dure** que
la mono-étape — sinon le verdict ne mesure rien (issue 3 = trop facile, garde-fou déclenché).

Run de référence mono-étape (`tools/substrate_ab.py`, 5 seeds, 300 ticks, 8 agents) :

| seed | legacy Δ (mono) | torch Δ (mono) |
|------|-----------------|----------------|
| 0 | +0.107 | +0.465 |
| 1 | +0.075 | +0.507 |
| 2 | +0.258 | +0.513 |
| 3 | -0.042 | +0.298 |
| 4 | -0.302 | +0.202 |
| **médiane** | **+0.075** | **+0.465** |

Verdict mono = `GRADIENT_GAGNE`, médiane diff +0.358, sign_p=0.062 (5 seeds, plancher).

Legacy Δ mono médian = **+0.075** → le legacy APPREND la contingence simple.
Legacy Δ compo médian = **-0.007** → le legacy ÉCHOUE la compositionnelle.
Contrôle passé : **tâche compositionnelle bien plus dure** (Δ passe de +0.075 à -0.007 pour legacy).
Issue 3 (garde-fou « trop facile ») : **NON déclenché**.

## Résultats — A/B compositionnel

| seed | legacy Δ compo | torch Δ compo | diff (torch−leg) | legacy hit_end | torch hit_end |
|------|----------------|---------------|-----------------|----------------|---------------|
| 0 | -0.020 | +0.010 | +0.030 | 0.000 | 0.010 |
| 1 | -0.017 | +0.000 | +0.017 | 0.000 | 0.000 |
| 2 | -0.003 | +0.014 | +0.017 | 0.000 | 0.051 |
| 3 | -0.007 | -0.003 | +0.003 | 0.057 | 0.054 |
| 4 | +0.017 | +0.051 | +0.034 | 0.061 | 0.155 |
| **médiane** | **-0.007** | **+0.010** | **+0.017** | **0.000** | **0.051** |

Verdict = `NEUTRE` (script : `median_diff=+0.017`, `grad_fav=5/5`, `sign_p=0.062`).

- Torch est favorable sur **5/5 seeds** mais les deltas absolus sont quasi-nuls (max +0.051, médiane +0.010).
- `hit_end` torch ≤ 0.155 sur tous seeds (5/5 essais pleinement corrects au mieux 15.5% → quasi-plancher).
- Legacy : 4/5 seeds avec Δ ≤ 0 ; seul seed=4 montre une trace (+0.017, hit_end=0.061).
- `sign_p = 0.062` : au plancher pour n=5 (test de signe, pas de puissance à 5 seeds).
- **Aucun des deux bras ne crack la tâche compositionnelle** à ce régime (~5 cachés, 8 agents, 150 trials).

## Verdict : ISSUE 2 — TAILLE_REQUISE

Ni le gradient ni le hebbien ne suffisent à cette échelle. Les deltas absolus proches de 0 indiquent
que la taille du réseau (représentation/capacité de mémorisation récurrente) est un verrou conjoint :
il ne suffit pas d'avoir la meilleure règle d'apprentissage si le substrat est trop petit pour encoder
la structure compositionnelle (S1→S2 conditionnel via récurrence).

Comparaison synthèse :

| tâche | legacy Δ médian | torch Δ médian | verdict |
|-------|-----------------|----------------|---------|
| mono-étape (EDR 115) | +0.075 | +0.465 | GRADIENT_GAGNE |
| compositionnelle (EDR 117) | -0.007 | +0.010 | NEUTRE (Issue 2) |

La **chute de torch** (+0.465 → +0.010) est aussi sévère que celle de legacy (+0.075 → -0.007) :
les deux bras s'effondrent face à la composition. Le signal torch (5/5 en direction) est réel mais
microscopique — insuffisant pour conclure que la règle seule lève le verrou compositionnel.

## Caveats

1. **Puissance insuffisante** : n=5 seeds, sign_p au plancher 0.062. Même si torch est 5/5 favorable,
   on ne peut pas conclure à issue 1 sans plus de seeds ou des deltas absolus plus larges.
2. **Taille non variée** : le run est à la taille de production (~5 cachés). Un sweep taille (20/50/100
   cachés) permettrait de trancher taille vs règle ; non fait ici (hors-scope de ce barreau).
3. **Trials limités** : 150 trials. La composition peut nécessiter une période de chauffe plus longue
   (curriculum progressif S1→S2 différé, ou plus de trials).
4. **Même bornage qu'EDR 115** : micro-tâche proxy, PAS une preuve de transfert apex en prod.

## Conséquences

- La **porte de décision torch-prod** reste verte (EDR 115 la justifie) mais le barreau compositionnel
  exige **taille + gradient conjointement**, pas le gradient seul.
- Suite recommandée : (a) sweep taille cachés (20/50/100) sur la tâche compositionnelle — isole si
  la représentation seule suffit ou si gradient×taille est nécessaire ; (b) curriculum progressif
  (récompenser d'abord X seul, puis Y|X) — réduit la difficulté du crédit différé.
- Lien EDR 113 clarifié : le γ-sweep no-op était bien Issue 2 (substrat bloqué), pas Issue 1
  (règle insuffisante) — EDR 117 confirme que la taille est aussi en cause, pas seulement la règle.

## Liens

- `[[sota-gap-substrate]]` — audit SOTA : ~5 cachés numpy sans gradient = verrou identifié
- `[[nas-bottleneck-is-substrate-not-search]]` — convergence leviers réfutés → substrat
- `[[coop-competence-is-population-property]]` — apex = 5 leviers réfutés (dont taille EDR 105/110)
- EDR 113 — γ-sweep no-op, Issue 2
- EDR 115 — barreau-0 : gradient bat hebbien sur mono-contingence
- Outils : `tools/substrate_ab_compositional.py`, `tools/substrate_ab.py`
- Commit banc : `fbec167` (branche `feat/d1-prod-pairing`)
