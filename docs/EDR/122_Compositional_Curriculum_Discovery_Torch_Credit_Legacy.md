---
id: EDR-122
type: EDR
title: "Curriculum compositionnel — SPLIT par substrat : DISCOVERY (torch, ×10) / CREDIT (legacy, 0.000) ; le gradient+curriculum craque le means→ends que ni l'un ni l'autre ne craquait"
status: validated
gate: null
verdict: "SPLIT par backend. Enseigner X d'abord (warmup dense) lève la composition Y|X pour torch (hit_end 0.03→0.30, ×10, 5/5 seeds) = DISCOVERY (le verrou était la récompense jointe rare), mais PAS pour legacy (0.000 même avec X maîtrisé + mémoire) = CREDIT (le hebbien ne binde pas). → gradient + curriculum/shaping craque le means→ends ; le hebbien numpy est crédit-limité. Renforce la thèse de migration moteur."
---

# EDR 122 : Curriculum compositionnel — DISCOVERY (torch) / CREDIT (legacy)

## Contexte

Chaîne 119→120 : la TAILLE n'est pas le verrou (119, ×16 cachés sans effet), la MÉMOIRE non plus
(120, `did_x` décodable de `H_S2` AUC~0.90). Restaient deux hypothèses sur l'échec compositionnel
means→ends :
- **Crédit (H2)** : même avec X maîtrisé + mémoire, la règle ne sait pas binder `move2` sur `did_x`.
- **Découverte (H3)** : la règle *pourrait* binder, mais la récompense jointe trop rare (~+1 que si X
  *et* Y) n'amorce jamais.

Le curriculum sépare les deux : **enseigner X d'abord (dense), puis tester Y|X**.

## Méthode

- **Script** : `tools/substrate_ab_compositional.py::compare_curriculum` (commits `5744b34` + `d5a55b8`).
- **2 phases, bascule DURE** (par agent, même population) :
  - **Phase A (warmup, dense sur X)** : `forward(obs_a)` → `move1`/`did_x` → `learn(+1 si did_x sinon −1)`.
    S1 SEUL. Enseigne X sur `obs_a` fixe (mono-contingence, apprenable cf. EDR 115). `warmup=150`.
  - **Phase B (compositionnel PUR)** : `forward(obs_a)`→learn(0 différé), `forward(obs_b)`→learn(reward
    +1 SSI Y ET did_x). `obs_b` n'encode pas `did_x`. S1 reward 0 (rien ne renforce X directement).
    `compo=250`.
- `obs_a` partagé A↔B (le X appris se réutilise). A/B `legacy` vs `torch`, **5 seeds**, 8 agents.
- **Baseline** : `warmup=0` (≡ phase B seule) → doit reproduire le plancher EDR 117/119.

## Contrôle d'efficacité de la phase A (le héros)

Avant de lire le verdict : le warmup DOIT enseigner X, sinon le curriculum ne teste rien.
**`warmup_didx_end` monte nettement au-dessus du base-rate ~0.125** sur les deux substrats :
legacy médian **0.75**, torch médian **0.98** (par seed : legacy 0.63–1.00, torch 0.75–1.00).
→ **Les deux substrats APPRENNENT X en phase A** (cohérent EDR 115). Le curriculum a décollé ;
le verdict de phase B est interprétable.

## Résultats

Per-seed (warmup_didx_end → hit_end phase B ; rétention X `compo_didx` start→end) :

| seed | backend | warmup_didx_end | **hit_end** | compo_didx (start→end) |
|------|---------|-----------------|-------------|------------------------|
| 0 | legacy | 1.000 | **0.000** | 0.891 → 0.625 |
| 0 | torch  | 0.980 | **0.306** | 0.827 → 0.377 |
| 1 | legacy | 0.750 | **0.000** | 0.530 → 0.375 |
| 1 | torch  | 0.750 | **0.204** | 0.718 → 0.329 |
| 2 | legacy | 0.750 | **0.000** | 0.792 → 0.750 |
| 2 | torch  | 0.875 | **0.312** | 0.806 → 0.450 |
| 3 | legacy | 0.922 | **0.000** | 0.556 → 0.498 |
| 3 | torch  | 1.000 | **0.347** | 0.935 → 0.617 |
| 4 | legacy | 0.628 | **0.000** | 0.415 → 0.250 |
| 4 | torch  | 1.000 | **0.302** | 0.907 → 0.371 |
| **médiane** | **legacy** | **0.75** | **0.000** | — |
| **médiane** | **torch**  | **0.98** | **0.306** | — |

**Baseline `warmup=0` (cohérence, 3 seeds)** : torch hit_end ~**0.03** (0.010–0.048), legacy **0.000**,
X rate ~0.12 (aléatoire, pas d'apprentissage de X). → reproduit le plancher EDR 117/119. ✓

## Verdict : SPLIT par substrat

Le résultat est **asymétrique** et c'est l'information décisive (l'enum du code = DISCOVERY car ≥1 bras
décolle ; la lecture honnête est SPLIT) :

- **torch = DISCOVERY (H3)** : une fois X enseigné (warmup), l'autograd **craque Y|X** — hit_end passe
  de **0.03 (baseline) à 0.30 (curriculum), ×10, sur les 5/5 seeds**. Le verrou de torch était la
  **découverte** : la récompense jointe trop rare n'amorçait jamais ; le shaping dense de X l'amorce.
- **legacy = CREDIT (H2)** : warmup réussit (X maîtrisé, did_x 0.75) ET X partiellement retenu en B
  (compo_didx 0.25–0.75) ET mémoire présente (EDR 120), MAIS hit_end = **0.000 sur les 5 seeds**, avec
  ET sans curriculum → le hebbien/numpy **ne binde JAMAIS Y sur did_x**. Le verrou de legacy est le
  **mécanisme de crédit** lui-même.

### Nuance — le binding n'est PAS le limiteur dominant pour torch ; la rétention de X borne le plafond

X **décline** en phase B (S1 reward 0, rien ne le renforce : compo_didx ~0.9→0.4). Le joint `hit_end`
(0.30) reste proche de la rétention de X en fin de B (~0.38) : le ratio `hit_end / did_x_end` vaut
**~0.7** (⚠️ ATTENTION : c'est un ratio de DEUX médianes agrégées séparément ; la médiane des ratios
PER-SEED est 0.70, plage 0.56–0.82 — pas une mesure per-trial de `P(Y|X)`, et did_x DÉCLINE dans la
fenêtre donc le conditionnel n'est pas propre). **Bornage honnête** : l'instrument n'enregistre que le
JOINT `mean((move2==Y) ET did_x)`, JAMAIS `move2==Y` inconditionnel → on ne MESURE pas `P(Y|X)`, on
l'infère. Ce qu'on peut dire SANS sur-lire : le joint de torch (0.30) n'est pas étranglé loin sous le
plafond de rétention de X (~0.38) → **le binding Y|X n'est PAS le limiteur résiduel dominant** (le
plafond est largement la décroissance de X). Un shaping qui maintient X (fade, ou bonus did_x résiduel)
testerait si torch monte au-delà — voie plausible, pas prouvée. legacy, lui, retient X autant
(compo_didx 0.25–0.75) mais le joint reste 0.000 → pour legacy le limiteur N'EST PAS la rétention,
c'est le binding lui-même.

| régime | legacy hit_end | torch hit_end | lecture |
|--------|----------------|---------------|---------|
| compo nu (117/119) | ~0 | ~0.05 | les deux au plancher |
| curriculum baseline (warmup=0) | 0.000 | ~0.03 | plancher reproduit (cohérence) |
| **curriculum (warmup=150)** | **0.000** | **0.306** | **torch DISCOVERY ×10 ; legacy CREDIT** |

## Caveats

1. **Verdict-enum vs lecture humaine** : `verdict_curriculum=DISCOVERY` (déclenché par le bras torch) ;
   la lecture scientifique honnête est **SPLIT** (DISCOVERY torch / CREDIT legacy). Les seuils (0.30/0.15)
   sont heuristiques ; le verdict final est lu sur les chiffres bruts.
2. **Bascule dure → X décline** en phase B : le crédit différé ne MAINTIENT pas le means même chez torch
   (compo_didx ~0.9→0.4). Borne le plafond ; un curriculum à fade le testerait (hors-scope, choisi).
3. **Puissance** : n=5 seeds. Le test de signe apparié torch>legacy donne **sign_p=0.0625** (5/5 =
   1/16, JUSTE au-dessus de 0.05 — plancher de puissance à n=5, pas significatif au seuil conventionnel).
   La robustesse repose sur la **consistance directionnelle 5/5** (torch décolle à ~0.30 SUR TOUS les
   seeds ; legacy à 0.000 SUR TOUS) + la **taille d'effet ×10**, plus convaincantes que le p-value pour
   ce design apparié intra-seed — mais le p-value est nommé, pas glissé.
4. **Micro-tâche proxy** : X-gate-Y, PAS une preuve de transfert apex en prod (bornage 115/117/119/120).
5. **0.30 n'est pas « résolu »** : la composition est PARTIELLEMENT cracké (torch), pas saturée ;
   c'est une porte de décision, pas une preuve de maîtrise.

## Conséquences

- **Thèse de migration moteur RENFORCÉE** : le means→ends compositionnel que NI substrat ne craquait
  seul (117/119) est cracké par **gradient + curriculum** (torch), PAS par **hebbien + curriculum**
  (legacy). → la voie vers l'apex = **substrat torch (autograd) EN PROD + shaping/curriculum du craft**.
- **Le hebbien numpy est crédit-limité** : aucun curriculum ne le sauve (0.000) → confirme l'audit
  [[sota-gap-substrate]] (la règle d'apprentissage, pas la taille ni la mémoire, est le mur).
- Chaîne 104-122 close sur le diagnostic : **le dernier verrou identifié (assignation de crédit
  compositionnel) est LEVÉ par gradient+curriculum pour torch, et IRRÉDUCTIBLE pour le hebbien**.
- Suite : (a) **curriculum à fade** (maintenir X) pour pousser torch au-delà de 0.30 ; (b) le gros
  chantier **torch-en-prod** (contrat forward complet) pour re-tester l'apex réel sur substrat gradient
  avec shaping du craft — coordonner avec la session // (backend barreau-0 + banc horizon-crédit).

## Liens

- `[[coop-competence-is-population-property]]` — chaîne des leviers ; crédit LEVÉ pour torch ici
- `[[sota-gap-substrate]]` — migration moteur : gradient+curriculum craque, hebbien non
- `[[nas-bottleneck-is-substrate-not-search]]` — verrou = règle d'apprentissage (crédit), confirmé
- EDR 120 — mémoire présente (le binding avait l'info, torch sait maintenant l'exploiter)
- EDR 119 — taille pas le verrou ; EDR 117 — les deux échouent nu ; EDR 115 — gradient bat hebbien (mono)
- Outils : `tools/substrate_ab_compositional.py` (`run_curriculum`/`compare_curriculum`)
- Données : `results/sab_curriculum.json`
