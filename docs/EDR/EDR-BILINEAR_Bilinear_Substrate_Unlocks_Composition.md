---
id: EDR-BILINEAR
type: EDR
title: "POSITIF (borné) : le terme bilinéaire lève le mur REPRÉSENTATIONNEL de (q+key)%K quand key et q sont co-présents (same-tick, crédit supervisé) — mais ne lève PAS, seul, le mur de RÉTENTION ; le nul REINFORCE de la Tâche 2 était confondu, dominé par la rétention plus que par le crédit"
status: active
gate: G2
tests: [SDR-G2]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

> ⚠️ **CLAUSE SUSPECTE (2026-09-01)** — ce record reste `active` et son résultat PRINCIPAL est intact ;
> c'est sa clause SECONDAIRE (le nul 2-pas) qui est bornée ci-dessous. Cf. [[EDR-RETAIN-COMPOSE-LR]].
>
> **Ce qui est SUSPECT — tout ce qui repose sur la condition `same_tick=False` (2 pas) mesurée à
> `lr=0.02`** : la clause du titre (`:4`) « **ne lève PAS, seul, le mur de RÉTENTION ; le nul REINFORCE de
> la Tâche 2 était [...] dominé par la rétention** », le § « Diagnostic du confond » (`:86-89`), le
> « second étage RÉTENTION+composition non résolu » (`:104`), la puce de portée `:111-114` et la
> prescription `:125-128` (« ne rouvre PAS `language→memory` » — numéros de ligne de la version d'AVANT
> cet encart ; les sections sont nommées ci-dessus, elles font foi). Ces passages viennent tous du bras
> secondaire mesuré à `lr=0.02`, `n_agents=16`, Adam (`tools/bilinear_composition_probe.py:163`, `:115`).
> [[EDR-RETAIN-COMPOSE-LR]] a mesuré (n=12, séparation totale 0/144) que dans ce régime EXACT — 2 pas,
> `n_agents=16` qui n'est PAS un minibatch (batch effectif **1**, `src/agents/backend_torch.py:85-86`) — le
> nul 2-pas est un **artefact du pas d'apprentissage** : `learned` 0.173 à `lr=0.02` contre **0.923** à
> `lr=0.002`.
>
> **RE-MESURÉ SUR CETTE SONDE-CI (n=12, 2026-09-01)** — pas seulement inféré par analogie. Contre-exemple
> gelé `test_bilinear_composition_null_under_retention_is_lr_dependent`
> (`tests/sandbox/test_instrument_calibration.py`), condition INCHANGÉE (`same_tick=False`,
> `credit_mode="supervised"`, `episodes=300`, `n_agents=16`, `K=6`, `rank=16`), seule variable ajoutée `lr` :
> · `lr=0.02` → plain 0.2180, bilinéaire **0.1789** (sous plain), `unlocked=False` — **reproduit au chiffre
> près** le nul publié le 2026-08-03 (0.218 / 0.178) ; · `lr=0.002` → plain 0.1812, bilinéaire **0.3797**
> (> bar 0.3167), `unlocked=True`. Séparation par-seed **TOTALE** sur le bras bilinéaire :
> max(lr=0.02)=0.2016 < min(lr=0.002)=0.3500, **0/144**, 12/12 seeds au-dessus de la barre (signe p=2⁻¹²).
> Donc le nul 2-pas ET le verdict `unlocked` sont des propriétés du **RÉGLAGE**, pas du substrat, et la
> clause « réparer le crédit SEUL ne débloque rien, le confond dominant était la RÉTENTION » **n'est PAS
> établie**. Elle est marquée SUSPECTE et **non établie**, mais **pas retirée** : ⚠️ 0.3797 reste très loin
> du 0.932 du régime 1-pas, et à peine au-dessus d'une barre elle-même douteuse (voir la dette ci-dessous)
> — cette mesure **ne dit pas** que le 2-pas soit RÉSOLU à `lr=0.002`, seulement que le nul qui fondait la
> clause ne survit pas au balayage du pas. Les chiffres du 2026-08-03 ne sont pas effacés : ils sont
> reproduits ci-dessus et restent vrais **à ce pas**.
>
> **Ce qui est INTACT — et même RENFORCÉ.** Le résultat phare (condition DÉCISIVE `same_tick=True`, UN
> SEUL pas, plain 0.271 vs bilinéaire 0.932, 0/144 chevauchement) est hors du régime suspect. Mieux :
> l'argument de séparabilité est désormais confirmé **QUANTITATIVEMENT** (mesures de sonde sœur,
> **NON RÉPLIQUÉES**, 3-4 seeds, une passe) : à `H_in=0` la forme close du plain est
> `logit_j = σ(W_jj)·tanh(W[key,j] + W[K+q,j])`, transformée monotone d'un score **SÉPARABLE** ; son
> **plafond structurel exact**, obtenu par optimisation directe plein-batch des 36 paires (8 restarts), est
> **0.3889** — contrôle positif du même optimiseur sur une table libre non séparable : **1.000**. Le
> plafond est donc une propriété du SUBSTRAT, pas de l'optimiseur. Et la séparation plain/bilinéaire est
> **totale à TOUT pas testé** (`lr ∈ {0.0005, 0.002, 0.02, 0.05, 0.1, 0.2, 0.5}`) :
> **max plain 0.3984 < min bilinéaire 0.9594**, écart jamais refermé (0.577 au meilleur pas du plain). La
> valeur 0.271 du record est simplement le point sous-entraîné d'une courbe qui SATURE à 0.389.
>
> **Dette ouverte — MARGE DE DÉCISION, pas réfutation.** La barre `1/K + 0.15 = 0.3167`
> (`tools/bilinear_composition_probe.py:174`) est **0.072 SOUS** ce plafond structurel 0.3889 : un substrat
> *prouvablement incapable* de composer PEUT la franchir. Le critère `unlocked = (plain ≤ bar) and
> (bilinéaire > bar)` (`:174-176`) bascule donc par simple allongement du budget — mesuré (NON RÉPLIQUÉ,
> 3 seeds) : plain à `lr=0.02`, `episodes=2400` (8× les 300 de ce record) → médiane **0.3703**, **3/3
> au-dessus de la barre**. C'est une dette de SEUIL à corriger dans la sonde (juger la **séparation entre
> bras**, ou embarquer le plafond constructif, jamais un seuil absolu), pas une remise en cause de la
> conclusion.

> ### ⚠️ CORRECTIF 2026-09-07 — le plafond du plain valait **0.8333**, pas 0.3889 ; la marge de capacité de ce record passe de 0.543 à 0.099
>
> **Ce qui est mesuré.** Même forme close, même tâche, même K : `argmax_j σ(W[j,j])·tanh(W[key,j] +
> W[K+q,j])` atteint **30/36 = 0.8333** sur les 36 paires — optimisation plein-batch, 24 restarts ×
> 20 000 pas, **re-vérifiée cellule par cellule sans autograd**. Le `0.3889` publié ci-dessus est
> SUPERSÉDÉ. Deux faits exacts l'encadrent, prouvés et non plus cherchés :
> * la sous-forme **purement additive** `argmax_j a[k,j]+b[q,j]` plafonne à **27/36 = 0.75**
>   EXACTEMENT (MILP, gap 0) — c'est une borne SUPÉRIEURE, pas un minorant ;
> * la perfection y est **infaisable pour tout K de 3 à 8** (LP). Pour K pair, l'argument est direct :
>   avec k'=k+K/2 et q'=q+K/2 on a k+q ≡ k'+q' et k+q' ≡ k'+q, et les quatre cellules exigent à la fois
>   `b_q[j1]+b_q'[j2] > b_q[j2]+b_q'[j1]` et son inverse strict. Une additivité ne porte pas la
>   structure de groupe. L'écart 30/36 vs 27/36 chiffre donc ce que `σ·tanh` achète : **3 cellules**.
>
> **La cause de l'erreur, et elle vaut plus que le chiffre.** La mesure d'origine portait deux contrôles
> appariés qui PASSAIENT tous les deux (table libre → 1.000 ; forme close sur cible séparable → 1.000).
> Ils innocentent la FORME et l'OPTIMISEUR ; **ni l'un ni l'autre ne peut dire si la RECHERCHE a
> convergé** — la seule question qui fixe la valeur d'un plafond. Reproduit à dessein : à 2 restarts ×
> 60 pas les deux contrôles valent 1.000 pendant que le plafond lit 0.278. Un contrôle de CAPACITÉ ne
> calibre pas un contrôle de BUDGET (E19, déplacé du pas d'apprentissage vers l'effort de recherche).
> Preuve directe de la faiblesse de la recherche : sur la forme additive, dont le MILP donne 0.75, la
> descente de gradient ne trouve que **0.3611** — un facteur 2 SUR UNE FORME DONT ON CONNAÎT LA RÉPONSE.
>
> **L'ARGUMENT lui-même était invalide, et c'est plus grave que le chiffre.** Ce record écrit que la
> forme close est une « transformée MONOTONE d'un score SÉPARABLE », d'où l'incapacité. **L'inférence ne
> tient pas** : la transformée est **PAR NŒUD** — `c_j = σ(W[j,j])` diffère d'un j à l'autre — et
> `argmax_j c_j·tanh(x_j)` n'égale `argmax_j x_j` QUE si tous les `c_j` sont égaux. Dès que deux
> diffèrent, la courbe d'iso-score entre deux colonnes est croissante NON LINÉAIRE ; deux de ses
> translatées se coupent DEUX fois, donc la même paire de points peut être séparée dans les deux sens —
> un **XOR 2×2**, impossible à tout score séparable. C'est précisément l'ingrédient qui fait franchir la
> borne séparable de 27/36 (solution mesurée : `c` de rapport max/min ≈ 1.9, donc NON uniformes).
> Détail qui explique pourquoi c'est passé inaperçu : `W_off = W*(1-eye)` EXCLUT la diagonale de
> l'excitation, donc `W[j,j]` n'agit QUE comme ce gain — on l'attend comme une auto-connexion, il est en
> fait le terme qui casse l'argument.
>
> **Où le 0.3889 vient exactement.** Une ascension de coordonnées exacte depuis des départs aléatoires
> donne une distribution d'optima locaux `{14:1, 15:1, 16:1, 17:3, 18:2, 19:3, 20:2, 21:4, 24:1, 25:4,
> 26:2, 27:6}` : **14/36 = 0.3889 est un optimum local BANAL** de cette surface, et avec 8 restarts on y
> tombe typiquement. Le chiffre publié n'était pas faux par accident de calcul — il était le résultat
> normal d'une recherche trop courte, présenté comme un plafond exact.
>
> ### ⛔ RECTIFICATION LE JOUR MÊME — la SÉPARATION DE CAPACITÉ de ce record N'EST PAS ÉTABLIE
>
> Le paragraphe ci-dessus a d'abord été écrit « la conclusion tient, marge 0.099 ». **C'était faux, et
> l'erreur est la mienne : j'ai adossé une conclusion à un MINORANT en le traitant comme un plafond.**
>
> Trois recherches INDÉPENDANTES sur la MÊME forme close, le même jour, par ordre d'effort croissant :
> **29/36 (0.806) → 34/36 (0.944) → 36/36 (1.000)**. Une quatrième, la mienne, atteint 33/36. Un
> « plafond » qui monte à chaque fois qu'on cherche plus fort **n'est pas un plafond** — c'est le
> plancher de l'optimiseur. La troisième mesure a d'ailleurs été obtenue par un chercheur qui a REFUSÉ
> son propre 35/36 après avoir calibré son pipeline sur une réponse exacte connue (le sous-cas additif,
> 27/36 par MILP, où son gradient ne trouvait que 13-14/36 — 13 cellules d'écart).
>
> **PREUVE MÉCANIQUE de l'origine du 0.3889, mesurée le 2026-09-07, et elle disqualifie un contrôle.**
> Sur la sous-forme purement ADDITIVE — celle dont le MILP PROUVE l'optimum à 27/36 = 0.75 — une
> descente de gradient à marge rend, par budget croissant : 13/36 · **14/36 = 0.3889** · **14/36 =
> 0.3889** · 15/36. Le nombre publié se reproduit comme un **PLATEAU STABLE, qui TIENT SUR UN
> DOUBLEMENT DU BUDGET** (15 000 puis 30 000 pas). Conséquence directe et contre-intuitive : **un
> contrôle de SATURATION l'aurait BÉNI**, puisque demi-budget et budget plein rendent le même chiffre.
> Le seul contrôle qui le refuse est celui qui ancre sur la borne PROUVÉE (0.3889 < 0.75). **Un plateau
> de recherche est indiscernable d'un plafond par tout contrôle qui ne dispose pas d'une VÉRITÉ EXACTE
> de référence.**
>
> **Conséquence, sans adoucissement.** Le bilinéaire mesure 0.932. Le plain atteint **0.9444 —
> mesuré ICI, re-vérifié en Python pur (victoire STRICTE) ET injecté dans le `W` d'un vrai
> `TorchPopulationModel` où le VRAI `forward` rend le même 34/36** ; témoin gelé dans
> `results/plain_ceiling_witness.json`. Deux chercheurs indépendants trouvent 0.944 et 1.000. **La capacité représentationnelle du plain n'est donc PAS inférieure à ce que le
> bilinéaire atteint** : la thèse « le bilinéaire peut représenter ce que le plain ne peut pas » n'est
> plus soutenue par ce dispositif. Ce qui SUBSISTE, et qui reste un résultat réel :
> **une séparation d'APPRENABILITÉ à budget fixe** — plain 0.271 vs bilinéaire 0.932 à `episodes=300`,
> séparation par-seed totale. Ce n'est pas ce que le record affirme.
>
> * **La phrase « une courbe qui SATURE à 0.389 » est FAUSSE.** La forme du plain ne sature pas là ; le
>   0.271 du record reste vrai comme MESURE, mais il dit le BUDGET, pas la capacité.
> * **La sonde ne certifie plus.** `run_bilinear_composition_probe` rend désormais `unlocked=None` et
>   `bar_status="CEILING_IS_MINORANT"` tant qu'aucune borne SUPÉRIEURE PROUVÉE n'est fournie. Une
>   condition nécessaire n'est pas une preuve, et laisser la sonde conclure sur un minorant était
>   exactement le défaut P2.15 déplacé d'un cran.
> * **Ce qui reste à faire, et c'est faisable** : une borne supérieure PROUVÉE pour la forme complète.
>   Le MILP en a produit une pour la sous-forme additive (27/36, gap 0) ; la relaxation « monotone
>   quelconque par colonne » est réfutée (elle atteint la perfection, elle ne borne rien) ; ce qui reste
>   à contraindre est la FORME de `tanh` elle-même.
>
> **Le 30/36 est AUDITABLE, et il tient dans le VRAI substrat.** Les 78 coefficients qui l'atteignent
> sont gelés dans `results/plain_ceiling_witness.json` — il avait fallu 19 restarts sur 24 pour
> tomber dessus, donc sans témoin chaque re-vérification serait un coup de dés. Recomptés en Python
> pur sans autograd : **30/36**. Puis injectés dans le `W` d'un vrai `TorchPopulationModel`
> (`BILINEAR=False`) et lus par le VRAI `forward` sur le chemin d'évaluation exact de la sonde :
> **30/36** aussi. La forme close EST le substrat — si les deux avaient divergé, ce plafond aurait
> été un aliasing au sens d'EDR-WARM-007, une grandeur mesurée qui n'est pas celle qui agit.
>
> Instrument : `tools/plain_substrate_ceiling.py` (trois contrôles appariés, dont la SATURATION du
> budget) · garde : `assert_bar_separates_the_incapable`, désormais APPELÉE · cliquet :
> `tools/check_bar_separation.py` (porte 9 du hook).

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
