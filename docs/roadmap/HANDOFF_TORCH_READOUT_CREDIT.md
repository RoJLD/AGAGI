# Handoff torch — le verrou est le READOUT / CRÉDIT, pas l'encodeur

> Artefact de coordination (élabore les gaps « à coordonner » C1-C3 du backlog cartographe).
> Destiné à la session qui possède le substrat torch/prod. Aucune décision imposée : une cible
> argumentée + des critères mesurables. Daté 2026-07-02, dérivé des EDR listés.

## Thèse unifiée : trois arcs indépendants convergent

Le substrat numpy (`MambaAgent`, ~5-172 nœuds) **encode adéquatement** ; le mur est le **mécanisme
qui mappe les représentations aux bonnes actions** (readout) et **qui leur assigne le crédit**
(optimisation par-tête / épisodique). L'encodeur récurrent est disculpé **trois fois, indépendamment** :

| Arc | EDR | Ce qui est disculpé | Ce qui est désigné |
|---|---|---|---|
| **Navigation** | EDR-NAV-001 | encodeur (H décode la direction à ~0.81, ≈ plafond obs 0.96) | **tête d'action** (émise==correct 2-3% ; le readout linéaire évolué ignore un signal linéairement présent) |
| **Têtes disjointes** | EDR 152/153/154/191 | architecture #5 (interférence réfutée, cos-conflit≈0) | **crédit** : GradNorm-lite / lr-par-tête dans le PLAT recouvre le gain (153 : +0.79 ; « crédit pas archi » robuste à l'interférence induite, 191) |
| **Binding (means→ends)** | EDR 148/158/159 | signal (128) / readout gate seul / init | **crédit ÉPISODIQUE** : gate + anti-sat portent le binding SOUS crédit épisodique (+0.298), échouent sous TD (+0.000) |

**Conclusion** : la migration torch doit prioriser (1) un **readout d'action différentiable entraîné
par gradient** et (2) une **assignation de crédit correcte** (lr/GradNorm par-tête + crédit épisodique).
**Ne PAS** commencer par refondre l'encodeur ni l'architecture (déjà disculpés). Cf.
[[sota-gap-substrate]], [[nas-bottleneck-is-substrate-not-search]], [[from-genome-flattens-architecture]].

## Cibles concrètes (critère mesurable + banc existant)

### T1 — NAV : entraîner la tête d'action par gradient  *(prio 1, la plus nette)*
- **Preuve** : EDR-NAV-001. H contient la direction-cible (décodable ~0.81) mais la politique émet le
  bon pas 2-3% du temps (et un *move* seulement 25-30%).
- **Action torch** : readout différentiable H→action, entraîné (gradient/REINFORCE) sur le signal de
  navigation déjà présent. Pas de refonte de l'encodeur récurrent.
- **Critère de succès mesurable** : relancer `tools/nav_localization_probe.py` sur la politique torch →
  `émise==correct` doit monter de ~0.03 vers l'accord de décodage (~0.8) ; `p_reach` (via
  `lewis_survival_sweep._measure_forage`, cohorte fixe) de ~0.52 vers ~0.875 (borne oracle EDR 114).
- **Banc prêt** : `nav_localization_probe` (probe) + `lewis_survival_sweep` (p_reach de-confondu 114b).

### T2 — Crédit multi-tête : GradNorm-lite / lr-par-tête dans le PLAT
- **Preuve** : EDR 153 (le plat + GradNorm-lite recouvre le gain disjoint) / 154 (moments par-tête ≈
  échelle de loss, résidu ~21 %) / 191 (crédit plat DÉPASSE disjoint même sous interférence induite).
- **Angle encore libre** (caveat EDR 154) : le proxy **lr-par-tête** n'a PAS été testé isolément
  (seuls moments-Adam et échelle-de-loss l'ont été). C'est le dernier levier proxy non-torch ouvert.
- **Action torch** : lr/GradNorm par-tête dans le connectome plat prod — **PAS** la refonte archi #5
  (réfutée comme levier, EDR 153).
- **Critère** : recouvrement ≥ celui de l'échelle-de-loss (0.79, EDR 153) sur `tools/disjoint_heads_*.py`.

### T3 — BIND : activer la recette gate + crédit épisodique en prod (flag OFF)
- **Preuve** : EDR 158 (`TorchPopulationModel.learn_episode` : crédit épisodique + gate + anti-sat
  PORTE le binding, +0.298, ADDITIF) / 159 (gate auto-scopé depuis H, task-agnostique, +0.232).
- **Action torch** : activer `learn_episode` (flag OFF par défaut) dans la boucle biosphère, valider
  hors banc jouet (le binding tient-il in-world ?).
- **Critère** : `P(Y|X) − P(Y|¬X)` > 0 in-world (instrument de binding, EDR 126/128) sans dégrader hit_end.

### T4 — (subordonné) BPTT fenêtré in-world
- **Preuve** : EDR 145 (BPTT numpy impossible) / 146 (BPTT SEUL ne craque pas le binding). Le BPTT
  DÉGRADE le gate (means→ends, `GATE_BINDS_BPTT_DEGRADES`). **Ne pas prioriser** : la recette binding
  vit SANS BPTT (crédit épisodique suffit, T3). BPTT fenêtré = exploration mémoire séparée, pas le levier binding.

## Séquence priorisée

1. **T1 (NAV readout)** — cible la plus nette, critère binaire, banc prêt, faible surface. Commencer ici.
2. **T3 (BIND en prod)** — recette déjà livrée (158/159), reste l'intégration boucle + validation in-world.
3. **T2 (lr-par-tête)** — proxy non-torch encore ouvert ; petit, ferme un caveat.
4. **T4 (BPTT)** — seulement si une demande mémoire explicite émerge ; PAS pour le binding.

## Coordination

- **Discipline flag-OFF** : chaque capacité s'active derrière un flag défaut OFF (parité prod préservée,
  cf. EDR 140/141 parité torch≈legacy, 158 ADDITIF). `git diff` prod non-régressif hors flag.
- **Ownership** : ces cibles touchent `src/agents/backend_torch.py` + boucle biosphère = territoire de la
  session torch. Ce doc est un *handoff*, pas une implémentation. Les bancs (`nav_localization_probe`,
  `disjoint_heads_*`, `substrate_ab_compositional`) restent côté tooling (sessions //).
- **Pont inter-murs** (hypothèse à tester, EDR-NAV-001) : navigation ↔ énergie (soin −10 compulsif
  EDR 094) = possiblement le MÊME readout émettant des actions chères non-navigantes. Si T1 corrige la
  navigation, re-mesurer la survie Lewis : un readout réparé pourrait lever les DEUX murs d'un coup.

Lignée : cartographe (backlog C1-C3) + EDR-NAV-001 / 152-191 / 148-159 → ce handoff unifié.
