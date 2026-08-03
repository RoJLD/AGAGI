---
id: EDR-BILINEAR
type: EDR
title: "POSITIF (borné) : le terme bilinéaire lève le mur REPRÉSENTATIONNEL de (q+key)%K quand key et q sont co-présents (same-tick, crédit supervisé) — mais ne lève PAS, seul, le mur de RÉTENTION ; le nul REINFORCE de la Tâche 2 était confondu, dominé par la rétention plus que par le crédit"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

## Question

Le finding LANG-MEMORY (`docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md`) et la sonde
`tools/bilinear_composition_probe.py` (Tâche 2, commit `4bd8b8b`) ont établi que la composition
`(q+key)%K` N'ÉMERGE PAS sur le substrat affine `H_new=(1-δ)H+δtanh(H·W_off)`, ni sur ce même substrat
augmenté d'un terme bilinéaire low-rank `((H·U)⊙(H·V))·W_bl` entraîné par REINFORCE épisodique
(`agent.learn_episode`, encode(key) au pas 0 puis usage(query) au pas 1). Une revue adversariale de ce nul
a jugé la conclusion **PRÉMATURÉE** et identifié deux confonds non contrôlés :

1. **CRÉDIT** (smoking gun) : le contrôle no-op `recall` (pur-rappel, tâche FACILE) montre déjà le
   bilinéaire NETTEMENT sous le plain (0.61-0.71 vs 0.96-1.0) — la paramétrisation bilinéaire est dure à
   optimiser sous REINFORCE, indépendamment de la composition. Et `learn_episode` fait `H=H.detach()` À
   CHAQUE pas → le gradient est SÉVRÉ à la frontière encode→usage.
2. **RÉTENTION** : `key` (pas 0) et `q` (pas 1) sont à des ticks différents — la composition exige que
   `key` soit PORTÉ par l'état récurrent à travers un pas avant d'être combiné à `q`.

Le nul de la Tâche 2 pouvait donc être un artefact d'optimiseur/de protocole, pas une limite
représentationnelle du terme bilinéaire lui-même. Cette Tâche 3 teste les deux leviers correctifs
identifiés par la revue **avant** de trancher le verdict, conformément au pré-vol expérimental (ne pas
raisonner à la place de mesurer).

## Méthode

Deux leviers ajoutés à `tools/bilinear_composition_probe.py` (`run_bilinear_composition_probe` /
`_train_eval_one`), **désactivés par défaut** (le chemin de calibration Tâche 2 est bit-pour-bit
inchangé — `test_bilinear_noop_on_recall` et les tests de régression du substrat restent verts sans
modification) :

- **`same_tick=True`** : `key` ET `q` injectés dans LA MÊME observation (slots disjoints `[0:K]`/
  `[K:2K]`), un SEUL pas, cible `(q+key)%K`. Supprime la RÉTENTION — le bilinéaire multiplie deux entrées
  déjà présentes dans `H` au même tick (`hu=H·U`, `hv=H·V` voient key et q simultanément).
- **`credit_mode="supervised"`** : entraînement par `agent.imitate_episode_bptt` (cross-entropy sur la
  cible au pas réponse, `mask_seq` pour ne pas superviser le pas d'encodage en mode 2-pas) au lieu de
  `agent.learn_episode` (REINFORCE, H détaché à chaque pas). BPTT NON tronqué → le gradient circule sans
  coupure entre les pas retenus.

Le test DÉCISIF combine les deux (`same_tick=True, credit_mode="supervised"`) : il lève les DEUX confonds
à la fois et isole la question purement REPRÉSENTATIONNELLE (le bilinéaire low-rank peut-il représenter le
produit `(q+key)%K` quand les deux opérandes sont disponibles simultanément ?). Un test SECONDAIRE
(`same_tick=False, credit_mode="supervised"`) répare le crédit SEUL, en conservant la RÉTENTION exigée
(2 pas comme la Tâche 2) — il isole si le crédit à lui seul suffisait, sans avoir à lever la rétention.

Budget : n=12 seeds, `episodes=300`, `n_agents=16`, `K=6`, `rank=16`, `lr=0.02` pour les deux conditions
(fixé après un smoke à 3 seeds ayant montré une séparation déjà nette à ce budget — pas besoin d'un budget
plus grand). Run FOREGROUND, pur torch CPU, aucun bail `kuzu`, aucun monde.

## Résultat

**Condition DÉCISIVE (`same_tick=True, credit_mode="supervised"`) — UNLOCKED, séparation totale :**

| | médiane | plage 12 seeds |
|---|---|---|
| PLAIN | 0.271 | [0.233, 0.303] |
| BILINÉAIRE | **0.932** | [0.891, 0.969] |

Seuil d'émergence `1/K+0.15≈0.317` (K=6, cf. précédents LANG-MEMORY/LANG-PERCEPTION). Plain reste SOUS
le seuil sur les 12 seeds (reproduit le plancher connu) ; bilinéaire est AU-DESSUS sur les 12 seeds, avec
une **séparation totale** — aucun recouvrement entre les 12 valeurs plain et les 12 valeurs bilinéaire
(`min(bilinéaire)=0.891 > max(plain)=0.303`). Wall-clock mesuré : ≈235-292s (< 5 min, << 9 min).

**Condition SECONDAIRE (`same_tick=False, credit_mode="supervised"` — crédit réparé, rétention conservée)
— reste NUL :**

| | médiane | plage 12 seeds |
|---|---|---|
| PLAIN | 0.218 | — |
| BILINÉAIRE | 0.178 | — |

Bilinéaire reste AU PLANCHER, **même SOUS plain** — reproduisant le « smoking gun » de la revue
adversariale (le bilinéaire est plus dur à optimiser) **malgré le crédit réparé** (BPTT non tronqué, plus
de REINFORCE, plus de coupure de gradient à la frontière encode→usage). Wall-clock mesuré : ≈160-199s.
Un contrôle complémentaire (1 seed, bilinéaire seul, jusqu'à 1800 épisodes — 6× le budget du run n=12)
confirme un plateau au plancher (0.186 à 900 épisodes, 0.161 à 1800) : ce n'est pas un budget insuffisant,
c'est un plateau reproductible.

**Diagnostic du confond** : réparer le CRÉDIT seul (BPTT supervisé) sans lever la RÉTENTION **ne débloque
rien** — le nul survit à l'identique. Lever la RÉTENTION (co-présence same-tick) en même temps que le
crédit fait basculer le résultat de 0.18 à 0.93. **Le confond dominant du nul de la Tâche 2 était donc la
RÉTENTION, pas le crédit isolément** — même si le crédit REINFORCE tronqué reste probablement un frein
additionnel (non testé isolément — `same_tick=True, credit_mode="reinforce"` n'a pas été mesuré à n=12
dans cette tâche, cf. Portée).

## Interprétation

Le terme bilinéaire low-rank `((H·U)⊙(H·V))·W_bl` **possède la capacité représentationnelle** de calculer
le produit/la combinaison `(q+key)%K` quand les deux opérandes sont des entrées PRÉSENTES au même tick —
la classe de fonctions manquante au substrat affine (aucun produit d'unités possible dans
`H·W_off`) est bien celle que prédisait le précédent `planner-depth1-refuted` (PLAN-001/003). Mais cette
capacité représentationnelle ne se traduit **pas automatiquement** en capacité à composer une entrée
REÇUE-PUIS-RETENUE avec une entrée reçue plus tard : porter `key` à travers UN SEUL pas de récurrence
(via `H_new=(1-δ)H+δtanh(H·W_off+bilinéaire(H))`) semble suffire à rendre l'information inexploitable par
ce même terme bilinéaire de rang 16, MÊME sous crédit non tronqué. Le mur de composition/binding
(SOTA-gap) a donc (au moins) **deux étages séparables** : un étage REPRÉSENTATIONNEL (résolu ici par le
terme bilinéaire) et un étage RÉTENTION+composition (non résolu par ce même terme, à ce rang/budget).

## Portée (bornée)

- Montre la CAPACITÉ (entraînement direct par crédit épisodique/supervisé sur un proxy), **pas**
  l'émergence évolutive in-world (le NAS active-t-il le bilinéaire ? hors scope).
- Proxy `(q+key)%K`, `K=6`, `n_agents=16`, `rank=16`, `lr=0.02`, `episodes=300` (n=12) — budgets NON
  balayés exhaustivement pour la condition secondaire (2-tick supervisé) au-delà du contrôle 1-seed/1800
  épisodes ; un rang plus grand ou un budget bien plus long pourraient en principe débloquer la rétention
  — non exploré ici (limite de bornage du pré-vol, pas une affirmation qu'aucun budget n'y arriverait).
- `same_tick=True` avec `credit_mode="reinforce"` (lever la rétention SEULE, sans réparer le crédit)
  n'a pas été mesuré à n=12 dans cette tâche — seul un smoke à 1 seed l'a exercé fonctionnellement (aucune
  conclusion tirée sur cette combinaison précise).
- Le substrat bilinéaire reste flag-gated (`TorchPopulationModel.BILINEAR`, off partout ailleurs — chemin
  prod intact, prouvé bit-identique par `tests/test_bilinear_substrate.py`, Tâche 1).

## Ce que ça débloque

Le terme bilinéaire ATTAQUE avec succès l'étage REPRÉSENTATIONNEL du verrou de composition/binding — la
première preuve directe, sur ce substrat, qu'un produit d'unités low-rank suffit à apprendre `(q+key)%K`
quasi-parfaitement (médiane 0.932) là où le substrat affine plafonne au hasard. Cela ne rouvre PAS
directement `language→memory` (EDR-LANG-MEMORY) tel quel : cette arête exige la combinaison RÉTENTION+
composition, précisément la condition où ce même terme reste nul (condition secondaire ci-dessus). Le
sous-projet suivant naturel n'est donc pas de re-tenter `language→memory` directement, mais d'isoler
LEQUEL des deux ingrédients manque encore à la rétention (rang plus grand ? budget bien plus long ?
`credit_mode="reinforce"` en same-tick pour vérifier que le crédit n'était pas SEUL le facteur qui a
débloqué le cas décisif ? une forme de terme bilinéaire appliquée AUSSI dans le passage encode→usage,
pas seulement à l'usage ?).

Cf. `docs/superpowers/specs/2026-08-03-bilinear-substrate-composition-design.md`,
`docs/superpowers/plans/2026-08-03-bilinear-substrate-composition.md`,
`.superpowers/sdd/2026-08-03-bilinear-substrate-composition/task-3-report.md` (artefact SDD
session-local, non tracké — les chiffres qu'il contient sont préservés dans `results/bilinear_composition.json`,
source de vérité committée).
