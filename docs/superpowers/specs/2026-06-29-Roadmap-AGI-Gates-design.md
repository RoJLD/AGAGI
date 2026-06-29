# Design — Fil directeur AGI : les 5 portes G0→G4 + consolidation EDR/ADR/SDR

> **Date** : 2026-06-29 · **Statut** : design validé (brainstorming), avant plan d'implémentation.
> **Place** : ce document est la *stratégie* qui chapeaute les 4 roadmaps de domaine
> ([`roadmap/SCIENCE.md`](../../roadmap/SCIENCE.md) · `NAS` · `BACKEND` · `FRONTEND`).
> Il ne remplace PAS [`FIL_CONDUCTEUR.md`](../../FIL_CONDUCTEUR.md) (mémoire historique EDR 010→087),
> il le **continue**. Sortie finale visée : un nouveau `docs/roadmap/FIL_DIRECTEUR_AGI.md`.

---

## 1. Thèse — et la tension qu'on tranche

Le projet teste depuis EDR 010 : **« le bon n'est pas dit mais trouvé — et trouvé seulement si le
monde l'EXIGE. »** Mais sa propre mémoire contient une tension non résolue :

- **Thèse fondatrice** (010/012) : le **monde doit EXIGER** (sélection).
- **Tournant** (067→070) : non, le levier est **COMMENT l'agent apprend** (gradient).
- **Récent** (105→108) : retour au substrat — **« le répertoire-monde est le verrou »**.

**Décision (SDR-000)** : ces trois lectures ne s'empilent pas, elles se **réconcilient en un point
mesurable** : la **généralisation zéro-shot**. Le monde doit exiger une compétence *qui transfère*, et
elle ne transfère que si l'agent l'a *apprise* (gradient), pas mémorisée. La métrique-étoile
`transfer_ratio` est l'endroit exact où « le monde exige » ET « l'agent apprend » se rencontrent.

## 2. Le moteur (architecture invariante des 5 portes)

Une seule architecture, trois rouages — **le GA n'est pas le moteur de l'intelligence, c'est le moteur
de la recherche de substrat** :

| Rouage | Rôle | État repo |
|---|---|---|
| **Boucle externe = GA** | explore topologies (`add_node`, `preserve_dims` ON), objectifs/demandes-monde, diversité | actif (PR #58) |
| **Boucle interne = gradient** | Actor-Critic intra-vie : comment l'agent apprend dans sa vie | actif (biosphère) |
| **Baldwin** | l'évolution façonne des inits *apprenables* | partiel (068) |
| **★ north-star** | `transfer_ratio` (zéro-shot → monde non vu) = signature intelligence-vs-mémorisation | outil existe |

> Fondé sur EDR 064/067-070 : la **mutation seule est un chercheur FAIBLE** (NAS = bloat neutre,
> langage = loterie 25 %). Le couple GA(structure)+gradient(apprentissage) est non-négociable.

## 3. Les 5 portes (G0→G4) — bottom-up par dépendance

Règle : on ne franchit une porte que si la précédente est **mesurée** (verdict EDR powered). Chaque
porte est une **SDR** (hypothèse falsifiable). Capacités **stratifiées** (EDR 075 : langage gated par
compétence gated par substrat) → l'ordre est une contrainte, pas une préférence.

### G0 — Le monde EXIGE-t-il ? *(porte de validité + contrainte compute)*
- **Hypothèse falsifiable** : un champion HoF survit significativement mieux qu'un agent dummy/aléatoire
  dans chaque monde utilisé en aval. Si ratio ≈ 1 → monde factice, toute « compétence » y est du bruit.
- **KPI** : `survival_ratio(champion)/survival_ratio(dummy)`, multi-seed appairé, powered.
- **Outil** : *à créer* — benchmark dummy-vs-champion (flaggé SCIENCE.md #2, n'existe pas), sur `Harness`.
- **Critère de passage** : ratio ≥ seuil powered sur les mondes aval. Monde qui échoue = exclu ou enrichi.
- **Sous-chantier bloquant — compute** : la rigueur multi-seed × K-éval × R-runs explose sur
  mono-machine (garde-fou SCIENCE.md). Parallélisme / early-stopping / budget = **prérequis de G0**,
  sinon G1 à l'échelle est intenable.

### G1 — La compétence GÉNÉRALISE-t-elle ? *(north-star)*
- **Hypothèse** : champion évolué en monde A atteint la compétence en monde B *jamais vu* mieux que
  tabula-rasa, **à compute égal**.
- **KPI** : `transfer_ratio`, test de signe binomial, multi-seed appairé.
- **Outil** : *existe* — [`tools/curriculum_transfer.py`](../../../tools/curriculum_transfer.py)
  (verdict TRANSFERE/NEUTRE/NUIT). Reste : *lancer à l'échelle* + opt-in `main_biosphere`.
- **Critère de passage** : verdict TRANSFERE, `sign_p` significatif.
- **Boucle de réfutation** : si NEUTRE/NUIT → confirmation du verrou « répertoire-monde » (EDR 105/108)
  → **ADR « enrichir UNE affordance de monde »** → nouvel EDR → re-test. C'est la boucle centrale du projet.

### G2 — L'agent COMPOSE-t-il ?
- **Hypothèse** : l'agent enchaîne des compétences acquises séparément en une séquence *nouvelle, non
  récompensée directement* (craft multi-étapes L3+, échelle EDR 018).
- **KPI** : taux d'émergence d'une chaîne jamais récompensée directement vs ablation ; ET elle transfère (↔G1).
- **Outil** : *à créer* — harnais de gates par paliers L0→L3 (design BACKLOG §1bis).
- **Critère de passage** : composition au-dessus du hasard ET `transfer_ratio` > 1 sur la chaîne composée.

### G3 — Le langage PAYE-t-il ? *(clôture Arc 4)*
- **Pré-condition levée** : la compétence-substrat existe enfin (G0-G2 lèvent le gate EDR 075).
- **Hypothèse** : le code référentiel fiable (`use_ref_head`, EDR 074) améliore *causalement* la chasse
  coop / survie des auditeurs.
- **KPI** : `mammoth_kills`/survie, ref_head ON vs OFF, powered R≥4, design audité 12 confounds (EDR 087).
- **Outil** : *existe* — [`tools/wire_ref_head.py`](../../../tools/wire_ref_head.py).
- **Critère de passage** : bénéfice causal robuste sous puissance (battre le « non robuste » d'EDR 088).

### G4 — L'agent ANTICIPE-t-il ? *(capstone cognitif)*
- **Hypothèse** : brancher l'organe de rêve sur `world_model.predict()` (vraie simulation de
  trajectoires — PAS le random-shooting latent réfuté EDR 095, PAS le depth-1 linéaire réfuté) produit
  une anticipation instrumentale qui paye.
- **KPI** : `anticipation_bench` (existe), variantes depth-k / `g` bilinéaire.
- **Outil** : *existe* — `tools/anticipation_bench.py`.
- **Critère de passage** : le planning bat le no-planning sur banc équitable (la barre que depth-1 a ratée).

## 4. Consolidation automatique — graphe EDR / ADR / SDR

### 4.1 Taxonomie des records
| Type | Sens | Couche | État |
|---|---|---|---|
| **EDR** Experience/Experiment Decision Record | « on a mesuré X, verdict Y » | empirique | *existe* (110, `docs/EDR/`) |
| **ADR** Architecture Decision Record | « on a choisi la structure/le code X parce que Y » | structurelle | *à créer* (`docs/ADR/`) |
| **SDR** Science/Strategy Decision Record | « on fixe la direction scientifique X » (les portes G0→G4) | stratégique | *à créer* (`docs/SDR/`) |

### 4.2 Causalité du graphe
```
SDR  ── MOTIVE ──▶  EDR  ── DECLENCHE ──▶  ADR
(porte)            (test)                 (changement substrat/code)
       ◀── VALIDE/REFUTE ──        ◀── TESTE_PAR ──
```
Exemple vivant : `SDR-G1` ──MOTIVE──▶ `EDR-105/108` (NEUTRE) ──DECLENCHE──▶ `ADR « enrichir affordance Z »` ──MOTIVE──▶ nouvel EDR.

### 4.3 Mécanisme (niveau choisi : **index + graphe statique**, pas de LLM)
- **Frontmatter normalisé** sur chaque record (YAML en tête de fichier `.md`) :
  ```yaml
  ---
  id: SDR-G1            # ou EDR-105, ADR-007
  type: SDR             # SDR | ADR | EDR
  title: ...
  status: open|tested|validated|refuted|superseded
  gate: G1              # rattachement à une porte (optionnel pour ADR transverses)
  motivates: [EDR-105, EDR-108]    # SDR → EDR
  triggers: [ADR-007]              # EDR → ADR
  tests: [SDR-G1]                  # EDR → SDR (réciproque de motivates)
  verdict: TRANSFERE|NEUTRE|NUIT|... # EDR seulement (prose libre autorisée en corps)
  ---
  ```
- **Outil** *à créer* : `tools/consolidate_records.py` — pur, testable, sans LLM. Scanne
  `docs/{EDR,ADR,SDR}/`, valide le frontmatter, construit le graphe (JSON :
  `results/records_graph.json`), détecte les liens cassés/orphelins, et **génère l'état roadmap**
  (par porte : ouverte/franchie, EDR qui la testent, ADR déclenchés).
- **Endpoints** *à créer* : `/api/adr` + `/api/sdr` (copie conforme du pattern `/api/edr` dans
  [`backend/app/routes/edr.py`](../../../backend/app/routes/edr.py)).
- **Frontend** : réutiliser le pattern [`lib/edrIndex.ts`](../../../frontend/src/lib/edrIndex.ts) pour
  ADR/SDR (vue graphe interactive = *hors scope* de cette itération, backlog).
- **Anti-théâtre** : l'outil échoue (exit≠0) si un `motivates`/`triggers` pointe vers un id inexistant
  ou si une porte `status: validated` n'a aucun EDR `validated` qui la teste. La consolidation **prouve**
  la cohérence, elle ne la décore pas.

> **Migration légère** : les EDR existants n'ont pas de frontmatter. L'outil tolère leur absence
> (record « non lié », signalé) → on enrichit incrémentalement, pas de big-bang sur les 110 EDR.

## 5. Méthode (le fil qui met dans le top 0,01 %)
- **Commandement 15** partout : 1 variable, powered (≥ ce que la puissance exige), valide-ou-revert.
- Chaque porte = un **test falsifiable** (signe/binomial), multi-seed appairé, **compute égal**.
- **Les résultats négatifs sont des livrables de premier rang** (les murs = contributions publiables).
- `transfer_ratio` mesuré à *chaque* porte, pas seulement G1.
- Tout changement cognitif **gèle l'aval** d'abord (sinon confound).

## 6. Périmètre & non-buts
- **Dans le périmètre** : `docs/roadmap/FIL_DIRECTEUR_AGI.md` (stratégie G0→G4), schéma frontmatter
  records, `tools/consolidate_records.py` + tests, endpoints `/api/adr`+`/api/sdr`, premiers SDR (G0-G4)
  et ADR rétro (moteur GA+gradient, `preserve_dims`, `Harness`).
- **Hors périmètre (backlog)** : vue graphe frontend interactive ; auto-extraction LLM des liens ;
  unification KuzuDB ; Arcs 5-7.

## 7. Risques
| Risque | Mitigation |
|---|---|
| Compute mono-machine fait exploser G1 | sous-chantier compute = prérequis G0 (parallélisme/early-stop) |
| G1 révèle le substrat comme cul-de-sac | c'est un *résultat*, pas un échec → boucle ADR enrichir-affordance |
| Frontmatter rétro sur 110 EDR = corvée | tolérance « non lié », enrichissement incrémental |
| Goodhart sur `transfer_ratio` | mondes B *jamais vus*, tabula-rasa à compute égal, test de signe |

## 8. Critères de succès du chantier (méta)
1. `FIL_DIRECTEUR_AGI.md` existe et lie chaque porte à ses EDR/ADR.
2. `tools/consolidate_records.py` vert (tests), génère `records_graph.json`, échoue sur lien cassé.
3. G0 livré : verdict mesuré « le monde exige » sur ≥1 monde aval.
4. G1 lancé à l'échelle : un premier `transfer_ratio` powered (quel que soit le verdict).
