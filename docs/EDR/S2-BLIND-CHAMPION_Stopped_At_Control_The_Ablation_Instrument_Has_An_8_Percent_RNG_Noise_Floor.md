---
id: EDR-S2-BLIND-CHAMPION
type: EDR
title: "ARRÊTÉ AU CONTRÔLE, et le contrôle a rapporté plus que la DV : l'instrument d'ablation de perception a un PLANCHER DE BRUIT de ±6-8 % dû à la DÉSYNCHRONISATION DE BANDE RNG — le champion publié est à 0,991, donc DEDANS"
status: active
verdict: INDETERMINE_HARNAIS_ABLATION_INSTRUMENT_HAS_8PCT_RNG_NOISE_FLOOR
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
extends: [EDR-EVO-011]
---

> ⚠️ **Ce record ne rapporte AUCUN verdict sur sa DV.** La règle scellée
> (`docs/preregistrations/S2-BLIND-CHAMPION.json`) impose : un contrôle qui échoue → `INDETERMINE-HARNAIS`,
> et **ne pas lire la suite**. Le contrôle a échoué. Ce qui suit est un résultat sur l'INSTRUMENT —
> et il vaut plus que la DV qu'il empêche de lire.

## Ce qui était demandé

Un champion dont on annule les lignes d'entrée de `W` survit-il mieux que le champion intact, dans
`stoneage` ? Observation d'origine à **n=1 seed**, faite en cherchant un contrôle NÉGATIF pour le
design de variance inter-sujets : **27,5 → 38,2 ticks, +39 %**. La règle scellée met cela à l'épreuve
sur 7 seeds appariées, avec quatre contrôles et une branche `PAS_DE_COUT` capable de RÉTRACTER
l'observation — sans quoi le dispositif n'aurait pu que la confirmer (classe E1).

## Le run (`results/s2_blind_champion.json`, 7 seeds, 14 cellules, 508 s)

| seed | intact | aveugle | r | contrôle (ii) `within` aveugle |
|---|---|---|---|---|
| 2026 | 27,5 | 38,2 | 1,391 | 0,933 |
| 3026 | 24,2 | 39,0 | 1,608 | 0,897 |
| 3027 | 22,2 ⚠️ | 39,0 | 1,753 | 0,897 |
| 3028 | 22,2 ⚠️ | 39,0 | 1,753 | 1,013 |
| 3029 | 26,0 | 35,8 | 1,375 | 0,941 |
| 3030 | 22,2 ⚠️ | 35,8 | 1,607 | 0,966 |
| 3031 | 24,5 | 35,8 | 1,459 | 1,059 |

La FAMILLE de contrôles est déclarée d'avance via `assert_control_family` (7 cellules, Bonferroni, `alpha_cell` = 0,05/7 = 0,00714) — la garde E23 livrée la veille, appliquée à son premier run réel. Elle n'a rien eu à refuser ici : le contrôle (ii) a échoué sur une AMPLITUDE, pas sur un seuil.

⚠️ = bras intact SOUS le plancher `PLANCHER_NOPERC["stoneage"]` = 24,0, donc écarté et NOMMÉ (issue
légitime déclarée d'avance). Contrôle (i) « intervention réelle et minimale » : **ok sur 7/7**
(`W[:num_inputs, :] == 0` exact, reste bit-identique). `assert_not_degenerate` passe.

**Contrôle (ii) ÉCHOUE** : l'AVEUGLE reste « sensible » à l'ablation de perception de 6 à 10 %, alors
qu'aucune information perceptive ne peut atteindre sa politique. Verdict scellé : **`INDETERMINE-HARNAIS`**.

## Pourquoi le contrôle a échoué — MESURÉ, pas supposé

Le code portait depuis toujours ce commentaire : *« l'ablation consomme des tirages RNG en plus →
tape intra-ère non identique »*. Personne ne l'avait **chiffré**. Trois mesures l'ont fait.

**1. Le NO-OP EXACT.** `NullAblatedMamba` (livré ici, `tools/s2_demand_ablation.py`) appelle
`derange_rows` — donc consomme exactement les mêmes tirages du flux global, boucle de rejet
comprise — puis **jette** la permutation. La perception reste INTACTE ; seule la bande bouge.

| sujet | `within_ratio` du NO-OP (perception intacte) |
|---|---|
| champion | **1,058** |
| champion aveuglé | **0,922** |

**±6-8 % de « sensibilité à l'ablation » sans qu'aucune observation n'ait changé.** C'est le plancher
de bruit de l'instrument, et il n'avait jamais été mesuré.

**2. L'appariement de bande le divise par 6.** `derange_rows` tire `permutation(B)` jusqu'à obtenir
un dérangement ; ces tirages ne dépendent QUE de l'état du RNG et de `B`, jamais des observations.
Faire consommer les mêmes tirages au bras de référence resynchronise donc les deux bras :

| sujet | ratio à BANDE APPARIÉE (no-op vs ablation) |
|---|---|
| champion aveuglé | **1,0122** |
| champion | **0,9369** |

**3. Le résidu de 1,2 % dit que l'intervention n'est PAS ce que le sceau affirme — et la cause
mesurée n'est aucune de celles que j'avais d'abord nommées.**

> ⚠️ **RECTIFICATION (2026-09-08, dans les heures qui ont suivi).** La première version de ce record
> attribuait le résidu à deux chemins : `H[:, :max_I] = x` et `world_model.observe_batch(...)`. Le
> second est **FAUX dans ce régime** — `MambaBatchModel.world_model` vaut `None` ici, donc le chemin
> de surprise est inactif, vérifié à l'exécution. C'était une inférence, la même faute que celle que
> ce record dénonce, commise dans le paragraphe qui la dénonce. Ce qui suit est mesuré.

Sonde à réponse connue : un génome dont `W[:num_inputs, :] = 0` doit produire des logits d'action
**invariants** quand on change l'observation. Modèle neuf par configuration, RNG épinglé, et le no-op
(même observation deux fois) mesuré d'abord — il vaut **0,0 exactement**, donc la sonde ne mesure pas
son propre bruit.

| configuration | no-op | logits(o1) vs logits(o2) |
|---|---|---|
| champion intact | 0 | 3,63 |
| `W[:num_inputs,:] = 0` | 0 | **1,52** |
| ... + `W_router = 0` | 0 | **1,52** |
| ... + `ABLATE_ROUTER` | 0 | **1,52** |

Ni les arêtes d'entrée de `W`, ni le routeur neuromodulateur, ni le compilateur NTM (qui laisse ces
arêtes à zéro, vérifié), ni le monde-modèle. **La cause est structurelle** :

> Le génome du champion déclare **64 entrées et 126 sorties dans un réseau de 172 nœuds**. 64 + 126 =
> 190 > 172 : les blocs d'entrée et de sortie **SE CHEVAUCHENT sur 18 nœuds**. Or `forward` écrit
> l'observation dans `H[:, :max_I]` et lit les logits d'action à partir de `max_I + max_H`, où
> `max_H = **−18**`. **Les 18 premiers logits d'action SONT l'observation** (composantes 46 à 63,
> multipliées par le masque d'attention), à 0,0025 près — l'écart résiduel étant la mise à jour
> `(1−δ)·H + δ·tanh(...)` sur ces mêmes slots. Vérifié composante par composante.

Un agent FRAIS n'a pas ce défaut : 59 + 108 = 167 ≤ 172. Le chevauchement est propre à la lignée du
champion (la divergence `num_inputs` 64 ↔ 59 déjà connue), et **rien ne le signale** : `max_H`
devient simplement négatif, en silence.

**Trois conséquences, dans l'ordre de gravité.**

1. **L'intervention « aveugler » de ce run est INVALIDE** : on ne supprime pas un chemin d'IDENTITÉ en
   annulant des poids. Le `-bis` devra aveugler à l'ENTRÉE (comme le fait déjà
   `PerceptionAblatedMamba`), pas dans `W`.
2. **18 des 126 logits d'action du champion sont l'observation brute**, sans un seul poids entre les
   deux. Toute lecture de « la politique traite-t-elle l'observation ? » sur CE sujet doit le dire —
   à commencer par [[EDR-EVO-004]] (saillance au plancher sur tous les canaux) : une saillance nulle
   mesurée sur une politique dont un dixième des sorties EST l'entrée n'a pas le même sens.
3. **Le verdict `PERCEPTION_DECOY` publié n'est PAS invalidé** : `PerceptionAblatedMamba` permute
   `batch_obs` à l'entrée, donc il ablate bien les deux chemins, chevauchement compris. Ce que ce
   record ajoute, c'est qu'une partie de ce que l'instrument ablate est un fil droit, pas un calcul.

La question scellée dit « les lignes d'entrée de W mises à zéro : l'observation n'entre plus dans le
calcul ». C'est une **inférence**, et elle est fausse — pas seulement incomplète : sur CE génome,
l'observation atteint les logits d'action **sans traverser un seul poids**. Classe **E8**, commise
dans la formulation même d'une règle scellée. Une règle scellée ne se corrige pas : la reprise se fera
sous `-bis`, en aveuglant à l'ENTRÉE (le seul endroit où le chevauchement est aussi coupé) et non
dans `W`.

## Ce que cela change pour tout ce qui utilise cet instrument

`run_ablation_map` porte les verdicts `PERCEPTION_DEMANDED` / `PERCEPTION_DECOY` de S2-002/003 et
d'`EDR-124`. Son `within_ratio` publié pour le champion vaut **0,991** — **à l'intérieur** de la bande
de bruit [0,922 ; 1,058] que le no-op vient de mesurer.

Cela ne fabrique **aucun faux `DEMANDED`** : du bruit ne crée pas de demande, et les verdicts négatifs
publiés restent des négatifs. Mais cela **borne la résolution** de tout l'arc : une demande
perceptive inférieure à ~8 % est INVISIBLE à cet instrument dans ce régime. `PERCEPTION_DECOY` doit
donc se lire « aucun effet DÉTECTABLE au-dessus d'un plancher de bruit de 8 % », jamais « aucun effet ».
`noop_control=True` est désormais disponible sur `run_ablation_map` (défaut `False`, donc
bit-identique pour tous les appelants existants : aucun record ne bouge) pour que ce plancher soit
mesuré à côté de chaque ratio publié.

## La DV, rapportée et NON LUE

`r` vaut 1,375 à 1,753, **dans le même sens sur 7 seeds sur 7**. C'est très au-dessus du plancher de
bruit de 8 %, et cela reste **sans valeur probante** tant que le contrôle échoue : le sceau l'interdit,
et la raison est bonne — on ne sait pas encore quelle part vient de la politique et quelle part du
monde-modèle. `r_blind` et `sign_p` sont rendus `nan`, `n=0`, exactement comme la règle l'exige. Les
seeds 3027, 3028 et 3030 sont écartés (bras intact sous le plancher) et nommés.

Deux DV secondaires publiées sans poids : les deux bras rendent `PERCEPTION_DECOY` partout où le
verdict est lisible, et `intact_median` du champion oscille entre 22,2 et 27,5 selon la seed — donc
**le champion lui-même est au niveau du plancher no-perception (24,0)**, ce qui est cohérent avec le
verdict DECOY publié et explique pourquoi le plancher écarte des seeds presque au hasard.

## Ce que la suite doit faire

1. Re-sceller en `-bis` en aveuglant **à l'entrée** et non dans `W` : c'est le seul point où le
   chevauchement entrée/sortie est coupé lui aussi. (La version initiale de ce point disait « et un
   bras qui coupe aussi le monde-modèle » : sans objet, `world_model` est `None` dans ce régime.)
2. Mesurer à **bande appariée** (`NullAblatedMamba` comme référence au lieu du bras nu) : le plancher
   de bruit tombe de 8 % à ~1 %, ce qui rend enfin lisible une demande perceptive faible.
3. Reprendre `S2-SUBJECT-VARIANCE`, arrêté à son smoke le même jour : ses deux contrôles câblés
   survivent 6-8 ticks contre un plancher de 24,0 — et la mesure du couplage amplifié
   (27,5 → 13,8 à ×3 → 6,2 à ×8) dit pourquoi un contrôle POSITIF in-world n'est pas constructible
   par amplification dans ce monde.

Converge [[EDR-EVO-011]] (lire le canal de type coûte la survie, r=0,631 : même direction, mesurée
sur un lecteur câblé et non sur le champion), [[EDR-124]] et S2-002/003 (dont il borne la résolution),
REF-DEMAND-MARKER (le gabarit within-subject, dont il chiffre le bruit pour la première fois).
