# Spec — Dashboard « Pilotage » AGAGI : une source unique, trois rendus, lecture seule

**Date** : 2026-09-22, **amendée le 2026-09-24 après revue adversariale** (§12 : 29 constats confirmés intégrés, dont
3 bloquants, plus une mesure de coût qui a changé le flux du backend). **Statut** : conception validée par robla en
quatre sections (consommateur « les deux, source unique » ; lecture seule au lot 1 ; approche A ; sections A-B-D-E
approuvées le 2026-09-22), implémentation à planifier. **Lot 0 CLOS** (fusion `79af2944`, 2026-09-23). **Portée** : AGAGI seul. **Dépend de** : la couche PM (spec
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
  "schema": "pilotage_v1",                      # ⚠️ pydantic v2 : `schema` masque un attribut de BaseModel -> alias
                                                # (`Field(alias="schema")`) ou le modèle émet un UserWarning
  "generated_at": <epoch s>,
  "repo_root": <str>,                           # POSIX, casse d'origine : find_repo_root(None).as_posix() —
                                                # "C:/Users/robla/VScode_Project/AGAGI". C'est CELUI-CI que les liens
                                                # vscode consomment, jamais `flotte.repo_root` (que le board normalise
                                                # en minuscules : "c:/users/robla/vscode_project/agagi")
  "aveugle": [<str>, ...],                      # une ligne par source absente ou par erreur nommée

  "flotte": null | { ... },                     # DEUX provenances, JAMAIS confondues (3.2) : le contenu de BOARD.json
                                                # (chemin du poll, écrit par le tick avec json.dump(default=str) — donc
                                                # un aller-retour JSON, pas le dict) ou board.compute(snap) en mémoire
                                                # (chemin ?frais=1). Ses clés sont le CONTRAT du board, figé par
                                                # tests/sandbox/test_pm_board.py, jamais réénumérées ici. Lu à la pointe
                                                # 6977912a : generated_at, repo_root, aveugle, sessions, sessions_mortes,
                                                # alertes (A1-A9), charge_connue {sims_en_vol, cpu_pct, bails_vivants},
                                                # worktrees, bails

  "roadmap": null | {
    "direction": {"rangs": [{"rang": "14 ter", "p_items": ["P2.78"], "statuts": ["close"]}, ...]},
                                                # rang -> LISTE : un rang n'est pas unique (5 rangs portés par deux
                                                # entrées à HEAD 79af2944), donc ce n'est pas une fonction.
                                                # ORDRE : (int(base), index du suffixe dans ["", "bis", "ter",
                                                # "quater", "quinquies"]) — un tri de CHAÎNES mettrait "14 quater"
                                                # avant "14 ter" et "10" avant "2", rendant la vue centrale illisible
    "entrees": [{                               # ORDRE : `bloc` croissant, puis ordre des `nums` de la tête
        "num": "P2.78",                         # UN numéro par entrée
        "nums": ["P2.78"],                      # tous les numéros de la TÊTE dont vient l'entrée (composite : 2+)
        "bloc": 43,                             # index du bloc (tête) d'origine — deux entrées d'une composite le partagent
        "priorite": "P2", "rang": "14 ter" | null,
        "statut": "ouverte" | "close" | "perimee" | "illisible",
        "date": "2026-09-22" | null,            # première date des DEUX premières lignes ; c'est la date du STATUT, pas
                                                # de l'ouverture (15 têtes en portent plusieurs, 10 aucune)
        "titre": <str>,                         # règle en 3.1 ; markdown TEL QUEL, aucune troncature dans le JSON
        "lignes": [671, 697],                   # 1-based, [début de la tête, dernière ligne AVANT la tête suivante]
        "clause": null | {"pred": "grep_present", "arg": "...", "satisfaite": true | false | null, "raison": null | <str>},
        "holds": [{"pred": "grep_present", "arg": "...", "satisfaite": true | false | null}, ...],   # `holds_when` : 8
                                                # entrées en portent ; une affirmation PERMANENTE rompue est un fait, pas
                                                # une fermeture — jamais confondue avec `clause`
        "chemins": [{"rel": "tools/cost_guard.py", "existe": true, "ligne": n | null}, ...],
        "chemins_non_captes": n                 # fragments backtickés contenant "/" que le motif n'a PAS pris (voir 3.1) :
                                                # une liste amputée ne se présente jamais comme complète
    }, ...],
    "comptes": {"par_priorite": {"P0": {"ouvertes": n, "closes": n, "perimees": n}, ...},
                "blocs": n, "numeros": n, "illisibles": n},   # DEUX comptes : têtes et numéros (égaux sans composite)
    "portes_agi": <records_graph["roadmap"] tel quel>          # {"G0": {"sdr", "status", "tested_by": [...]}, ...}
  },

  "portes": null | [{                           # ORDRE : int(num) croissant — PAS l'ordre du fichier, PAS un tri de
                                                # chaînes ; les numéros sont NON CONTIGUS (ni 19 ni 20) et le hook
                                                # écrit le bloc 21 AVANT le bloc 18
    "num": "1",                                 # chaîne, extraite du hook par `^#\s*(\d+)\.` en tête de bloc
    "module": "tools.check_record_links",       # premier `python tools/check_(\w+)\.py` du bloc, dédupliqué (un bloc
                                                # peut lancer son check DEUX fois : --only puis complet)
    "titre": <str> | null, "temoins": [<str>, ...] | null,
    "mutations": n | null,                      # null = porte branchée au hook mais ABSENTE de PORTES (non mutée)
    "baseline": null | {"chemin": "tools/record_link_baseline.json", "existe": true, "dette": n | null}
  }, ...],

  "charge": null | {
    "sims_en_vol": n | null, "cpu_pct": x | null, "bails_vivants": [...] | null,     # noms du board, jamais renommés
    "flotte_age_s": x | null,                   # âge du BOARD.json servi (section 3.2) — jamais une flotte muette
    "ratio_science_methodo": x | null, "fichiers": {"science", "methodo", "autre"} | null,
    "fenetre": {"depuis": "2026-08-24", "jours": 30} | null    # la VRAIE fenêtre du ratio (glissante), pas `depuis`
  }
}
```

Règles du schéma :

- `flotte` est la sortie de `board.compute` **sans transformation** (test de non-duplication, section 6) ; ses propres
  lignes `aveugle` sont recopiées dans le `aveugle` de tête, préfixées `flotte:`.
- **La parité de compte porte sur les BLOCS, pas sur les entrées** : `assert comptes["blocs"] == compter_entrees(txt)`
  (`tools/check_backlog_freshness.py:373`, signature `compter_entrees(txt=None)` — il compte des LIGNES de tête, donc
  une tête composite `P2.0 / P2.1` vaut **1**). Les entrées sont dupliquées par numéro **après** l'assertion, d'où
  `comptes["numeros"] >= comptes["blocs"]`. Écrire l'assertion sur les entrées la ferait lever au premier composite —
  et `compute_pilotage` tomberait alors dans le `except` du service : **tout le pilotage deviendrait aveugle à cause
  d'une seule tête**. (Mesuré le 2026-09-24 : 123 blocs = 123 numéros sur disque, **aucune tête composite** — la
  contradiction serait restée invisible jusqu'au premier `P2.0 / P2.1`.)
- Une entrée inanalysable est `illisible`, jamais absente.
- `portes` est recomputé **depuis le hook** (`tools/hooks/pre-commit`, même motif que
  `check_synthesis_counts._portes_hook`, qui publie `count:portes_hook` dans CLAUDE.md), puis **joint** à
  `check_gate_mutation.PORTES` pour les titres, témoins et mutations. `PORTES` n'est PAS l'inventaire des gardes :
  c'est la table des portes MUTÉES. Mesuré le 2026-09-24 : **18 scripts `check_*` au hook, 16 clés dans `PORTES`** —
  `check_staged_authorship` (porte 7) et `check_gate_mutation` (porte 15, le cliquet des cliquets) en sont absents.
  Une porte du hook hors `PORTES` porte `mutations: null`, jamais 0. Aucun nombre n'est écrit en dur.
- `charge` fusionne `flotte.charge_connue` (champs repris SOUS LEURS NOMS du board) et `ROLES_COUNTS.json` ; chaque
  champ est `null` si sa source manque. **`fenetre` (glissante, 30 j) est la fenêtre du ratio ; la clé `depuis` de
  `ROLES_COUNTS.json` est la constante `DEBUT` (début du rôle PM) et ne doit jamais être servie comme fenêtre** —
  sinon le ratio est attribué à une période qui n'est pas la sienne (`tools/pm/roles_counts.py`, `DEBUT` +
  `fenetre: {depuis, jours}`). L'unité du ratio est le **fichier modifié**, pas le commit.

### 2.3 « Avancement » : trois lectures

1. **La direction 🧭** : les rangs tranchés et le statut réel de chacun — « où on en est de ce qu'on a décidé ».
   Compte mesuré par la règle retenue, à HEAD `79af2944` le 2026-09-24 : **31 têtes portent un rang, 26 rangs
   distincts**, dont **5 rangs portés par deux entrées** (rang 1 → P1.6 et P2.73 ; rang 4 → P4.4 et P4.17 ; rang 6 →
   P2.59 et P4.12 ; rang 9 → P2.60 et P4.14 ; rang 14 → deux entrées). Un rang n'est donc **pas** une clé : la
   direction est une liste par rang. *(Le « 19 » de la première rédaction n'était reproductible par aucune lecture —
   il est retiré, pas corrigé.)*
2. **Les portes G0-G4** (`records_graph.roadmap`) : statut, SDR, records qui les testent.
3. **Le rythme** : ouvertes / closes / périmées par priorité, ratio science/méthodo et sa fenêtre glissante — datés.

---

## 3. Composants

### 3.1 `tools/pm/pilotage.py` — nouveau, n'écrit jamais rien

**Lecteurs** (chacun rend `None` si la source est absente ou illisible, jamais une valeur par défaut) :

| fonction | source | chemin |
| --- | --- | --- |
| `read_backlog(repo_root)` | texte du backlog | `<root>/docs/roadmap/PRIORITES_ET_DETTES.md` |
| `read_records_graph(repo_root)` | graphe de records | `paths.results_file("records_graph.json")` — **jamais le littéral `results/…`** (porte 12) |
| `read_roles_counts(repo_root)` | compteurs du PM | `paths.pm_dir("ROLES_COUNTS.json")` |
| `read_portes(repo_root)` | inventaire des portes | `tools/hooks/pre-commit` (source d'autorité), joint à `check_gate_mutation.PORTES` et à `BASELINES` |

**`read_portes` — extraction déclarée, parce que `_portes_hook` ne suffit pas.** `check_synthesis_counts._portes_hook`
rend `len(set(...))` : un COMPTE, sans numéro ni ordre. La spec déclare donc l'extraction : le numéro par
`^#\s*(\d+)\.` en tête de bloc de commentaire, le module par le **premier** `python tools/check_(\w+)\.py` du bloc
(dédupliqué : un bloc lance parfois son check deux fois, `--only` puis complet — `tools/hooks/pre-commit:22,24` et
`:55,57`), la liste triée par `int(num)`. Mesuré le 2026-09-24 : **19 modules distincts, 19 blocs numérotés dans
l'ordre 1..17 puis 21 puis 18** — les numéros ne sont **ni contigus** (pas de 19 ni 20) **ni dans l'ordre du fichier**.
Cas de calibration : un hook FACTICE portant un bloc dont le numéro et l'ordre divergent.

⚠️ **La racine du dépôt ne peut pas venir de `find_repo_root` seul.** `tools/parity_check.py:44-47` essaie
`Path.cwd()` **en premier** : un backend (ou un `python -m`) lancé depuis un autre dépôt — ou n'importe quel répertoire
portant `.git` — rend CE répertoire. Mesuré le 2026-09-24 depuis un `git init` jetable : la fonction rend le répertoire
jetable, pas AGAGI. Le pilotage deviendrait alors entièrement aveugle **en accusant les bons fichiers d'être absents** :
le négatif FABRIQUÉ que le principe 3 interdit. Deux règles, les deux exigées : (a) la racine s'ancre sur le MODULE
(`Path(__file__).resolve().parents[2]` depuis `tools/pm/pilotage.py`), `find_repo_root` en repli seulement ;
(b) **garde de santé déclarée** — si la racine retenue ne porte pas `docs/roadmap/PRIORITES_ET_DETTES.md` ET
`tools/hooks/pre-commit`, la sortie porte une ligne `aveugle` qui **NOMME la racine résolue**, jamais un « fichier
absent ». Contre-exemple gelé : un cwd étranger portant `.git`.

⚠️ **Les accesseurs de `src/paths.py` rendent un chemin RELATIF quand aucune variable d'environnement n'est posée**
(mesuré le 2026-09-24, environnement nettoyé : `paths.results_file("records_graph.json")` → `results/records_graph.json`,
`paths.pm_dir("BOARD.json")` → `data/pm/BOARD.json`, `os.path.isabs` → `False`). Un chemin relatif dépend du répertoire
courant du processus — celui d'`uvicorn` n'est pas garanti. Chaque lecteur **ancre donc explicitement** :
`os.path.join(repo_root, chemin)` quand le chemin rendu est relatif, `repo_root` venant de `find_repo_root`. C'est
l'indirection de la porte 12 PLUS l'ancrage, jamais l'un sans l'autre.

**`BASELINES`** : table déclarée dans le module — **mapping EXPLICITE `module -> (fichier de baseline, clé de la
collection qui compte la dette ou None)`**, parce qu'il n'est pas dérivable du nom du module
(`tools.check_record_links` → `record_link_baseline.json`, sans « s »). Baselines existantes au 2026-09-24
(`ls tools/*baseline*.json`, 13 fichiers) : `agi_taxonomy`, `backlog_freshness` (clé `legataires`), `bar_separation`,
`calibration_reach`, `control_family`, `data_paths` (clé `fichiers`), `fabricated_defaults`, `guard_negative_cases`,
`instrument_calibration`, `io_overlap`, `record_link`, `substrate_pinning`, `test_census`. Seules `backlog_freshness`
et `data_paths` ont une clé de dette déclarée (leur forme a été lue) ; les autres portent `dette: null` jusqu'à ce
qu'un auteur DÉCLARE la clé — on ne proxifie pas ce qu'on n'a pas lu. `existe` est mesuré à chaque appel. Une porte du
hook sans entrée dans `BASELINES` porte `baseline: null`.

**`parse_roadmap(txt, repo_root, now, evaluer_clause=_evalue_clause) -> dict`** — réutilise le cliquet, n'invente
aucun regex d'entrée :

- bornes des BLOCS : `_ENTREE.finditer(txt)` (`tools/check_backlog_freshness.py:91`, même objet que `_entrees`) ;
  numéros de ligne = comptage des `\n` avant l'offset de début et de fin ;
- `nums` = groupe 1 de `_TETE` (`:59`) découpé sur `/` ; **le bloc est l'unité de la parité** (règle du §2.2), et une
  entrée est émise par numéro APRÈS l'assertion, toutes portant le même `bloc` et les mêmes `lignes` ;
- `priorite` = préfixe avant le point ; `rang` = regex `—\s*rang\s+(\d+(?:\s+(?:bis|ter|quater|quinquies))?)` sur les
  **deux premières lignes** (même fenêtre que le statut : deux entrées portent leur rang sur la 2ᵉ ligne, P4.15 et
  P4.9), `null` sinon. ⚠️ Sans `quinquies`, « rang 4 quinquies » (P4.17) serait **tronqué en `4`** et entrerait en
  collision silencieuse avec le rang 4 de P4.4 ; le suffixe est capté ou le rang est `null`, jamais tronqué ;
- `date` = première `\d{4}-\d{2}-\d{2}` des deux premières lignes, `null` sinon. **C'est la date du STATUT** (« CLOSE le
  2026-09-15 », « mesurée le 2026-09-16 »), pas celle de l'ouverture : mesuré sur le backlog réel, **15 têtes portent
  plus d'une date** et **10 n'en portent aucune**. Le champ est descriptif ; aucune lecture du lot 1 n'en dépend, et un
  calcul de « fermetures par semaine » est du lot 2, qui devra alors se donner une règle plus fine ;
- `titre` = la ligne de tête **privée de** `**`, des numéros, du marqueur de statut, du rang et de la date ; le markdown
  restant est laissé **TEL QUEL** et rendu en texte, jamais interprété ; **aucune troncature dans le JSON** (la
  troncature est CSS, le titre complet reste accessible). Mesuré : le titre le plus long fait **566 caractères** et
  17 853 octets de titres au total — une troncature à l'aveugle couperait au milieu d'un lien markdown (cas réel :
  la tête de P3.7 porte un lien vers un ADR). Cas de calibration : une tête coupée au milieu d'un lien → titre complet,
  aucun markdown fermé d'office ;
- `lignes` = **1-based**, `[première ligne de la tête, dernière ligne AVANT la tête suivante]` — attention, les bornes
  de `_entrees` vont du début d'un bloc au **début du bloc suivant** (`check_backlog_freshness.py:100`), donc la borne
  haute brute désigne la tête d'à côté : on retire 1. Contre-exemple gelé : la dernière ligne d'une entrée ne doit
  jamais être la tête de la suivante ;
- `statut` : `perimee` si `PÉRIMÉE` ou `CADUQUE` dans les deux premières lignes ; sinon `close` si l'un des
  `_CLOSE_MARQUEURS` (`:92`) y figure — même règle que le cliquet ; sinon `ouverte` ;
- `clause` : `_CLAUSE.findall(bloc)` (`:82`) ; la première clause est évaluée par `evaluer_clause` ; une exception
  donne `satisfaite: null, raison: <str(exc)>` ; plusieurs clauses → la première est évaluée, les autres listées dans
  `raison`.
  ⚠️ **`_evalue_clause` ne prend AUCUNE racine et ignore donc `repo_root`** : `path_present`/`path_absent` passent par
  `_existe(rel)` qui joint au `_ROOT` du module (le dépôt où vit `check_backlog_freshness.py`, calculé à l'import) et
  exigent en plus que le fichier soit **SUIVI par git** ; `grep_*` lit le même `_ROOT` — et sous `GIT_INDEX_FILE`
  (pendant un commit) tout est jugé dans l'INDEX. Conséquences écrites une fois pour toutes : (a) `satisfaite` est
  toujours jugé contre le dépôt du module, jamais contre `repo_root` ; (b) `repo_root` ne gouverne que
  `chemins[].existe` ; (c) un fichier créé dans un `tmp_path` ne peut **jamais** rendre `true` (chemin relatif →
  `false` ; chemin absolu → `null` + « existe ICI mais n'est PAS SUIVI par git ») — d'où le paramètre `evaluer_clause`
  injectable, qui est ce que la calibration utilise (§6) ;
- `chemins` : `_BACKTICK_PATH.findall(bloc)` (`:61`) filtrés sur `"/" in c` (même filtre que
  `tools/pm/snapshot.py::read_backlog_paths`), `existe` = `os.path.exists(join(repo_root, rel))`.
  ⚠️ **Ce motif TRONQUE, et il faut le DIRE plutôt que l'élargir en douce** : il n'admet que cinq extensions
  (`py|md|json|yml|yaml`) et refuse un chemin commençant par un point (`[\w]` initial). Mesuré le 2026-09-24 sur le
  backlog : **364 fragments backtickés contiennent un `/`, 201 sont captés, 163 sont INVISIBLES** — dont
  `.github/workflows/ci.yml`, `.claude/worktrees/…`, et `tools/hooks/pre-commit` (sans extension, cité **7 fois**).
  Présenter cette liste comme complète serait la forme (c) du registre — un motif qui tronque en silence — appliquée à
  l'instrument qui affiche les preuves. Donc : `chemins_non_captes` compte les fragments non pris, et la vue écrit
  « 5 chemins affichés, 3 non reconnus par le motif ». Élargir le motif est un changement du CLIQUET, hors de ce lot :
  il ne se fait pas dans un dashboard.
- `ligne` d'un chemin : `null` par défaut. Le numéro de ligne du champ `lignes` est une position dans le BACKLOG, jamais
  dans le fichier cité (mesuré : `tools/cost_guard.py` fait 139 lignes, l'entrée qui le cite commence ligne 671) — l'y
  appliquer ouvrirait au-delà de la fin du fichier. Un `ligne` non nul n'est rempli que si la citation porte elle-même
  un suffixe `:n` ou `::symbole` résolu par grep ;
- toute exception dans le traitement d'UN bloc → une entrée `statut: "illisible"`, `titre` = première ligne brute, le
  reste `null` ; la fonction termine par `assert comptes["blocs"] == compter_entrees(txt)` (§2.2).

**`compute_pilotage(snap, backlog_txt, records_graph, roles_counts, portes, now) -> dict`** — pure ; appelle
`board.compute(snap, now=now)` si `snap` n'est pas `None` ; assemble le schéma 2.2.

**`main(argv)`** : `--json` imprime le résultat (indent 1, `ensure_ascii=False`), `--repo-root` optionnel ; **aucune
écriture de fichier**. Nommage : pas de `def run(` au niveau module (collision connue du cliquet de calibration).

### 3.2 Backend

⚠️ **Mesure qui change le flux (2026-09-24, charge notée : 40 % CPU au départ, 9 processus python, arbre principal)** :
`tools.pm.snapshot.snapshot(repo_root)` coûte **15,6 / 16,6 / 18,1 s** (aucune source `None`), dont `read_processes`
≈ 9 s, `read_recent_commits` ≈ 4 s, `read_worktrees` ≈ 2 s, `read_cpu_pct` ≈ 1 s (plancher imposé par
`psutil.cpu_percent(interval=1.0)`) — tandis que **toute la roadmap coûte 0,70 s** (123 blocs ; découpe 5 ms ;
57 clauses évaluées à 12 ms pièce, chacune lançant un `git`). Deux conséquences dirimantes : le timeout par défaut
d'`apiFetch` est de **10 s** (`frontend/src/api/client.ts:23`) — la requête expirerait côté client ; et un poll de 30 s
ferait tourner git + psutil en permanence, c'est-à-dire la charge machine que la règle E12 du dépôt interdit
(« un seul run lourd à la fois ; noter la charge au départ de chaque cellule »). **Le backend ne recalcule donc pas
la flotte.**

- `backend/app/services/pilotage_service.py`, racine par la règle du §3.1 (ancrage sur le module + garde de santé) :
  - **flotte = lecture de `paths.pm_dir("BOARD.json")`** (ancré sur la racine), le cache écrit par le tick PM dont il
    est l'unique writer. ⚠️ Ce fichier est écrit par `json.dump(..., default=str)` (`tools/pm/tick.py:100`), donc **ce
    qui est servi est un ALLER-RETOUR JSON, pas le dict de `board.compute`** : `default=str` stringifie en silence tout
    objet non sérialisable. Le §6 en tire deux tests distincts au lieu d'un. Absent → `flotte: null` + ligne
    `aveugle: "flotte: data/pm/BOARD.json absent — le tick PM n'a pas encore tourné"`. Une flotte vieille est servie
    AVEC son âge, jamais muette. Sa fraîcheur est donc celle du tick (20-30 min), et c'est écrit dans la vue.
  - **`charge.flotte_age_s = now - flotte["generated_at"]`**, et `null` si la clé manque — **jamais le `mtime` du
    fichier** : un `git checkout`, une copie ou une écriture interrompue donne un mtime frais sur un contenu périmé, et
    la vue annoncerait une fraîcheur supposée, ce que le §5 interdit. Contre-exemple gelé : un `BOARD.json` dont le
    mtime et le `generated_at` diffèrent de plusieurs minutes — le seul cas qui distingue les deux règles.
  - **roadmap, portes, charge** : recalculés à la demande, cache mémoire `(généré_à, dict)`, `ttl_s=30.0` — 0,70 s
    mesuré, tenable.
  - `get_pilotage(ttl_s=30.0, frais=False)` : `frais=True` recalcule la flotte par `snapshot()` + `board.compute`
    **en mémoire** (rien n'est écrit : `BOARD.json` reste au PM). Coût annoncé 16-18 s, donc jamais sur le chemin du
    poll ; la route le porte en `?frais=1`.
  - Toute exception → dict `pilotage_v1` dont `aveugle = ["pilotage: <type>: <msg>"]` et les quatre blocs `null`
    (jamais 500, jamais silencieux).
- `backend/app/routes/pm.py` : `GET /pilotage` (monté `prefix="/api/pm"`, `tags=["pm"]`), paramètre `frais: bool = False`.
  **Pas de `response_model` strict sur `flotte`** : le contrat du board évolue chez son propriétaire, et un
  `response_model` qui refuse une clé neuve lèverait un 500 **hors** du `try/except` du service — une seconde source
  d'erreur que la §5 ne couvrirait pas. Le modèle pydantic (`backend/app/schemas.py`) type donc `schema`,
  `generated_at`, `repo_root`, `aveugle`, `roadmap`, `portes`, `charge`, et déclare `flotte: dict | None`. ⚠️ À
  vérifier au pas 2 : `openapi-typescript` rend `{[key: string]: unknown}` pour un `dict[str, Any]`, donc les champs
  typés doivent être des modèles nommés là où le frontend en a besoin (entrées de roadmap, portes, charge) — sinon les
  types générés ne servent à rien.
- **Types générés, chaîne réelle** (mesurée, la §11 ne pose plus la question) : `tools/dump_openapi.py` écrit
  `frontend/openapi.json` depuis `app.openapi()`, `make api-types` enchaîne le dump et `npm run gen:api`, et la CI
  (`.github/workflows/ci.yml:164-168`) régénère les deux puis exige `git diff --exit-code`. **`openapi.json` et
  `schema.ts` sont donc régénérés et committés dans le MÊME commit que la route** (pas 2), sinon la CI rougit.
- `backend/app/main.py` : `include_router(pm_router, prefix="/api/pm", tags=["pm"])` ; **et correction de P2.81** :
  `RESULTS_DIR = find_repo_root(None) / "results"` (l.68) — voir section 10.
- La porte de parité (`tools/parity_check`, exposée par `/api/health/parity`) signale tout endpoint non consommé : le
  nouveau l'est par 3.3.

### 3.3 Frontend — famille « Pilotage »

- `frontend/src/tabs.ts` : `TAB_KEYS` gagne `"flotte" | "roadmap" | "portes"` ; `TAB_FAMILIES` gagne
  `{ family: "Pilotage", tabs: [Flotte, Roadmap, Portes] }` (icônes lucide : `Users`, **`MapIcon`** — jamais `Map`, qui
  masquerait le global JavaScript dans ce module —, `ShieldCheck`). `frontend/src/tabs.test.tsx:7` est **générique**
  (`items.map(id) === TAB_KEYS`) : il passe sans modification si les clés sont ajoutées en fin de `TAB_KEYS` et la
  famille en fin de `TAB_FAMILIES` ; il n'y a donc rien à « mettre à jour » mais **une assertion à AJOUTER** (groupe
  `Pilotage`, libellés, icônes présentes) — sans elle, la famille n'est couverte par aucun témoin.
- `frontend/src/App.tsx` : trois `lazy()` (l.12-31) et trois branches dans la suite de `{tab === "…" && <Vue/>}`
  (l.74-102 — ce n'est pas un `switch`) ; `showSidebar` (l.36) reste faux pour ces onglets. Le `lazy()` par vue suit la
  convention (20 vues lazy) et n'ajoute aucune dépendance lourde : J5 est respecté sans action.
- `frontend/src/api/queryKeys.ts` : `pm: { pilotage: ["pm", "pilotage"] as const }`.
- `frontend/src/api/pm.ts` : `fetchPilotage(frais = false)` appelant **`apiFetch<PilotageV1>("/api/pm/pilotage")` avec
  le chemin LITTÉRAL** dans un fichier non-test — c'est la seule forme que la porte de parité reconnaît comme
  consommation (`tools/parity_check.py:189` : le littéral doit être le premier argument direct, ni constante ni
  variable, et les `*.test.ts(x)` sont exclus). Type `PilotageV1` depuis `schema.ts` (généré) avec un alias local.
- **Pas de hook dédié** : la convention du dépôt est `useQuery` **inline dans chaque vue** avec la MÊME `queryKey`
  (React Query déduplique), comme les trois composants sandbox ; les options communes vivent dans
  `frontend/src/lib/polling.ts` — on y ajoute `PILOTAGE_POLL` sur le modèle de `STATUS_POLL`
  (`refetchInterval: 30_000`, `staleTime: 5_000`, `refetchIntervalInBackground: false` — `livePoll` ne sonde déjà pas
  en arrière-plan, `polling.ts:11-19`). Une seule requête réseau, trois consommateurs.
- `frontend/src/components/pilotage/AveugleBanner.tsx` : rend la liste `aveugle` en tête, jamais masqué s'il y a une
  ligne. Deux natures, deux rôles (convention J3) : `role="status" aria-live="polite"` pour une source absente,
  `role="alert"` pour une ligne commençant par `pilotage:` (exception du service).
- **États obligatoires par vue** (Definition of Done de `FRONTEND.md`, et la §5 interdit le tableau muet) :
  `isLoading → <Loading/>`, `error → <ErrorState onRetry={refetch}/>`, **bloc `null` → `<Empty message=…/>` dont le
  message reprend la ligne `aveugle` correspondante** — jamais une table vide.
- `frontend/src/components/pilotage/PilotageFlotteView.tsx` : `Stat` × 4 (sims en vol, CPU instantané — 1 s, pas une
  moyenne —, bails, **âge de la flotte**), table des sessions (nom, branche, P-items revendiqués / inférés, nombre de
  fichiers en vol, âge du heartbeat), alertes en liste avec `Badge` (`danger` pour `alerte`, `warning` pour `info`) et
  preuve dépliable (`<details>`).
  ⚠️ **`Stat` REFUSE `null`** : sa signature est `value: string | number` (`frontend/src/components/ui/Stat.tsx:1-4`) et
  `tsconfig` est `strict` — vérifié par `tsc` sur `value={sims}` avec `sims: number | null` : `error TS2322`. Or les
  trois champs de charge sont `n | null` par construction (porte 14). **Tranché : la conversion se fait dans la vue,
  pas dans la primitive** — une valeur absente est rendue `"non mesuré"` (chaîne littérale, lisible par un lecteur
  d'écran), jamais `0`, jamais un tiret nu. `Stat` n'est pas modifié. Cas vitest : une `charge` à champs `null` rend
  quatre `Stat` portant « non mesuré » et aucun zéro.
  Bouton « recalculer la flotte (≈ 20 s, charge la machine) » → `?frais=1`, **désactivé** quand le dernier tableau
  annonce `sims_en_vol > 0` (règle : un seul run lourd à la fois).
  ⚠️ **Ce chemin expirerait par construction** : `apiFetch` a un `timeoutMs` par défaut de **10 s**
  (`frontend/src/api/client.ts:23`) alors que le recalcul mesure 15,6-18,1 s. L'appel `frais` passe donc
  `apiFetch(..., { timeoutMs: 40_000 })` — marge sur le majorant — et la vue distingue `isFetching` (recalcul en cours :
  les données du cache restent affichées AVEC leur âge et un indicateur) de `isLoading` (aucune donnée). Cas vitest :
  le `timeoutMs` transmis est > 18 000.
- `frontend/src/components/pilotage/PilotageRoadmapView.tsx` : direction (table rang → **liste** de P-items → statuts) ;
  cartes G0-G4 (`Panel` : statut, SDR, records) ; table des entrées avec filtres priorité et statut (`Field`), colonne
  clause en `Badge` — **`success` satisfaite / `warning` non / `purple` invérifiable** (la primitive n'a que
  `teal | success | danger | warning | purple`, pas de `neutral`, et pas de prop `title` : `variant="neutral"` ferait
  échouer `tsc`, donc `npm run build`) —, la raison en **texte visible** (`text-dim`), jamais dans un `title`
  (inatteignable au clavier, J3). **Deux liens, deux gabarits LITTÉRAUX** : l'entrée elle-même →
  `vscode://file/C:/Users/robla/VScode_Project/AGAGI/docs/roadmap/PRIORITES_ET_DETTES.md:671` (avec `lignes[0]`) ; un
  chemin cité → `vscode://file/C:/Users/robla/VScode_Project/AGAGI/tools/cost_guard.py`, **sans ligne** sauf si
  `ligne` est non nul (la ligne du champ `lignes` est une position dans le BACKLOG : l'appliquer au fichier cité
  ouvrirait au-delà de sa fin). Les deux se bâtissent sur le `repo_root` **DE TÊTE**, en POSIX — jamais
  `flotte.repo_root` (minuscules) : un antislash dans un `href` est encodé `%5C` et VS Code ne le résout pas. Chaque
  lien porte `aria-label="ouvrir … dans VS Code"`. Un chemin absent est rendu `<s>chemin</s>
  <span class="text-dim">(absent)</span>`, non cliquable — le style seul ne dit rien à un lecteur d'écran. Sous la
  table, si `chemins_non_captes > 0` : « n chemin(s) cité(s) non reconnu(s) par le motif du cliquet », pour qu'une liste
  amputée ne se présente jamais comme complète. `Stat` ouvertes / closes / périmées par priorité, datés de
  `generated_at`.
- `frontend/src/components/pilotage/PilotagePortesView.tsx` : table (n°, module, titre, témoins, mutations, baseline,
  dette) ; phrase fixe en tête : « inventaire recomputé depuis le hook pre-commit, joint à check_gate_mutation.PORTES
  pour les mutations — aucune porte n'est exécutée d'ici ».
- Primitives existantes : `Panel`, `Stat({label, value})`, `Badge({variant, children})`, `Empty({message, action})`,
  `Loading`, `ErrorState`, `Field` (`frontend/src/components/ui/`). **Une seule addition de style assumée** :
  `a:focus-visible, summary:focus-visible` dans le bloc `frontend/src/styles.css:553` (mêmes tokens) — les règles
  actuelles ne couvrent que `.btn`, `.tab`, les champs, `textarea`, `.checkbox-inline input`, `.toast-dismiss`, et
  cette famille introduit les deux premiers `<a>`/`<details>` interactifs du dépôt. Thème : tokens CSS existants ;
  `aria-label` sur les tables. Aucun emoji dans les libellés (règle utilisateur).

### 3.4 Tick PM et page artefact

- `tools/pm/tick.py` (fichier de la session `pm-roles`) : après l'écriture de `BOARD.json`, écrire
  `paths.pm_dir("PILOTAGE.json")` = `compute_pilotage(...)` avec le même `snap` (≈ 3 lignes : import, appel, dump).
  Patch proposé au propriétaire ; ou appliqué par moi après le lot 0 avec `check_staged_authorship.snapshot`/`verify`.
- Skill `/pm` (`.claude/skills/pm/SKILL.md`, même propriétaire) : un pas supplémentaire — si `PILOTAGE.json` a changé
  depuis le tick précédent, publier vers l'artefact : `Artifact write_db` (`db_op: set`, `collection: pilotage`,
  `doc_id: latest`, `file_path: <data_root>/pm/PILOTAGE.json`) puis un second `set` avec `doc_id: <AAAA-MM-JJ-HHMM>`.
  Le PM est l'unique writer de cette base ; personne d'autre ne la touche.
  ⚠️ **Taille MESURÉE et rétention déclarée** — le document construit sur l'état réel (127 blocs, 269 chemins,
  `portes_agi` complet) pèse **87 411 octets à `indent=1`** (67 839 compacts) pour la seule roadmap, plus 7 039 octets
  de `BOARD.json` : **≈ 94 Ko par version**, dont 17,9 Ko de titres. À deux documents par tick et un tick toutes les
  20-30 min, la croissance est non bornée. Règles : (i) publier le doc daté **une fois par jour** (le premier tick du
  jour), pas à chaque tick ; (ii) le tick PM — unique writer — **supprime** les docs datés au-delà des **30 derniers** ;
  (iii) `latest` est toujours réécrit. Si une limite du store refuse un document (les limites par document et par
  collection sont à lire AVANT le premier `write_db`, même passe que les règles d'accès), le tick écrit l'échec dans son
  digest et la page affiche la dernière version reçue avec sa date — jamais une page vide sans explication.
- Page : `tools/pm/artefact/pilotage.html`, versionnée, **publiée la première fois par la session PM** (celle qui tient
  le bail `pm` : c'est elle qui déclare les capacités et qui republie ensuite ; aucune autre session ne publie cette
  page), favicon fixé à la création, **URL notée dans `docs/roadmap/FRONTEND.md`** — c'est là que les ticks suivants la
  relisent. Capacités déclarées après lecture du skill `artifact-capabilities` (a minima `db`). ⚠️ **À trancher au pas 4
  avec ce skill en main** : une capacité `db` nue laisse, d'après un constat NON VÉRIFIÉ de la revue (§12), tout viewer
  de niveau `interact` écrire les documents partagés — l'unicité du writer ne serait alors pas garantie par le store
  mais seulement par convention. Vérifier les règles d'accès avant la première publication, et restreindre l'écriture
  au propriétaire si le store le permet. Elle lit `pilotage/latest`, rend les
  quatre blocs en texte (aucun lien de fichier : hors machine, ce serait un chemin mort), liste les docs datés
  disponibles ; sans doc : « aucune publication reçue », jamais un tableau vide. Thème clair/sombre selon les règles de
  l'outil (tokens sur `:root`, redéfinis sous `prefers-color-scheme` et `[data-theme]`).

---

## 4. Flux de données — un writer par fichier

| fichier / base | writer unique | lecteurs |
| --- | --- | --- |
| `~/.claude/sessions/<pid>.json` | Claude Code | `tools/pm/snapshot.py` |
| `<data_root>/sessions/<sid>.json` | hooks de CETTE session | `snapshot.py` |
| `<data_root>/pm/BOARD.json`, `ROLES_COUNTS.json`, `alerts.jsonl` | session PM (tick) | backend (**la flotte servie EST ce fichier**, §3.2), frontend |
| `<data_root>/pm/PILOTAGE.json` | session PM (tick) | skill `/pm` |
| base de l'artefact, collection `pilotage` | session PM (`write_db`) | page artefact |
| `docs/roadmap/PRIORITES_ET_DETTES.md` | commits path-scopés | `pilotage.py` |
| `results/records_graph.json` | `tools/consolidate_records.py` (le seul writer — `check_record_links.py` ne l'écrit pas, il le VÉRIFIE) | `pilotage.py` |
| cache mémoire du backend | `pilotage_service` (processus backend) | route |

Le backend **n'écrit aucun fichier**. `pilotage.py` **n'écrit aucun fichier**. Chemins de données par `src/paths.py`
(`pm_dir`, `results_file`), **ancrés sur `repo_root`** (§3.1 : sans variable d'environnement ces accesseurs rendent du
relatif). `data/pm/` et `data/sessions/` sont ignorés par git (`.gitignore:51-52`, vérifié le 2026-09-24 par
`git check-ignore -v` **après** la fusion du lot 0 — un constat de la revue les disait « ni suivis ni ignorés », ce qui
était vrai avant la fusion et ne l'est plus).

---

## 5. Erreurs et modes dégradés — tous visibles

| cas | comportement |
| --- | --- |
| PM jamais lancé (`BOARD.json` absent) | `flotte = null` + ligne `aveugle` nommant le fichier et le remède (lancer le tick) ; `charge.ratio_science_methodo = null` + sa ligne. La flotte n'est PAS recalculée en douce : le coût interdit de le faire sur le chemin du poll (§3.2) |
| `BOARD.json` vieux | servi TEL QUEL avec `charge.flotte_age_s` ; la vue affiche l'âge. Jamais de tableau muet, jamais de fraîcheur supposée |
| bulletins absents | `flotte.aveugle` porte la ligne du board (« bulletins de session ») ; claims et fichiers en vol à vide, MARQUÉS aveugles, pas « 0 » |
| backlog introuvable | `roadmap = null`, ligne `aveugle` |
| `records_graph.json` absent | `roadmap.portes_agi = null`, ligne `aveugle` |
| exception dans un lecteur ou dans `compute_pilotage` | 200, `aveugle = ["pilotage: <type>: <msg>"]`, blocs `null` (et `role="alert"` côté vue) |
| `?frais=1` pendant qu'une simulation est en vol | le bouton est désactivé côté vue ; côté API la réponse porte une ligne `aveugle` disant que le recalcul a été refusé (charge) — refus DIT, jamais silencieux |
| entrée de backlog inanalysable | `statut: illisible`, comptée ; parité assertée sur les BLOCS (§2.2) |
| clause dont le prédicat lève ou est inconnu | `satisfaite: null`, `raison` |
| chemin cité absent | `existe: false` → `<s>` + « (absent) », non cliquable |
| psutil absent | `flotte.aveugle` (« processus (psutil) »), déjà géré par le board |
| base de l'artefact vide ou illisible | « aucune publication reçue » + date du dernier doc s'il existe |
| backend arrêté | `ErrorState` de React Query (comportement existant des autres vues) |
| un bloc `null` alors que la réponse est 200 | `<Empty/>` par vue, message = la ligne `aveugle` correspondante (Definition of Done) |

---

## 6. Tests et calibration

`compute_pilotage` et `parse_roadmap` produisent des affirmations (statut, clause satisfaite, comptes) : ce sont des
instruments, **déclarés `CALIBRATED`** dans `tests/sandbox/test_instrument_calibration.py`.

⚠️ **Mais le cliquet ne les DÉTECTE pas, et une déclaration non détectée est ignorée EN SILENCE** (branche
« déclaration périmée », `tools/check_instrument_calibration.py:249`). Mesuré le 2026-09-24 : aucun de ses **14 motifs**
ne capte `compute_*` ni `parse_*` (les motifs couvrent `*verdict*`, `measure*`, `run_*`, `classify*`, `benchmark*`,
`assert_*`, `compare*`, `sweep*`, `probe*`, `learn*`…). Écrire « déclarés CALIBRATED que le cliquet les détecte ou non »
serait donc une règle sans application exécutable (E10). Ce que la spec engage à la place : la déclaration est écrite
(elle documente), **la garantie vient des cas qui TOURNENT en CI** (job `suite-complete`, par répertoire), et
l'élargissement du cliquet est chiffré et inscrit au backlog — **7 fonctions non déjà captées** par un motif
`compute_*`/`parse_*` (dont `tools/pm/roles_counts.py::compute_counts`, un instrument du PM aujourd'hui hors
périmètre), 5 autres `compute_*_verdict` étant déjà prises par le motif `*verdict*`. Coût d'élargissement connu avant
décision, comme le dépôt l'exige.

`tests/sandbox/test_pm_pilotage.py` — zéro monde, tout injecté, exemption de bail déclarée :

| forme | cas |
| --- | --- |
| no-op exact | `compute_pilotage(None, None, None, None, None, now)` → cinq lignes `aveugle` (flotte, backlog, records_graph, roles_counts, portes), quatre blocs `null`, aucun `0` ni liste vide dans la sortie |
| injection à dose connue | backlog synthétique de 6 entrées : 2 ouvertes, 1 close, 1 périmée, 1 à clause satisfaite, 1 à clause de prédicat inconnu → statuts, `satisfaite`, `lignes` et `chemins` EXACTS. **La clause passe par un `evaluer_clause` FACTICE** (§3.1 : `_evalue_clause` juge contre le dépôt du module et exige un fichier suivi par git, donc un `tmp_path` ne peut jamais rendre `true`) |
| clause réelle, réponse connue | un cas NON factice sur le dépôt : `grep_present=tools/cost_guard.py::process_time` → `true` ; un chemin absent → `false` ; un chemin absolu hors dépôt → `null` + raison « pas suivi par git ». C'est le contrôle positif de la couche d'évaluation |
| prédiction | ajouter UNE entrée close au synthétique → `comptes.par_priorite.P2.closes` +1, aucun autre champ ne bouge |
| parité de compte | sur le backlog RÉEL : `comptes["blocs"] == compter_entrees(txt)` et `illisibles == 0` (si une entrée réelle devient illisible, le test la nomme) |
| tête composite | `**P2.0 / P2.1 — …**` → **1 bloc et 2 entrées**, mêmes `lignes`, `nums` de longueur 2, et l'assertion de parité ne lève PAS (c'est le contre-exemple du défaut bloquant trouvé en revue) |
| rang | `rang 4 quinquies` n'est pas tronqué en `4` ; un rang porté par deux entrées donne une seule ligne de direction avec deux `p_items` ; un rang sur la 2ᵉ ligne est capté |
| non-duplication, chemin `?frais=1` | `flotte` == `board.compute(snap, now=now)` (égalité de dict) sur un instantané injecté |
| non-duplication, chemin SERVI | après aller-retour JSON d'un `BOARD.json` factice : `set(flotte) == set(board.compute(snap))` et les valeurs scalaires égales. Contre-exemple gelé : un champ que `json.dump(default=str)` transforme (un objet non sérialisable) — le test doit le NOMMER, pas l'avaler |
| âge de la flotte | `BOARD.json` dont le `mtime` et le `generated_at` diffèrent de plusieurs minutes → `flotte_age_s` suit `generated_at` ; clé absente → `null` |
| racine étrangère | cwd dans un dépôt jetable (`git init`) → ligne `aveugle` NOMMANT la racine résolue, aucun « fichier absent » |
| chemins tronqués par le motif | une entrée citant `.github/workflows/ci.yml` et `tools/hooks/pre-commit` → `chemins` ne les porte pas ET `chemins_non_captes == 2` |
| ordres | `rangs` triés par (base, suffixe) : `14 ter` AVANT `14 quater`, `2` AVANT `10` ; `entrees` dans l'ordre du backlog |
| titre | une tête coupée au milieu d'un lien markdown → titre complet, markdown inchangé, aucune troncature |
| inventaire des portes | `len(portes)` == nombre de scripts `check_*` du hook (recomputé, **pas** `len(PORTES)`) ; une porte du hook hors `PORTES` → `mutations: null` ; pour chaque baseline déclarée : `existe` mesuré, `dette` = taille de la collection déclarée ou `null` |
| fenêtre du ratio | `charge.fenetre` == `roles_counts["fenetre"]` et **jamais** `roles_counts["depuis"]` (contre-exemple : un `ROLES_COUNTS.json` dont les deux diffèrent) |
| ancrage des chemins | environnement sans `AGAGI_*`, cwd ≠ dépôt → les lecteurs trouvent quand même leurs fichiers (contre-exemple du relatif, §3.1) |
| `main --json` | n'écrit aucun fichier (répertoire de travail `tmp_path`, listing avant/après identique) |

`tests/test_backend.py` (ajouts) :

| cas | attendu |
| --- | --- |
| `GET /api/pm/pilotage` | 200, `schema == "pilotage_v1"`, `generated_at` numérique |
| service qui lève (monkeypatch de `compute_pilotage`) | 200, `aveugle[0]` commence par `pilotage:`, blocs `null` |
| cache | deux appels sous le TTL → les lecteurs appelés une fois (compteur monkeypatché) |
| flotte absente | `BOARD.json` pointé vers un `tmp_path` vide → `flotte: null` + ligne `aveugle`, 200 |
| flotte servie avec son âge | `BOARD.json` factice daté → `charge.flotte_age_s` ≈ l'âge attendu (±1 s) |
| poll sans recalcul | une requête SANS `frais=1` n'appelle jamais `snapshot` (monkeypatch qui lève si appelé) — c'est la garde du coût mesuré en §3.2 |
| **P2.81, sans effet de bord** | `main.LIVE_PROGRESS_PATH == Path(sandbox_service.PROJECT_ROOT) / "results" / "live_progress.jsonl"`. ⚠️ **Ne PAS appeler `_arm_live_progress(env, None)` dans un test** : il fait `os.makedirs` puis `open(path, "w")` sur le VRAI `<dépôt>/results/live_progress.jsonl` — il TRONQUERAIT le puits de progression d'un run en vol, et un test deviendrait un writer d'un fichier partagé (l'inverse de ce que cette spec défend). Correctif propre au pas 2 : extraire de `sandbox_service` un helper PUR `default_live_progress_path()` utilisé par `_arm_live_progress` ET par le test |

Frontend (vitest, `frontend/src/components/pilotage/*.test.tsx`, `frontend/src/api/pm.test.ts`) : `tabs.test.tsx`
**étendu d'une assertion** sur la famille Pilotage (groupe, libellés, icônes) — l'assertion existante est générique et
passerait sans rien voir ; `AveugleBanner` rendu dès qu'une ligne existe, absent sinon, `role="alert"` pour une ligne
`pilotage:` ; statut `illisible` rendu ; **un cas par vue avec son bloc à `null` → `Empty`, jamais de table vide** ;
lien `vscode://file/` construit depuis `repo_root + rel + ligne` quand `existe`, `<s>` + « (absent) » sinon ;
`fetchPilotage` appelle `/api/pm/pilotage` ; bouton `?frais=1` désactivé quand `sims_en_vol > 0`.

Cliquets respectés par construction : porte 12 (aucun littéral `data/` ni `results/` dans `tools/pm/pilotage.py`,
`backend/app/routes/pm.py`, `backend/app/services/pilotage_service.py`), porte 14 (aucune constante sur source vide),
porte 10 (le recensement de tests monte), un writer par fichier. Porte de parité : le chemin littéral est dans
`frontend/src/api/pm.ts` (§3.3).

**Coût — MESURÉ le 2026-09-24, pas supposé** (charge notée : 40 % CPU, 9 processus python ; arbre principal,
HEAD `79af2944`) : `snapshot()` **15,6 / 16,6 / 18,1 s** ; roadmap complète **0,70 s** (123 blocs, 57 clauses à 12 ms,
découpe 5 ms, `compter_entrees` 8 ms). Ces deux chiffres sont ce qui a fait renoncer au recalcul de la flotte dans la
requête (§3.2) ; ce sont des MAJORANTS (machine partagée). À re-mesurer machine au repos avant de discuter le TTL, et à
publier ici avec la charge du moment.

**Chemin SERVI — MESURÉ le 2026-09-24** (worktree `chantier/pilotage`, HEAD `31785f77` ; charge NOTÉE avant
chaque passe, machine sous forte charge PARTAGÉE tout du long) : `get_pilotage()` (le poll — jamais
`snapshot()`) rend, à cache FROID (`_vider_cache()` avant chaque appel), **2,64 s** (cpu_percent(1) 97,6 %,
12 processus python), **7,84 s** (84,5 %, 16 processus) puis **8,96 s** (83,0 %, 16 processus) sur trois passes
indépendantes, et **< 10 µs** à cache CHAUD dans les trois cas — 2 aveuglements, `schema` `pilotage_v1`,
131 blocs de roadmap, 19 portes, stables sur les trois passes ; cohérent avec le 4,07 s relevé côté endpoint
`GET /api/pm/pilotage` (premier appel HTTP, cache vide). ⚠️ La VARIANCE est le fait à retenir, pas la
meilleure passe : sous charge partagée la marge tombe à **1,04 s** sous le timeout client de 10 s (passe à
8,96 s), loin du « plus de 3× » qu'une première mesure isolée aurait suggéré — à re-mesurer machine au repos
avant de fixer une marge de confiance, et publier l'unité SOUS CHARGE à côté de l'unité LIBRE (classe E12
appliquée au coût, cf. CLAUDE.md).

---

## 7. Ordre de livraison — chaque pas utile seul

| # | livrable | où | propriétaire |
| --- | --- | --- | --- |
| 0 | **FAIT le 2026-09-23** : fusion `chantier/pm-roles` → `feat/d1-prod-pairing` (`79af2944`, poussée) — `tools/pm/{snapshot,board,bulletin,alerts,roles_counts,tick}.py`, `paths.sessions_dir`/`pm_dir`, `docs/roadmap/ROLES.md`, porte 21, 119 tests ; `.gitignore:51-52` porte `data/sessions/` et `data/pm/` ; `src/paths.py` est l'UNION attendue (`proposals_root` de d1 ET `sessions_dir`/`pm_dir` du PM — le conflit annoncé par la revue a été résolu dans la fusion, vérifié le 2026-09-24) | arbre principal | session `pm-roles` |
| 1 | `tools/pm/pilotage.py` + `tests/sandbox/test_pm_pilotage.py` + déclaration `CALIBRATED` — utilisable à la main (`python -m tools.pm.pilotage --json`) | **worktree `.claude/worktrees/pilotage`** (chemin COURT : sous Windows, un worktree sous `.worktrees/` + des noms de records longs dépasse 260 caractères et `git worktree add` échoue), branche `chantier/pilotage` depuis `feat/d1-prod-pairing` (le lot 0 y est) | moi |
| 2 | service + route + schémas pydantic + tests backend ; correction P2.81 dans `main.py` (+ helper pur `default_live_progress_path`) et son test SANS effet de bord ; **`make api-types` dans le MÊME commit** (`openapi.json` + `schema.ts`, sinon la CI rougit) | idem | moi |
| 3 | famille « Pilotage » (3 vues, bandeau, `PILOTAGE_POLL`, client, assertion de `tabs.test.tsx`, `a:focus-visible`/`summary:focus-visible`) + tests vitest (`npm ci` dans le worktree) | idem | moi |
| 4 | patch `tick.py` (3 lignes) + pas du skill `/pm` + `tools/pm/artefact/pilotage.html` publié (skill `artifact-capabilities` lu d'abord), URL notée dans `FRONTEND.md` | fichiers de `pm-roles` | pm-roles, ou moi après fusion avec `snapshot`/`verify` |
| 5 | `docs/roadmap/FRONTEND.md` : « Vague K — Pilotage » (état, URL de l'artefact, coût mesuré) | arbre partagé | moi |

Chaque pas : commit path-scopé (`git commit -- <chemins>`), **après accord explicite de robla**, compte d'entité ≥
avant, aucun backtick dans un message de commit, citation et artefact dans le MÊME commit (règle CLAUDE.md du
2026-09-22).

---

## 8. Contraintes du dépôt honorées

Porte 12 (chemins via `src/paths.py`, **plus l'ancrage sur `repo_root`** : l'indirection seule rend du relatif) ·
porte 14 (`None` et `aveugle`, jamais une constante) · porte 10 (recensement) · cliquet de calibration (déclaration
écrite, détection impossible aujourd'hui — dit en §6, élargissement chiffré en §10) · un writer par fichier (le backend
et `pilotage.py` n'écrivent rien ; un TEST non plus — cf. P2.81) · pas de `def run(` au niveau module dans `tools/pm/` ·
aucun bail `kuzu` (lecture seule sur le monde, aucune simulation) · **E12 : le coût est mesuré à charge notée et il a
changé le design** (§3.2) · pas d'emoji dans les libellés · Windows : chemins absolus, `/` dans les chemins de
`src/paths.py`, worktree à chemin COURT · règle « citation + artefact dans le même commit ».

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

## 10. À consigner au backlog avec cette spec (preuves du 2026-09-22, revérifiées le 2026-09-24)

1. **Lot 0 — CLOS le 2026-09-23** par la fusion `79af2944` (§7). L'entrée n'a pas lieu d'être créée : le prérequis est
   satisfait. *(État d'origine, conservé comme mesure : `data/sessions/` absent de l'arbre principal,
   `.claude/settings.json` seulement sur `chantier/pm-roles`, `BOARD.md` du 22 à 21:24 = 6 sessions / 0 claim /
   0 fichier.)*
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
6. **Élargissement du cliquet de calibration aux motifs `compute_*` / `parse_*`, coût CHIFFRÉ avant décision** — aucun
   des 14 motifs de `tools/check_instrument_calibration.py` ne les capte, et une déclaration non détectée est ignorée
   en silence (`:249`). Dette nette d'un élargissement, mesurée le 2026-09-24 : **7 fonctions** non déjà captées —
   `tools/pm/roles_counts.py::compute_counts`, `tools/compositional_transfer_probe.py::compute_transfer`,
   `tools/cartography.py::parse_territories`, `tools/consolidate_records.py::parse_record`,
   `src/visualization.py::compute_genome_layers`, `src/graph_rag/reflexive_supervisor.py::compute_trend`,
   `src/metaprog/rsi_loop.py::parse_demand_response` (les cinq `compute_*_verdict` sont déjà pris par le motif
   `*verdict*`). C'est le 7ᵉ angle mort de nommage de ce cliquet, et il rendrait détectables les instruments de cette
   spec.

---

## 11. À vérifier à l'implémentation (faits, pas décisions)

Les quatre points que la première rédaction posait en questions sont **tranchés par une mesure** et vivent désormais
dans le corps de la spec : la chaîne `openapi.json`/`schema.ts` et son drift-gate CI (§3.2), `livePoll` qui ne sonde pas
en arrière-plan (§3.3), le coût de `snapshot()` et de la roadmap (§3.2 et §6), la non-détection de `compute_*`/`parse_*`
par le cliquet (§6 et §10.6). Restent :

- Capacités exactes de l'artefact (`db`, `user`), forme de `window.claude`, **et surtout qui peut ÉCRIRE la base** :
  lire le skill `artifact-capabilities` avant la première publication (§3.4).
- `vscode://file/<abs>:<ligne>` : vérifier qu'un chemin Windows (`C:/…`) s'ouvre depuis le navigateur de robla.
- `openapi-typescript` sur un `dict[str, Any]` : confirmer au pas 2 que les champs consommés par le frontend sont des
  modèles NOMMÉS (sinon `{[key: string]: unknown}` et les types générés ne servent à rien).
- Re-mesurer `snapshot()` machine au repos (les 15,6-18,1 s sont un majorant) — le chiffre ne change pas le design, il
  borne le coût de `?frais=1`.

---

## 12. Revue adversariale — ce qu'elle a trouvé, et ce qu'elle n'a PAS couvert

Passe du 2026-09-23/24 : cinq lentilles indépendantes qui lancent leurs propres sondes (faits de code, doctrine,
faisabilité, complétude, conventions frontend), puis trois juges par constat (reproduire la preuve / importance /
exactitude de la correction), majorité requise. Coût : 288 agents lancés, **11,4 M de tokens**, 1 134 appels d'outils.

**Intégré dans cette spec : 29 constats confirmés** (13 faits de code, 11 frontend, 5 doctrine), dont **3 défauts
bloquants** — chacun trouvé indépendamment par deux lentilles :

1. la parité de compte contredisait la règle des têtes composites (le test de §6 aurait fait lever `parse_roadmap`, et
   le service aurait rendu TOUT le pilotage aveugle) ;
2. `_evalue_clause` ignore `repo_root`, juge contre le dépôt du module et exige un fichier suivi par git — le cas de
   calibration prévu était infaisable ;
3. `Badge variant="neutral"` n'existe pas (ni la prop `title`) : `tsc` aurait cassé `npm run build`.

Plus une mesure qui a changé le flux : `snapshot()` coûte 15,6-18,1 s, au-delà du timeout de 10 s d'`apiFetch` — la
flotte n'est plus recalculée dans la requête (§3.2).

**Passe 2 (2026-09-24) — le trou de la première passe est FERMÉ.** Les lentilles **faisabilité** et **complétude**
(40 constats) avaient rendu leurs rapports sans qu'aucun de leurs 120 juges ne survive à la limite de session. Ils ont
été rejugés contre la spec AMENDÉE, trois juges chacun (reproduire / déjà-corrigé / importance) : **30 réfutés ou déjà
corrigés** — donc l'intégration de la passe 1 avait bien absorbé tous leurs bloquants et importants — et **10 retenus,
tous mineurs**, tous intégrés ci-dessus (conventions de `titre`, `date` et `lignes` ; borne d'extension de
`_BACKTICK_PATH` ; `Stat` face à `null` ; ordre des candidats de `find_repo_root` ; forme du lien `vscode://` ; limites
du store ; `schema` sous pydantic v2 ; forme de l'exemption de bail). Coût : 121 agents, 9,7 M de tokens.

**Critique de complétude final** — un agent chargé de la seule question « qu'est-ce qui manque pour implémenter sans
poser de question ? » a trouvé **17 manques, dont 3 BLOQUANTS que ni la passe 1 ni la passe 2 n'avaient vus**, chacun
avec sa sonde :

1. **`Stat` refuse ce que la spec lui demande** — `value: string | number`, `tsc` strict, erreur `TS2322` sur un `null`
   mesurée. C'est le bloquant n°3 (Badge) répété sur une AUTRE primitive : la leçon n'avait pas été généralisée.
   Tranché en §3.3 (conversion dans la vue, « non mesuré »).
2. **`?frais=1` expirerait par construction** — la mesure de `snapshot()` (18 s) avait changé le poll mais pas le seul
   chemin qui la paie encore : `apiFetch` coupe à 10 s. Tranché en §3.3 (`timeoutMs: 40_000`, `isFetching`).
3. **`portes[].num` et l'ordre ne sont pas dérivables de la source déclarée** — `_portes_hook` rend un COMPTE ;
   la numérotation du hook n'est ni contiguë ni dans l'ordre du fichier. Tranché en §3.1 (motif d'extraction déclaré).

Les neuf manques « importants » sont intégrés aux mêmes sections : deux définitions incompatibles de `flotte` (dict vs
fichier écrit avec `default=str`), `flotte_age_s` sans source (mtime vs `generated_at`), `find_repo_root` qui essaie le
cwd d'abord, deux formes contradictoires de `repo_root`, le `<ligne>` du lien vscode qui n'existait pas, 163 chemins
cités invisibles sur 364, la taille non bornée des documents publiés (94 Ko/version mesurés), l'absence d'ordre de tri,
la règle de `titre`.

**Ce qui reste non vérifié, dit plutôt que tu** : les règles d'ACCÈS du store de l'artefact (qui peut écrire sous une
capacité `db` nue) et la forme exacte des types générés depuis un `dict[str, Any]` — les deux sont nommés en §3.4 et
§11, à trancher au pas 2 et au pas 4 avec le skill `artifact-capabilities` en main. Aucun ne bloque le pas 1.
