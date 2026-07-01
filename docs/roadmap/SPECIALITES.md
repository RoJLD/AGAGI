# Registre des territoires de recherche — AGAGI

> Source de vérité de la spécialisation. Éditer la carte = éditer ce fichier (path-scoped, ligne-à-ligne).
> Design : `docs/superpowers/specs/2026-07-01-territoires-recherche-cartographe-design.md`.

## Convention d'identifiants

- Nouveaux records : `EDR-<PREFIX>-<nnn>` (nnn zéro-paddé à 3, séquence propre au préfixe). Frontmatter `id:` obligatoire.
- Nom de fichier miroir : `docs/EDR/<PREFIX>-<nnn>_Titre.md` (ex. `SUB-012_...md`).
- **Append-only** : un préfixe n'est jamais réutilisé ni renuméroté → collision impossible.
- Legacy `EDR-nnn` (1-151) : intouché, cohabite.
- Collaboration : un pilote (préfixe propriétaire) + champ frontmatter `also: [PREFIX, …]`.

## Commons partagés (intendant désigné, read-mostly)

| Commons | Intendant | Notes |
|---------|-----------|-------|
| Sim de monde | WLD | WLD/CRAFT/NAV/FAM le LISENT ; chacun écrit ses propres probes |
| `tools/consolidate_records.py` | INFRA | outil de graphe des records |
| Core substrat | SUB | moteur torch/legacy |
| `tools/substrate_ab_compositional.py` | BIND | banc compositionnel |

## Territoires

### SUB — Substrat & Moteur d'apprentissage
- statut: actif
- couche: Substrat/Moteur
- question_phare: Moteur torch ≥ legacy + exploiter le gradient (BPTT in-world)
- fichiers_possedes: tools/substrate_world_ab.py, tools/torch_*_probe.py
- memoire: sota-gap-substrate.md
- legacy_edr: 134,135,137,138,139,140,141,143,144,145
- frontiere_courante: BPTT fenêtré in-world (persister le graphe K ticks)
- ponts_actifs: [BIND (portage means→ends), MEM (BPTT-mémoire)]
- filiation: —

### BIND — Crédit compositionnel & means→ends
- statut: actif (résolu sur proxy → portage)
- couche: Substrat/Cognition
- question_phare: Cracker le means→ends conditionnel
- fichiers_possedes: tools/substrate_ab_compositional.py
- memoire: coop-competence-is-population-property.md
- legacy_edr: 128,129,130,131,132,133,136,149
- frontiere_courante: porter la recette (gate + anti-saturation) en substrat torch-prod
- ponts_actifs: [SUB (portage)]
- filiation: —

### MEM — Mémoire
- statut: dormant (Partie A close)
- couche: Substrat
- question_phare: La mémoire paie-t-elle, et quand
- fichiers_possedes: —
- memoire: memory-architecture-audit.md
- legacy_edr: 062,064,067,120,123
- frontiere_courante: BPTT-mémoire in-world (pont SUB)
- ponts_actifs: [SUB]
- filiation: —

### WLD — Demande d'intelligence & plancher
- statut: actif
- couche: Monde
- question_phare: Le monde exige-t-il l'intelligence (métrique life_score)
- fichiers_possedes: (commons sim de monde — intendant)
- memoire: s2-world-demand-thread.md, world-floor-survivability-gate.md
- legacy_edr: 085,124
- frontiere_courante: réparer le gate de cohérence life_score (survivant≠marqueur)
- ponts_actifs: —
- filiation: —

### CRAFT — Craft, rétention & outils
- statut: actif
- couche: Monde
- question_phare: Pourquoi le craft n'est pas retenu
- fichiers_possedes: tools/craft_*.py
- memoire: world-floor-survivability-gate.md
- legacy_edr: 125,127
- frontiere_courante: mécanisme de rétention du craft en cohorte fixe
- ponts_actifs: —
- filiation: —

### NAV — Navigation & économie d'énergie
- statut: dormant
- couche: Monde
- question_phare: Le mur de navigation (approche vs capture)
- fichiers_possedes: tools/lewis_survival_sweep.py, tools/nav_*.py
- memoire: lewis-energy-economy-wall.md
- legacy_edr: 090,107,110,113,114
- frontiere_courante: mur = politique/substrat (pont SUB) ; dette knob disable_repro
- ponts_actifs: [SUB]
- filiation: —

### FAM — Famine, stockage & spécialisation
- statut: actif
- couche: Monde
- question_phare: Émergence de spécialisation world-spécifique
- fichiers_possedes: tools/famine_harshness_probe.py, tools/cross_world_transfer.py
- memoire: fil-directeur-agi-gates.md
- legacy_edr: 155,156,157
- frontiere_courante: durcir réfuté → levier = substrat/moteur (pont SUB) ; EDR-157 re-confirme (durcir DÉGRADE, le substrat ne spécialise pas)
- ponts_actifs: [SUB]
- filiation: —

### COG — Types d'intelligence & organes cognitifs
- statut: actif (dreaming réfuté ; ToM comportemental épuisé sur instrument gelé MAIS volet causal OUVERT — cf. EDR-151/150 ; têtes disjointes relancées 152-154)
- couche: Cognition
- question_phare: Quels types émergent / sont dissociables
- fichiers_possedes: tools/tom_probe.py, tools/anticipation_bench.py, tools/disjoint_heads_ab.py
- memoire: intelligence-typing-flat-connectome.md, dreaming-organ-not-dead.md, planner-depth1-refuted.md
- legacy_edr: 093,094,095,150,151,152,153,154
- frontiere_courante: équilibrage de crédit multi-tête (GradNorm-lite / lr-par-tête) dans le connectome PLAT, porté en prod — PAS la refonte #5 (EDR 152-154) ; + volet causal ToM NON TESTÉ (incitation ToM→life_score, différé migration torch — EDR 150/151)
- ponts_actifs: [BIND (crédit multi-tête), SUB (portage prod)]
- filiation: —

### INFRA — Instruments, méthodo & reproductibilité
- statut: continu
- couche: Instruments
- question_phare: Garder les bancs sains et reproductibles
- fichiers_possedes: tools/consolidate_records.py, tools/cartography.py (Partie 2)
- memoire: biosphere-ambient-memory-nonrepro.md, multiprocess-experiment-hazards.md, parallel-sessions-shared-tree.md
- legacy_edr: —
- frontiere_courante: cartographe automatique (Partie 2)
- ponts_actifs: [tous]
- filiation: —

### PROD — Migration prod, Backend & Frontend
- statut: actif
- couche: Prod
- question_phare: Porter les recettes validées en prod
- fichiers_possedes: (roadmap BACKEND.md / FRONTEND.md)
- memoire: sweep-view-backend-patch-pending.md
- legacy_edr: —
- frontiere_courante: embarquer gate+anti-saturation (BIND) et adaptateur torch (SUB) en prod
- ponts_actifs: [BIND, SUB]
- filiation: —

## Doublons legacy connus (à nettoyer de façon coordonnée, cf. cartographe)

EDR-093, EDR-094, EDR-100, EDR-105, EDR-113 : deux records distincts partagent le numéro (collisions
de sessions //). Tolérés (legacy cohabite) ; signalés en `warnings` par consolidate.

Collision de titres (FAM, notée 2026-07-01 par le cartographe) : les fichiers `155_*`/`156_*`/`157_*.md`
(id frontmatter EDR-155/156/157, rattachés à FAM) portent des titres H1 internes « EDR 126/129/130 »
— numérotation FAM héritée du suivi mémoire. NE PAS confondre avec les EDR-126/129/130 de BIND
(fil Compositional). Cohabitation tolérée ; à harmoniser lors d'un nettoyage coordonné.

Collision de numéros 155/156 (COG↔FAM, notée 2026-07-01) : le fil disjoint-heads (COG, session //)
suit en MÉMOIRE des records « EDR-155/156 » (V2/V3 `disjoint_heads_correlated.py`) qui ne sont PAS
matérialisés en `docs/EDR/` ; sur disque, 155/156/157 = les records FAMINE (autoritaires). Aucun doublon
d'id disque (donc pas de `warning` consolidate), mais la session disjoint-heads NE DOIT PAS filer ses
V2/V3 sous 155-157. **Règle de sortie** : tout nouveau record COG (dont les disjoint V2/V3) prend un ID
PRÉFIXÉ `EDR-COG-nnn` (convention append-only, cf. en-tête), pas un numéro legacy.
