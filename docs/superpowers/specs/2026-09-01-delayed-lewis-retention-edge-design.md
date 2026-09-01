# La coordination référentielle DIFFÉRÉE exige-t-elle la rétention d'état ?

**Date** : 2026-09-01
**Statut** : design validé, prêt pour plan d'implémentation
**Vision parente** : AGI-Taxonomy — 3ᵉ arête du graphe de prérequis, et **première ablation de SUBSTRAT**.
Cf. [[EDR-LANG-PERCEPTION]], [[EDR-MEM-PERCEPTION]], [[EDR-RETAIN-COMPOSE-LR]], la porte durcie ce jour
(commits `7806f36` / `366217d`) et la classe **E19** du registre.

---

## 1. Objectif et cadrage honnête

Mesurer, avec la méthodologie du graphe, si une tâche de **coordination référentielle différée** exige la
**rétention d'état** — et graver l'arête `language→memory` si les deux jambes de la porte passent.

**Ce que le record dira** (contrainte de rédaction, pas cosmétique) : « une tâche de coordination
référentielle **DIFFÉRÉE** exige la rétention d'état ; la **même tâche non différée** ne l'exige pas ».
Pas « le langage exige la mémoire ». Le nœud `language` est instancié pour de vrai — sender + receiver +
canal + asymétrie d'information — ce qui lève l'**équivocation de nœud** qui disqualifiait
`tools/language_memory_demand_probe.py` (mono-agent : aucun langage n'y était échangé). Mais le contenu
mesuré reste une propriété de la TÂCHE.

**Ce qui est acquis d'avance et n'est donc pas le résultat** : le bras principal est **arithmétiquement
forcé** — privé de l'information sur la cible, le receiver est au hasard, donc `X_DEMANDED` est garanti
dès qu'il est vivant. Les deux arêtes gravées ont exactement cette structure. **Tout le contenu empirique
vit dans les bras de CONTRÔLE**, et c'est d'eux que le design doit répondre.

## 2. Partie A (PRÉALABLE) — corriger `ablation_verdict`, unilatéral

`tools/demand_marker.py` déclenche `X_DECOY` (lu « ablation inerte » ⇒ `specificity_control='pass'`) pour
**tout** `ratio <= 1.3` — y compris `0.596`, c'est-à-dire une ablation qui **multiplie le contrôle par
1.68**. `_degeneracy` ne l'attrape pas : elle ne teste que « intact au plancher » et « les DEUX bras au
plafond », or ici l'intact est vivant et seul l'ABLÉ sature.

- **Correctif** : borner `X_DECOY` des DEUX côtés — `1/decoy_ceiling <= ratio <= decoy_ceiling`
  (≈ `0.77 <= ratio <= 1.3`) — ou émettre un verdict distinct `INCONCLUSIVE_INVERTED` sous `1/1.3`.
  Choisir l'option qui préserve la compatibilité des deux arêtes gravées (à VÉRIFIER, non supposé).
- **Contre-exemple gelé, déjà mesuré** : `ci=[0.510,0.658,0.592]`, `ca=[0.988,0.994,0.994]`, ratio
  **0.596**, aujourd'hui `X_DECOY`. Doit devenir non-`pass`.
- **Contrôle positif** : un vrai decoy (ratio ≈ 1.0) doit RESTER `X_DECOY` — sinon la garde refuse tout.
- **Non-régression obligatoire** : `check_agi_taxonomy` doit rester à 2 arêtes / 0 violation.
- Rattacher en **occurrence E3** au registre (garde écrite ET testée dans la même passe).

Pourquoi d'abord : c'est l'instrument PARTAGÉ des trois arêtes, et la mesure de la partie B peut réellement
le déclencher. Même logique que le durcissement de la porte : réparer avant d'ajouter.

## 3. Partie B — le protocole Lewis DIFFÉRÉ

Base : `tools/perception_coordination_demand_probe.py` (déjà calibrée générateur A — sender oracle
effondre, sender aléatoire inerte — et déjà chiffrée : n=12 en 237.5 s). Deux populations SÉPARÉES, jamais
de poids partagés ; le canal est un entier ré-encodé en one-hot côté receiver.

**Les deux bras principaux sont symétriques par la DATE de présentation de la cible au sender** — canal,
sender, longueur de séquence et nombre de forwards IDENTIQUES ; seule la date change :

- **RETAIN** (bras testé) : la cible est montrée au sender au **tick 1** ; un référent-leurre au tick de
  choix. Le receiver doit RETENIR à travers D ticks.
- **PRESENT** (contrôle de DEMANDE) : un référent-leurre au tick 1 ; la **cible** au tick de choix. Le
  receiver peut résoudre SANS retenir.

Le **référent-leurre** est tiré **uniformément sur `[0,K)` et indépendamment de la cible** (jamais
« différent de la cible » : la contrainte biaiserait le plancher). C'est la leçon MEM-PERCEPTION —
dans un contrôle de spécificité sur tâche récurrente, le canal ablaté doit être **décorrélé de la
réponse**, sinon un confond d'entraînement fabrique une fausse demande.

⚠️ Le bruit plafonnant (§3.3) porte sur le signal **effectivement porteur dans chaque bras**. Bruiter le
signal re-présenté tout en laissant le signal propre au tick 1 rendrait la rétention à nouveau PAYANTE
dans le contrôle — version dynamique du piège de MEM-PERCEPTION itération 1.

Les slots d'entrée sont écrasés à chaque tick (`backend_torch.py:123`) : les ticks de délai côté receiver
sont donc des vecteurs nuls, et un signal maintenu au tick de choix tuerait la demande.

### 3.1 L'ablation : SUBSTITUTION D'ÉTAT DÉCORRÉLÉE (non négociable)

**Le H-reset à zéro est FAUX et doit être explicitement écarté.** Sur ce substrat
`logit_j = (1−δ_j)·H_prev_j + δ_j·tanh(...)` avec δ médian **0.500**, et **108 des 113 nœuds portés SONT
les readouts** : remettre H à zéro ne coupe pas un canal, ça supprime **la moitié de la sortie**. Mesuré
sur le contrôle : intact `[0.510, 0.658, 0.592]` → H-reset `[0.988, 0.994, 0.994]` — l'ablation
**AMÉLIORE de +0.40, 3/3 seeds**. Et sous H-reset le contrôle rend `pass` sur un design **délibérément
cassé** aussi bien que sur un design correct : il ne mesure plus rien.

**Écarter aussi le repli « n'effacer que les nœuds non-readout »** : seuls **5 nœuds** (59..63) ne sont ni
entrée ni readout ; mesuré INERTE sur RETAIN (3/3) ⇒ `VACUOUS_ABLATION`.

**L'ablation retenue** : rejouer le préfixe (émission + délai) avec un **référent DÉRANGÉ**, sur le même
agent et les mêmes poids, puis présenter le tick de choix. La distribution marginale de H, sa norme et ses
corrélations internes sont préservées ; seule l'information sur la cible de CE trial est détruite. C'est
l'analogue-état exact de `derange_rows`, l'ablation des deux arêtes déjà gravées.

Mesuré (3 seeds, 600 ép.) : RETAIN `0.633/0.654/0.621` → `0.194/0.175/0.177` (**ratio 3.58**,
`X_DEMANDED`) ; PRESENT Δ `0.012/0.002/0.002` (**SURGICAL**) ; et le design cassé rend **ratio 1.856 →
`fail`** ⇒ **le contrôle DISCRIMINE**.

⚠️ La substitution uniforme laisse une coïncidence de `1/K` avec la vraie cible : tirer le référent de
substitution **uniformément**, jamais « différent de la cible » (le second biaiserait le plancher).

### 3.2 Trois bras de contrôle, pas deux

`leakage <= tol` **subsume strictement** `ratio <= 1.3` : lire un seul bras comme `specificity_control` ET
comme bras d'aliasing ferait reposer les deux verrous de la porte sur une seule mesure — exactement la
configuration « deux gardes dont aucune ne peut échouer » fermée ce matin. Donc :

| bras | rôle | attendu |
|---|---|---|
| **RETAIN** | bras testé | `X_DEMANDED` (forcé — ce n'est pas le résultat) |
| **PRESENT** | `specificity_control` | vivant ET inerte → `X_DECOY` non dégénéré |
| **ALIAS** | `functional_aliasing` | capacité INDÉPENDANTE, vivante, inerte → `SURGICAL` |

**ALIAS** = une discrimination perceptive immédiate **bruitée**, sur **slots d'entrée dédiés**. Son plafond
doit venir de **BAYES** (propriété de la tâche), jamais d'un sous-entraînement — sinon la garde de
non-saturation dépend du réglage et **E19 mord sur la garde elle-même**. L'entraîner sur le **MÊME contexte
porté** que le bras principal (piège déjà corrigé dans `language_memory_demand_probe.py:267-273`) : sinon
l'éval intacte est hors-distribution et le signe de la fuite peut s'inverser.

⚠️ **Point ouvert que le plan doit résoudre en premier, avec mesure** : le substrat n'a qu'une **tête
d'action unique** (`_MOVE_LOGITS=8`), et LANG-MEMORY a déjà buté dessus — « 2 capacités entraînées dans un
même forward impossible → forwards séparés à H partagé ». Deux capacités doivent donc être lues sur des
tranches de logits qui ne se recouvrent pas, ou par forwards séparés partageant H. Le plan doit **vérifier
mécaniquement** la solution retenue (les deux bras s'entraînent-ils sans s'écraser ?) avant d'engager le
run-verdict — c'est un candidat au crible fail-fast T1.

### 3.3 Plafonnement structurel des contrôles (parade E19)

Mesuré : `lr=0.05` garde le contrôle vivant mais RETAIN à 0.62-0.65 ; `lr=0.02` monte RETAIN à
`[0.873, 0.946]` mais **sature le contrôle à 1.000** (2/2 seeds) ⇒ `specificity_control='fail'` +
`DEGENERATE_CONTROL`. **Le réglage qui optimise le bras testé tue le contrôle** — le « conflit à deux
jambes » qui a bloqué LANG-MEMORY.

Parade, comme les deux arêtes gravées : bruiter le signal porteur avec `flip_p=0.3` ⇒ plafond
`(1−flip_p)+flip_p/K = 0.75`, **sous la barre de vitalité quel que soit le `lr`**.

## 4. Verdict, gravure, et l'issue négative

L'arête n'est gravée que si les DEUX jambes passent, sous la porte durcie :
`ablation_verdict == X_DEMANDED` · `n >= 12` · `specificity_control == 'pass'` (exigé en toute
circonstance) · `ablation_target = 'substrate'` ⇒ `functional_aliasing == 'pass'` **mesuré** (jamais
`'n/a'`) · record existant.

Rapporter en plus, au standard des deux arêtes existantes : **séparation par seed** (elles tiennent
12/12 sans chevauchement — la troisième ne doit pas passer sous un standard plus faible), `leak_seeds`, et
la grille de `lr` COMPLÈTE.

**Issue négative explicitement prévue** : le H-reset améliore les tâches feedforward évaluées sur contexte
porté (0.541 → 0.794 mesuré) ; la garde étant bilatérale, le bras ALIAS peut échouer **par le haut** à
faible budget. La fermeture du leakage avec le budget est CONSTATÉE (0.29 → 0.03-0.10 entre 200 et 700
épisodes) mais **PAS acquise**. Si elle ne se referme pas sous `tol=0.05`, **l'arête n'est pas gravable et
on écrit le NÉGATIF** — c'est une issue légitime du round, pas un échec à contourner.

## 5. Calibration (générateur A + un générateur NÉGATIF)

- **Positif** (hérité, à préserver) : sender oracle → effondrement ; sender aléatoire → inerte.
- **NÉGATIF, nouveau et central** : geler le **design REDUNDANT** (préfixe portant la réponse — l'erreur
  exacte de MEM-PERCEPTION itération 1) comme contre-exemple : la sonde DOIT rendre
  `specificity_control='fail'`, valeur mesurée **ratio ≈ 1.856**. C'est ce qui prouve que le contrôle PEUT
  échouer — sans lui, l'arête se graverait sur un contrôle qui valide n'importe quoi.
- **Ablation vacuous** : le reset non-readout doit rendre `VACUOUS_ABLATION` (chiffre : 5 nœuds).
- Partie A : contre-exemple `ratio 0.596` + contrôle positif `ratio ≈ 1.0`.

## 6. Bornage, E19, pré-vol

- **Coût mesuré** : ~22 s par cellule (seed × bras) ; le `_step` de délai est gratuit — **le coût suit le
  NOMBRE DE BRAS, pas D**. 3 bras × 12 seeds = 36 cellules ≈ **13.2 min par point de `lr`**.
- **Ordre fail-fast** : (T1) crible 3 seeds — RETAIN apprend-il ET PRESENT est-il vivant+inerte SOUS
  plafonnement ? (T2) balayage `lr` ≥ 3 points sur seeds **disjoints**, critère de sélection **scellé
  avant le run** et défini **UNIQUEMENT sur RETAIN intact** — jamais sur un contrôle, jamais sur un bras
  ablé. (T3) run-verdict n=12 **FOREGROUND**, `torch.set_num_threads(1)`.
- Si le run-verdict dépasse ~10 min : réduire `n_agents` 16→8 (gain 1.7×, échantillon INTRA-seed) —
  **jamais** `n` (unité de réplication), **jamais** les épisodes (un sous-entraînement fabrique le nul),
  **jamais** un plafond en secondes (E13).
- **Pré-inscription obligatoire** : nommer les grandeurs que le record devra citer (`RETAIN_intact`,
  `PRESENT_intact`, `ALIAS_intact`, `ablation_verdict`, `specificity_control`, `functional_aliasing`,
  `ablation_target`, la grille de `lr`), sinon `check_preregistration_applied` échoue.
- Pur torch CPU, **aucun bail `kuzu`**, aucun monde. Provenance : le verdict sort de la fonction CALIBRÉE.

## 7. Fichiers

- `tools/demand_marker.py` (MODIF, partie A) — bornage bilatéral de `X_DECOY`.
- `tools/delayed_coordination_demand_probe.py` (NOUVEAU) — la sonde 3 bras.
- `tests/sandbox/test_instrument_calibration.py` (MODIF) — contre-exemples gelés + `CALIBRATED` par branches.
- `results/delayed_lewis_edge.json` (NOUVEAU) — accuracies par seed + `_params` + grille `lr`.
- `docs/preregistrations/DELAYED-COORD-001.json` (NOUVEAU) — règle scellée.
- `docs/EDR/EDR-DELAYED-COORD_Deferred_Referential_Coordination_Demands_Retention.md` (NOUVEAU) — le record.
- `data/agi_taxonomy/demands.json` (MODIF) — **seulement si les deux jambes passent**.

## 8. Critères de succès

1. Partie A : `X_DECOY` borné des deux côtés, contre-exemple 0.596 refusé, vrai decoy préservé, 2 arêtes
   intactes, occurrence E3 inscrite.
2. Sonde 3 bras calibrée, dont le générateur NÉGATIF (design REDUNDANT → `fail`).
3. Run n=12 FOREGROUND : les 3 bras mesurés, `lr` balayé, critère scellé respecté, séparation par seed.
4. Arête gravée SI et SEULEMENT SI les deux jambes passent ; sinon **record négatif honnête**.

## 9. Hors scope

- Re-mesurer `(q+key)%K` (équivocation de nœud — abandonné, cf. §1).
- Émergence in-world / évolutive de la coordination différée.
- Généraliser le résultat à `language` au sens large : le record parle de la TÂCHE.

## 10. Risques

- **Le contrôle ALIAS ne referme pas son leakage** → arête non gravable → négatif (prévu, §4).
- **Aucun `lr` ne tient les deux jambes** malgré le plafonnement → re-concevoir le plafond, ne pas
  choisir le `lr` sur le bras testé (E19).
- **La substitution décorrélée laisse une fuite résiduelle** → mesurer, ne pas supposer.
- **Sur-lecture du résultat** : `X_DEMANDED` sur RETAIN est forcé ; seul l'échec possible des contrôles
  porte l'information. Le record doit le dire explicitement.
