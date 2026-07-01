# Migration SOTA & graphe REF — Implementation Plan

> Design : `../specs/2026-06-29-SOTA-Migration-design.md`. Méthode : Commandement 15
> (1 variable, powered, valide-ou-revert). Sessions parallèles : commits path-scoped.

**Goal:** Garder l'instrument (mondes/métriques/discipline), migrer le moteur numpy maison vers
des briques SOTA entraînées par gradient, sous A/B falsifiable ; ancrer chaque axe dans le
graphe records via des nœuds REF.

## Étape 0 — Graphe REF (✅ LIVRÉ 2026-06-29)

- [x] Type `REF` + scan `docs/REF/` dans `tools/consolidate_records.py`
- [x] Arêtes-pont `rediscovered_by`/`supersedes`/`adopt_for`/`grounds`
- [x] 4 tests RED→GREEN + 11 historiques verts (15 total)
- [x] 11 nœuds REF + README de convention ; consolidation 0 problème
- [x] Enforcement : champ `requires_ref` → `validate_graph` lève `missing_ref` si aucun
  nœud REF ne couvre le record ; `main` sort ≠0 (gate démontré sur SDR-G1/G4, ancrés)

## Axe 1 — Substrat LTC + apprentissage (PRIORITÉ, casse le verrou prouvé)

- [ ] Ajouter `requirements-torch.txt` (torch, `ncps`) — extra optionnel, jamais dans le core
- [ ] Définir l'interface `AgentModel` (forward / learn / from_genome) ; numpy = backend `legacy`
- [ ] Backend `torch` : LTC/CfC via `ncps`, entraîné par gradient (sélection `AGENT_BACKEND=torch`)
- [ ] A/B `transfer_ratio` (G1) torch vs legacy, apparié multi-seed via `Harness`, budget égal
- [ ] Gate de succès : torch ≥ legacy ET casse le plateau de compétence (EDR 081) → sinon EDR négatif
- [ ] EDR de verdict + REF-LTC-2021 `adopt_for` mis à jour selon le résultat

## Axe 2 — NAS utile (profondeur sous gradient)

- [ ] Une fois Axe 1 vert : l'évolution choisit `hidden_layers ∈ {1,2,4}` (hyperparam, pas split neutre)
- [ ] Sweep : la capacité paie-t-elle enfin sous gradient ? (confirme/réfute EDR 110 sur substrat torch)

## Axe 3 — Anticipation DreamerV3 (G4)

- [ ] `world_model.py` : world model latent appris (au-delà du RND à projection fixe)
- [ ] Brancher le « dreaming » sur `world_model.predict()` (rollouts latents) — gated OFF par défaut
- [ ] `anticipation_bench.py` : Dreamer ON vs OFF ; gate = bat le random-shooting latent actuel

## Axe 4 — Langage EGG (Arc 4)

- [ ] Wrapper `referential_head.py` sur EGG (signaling game outillé)
- [ ] `wire_ref_head.py` : MI(token;apex) + bénéfice fonctionnel EGG vs maison

## Axe 5 — Curriculum POET/OMNI (G0-G1)

- [ ] Brancher `curriculum/runner.py` (dormant) sur un générateur d'environnements co-évolué
- [ ] `curriculum_transfer.py` : POET vs séquence manuelle, `transfer_ratio` apparié

## Axe 6 — RSI ELM/ADAS (#8)

- [ ] Armer `llm_proposer_fn.py` (anthropic) dans la boucle `rsi_loop.py`, sandbox durcie
- [ ] Mesurer : le #8 trouve-t-il une amélioration réelle une fois le substrat torch (espace non-barren) ?

## Contraintes globales

- **Non-régression** : tout backend SOTA est opt-in ; le chemin legacy numpy reste vert.
- **1 variable** : geler l'aval avant tout changement cognitif (sinon confound).
- **Négatifs = livrables** : un axe qui ne bat pas le baseline → EDR négatif consigné, pas un échec.
- **Path-scoped commits** (sessions parallèles, cf. mémoire `parallel-sessions-shared-tree`).
