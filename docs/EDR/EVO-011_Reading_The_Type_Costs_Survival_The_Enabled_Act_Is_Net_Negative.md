---
id: EDR-EVO-011
type: EDR
title: "Le pré-vol RÉPOND et ferme EVO-011 sans run évolutif : lire le canal de type COÛTE la survie (r=0,63, sign_p=0,006, 12/12 contrôles) — parce que l'ACTE que la lecture débloque est net-négatif en énergie"
status: active
verdict: READING_COSTS_SURVIVAL_ENABLED_ACT_IS_NET_NEGATIVE
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
extends: [EDR-EVO-004]
---

## Question, et pourquoi un pré-vol

EVO-011 avait été ARRÊTÉ au pré-vol : trois défauts de harnais (`do_throw` gaté par
l'inventaire, `_throw_did` écrit seulement en branche torche, `life_score` incohérent), aucun
résultat rapporté. La question restait ouverte — **la survie seule garde-t-elle une
cognition ATTEIGNABLE sur un canal à contenu de monde (`obs[4]`, le type d'apex) ?**

Un run évolutif n'était pas nécessaire pour y répondre. Si un lecteur **câblé à la main** — le meilleur
lecteur possible, que l'évolution ne pourrait qu'approcher — ne survit pas mieux qu'un témoin
identique sans l'arête, alors la sélection par la survie ne peut pas retenir cette lecture, quelle que
soit sa capacité à la découvrir. C'est le pré-vol scellé ici, et il **répond**.

## Règle scellée, et pourquoi elle a dû être re-scellée

`docs/preregistrations/EVO-011-PREVOL.json` (chaîne RÉELLE : la chaîne `throw → kill` de la règle
d'origine `EVO-011.json` est **coupée par construction** — un lancer ÉTOURDIT, il ne tue pas ;
registre E2 occ. 3). Trois bras à cohorte fixe de 24 clones, 200 ticks, 12 seeds, sous bail `kuzu` :

| bras | arête | rôle |
|---|---|---|
| **TÉMOIN** | `W[4, o+8] = 0.0` exact | ne lance jamais (`logits[8] = 0` exactement) |
| **LECTEUR** | `W[4, o+8] = +8.0` | l'arête EXACTE de la règle |
| **BROUILLÉ** | `+8.0`, mais `obs[4]` remplacé par ±1 sur un RNG DÉDIÉ | sépare « lire le TYPE » de « LANCER » |

**Le premier run a rendu `INDÉTERMINÉ-HARNAIS`** (`results/evo011_preflight.json`, gravé) : 11 seeds
sur 12 passent tous les contrôles, le seed 9 fait échouer le contrôle (i) — `P(throw | type = −1)`
= 0,800 (n=25) hors la bande scellée (0,25 ; 0,75). Ce n'était pas du bruit sur ce seed (binomial
bilatéral exact p = 0,004), **mais le contrôle est appliqué à une FAMILLE de 24 cellules** (2 types
× 12 seeds) et son taux de fausse alarme n'avait jamais été contrôlé. Calcul exact, aux n réellement
observés, sous l'hypothèse d'un brouillage PARFAIT : **P(au moins une cellule hors bande) = 0,216**.
Un harnais parfaitement correct faisait donc échouer ce contrôle **une fois sur cinq**.

Une règle scellée ne se corrige pas : re-scellée en `EVO-011-PREVOL-bis`, **une seule clause changée**,
le correctif fixé par PRINCIPE (contrôler le FWER à 0,05) et non pour obtenir une issue — la bande
fixe devient un test binomial exact au seuil de Bonferroni `α' = 0,05/24 = 0,002083`, la taille de la
famille étant connue d'avance puisque le n est scellé. Les deux propriétés sont **exigées et testées** :
le FWER retombe à ≤ 0,05, **et le contrôle sait encore ÉCHOUER** (un brouilleur réellement cassé,
p = 0,9 sur n = 25, donne p ≈ 1e-5 ≪ α' et est refusé) — sans cette seconde, le correctif aurait été
un contrôle qui ne peut plus échouer, c.-à-d. pire que le défaut (classe E1).

> C'est **exactement la même classe de défaut** — une famille de tests non traitée comme une famille —
> que la correction de Holm silencieusement perdue dans `tools/s2_demand.py::run_s2`, trouvée et
> corrigée le même jour. Ici elle joue en sens INVERSE : fausse alarme au lieu de p-hacking.

## Résultat (`results/evo011_preflight_bis.json`, n = 12, 12/12 contrôles passés)

| bras | lancers (méd.) | énergie phase ACTION (méd.) | âge médian (méd. sur seeds) |
|---|---|---|---|
| TÉMOIN | 0 | −47 | **20,8** |
| LECTEUR | 95 | 814 | **13,8** |
| BROUILLÉ | 164 | 1319 | **11,0** |

**DV primaire scellée** — `r` = médiane sur seeds de (âge médian LECTEUR / âge médian TÉMOIN) :

**r = 0,631**, `sign_p` = **0,0064**, **11 seeds sur 12 sous 1,0**.

Branche scellée `r ≤ 1,10` → **`NE PAIE PAS`**. Aucun run évolutif n'est engagé : c'est la branche
« réponse sans évoluer » prévue par la règle d'origine.

Contrôles, tous passés sur les 12 seeds : saillance de décision 0,000 (TÉMOIN) / 1,000 (LECTEUR) ;
`P(throw | obs4=+1)` = 1,000 et `P(throw | −1)` = 0,000 pour le LECTEUR ; `throws = 0` EXACT pour le
TÉMOIN ; arête `W[4,o+8]` = 0,0 / 8,0 / 8,0 **exacte en fin de run** ; identité de décision au seam
batch (E6) ; empreinte monde+RNG **identique** entre bras à t=0 (E5) ; `life_score` recomposable ;
port à âge apparié ; **censure 0 %** partout ; dérive du génome 0,0 (gel de la plasticité intra-vie).

## Grandeurs scellées, MESURÉES (médianes sur les 12 seeds) — aucune omission

Le cliquet `check_preregistration_applied.py` exige que toute grandeur nommée par la règle figure
dans le record : une DV scellée qu'on ne rapporte pas est une DV substituée (classe E11).

| grandeur scellée | TÉMOIN | LECTEUR | BROUILLÉ |
|---|---|---|---|
| `throw_decided` (décisions, TOUT régime — compteur posé le 2026-09-07 hors du gate d'inventaire) | 0 | 95 | 163,5 |
| `throw_prey_hits` | 0 | 24,5 | 35,5 |
| `env.big_kills` / `env.leurre_hits` | 8,5 / 5 | 7 / 5 | 7 / 5 |
| `sum(mammoth_kills)` (crédit de meute, à côté du compteur monde) | 13,5 | 11 | 12 |
| `measure_decision_saliency` (instrument calibré) | **0,000** | **1,000** | 1,000 |
| `W[4, o+8]` en FIN de run (contrôle (ii)) | **0,0 exact** | **8,0 exact** | 8,0 exact |
| `calculate_life_score` — écart au score recomposé (contrôle (vi)) | 0,0 | 0,0 | 0,0 |

⚠️ `big_kills`, `leurre_hits` et `mammoth_kills` sont **SATURÉS** (population d'apex épuisée dans les
trois bras) : leur quasi-égalité n'est PAS une absence d'effet, et le runner le DIT au lieu de laisser
la lire comme un nul. `throw_prey_hits ≥ 1` (contrôle (iv)) est atteint : la chaîne se ferme réellement.

**Contrôles du pré-vol, tous exécutés et tous passés** : `assert_n_per_arm` (24 agents/bras),
`assert_not_degenerate` (âges de chaque bras), `assert_ablation_changes_something` (profils
`P(throw|type)` différents entre LECTEUR et BROUILLÉ), `CostGuard` (plafond 150 s/seed) et
`project_cost` APRÈS le smoke (2,4 s/seed mesuré, 1,4 min projeté ≤ 30 min de budget).

⚠️ **Écart de régime déclaré (E6)** : la décision est lue au seam BATCH, celui qui agit ; mesuré contre
`recurrent_forward` (H=0), l'écart de logit vaut **6,997** pour LECTEUR et BROUILLÉ — c'est précisément
pourquoi la lecture hors régime aurait menti, et le contrôle (i+) vérifie que la décision LUE est
identique au `throw_decided` incrémenté par le monde (0 désaccord sur les 12 seeds).

## Ce que ça dit, et ce que ça ne dit pas

**Le verdict est plus fort qu'un nul : lire COÛTE.** Le lecteur ne « manque pas » de payer, il vit
**37 % moins longtemps**. Et le mécanisme est lisible dans le bilan énergétique, pas inféré : le
lancer facture ~8 énergie, la phase ACTION passe de −47 (témoin) à 814 (lecteur) à 1319 (brouillé), et
**les agents meurent de FAIM, pas de riposte** (morts énergie/hp = 24/0 dans les trois bras). La
dose-réponse est monotone sur les trois bras — plus on lance, moins on vit.

⚠️ **Le maillon que la règle avait scellé n'est PAS celui qui agit**, et le runner le MESURE au lieu
de l'inférer : la riposte encaissée vaut 41–63 hp pour 1320 hp de départ (**3–5 %**). Le dernier
maillon (« mêlée SANS riposte ») est quantitativement négligeable ici. Ce qui décide est le CANAL DE
COÛT, en amont de toute la chaîne scellée. Le verdict de survie tient — c'est une comparaison de
survie, pas une lecture de mécanisme — mais toute lecture mécaniste doit passer par l'énergie.

**DV secondaires, rapportées SANS poids** (la règle ne les rend décisives que dans la branche haute,
qui n'est pas atteinte) : LECTEUR/BROUILLÉ **r = 1,35**, `sign_p` = 0,00098 ; BROUILLÉ/TÉMOIN
**r = 0,52**. Lu littéralement : *lire le type a de la valeur CONDITIONNELLEMENT au fait de lancer*
(lancer à bon escient bat lancer au hasard de 35 %), mais **l'acte lui-même est net-négatif**, donc
aucune quantité de lecture ne peut battre le fait de ne pas lancer. La survie ne peut pas sélectionner
une lecture dont l'acte aval coûte plus qu'il ne rapporte.

**Portée.** Un banc, un monde (`Biosphere3D` + `_setup_lewis`), un canal (`obs[4]`), un acte (le
lancer), un régime (24 clones, 200 ticks, énergie 80). Le résultat ne dit rien d'un monde où lancer
serait rentable — il dit que **dans CE monde**, le canal `obs[4]` n'a pas de débouché survivable, ce
qui explique pourquoi l'évolution ne le lit pas. Deux saturations sont rapportées et **non
bloquantes** : la population d'apex est ÉPUISÉE dans les trois bras (`big_kills` / `leurre_hits`
saturés — leur égalité entre bras n'est PAS une absence d'effet), et le LATCH du logit fait que le
lecteur continue à lancer hors adjacence après avoir vu un mammouth (`P(throw | obs4=0)` = 0,039
contre 0,000 pour le témoin) — voie causale alternative, non scellée, non corrigée.

## Convergences

Ferme la question qu'EVO-011 avait laissée OUVERTE en s'arrêtant au pré-vol sur trois défauts de harnais (aucun record : l'arrêt n'avait rien produit à graver ; la règle d'origine `docs/preregistrations/EVO-011.json` reste scellée et NON appliquée). Corrobore causalement
[[EDR-EVO-003]] et [[EDR-EVO-004]] (la politique évoluée ignore `obs[4]`) en donnant la RAISON : ce
n'est pas seulement qu'elle ne le lit pas, c'est que le lire ne se paie pas. Renforce **S2-012** et le
fil [[s2-world-demand-thread]] : le monde exige la survie, pas la perception — ici on mesure pourquoi.
Adopte REF-EXPERIMENT-PREFLIGHT (le pré-vol a répondu et a économisé le run évolutif complet).
