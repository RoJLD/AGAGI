---
id: EDR-131
type: EDR
title: "Le plafond 7/10 du gate (EDR 129/130) est une PATH-DEPENDENCE PRÉCOCE vers le bassin always-Y, PAS une limite de représentation : did_x est également décodable de H_S2 chez les seeds collapsés et bindeurs (AUC 0.90 vs 0.96, séparation 0.06 = NULLE), mais les collapsés saturent en always-Y dès le premier quart (y_rate 0.95 vs 0.76) → le sort est scellé tôt, avant que le gate n'apprenne à conditionner ; explique pourquoi les interventions tardives d'EDR 130 échouent (le bassin est déjà entré)"
status: validated
gate: null
verdict: "Diagnostic du plafond 7/10 (pourquoi les seeds 0,3,4 collapsent déterministiquement). probe_collapse_predictors : gate learned + capture PRÉCOCE (1er quart / 1re moitié) de 3 prédicteurs, corrélés à l'issue bind/collapse. (1) REPRÉSENTATION RÉFUTÉE : did_x_auc_early (décodabilité de did_x depuis H_S2) est ÉLEVÉE chez TOUS — bindeurs 0.956, collapsés 0.895, séparation 0.060 (nulle). La mémoire encode did_x proprement même chez les collapsés (0.82-0.96) → le collapse n'est PAS représentationnel (prolonge EDR 120 aux seeds collapsés). (2) ENTRÉE PRÉCOCE DU BASSIN : y_rate_start collapsés 0.948 (quasi always-Y) vs bindeurs 0.755 → les collapsés SATURENT en always-Y dès le 1er quart ; binding_gap_start collapsés -0.057 vs bindeurs 0.475 (séparation 0.532) → le sort est déterminé tôt. La politique s'enferme dans always-Y avant que le gate n'apprenne à router, alors que l'info did_x EST disponible. → Le plafond n'est pas une limite de représentation mais une PATH-DEPENDENCE d'initialisation/trajectoire précoce ; ça explique pourquoi les leviers TARDIFS d'EDR 130 (entropie/éligibilité) échouent (le bassin est déjà entré). Actionnable : intervenir TÔT (warm-start du gate, récompense différée, freiner la saturation-Y précoce)."
---

# EDR 131 : Le collapse du gate est une path-dependence précoce (always-Y), pas une limite de représentation

## Question

EDR 129 : le gate appris débloque le binding sur 7/10 seeds, collapse en always-Y sur 3/10 (seeds 0,3,4).
EDR 130 : les leviers crédit/optimisation TARDIFS (entropie, éligibilité) ne firment PAS ces collapses,
qui sont déterministes par seed → inféré « init/bassin ». Ce diagnostic teste POURQUOI : représentation
(la mémoire encode-t-elle mal did_x chez les collapsés ?) vs trajectoire (entrent-ils le bassin always-Y
tôt ?).

## Méthode

`probe_collapse_predictors` : pour chaque seed, gate learned (régime incitatif fade0.0/pen2) + capture
PRÉCOCE de 3 prédicteurs, corrélés à l'issue finale bind (gap_end>0.3) / collapse :
- **did_x_auc_early** : AUC du décodage linéaire de did_x depuis H_S2 (pooled agents×trials, 1re moitié)
  → hypothèse REPRÉSENTATION (réutilise `_decode_auc` d'EDR 120).
- **y_rate_start**, **binding_gap_start** : marginale Y et gap conditionnel du 1er quart → hypothèse
  TRAJECTOIRE (entrée précoce du bassin). 10 seeds.

## Résultats

n_bind = **7/10** (reproduit EDR 129/130 : bindeurs {1,2,5,6,7,8,9}, collapsés {0,3,4}).

| prédicteur | moyenne BINDEUR | moyenne COLLAPSÉ | \|séparation\| |
|------------|----------------:|-----------------:|--------------:|
| binding_gap_start | 0.475 | −0.057 | **0.532** |
| y_rate_start | 0.755 | 0.948 | 0.194 |
| did_x_auc_early | 0.956 | 0.895 | **0.060** |

Par seed (did_x_auc_early) : collapsés 0.821 / 0.906 / 0.960 ; bindeurs 0.921-0.989. did_x est **bien
décodable partout**.

## Interprétation

**(1) REPRÉSENTATION RÉFUTÉE.** did_x_auc_early est élevée chez les DEUX groupes (0.90 collapsés, 0.96
bindeurs ; séparation 0.06 = nulle). La mémoire récurrente encode did_x proprement MÊME chez les seeds
qui collapsent → le collapse n'est PAS un défaut de représentation. C'est le prolongement fin d'EDR 120
(« MEMORY_PRESENT ») aux seeds collapsés : l'info est là, disponible pour un readout linéaire, y compris
là où le gate échoue.

**(2) ENTRÉE PRÉCOCE DU BASSIN always-Y.** Les collapsés ont y_rate_start ≈ 0.95 (quasi always-Y) dès le
1er quart, contre 0.76 pour les bindeurs. Ils saturent la marginale Y TÔT — avant que le gate n'ait
appris à conditionner — et ne peuvent en sortir (P(Y)→1 tue le gradient différentiel). L'info did_x est
disponible mais INUTILISÉE car la politique s'est verrouillée.

→ **Le plafond 7/10 est une PATH-DEPENDENCE d'init/trajectoire précoce, pas une limite de capacité de la
mémoire.** Cela explique mécaniquement l'échec des leviers d'EDR 130 : entropie et éligibilité agissent
TROP TARD (le bassin always-Y est déjà entré au 1er quart). **Actionnable** : la fiabilité se gagnera par
une intervention PRÉCOCE — warm-start du gate (apprendre à lire did_x avant d'exposer à la récompense
jointe), récompense différée/annelée, ou freiner la saturation-Y précoce du substrat de base.

## Bornage / honnêteté

- **binding_gap_start prédit binding_gap_end est PARTIELLEMENT tautologique** (même trajectoire, 1er vs
  4e quart) : ce n'est PAS la preuve porteuse. Les deux évidences INDÉPENDANTES sont (a) l'AUC (réfute la
  représentation, mesure orthogonale au gap) et (b) y_rate_start (les collapsés sont déjà à 0.95 =
  mécanisme de saturation précoce). Le gap_start ne fait que dater le verrouillage.
- **AUC pooled agents×trials** (pas per-agent comme EDR 120) : mesure population grossière ; conflit
  d'identité d'agent possible. Mais l'écart NUL bind/collapse (0.06) est robuste à cette grossièreté
  (aucun des deux groupes n'est bas). Un per-agent affinerait sans changer le verdict de réfutation.
- **Path-dependence est INFÉRÉE de la corrélation, pas prouvée causalement** : le test causal = une
  intervention précoce (warm-start) qui RESCAPE les collapsés → c'est la piste suivante directe.
- n=10, micro-tâche proxy, régime hérité 129/130.

Outils : `tools/substrate_ab_compositional.py` (`run_curriculum_fade_gated(capture_probe=)`,
`probe_collapse_predictors`). Tests `tests/sandbox/test_substrate_ab_compositional.py`. Prolonge la
trilogie 128-129-130 (explique le plafond de reliabilité) et EDR 120 (mémoire présente, jusque chez les
collapsés). Piste suivante = intervention précoce (warm-start du gate) pour tester causalement la
path-dependence.
