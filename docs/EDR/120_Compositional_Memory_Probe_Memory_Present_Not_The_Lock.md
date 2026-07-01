---
id: EDR-120
type: EDR
title: Sonde mémoire compositionnelle — la MÉMOIRE n'est PAS le verrou (MEMORY_PRESENT ; did_x décodable de H_S2 AUC~0.90, contrôle permutation = 0.5)
status: validated
gate: null
verdict: MEMORY_PRESENT. did_x (action X de S1) est décodable linéairement de l'état récurrent H_S2 qui produit move2 (AUC ~0.90 legacy ET torch), contrôle par permutation = 0.5 (décodeur honnête). La récurrence PORTE la précondition jusqu'à S2 → la mémoire n'est PAS le verrou compositionnel → le verrou est EN AVAL (crédit / découverte). Prochain chantier = curriculum.
---

# EDR 120 : Sonde mémoire — la mémoire n'est pas le verrou (MEMORY_PRESENT)

## Contexte

EDR 119 a tranché Issue C : grossir les cachés ×16 ne lève pas la composition means→ends ; le verrou
est le **mécanisme** (crédit / mémoire), pas la taille. Ce chantier attaque la PREMIÈRE des trois
hypothèses emboîtées : **`did_x` (l'action X émise en S1) est-il seulement *présent* dans l'état
récurrent `H_S2` qui produit `move2` ?** Si l'info n'est pas portée, le verrou est la **mémoire** et
le curriculum (crédit/découverte) serait futile. Prérequis logique avant toute intervention.

## Méthode

- **Script** : `tools/substrate_ab_compositional.py::memory_probe` (commits `d0d215b` + contrôle
  permutation `d3f3593`).
- **Sonde PURE, sans apprentissage** (capacité intrinsèque à l'init, W aléatoire ; aucun `pop.learn`).
  Par trial : lire l'état AVANT S1 (`H_pre`), `forward(obs_a_t)` → `move1`/`did_x = move1==target_x`,
  `forward(obs_b)` → lire `H_S2`. **`obs_a` VARIÉ par trial** (fait varier `did_x` indépendamment de
  l'identité) ; **`obs_b` FIXE** (comme la tâche : S2 n'encode pas `did_x`, seule la récurrence peut
  le porter).
- **Décodage PER-AGENT** (fidèle au readout per-agent : chaque agent a son W) : régression logistique
  `sklearn` + `StandardScaler`, split stratifié 70/30, **ROC-AUC sur held-out** (robuste au
  déséquilibre `did_x` ~1/8). Décodage sur la tranche non-input `H[:, I:]` (cachés+sortie). Agent
  inclus seulement si les 2 classes ont ≥ 8 échantillons ; `n_qualifying` reporté.
- A/B `legacy` vs `torch`, 3 seeds, `n_agents=16`, `trials=300`. EXIT CODE = 0.

## Contrôles (anti-théâtre) — le contrôle par PERMUTATION est le héros

Deux contrôles décodent depuis le MÊME régime (mêmes dimensions/échantillons) pour distinguer signal
réel d'artefact :

1. **Contrôle `H_pre`** (prévu au plan) : décoder `did_x` de l'état AVANT d'avoir vu `obs_a_t`.
   **Il N'EST PAS sorti à 0.5** (legacy ~0.58, **torch ~0.74**). Diagnostic honnête : `H_pre` est en
   **amont CAUSAL** de `did_x` — la récurrence biaise l'action S1 suivante (la LTC continue de torch
   très fortement) → `H_pre` prédit légitimement `did_x` sans le « contenir ». Le contrôle `H_pre`
   conflait « contient l'issue » avec « prédit l'issue » → insuffisant seul.
2. **Contrôle par PERMUTATION** (ajouté après investigation, commit `d3f3593`) : décoder un `did_x`
   MÉLANGÉ depuis `H_S2`. **AUC_shuffled MÉDIAN = 0.5** (legacy 0.474, torch 0.515 ; `control_valid =
   True`, tous ∈ [0.40, 0.60]). → le décodeur 113-dim sur ~26 échantillons/agent **NE gonfle PAS**
   l'AUC en médiane : les valeurs élevées (AUC_s2 ~0.90, AUC_pre ~0.58/0.77) sont du **signal génuin**.
   **Dispersion honnête du null** (queue à n faible) : la permutation par agent a un étalement large
   (legacy max 0.94, p95 0.64, 17 % d'agents > 0.6 ; torch max 0.82, p95 0.67, 22 % > 0.6) — attendu
   pour un vrai null à ~26 échantillons. **Mais la séparation tient quand même** : le MINIMUM per-agent
   d'`AUC_s2` (legacy 0.743, torch 0.716) **dépasse le p95 de la permutation** (0.64 / 0.67), et la
   médiane `AUC_s2` (~0.90) est très au-dessus du null. Le signal est donc séparé du bruit même en
   tenant compte de la dispersion, pas seulement en médiane. **Le verdict gate sur ce contrôle
   permutation, pas sur le delta `H_pre`** (confondu, cf. point 1).

> Leçon méthodo : le contrôle prévu (`H_pre`) a échoué à donner 0.5 ; au lieu de conclure à l'aveugle,
> l'investigation par permutation a tranché « signal réel vs artefact » ET réinterprété `H_pre` élevé
> comme l'effet amont-causal de la récurrence (qui RENFORCE « mémoire présente »).

## Résultats

Par cellule (backend × seed ; médianes per-agent) :

| backend | seed | n_qual | base_rate | **AUC_s2** | AUC_pre | delta (s2−pre) | **AUC_shuffled** |
|---------|------|--------|-----------|-----------|---------|----------------|------------------|
| legacy | 0 | 14 | 0.153 | **0.882** | 0.586 | +0.296 | 0.528 |
| legacy | 1 | 11 | 0.083 | **0.904** | 0.576 | +0.327 | 0.470 |
| legacy | 2 | 10 | 0.110 | **0.908** | 0.582 | +0.327 | 0.474 |
| torch  | 0 | 12 | 0.123 | **0.905** | 0.771 | +0.134 | 0.537 |
| torch  | 1 | 6  | 0.049 | **0.946** | 0.762 | +0.183 | 0.515 |
| torch  | 2 | 9  | 0.097 | **0.876** | 0.674 | +0.202 | 0.494 |

Agrégats : legacy AUC_s2 **0.904** (shuffled 0.474) ; torch AUC_s2 **0.905** (shuffled 0.515).

- **`did_x` est décodable de `H_S2` à AUC ~0.90 sur les DEUX substrats**, contre un plancher de
  permutation à 0.5 → signal massif et génuin.
- **delta (s2 − pre) positif partout** (legacy +0.30, torch +0.13–0.20) — COHÉRENT avec un apport de S1
  au-dessus de la base récurrente, mais n'isole PAS causalement cet apport : `H_pre` étant déjà
  prédictif (récurrence amont), le delta confond « S1 ajoute du signal » et « la trajectoire récurrente
  dérive davantage vers une région prédictive de `did_x` ». Diagnostic secondaire, pas le fondement du
  verdict (qui repose sur AUC_s2 vs permutation).
- `H_pre` lui-même porte déjà `did_x` (récurrence causale), torch (0.77) > legacy (0.58) — la LTC
  continue de torch propage l'information plus fortement.

## Verdict : MEMORY_PRESENT — la mémoire n'est pas le verrou

La récurrence PORTE `did_x` jusqu'à l'état qui produit `move2` (AUC_s2 ~0.90, contrôle permutation 0.5).
**L'information est DISPONIBLE pour un readout linéaire** — un poids de sortie *pourrait* conditionner
`move2` sur `did_x`. Donc le substrat n'échoue PAS la composition par défaut de mémoire. Le verrou est
**EN AVAL** :

- **Crédit (H2)** : la règle (hebbien legacy / autograd TD(0) torch) n'arrive pas à APPRENDRE à utiliser
  le signal `did_x` pourtant présent — assigner le crédit de la récompense S2 vers l'action S1.
- **Découverte (H3)** : la récompense jointe trop rare (~+1 seulement si X *et* Y, quasi jamais par
  hasard) ne donne jamais de signal d'amorçage.

→ Prochain chantier = **curriculum progressif** (récompenser `did_x` seul en S1, dense, puis basculer
Y|X) pour trancher H2 (crédit) vs H3 (découverte).

| hypothèse | statut (EDR) |
|-----------|--------------|
| Taille / capacité réseau | RÉFUTÉE (119 : ×16 cachés sans effet) |
| **Mémoire (la récurrence porte-t-elle did_x ?)** | **RÉFUTÉE (120 : OUI, AUC_s2 ~0.90)** |
| Crédit (la règle exploite-t-elle le signal ?) | OUVERTE → curriculum |
| Découverte (la récompense amorce-t-elle ?) | OUVERTE → curriculum |

## Caveats

1. **Capacité à l'init, pas apprentissage** : la sonde mesure que l'information est PHYSIQUEMENT
   présente dans l'état (condition nécessaire), pas que la règle sait l'exploiter — c'est précisément
   ce que le curriculum testera. « Disponible pour un readout » ≠ « la règle a appris le readout ».
2. **`H_pre` ≠ 0.5** : le contrôle prévu est confondu par l'amont causal de la récurrence ; le verdict
   repose sur **AUC_s2 vs permutation (0.5)**, pas sur le delta `H_pre`. Le delta reste cohérent
   (positif) mais secondaire.
3. **Puissance** : 3 seeds ; `n_qualifying` faible par cellule (6–14 agents ; torch seed=1 = 6 seulement,
   base_rate 0.049) → AUC per-agent bruitées sur petits test-sets déséquilibrés. La permutation à 0.5
   et la convergence AUC_s2 ~0.90 sur 6 cellules rendent le signal robuste malgré le bruit per-cellule.
4. **Micro-tâche proxy** : tâche X-gate-Y, PAS une preuve de transfert apex en prod (même bornage
   qu'EDR 115/117/119).
5. **`target_x=0` sur 8 moves** → base_rate ~1/8 déséquilibré ; AUC (sans seuil) choisi exprès pour
   cette raison.

## Conséquences

- La **migration moteur** ([[sota-gap-substrate]]) ne doit PAS se focaliser sur la capacité mémoire
  brute (la récurrence porte déjà l'info) ni sur la taille (EDR 119) — mais sur le **mécanisme de
  crédit/apprentissage compositionnel** (TD(λ)/éligibilité, curriculum, signal d'amorçage dense).
- Suite directe : **curriculum progressif** sur le banc (récompenser X seul puis Y|X) — si ça craque
  la composition → verrou = découverte (récompense rare), actionnable par shaping en prod ; si non →
  verrou = crédit (la règle ne sait pas binder même avec signal + mémoire), plus profond.
- Convergence 104-119-120 : capacité/sélection/diversité/répertoire/horizon/**taille**/**mémoire** tous
  écartés → le verrou de la composition/apex se resserre sur l'**assignation de crédit** elle-même.

## Liens

- `[[coop-competence-is-population-property]]` — apex = leviers réfutés ; mémoire réfutée ici
- `[[sota-gap-substrate]]` — migration moteur : cibler le crédit, pas la mémoire brute ni la taille
- `[[nas-bottleneck-is-substrate-not-search]]` — verrou substrat précisé : mécanisme de crédit
- EDR 119 — sweep taille (la taille n'est pas le verrou)
- EDR 117 — learnabilité compositionnelle (les deux substrats échouent)
- EDR 115 — barreau-0 : gradient bat hebbien sur mono-contingence
- Outils : `tools/substrate_ab_compositional.py` (`memory_probe`)
- Données : `results/sab_memory_probe.json` (per-agent complet + AUC_shuffled)
