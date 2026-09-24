# Spec — Dashboard « Pilotage » AGAGI : une source unique, trois rendus, lecture seule

**Date** : 2026-09-22. **Statut** : conception validée par robla en quatre sections (consommateur « les deux, source
unique » ; lecture seule au lot 1 ; approche A ; sections A-B-D-E approuvées le 2026-09-22), implémentation à
planifier. **Portée** : AGAGI seul. **Dépend de** : la couche PM (spec
`docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md`, livrée sur `chantier/pm-roles` le 2026-09-22, pointe
`6977912a` le 2026-09-23, non fusionnée : la fusion sur `feat/d1-prod-pairing` attend la décision de robla).

**Provenance** : état mesuré le 2026-09-22 au soir (commandes citées dans chaque section) ; tout chiffre ci-dessous
est daté et recomputable, aucun n'est recopié d'un autre document.

---

## 0. Ce qu'on construit, et pourquoi

robla fait tourner 6 sessions Claude sur l'arbre AGAGI partagé (registre natif `~/.claude/sessions/*.json`, 14
entrées dont 6 en cwd AGAGI le 2026-09-22) plus des sous-agents de workflow. Trois questions posées le 2026-09-22 :
« a-t-on le visu sur ce que font les agents en temps réel ? », « peut-on lier aux artefacts de création Claude ? »,
« comment gérer le projet et connaître l'avancement depuis un dashboard ? ».

**Réponses mesurées avant de concevoir :**

1. *Temps réel* — partiellement, et pas dans le frontend. `tools/pm/board.py::compute` (branche `chantier/pm-roles`,
   `155b7a0a`) produit `data/pm/BOARD.md` : lu le 2026-09-22 21:24, il voit **6 sessions AGAGI, 0 P-item, 0 fichier
   en vol pour chacune, 3 alertes A3** — les hooks bulletin (`.claude/settings.json`) n'existent que sur cette
   branche, donc aucune session de l'arbre principal n'écrit de bulletin (`data/sessions/` absent sur l'arbre
   principal, vide dans le worktree). Les sous-agents de workflow (worktrees `.claude/worktrees/wf_*`, verrouillés)
   ne sont dans aucun registre. Le frontend (19 onglets, 4 familles, `frontend/src/tabs.ts`) est un instrument
   scientifique sans notion de session, de backlog ni de roadmap. Pointe de `chantier/pm-roles` le 2026-09-23 :
   `6977912a` — le board publie désormais `cpu_pct` (instantané, 1 s, à la place de `cpu_5min_pct`), les
   `sessions_mortes` écartées et l'alerte A9 (hooks en échec) ; son contrat est figé par `tests/sandbox/test_pm_board.py`.
2. *Artefacts Claude* — aucun artefact AGAGI n'existe (11 publiés le 2026-09-22, tous ELYSIUM ou personnels). Un
   artefact ne peut pas lire les fichiers locaux (CSP) ; il peut porter une base qu'une session alimente. Il ne peut
   donc être qu'une **vue poussée**, jamais le cockpit.
3. *Avancement* — les sources existent en fichiers : le backlog (`docs/roadmap/PRIORITES_ET_DETTES.md`, 119 entrées,
   clauses `closes_when` évaluables par `tools/check_backlog_freshness.py`), `results/records_graph.json` (clé
   `roadmap` : G0-G4 avec `status`, `sdr`, `tested_by` ; clé `graph.nodes` : 300 EDR et ADR), `data/pm/ROLES_COUNTS.json`
   (ratio science/méthodo, 0,83 le 2026-09-22 sur la fenêtre depuis le 09-16), l'inventaire des portes
   (`tools/check_gate_mutation.py:69`, `PORTES`).

**Décisions de robla (2026-09-22)** : consommateur = **les deux, source unique** (cockpit local temps réel ET page
publiée) ; **lecture seule** au lot 1 (un dashboard qui écrit serait un writer de plus sur des fichiers partagés) ;
approche **A** (une fonction pure, trois rendus).

---

## 1. Principes

1. **Une source, une fonction pure.** `compute_pilotage(...)` prend tout en argument et n'écrit rien ; elle est
   calibrable par injection à réponse connue comme n'importe quel instrument du dépôt.
2. **Un writer par fichier, toujours.** Le backend ne produit aucun fichier ; `PILOTAGE.json` est écrit par le tick PM ;
   la base de l'artefact est écrite par la session PM.
3. **Aveuglement visible (porte 14 appliquée au schéma).** Une source absente donne une ligne `aveugle` et un bloc
   `null` — jamais un 0, jamais une liste vide, jamais un « 0 alerte » silencieux.
4. **Aucun pourcentage d'avancement.** Le backlog grossit en travaillant (les entrées closes restent) ; un « x % »
   serait un chiffre fabriqué. On montre des comptes recomputés, datés, et trois lectures (section 2.3).
5. **Le lien vers la preuve, pas vers un décor.** Chaque élément pointe vers son fichier (P-item → chemins cités ;
   porte G → records ; session → fichiers en vol) ; un chemin absent est rendu absent, jamais déguisé en lien.
6. **La racine du dépôt se résout par `tools.parity_check.find_repo_root`** (`tools/parity_check.py:40`), jamais par
   `Path(__file__).parents[N]` — cf. P2.81 (section 10).

---

## 2. Architecture

### 2.1 Vue d'ensemble

```text
sources (fichiers, git, registre, psutil)
   │  lues par tools/pm/snapshot.py (existant) + tools/pm/pilotage.py (lecteurs, None si absent)
   ▼
compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now) -> pilotage_v1   [PURE]
   │
   ├─ backend  GET /api/pm/pilotage   (en mémoire, cache 30 s, n'écrit rien)   ──► frontend, famille « Pilotage »
   │
   └─ tick PM  data/pm/PILOTAGE.json  (writer PM)  ──► skill /pm : Artifact write_db ──► page artefact
```

### 2.2 Le schéma `pilotage_v1`

```text
{
  "schema": "pilotage_v1",
  "generated_at": <epoch s>,
  "repo_root": <str>,
  "aveugle": [<str>, ...],                      # une ligne par source absente ou par erreur nommée

  "flotte": null | { ... },                     # = tools.pm.board.compute(snap), INCHANGÉ : ses clés sont le CONTRAT du
                                                # board, figé par tests/sandbox/test_pm_board.py, jamais réénumérées ici.
                                                # Lu à la pointe 6977912a (2026-09-23) : generated_at, repo_root, aveugle,
                                                # sessions, sessions_mortes, alertes (A1-A9),
                                                # charge_connue {sims_en_vol, cpu_pct, bails_vivants}, worktrees, bails

  "roadmap": null | {
    "direction": {"rangs": [{"rang": "14 ter", "p_item": "P2.78", "statut": "close"}, ...]},
    "entrees": [{
        "num": "P2.78", "priorite": "P2", "rang": "14 ter" | null,
        "statut": "ouverte" | "close" | "perimee" | "illisible",
        "date": "2026-09-22" | null, "titre": <str>, "lignes": [671, 697],
        "clause": null | {"pred": "grep_present", "arg": "...", "satisfaite": true | false | null, "raison": null | <str>},
        "chemins": [{"rel": "tools/cost_guard.py", "existe": true}, ...]
    }, ...],
    "comptes": {"par_priorite": {"P0": {"ouvertes": n, "closes": n, "perimees": n}, ...}, "total": n, "illisibles": n},
    "portes_agi": <records_graph["roadmap"] tel quel>          # {"G0": {"sdr", "status", "tested_by": [...]}, ...}
  },

  "portes": null | [{
    "num": "1", "module": "tools.check_record_links", "titre": <str>, "temoins": [<str>, ...],
    "baseline": null | {"chemin": "tools/record_link_baseline.json", "existe": true, "dette": n | null}
  }, ...],

  "charge": null | {
    "sims_en_vol": n | null, "cpu_pct": x | null, "bails_vivants": [...] | null,     # noms du board, jamais renommés
    "ratio_science_methodo": x | null, "fichiers": {"science", "methodo", "autre"} | null, "depuis": "2026-09-16" | null
  }
}
```

Règles du schéma :

- `flotte` est la sortie de `board.compute` **sans transformation** (test de non-duplication, section 6) ; ses propres
  lignes `aveugle` sont recopiées dans le `aveugle` de tête, préfixées `flotte:`.
- `roadmap.entrees` a exactement `compter_entrees(txt)` éléments (`tools/check_backlog_freshness.py:315`) : une entrée
  inanalysable est `illisible`, jamais absente.
- `portes` est recomputé depuis `check_gate_mutation.PORTES` : le nombre n'est écrit nulle part.
- `charge` fusionne `flotte.charge_connue` (champs repris SOUS LEURS NOMS du board) et `ROLES_COUNTS.json` ; chaque
  champ est `null` si sa source manque.

### 2.3 « Avancement » : trois lectures

1. **La direction 🧭** : les rangs tranchés (têtes d'entrée portant `rang N`, 19 le 2026-09-22) et le statut réel de
   chacun — c'est « où on en est de ce qu'on a décidé ».
2. **Les portes G0-G4** (`records_graph.roadmap`) : statut, SDR, records qui les testent.
3. **Le rythme** : ouvertes / closes / périmées par priorité, ratio science/méthodo et sa fenêtre — datés.

---

## 3. Composants

### 3.1 `tools/pm/pilotage.py` — nouveau, n'écrit jamais rien

**Lecteurs** (chacun rend `None` si la source est absente ou illisible, jamais une valeur par défaut) :

| fonction | source | chemin |
| --- | --- | --- |
| `read_backlog(repo_root)` | texte du backlog | `<root>/docs/roadmap/PRIORITES_ET_DETTES.md` |
| `read_records_graph()` | graphe de records | `paths.results_file("records_graph.json")` — **jamais le littéral `results/…`** (porte 12) |
| `read_roles_counts()` | compteurs du PM | `paths.pm_dir("ROLES_COUNTS.json")` |
| `read_portes()` | inventaire des portes | `tools.check_gate_mutation.PORTES` joint à la table `BASELINES` (ci-dessous) |

**`BASELINES`** : table déclarée dans le module, `module -> (chemin de baseline relatif, clé de la collection qui
compte la dette ou None)`. Au 2026-09-22 les baselines existantes sont (`ls tools/*baseline*.json`) :
`agi_taxonomy`, `backlog_freshness` (`legataires`), `bar_separation`, `calibration_reach`, `control_family`,
`data_paths` (`fichiers`), `fabricated_defaults`, `guard_negative_cases`, `instrument_calibration`, `io_overlap`,
`record_link`, `substrate_pinning`, `test_census`. Seules `backlog_freshness` et `data_paths` ont une clé de dette
déclarée (leur forme a été lue) ; les autres portent `dette: null` jusqu'à ce qu'un auteur DÉCLARE la clé — on ne
proxifie pas ce qu'on n'a pas lu. `existe` est mesuré à chaque appel.

**`parse_roadmap(txt, repo_root, now) -> dict`** — réutilise le cliquet, n'invente aucun regex d'entrée :

- bornes des entrées : `_ENTREE.finditer(txt)` (`tools/check_backlog_freshness.py:91`, même objet que `_entrees`) ;
  numéros de ligne = comptage des `\n` avant l'offset de début et de fin ;
- `num` = groupe 1 de `_TETE` (`:59`) ; une tête composite `P2.0 / P2.1` donne une entrée par numéro, mêmes bornes ;
- `priorite` = préfixe avant le point ; `rang` = regex `—\s*rang\s+(\d+(?:\s+(?:bis|ter|quater))?)` sur la première
  ligne, `null` sinon ; `date` = première `\d{4}-\d{2}-\d{2}` des deux premières lignes, `null` sinon ;
- `statut` : `perimee` si `PÉRIMÉE` ou `CADUQUE` dans les deux premières lignes ; sinon `close` si l'un des
  `_CLOSE_MARQUEURS` (`:92`) y figure — même règle que le cliquet ; sinon `ouverte` ;
- `clause` : `_CLAUSE.findall(bloc)` (`:82`) ; la première clause est évaluée par `_evalue_clause` (`:125`) ; une
  exception pendant l'évaluation donne `satisfaite: null, raison: <str(exc)>` ; plusieurs clauses → la première est
  évaluée, les autres listées dans `raison` ;
- `chemins` : `_BACKTICK_PATH.findall(bloc)` (`:61`) filtrés sur `"/" in c` (même filtre que
  `tools/pm/snapshot.py::read_backlog_paths`), `existe` = `os.path.exists(join(root, rel))` ;
- toute exception dans le traitement d'UNE entrée → `statut: "illisible"`, `titre` = première ligne brute, le reste
  `null` ; la fonction termine par `assert len(entrees) == compter_entrees(txt)`.

**`compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now) -> dict`** — pure ; appelle
`board.compute(snap, now=now)` si `snap` n'est pas `None` ; assemble le schéma 2.2.

**`main(argv)`** : `--json` imprime le résultat (indent 1, `ensure_ascii=False`), `--repo-root` optionnel ; **aucune
écriture de fichier**. Nommage : pas de `def run(` au niveau module (collision connue du cliquet de calibration).

### 3.2 Backend

- `backend/app/services/pilotage_service.py` : `get_pilotage(ttl_s=30.0) -> dict` — cache mémoire `(généré_à, dict)` ;
  sous le TTL rend le cache ; sinon `snapshot(repo_root)` (`tools.pm.snapshot`) + lecteurs + `compute_pilotage`.
  Racine = `find_repo_root(None)`. Toute exception → dict `pilotage_v1` dont `aveugle = ["pilotage: <type>: <msg>"]`
  et les quatre blocs `null` (jamais 500, jamais silencieux).
- `backend/app/routes/pm.py` : `GET /pilotage` (monté `prefix="/api/pm"`, `tags=["pm"]`), `response_model=PilotageV1`
  (modèles pydantic dans `backend/app/schemas.py`, `extra="allow"` sur `flotte` qui reprend le schéma du board) — c'est
  ce qui donne les types TypeScript par `npm run gen:api` (`frontend/package.json`, script `gen:api`).
- `backend/app/main.py` : `include_router(pm_router, prefix="/api/pm", tags=["pm"])` ; **et correction de P2.81** :
  `RESULTS_DIR = find_repo_root(None) / "results"` (l.68) — voir section 10.
- La porte de parité (`tools/parity_check`, exposée par `/api/health/parity`) signale tout endpoint non consommé : le
  nouveau l'est par 3.3.

### 3.3 Frontend — famille « Pilotage »

- `frontend/src/tabs.ts` : `TAB_KEYS` gagne `"flotte" | "roadmap" | "portes"` ; `TAB_FAMILIES` gagne
  `{ family: "Pilotage", tabs: [Flotte, Roadmap, Portes] }` (icônes lucide : `Users`, `Map`, `ShieldCheck`) ;
  `frontend/src/tabs.test.tsx:7` (ordre = concat des familles = `TAB_KEYS`) est mis à jour en conséquence.
- `frontend/src/App.tsx` : trois `lazy()` (l.12-31) et trois branches dans le `switch` implicite (l.74-96) ;
  `showSidebar` (l.36) reste faux pour ces onglets.
- `frontend/src/api/queryKeys.ts` : `pm: { pilotage: ["pm", "pilotage"] as const }`.
- `frontend/src/api/pm.ts` : `fetchPilotage(): Promise<PilotageV1>` via `apiFetch` (`frontend/src/api/client.ts`) ;
  type `PilotageV1` importé de `schema.ts` (généré) avec un alias local.
- `frontend/src/hooks/usePilotage.ts` : `useQuery({ queryKey: queryKeys.pm.pilotage, queryFn: fetchPilotage,
  ...livePoll(30_000) })` (`frontend/src/lib/polling.ts:11`, `livePoll(intervalMs)`) — un seul fetch pour les trois vues.
- `frontend/src/components/pilotage/AveugleBanner.tsx` : rend la liste `aveugle` en tête, `role="status"`,
  jamais masqué s'il y a une ligne.
- `frontend/src/components/pilotage/PilotageFlotteView.tsx` : `Stat` × 3 (sims en vol, CPU instantané, bails), table des
  sessions (nom, branche, P-items revendiqués / inférés, nombre de fichiers en vol, âge du heartbeat), alertes en
  liste avec `Badge` (`danger` pour `alerte`, `warning` pour `info`) et preuve dépliable (`<details>`).
- `frontend/src/components/pilotage/PilotageRoadmapView.tsx` : direction (table rang → P-item → statut) ; cartes
  G0-G4 (`Panel` : statut, SDR, records) ; table des entrées avec filtres priorité et statut (`Field`), colonne
  clause en `Badge` (`success` satisfaite / `warning` non / `neutral` invérifiable avec la raison en `title`),
  chemins cités en `<a href="vscode://file/<abs>:<ligne>">` quand `existe`, sinon `<s>` non cliquable ; `Stat`
  ouvertes / closes / périmées par priorité, datés de `generated_at`.
- `frontend/src/components/pilotage/PilotagePortesView.tsx` : table (n°, module, titre, témoins, baseline, dette) ;
  phrase fixe en tête : « inventaire recomputé depuis check_gate_mutation.PORTES — aucune porte n'est exécutée d'ici ».
- Primitives existantes uniquement : `Panel`, `Stat({label, value})`, `Badge`, `Empty({message, action})`, `Loading`,
  `ErrorState`, `Field` (`frontend/src/components/ui/`). Thème : tokens CSS existants ; a11y : `:focus-visible` via les
  classes existantes, `aria-label` sur les tables. Aucun emoji dans les libellés (règle utilisateur).

### 3.4 Tick PM et page artefact

- `tools/pm/tick.py` (fichier de la session `pm-roles`) : après l'écriture de `BOARD.json`, écrire
  `paths.pm_dir("PILOTAGE.json")` = `compute_pilotage(...)` avec le même `snap` (≈ 3 lignes : import, appel, dump).
  Patch proposé au propriétaire ; ou appliqué par moi après le lot 0 avec `check_staged_authorship.snapshot`/`verify`.
- Skill `/pm` (`.claude/skills/pm/SKILL.md`, même propriétaire) : un pas supplémentaire — si `PILOTAGE.json` a changé
  depuis le tick précédent, publier vers l'artefact : `Artifact write_db` (`db_op: set`, `collection: pilotage`,
  `doc_id: latest`, `file_path: <data_root>/pm/PILOTAGE.json`) puis un second `set` avec `doc_id: <AAAA-MM-JJ-HHMM>`.
  Le PM est l'unique writer de cette base ; personne d'autre ne la touche.
- Page : `tools/pm/artefact/pilotage.html`, versionnée, publiée UNE fois par l'outil Artifact (favicon fixé à la
  création ; URL notée dans `docs/roadmap/FRONTEND.md`), capacités déclarées après lecture du skill
  `artifact-capabilities` (a minima `db` ; `user` si la lecture par viewer l'exige). Elle lit `pilotage/latest`, rend les
  quatre blocs en texte (aucun lien de fichier : hors machine, ce serait un chemin mort), liste les docs datés
  disponibles ; sans doc : « aucune publication reçue », jamais un tableau vide. Thème clair/sombre selon les règles de
  l'outil (tokens sur `:root`, redéfinis sous `prefers-color-scheme` et `[data-theme]`).

---

## 4. Flux de données — un writer par fichier

| fichier / base | writer unique | lecteurs |
| --- | --- | --- |
| `~/.claude/sessions/<pid>.json` | Claude Code | `tools/pm/snapshot.py` |
| `<data_root>/sessions/<sid>.json` | hooks de CETTE session | `snapshot.py` |
| `<data_root>/pm/BOARD.json`, `ROLES_COUNTS.json`, `alerts.jsonl` | session PM (tick) | backend (lecture), frontend |
| `<data_root>/pm/PILOTAGE.json` | session PM (tick) | skill `/pm` |
| base de l'artefact, collection `pilotage` | session PM (`write_db`) | page artefact |
| `docs/roadmap/PRIORITES_ET_DETTES.md` | commits path-scopés | `pilotage.py` |
| `results/records_graph.json` | `tools/check_record_links.py` | `pilotage.py` |
| cache mémoire du backend | `pilotage_service` (processus backend) | route |

Le backend **n'écrit aucun fichier**. `pilotage.py` **n'écrit aucun fichier**. Chemins de données par `src/paths.py`
(`pm_dir`, `results_file`) ; `data/pm/` et `data/sessions/` restent ignorés par git (lot 0).

---

## 5. Erreurs et modes dégradés — tous visibles

| cas | comportement |
| --- | --- |
| PM jamais lancé (`data/pm/` absent) | `charge.ratio_science_methodo = null`, ligne `aveugle` ; `flotte` reste calculée en direct par le backend (le snapshot ne dépend pas du PM) |
| bulletins absents (lot 0 non fait) | `flotte.aveugle` porte la ligne du board (« bulletins de session ») ; claims et fichiers en vol à vide, MARQUÉS aveugles, pas « 0 » |
| backlog introuvable | `roadmap = null`, ligne `aveugle` |
| `records_graph.json` absent | `roadmap.portes_agi = null`, ligne `aveugle` |
| exception dans `snapshot`/`compute` | 200, `aveugle = ["pilotage: <type>: <msg>"]`, blocs `null` |
| entrée de backlog inanalysable | `statut: illisible`, comptée ; parité de compte assertée |
| clause dont le prédicat lève ou est inconnu | `satisfaite: null`, `raison` |
| chemin cité absent | `existe: false` → rendu barré, non cliquable |
| psutil absent | `flotte.aveugle` (« processus (psutil) »), déjà géré par le board |
| base de l'artefact vide ou illisible | « aucune publication reçue » + date du dernier doc s'il existe |
| backend arrêté | `ErrorState` de React Query (comportement existant des autres vues) |

---

## 6. Tests et calibration

`compute_pilotage` et `parse_roadmap` produisent des affirmations (statut, clause satisfaite, comptes) : ce sont des
instruments, **déclarés `CALIBRATED`** dans `tests/sandbox/test_instrument_calibration.py` que le cliquet les détecte
ou non par motif.

`tests/sandbox/test_pm_pilotage.py` — zéro monde, tout injecté, exemption de bail déclarée :

| forme | cas |
| --- | --- |
| no-op exact | `compute_pilotage(None, None, None, None, None, now)` → cinq lignes `aveugle` (flotte, backlog, records_graph, roles_counts, portes), quatre blocs `null`, aucun `0` ni liste vide dans la sortie |
| injection à dose connue | backlog synthétique de 6 entrées : 2 ouvertes, 1 close, 1 périmée, 1 à clause `path_present` satisfaite (fichier créé dans `tmp_path`), 1 à clause de prédicat inconnu → statuts, `satisfaite` (`true` / `null` + raison), `lignes` et `chemins` EXACTS |
| prédiction | ajouter UNE entrée close au synthétique → `comptes.par_priorite.P2.closes` +1, aucun autre champ ne bouge |
| parité de compte | sur le backlog RÉEL : `len(entrees) == compter_entrees(txt)` et `illisibles == 0` (si une entrée réelle devient illisible, le test la nomme) |
| tête composite | `**P2.0 / P2.1 — …**` → deux entrées, mêmes `lignes` |
| non-duplication | `flotte` == `board.compute(snap, now=now)` (égalité de dict) sur un instantané injecté |
| inventaire des portes | `len(portes) == len(PORTES)` ; pour chaque baseline déclarée : `existe` mesuré, `dette` = taille de la collection déclarée ou `null` |
| `main --json` | n'écrit aucun fichier (répertoire de travail `tmp_path`, listing avant/après identique) |

`tests/test_backend.py` (ajouts) :

| cas | attendu |
| --- | --- |
| `GET /api/pm/pilotage` | 200, `schema == "pilotage_v1"`, `generated_at` numérique |
| service qui lève (monkeypatch de `compute_pilotage`) | 200, `aveugle[0]` commence par `pilotage:`, blocs `null` |
| cache | deux appels sous le TTL → `compute_pilotage` appelé une fois (compteur monkeypatché) |
| **P2.81 sans monkeypatch** | `main.LIVE_PROGRESS_PATH == Path(sandbox_service._arm_live_progress({}, progress_path=None))` — le test qui ne pouvait pas échouer sur le vrai chemin devient un test qui le peut |

Frontend (vitest, `frontend/src/components/pilotage/*.test.tsx`, `frontend/src/api/pm.test.ts`) :
`tabs.test.tsx` mis à jour ; `AveugleBanner` rendu dès qu'une ligne existe et absent sinon ; statut `illisible` rendu ;
lien `vscode://file/` construit depuis `repo_root + rel + ligne` quand `existe`, `<s>` sinon ; `fetchPilotage` appelle
`/api/pm/pilotage`.

Cliquets respectés par construction : porte 12 (aucun littéral `data/` ni `results/` dans `tools/pm/pilotage.py`,
`backend/app/routes/pm.py`, `backend/app/services/pilotage_service.py`), porte 14 (aucune constante sur source vide),
porte 10 (le recensement de tests monte), calibration (déclarations), un writer par fichier.

**Coût mesuré, pas supposé** : après implémentation, mesurer `snapshot()` + `compute_pilotage` sur le backlog réel
(4 200 lignes) et une machine à charge connue ; publier le chiffre dans cette spec (section 11) — c'est lui qui
justifie ou non le TTL de 30 s (E12).

---

## 7. Ordre de livraison — chaque pas utile seul

| # | livrable | où | propriétaire |
| --- | --- | --- | --- |
| 0 | fusion `chantier/pm-roles` → `feat/d1-prod-pairing` ; `.claude/settings.json` sur l'arbre principal ; `data/sessions/`, `data/pm/` ignorés | branche `pm-roles` | session `pm-roles` (ou robla) |
| 1 | `tools/pm/pilotage.py` + `tests/sandbox/test_pm_pilotage.py` + déclarations `CALIBRATED` — utilisable à la main (`python -m tools.pm.pilotage --json`) | **worktree `.worktrees/pilotage`, branche `chantier/pilotage` créée depuis `chantier/pm-roles`** (les imports `tools.pm.*` y existent ; l'arbre partagé n'est pas touché ; rebase sur `feat/d1-prod-pairing` après le lot 0) | moi |
| 2 | service + route + schémas pydantic + tests backend ; correction P2.81 dans `main.py` avec son test sans monkeypatch | idem | moi |
| 3 | famille « Pilotage » (3 vues, bandeau, hook, client, `gen:api`) + tests vitest (`npm ci` dans le worktree) | idem | moi |
| 4 | patch `tick.py` (3 lignes) + pas du skill `/pm` + `tools/pm/artefact/pilotage.html` publié (skill `artifact-capabilities` lu d'abord), URL notée dans `FRONTEND.md` | fichiers de `pm-roles` | pm-roles, ou moi après fusion avec `snapshot`/`verify` |
| 5 | `docs/roadmap/FRONTEND.md` : « Vague K — Pilotage » (état, URL de l'artefact, coût mesuré) | arbre partagé | moi |

Chaque pas : commit path-scopé (`git commit -- <chemins>`), **après accord explicite de robla**, compte d'entité ≥
avant, aucun backtick dans un message de commit, citation et artefact dans le MÊME commit (règle CLAUDE.md du
2026-09-22).

---

## 8. Contraintes du dépôt honorées

Porte 12 (chemins via `src/paths.py`) · porte 14 (`None` et `aveugle`, jamais une constante) · porte 10 (recensement)
· cliquet de calibration (`compute_pilotage`, `parse_roadmap` déclarés) · un writer par fichier · pas de `def run(` au
niveau module dans `tools/pm/` · aucun bail `kuzu` (lecture seule sur le monde, aucune simulation) · pas d'emoji dans
les libellés · Windows : chemins absolus, `/` dans les chemins de `src/paths.py` · règle « citation + artefact dans le
même commit ».

---

## 9. Hors périmètre (YAGNI, décidé le 2026-09-22)

Aucune action depuis le dashboard (lot 2 éventuel : file de demandes lue par le PM) · aucune exécution de porte
depuis l'UI · pas de WebSocket (poll 30 s ; les sessions vivent des heures) · pas de pourcentage d'avancement · pas
d'historique en base côté backend (l'artefact garde les docs datés) · pas de détection des sous-agents de workflow
(périmètre du board, section 10) · pas de refonte des 19 onglets existants.

**Lot 2 « Science » — décidé HORS de ce lot par robla le 2026-09-22, à brainstormer séparément avant toute
implémentation.** Demande d'origine : « la visu de nos arbres en temps réel, les taxonomies, nos runs, la
compréhension, à quoi ils servent, ce qu'on en tire, visuelle de nos avancées ». Ce que ce lot-ci couvre déjà :
worktrees (liste, branche, fusionné, session attachée), runs en vol (bails, processus), portes G0-G4 avec `tested_by`,
comptes datés. Ce qu'il ne couvre PAS, et les sources MESURÉES le 2026-09-22 pour le brainstorm du lot 2 :

- **taxonomie** : `data/agi_taxonomy/capabilities.json`, `demands.json` (arêtes ÉTABLIES), `refuted.json`
  (`tools/check_agi_taxonomy.py:40-43`) — aucune vue ; le frontend a un rendu d3-force réutilisable
  (`ProvenanceGraph`, `TopologyViewer`) ;
- **pipeline** scellée → run → record → arête : 66 `docs/preregistrations/*.json` (`{name, rule, seal}`) ;
  `tools/check_preregistration_applied.py::couverture()` (`:177`) et `familles_sans_record()` (`:193`) ;
- **ce qu'on en tire** : `results/records_graph.json` — 321 nœuds, **131 verdicts**, 454 arêtes ; « le mur a trois
  noms » dans `docs/roadmap/FIL_DIRECTEUR_AGI.md` ;
- **rythme** : records ajoutés par semaine ISO (`git log --diff-filter=A -- docs/EDR` : 13 / 4 / 6 / 3 sur
  S36→S39 2026), fermetures par semaine (dates des têtes d'entrée), commits science / méthodo (`roles_counts`) ;
- **arbres** : avance/retard par branche (`git rev-list --left-right --count feat/d1-prod-pairing...<b>` :
  `pm-roles` 22 / 18, `harness-r1` 7 / 23, `reconcile-d1-main` 0 / 644 — worktree périmé).

---

## 10. À consigner au backlog avec cette spec (preuves du 2026-09-22)

1. **Lot 0 comme prérequis nommé** — `data/sessions/` absent sur l'arbre principal ; `.claude/settings.json` n'existe
   que sur `chantier/pm-roles` (`git show 155b7a0a:.claude/settings.json`) ; `BOARD.md` du 2026-09-22 21:24 : 6
   sessions, 0 claim, 0 fichier. Propriétaire : session `pm-roles`.
2. **Les sous-agents de workflow sont invisibles au registre natif** — `git worktree list` : deux worktrees
   `.claude/worktrees/wf_5a3dc4f2-e4c-{1,2}` verrouillés, aucune entrée dans `~/.claude/sessions/` ; le tableau ne
   peut ni les compter dans la charge ni voir leurs fichiers. Détecteur candidat côté `board` (worktree `wf_*` +
   `locked` → « agents de workflow en vol »). Périmètre `pm-roles`.
3. **P2.81** (déjà inscrite le 2026-09-22) : `backend/app/main.py:68` résout la racine un niveau trop haut ; corrigée
   au pas 2.
4. **Lot 2 « Science » à brainstormer** (section 9) — entrée de rang bas qui porte les sources mesurées ci-dessus et la
   décision de robla ; clause `closes_when:path_present=` sur la spec du lot 2 quand elle existera.
5. **`/api/strategy/strategy_tree` n'a aucun consommateur frontend** (`grep -rln strategy_tree frontend/src/components`
   vide le 2026-09-22) — à confirmer par la porte de parité (onglet Santé) avant de le retirer ou de le brancher ;
   hors périmètre de ce lot.

---

## 11. À vérifier à l'implémentation (faits, pas décisions)

- Le cliquet de calibration détecte-t-il `compute_pilotage` / `parse_roadmap` par motif ? Sinon les déclarer quand même
  (même règle que `board.compute`).
- `gen:api` : `openapi.json` est-il régénéré par un script ou exporté à la main depuis l'app ? (`frontend/package.json`
  ne montre que la conversion `openapi.json -> schema.ts`.)
- `livePoll(30_000)` : vérifier `refetchIntervalInBackground: false` (`frontend/src/lib/polling.ts`) — un onglet en
  arrière-plan ne doit pas recalculer le snapshot toutes les 30 s.
- Coût de `snapshot()` (git log 24 h, `git worktree list`, psutil) sur machine à charge connue → chiffre à publier ici.
- Capacités exactes de l'artefact (`db`, `user`) et forme de `window.claude` : lire le skill `artifact-capabilities`
  avant d'écrire `pilotage.html`.
- `vscode://file/<abs>:<ligne>` : vérifier qu'un chemin Windows (`C:/…`) s'ouvre depuis le navigateur de robla.
