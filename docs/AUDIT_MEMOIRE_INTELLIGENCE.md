# Audit — Mémoire & Typologie d'intelligence (2026-06-30)

> Audit *grounded* (lecture du code, pas de la roadmap) de deux questions : (1) comment la mémoire
> émerge / est-elle gérée / sait-on l'améliorer ; (2) gère-t-on et distingue-t-on les types
> d'intelligence dans le modèle. **Constat transverse** : les deux butent sur le même verrou que l'arc
> Lewis — le SUBSTRAT (connectome plat ~5 cachés, fitness scalaire). Issue cohérente = migration moteur
> (substrat différentiable + plasticité, cf. `roadmap/NAS.md` + memoire `sota-gap-substrate`).

## Partie A — Mémoire

**Elle n'émerge pas au sens fort : elle est surtout câblée/génétique.** 5 couches, 5 échelles de temps :

| Couche | Mécanisme | Statut |
|---|---|---|
| Travail (intra-tick) | état récurrent `H_prev` (LTC/Mamba), MAJ chaque tick (`mamba_agent.py`) | **ACTIVE** — vraie mémoire de travail |
| Explicite (NTM) | `NTM_Memory` 10×5, R/W par adressage cosinus (`mamba_agent.py:691`) | **ACTIVE** chaque tick |
| Long terme (KuzuDB) | `AsyncMemoryRetriever` (`graph_rag/memory_retriever.py:8`) | **PARTIELLE, plate** |
| Génétique | connectome `W` (génome = poids), plastique intra-vie (Actor-Critic) + inter-gén | **ACTIVE, lamarckien** |
| Gène `memory_cache` | déclaré, jamais muté, remis `None` au clonage (`mutation.py:27/52`) | **MORT** |

**Constats durs :**
1. **La « mémoire épisodique » n'en est pas une.** Requête KuzuDB = `MATCH (t:AgentThought) ORDER BY t.value_pred DESC LIMIT 500` → top-500 MONDIAL toutes vies, **distillé en 5 scalaires** injectés dans l'obs (slots 51-55). Pas d'ordre temporel, pas de trace par agent, pas d'embedding. C'est « ce qui a le mieux marché pour tous », pas « mon vécu ».
2. **Gestion partiellement cassée (2 points)** : (a) non-repro ambiante — fix `stop(); clear()` présent dans `main_curriculum.py:66` mais `robust_hof.py:40` appelle `stop()` SANS `clear()` → fuite de cache entre évals back-to-back (cf. memoire `biosphere-ambient-memory-nonrepro`) ; (b) canal lamarckien (gradient intra-vie → `genome.W`) a propagé des NaN sur longs épisodes (EDR 086, corrigé clip ±30).
3. **On sait l'améliorer, et c'est mesuré.** EDR 067 : le **BPTT** porte la mémoire 0.78 → **1.00** (rappel K-bits) là où la mutation sature ; existe dans `tools/grad_mem.py` mais **hors boucle vivante**. EDR 062/058 : les tâches actuelles (forage réactif) **n'exigent pas de mémoire** → l'archi ne grandit pas, la mémoire ne paie pas.

**Machinerie morte** : gène `memory_cache` ; `H_history`/`H_potentials` (initialisés/sérialisés mais non mis à jour dans le batch forward, vivants seulement dans le `recurrent_forward` legacy).

## Partie B — Typologie d'intelligence

**Non, pas dans le modèle.** L'agent est **un connectome plat** : `W` 172×172, **5 nœuds cachés** entre 59 entrées / 108 sorties (`mamba_agent.py:21`). Les « têtes » (mouvement, critique=logit 28, token langage, dream-trigger, têtes NTM, masque d'attention) sont des **tranches positionnelles de la même couche de sortie** — pas de modules séparés, pas d'isolation de gradient, pas de circuit dédié.

**Facultés (statut réel) :**
- **World model / surprise** (RND, `world_model.py`) — ACTIVE, mais bonus intra-vie, **pas le signal de fitness** (sélection = `life_score`, scalaire).
- **Critique RL** (logit 28, Actor-Critic TD) — ACTIVE.
- **Tête langage** (`referential_head.py`) — **SEUL vrai module séparé** (ajouté car le connectome plat échouait à produire un langage fiable, EDR 073). Gated off, bénéfice nul (G3).
- **Dreaming / planner** — PARTIELS (`PLAN_BIAS=0`, organe MCTS off par défaut).
- **Theory of Mind** — **MORTE** (un commentaire dans un chemin déprécié, zéro implémentation).

**Taxonomie (surtout docs) :**
- **Portes G0-G4** (`roadmap/FIL_DIRECTEUR_AGI.md`) : G0 PASSÉE ; G1 transfert (outil OK, pas de pass), G2 composition (« à créer », non instrumentée), G3 langage (résultat = pas de bénéfice), G4 anticipation (planner off) — partielles/non prouvées.
- **Échelle de mondes** : worlds 0/1 réels et benchmarkés ; **world 3 industriel = 18 lignes** (compteur de pollution), world 2 agricole = Biosphere + spawn saisonnier, **sans KPI cognitif propre** → « chaque monde exige un type d'intelligence » est ASPIRATIONNEL pour 2 et 3.
- Seule taxonomie comportementale dans le code = archive MAP-Elites 4 tiers `{survit, forage, craft, chasse apex}` (`map_elites.py`), intégration boucle principale non confirmée.

**Bilan** : un seul modèle indifférencié, une seule fitness scalaire, aucune dissociation des facultés. On ne distingue pas les intelligences — on les écrase sur l'âge de survie.

---

## Backlog priorisé (ce qu'on doit faire / expérimenter)

Tri par (valeur × levier) / coût, en respectant la coordination avec la session // moteur torch.
Légende coordination : **[I]** = instrument-side, zéro collision ; **[M]** = à poser dans le moteur torch (coordonner).

### P0 — Quick win / hygiène (cheap, immédiat) **[I]**
1. **Fix `clear()` manquant** dans `robust_hof.py:40` (`stop()` sans `clear()` → fuite de cache, non-repro entre évals back-to-back). Une ligne. Étend `biosphere-ambient-memory-nonrepro`.

> **NE PAS supprimer la « machinerie morte »** (`memory_cache`, `H_history`/`H_potentials`, `bytecode`).
> Décision 2026-06-30 : (a) `memory_cache` n'est pas mort mais **DORMANT** — lu par le moteur legacy
> `evolution.py::forward()` (op 4 Neurone-Sonde), même statut que `bytecode` qu'EDR 031 a gardé comme
> « câblage différé Vague 2 (RSI) » ; (b) ce sont des champs `Genome` → supprimer touche la
> sérialisation (champions/HoF KuzuDB), risque de régression pour gain nul ; (c) `mutation.py`/
> `evolution.py` sont édités par la session // moteur torch → collision ; (d) la migration moteur les
> retirera d'elle-même. **La valeur = les DOCUMENTER mort-en-prod (fait ici)**, pas les couper. Seul
> garde-fou utile contre la reconfusion (cf. bug keystone `from_genome`) = ce statut écrit.

### P1 — Leviers mesurés à fort ROI (falsifiables, préalables) **[I]**
3. **Banc « demande mémoire »** : tâche n-back / delayed-match-to-sample (nouveau monde/bench). EDR 062/058 : SANS demande mémoire, l'archi ne grandit pas et la mémoire ne paie pas → **préalable** qui débloque #4/#6 (sans lui, BPTT et récup épisodique optimisent une capacité que rien n'exige).
4. **Brancher le BPTT à travers les ticks** dans la boucle d'apprentissage vivante. EDR 067 : 0.78 → **1.00** sur rappel K-bits ; machinerie dans `tools/grad_mem.py`. Mieux fait dans le substrat différentiable → **[M]** coordination.

### P2 — Structurel moteur (torch) **[M]**
5. **Têtes disjointes + losses séparées + isolation de gradient** (world-model / critic / langage / action) dans le substrat torch. Aujourd'hui tout partage les 172 nœuds sans isolation ; la tête référentielle est le SEUL module séparé (et il a fallu l'ajouter pour que le langage marche, EDR 073) → généraliser le pattern.
6. **Récup épisodique réelle** : remplacer les 5 scalaires (top-500 global) par une trace content-addressable PAR AGENT, ordonnée dans le temps (embedding + requête de similarité réelle), branchée dans la décision.

### P3 — Distinguer & mesurer les types (instrument) **[I]**
7. **Fitness multi-objectif / per-type** : cesser d'écraser sur `life_score` ; mesurer survie / forage / craft / coop / langage séparément. Intégrer l'archive **MAP-Elites 4-tier déjà codée** (`map_elites.py`) à la boucle principale.
8. **Implémenter réellement worlds 2 & 3** avec KPI cognitif propre (agricole = anticipation/gratification différée ; industriel = coopération/division du travail) — sinon G1-G4 restent factices. **Instrumenter G2 composition** (outil « à créer »). Recoupe FamineWorld (session //, pénurie cyclique = anticipation).

### P4 — Différé / aspirationnel
9. **Theory of Mind** (module de modélisation d'autrui) — `BACKLOG.md:115`. Après que la coopération émergée mûrisse (EDR 028).

> **Lecture stratégique** : #4 (BPTT mémoire) et #5 (têtes disjointes) sont les deux leviers structurels, et tous deux sont NATURELLEMENT des chantiers du moteur torch (différentiable). #1/#2/#3/#6/#7 sont instrument-side et faisables sans collision. La migration moteur adresse littéralement les deux questions de l'audit : mémoire entraînable par gradient (#4) + facultés disjointes à losses séparées (#5).

---

## Clôture Partie A — Mémoire (synthèse, 2026-07-01)

> Record de **synthèse** (pas une expérience neuve) : la question « la mémoire émerge-t-elle / paie-t-elle ? »
> est désormais instrumentée sur ses **5 couches**, chacune par un instrument distinct. Verdict transversal
> convergent, cohérent avec l'arc substrat. Écrit après cartographie du backlog contre les sessions // actives
> (voir notes de coordination ci-dessous). Aucune expérience relancée.

### Les 5 couches × instrument × verdict

| Couche (§A) | Question | Instrument | Verdict | Preuve |
|---|---|---|---|---|
| **Travail** (`H_prev` récurrent) | La récurrence porte-t-elle l'info ? | décode latent de `H_S2` | **PRÉSENTE** (did_x décodable AUC~0.90) | EDR 120 / 150 |
| **Explicite** (NTM 10×5) | La mémoire câblée paie-t-elle in-world ? | `ABLATE_NTM` (bundle organes) | **INERTE** (organes du champion inertes, NEUTRE p=1.0) | EDR-134 / 135 (fil //) |
| **Long-terme** (KuzuDB → slots obs 51-55) | Le canal « épisodique » contribue-t-il ? | neutralisé par défaut en `benchmark_mode` | **SANS COÛT** (déjà ablaté dans toute éval rigoureuse ; champions performent) | lessons P0 + `biosphere-ambient-memory-nonrepro` |
| **Génétique** (`W` lamarckien) | Peut-on améliorer par gradient ? | mem_nas / grad_mem (isolation) | **OUI EN ISOLATION** (BPTT 0.78→1.00 rappel K-bits ; domine la mutation à tout délai) | EDR 064 / 067 / 123 |
| **`memory_cache`** (gène) | — | — | **DORMANT** (lu par `evolution.py` legacy, non muté ; à documenter, pas couper) | audit §A + décision 2026-06-30 |

### Verdict transversal

**La mémoire *peut* payer (isolation, gradient) mais *ne paie pas* dans les tâches actuelles.** Les tâches réactives
(forage) n'exigent pas de mémoire (EDR 062/058) → l'architecture ne grandit pas, le canal explicite est inerte
in-world, le canal long-terme est neutralisable sans coût, et la représentation récurrente porte de l'info sans
qu'elle soit *exploitée* pour la fitness. Nuance clé (EDR 123) : recall-through-delay ≠ crédit compositionnel
moyens→fins — la mutation tient le recall (~0.8 à D=24) mais échoue le compositionnel (hit_end~0, EDR 119/120) ;
**le verrou n'est pas le délai de mémoire, c'est le crédit** (means→ends), lui-même = verrou substrat/moteur.
Même diagnostic que Lewis, le binding compositionnel et la ToM : **substrat plat, fitness scalaire** → migration
moteur (substrat différentiable + plasticité/crédit, cf. `roadmap/NAS.md` + `sota-gap-substrate`).

### Notes de coordination (sessions // — 2026-07-01)

- **P0.1 (`clear()` manquant `robust_hof.py`) = RÉGLÉ en //** : commit `eec991b` (chantier/gradient-erosion) déplace
  `stop()+clear()` **AVANT** la boucle (pattern `main_curriculum`) et retire le `stop()` nu — meilleur que le
  one-liner proposé. **La ligne P0.1 du backlog ci-dessus est donc PÉRIMÉE** (garder pour trace, ne pas ré-exécuter).
- **Ablation NTM** : le flag `ABLATE_NTM` (+`ABLATE_ATTENTION`) a été posé par le fil in-world **EDR-134**, et
  **EDR-135** l'a exercé (bundle « legacy-core », tous organes OFF) → organes du champion INERTES. Isoler la NTM
  seule serait redondant et collisionnerait ce fil (le plus actif sur `mamba_agent.py`).
- **`H_prev` (working memory)** : ablation = retirer la récurrence cœur → éditer `mamba_agent.py` collisionne le
  fil torch. Non poursuivi.
- **Instruments per-type ToM** : représentationnel = **EDR 150** (ex-132/141, `tools/tom_probe.py`) ; comportemental =
  **EDR 151** (ex-139/142, `tools/tom_coordination.py`). Parqués dans le **bloc distant 150+** le 2026-07-01 après
  deux collisions cross-session (132 puis 141 repris par les fils compositional/torch //) — **convention** :
  instruments per-type/ToM en 150+, fils // (compositional/torch/famine) en 120-149.

### Conséquence

La **Partie A est close instrumentalement** : aucun axe expérimental mémoire substantiel n'est laissé vierge
(les restants sont couverts ou occupés en //). Le levier n'est plus un instrument mémoire de plus — c'est la
migration moteur (#4 BPTT-en-boucle + crédit différentiable), naturellement un chantier torch (coordonner).
