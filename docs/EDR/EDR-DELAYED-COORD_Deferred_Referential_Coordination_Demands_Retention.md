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
au tick de choix**. C'est lui qui plancherise tout. Mesuré à D=0 :

| condition | PRESENT |
|---|---|
| avec leurre (design d'origine) | **0.170** (plancher) |
| leurre retiré | **0.338** |
| référence Lewis publiée ([[EDR-LANG-PERCEPTION]]) | 0.342 |

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
  dans la garde même qui traque les nuls artefactuels ;
- la classe **E10** a récidivé deux fois dans la journée sur `tests/sandbox/test_instrument_calibration.py`
  (fichier partagé à forte contention), dans les deux sens — sa règle de promotion s'applique.

Cf. [[EDR-LANG-PERCEPTION]] (référence, répliquée), [[EDR-MEM-PERCEPTION]] (report passif),
[[EDR-LANG-MEMORY]] (tentative précédente, équivocation de nœud), [[EDR-RETAIN-COMPOSE-LR]] (classe E19).
