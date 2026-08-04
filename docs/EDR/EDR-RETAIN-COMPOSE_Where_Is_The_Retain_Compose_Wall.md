---
id: EDR-RETAIN-COMPOSE
type: EDR
title: "OÙ est le mur retain+compose : diagnostic par oracle de rétention (RÉTENTION_APPRISE / LECTURE_D_ÉTAT)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## Question
BILINEAR a débloqué la composition à opérandes CO-PRÉSENTS mais le 2-tick (retenir key PUIS composer) reste
nul — même sous BPTT non-tronqué (pas le gradient). La rétention seule marche (MEM-PERCEPTION), la composition
seule marche (BILINEAR). OÙ est le gap de la COMBINAISON ?

## Méthode
3 conditions bilinéaire+supervisé (cross-entropy via `_step` direct, grad) sur (q+key)%K, n=12 : `same_tick`
(key+q co-présents en entrée, contrôle positif), `oracle` (key injecté PAR FIAT dans des nœuds d'état
`mem_slots`, rétention PARFAITE), `learned` (2-tick, rétention apprise). Calibré : same_tick compose (positif),
oracle décorrélé -> plancher (négatif).

Budget mesuré (FOREGROUND) : `episodes=600` (pas le défaut 1500), `n_agents=16`, `K=6`, `lr=0.02`, `eval_batches=40`,
12 seeds, `runtime_s=648.0`. Bornage — quelle direction ce budget protège : le smoke (3 seeds, mêmes
`episodes=600`/`n_agents=16`, dt=91.8s) montrait déjà `same_tick=0.966`/`oracle=0.972` — quasi au plafond.
Vérification explicite : `oracle` sur seed 0 à `episodes=1200` (2×) donne 0.959, contre 0.964 à `episodes=600`
— plateau confirmé, `oracle` ne grimpe pas depuis `episodes=600`. Ce contrôle écarte un sous-entraînement
d'ORACLE, qui ne menacerait qu'une lecture REPRESENTATION (oracle plafonnant bas par manque d'épisodes plutôt
que par incapacité) — **pas** le verdict RETENTION livré ici. La direction qui menacerait RETENTION est un
`learned` sous-évalué par artefact (le nul `learned` ≤ bar serait un plancher de plomberie, pas de rétention) :
ce risque n'est PAS couvert par ce contrôle de plateau — il repose sur le résultat BILINEAR antérieur (cf.
« Contrôle du nul » sous Portée). `episodes=600` retenu (pas 1500) pour tenir le run n=12 en foreground.

## Résultat
same_tick 0.969 (>bar 0.317, le bilinéaire compose) ; oracle 0.971 ; learned 0.173. **Verdict : RETENTION.**

oracle APPREND (0.971, quasi au niveau de same_tick 0.969, séparation par-seed nette : oracle∈[0.964,0.981]
sur les 12 seeds, aucun chevauchement avec learned∈[0.133,0.191]) alors que learned échoue (0.173 ≤ bar,
reproduit le ~0.18 qui motivait ce diagnostic) -> le gap n'est PAS la composition d'un état porté mais la
RÉTENTION APPRISE (holder le key en apprenant à composer). Le bilinéaire sait composer un état retenu PROPRE
(mem_slots) exactement comme il compose des opérandes co-présents ; ce qui manque au 2-tick est la capacité à
construire cet état retenu par apprentissage plutôt que de le recevoir par fiat.

## Portée (bornée)
Diagnostic sous ORACLE parfait (isole la variable), pas l'émergence. Un seul rang/budget. mem_slots = nœuds
d'état non-readout (le key porté y est lisible par le bilinéaire par construction).

**Contrôle du nul `learned`** : ce round n'inclut PAS de contrôle positif interne prouvant que le pipeline
2-tick POURRAIT réussir si la rétention était résolue — si `learned` plafonnait par un défaut de plomberie
plutôt que par une vraie difficulté de rétention, la sonde rapporterait le même ~0.17. Ce qui rend le nul
`learned` interprétable est HÉRITÉ, pas démontré ici : (a) le flux de gradient est câblé (pas de `.detach()`
entre pas 1 et pas 2, W reçoit le gradient à travers le carry) ; (b) `learned` montre un vrai étalement
par-seed [0.133, 0.191], pas une constante dégénérée ; (c) le nul du 2-tick sous BPTT non-tronqué est un
résultat ANTÉRIEUR déjà établi (sous-projet BILINEAR), que ce run reproduit. Un round futur devrait ajouter
un contrôle positif de rappel 2-tick interne.

## Ce que ça débloque
Nomme le prochain levier : un mécanisme de rétention apprise (porte d'oubli / registre) + le bilinéaire.
Lire un état porté PROPRE (canonique, one-hot dans un slot fixe) fonctionne déjà (oracle) — le bilinéaire
n'a pas besoin d'être refondu pour CE cas. Non séparé par ce diagnostic : H1a (la rétention apprise échoue
à retenir) vs H1b (elle retient, mais dans une forme non lisible par le bilinéaire — représentation
distribuée/non-canonique) ; une future rétention apprise pourrait donc encore exiger un ajustement côté
lecture. Cf. `docs/superpowers/specs/2026-08-04-retain-compose-diagnostic-design.md`.
