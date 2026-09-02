---
id: EDR-DELAYED-COORD
type: EDR
title: "NÉGATIF — la coordination référentielle DIFFÉRÉE n'est pas mesurable sur ce substrat : le report PASSIF marche, l'ÉCRITURE APPRISE dans le report ne marche pas"
status: active
verdict: DELAYED_COORDINATION_EDGE_NOT_MEASURABLE_LEARNED_CARRY_FAILS
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
---

> ⚠️ **RÉGIME D'OPTIMISATION NON BALAYÉ (rétro-audit 2026-09-02) — le verdict NÉGATIF « non mesurable telle que spécifiée » est INCHANGÉ ; seule la clause mécanique du §2 est bornée.** Tous les chiffres du crible et des trois chemins de crédit sont mesurés à `lr=0.05` UNIQUEMENT — du côté divergent de la bascule E19 : [[EDR-RETAIN-COMPOSE-LR]] a mesuré qu'à batch effectif 1 un nul 2-pas à `lr ≥ 0.02` peut être un artefact du pas d'apprentissage (learned 0.173 → 0.923 en passant de 0.02 à 0.002, 0/144, n=12). Le balayage `lr` ≥ 3 points prescrit par la spec (T2, seeds disjoints, critère scellé sur RETAIN intact seul) n'a jamais été atteint : le crible T1 a échoué avant. La phrase « l'ÉCRITURE APPRISE dans le report ne marche pas » doit donc se lire « ...ne marche pas à `lr=0.05` » : les trois chemins de crédit varient le MÉCANISME de crédit, pas le PAS. Avant toute citation de ce mur comme propriété du SUBSTRAT (« c'est là qu'est le mur »), re-mesurer RETAIN (leurre retiré) à `lr=0.002` — coût ~13.2 min par point de `lr` selon la spec. Le pilote `lr=0.02` (RETAIN 0.873-0.946) ne vaut PAS contre-preuve : suspect canal oracle-équivalent (cf. Portée).

> ## Mesure prescrite par le rétro-audit — EXÉCUTÉE (2026-09-02) : la clause §2 reste BORNÉE
>
> Le balayage demandé ci-dessus a été fait (leurre RETIRÉ, D=2, 800 ép., `n_agents=16`, 3 seeds, `flip_p=0`,
> chemin `bptt`), et **il ne tranche pas** — pour une raison qui est elle-même le sujet de ce record.
>
> | bras | `lr` | par seed | médiane | > barre 0.317 |
> |---|---|---|---|---|
> | RETAIN | 0.05 | 0.2266 / 0.2406 / 0.2094 | **0.2266** | 0/3 |
> | RETAIN | 0.002 | 0.1891 / 0.1984 / 0.1734 | **0.1891** | 0/3 |
> | PRESENT | 0.05 | 0.3375 / 0.3313 / 0.3562 | **0.3375** | **3/3** |
> | PRESENT | 0.002 | 0.1906 / 0.1297 / 0.2000 | **0.1906** | 0/3 |
>
> **Ni confirmation, ni réfutation — la troisième branche.** RETAIN ne franchit la barre à aucun des deux
> pas : la bascule d'[[EDR-RETAIN-COMPOSE-LR]] **ne se reproduit pas** ici. Mais le nul à `lr=0.002` est
> **ININTERPRÉTABLE** : le contrôle PRESENT, qui ne demande AUCUNE rétention, s'effondre lui aussi au
> plancher — à 800 épisodes, ce pas n'apprend rien du tout. C'est exactement le motif E3 que la garde
> `assert_verdict_invariant_to_optimizer` refuse depuis sa correction du même jour : **quand la RÉFÉRENCE
> s'effondre, la comparaison est vide**. La clause du §2 ne peut donc PAS être débornée — et elle n'est pas
> réfutée non plus. Sous-produit solide : le **0.223** du §1 est répliqué (**0.2266**).
>
> **Deux défauts d'instrument découverts par cette mesure, et ils débordent ce record :**
> 1. ⚠️ **Les chiffres du §1 se lisent à `flip_p = 0`, pas au défaut du module (0.3).** Le contrôle de
>    sanité ne reproduit le 0.338 qu'à bruit nul (0.3375, écart 0.0005) ; à `flip_p=0.3` il rend 0.239.
>    Cause vérifiée : la sonde de référence montre au sender un one-hot **propre**, alors que `_noisy_onehot`
>    bruite le **canal**. C'est une RECONSTRUCTION (le seul réglage qui reproduit 0.338 et 0.170), pas une
>    lecture d'un paramètre déclaré.
> 2. ⚠️ **À `flip_p=0.3`, la barre `1/K+0.15 = 0.317` est INATTEIGNABLE EN PRINCIPE** — le bras le plus
>    facile (PRESENT sans leurre) plafonne à 0.239. Toute cellule mesurée au défaut du module et comparée à
>    cette barre est un **instrument à ISSUE UNIQUE** (classes E1/E2 : un bras qui ne peut pas réussir).
>
> **Confond non levé, à inscrire dans tout balayage futur** : `episodes` est **confondu avec `lr`** — « pas
> bas » et « sous-entraîné » ne sont pas séparés. Un balayage honnête doit AUGMENTER le budget aux pas bas.
> Portée de cette mesure : n=3, un seul chemin de crédit, 2 points de `lr` au lieu des ≥3 prescrits,
> `lr=0.02` non mesuré.

> ## Balayage DÉCONFONDU (2026-09-02) — la clause OPÉRATIONNELLE est RÉFUTÉE, la clause SCIENTIFIQUE en sort RENFORCÉE, et le verdict NÉGATIF tient pour une bien meilleure raison
>
> Le balayage a enfin été fait proprement, après avoir levé **deux** confonds — celui que ce record
> nomme, et un qu'il ne nommait pas.
>
> **Le confond non nommé, et il était fatal : `lr` pilotait LES DEUX optimiseurs.** Le baisser ne
> ralentissait pas seulement l'apprentissage du receiver (l'axe E19 qu'on interroge) : il dégradait
> l'émergence du code de Lewis chez le **sender**, donc l'INFORMATION DU CANAL. Tout balayage en `lr`
> changeait la **tâche** en même temps que la vitesse d'apprentissage, et ses points étaient
> incomparables entre eux. Levier `sender_lr` livré ; **sender fixé à 0.05** dans tout ce qui suit.
> Le confond nommé (`episodes` × `lr`) est levé par `eval_every` : chaque cellule rend une COURBE, donc
> « au plancher » et « sous-entraîné » deviennent DISCERNABLES (un bras sous-entraîné MONTE).
>
> **1. RETAIN monte quand le pas baisse ; PRESENT descend.** D=2, `flip_p=0`, sans leurre, `bptt`,
> 1600 ép., 3 seeds, sender fixe :
>
> | `lr` receiver | 0.05 | 0.02 | 0.005 | 0.002 |
> |---|---|---|---|---|
> | RETAIN (médiane) | 0.2109 | 0.2313 | 0.2453 | **0.2969** |
> | PRESENT (médiane) | **0.3891** | 0.3562 | 0.3047 | 0.2594 |
>
> Monotone dans les deux sens, 3/3 seeds chacun, séparation COMPLÈTE de RETAIN entre les extrêmes
> (pire seed à 0.002 = 0.2844 > meilleur seed à 0.05 = 0.2406). Test des signes apparié, n=3 : **p=0.125**.
> ⚠️ **Le confond résiduel a un SIGNE CONNU, et c'est ce qui rend la lecture possible** : à 1600 ép.
> aucun bras n'est convergé (toutes les pentes > 0, PRESENT fait +0.19 à `lr=0.05`). Or le
> sous-entraînement pousse une cellule VERS LE BAS quand `lr` baisse — c'est exactement ce que fait
> PRESENT, dont la chute n'est donc PAS interprétable. RETAIN va à l'INVERSE du confond : celui-ci ne
> peut pas avoir fabriqué sa montée, seulement l'avoir masquée. **L'effet mesuré est un minorant.**
>
> **2. Budget ×3 à `lr=0.002` (4800 ép., mêmes seeds — le budget est la seule variable) : le bras
> « qui n'a jamais décollé » décolle.** RETAIN `[0.3063, 0.3219, 0.3375]`, ablaté 0.1484, **ratio 2.17**
> (retirer l'état porté le ramène SOUS le hasard). Et l'axe dominant est identifié : le **pas** a rendu
> +0.086, le budget ×3 seulement +0.025 — le pas commande d'un facteur **3.4**.
> ⇒ **La clause opérationnelle du §"Verdict" — « RETAIN au plancher, le bras principal n'a jamais
> décollé » — est RÉFUTÉE.** Elle était mesurée au point le PLUS DÉFAVORABLE de l'axe `lr`. C'est une
> récidive de la classe **E19** dans le record écrit pour en borner une.
>
> **3. Mais c'est du report PASSIF, et cette fois la comparaison a du CONTENU.** Au régime vivant
> (`lr=0.002`, 4800 ép., mêmes seeds, le chemin de crédit est la SEULE variable) :
>
> | chemin de crédit | RETAIN par seed | médiane | écart intra-seed vs `bptt` |
> |---|---|---|---|
> | `reinforce` — `H.detach()` à CHAQUE pas (`backend_torch.py:357`) : apprendre à ÉCRIRE est IMPOSSIBLE | 0.3063 / 0.3125 / 0.3484 | 0.3125 | +0.006 / +0.027 / −0.031 |
> | `bptt` — le gradient TRAVERSE le report | 0.3063 / 0.3219 / 0.3375 | 0.3219 | — |
> | `imitate` — BPTT supervisé masqué au dernier pas | 0.2953 / 0.3297 / 0.3453 | 0.3297 | −0.011 / +0.023 / −0.008 |
>
> Étendue des médianes **0.017**, soit UNE erreur-type ; signes mêlés sur les deux contrastes.
> Supprimer la capacité d'apprendre à écrire dans le report **ne coûte rien**.
> ⇒ **La clause scientifique du §2 est CORROBORÉE, et pour la première fois de façon informative.**
> Le §2 la fondait sur trois chemins tous AU PLANCHER — or un bras au plancher est insensible à tout,
> donc cette comparaison ne pouvait rien montrer : c'est le motif **E3**, celui-là même que ce record
> applique à ses deux critères « non adjudicables ». Refaite sur un bras **VIVANT**, elle donne une
> réponse qui a du contenu, et c'est la même.
>
> **4. Le verdict NÉGATIF tient — mais sa raison change, et la nouvelle est plus forte.** Ce n'était pas
> « le bras n'a pas décollé » (c'est faux). C'est que **le design ne peut produire AUCUN contrôle de
> spécificité valide, dans AUCUN de ses deux réglages** : avec leurre tout plancherise (§1) ; sans
> leurre, l'ablation de PRESENT est un no-op EXACT — mesuré ici, `ablated == intact` au chiffre près
> (0.3219 = 0.3219) — donc son inertie est **vacuité**. Et l'effondrement de RETAIN sous ablation est
> arithmétiquement forcé, comme le module le dit lui-même. Un bras vivant NE SUFFIT PAS : la 3ᵉ arête
> est bloquée par la **CONCEPTION**, pas par la mesure.
>
> **Portée — ce qui n'est PAS établi.** n=3 partout : rien de gravable (garde d'évaporation de
> puissance). ⚠️ **Et la « vitalité » ne doit pas être sur-lue** : RETAIN médian 0.3219 contre barre
> 0.31667 fait une marge de **0.0052**, soit **0.28 erreur-type** (σ=0.0184 sur `n_eval`=640).
> `assert_bar_is_reachable`, la garde livrée la veille, exige `> barre + σ` = 0.3351 : **appliquée à ce
> chiffre, elle REFUSE**. Ce qui survit au recalcul est le **ratio 2.17** (~6.7 σ) et la **montée en
> `lr`** ; pas le franchissement de barre. Cela renvoie à **P2.15** : tant que `1/K+0.15`, constante
> importée d'une autre tâche, n'est pas refondée sur une référence INTRA-dispositif, tout verdict lu
> contre elle est sans contenu.

## Question

3ᵉ arête du graphe AGI-Taxonomy, et **première ablation de SUBSTRAT**. La tentative précédente
([[EDR-LANG-MEMORY]]) souffrait d'une **équivocation de nœud** : sa sonde est mono-agent, alors que
`capabilities.json` définit `language` comme référentiel/coordination (sender, receiver, canal, asymétrie
d'information) — graver ainsi aurait écrit « le langage exige la mémoire » sur une mesure où aucun langage
n'était échangé. D'où cette forme : un **jeu de Lewis DIFFÉRÉ**, qui instancie le nœud pour de vrai —
le sender voit un référent au tick 1, le receiver choisit au tick 1+D, l'ablation est une substitution de
l'état porté du receiver.

## Verdict : NÉGATIF — l'arête n'est PAS gravée

Le crible fail-fast, prévu au design pour tuer le round tôt et pas cher, a échoué et n'a jamais été
franchi. Aux réglages prescrits (D=2, 800 épisodes, `n_agents=16`, `lr=0.05`, `flip_p=0.3`, 3 seeds,
plancher `1/K = 0.167`) :

| critère | mesure | lecture |
|---|---|---|
| RETAIN (bras testé) apprend | `[0.186, 0.164, 0.206]` | **ÉCHEC** — au plancher |
| RETAIN s'effondre sous ablation | `[0.159, 0.139, 0.158]` | non adjudicable (part du plancher) |
| PRESENT (contrôle de demande) vivant | `[0.167, 0.186, 0.186]` | **ÉCHEC par le BAS**, pas par saturation |
| PRESENT inerte sous ablation | Δ `0.010 / 0.014 / 0.005` | non adjudicable — un bras au plancher est inerte à tout |

Les deux « non adjudicables » sont le cœur de l'honnêteté de ce record : compter le 4ᵉ critère comme un
`pass` aurait gravé l'arête sur un contrôle qui **valide n'importe quoi**. C'est exactement la
dégénérescence que la garde armée le 2026-09-01 (occurrence 3 d'E3) existe pour refuser.

## Ce que la mesure a trouvé, et qui n'était pas la question posée

### 1. Un défaut de CONCEPTION du protocole, mesuré

Le design imposait, au nom de la symétrie des deux bras par la DATE de présentation, un **référent-leurre
au tick de choix**. C'est lui qui plancherise tout. Mesuré à **`D=0`, `flip_p=0`, `episodes=800`,
`n_agents=16`, `K=6`, 3 seeds** — le régime est inscrit DANS le tableau, et pas seulement dans le texte,
parce qu'il a fallu le RECONSTRUIRE après coup (§ encart) faute de l'avoir écrit ici la première fois :

| condition (`flip_p=0`, D=0) | PRESENT |
|---|---|
| avec leurre (design d'origine) | **0.170** (plancher) |
| leurre retiré | **0.338** |
| référence Lewis publiée ([[EDR-LANG-PERCEPTION]]) | 0.342 |

⚠️ Ces trois valeurs ne sont PAS comparables à une cellule mesurée au défaut du module (`flip_p=0.3`) :
au bruit par défaut, le bras le plus facile plafonne à **0.239**. Voir l'encart en tête pour la conséquence
— une barre inatteignable fait un instrument à issue unique.

Soit la référence **à 0.004 près**. Mécanisme, et il est ironique : `logit = (1−δ)·H_prev + δ·tanh(…)`
avec δ médian ≈ 0.5, et **108 des 113 nœuds portés SONT les nœuds de readout**. Un leurre présenté au tick
de choix injecte donc une **réponse concurrente de même amplitude** dans les logits mêmes qu'on lit. C'est
la propriété qui avait servi, dans le design, à **interdire** l'ablation par H-reset — et le protocole l'a
heurtée de l'autre côté.

⚠️ Retirer le leurre est **nécessaire mais NON SUFFISANT** : sur la variante fidèle à l'arête gravée,
RETAIN monte à **0.223** — toujours sous la barre `1/K + 0.15 = 0.317`. Suspect suivant identifié mais
**NON vérifié** : le crédit des actions neutres, qui croît avec la longueur de séquence.

### 2. Le report PASSIF marche ; l'ÉCRITURE APPRISE dans le report ne marche pas

C'est le contenu scientifique de ce round, et il est mécanique.

Une hypothèse intermédiaire — « `learn_episode` détache `H` à chaque pas, donc aucun gradient ne façonne la
rétention » — a été **posée puis réfutée par la mesure** : l'arête gravée [[EDR-MEM-PERCEPTION]] atteint
**0.564 à D=2 sous `learn_episode`**, par report **passif** (`_step` écrit l'observation dans `H[:, :I]`,
δ la porte, et le readout apprend à la décoder). La troncature n'interdit donc pas toute rétention : elle
interdit d'apprendre à **ÉCRIRE** dans le report.

Prédiction qui en découle, faite avant mesure puis **vérifiée** : remplacer le chemin de crédit par un
chemin traversant le report ne doit rien changer, puisque le problème n'est pas le gradient mais ce qu'il
peut atteindre. Mesuré, RETAIN reste au plancher sur les **trois** chemins :
`learn_episode_bptt(truncate=False)` → `[0.191, 0.192, 0.184]` ; `imitate_episode_bptt` masqué au dernier
pas → `[0.209, 0.191, 0.203]` ; `reinforce` → `[0.186, 0.164, 0.206]`.

### 3. Une alerte sur une arête GRAVÉE, levée par réplication

Une mesure intermédiaire suggérait que la sonde de référence — celle qui a gravé `language→perception` —
tombait elle aussi au plancher à son point de fonctionnement prescrit. **Répliqué et RÉFUTÉ** au point
réellement publié (`episodes=800`, `n_agents=16`, `lr=0.05`, `sender_mode='learned'`) :

`coord_intact` **[0.3422, 0.3063, 0.4047]** (médiane 0.342 contre **0.34375** publié) ·
`coord_ablated` [0.1656, 0.1672, 0.1531] (contre 0.1625) · ratio **2.066** contre **2.115** ·
`nocoord` vivant 0.731-0.759 (contre ~0.74). **`language→perception` n'est pas menacée.**

Classe **E8** appliquée : le signe n'a pas été propagé par raisonnement, il a été mesuré avant d'être écrit.

## Portée (bornée)

- **Ce record ne dit PAS que la coordination différée n'exige pas la rétention.** Il dit que la tâche,
  **telle que spécifiée et sur ce substrat**, n'est pas apprenable — donc que l'arête n'est pas mesurable
  ainsi. Le bras principal n'ayant jamais décollé, aucun verdict de demande n'est interprétable.
- **n=3 partout**, sauf la réplication de la référence (n=3 également) : suffisant pour tuer un round au
  crible, **insuffisant pour graver quoi que ce soit** de positif (garde d'évaporation de puissance).
- **NON RÉPLIQUÉ** par une seconde main, et à re-mesurer avant citation comme fait : la bascule du leurre
  (0.170 → 0.338), le 0.564 à D=2 de MEM-PERCEPTION sous `learn_episode`, et les valeurs du crible.
  Seule la réplication de la sonde de référence (§3) a été refaite indépendamment.
- Les chiffres pilotes qui fondaient le design (RETAIN 0.62-0.65) **ne sont reproduits par aucune** des
  configurations × 3 chemins de crédit mesurés ; ils correspondent vraisemblablement à un canal
  oracle-équivalent — auquel cas l'équivocation de nœud que ce design existait pour lever serait revenue
  intacte. C'est la raison pour laquelle le round s'arrête au lieu d'appliquer un quatrième correctif.

## Ce que ça débloque

Le prochain levier n'est pas un correctif de plus sur ce protocole, c'est la question que la mesure a
isolée : **comment fait-on apprendre à ÉCRIRE dans le report ?** Le report passif étant acquis (0.564) et
l'écriture apprise étant au plancher sur trois chemins de crédit, c'est là qu'est le mur — et il est
nommé, pas conjecturé.

Deux dettes ouvertes par ce round, inscrites au backlog :
- la garde `assert_verdict_invariant_to_optimizer` (livrée le 2026-09-01) tire **dégénérément** quand
  c'est le bras de RÉFÉRENCE qui s'effondre : l'écart se referme sans que le bras testé monte. Motif E3
  dans la garde même qui traque les nuls artefactuels. Balayage mesuré ici (bras testé = émission Lewis
  apprise, bras de référence = canal ORACLE, même sonde, même seed, `episodes=1200`) : `lr=0.02` → testé
  **0.141**, référence **0.436** (écart 0.295) ; `lr=0.08` → testé **0.203**, référence **0.194** (écart
  −0.009) ⇒ closure = 1 − (−0.009/0.295) ≈ **103.1 %**, au-dessus du seuil 2/3 — la garde (avant
  correctif) lit ça comme un « artefact d'hyperparamètre » alors que le bras testé reste dans la bande
  du crible publié ci-dessus (0.164-0.206) et que c'est la RÉFÉRENCE qui s'effondre. **Ces quatre chiffres
  sont la provenance du contre-exemple gelé**
  `test_optimizer_sweep_returns_INCONCLUSIVE_when_the_REFERENCE_collapses`
  (`tests/sandbox/test_experiment_preflight.py`) ; corrigé au commit `8d0b959` (paramètre opt-in
  `reference_floor` + exception `ReferenceCollapsedError`) ;
- la classe **E10** a récidivé deux fois dans la journée sur `tests/sandbox/test_instrument_calibration.py`
  (fichier partagé à forte contention), dans les deux sens — sa règle de promotion s'applique.

Cf. [[EDR-LANG-PERCEPTION]] (référence, répliquée), [[EDR-MEM-PERCEPTION]] (report passif),
[[EDR-LANG-MEMORY]] (tentative précédente, équivocation de nœud), [[EDR-RETAIN-COMPOSE-LR]] (classe E19).
