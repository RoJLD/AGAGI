---
id: EDR-DREAM-006
type: EDR
title: "La localisation du registre par ROLE de nœud est confondue par la TAILLE (input 59 / hidden 5 / output 108) : le « cœur récurrent » n'est que 5 nœuds sur 172 — confondant attrapé AVANT le run n=12, pas après"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-DREAM-005]
---

## Question
[[EDR-DREAM-004]]/[[EDR-DREAM-005]] : le bénéfice exige un bruit PORTÉ par l'état récurrent. Question
posée : **DANS l'état porté, quel registre** le bruit doit-il toucher pour débloquer la reproduction —
le cœur récurrent, ou un readout sémantique (valeur 28, goal, NTM) ?

## Méthode
Seam `MambaBatchModel.DREAM_NOISE_GROUP` (défaut "all" = prod inchangée) restreignant le bruit du rêve
à un rôle de nœud — input / hidden / output — via un masque **calibré** (partition exacte prouvée au
point d'injection : disjoints + union = tous les nœuds réels, `test_dream_node_group_mask.py` 5/5, car
le couplage par `W` rend « seuls ces nœuds ont changé » intestable après un forward). Smoke 2 seeds :
off | H_all (= le H_0.2 gagnant de DREAM-004) | H_hidden | H_output | H_input.

## Résultat du smoke (n=2) et le CONFONDANT qu'il révèle

| bras | seed0 `n_lived` | seed1 `n_lived` | nœuds noisés |
|---|---|---|---|
| off | 96 | 56 | 0 |
| H_all | 1135 (11.8×) | 602 (10.7×) | 172 |
| **H_hidden** | **157 (1.6×)** | **61 (1.1×)** | **5** |
| H_output | 1838 (19.1×) | 316 (5.6×) | 108 |
| H_input | 1109 (11.6×) | 3131 (55.9×) | 59 |

**Non-régression validée** : H_all reproduit `n_lived` de DREAM-004 à l'identique (seed0 1135) → le
seam à "all" est bit-identique au chemin historique.

**Le CONFONDANT** : les groupes diffèrent d'un facteur **20 en taille** — input 59, hidden **5**,
output 108 nœuds. À σ=0.2 par nœud, « H_hidden faible » injecte 20× moins de bruit TOTAL que H_output.
Impossible de dire si le cœur récurrent est faible *parce que c'est le cœur* ou *parce qu'il n'a que 5
nœuds sur 172*. Et le smoke est **incohérent entre seeds** : seed0 output > input, seed1 input ≫ output
(55.9× vs 5.6×) — ni la taille ni un registre stable n'expliquent le motif.

## Verdict
**`ROLE_BASED_LOCALIZATION_IS_SIZE_CONFOUNDED__NOT_RUN`**

Le design par rôle **n'identifie pas** le registre : la comparaison est confondue par la taille du
groupe, et le n=2 montre déjà une variance inter-seed qui interdit tout verdict propre. **Lancer la n=12
(≈2 h, les bras forts explosent `n_lived`) aurait mesuré une grandeur confondue** — précisément le
mode d'échec que le pré-vol du dépôt existe pour prévenir. Le confondant est attrapé AVANT le run.

## Le seul fait robuste, et sa vraie portée
`H_hidden` est faible sur les deux seeds. Mais **le « cœur récurrent » de cette architecture n'est que
5 nœuds sur 172** — l'état est dominé par les nœuds d'entrée (59) et de sortie (108). « Cœur faible »
est donc indissociable de « 5 nœuds seulement ». Ce que ça dit vraiment : la dynamique récurrente vit
dans une couche cachée **minuscule**, et l'essentiel de l'état porté EST la périphérie I/O — cohérent
avec [[from-genome-flattens-architecture]] (le connectome est plat, peu de vraie profondeur cachée).

## Prochaine étape (non lancée — arbitrage)
Pour localiser proprement, deux designs qui contrôlent la taille :
1. **Nombre de nœuds apparié** : noiser exactement K nœuds tirés de chaque rôle (K = 5, la contrainte
   du cœur), même σ → seule la ROLE varie. Exige un sous-échantillon fixé par épisode (cache).
2. **Registres sémantiques** (le plus interprétable, réponse directe à « satiété / maturité repro ») :
   noiser seulement la valeur (nœud 28), le goal (5 nœuds), l'action (8), les têtes NTM (20) — tous
   petits et comparables. Exige un seam par plage d'indices de `preds`.

## Leçon (registre) — E13 en positif
La discipline du pré-vol a fonctionné : le confondant de taille a été mesuré (compter les nœuds par
groupe) AVANT d'engager le run, pas découvert dans les résultats. Un design par rôle sur des groupes de
tailles 5/59/108 produit des chiffres nets mais ininterprétables — la forme exacte des faux résultats
que le dépôt collectionne (aliasing WARM-007, autels AUDIT-002). *Compter les unités de l'intervention
avant de comparer.*

Converge [[EDR-DREAM-005]], [[EDR-DREAM-004]], [[from-genome-flattens-architecture]],
REF-EXPERIMENT-PREFLIGHT.
