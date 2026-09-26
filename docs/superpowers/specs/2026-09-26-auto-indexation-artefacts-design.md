# Spec — Auto-indexation des artefacts (P2.87) et lot 2 « Science » du dashboard (P2.84)

**Date** : 2026-09-26. **Statut** : v2, AMENDÉE par une revue adversariale opus le jour même (§12 : 3 bloquants,
14 importants, 7 mineurs, tous intégrés). Conception issue d'un brainstorm remis à Master 2 ; approche A retenue
(« lecteur tolérant à la lecture ») avec quatre conditions (§1). **APPROUVÉE par Master 2 le 2026-09-26 ; décisions
D1-D3 tranchées (§9, qui fait foi sur les sections précédentes là où D1 les déplace).** Prochaine étape : le plan.
**Portée** : AGAGI seul. **Dépend de** : le lot 1 du dashboard (`docs/superpowers/specs/2026-09-22-pilotage-dashboard-design.md`,
pas 1-5 livrés, `5d534d44`). **Ne ferme rien** : les clauses de P2.87 et P2.84 sont repointées sur le CODE qu'elles
attendent (§11), jamais sur ce document.

**Provenance** : chiffres mesurés le 2026-09-26 sur HEAD `5d534d44` (worktree `.worktrees/front`), commande citée.

---

## 0. Ce qu'on construit, et pourquoi

Le lot 1 lit des sources EXISTANTES une par une, chacune avec son lecteur écrit à la main. robla a demandé l'inverse
(P2.87) : que **produire un artefact suffise à l'indexer**, et, séparément (P2.84), « la visu de nos arbres, les
taxonomies, nos runs, à quoi ils servent, ce qu'on en tire ». Ce lot livre les deux, dans cet ordre : un **index** des
artefacts du dépôt, puis trois vues « Science » construites SUR cet index et sur des sources déjà publiées.

**Familles mesurées** (`glob` sur HEAD) :

| famille | motif | fichiers | ce qui est déclaré aujourd'hui | date disponible |
| --- | --- | --- | --- | --- |
| record | `docs/EDR/*.md` | 305 (+ `README.md`) | frontmatter YAML imposé par la porte 1 (34 EDR légataires sans frontmatter) ; `verdict` sur 139 | **aucune publiée** : 0 `date:` en frontmatter, 0 nom daté |
| adr | `docs/ADR/*.md` | 5 | frontmatter | non |
| ref | `docs/REF/*.md` | 20 (+ `README.md`) | frontmatter (11 sans `status`) | non |
| sdr | `docs/SDR/*.md` | 5 | frontmatter (portes G0-G4) | non |
| resultat | `results/*.json` | 105 (dont `records_graph.json`, dérivé) | 26 portent `regime`/`_regime` ; clé racine `verdict` sur 18 (14 dict, 4 chaînes) ; 1 racine de type liste | variable |
| preinscription | `docs/preregistrations/*.json` | 71 | `{name, rule, seal}` | non |
| spec | `docs/superpowers/specs/*.md` | 130 | aucun frontmatter | nom `AAAA-MM-JJ-…` : 130/130 |
| plan | `docs/superpowers/plans/*.md` | 124 | aucun frontmatter | nom daté : 124/124 |
| revue | `docs/reviews/*.md` | 1 (+ `README.md`) | — | nom daté : 1/1 |

**Date d'entrée dans le dépôt** — commande (§3.1, figée) sur les répertoires de la table :
`git log --no-renames --diff-filter=A --format=%x1e%ct --name-only -- <répertoires>` → 787 chemins, **305/305 EDR
datés**, 0,15-0,19 s (charge 73,7 % sur 1 s) ; avec `-M` (renommages détectés) : 294/305, les 11 manquants étant des
fichiers RENOMMÉS. C'est la **seule** source de date des records : aucune source publiée n'en porte (D1, §9).

---

## 1. Principes (dont les quatre conditions de Master 2)

1. **Lecture seule, un writer par fichier.** L'indexeur, `compute_science` et les vues n'écrivent rien ; rien n'est
   demandé aux auteurs d'artefacts (approche A : l'indexation se fait à la LECTURE).
2. **Le lecteur tolérant ne FABRIQUE jamais un état** (condition 2). Un champ n'est rempli que depuis ce que le
   fichier DÉCLARE (frontmatter brut, clé JSON, premier titre `# ` d'un `.md` non-record, préfixe daté d'un nom par
   convention de famille). Tout champ introuvable vaut `null` ET il est compté, par famille et par champ, avec une
   raison tirée d'un **vocabulaire fermé** (§3.1). Jamais une valeur par défaut (porte 14), jamais un titre tiré du
   nom de fichier, jamais un `status: open` que personne n'a écrit, jamais une date de repli.
3. **Couverture du format déclaré publiée par famille et PAR CLÉ, sans pression implicite** (condition 3). Un
   compte, jamais une note, un seuil ou une couleur d'alerte ; aucune porte n'en naît sans une mesure et une décision.
4. **Une famille neuve = une ligne de la table `FAMILLES`.** Trois formes de lecture seulement (§3.1) ; une forme
   inconnue est un ajout de code, dit comme tel. Ce que l'index ne voit pas est PUBLIÉ (`hors_familles`, §3.1).
5. **Aucune vue ne recalcule un verdict ni n'écrit une tendance** (condition 4) : vue 3 = des comptes par semaine,
   jamais « s'accélère » / « ralentit » ; vue 2 = arêtes réfutées visibles, distinctes, avec ce qui les a dépassées.
6. **Tout import backend vers `tools/` tourne dans l'IMAGE docker** (leçon `b7a06d87`, condition 4) : `tools/` et
   `docs/` y sont des volumes `:ro` sous `/app`, `results/` et `data/` des volumes que le backend ne touche pas ;
   `backend/requirements.txt` est la seule liste de dépendances. Une source qui ne s'y trouve pas est NOMMÉE comme
   absente, jamais comptée zéro (B2).
7. **Deux dates, jamais confondues** : `date_declaree` (frontmatter `date:`, clé JSON `date`, ou nom daté selon la
   famille) et `date_ajout_git` (§3.1). Une vue qui compte par semaine NOMME la date qu'elle utilise.
8. **Refus locaux, jamais globaux** (I10) : une famille qui rompt sa parité devient `null` avec une ligne ; un
   artefact au type inattendu voit ses champs normalisés à `null` et comptés — jamais tout l'index aveuglé par un fichier.

---

## 2. Architecture

```text
fichiers (globs de FAMILLES, ancrés sur la racine via src/paths.py)     git (si le dépôt répond ET n'est pas superficiel)
        │                                                                         │
        ▼                                                                         ▼
indexer(racine, dates_git=lire_dates_git(racine), suivis=lire_suivis(racine)) -> index_v1                 [PUR hors lecteurs]
        │
        ├─ backend  GET /api/pm/index    (cache 60 s, n'écrit rien)  ──► onglet « Index » (famille Pilotage)
        │
        └─ compute_science(index, taxonomie, preinscriptions, records_graph, now) -> science_v1                 [PUR]
                 │    (index lu dans le MÊME cache que /api/pm/index — jamais recalculé deux fois)
                 └─ backend  GET /api/pm/science  (cache 60 s)  ──► famille « Science » : Pipeline, Taxonomie, Trouvailles
```

Pas de tick PM : l'index coûte peu (§6), le backend le calcule à la demande avec le filet de `/api/pm/pilotage` (mode
dégradé nommé, jamais 500, chaque bloc validé contre son modèle AVANT la route).

---

## 3. Composants

### 3.1 `tools/pm/index_artefacts.py` — l'index (P2.87)

**Table déclarée `FAMILLES`**, dans cet ordre (l'ordre de sortie) :

| nom | racine (ancrée) | motif | forme | exclus déclarés | `date_declaree` |
| --- | --- | --- | --- | --- | --- |
| `record` | `<racine>/docs/EDR` | `*.md` | `md_frontmatter` | `README.md` | frontmatter `date:` |
| `adr` | `<racine>/docs/ADR` | `*.md` | `md_frontmatter` | — | frontmatter `date:` |
| `ref` | `<racine>/docs/REF` | `*.md` | `md_frontmatter` | `README.md` | frontmatter `date:` |
| `sdr` | `<racine>/docs/SDR` | `*.md` | `md_frontmatter` | — | frontmatter `date:` |
| `resultat` | `paths.results_root()` ancré | `*.json` | `json` | `records_graph.json` (dérivé par `consolidate_records`) | clé racine `date` |
| `preinscription` | `<racine>/docs/preregistrations` | `*.json` | `json` | — | clé racine `date` |
| `spec` | `<racine>/docs/superpowers/specs` | `*.md` | `md` | — | préfixe `AAAA-MM-JJ-` du nom |
| `plan` | `<racine>/docs/superpowers/plans` | `*.md` | `md` | — | préfixe du nom |
| `revue` | `<racine>/docs/reviews` | `*.md` | `md` | `README.md` | préfixe du nom |

Les répertoires passent par `src/paths.py` quand un accesseur existe (`results_root()`), ancrés sur la racine s'ils
sont relatifs (règle du lot 1, §3.1) — aucun littéral `results/` ni `data/` dans le module (porte 12, I5). Les exclus
sont PUBLIÉS par famille (`exclus: [...]`), jamais retirés en silence.

**Trois formes de lecture, et rien d'autre.**

- **Lecteur de frontmatter brut, partagé** : `tools/consolidate_records.py` gagne `lire_frontmatter(texte) -> dict |
  None` (le bloc `---` en tête, `yaml.safe_load`), que `parse_record` appelle désormais — **comportement de
  `parse_record` inchangé**, vérifié par ses tests existants et par un témoin d'équivalence sur les 335 records réels.
  Il LÈVE sur un YAML invalide (`YAMLError`, et `ValueError` d'une date impossible comme `2026-13-45`) et sur une
  racine non-dict ; il rend `None` sans bloc. `parse_record`, lui, garde ses défauts — ce sont ceux de la porte 1, pas
  ceux de l'index : **l'index n'utilise JAMAIS `parse_record`** (B1 : il fabrique titre et `status: open`). Import
  PARESSEUX dans le lecteur (I4) : PyYAML absent n'aveugle que les formes à frontmatter, avec une ligne.
- `md_frontmatter` (records) : champs pris dans le frontmatter BRUT seulement — `titre` = `title` (chaîne),
  `etat` = `verdict` si chaîne, sinon `status` si chaîne, `etat_source` = `"verdict" | "status" | null` (M5),
  `date_declaree` = `date:` (`datetime.date` → ISO ; chaîne `AAAA-MM-JJ` validée), `liens` = toutes les clés de
  `consolidate_records._LIST_KEYS` (I11 : 496 arêtes, dont les rétractations), `gate`. Pas de frontmatter →
  artefact indexé, champs `null`, raison `frontmatter_absent` (les 34 légataires et `README.md` exclu à part).
- `md` (spec, plan, revue) : `titre` = premier titre `# ` hors bloc de code ; `date_declaree` = préfixe daté du nom
  (validé : `2026-13-45` → `null`, raison `nom_date_invalide`) ; frontmatter OPTIONNEL par le lecteur partagé
  (`type`, `date`, `sujet`, `etat`, `liens` — §3.3), dont `date:` l'emporte sur le nom et le dit (`date_source`).
- `json` (resultat, preinscription) : `titre` = clé `name` sinon `title` (chaîne) ; `etat` = clé `etat` sinon
  `verdict` (chaîne), `etat_source` publié (I7 b) ; `regime` = présence de `regime`/`_regime` ; `scelle` = présence
  de `seal` (préinscriptions seulement, `null` = non applicable ailleurs — I7 a) ; racine non-objet → artefact
  indexé, champs `null`, raison `racine_non_objet` (M2) ; JSON invalide → ILLISIBLE.

**Vocabulaire FERMÉ des raisons** (I12) — `illisible` : `encodage_invalide`, `fichier_vide`, `json_invalide`,
`frontmatter_yaml_invalide`, `frontmatter_non_dict`, `pyyaml_absent`. Champ introuvable : `frontmatter_absent`,
`cle_absente`, `type_inattendu`, `racine_non_objet`, `titre_md_absent`, `nom_non_date`, `nom_date_invalide`,
`date_invalide`. Date git : `git_indisponible`, `historique_tronque`, `hors_depot`, `non_suivi`, `sans_ajout_trouve`.
Une raison hors vocabulaire est un défaut de code (un témoin énumère les raisons produites).

**`lire_dates_git(racine) -> (dict | None, raison | None)`** (B3, I1, I2) :
- environnement par `tools.check_evidence_provenance._env_pour(racine)` (règle à deux faces : isole pour un dépôt
  tiers, hérite pour le dépôt courant) ; refus (`None`, `git_indisponible`) si git est absent ou muet, ou si
  `git rev-parse --show-toplevel` ne rend pas la racine (dépôt extérieur par fuite de `GIT_DIR`) ;
- **clone superficiel** (`git rev-parse --is-shallow-repository` = `true`) → `None`, `historique_tronque` : un
  `--depth 1` date les 305 EDR du jour du clone (sondé) — deux jobs CI sur trois clonent ainsi ;
- commande FIGÉE, jamais la config héritée : `git -c diff.renames=false log --no-renames --diff-filter=A
  --format=%x1e%ct --name-only -- <répertoires relatifs de FAMILLES>` ; pour un chemin ajouté plusieurs fois (21
  sondés), la date retenue est la PLUS ANCIENNE (dernière occurrence d'une sortie antichronologique) ; `%ct`
  (date d'entrée dans la branche) ; jour et semaine ISO calculés en **UTC** ;
- sémantique publiée telle quelle : **« date d'entrée du CHEMIN actuel dans le dépôt »** — un renommage est une
  entrée (305/305 datés) ; la vue le dit ;
- un fichier de la famille non suivi (`lire_suivis` : `git ls-files -z -- <répertoires>`) → `null`, `non_suivi` ;
  un répertoire hors dépôt (`AGAGI_RESULTS_ROOT` pointé ailleurs) → `null`, `hors_depot` ; suivi sans ajout trouvé →
  `null`, `sans_ajout_trouve`.

**`indexer(racine, dates_git, suivis, raison_git) -> index_v1`** :

```text
{
  "schema": "index_v1", "generated_at": <epoch>, "repo_root": <POSIX>,
  "aveugle": [<str>, ...],               # préfixes : « dates : … », « famille <nom> : … », « hors familles : … » ;
                                         # « index: » est RÉSERVÉ au mode dégradé du service (I3)
  "familles": [{
     "nom", "motif", "exclus": [...], "fichiers": n | null,           # null = répertoire ABSENT (ligne), 0 = mesuré
     "indexes": n | null, "illisibles": [{"chemin", "raison"}],
     "champs_introuvables": {"titre": {"raison": n, ...}, "date_declaree": {...}, "etat": {...},
                             "date_ajout_git": {...}},
     "format_declare": {"date": n, "etat": n, "sujet": n, "liens": n, "fichiers": n}   # par CLÉ ; `type` exclu
                                         # (la porte 1 l'impose aux records : le compter serait une couverture fabriquée)
  }, ...],
  "hors_familles": {"n": n | null, "repertoires": {"docs/roadmap": n, ...}},   # fichiers SUIVIS sous docs/ et le
                                         # répertoire des résultats qui ne tombent dans aucune famille (I13) ;
                                         # null sans git
  "artefacts": [{"famille", "chemin", "titre", "date_declaree", "date_source", "date_ajout_git", "etat",
                 "etat_source", "regime", "scelle", "gate", "liens": [{"rel", "cible"}]}]
}
```

- **Parité par famille, sur la MÊME liste** (I10 a) : la liste globbée une fois ; chaque fichier finit dans
  exactement un de `indexes` / `illisibles` / `exclus`. Rupture → la FAMILLE à `null` + ligne qui la nomme (jamais
  une `ValueError` qui aveuglerait tout l'index) ; témoin : un lecteur qui perd un fichier rompt la parité.
- **Types normalisés artefact par artefact** (I10 b) : une valeur non-chaîne là où une chaîne est attendue
  (`title: [a, b]`, `verdict: {x: 1}`) → `null`, compté `type_inattendu` ; aucun artefact ne peut faire refuser le bloc.
- Ordre : familles dans l'ordre de la table, artefacts par (famille, chemin POSIX).

### 3.2 `tools/pm/science.py` — les trois blocs (P2.84)

**`compute_science(index, taxonomie, preinscriptions, records_graph, now) -> science_v1`**, pur, sources injectées ;
bloc `null` + ligne (préfixe du bloc) quand sa source manque.

- **`pipeline`** (vue 1) — source : `tools/check_preregistration_applied.py`, fonctions PUBLIQUES `couverture()`
  (`inspectees, sans_grandeur, sans_record, total`, en familles) et `familles_sans_record()`. ⚠️ **Sans ses
  répertoires, ce module ne lève pas : il rend `(0, 0, 0, 0)` et `[]`** (sondé : module copié seul). Le service
  vérifie donc `isdir(module._PREREG) and isdir(module._EDR)` AVANT l'appel ; sinon `pipeline = null` + ligne
  `pipeline : racine du module <_ROOT> sans docs/preregistrations ou docs/EDR` (B2). S'y ajoute la liste des
  pré-inscriptions de l'index (nom, `scelle`, `date_ajout_git`). Aucune jointure règle ↔ record refaite ici.
- **`taxonomie`** (vue 2) — source : `data/agi_taxonomy/{capabilities,demands,refuted}.json` (par
  `paths.data_file`), recopiés : capacités ; arêtes `nature: "etablie"` (avec `strength`, `evidence`) et `nature:
  "refutee"` (avec `verdict`, `reason`, **`superseded_by`**). Mesuré : les deux réfutées portent sur la paire
  `language ← memory`, aussi ÉTABLIE dans `demands.json` — la vue dit « dépassée par <record> » (I8), elle ne trace
  pas trois arêtes contradictoires sans légende.
- **`trouvailles`** (vue 3) — **verdicts lus dans l'INDEX** (records, `etat_source == "verdict"`, 139 aujourd'hui),
  pas dans `records_graph.json`, **périmé** (dernier commit le 2026-09-16, 131 verdicts, aucun horodatage — I9) ;
  `records_graph` sert seulement à publier l'écart : si son compte diffère de celui de l'index, ligne
  `trouvailles : results/records_graph.json compte n verdicts, docs/EDR en déclare m — graphe à regénérer
  (tools/consolidate_records.py)`. **`par_semaine`** : par famille, sur UNE date nommée
  (`date_ajout_git` pour record/adr/ref/sdr/resultat/preinscription, `date_declaree` pour spec/plan/revue) ; clés
  `"AAAA-Www"` (ISO, UTC), **denses** entre la première et la dernière semaine de la famille — un zéro y est une
  mesure puisque la source de date est complète ; artefacts sans cette date comptés dans `sans_date` par raison ; si
  la source de date de la famille est indisponible (git), `par_semaine[famille] = null` et `sans_date` porte le
  total sous `git_indisponible` (M4). Aucune clé de tendance (le témoin énumère les clés de sortie).

### 3.3 Le « format déclaré »

Un frontmatter YAML optionnel en tête d'un `.md` (`type`, `date` `AAAA-MM-JJ`, `sujet`, `etat`, `liens`), ou les clés
racine `date` / `etat` d'un JSON. **Rien n'impose de l'écrire** ; l'index le lit quand il existe et publie, par
famille, le nombre de fichiers qui déclarent CHAQUE clé (sauf `type`). La vue montre ces comptes sans seuil ni
couleur. Une porte qui l'exigerait est une décision future de robla, après mesure (condition 3).

### 3.4 Backend

- `backend/app/services/index_service.py` et `science_service.py` sur le modèle de `pilotage_service.py` : imports
  GARDÉS (`tools.pm.index_artefacts`, `tools.pm.science`, `tools.check_preregistration_applied`), ligne `index:
  ImportError …` / `science: ImportError …` qui NOMME le module ; racine par `pilotage.racine_depot()` (ancrée sur le
  module, garde de santé) ; cache 60 s ; `science_service` lit l'index par `index_service.get_index()` (même cache) ;
  chaque bloc validé contre son modèle DANS le filet ; lignes de source jamais préfixées `index:`/`science:` (I3).
- `backend/app/routes/pm.py` : `GET /index` et `GET /science`.
- `backend/app/schemas.py` : `IndexV1` (`IndexFamille`, `IndexArtefact`, `IndexLien`), `ScienceV1` (`Pipeline`,
  `Taxonomie`, `TaxonomieArete`, `Trouvailles`) — modèles NOMMÉS ; **`make api-types` dans le même commit**, LF.
- **`backend/requirements.txt` gagne `pyyaml`** (D2).
- **CI, smoke docker** : `/api/pm/index` et `/api/pm/science` en plus ; **rouge** sur toute ligne `index:` /
  `science:` ET si `pipeline` est `null` ou `pipeline.couverture.total == 0` (B2 : le module sans racine rend zéro,
  pas une exception). La ligne `dates : git indisponible` y est ATTENDUE (ni git ni `.git` dans l'image) et ne rougit
  pas.

### 3.5 Frontend

- Famille **Pilotage** : 4ᵉ onglet **Index** — par famille : fichiers, indexés, illisibles (avec raisons), exclus,
  champs introuvables par raison, format déclaré par clé ; `hors_familles` ; puis la liste filtrable des artefacts
  (famille, texte, sans date, illisible) ; lien `vscode://file/` sur le `repo_root` de tête.
- Famille **Science** (nouvelle) : **Pipeline**, **Taxonomie**, **Trouvailles** ; `useQuery` inline par vue sur
  `queryKeys.pm.science`, `SCIENCE_POLL` (60 s).
  - **Pipeline** : les quatre comptes de `couverture()` en `Stat` ; les familles sans record NOMMÉES, avec la phrase
    du module (« un humain tranche ») ; la table des pré-inscriptions.
  - **Taxonomie** : graphe capacités → prérequis ; établies en trait plein, **réfutées en pointillés d'une autre
    couleur, leur nature ÉCRITE** (légende et tableau : verdict, raison, « dépassée par … ») ; disposition calculée
    pour N capacités (cercle déterministe) si `ProvenanceGraph` ne convient pas — tranché au plan (M6).
  - **Trouvailles** : table des verdicts de l'index (filtres verdict, gate) ; `par_semaine` en table (semaine ×
    famille), **le nom de la date en en-tête**, « non mesurable ici (git indisponible) » quand `null` ; aucune phrase
    sur la pente.
- Règles du lot 1 : `AveugleBanner`, bloc `null` → `Empty` avec SA ligne, `Loading` / `ErrorState`, aucun `fetch`
  hors `api/`, zéro `setInterval`, chemins littéraux dans `api/pm.ts`.

---

## 4. Flux de données — un writer par fichier

| source | writer | lecteur |
| --- | --- | --- |
| `docs/{EDR,ADR,REF,SDR,superpowers/*,reviews,preregistrations}` | commits path-scopés | `index_artefacts.py` |
| répertoire des résultats | runners | `index_artefacts.py` |
| `results/records_graph.json` | `tools/consolidate_records.py` | `science.py` (écart de compte seulement) |
| `data/agi_taxonomy/*.json` | commits (porte 5) | `science.py` |
| historique git | commits | `lire_dates_git`, `lire_suivis` (lecture) |
| cache mémoire | processus backend | routes |

`tools/consolidate_records.py` gagne une fonction (`lire_frontmatter`) sans changer ce qu'il ÉCRIT ni ce que
`parse_record` rend.

---

## 5. Erreurs et modes dégradés

| cas | comportement |
| --- | --- |
| git absent (image docker) | `dates_git = None` : `date_ajout_git` `null` partout, comptée `git_indisponible` ; UNE ligne `dates : git indisponible dans ce processus` ; `par_semaine` des familles datées par git → `null` ; `hors_familles` → `null` + ligne |
| clone superficiel | idem, raison `historique_tronque` |
| dépôt extérieur (fuite `GIT_DIR`) | idem, `git_indisponible` + ligne nommant le toplevel rendu |
| répertoire d'une famille absent | `fichiers: null` + ligne nommant le répertoire ; jamais `0` |
| fichier illisible | `illisibles` avec raison du vocabulaire ; parité tenue |
| PyYAML absent | fichiers à frontmatter → `illisibles`, raison `pyyaml_absent`, UNE ligne ; les familles json et md sans frontmatter restent servies (import paresseux) |
| parité rompue sur une famille | cette famille `null` + ligne ; les autres servies |
| module de la pipeline sans racine | `pipeline = null` + ligne nommant `_ROOT` (jamais ses zéros) |
| `records_graph.json` absent ou divergent | ligne d'écart ; les verdicts viennent de l'index |
| `data/agi_taxonomy` absent | `taxonomie = null` + ligne |
| exception ailleurs | 200, `aveugle = ["index: …"]` ou `["science: …"]`, blocs `null`, `role="alert"` côté vue |

---

## 6. Coût

Mesuré à la conception : `git log` figé 0,15-0,19 s (3 passes, charge 73,7 %) ; `parse_record` sur 335 records
0,39 s (relecteur, charge 24 %) — le lecteur brut coûte au plus autant ; `couverture()` 0,22 s et
`familles_sans_record()` 0,19 s (chacune relit les 305 EDR). **À mesurer au pas 1, machine au repos, charge notée** :
`indexer` complet, taille de `index_v1` (≈ 770 artefacts), `compute_science`. Si l'index dépasse 2 s à froid, le
cache passe à 300 s — décidé sur la mesure.

---

## 7. Tests et calibration

`indexer` et `compute_science` produisent des comptes : instruments déclarés `CALIBRATED` dans
`tests/sandbox/test_instrument_calibration.py`. ⚠️ Le cliquet (porte 2) ne DÉTECTE pas ces noms (P2.83) et une
déclaration ignorée NOUVELLE fait échouer la porte (`check_instrument_calibration.py:528`, sondé) : les deux
déclarations sont gelées, en noms QUALIFIÉS, dans `declarations_ignorees` de sa baseline, **dans le même commit**,
comme `compute_pilotage` et `parse_roadmap` au lot 1 (I6).

| forme | cas |
| --- | --- |
| no-op exact | racine vide → chaque famille `fichiers: null` + une ligne par répertoire ; aucun `0`, aucune liste vide présentée comme mesure |
| injection à dose connue | dépôt jetable : EDR à frontmatter complet, EDR sans frontmatter, REF sans `status`, frontmatter YAML cassé, frontmatter liste, `date: 2026-13-45`, fichier vide, JSON invalide, JSON racine liste, JSON sans `name`, spec datée sans titre `# `, plan au nom non daté, `README.md` exclu → comptes et raisons EXACTS ; **aucun `status: open`, aucun titre tiré du nom** (contre-exemple B1 gelé) |
| équivalence | `parse_record` rend le même dict qu'avant l'extraction de `lire_frontmatter` sur les 335 records réels (témoin de non-régression de la porte 1) |
| parité | dépôt réel : chaque fichier globbé dans exactement un compartiment ; un lecteur qui perd un fichier → sa famille `null` + ligne, les autres servies |
| types | `title: [a, b]`, `verdict: {x: 1}` → `null`, `type_inattendu`, bloc servi |
| prédiction | un fichier ajouté à une famille du dépôt jetable → sa famille +1, rien d'autre ne bouge |
| dates git | dépôt jetable RÉEL (environnement isolé) : deux commits à `GIT_COMMITTER_DATE` connues ; un chemin ajouté, supprimé, recréé → la plus ancienne ; un renommage → date du renommage (sémantique « chemin ») ; un fichier non suivi → `non_suivi` ; **clone `--depth 1` → `None`, `historique_tronque`** ; hors dépôt → `None` ; `diff.renames` posé dans la config → même résultat (commande figée) ; minuit UTC : semaine ISO en UTC |
| hors familles | fichier suivi sous `docs/roadmap` → compté dans `hors_familles` |
| porte 12 | le module ne porte aucun littéral `results/` ni `data/` (la porte le juge au commit) |
| science, pipeline | `couverture()` injectée → recopiée ; **module sans ses répertoires → `pipeline null` + ligne, jamais `(0,0,0,0)`** (contre-exemple B2 gelé) |
| science, taxonomie | fichiers réels : 3 établies, 2 réfutées avec `superseded_by` ; une réfutée retirée de l'entrée → le témoin la NOMME |
| science, par semaine | injection : records datés dans deux semaines non contiguës → semaine intermédiaire à 0 (dense) ; 1 sans date → `sans_date` ; git absent → `null` et `sans_date` = total ; clés de sortie énumérées (aucune tendance) |
| science, trouvailles | verdicts de l'index ; `records_graph` à un autre compte → ligne d'écart |
| backend | les six cas de `/api/pm/pilotage` pour chaque route (200 + schéma, service qui lève, cache, bloc de type étranger → `null` sans 500, import refusé nommé) ; `/science` n'appelle pas `indexer` quand le cache de l'index est chaud |
| image docker | reproduit SANS docker comme `b7a06d87` : dossier = image + volumes, venv limité à `backend/requirements.txt` → 200 sans ligne `index:`/`science:`, `pipeline.couverture.total > 0`, ligne `dates : git indisponible` présente |
| frontend | bloc `null` → `Empty` par vue ; réfutées rendues ET légendées avec « dépassée par » ; `par_semaine` sans aucun texte de tendance ; « non mesurable ici » quand `null` ; mutants sur chaque règle, comme au lot 1 |

Aucun test n'écrit dans l'arbre (P2.113 a) : dépôts jetables sous `tmp_path`, environnement git isolé, `pytest.ini`
à côté de tout fichier sur lequel un témoin relance pytest.

---

## 8. Ordre de livraison

| # | livrable |
| --- | --- |
| 1 | `lire_frontmatter` extrait dans `consolidate_records` (+ témoin d'équivalence) ; `tools/pm/index_artefacts.py` + tests + déclarations gelées ; coût publié au §6 |
| 2 | `index_service` + route + schémas + `make api-types` + `pyyaml` + smoke CI ; reproduction « image sans docker » |
| 3 | onglet Index (frontend) |
| 4 | `tools/pm/science.py` + `science_service` + route + schémas + smoke |
| 5 | famille Science, une vue par commit : Pipeline, Taxonomie, Trouvailles |

Chaque pas : commit par `commit-exact`, tests Windows et WSL, revue adversariale opus avant commit pour les pas 1, 2
et 4 (ceux qui produisent des comptes), chaîne remise à Master 2.

**Hors périmètre, décidé** : publication de l'index dans la page artefact claude.ai ; les ledgers `.superpowers/sdd`
(cinq fichiers suivis, `git ls-files .superpowers`) ; les « arbres » (avance / retard par branche : c'est git, pas
un artefact) ; toute porte sur le format déclaré ; **les « fermetures par semaine » de P2.84 (d)** — la date d'une tête
d'entrée est celle de son STATUT (lot 1, §3.1 : 15 têtes en portent plusieurs), il faudrait une règle plus fine,
qui n'est pas celle de ce lot (I14 b).

---

## 9. Décisions — TRANCHÉES par Master 2 le 2026-09-26 (spec approuvée)

- **D1 — dater par git LÀ où l'historique complet existe, publier, LIRE avec l'âge : le patron de `BOARD.json`.**
  Ni git dans l'image, ni renoncement au rythme. La commande d'écriture (`python -m tools.pm.index_artefacts
  --ecrire-dates`, appelée par le tick PM, ou lancée sur batcave) calcule les dates (§3.1, commande figée) et écrit
  `paths.pm_dir("DATES_GIT.json")` avec son `generated_at`, le sha de HEAD et l'**état de l'historique** mesuré par
  `git rev-parse --is-shallow-repository` (`complet` / `tronque` / `indisponible`). Le backend et l'index ne lancent
  JAMAIS git : ils LISENT ce fichier (`data/` est monté dans l'image), avec son âge calculé sur `generated_at`, jamais
  sur le `mtime`. Fichier absent, historique tronqué ou indisponible → `date_ajout_git = null` + raison du
  vocabulaire fermé, jamais une date du jour. Sémantique publiée : « entrée du chemin actuel dans le dépôt, à la date
  de l'instantané » (renommage = entrée, 305/305).
- **D2 — `pyyaml` dans `backend/requirements.txt`** (leçon `b7a06d87` : l'image n'a que cette liste), avec un témoin
  qui lit un frontmatter RÉEL dans les conditions de l'image (venv limité à cette liste, §7 « image docker »).
- **D3 — l'onglet Index va dans la famille Pilotage**, les trois vues dans une famille Science neuve.

**Ce que D1 change dans les sections précédentes** (elles gardent leur texte d'avant décision ; en cas d'écart,
ce paragraphe fait foi) :
- §2 : `lire_dates_git` sort du chemin de requête ; il n'existe que dans l'écrivain de `DATES_GIT.json`. `indexer`
  reçoit `dates = read_dates(racine)` (le fichier) et `lire_suivis` n'existe plus côté lecture : la liste des
  fichiers suivis voyage DANS `DATES_GIT.json` (clé `suivis`, même instantané), et `hors_familles` est publié avec
  l'âge de cet instantané.
- **Forme de `DATES_GIT.json`** (`dates_git_v1`, writer unique : `index_artefacts.ecrire_dates_git`, appelé par le
  tick PM ou à la main — même programme, comme `BOARD.json` et `board.main`) : `{schema, generated_at, head,
  historique: "complet" | "tronque" | "indisponible", raison: null | <str>, dates: {chemin: "AAAA-MM-JJ" (UTC)} |
  null, suivis: [chemin, …] | null}` — `dates` et `suivis` valent `null`, jamais `{}` ni `[]`, quand l'historique
  n'est pas `complet`.
- **Vocabulaire des raisons de `date_ajout_git`** (remplace celui du §3.1) : `dates_absentes` (fichier introuvable
  ou illisible, chemin CHERCHÉ nommé en ligne, les deux causes sans en choisir une — leçon G9 du lot 1),
  `historique_tronque`, `git_indisponible` (là où l'écrivain a tourné), `hors_depot`, `absent_des_dates` (chemin
  hors de l'instantané : ajouté depuis, ou non suivi à cette date — l'index ne tranche pas sans git), et
  `sans_ajout_trouve` (suivi dans l'instantané, sans ajout trouvé). La raison `non_suivi` disparaît : sans git
  vivant, elle affirmerait un état présent tiré d'un instantané passé.
- §5 : la ligne « git absent (image docker) » devient « `DATES_GIT.json` absent » (même comportement, raison
  `dates_absentes`) ; un instantané vieux est servi AVEC son âge (`dates_age_s`) ; la ligne `dates : …` du smoke CI
  est attendue (aucun `DATES_GIT.json` dans le `data/` de la CI).
- §7 : les cas « dates git » visent l'ÉCRIVAIN (dépôt jetable réel, clone `--depth 1` → `historique: "tronque"`,
  `dates: null`) et le LECTEUR (fichier absent, tronqué, âge sur `generated_at` et non sur un `mtime` volontairement
  décalé — contre-exemple du lot 1) ; le tick PM qui écrit `DATES_GIT.json` passe par le même filet que le pilotage
  (une exception devient une ligne de digest, jamais un tick qui échoue).
- §8 : le pas 1 livre aussi l'écrivain et le patch du tick PM.

---

## 10. Contraintes du dépôt honorées

Porte 12 (chemins par `src/paths.py`, ancrés) · porte 14 (`null` + raison, jamais une constante) · porte 2 (déclarations
gelées dans le même commit) · porte 10 (recensement monte) · un writer par fichier · règle à deux faces des `GIT_*` ·
`make api-types` au même commit · aucun test n'écrit dans l'arbre · aucun bail `kuzu` (aucune simulation).

---

## 11. Backlog, dans le commit de cette spec

- **P2.87** : clause repointée sur le code — `closes_when:path_present=tools/pm/index_artefacts.py` (la porte 4 refuse
  un `grep_present` sur un fichier qui n'existe pas encore : clause « invérifiable ») — et note « spec écrite le
  2026-09-26 » ; elle ne se ferme qu'avec l'index livré (I14 c).
- **P2.84** : clause repointée sur `tools/pm/science.py`, même règle.

---

## 12. Revue adversariale (2026-09-26, un relecteur opus, sondes propres)

**3 bloquants, tous intégrés** : (B1) `parse_record` fabrique un titre tiré du nom et `status: open` pour 34 EDR sans
frontmatter et 11 REF sans `status`, avale un YAML cassé dans un WARN et JETTE la clé `date` — l'index ne l'utilise
plus, il lit le frontmatter BRUT par un lecteur partagé ; (B2) le module de la pipeline rend `(0,0,0,0)` sans ses
répertoires au lieu de lever — vérifié AVANT l'appel, et le smoke exige `total > 0` ; (B3) un clone `--depth 1` date
les 305 EDR du jour du clone — `historique_tronque`.
**14 importants intégrés** : commande git figée et vocabulaire de raisons (I1), environnement à deux faces (I2),
préfixes réservés au mode dégradé (I3), import paresseux de PyYAML (I4), porte 12 (I5), porte 2 et gel des
déclarations (I6), `scelle` et `etat` JSON (I7), `superseded_by` (I8), `records_graph` périmé (I9), refus locaux
(I10), toutes les clés de liens (I11), couverture par clé et raisons fermées (I12), famille `sdr` et `hors_familles`
(I13), conséquences de D1 et clauses sur le code (I14). **7 mineurs** : chiffres corrigés (M1 — le « 20 verdicts
racine » de la v1 comptait les clés CONTENANT « verdict »), racine JSON liste (M2), dates YAML et noms invalides (M3),
`par_semaine` dense (M4), `etat_source` (M5), disposition pour N capacités et cache partagé (M6), `records_graph.json`
exclu des résultats (M7).
