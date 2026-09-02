---
id: EDR-RETAIN-COMPOSE
type: EDR
title: "OÙ est le mur retain+compose : diagnostic par oracle de rétention (RÉTENTION_APPRISE / LECTURE_D_ÉTAT)"
status: retracted
verdict: RETIRÉ (ex-RETENTION) — réfuté par EDR-RETAIN-COMPOSE-LR
retracted_by: [EDR-RETAIN-COMPOSE-LR]
gate: G2
tests: [SDR-G2]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## ⛔ RÉTRACTATION (2026-09-01) — le verdict est RETIRÉ, les CHIFFRES tiennent

Ce record livrait `RETENTION` sur la foi d'un `learned = 0.173`. Ce nul est un **artefact du pas
d'apprentissage**. En ne changeant QUE `lr`, à protocole identique (`run_retain_compose_diagnostic_probe`,
`episodes=600`, `n_agents=16`, `K=6`, 12 seeds, `bar=0.3167`) :

| lr | same_tick | oracle | learned | verdict rendu |
|---|---|---|---|---|
| **0.02** (ce record) | 0.969 | 0.971 | **0.173** | `RETENTION` |
| **0.002** | 0.937 | 0.945 | **0.923** | `INCONCLUSIVE` |

`learned` par seed — lr=0.02 : [0.145, 0.150, 0.166, 0.166, 0.169, 0.172, 0.173, 0.175, 0.181, 0.184,
0.188, 0.192] ; lr=0.002 : [0.897, 0.900, 0.905, 0.906, 0.914, 0.917, 0.928, 0.933, 0.939, 0.941, 0.953,
0.964]. **Séparation TOTALE** : min(lr=0.002)=0.897 > max(lr=0.02)=0.192, **0/144** chevauchement ; 12/12
au-dessus de la bar à lr=0.002 (test de signe p=2⁻¹²). L'écart `learned`↔`oracle` passe de **0.798 à 0.022**.

**Cause racine** : `n_agents=16` n'est PAS un minibatch — chaque agent porte ses PROPRES `W/U/V/W_bl`
(`src/agents/backend_torch.py:85-86`, `:113-115`), donc `F.cross_entropy` sur 16 lignes donne à chaque jeu
de paramètres **exactement 1 exemple par pas** (batch effectif = 1) sous Adam `lr=0.02`
(`tools/retain_compose_diagnostic_probe.py:80`, signature `:101`). `same_tick` et `oracle` sont des
problèmes à UN SEUL `_step` (bien conditionnés) et tolèrent ce pas ; `learned` enchaîne **DEUX `_step`**
avec BPTT et diverge. L'hyperparamètre avait été validé implicitement sur les conditions FACILES, puis
appliqué à la condition TESTÉE.

**Pourquoi la calibration ne pouvait pas l'attraper** : les deux contrôles calibrés de la sonde
(`test_retain_compose_same_tick_composes`, `test_retain_compose_decorrelated_oracle_is_floor`,
`tests/sandbox/test_instrument_calibration.py:1658` et `:1668`) sont TOUS DEUX des conditions à un seul
`_step`. Par construction, aucun ne POUVAIT détecter une pathologie propre au régime 2-pas.

* **Les CHIFFRES tiennent** : `same_tick 0.969 / oracle 0.971 / learned 0.173` sont reproduits au chiffre
  près à lr=0.02. Aucune expérience ultérieure n'efface une mesure. Tout le corps ci-dessous est CONSERVÉ
  intact.
* **Le VERDICT est RETIRÉ** : `RETENTION` n'est pas une propriété du substrat, c'est une propriété du
  réglage. H2 (« lecture d'état ») n'a jamais été réfutée ; H1 (« rétention apprise ») ne tient plus — à
  lr=0.002 le 2-tick atteint **0.923 avec une rétention APPRISE**, sans aucun oracle, sur 12/12 seeds.
  Corroborant **NON RÉPLIQUÉ** (une seule passe d'agent) : le key est linéairement décodable à **1.000**
  depuis l'état porté `H1[:, 59:]` **dès l'init** — il était TOUJOURS retenu.
* **Statut** : ce record est rétrogradé en **mesure à un seul point d'hyperparamètre**. Il ne porte plus de
  verdict, plus de prescription (« mécanisme de rétention apprise / porte d'oubli / registre » : SANS
  OBJET), et ne doit plus être cité comme tel. Le fil est repris par [[EDR-RETAIN-COMPOSE-LR]].

**Classe E19 du registre** (« réglage d'optimisation validé sur les conditions FACILES, appliqué à la
condition TESTÉE »), recoupe **E14** (le cliquet comptait cet instrument comme *calibré*).

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
