---
id: EDR-136
type: EDR
title: "PREMIÈRE recette de fiabilité 10/10 du binding compositionnel (gate + anti-saturation de la politique de base) — et c'est du binding RÉEL, pas un artefact du gap : à pénalité 6 les 3 irréductibles (0,3,4) bindent avec P(Y|X) qui RESTE haut (0.85–0.99) pendant que P(Y|¬X)→0.016 et hit_end PRÉSERVÉ (0.62≈baseline) ; dose-réponse à optimum (pen=12 RE-DÉGRADE hit_end 0.62→0.55 → bande, pas nombre magique) ; décomposition base/gate (revue) : base-seule préserve l'accomplissement (hit 0.75) et rescape 2/3 mais laisse seed 3 saturé, gate-seule atteint 10/10 gaps MAIS par suppression coûteuse (hit chute 0.62→0.48) → le 10/10 PROPRE exige BOTH ; contrôle none+pénalité = 0/10 (la pénalité seule ne conditionne pas)"
status: validated
gate: null
verdict: "Test côté POLITIQUE DE BASE du verrou résiduel d'EDR 133 (bassin d'optim : les résistants saturent P(Y)→1 tôt, annulant le gradient différentiel du gate, EDR 131). Levier `_apply_y_saturation_penalty` : pénalité HOMÉOSTATIQUE retirant coef·(y_rate_pop−cible) à la récompense des Y-pickers quand la marginale Y de population dépasse 0.5 (≠ EDR 128 Y-SANS-X conditionnel : ici marginale INCONDITIONNELLE). gate learned, régime fade0.0/pen2, 10 seeds. Sur revue, propagation des VRAIES métriques (P(Y|X), P(Y|¬X), hit_end) + décomposition base/gate (`y_saturation_scope`) + branche descendante. VERDICT ANTISAT_RESCUES (BOTH). (1) 10/10 à pen=6 (vs 7/10 base) — 1ère fois de la chaîne 128-133 — et RÉEL, pas artefact du gap : chez 0,3,4 P(Y|X) RESTE haut (0.85/0.99/0.86) pendant que P(Y|¬X)→~0.016, hit_end PRÉSERVÉ (0.67/0.74/0.62 vs 0.69/0.75/0.76 base) ; hit_end médian 0.618→0.623 (binders non dégradés). (2) NOMBRE MAGIQUE réfuté : pen=12 RE-DÉGRADE (gap_med 0.855→0.719, hit_med 0.623→0.551, P(Y|X) chute) → pen=6 = optimum, bande. (3) CHECK MANIP : y_rate_start résistants ~0.95→~0.75. (4) DÉCOMPOSITION base/gate (revue #4) : BASE-seule = 8/10, rescape 0,4 en PRÉSERVANT hit (0.749) mais seed 3 reste saturé (pynx 1.0) → ingrédient QUALITÉ/accomplissement, incomplet ; GATE-seule = 10/10 gaps MAIS hit CHUTE (0.477) = gaps gonflés par suppression coûteuse ; BOTH = 10/10 + hit préservé (0.623) → le vrai 10/10 exige les DEUX, la base porte l'accomplissement, le gate couvre seed 3. (5) ATTRIBUTION : none (sans gate) + pen6 = 0/10 (gap 0.072, hit 0.102) → la pénalité inconditionnelle ne conditionne pas seule. CONCLUSION : confirme causalement EDR 131/133 (désaturer débloque) ; recette migration = gate de conditionnement (129) + anti-saturation homéostatique atteignant la politique de base. « Locus base vs gate » NUANCÉ (revue) : base = conditionnement préservant l'accomplissement mais 2/3, couverture complète via BOTH ; PAS 'base pas gate'."
---

# EDR 136 : Anti-saturation de la politique de base — première recette 10/10 du binding, vérifiée réelle

## Question

EDR 133 a conclu que le verrou résiduel de fiabilité (seeds 3,4 jamais rescapés par les interventions
côté GATE : signal 128, crédit 130, init 132, capacité 133) est un BASSIN d'optimisation, dont EDR 131
donne le mécanisme : les collapsés saturent P(Y)→1 dès le 1er quart, annulant le gradient différentiel
P(Y|X)−P(Y|¬X) du gate. Test côté POLITIQUE DE BASE : empêcher la saturation-Y précoce rescape-t-il les
résistants, et est-ce du binding RÉEL ou un artefact du gap ?

## Méthode

Levier `_apply_y_saturation_penalty` (PUR, testé) : à chaque trial, si la marginale Y de POPULATION
dépasse `y_saturation_target=0.5`, on retire `coef·(y_rate_pop−cible)` à la récompense des seuls
Y-pickers → pression homéostatique gardant P(Y) loin de 1, préservant la variance sur ¬X. ≠ EDR 128
(Y-SANS-X conditionnel) : ici marginale INCONDITIONNELLE (ne reçoit jamais did_x).

`sweep_y_saturation` (gate learned, fade0.0/pen2, 10 seeds). **Sur revue sceptique**, ajouts décisifs :
- Propagation des VRAIES métriques par seed : `p_y_given_x_end`, `p_y_given_not_x_end`, `hit_end`
  (anti-artefact : le gap peut monter en baissant P(Y) ; on veut voir si P(Y|X) ET hit_end tiennent).
- `y_saturation_scope` ∈ {both, base, gate} : décompose QUEL apprenant reçoit la reward pénalisée
  (both=base+gate ; base=seul pop.learn, le gate lit la reward BRUTE ; gate=seule l'avantage du gate).
- Dose {0,6,12} (12 = branche descendante, réfute le nombre magique) ; contrôle none (sans gate).
Bind = binding_gap_end > 0.30. Outil `tools/substrate_ab_compositional.py`.

## Résultats

**Recette (BOTH) — 10/10, et c'est du binding RÉEL.**

| pénalité | n_bind | gap méd | **hit_end méd** | y_rate_start méd |
|----------|:------:|:-------:|:---------------:|:----------------:|
| 0 (base) | 7/10 | 0.370 | 0.618 | 0.827 |
| 6 | **10/10** | 0.855 | **0.623** | 0.702 |
| 12 | 10/10 | 0.719 | 0.551 | 0.567 |

Résistants à pen=6 (BOTH), le test anti-artefact :

| seed | pen0 : gap / P(Y\|X) / P(Y\|¬X) / hit | pen6 : gap / P(Y\|X) / P(Y\|¬X) / hit |
|------|--------------------------------------|--------------------------------------|
| 0 | −0.00 / 0.997 / 1.000 / 0.685 | +0.887 / **0.903** / 0.016 / **0.673** |
| 3 | 0.00 / 1.000 / 1.000 / 0.754 | +0.970 / **0.987** / 0.016 / **0.742** |
| 4 | −0.00 / 0.997 / 1.000 / 0.764 | +0.841 / **0.856** / 0.015 / 0.621 |

À pen=6, **P(Y|X) RESTE haut (0.85–0.99)** pendant que P(Y|¬X) s'effondre (→0.016) et **hit_end est
PRÉSERVÉ** (0.62–0.74). Ce n'est PAS un gap gonflé par suppression globale : c'est du conditionnement
(Y sur X, pas sur ¬X). **hit_end médian 0.618→0.623** : les binders natifs ne sont pas dégradés.

**Nombre magique réfuté.** À pen=12, gap_med et hit_end RE-BAISSENT (0.855→0.719 ; 0.623→0.551 ;
P(Y|X) résistants chute, ex. seed 0 0.903→0.773) → pen=6 est un OPTIMUM, une bande, pas un point ajusté.

**Décomposition base/gate (revue #4).**

| scope (pen=6) | n_bind | gap méd | hit_end méd | résistants |
|---------------|:------:|:-------:|:-----------:|------------|
| BASE seule | 8/10 | 0.895 | **0.749** | rescape 0,4 ; seed 3 reste saturé (P(Y\|¬X)=1.0) |
| GATE seule | 10/10 | 0.540 | **0.477** | 10/10 gaps mais hit CHUTE |
| BOTH | 10/10 | 0.855 | 0.623 | 10/10 + hit préservé |

**Attribution.** none (aucun gate) + pen=6 = **0/10** (gap 0.072, hit 0.102) : la pénalité inconditionnelle
ne conditionne pas seule.

## Interprétation

**Première recette 10/10 de la chaîne 128-133, et vérifiée RÉELLE.** Le contrôle anti-artefact demandé
par la revue la renforce au lieu de l'affaiblir : les résistants bindent parce que P(Y|X) reste haut et
P(Y|¬X) s'effondre, avec hit_end (accomplissement X-puis-Y) préservé. Ce n'est pas de la suppression
globale (qui aurait fait chuter P(Y|X) et hit_end — c'est justement ce qu'on voit sous none+pen : hit
0.102).

**Le rescue = gate × désaturation, confirmant causalement EDR 131/133.** Sans gate, la désaturation ne
conditionne rien (none 0/10) ; sans désaturation, le gate reste à 7/10 (les résistants saturent avant
qu'il apprenne). Ensemble : 10/10. Abaisser la saturation précoce (y_rate_start résistants ~0.95→~0.75)
débloque précisément leur binding → la saturation-Y précoce ÉTAIT le verrou résiduel d'EDR 133.

**« Locus base vs gate » — NUANCÉ (correction de revue).** La décomposition interdit le raccourci « côté
base pas gate » : (a) la pénalité sur la BASE seule est l'ingrédient de QUALITÉ — elle préserve/augmente
l'accomplissement (hit 0.749) et rescape 0,4 par vrai conditionnement (P(Y|X)=1.0) — mais est INCOMPLÈTE
(seed 3, le plus dur d'EDR 133, reste saturé) ; (b) la pénalité sur le GATE seul atteint 10/10 gaps mais
au prix de l'accomplissement (hit 0.477) — c'est le mécanisme « gap gonflé par suppression » redouté par
la revue, rendu VISIBLE ; (c) le 10/10 PROPRE (gaps hauts ET hit préservé) exige les DEUX : la base porte
l'accomplissement, une pression côté gate couvre seed 3. **La migration doit atteindre la politique de
base** (sinon on gonfle les gaps sans accomplir), mais la couverture complète est une CONJONCTION.

**Migration.** Recette concrète : (1) gate de conditionnement lisant la mémoire récurrente (EDR 129) +
(2) pression homéostatique / floor d'entropie sur la marginale d'action de la politique de base,
empêchant l'effondrement prématuré vers une action dominante. (2) est un mécanisme standard et plausible
(régularisation d'entropie, plasticité homéostatique), pas un hack de banc.

## Bornage / honnêteté

- **Recette de CONJONCTION** : la pénalité N'EST utile qu'AVEC le gate (none 0/10) ; à présenter comme
  « désaturer laisse le gate finir », pas « l'anti-saturation résout le binding ».
- **base-seule ≠ 10/10** : elle rescape 2/3 et préserve l'accomplissement, mais seed 3 exige aussi la
  pression côté gate. Le « locus » n'est donc pas purement la base ; c'est une combinaison où la base est
  l'ingrédient qui garde l'accomplissement.
- **gate-seule = piège** : 10/10 gaps mais hit 0.477 → un gap élevé N'EST PAS suffisant comme critère ;
  hit_end est le garde-fou. Le seuil bind (gap>0.30) surestime la réussite sans hit_end.
- **pen=6/cible=0.5 = knobs** : dose-réponse continue avec optimum (pen=12 dégrade), non ajusté a
  posteriori ; mais l'optimum dépend du régime (n_agents=8 → granularité marginale 1/8 grossière).
- **Homéostasie de population** (marginale collective par trial, n=8 petit) : statistique grossière ; la
  marginale par trial peut corréler faiblement avec la composition did_x du trial (indépendance garantie
  par CONSTRUCTION du câblage — la pénalité ne reçoit pas did_x — pas par la distribution). Fuite directe
  exclue, corrélation populationnelle résiduelle non exclue mais ténue.
- **Régime hérité 129-133** (fade0.0/pen2, gate linéaire) ; généralité hors proxy à établir. Preuve de
  MÉCANISME, pas de déploiement.
- n=10, micro-tâche X-gate-Y, déterminisme par graine.

Outils : `tools/substrate_ab_compositional.py` (`_apply_y_saturation_penalty`,
`run_curriculum_fade_gated(y_saturation_penalty=, y_saturation_target=, y_saturation_scope=)`,
`sweep_y_saturation`). Tests `tests/sandbox/test_substrate_ab_compositional.py`. **CLÔT positivement la
quête de fiabilité** ouverte en EDR 129 : recette = gate de conditionnement (129) + anti-saturation
atteignant la politique de base (136). Confirme causalement EDR 131 et résout le bassin d'EDR 133.
Numéro 136 (134/135 réservés par le fil in-world parallèle, cf. [[parallel-sessions-shared-tree]]).
