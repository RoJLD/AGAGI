# Plan 1/3 — PM : tableau déterministe, bulletin par hooks, tick `/pm`, registre `ROLES.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à la flotte de sessions AGAGI un tableau « qui fait quoi / hygiène / charge » calculé sans LLM, alimenté par des bulletins écrits par hooks, lu par toute session à son démarrage, et un protocole de tick pour la session PM.

**Architecture:** `tools/pm/snapshot.py` LIT les sources (registre natif `~/.claude/sessions`, bulletins, git, bails, processus) et rend `None` par source indisponible ; `tools/pm/board.py::compute(snap)` est une fonction PURE qui rend sessions, alertes A1-A8, charge connue et la liste des aveuglements ; `tools/pm/bulletin.py` est l'unique writer du bulletin d'UNE session, branché par `.claude/settings.json` ; la session PM tient le bail `pm`, lance `board.main`, journalise les alertes et tient `docs/roadmap/ROLES.md`.

**Tech Stack:** Python 3 stdlib + `psutil` (import LOCAL sous try/except, convention du dépôt), git CLI, hooks Claude Code (`SessionStart`, `PostToolUse`, `Stop`, `SessionEnd`), pytest.

**Spec:** `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` (§2.1, §3.1, §3.2, §3.3, §3.6, §4, §5, §6.1, §6.2, §7 étapes 1-3).

## Global Constraints

- **Porte 12** : aucune constante de chaîne commençant par `data/` ou `results/` dans un `.py` sous `tools/` — tout chemin passe par `src.paths` (`paths.sessions_dir(...)`, `paths.pm_dir(...)`). Le cliquet est AST : une f-string `f"data/{x}"` est attrapée aussi.
- **Porte 14** : jamais `agrégat if collection else 0.0` ; une source vide ou absente rend `None` et le tableau écrit `AVEUGLE SUR <source>`.
- **Cliquet de calibration** : pas de `def run(` au niveau module dans `tools/pm/` (`run` est un nom d'instrument déjà en collision sur 3 fichiers) ; nommer `main`, `compute`, `collect_*`, `read_*`, `render_*`. Le scan est TEXTUEL, ancré `^def`.
- **psutil** : jamais `import psutil` au niveau module ; import local dans `try/except`, chemin dégradé `None` (pas `[]`, pas `0`).
- **Un writer par fichier** : `data/sessions/<sid>.json` = les hooks de CETTE session ; `data/pm/*` = la session PM ; `docs/roadmap/ROLES.md` = la session PM.
- **Hooks** : commande sans backtick ni séquence d'échappement ; le processus hook sort TOUJOURS 0 ; toute erreur va dans `paths.pm_dir("hook_errors.log")`.
- **Tests** : `PYTHONIOENCODING=utf-8 python -m pytest <fichier> -q -p no:cacheprovider` depuis la racine ; timeout 120 s par défaut ; comparer les chemins de `src.paths` au LITTÉRAL avec `/` (jamais `os.path.join`).
- **Commits** : path-scoped `git commit -m "..." -- <chemins>` ; sur un fichier PARTAGÉ (`src/paths.py`, `.gitignore`, `tests/sandbox/test_paths.py`, `CLAUDE.md`), `python -c "from tools.check_staged_authorship import snapshot; snapshot(['<fichier>'], owner='plan-pm')"` avant d'éditer et `verify` avant de committer. Aucun backtick dans un message de commit. **L'exécutant demande l'accord de robla avant le PREMIER commit de sa session** (règle : jamais committer sans demande explicite).
- **Après chaque ajout de porte au hook** : entrée dans `check_gate_mutation.PORTES`, témoin qui rougit, et la phrase + balise `<!-- count:portes_hook=N -->` de `CLAUDE.md` mises à jour ensemble.

---

## Structure des fichiers

| fichier | responsabilité | créé/modifié |
| --- | --- | --- |
| `src/paths.py` | `sessions_dir(*p)`, `pm_dir(*p)` — indirection porte 12 | modifié |
| `.gitignore` | `data/sessions/`, `data/pm/` | modifié |
| `tools/pm/__init__.py` | docstring du paquet | créé |
| `tools/pm/snapshot.py` | lecteurs de sources, `None` si indisponible ; `snapshot()` | créé |
| `tools/pm/board.py` | `compute(snap)` pur, `render_md`, `main` (écrit BOARD.json/BOARD.md) | créé |
| `tools/pm/bulletin.py` | point d'entrée des hooks ; `claim` ; résumé du tableau au démarrage | créé |
| `tools/pm/alerts.py` | journal `alerts.jsonl` : diff, append, suivi | créé |
| `tools/pm/roles_counts.py` | compteurs recomputés → `ROLES_COUNTS.json` | créé |
| `tools/check_roles_registry.py` | porte 21 : cinq colonnes obligatoires de `ROLES.md` | créé |
| `.claude/settings.json` | hooks des 4 événements | créé |
| `.claude/skills/pm/SKILL.md` | protocole du tick `/pm` | créé |
| `docs/roadmap/ROLES.md` | registre des rôles (writer PM) | créé |
| `tools/hooks/pre-commit`, `tools/check_gate_mutation.py`, `tools/check_synthesis_counts.py`, `CLAUDE.md` | porte 21 branchée, mutée, comptée | modifiés |
| `tests/sandbox/test_paths.py` | 2 tests ajoutés | modifié |
| `tests/sandbox/test_pm_snapshot.py`, `test_pm_board.py`, `test_pm_bulletin.py`, `test_pm_alerts.py`, `test_pm_roles_counts.py`, `test_roles_registry_gate.py`, `test_pm_hooks_config.py` | témoins | créés |

---

### Task 1 : `src/paths.py` — `sessions_dir` / `pm_dir` + `.gitignore`

**Files:**
- Modify: `src/paths.py` (`__all__` l.35-39 ; section « artefacts FROIDS » après `data_file`, l.103-106)
- Modify: `.gitignore` (après la ligne `data/agent_states/`, l.49)
- Test: `tests/sandbox/test_paths.py` (ajouter en fin de fichier)

**Interfaces:**
- Produces: `paths.sessions_dir(*parties) -> str` (`"data/sessions"`, `"data/sessions/x.json"`), `paths.pm_dir(*parties) -> str` (`"data/pm"`, `"data/pm/BOARD.json"`). Racine relue à chaque appel via `data_root()`. Aucun accesseur ne crée de répertoire : l'appelant fait `os.makedirs(..., exist_ok=True)`.

- [ ] **Step 1 : écrire les deux tests (échouent : attribut absent)**

Ajouter à la fin de `tests/sandbox/test_paths.py` :

```python
def test_sessions_et_pm_sont_sous_la_racine_FROIDE_au_litteral_d_aujourd_hui():
    # PM (spec 2026-09-16 §3.1, §3.2) : bulletins de session et tableau, deux sous-repertoires de data/.
    assert paths.sessions_dir() == "data/sessions"
    assert paths.sessions_dir("6f3aee07.json") == "data/sessions/6f3aee07.json"
    assert paths.pm_dir() == "data/pm"
    assert paths.pm_dir("BOARD.json") == "data/pm/BOARD.json"


def test_sessions_et_pm_suivent_AGAGI_DATA_ROOT(monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", "//nas/agagi/froid")
    assert paths.sessions_dir() == "//nas/agagi/froid/sessions"
    assert paths.pm_dir("alerts.jsonl") == "//nas/agagi/froid/pm/alerts.jsonl"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_paths.py -q -p no:cacheprovider`
Expected: 2 FAILED — `AttributeError: module 'src.paths' has no attribute 'sessions_dir'`.

- [ ] **Step 3 : implémenter**

Dans `src/paths.py`, remplacer la ligne de `__all__` `"hall_of_fame", "agent_states", "epoch_states", "genomes", "data_file",` par :

```python
    "hall_of_fame", "agent_states", "epoch_states", "genomes", "data_file", "sessions_dir", "pm_dir",
```

et ajouter après la fonction `data_file` (avant le bandeau `# --- sorties de mesure`) :

```python
def sessions_dir(*parties):
    """Bulletins de session du PM (un JSON par sessionId, writer = les hooks de CETTE session)."""
    return _sous(data_root(), "sessions", *parties)


def pm_dir(*parties):
    """Artefacts du PM : BOARD.json, BOARD.md, alerts.jsonl, hook_errors.log, ROLES_COUNTS.json (writer = PM)."""
    return _sous(data_root(), "pm", *parties)
```

Dans `.gitignore`, après `data/agent_states/` :

```
# PM (2026-09-16, spec pm-stratege-refutateur) : bulletins par session et tableau, artefacts RUNTIME, jamais suivis.
data/sessions/
data/pm/
```

- [ ] **Step 4 : lancer, vérifier le vert + le cliquet des chemins**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_paths.py -q -p no:cacheprovider`
Expected: tous PASS (13 passed).
Run: `git check-ignore -v data/sessions/x.json data/pm/x.json`
Expected: deux lignes citant `.gitignore`.
Run: `PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only src/paths.py`
Expected: exit 0 (`src/paths.py` est hors périmètre).

- [ ] **Step 5 : commit (path-scoped, après accord de robla)**

```bash
git add src/paths.py .gitignore tests/sandbox/test_paths.py
git commit -m "feat(pm): paths.sessions_dir / paths.pm_dir + data/sessions et data/pm ignores -- indirection porte 12 pour le tableau PM" -- src/paths.py .gitignore tests/sandbox/test_paths.py
```

---

### Task 2 : `tools/pm/snapshot.py` — lecteurs de sources, `None` si indisponible

**Files:**
- Create: `tools/pm/__init__.py`
- Create: `tools/pm/snapshot.py`
- Test: `tests/sandbox/test_pm_snapshot.py`

**Interfaces:**
- Consumes: `paths.sessions_dir()` (Task 1) ; `tools.jobs.doctor.classify_leases(leases_dir=)`, `tools.jobs.lease.is_holder_alive(lease)`, `tools.jobs.doctor.project_processes()` ; `tools.check_amputation.compter(chemin, src)` ; `tools.check_backlog_freshness._TETE`, `_BACKTICK_PATH`.
- Produces:
  - `norm(p) -> str` (absolu, casse normalisée, `/`)
  - `read_registry(registry_dir=None) -> list[dict] | None` — dicts `{pid, session_id, name, cwd, kind, started_at, updated_at}` (secondes epoch) ou `{"illisible": nom}`
  - `read_bulletins(sessions_dir=None) -> list[dict] | None`
  - `read_worktrees(repo_root) -> list[dict] | None` — `{path, branch, head, merged (bool|None), head_time (float|None)}`
  - `read_recent_commits(repo_root, since="24 hours ago", amputation_seuil=100) -> list[dict] | None` — `{sha, sujet, insertions, deletions, amputations: [{chemin, avant, apres}]}`
  - `read_leases(leases_dir=None) -> {"live": [...], "dead": [...]} | None` — chaque bail `{resource, pid, owner, created, expires_at, ttl_s, vivant, detenteur_vivant}`
  - `read_processes() -> list[dict] | None` — `project_processes()` + `simulation: bool`
  - `read_cpu_5min() -> float | None` (pourcentage)
  - `read_backlog_paths(repo_root) -> dict[str, list[str]] | None` — P-item → chemins cités
  - `snapshot(repo_root, *, registry_dir=None, sessions_dir=None, leases_dir=None, now=None, since="24 hours ago") -> dict` avec clés `now, repo_root, psutil, registry, bulletins, worktrees, commits, leases, processes, cpu_5min_pct, backlog_paths`

- [ ] **Step 1 : écrire les tests (échouent : module absent)**

Créer `tests/sandbox/test_pm_snapshot.py` :

```python
"""Lecteurs du tableau PM : chaque source absente rend None (jamais une valeur), chaque source presente est lue."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import snapshot as S  # noqa: E402


def _git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, encoding="utf-8", check=True).stdout


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "depot"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "a.md").write_text("\n".join(f"ligne {i}" for i in range(300)), encoding="utf-8")
    _git(r, "add", "a.md")
    _git(r, "commit", "-q", "-m", "init")
    return r


def test_registry_ABSENT_rend_None_pas_une_liste_vide(tmp_path):
    assert S.read_registry(str(tmp_path / "nulle_part")) is None


def test_registry_lit_les_champs_natifs_et_convertit_les_millisecondes(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "18276.json").write_text(json.dumps({"pid": 18276, "sessionId": "6f3a", "cwd": "c:\\x\\AGAGI",
                                              "startedAt": 1789515082665, "updatedAt": 1789515090000,
                                              "kind": "interactive", "name": "agagi-11"}), encoding="utf-8")
    (d / "casse.json").write_text("{pas du json", encoding="utf-8")
    reg = S.read_registry(str(d))
    assert len(reg) == 2
    ok = [r for r in reg if "illisible" not in r][0]
    assert ok["name"] == "agagi-11" and ok["session_id"] == "6f3a" and ok["pid"] == 18276
    assert ok["started_at"] == pytest.approx(1789515082.665)
    assert [r for r in reg if "illisible" in r][0]["illisible"] == "casse.json"


def test_bulletins_ABSENTS_rend_None_et_presents_sont_lus(tmp_path):
    assert S.read_bulletins(str(tmp_path / "rien")) is None
    d = tmp_path / "sessions"
    d.mkdir()
    (d / "s1.json").write_text(json.dumps({"session_id": "s1", "claims": ["P4.9"]}), encoding="utf-8")
    assert S.read_bulletins(str(d)) == [{"session_id": "s1", "claims": ["P4.9"]}]


def test_worktrees_liste_l_arbre_principal_avec_sa_branche(repo):
    w = S.read_worktrees(str(repo))
    assert len(w) == 1 and w[0]["branch"] == "main" and w[0]["path"] == S.norm(str(repo))
    assert w[0]["head_time"] is not None and w[0]["merged"] is True


def test_worktrees_hors_depot_rend_None(tmp_path):
    assert S.read_worktrees(str(tmp_path)) is None


def test_commits_recents_mesurent_les_suppressions_et_l_AMPUTATION(repo):
    (repo / "a.md").write_text("ligne 0\n", encoding="utf-8")            # 300 -> 1 ligne non vide
    _git(repo, "commit", "-q", "-am", "ampute")
    c = S.read_recent_commits(str(repo), since="1 day ago", amputation_seuil=100)
    assert c[0]["sujet"] == "ampute" and c[0]["deletions"] >= 299
    assert c[0]["amputations"] == [{"chemin": "a.md", "avant": 300, "apres": 1}]
    assert c[1]["sujet"] == "init" and c[1]["amputations"] == []


def test_leases_lit_le_repertoire_injecte_et_dit_si_le_detenteur_vit(tmp_path):
    from tools.jobs import lease as L
    L.acquire("kuzu", owner="vivant", ttl_s=3600.0, leases_dir=tmp_path, pid=os.getpid())
    L.acquire("pm", owner="fantome", leases_dir=tmp_path, pid=999_999)
    lz = S.read_leases(leases_dir=tmp_path)
    assert [x["resource"] for x in lz["live"]] == ["kuzu"]
    mort = lz["dead"][0]
    assert mort["resource"] == "pm" and mort["vivant"] is False and mort["detenteur_vivant"] is False


def test_backlog_paths_associe_chaque_P_item_aux_chemins_qu_il_cite(tmp_path):
    d = tmp_path / "docs" / "roadmap"
    d.mkdir(parents=True)
    (d / "PRIORITES_ET_DETTES.md").write_text(
        "**P4.9 — OUVERTE — ablation du credit.**\nQuoi : `tools/evo_runs/s2_credit_ablation.py` et `results/x.json`.\n\n"
        "**P2.78 — OUVERTE — autre.**\nRien de cite ici.\n", encoding="utf-8")
    bp = S.read_backlog_paths(str(tmp_path))
    assert bp["P4.9"] == ["results/x.json", "tools/evo_runs/s2_credit_ablation.py"]
    assert bp["P2.78"] == []
    assert S.read_backlog_paths(str(tmp_path / "ailleurs")) is None


def test_snapshot_porte_toutes_les_cles_et_ne_leve_pas_sans_sources(tmp_path, repo):
    snap = S.snapshot(str(repo), registry_dir=str(tmp_path / "r"), sessions_dir=str(tmp_path / "s"),
                      leases_dir=tmp_path / "l", now=1000.0)
    assert snap["now"] == 1000.0 and snap["repo_root"] == S.norm(str(repo))
    assert snap["registry"] is None and snap["bulletins"] is None
    assert snap["backlog_paths"] is None                      # pas de backlog dans ce depot factice
    assert snap["leases"] == {"live": [], "dead": []}
    assert set(snap) >= {"psutil", "worktrees", "commits", "processes", "cpu_5min_pct"}
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_snapshot.py -q -p no:cacheprovider`
Expected: erreur de collecte `ModuleNotFoundError: No module named 'tools.pm'`.

- [ ] **Step 3 : implémenter**

`tools/pm/__init__.py` :

```python
"""PM AGAGI : tableau deterministe de la flotte de sessions, bulletins par hooks, journal d'alertes."""
```

`tools/pm/snapshot.py` :

```python
"""Instantané des SOURCES du tableau PM — lecture seule, une fonction par source.

Chaque lecteur rend `None` quand sa source est indisponible (répertoire absent, git muet, psutil manquant) :
jamais une valeur par défaut. `board.compute` transforme chaque `None` en ligne `AVEUGLE SUR <source>` —
une source absente ne doit pas ressembler à une source saine (porte 14). Aucune écriture, aucun bail,
aucun monde : cette couche est CPU pur.
"""
import glob
import json
import os
import re
import subprocess
import time

from src import paths

REGISTRY_DIR_DEFAULT = os.path.join(os.path.expanduser("~"), ".claude", "sessions")
# Une ligne de commande de simulation : runners du monde, sondes, balayages, calibrations.
SIM_MARKERS = ("evo_runs", "_run.py", "probe", "sweep", "calibration", "s2_", "learner")
_DELETIONS = re.compile(r"(\d+) deletions?\(-\)")
_INSERTIONS = re.compile(r"(\d+) insertions?\(\+\)")


def norm(p):
    """Chemin comparable entre registre, worktrees et bulletins : absolu, casse normalisée, slashs avant."""
    return os.path.normcase(os.path.abspath(p)).replace("\\", "/").rstrip("/")


def _psutil():
    try:
        import psutil
        return psutil
    except Exception:                                   # noqa: BLE001 — dégradé déclaré : None
        return None


def _git(repo_root, *args, timeout=20):
    try:
        out = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, encoding="utf-8",
                             errors="replace", timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def _ms(v):
    return (float(v) / 1000.0) if v else None


def read_registry(registry_dir=None):
    d = registry_dir or REGISTRY_DIR_DEFAULT
    if not os.path.isdir(d):
        return None
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                r = json.load(fh)
        except (OSError, ValueError):
            out.append({"illisible": os.path.basename(f)})
            continue
        out.append({"pid": r.get("pid"), "session_id": r.get("sessionId"), "name": r.get("name"),
                    "cwd": r.get("cwd"), "kind": r.get("kind"),
                    "started_at": _ms(r.get("startedAt")), "updated_at": _ms(r.get("updatedAt"))})
    return out


def read_bulletins(sessions_dir=None):
    d = sessions_dir or paths.sessions_dir()
    if not os.path.isdir(d):
        return None
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                out.append(json.load(fh))
        except (OSError, ValueError):
            out.append({"illisible": os.path.basename(f)})
    return out


def read_worktrees(repo_root):
    txt = _git(repo_root, "worktree", "list", "--porcelain")
    if txt is None:
        return None
    merged = _git(repo_root, "branch", "--merged", "main", "--format=%(refname:short)")
    fusionnees = set(merged.split()) if merged is not None else None
    out, cur = [], {}
    for ligne in txt.splitlines() + [""]:
        if not ligne:
            if cur:
                out.append(cur)
                cur = {}
            continue
        cle, _, val = ligne.partition(" ")
        if cle == "worktree":
            cur = {"path": norm(val), "branch": None, "head": None}
        elif cle == "HEAD":
            cur["head"] = val
        elif cle == "branch":
            cur["branch"] = val.replace("refs/heads/", "")
    for w in out:
        w["merged"] = (w["branch"] in fusionnees) if (fusionnees is not None and w["branch"]) else None
        t = _git(repo_root, "log", "-1", "--format=%ct", w["head"]) if w["head"] else None
        w["head_time"] = float(t.strip()) if t and t.strip().isdigit() else None
    return out


def _amputations(repo_root, sha):
    """Fichiers du commit dont le compte d'ENTITÉ (tools/check_amputation.compter) tombe à 0 ou sous la moitié."""
    from tools.check_amputation import compter
    noms = _git(repo_root, "show", "--name-only", "--format=", sha)
    res = []
    for rel in (noms or "").split():
        avant, apres = _git(repo_root, "show", f"{sha}^:{rel}"), _git(repo_root, "show", f"{sha}:{rel}")
        if avant is None or apres is None:
            continue
        a, b = compter(rel, avant), compter(rel, apres)
        if a is None or b is None:
            continue
        if a > 0 and (b == 0 or b < a / 2):
            res.append({"chemin": rel, "avant": a, "apres": b})
    return res


def read_recent_commits(repo_root, since="24 hours ago", amputation_seuil=100):
    txt = _git(repo_root, "log", "--all", f"--since={since}", "--format=%x1e%H%x1f%s", "--shortstat")
    if txt is None:
        return None
    out = []
    for bloc in txt.split("\x1e"):
        bloc = bloc.strip()
        if not bloc:
            continue
        tete, _, reste = bloc.partition("\n")
        sha, _, sujet = tete.partition("\x1f")
        ins, dele = _INSERTIONS.search(reste), _DELETIONS.search(reste)
        c = {"sha": sha[:10], "sujet": sujet.strip(), "insertions": int(ins.group(1)) if ins else 0,
             "deletions": int(dele.group(1)) if dele else 0, "amputations": []}
        if c["deletions"] >= amputation_seuil:
            c["amputations"] = _amputations(repo_root, sha)
        out.append(c)
    return out


def read_leases(leases_dir=None):
    try:
        from tools.jobs import doctor as D
        from tools.jobs import lease as L
    except ImportError:
        return None
    cls = D.classify_leases(leases_dir=leases_dir)

    def _d(lz, vivant):
        return {"resource": lz.resource, "pid": lz.pid, "owner": lz.owner, "created": lz.created,
                "expires_at": lz.expires_at, "ttl_s": lz.ttl_s, "vivant": vivant,
                "detenteur_vivant": L.is_holder_alive(lz)}
    return {"live": [_d(x, True) for x in cls["live"]], "dead": [_d(x, False) for x in cls["dead"]]}


def read_processes():
    if _psutil() is None:
        return None
    from tools.jobs import doctor as D
    procs = D.project_processes()
    for p in procs:
        p["simulation"] = any(m in p["cmd"] for m in SIM_MARKERS)
    return procs


def read_cpu_5min():
    ps = _psutil()
    if ps is None:
        return None
    try:
        return 100.0 * ps.getloadavg()[1] / float(ps.cpu_count() or 1)
    except (OSError, AttributeError):
        return None


def read_backlog_paths(repo_root):
    p = os.path.join(repo_root, "docs", "roadmap", "PRIORITES_ET_DETTES.md")
    try:
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
    except OSError:
        return None
    from tools.check_backlog_freshness import _BACKTICK_PATH, _TETE
    tete = re.compile(_TETE)
    out, courant = {}, None
    for ligne in txt.splitlines():
        m = tete.match(ligne.strip())
        if m:
            courant = m.group(1).split("/")[0].strip()
            out.setdefault(courant, set())
            continue
        if courant is not None:
            for c in _BACKTICK_PATH.findall(ligne):
                if "/" in c:
                    out[courant].add(c)
    return {k: sorted(v) for k, v in out.items()}


def snapshot(repo_root, *, registry_dir=None, sessions_dir=None, leases_dir=None, now=None,
             since="24 hours ago"):
    return {"now": time.time() if now is None else float(now), "repo_root": norm(repo_root),
            "psutil": _psutil() is not None,
            "registry": read_registry(registry_dir), "bulletins": read_bulletins(sessions_dir),
            "worktrees": read_worktrees(repo_root), "commits": read_recent_commits(repo_root, since),
            "leases": read_leases(leases_dir), "processes": read_processes(),
            "cpu_5min_pct": read_cpu_5min(), "backlog_paths": read_backlog_paths(repo_root)}
```

- [ ] **Step 4 : lancer, vérifier le vert + les portes 12 et 14**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_snapshot.py -q -p no:cacheprovider`
Expected: 9 passed.
Run: `PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/pm/snapshot.py tools/pm/__init__.py`
Expected: exit 0, aucun nouveau littéral.
Run: `PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/pm/snapshot.py`
Expected: exit 0.
Run: `PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py --only tools/pm/snapshot.py`
Expected: `OK : aucun nouvel instrument non calibré.` (aucun nom de `snapshot.py` ne matche un motif d'instrument).

- [ ] **Step 5 : commit**

```bash
git add tools/pm/__init__.py tools/pm/snapshot.py tests/sandbox/test_pm_snapshot.py
git commit -m "feat(pm): tools/pm/snapshot.py -- lecteurs de sources du tableau PM, None par source indisponible (registre natif, bulletins, worktrees, commits+amputation, bails, processus, backlog)" -- tools/pm/__init__.py tools/pm/snapshot.py tests/sandbox/test_pm_snapshot.py
```

---

### Task 3 : `tools/pm/board.py` — `compute(snap)` pur, alertes A1-A8, `render_md`, `main`

**Files:**
- Create: `tools/pm/board.py`
- Test: `tests/sandbox/test_pm_board.py`

**Interfaces:**
- Consumes: le dict de `snapshot()` (Task 2) ; `paths.pm_dir()`.
- Produces:
  - `SEUILS = {"suppressions": 500, "cpu_pct": 80.0, "sims_max": 1, "worktree_jours": 7, "sans_claim_h": 1.0, "heartbeat_h": 2.0}`
  - `compute(snap, now=None) -> dict` avec clés `generated_at, repo_root, aveugle (list[str]), sessions (list[dict]), alertes (list[dict]), charge_connue (dict), worktrees, bails`. Une alerte = `{"id": "A1".."A8", "cle": "<id>:<sujet>", "gravite": "alerte"|"info", "message": str, "preuve": dict}`.
  - `render_md(board) -> str` — `AVEUGLE SUR …` en TÊTE, puis charge connue, sessions, alertes, worktrees.
  - `summary(board, max_lines=25) -> str` — le résumé que le hook `SessionStart` imprime.
  - `main(argv=None) -> int` — options `--repo-root`, `--registry-dir`, `--sessions-dir`, `--stdout` ; écrit `paths.pm_dir("BOARD.json")` et `paths.pm_dir("BOARD.md")`.

- [ ] **Step 1 : écrire les tests (échouent : module absent)**

Créer `tests/sandbox/test_pm_board.py` :

```python
"""Tableau PM : `compute` est PUR — chaque alerte a son cas positif et son no-op, chaque source absente rend
un AVEUGLEMENT visible et jamais un « 0 alerte »."""
import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import board as B  # noqa: E402

NOW = 1_800_000_000.0
ROOT = "c:/x/agagi"


def _reg(name, sid, cwd=ROOT, started=NOW - 600):
    return {"pid": 1, "session_id": sid, "name": name, "cwd": cwd, "kind": "interactive",
            "started_at": started, "updated_at": NOW}


def _bul(sid, files=(), claims=(), heartbeat=NOW - 60, branch="feat/x"):
    return {"session_id": sid, "files_touched": list(files), "claims": list(claims),
            "heartbeat_at": heartbeat, "branch": branch}


def _snap(**kw):
    base = {"now": NOW, "repo_root": ROOT, "psutil": True,
            "registry": [_reg("agagi-11", "s1"), _reg("agagi-52", "s2"), _reg("elysium-d4", "e1", cwd="c:/x/elysium")],
            "bulletins": [_bul("s1"), _bul("s2")],
            "worktrees": [{"path": ROOT, "branch": "main", "head": "abc", "merged": True, "head_time": NOW}],
            "commits": [{"sha": "abc1234567", "sujet": "ok", "insertions": 3, "deletions": 2, "amputations": []}],
            "leases": {"live": [], "dead": []}, "processes": [], "cpu_5min_pct": 12.0,
            "backlog_paths": {"P4.9": ["tools/evo_runs/s2_credit_ablation.py"], "P2.78": []}}
    base.update(kw)
    return base


def _ids(board, id_):
    return [a for a in board["alertes"] if a["id"] == id_]


def test_NOOP_exact_un_etat_sain_ne_leve_AUCUNE_alerte_ni_aveuglement():
    b = B.compute(_snap())
    assert b["alertes"] == [] and b["aveugle"] == []
    assert [s["name"] for s in b["sessions"]] == ["agagi-11", "agagi-52"]     # elysium hors dépôt


def test_A1_deux_sessions_sur_le_meme_fichier_et_pas_une_seule():
    b = B.compute(_snap(bulletins=[_bul("s1", files=["src/paths.py"]), _bul("s2", files=["src/paths.py", "x.py"])]))
    a = _ids(b, "A1")
    assert len(a) == 1 and a[0]["preuve"] == {"fichier": "src/paths.py", "sessions": ["agagi-11", "agagi-52"]}
    assert a[0]["cle"] == "A1:src/paths.py" and a[0]["gravite"] == "alerte"
    assert _ids(B.compute(_snap(bulletins=[_bul("s1", files=["x.py"]), _bul("s2", files=["y.py"])])), "A1") == []


def test_A2_bail_orphelin_ALERTE_et_ttl_expire_detenteur_vivant_INFO():
    morts = [{"resource": "kuzu", "pid": 9, "owner": "o", "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False,
              "detenteur_vivant": False},
             {"resource": "pm", "pid": 8, "owner": "p", "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False,
              "detenteur_vivant": True}]
    b = B.compute(_snap(leases={"live": [], "dead": morts}))
    a = {x["cle"]: x["gravite"] for x in _ids(b, "A2")}
    assert a == {"A2:kuzu": "alerte", "A2:pm": "info"}


def test_A2_sans_psutil_l_identite_des_detenteurs_est_AVEUGLE_pas_fausse():
    b = B.compute(_snap(psutil=False, leases={"live": [], "dead": [{"resource": "kuzu", "pid": 9, "owner": "o",
                  "created": 0, "expires_at": 1, "ttl_s": 1, "vivant": False, "detenteur_vivant": False}]}))
    assert _ids(b, "A2") == [] and any("psutil" in x for x in b["aveugle"])


def test_A3_worktree_sans_session_fusionne_ou_inactif_et_pas_celui_d_une_session():
    wts = [{"path": ROOT, "branch": "main", "head": "a", "merged": True, "head_time": NOW},
           {"path": ROOT + "/.claude/worktrees/wf-1", "branch": "wf-1", "head": "b", "merged": True, "head_time": NOW},
           {"path": ROOT + "/.worktrees/vieux", "branch": "chantier/vieux", "head": "c", "merged": False,
            "head_time": NOW - 8 * 86400},
           {"path": ROOT + "/.worktrees/actif", "branch": "chantier/actif", "head": "d", "merged": False,
            "head_time": NOW - 8 * 86400}]
    reg = [_reg("agagi-11", "s1"), _reg("agagi-52", "s2", cwd=ROOT + "/.worktrees/actif")]
    b = B.compute(_snap(worktrees=wts, registry=reg))
    assert sorted(a["cle"] for a in _ids(b, "A3")) == ["A3:" + ROOT + "/.claude/worktrees/wf-1", "A3:" + ROOT + "/.worktrees/vieux"]


def test_A4_commit_a_grosse_suppression_OU_amputation_et_pas_un_commit_ordinaire():
    gros = {"sha": "dead000000", "sujet": "menage", "insertions": 0, "deletions": 2372, "amputations": []}
    ampute = {"sha": "beef000000", "sujet": "x", "insertions": 1, "deletions": 120,
              "amputations": [{"chemin": "docs/roadmap/PRIORITES_ET_DETTES.md", "avant": 2352, "apres": 0}]}
    b = B.compute(_snap(commits=[gros, ampute, {"sha": "ok", "sujet": "ok", "insertions": 1, "deletions": 499, "amputations": []}]))
    assert sorted(a["cle"] for a in _ids(b, "A4")) == ["A4:beef000000", "A4:dead000000"]


def test_A5_deux_simulations_en_vol_ou_cpu_sature_et_ni_l_un_ni_l_autre_sinon():
    procs = [{"pid": 1, "age_min": 5, "rss_mb": 10, "cmd": "python tools/evo_runs/x_run.py", "simulation": True},
             {"pid": 2, "age_min": 5, "rss_mb": 10, "cmd": "python tools/s2_probe.py", "simulation": True},
             {"pid": 3, "age_min": 5, "rss_mb": 10, "cmd": "python -m pytest", "simulation": False}]
    b = B.compute(_snap(processes=procs))
    assert [a["cle"] for a in _ids(b, "A5")] == ["A5:sims"] and b["charge_connue"]["sims_en_vol"] == 2
    b2 = B.compute(_snap(cpu_5min_pct=91.0))
    assert [a["cle"] for a in _ids(b2, "A5")] == ["A5:cpu"]
    assert _ids(B.compute(_snap(processes=procs[:1], cpu_5min_pct=79.9)), "A5") == []


def test_A6_meme_P_item_revendique_par_deux_sessions():
    b = B.compute(_snap(bulletins=[_bul("s1", claims=["P4.9"]), _bul("s2", claims=["P4.9", "P2.78"])]))
    a = _ids(b, "A6")
    assert len(a) == 1 and a[0]["preuve"] == {"p_item": "P4.9", "sessions": ["agagi-11", "agagi-52"]}


def test_A7_session_active_plus_d_une_heure_sans_claim_ni_inference_est_une_INFO():
    reg = [_reg("agagi-11", "s1", started=NOW - 2 * 3600), _reg("agagi-52", "s2", started=NOW - 2 * 3600)]
    bul = [_bul("s1"), _bul("s2", files=["tools/evo_runs/s2_credit_ablation.py"])]
    b = B.compute(_snap(registry=reg, bulletins=bul))
    a = _ids(b, "A7")
    assert [x["cle"] for x in a] == ["A7:agagi-11"] and a[0]["gravite"] == "info"
    s2 = [s for s in b["sessions"] if s["name"] == "agagi-52"][0]
    assert s2["claims_inferes"] == ["P4.9"]                     # inféré des fichiers touchés, marqué comme tel


def test_A8_heartbeat_vieux_de_plus_de_deux_heures_est_une_INFO():
    b = B.compute(_snap(bulletins=[_bul("s1", heartbeat=NOW - 3 * 3600), _bul("s2")]))
    assert [x["cle"] for x in _ids(b, "A8")] == ["A8:agagi-11"]


def test_chaque_source_ABSENTE_est_nommee_AVEUGLE_et_ses_alertes_sont_supprimees():
    b = B.compute(_snap(registry=None, bulletins=None, worktrees=None, commits=None, leases=None, processes=None,
                        cpu_5min_pct=None, backlog_paths=None))
    assert b["alertes"] == [] and b["sessions"] == []
    assert len(b["aveugle"]) == 7
    assert b["charge_connue"] == {"sims_en_vol": None, "cpu_5min_pct": None, "bails_vivants": None}
    md = B.render_md(b)
    assert md.splitlines()[2].startswith("AVEUGLE SUR")          # en tête, avant toute autre ligne


def test_render_et_summary_portent_les_alertes_et_la_charge():
    b = B.compute(_snap(bulletins=[_bul("s1", files=["a.py"]), _bul("s2", files=["a.py"])]))
    md = B.render_md(b)
    assert "A1" in md and "agagi-11" in md and "charge connue" in md.lower()
    s = B.summary(b)
    assert len(s.splitlines()) <= 25 and "A1" in s


def test_main_ecrit_BOARD_json_et_md_sous_pm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    code = B.main(["--repo-root", os.getcwd(), "--registry-dir", str(tmp_path / "aucun"),
                   "--sessions-dir", str(tmp_path / "aucun")])
    assert code == 0
    j = json.loads((tmp_path / "pm" / "BOARD.json").read_text(encoding="utf-8"))
    assert "registre natif" in " ".join(j["aveugle"])
    assert (tmp_path / "pm" / "BOARD.md").read_text(encoding="utf-8").startswith("# Tableau PM")
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_board.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: No module named 'tools.pm.board'`.

- [ ] **Step 3 : implémenter**

`tools/pm/board.py` :

```python
"""Tableau PM — `compute(snap)` est PUR : un instantané (tools/pm/snapshot.py) -> sessions, alertes A1-A8,
charge connue, aveuglements. Seul `main` écrit (BOARD.json, BOARD.md sous paths.pm_dir()) : le PM en est
l'unique writer ; le hook SessionStart ne fait que LIRE le JSON en cache.

Une source absente ne produit jamais « 0 alerte » : elle produit une ligne AVEUGLE SUR <source> en tête du
tableau et supprime les alertes qui en dépendent (porte 14 appliquée au tableau lui-même).
"""
import argparse
import json
import os
import sys
import time

from src import paths
from tools.pm.snapshot import norm, snapshot

SEUILS = {"suppressions": 500, "cpu_pct": 80.0, "sims_max": 1, "worktree_jours": 7,
          "sans_claim_h": 1.0, "heartbeat_h": 2.0}


def _h(sec):
    return sec / 3600.0


def _nom(s):
    return s.get("name") or s.get("session_id") or "?"


def _sessions(snap):
    """Sessions DU DÉPÔT : registre natif dont le cwd est la racine ou un worktree, joint aux bulletins."""
    racines = {snap["repo_root"]} | {w["path"] for w in (snap.get("worktrees") or [])}
    bull = {b.get("session_id"): b for b in (snap.get("bulletins") or []) if b.get("session_id")}
    out = []
    for r in (snap.get("registry") or []):
        if "illisible" in r or not r.get("cwd"):
            continue
        cwd = norm(r["cwd"])
        if not any(cwd == x or cwd.startswith(x + "/") for x in racines):
            continue
        b = bull.get(r.get("session_id"), {})
        out.append({"name": r.get("name"), "session_id": r.get("session_id"), "pid": r.get("pid"), "cwd": cwd,
                    "started_at": r.get("started_at"), "branch": b.get("branch"),
                    "claims": list(b.get("claims") or []), "claims_inferes": [],
                    "files_touched": list(b.get("files_touched") or []),
                    "heartbeat_at": b.get("heartbeat_at"), "bulletin": bool(b)})
    return out


def _inferer_claims(sessions, backlog_paths):
    if backlog_paths is None:
        return
    for s in sessions:
        touches = set(s["files_touched"])
        s["claims_inferes"] = sorted(p for p, chemins in backlog_paths.items() if touches & set(chemins))


def _alertes(snap, sessions, now):
    A, aveugle = [], []

    def add(id_, cle, gravite, message, preuve):
        A.append({"id": id_, "cle": f"{id_}:{cle}", "gravite": gravite, "message": message, "preuve": preuve})

    if snap.get("registry") is None:
        aveugle.append("registre natif (~/.claude/sessions)")
    if snap.get("bulletins") is None:
        aveugle.append("bulletins de session (paths.sessions_dir)")
    else:                                                       # A1 — un fichier, deux sessions vivantes
        par_fichier = {}
        for s in sessions:
            for f in s["files_touched"]:
                par_fichier.setdefault(f, set()).add(_nom(s))
        for f, noms in sorted(par_fichier.items()):
            if len(noms) >= 2:
                add("A1", f, "alerte", f"{f} touché par {len(noms)} sessions vivantes : {', '.join(sorted(noms))}",
                    {"fichier": f, "sessions": sorted(noms)})

    leases = snap.get("leases")                                 # A2 — bails
    if leases is None:
        aveugle.append("bails (tools/jobs)")
    elif not snap.get("psutil"):
        aveugle.append("identité des détenteurs de bail (psutil absent)")
    else:
        for lz in leases["dead"]:
            if lz["detenteur_vivant"]:
                add("A2", lz["resource"], "info",
                    f"bail {lz['resource']} : TTL expiré, détenteur VIVANT (heartbeat manquant ; owner={lz['owner']!r}, pid={lz['pid']})", lz)
            else:
                add("A2", lz["resource"], "alerte",
                    f"bail {lz['resource']} ORPHELIN : détenteur mort (owner={lz['owner']!r}, pid={lz['pid']})", lz)

    wts = snap.get("worktrees")                                 # A3 — worktrees sans session
    if wts is None:
        aveugle.append("worktrees (git)")
    else:
        cwds = {s["cwd"] for s in sessions}
        for w in wts:
            if w["path"] == snap["repo_root"] or w["path"] in cwds:
                continue
            vieux = w.get("head_time") is not None and (now - w["head_time"]) > SEUILS["worktree_jours"] * 86400
            if w.get("merged") or vieux:
                raison = "branche fusionnée" if w.get("merged") else f"inactif > {SEUILS['worktree_jours']} j"
                add("A3", w["path"], "alerte", f"worktree sans session {w['path']} ({w.get('branch')}) : {raison}", w)

    commits = snap.get("commits")                               # A4 — grosse suppression / amputation (E22)
    if commits is None:
        aveugle.append("commits récents (git)")
    else:
        for c in commits:
            if c["deletions"] >= SEUILS["suppressions"] or c["amputations"]:
                add("A4", c["sha"], "alerte",
                    f"commit {c['sha']} : -{c['deletions']} lignes, {len(c['amputations'])} fichier(s) amputé(s) — {c['sujet'][:80]}", c)

    procs = snap.get("processes")                               # A5 — charge
    if procs is None:
        aveugle.append("processus (psutil)")
    sims = [p for p in (procs or []) if p.get("simulation")]
    if procs is not None and len(sims) > SEUILS["sims_max"]:
        add("A5", "sims", "alerte", f"{len(sims)} simulations en vol : pas une de plus (contention kuzu, coût contaminé E12)",
            {"pids": [p["pid"] for p in sims], "cmds": [p["cmd"] for p in sims]})
    cpu = snap.get("cpu_5min_pct")
    if cpu is not None and cpu > SEUILS["cpu_pct"]:
        add("A5", "cpu", "alerte", f"charge CPU 5 min = {cpu:.0f} % > {SEUILS['cpu_pct']:.0f} %", {"cpu_5min_pct": cpu})

    par_claim = {}                                              # A6 — même P-item
    for s in sessions:
        for c in s["claims"]:
            par_claim.setdefault(c, set()).add(_nom(s))
    for c, noms in sorted(par_claim.items()):
        if len(noms) >= 2:
            add("A6", c, "alerte", f"{c} revendiqué par {', '.join(sorted(noms))}", {"p_item": c, "sessions": sorted(noms)})

    for s in sessions:                                          # A7 / A8 — informations
        if not s["bulletin"]:
            continue
        age_h = _h(now - s["started_at"]) if s.get("started_at") else None
        if age_h is not None and age_h > SEUILS["sans_claim_h"] and not s["claims"] and not s["claims_inferes"]:
            add("A7", _nom(s), "info", f"{_nom(s)} active depuis {age_h:.1f} h sans P-item revendiqué ni inféré", {"session": _nom(s)})
        hb = s.get("heartbeat_at")
        if hb is not None and _h(now - hb) > SEUILS["heartbeat_h"]:
            add("A8", _nom(s), "info", f"{_nom(s)} : heartbeat vieux de {_h(now - hb):.1f} h, PID vivant", {"session": _nom(s)})
    return A, aveugle


def compute(snap, now=None):
    now = float(snap.get("now")) if now is None else float(now)
    sessions = _sessions(snap)
    _inferer_claims(sessions, snap.get("backlog_paths"))
    alertes, aveugle = _alertes(snap, sessions, now)
    if snap.get("backlog_paths") is None:
        aveugle.append("backlog (chemins cités par les entrées)")
    procs, leases = snap.get("processes"), snap.get("leases")
    charge = {"sims_en_vol": (sum(1 for p in procs if p.get("simulation")) if procs is not None else None),
              "cpu_5min_pct": snap.get("cpu_5min_pct"),
              "bails_vivants": ([l["resource"] for l in leases["live"]] if leases is not None else None)}
    return {"generated_at": now, "repo_root": snap["repo_root"], "aveugle": aveugle, "sessions": sessions,
            "alertes": alertes, "charge_connue": charge, "worktrees": snap.get("worktrees"), "bails": leases}


def render_md(board):
    L = ["# Tableau PM", f"généré : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(board['generated_at']))}"]
    for a in board["aveugle"]:
        L.append(f"AVEUGLE SUR {a}")
    c = board["charge_connue"]
    L += ["", "## Charge connue",
          f"simulations en vol : {c['sims_en_vol']} · CPU 5 min : {c['cpu_5min_pct']} % · bails vivants : {c['bails_vivants']}",
          "", "## Sessions", "| session | branche | P-items | inférés | fichiers en vol | heartbeat |", "| --- | --- | --- | --- | --- | --- |"]
    for s in board["sessions"]:
        hb = f"{_h(board['generated_at'] - s['heartbeat_at']):.1f} h" if s.get("heartbeat_at") else "—"
        L.append(f"| {_nom(s)} | {s.get('branch') or '—'} | {', '.join(s['claims']) or '—'} | "
                 f"{', '.join(s['claims_inferes']) or '—'} | {len(s['files_touched'])} | {hb} |")
    L += ["", f"## Alertes ({len(board['alertes'])})"]
    for a in board["alertes"]:
        L.append(f"- [{a['gravite']}] {a['cle']} — {a['message']}")
    L += ["", "## Worktrees"]
    for w in (board.get("worktrees") or []):
        L.append(f"- {w['path']} ({w.get('branch')}) fusionné={w.get('merged')}")
    return "\n".join(L) + "\n"


def summary(board, max_lines=25):
    """Ce qu'une session lit à sa naissance : aveuglements, charge, qui est sur quoi, alertes."""
    L = [f"[PM] tableau du {time.strftime('%Y-%m-%d %H:%M', time.localtime(board['generated_at']))} — {len(board['sessions'])} sessions AGAGI"]
    L += [f"[PM] AVEUGLE SUR {a}" for a in board["aveugle"]]
    c = board["charge_connue"]
    L.append(f"[PM] charge : sims={c['sims_en_vol']} cpu5={c['cpu_5min_pct']} bails={c['bails_vivants']}")
    for s in board["sessions"]:
        L.append(f"[PM] {_nom(s)} : {', '.join(s['claims'] or s['claims_inferes']) or 'sans P-item'} — {len(s['files_touched'])} fichiers en vol")
    for a in board["alertes"]:
        L.append(f"[PM] {a['gravite'].upper()} {a['cle']} — {a['message']}")
    if len(L) > max_lines:
        L = L[:max_lines - 1] + [f"[PM] … {len(L) - max_lines + 1} lignes de plus dans BOARD.md"]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--registry-dir", default=None)
    ap.add_argument("--sessions-dir", default=None)
    ap.add_argument("--stdout", action="store_true", help="imprime le markdown au lieu du résumé")
    args = ap.parse_args(argv)
    board = compute(snapshot(args.repo_root, registry_dir=args.registry_dir, sessions_dir=args.sessions_dir))
    os.makedirs(paths.pm_dir(), exist_ok=True)
    with open(paths.pm_dir("BOARD.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=1, default=str)
    md = render_md(board)
    with open(paths.pm_dir("BOARD.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md if args.stdout else summary(board))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : lancer, vérifier le vert + les portes**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_board.py -q -p no:cacheprovider`
Expected: 14 passed.
Run: `PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/pm/board.py && PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/pm/board.py && PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py --only tools/pm/board.py`
Expected: trois exit 0.
Run: `PYTHONIOENCODING=utf-8 python -m tools.pm.board`
Expected: le résumé réel de la machine (sessions AGAGI, `AVEUGLE SUR bulletins de session` tant que la Task 4 n'est pas livrée) ; `data/pm/BOARD.md` existe.

- [ ] **Step 5 : commit**

```bash
git add tools/pm/board.py tests/sandbox/test_pm_board.py
git commit -m "feat(pm): tools/pm/board.py -- compute() pur (sessions, A1-A8, charge connue, AVEUGLE SUR <source>), render_md, summary, main ecrit BOARD.json/BOARD.md sous paths.pm_dir" -- tools/pm/board.py tests/sandbox/test_pm_board.py
```

---

### Task 4 : `tools/pm/bulletin.py` — le bulletin d'une session, écrit par ses hooks

**Files:**
- Create: `tools/pm/bulletin.py`
- Test: `tests/sandbox/test_pm_bulletin.py`

**Interfaces:**
- Consumes: `paths.sessions_dir()`, `paths.pm_dir()` ; `tools.pm.snapshot.read_registry` ; `tools.pm.board.summary`.
- Produces:
  - `EVENTS = ("start", "tool", "stop", "end")` (événements de hook, JSON sur stdin) + sous-commande `claim`.
  - `charger(session_id, sessions_dir) -> dict`, `ecrire(bul, sessions_dir) -> None` (écriture `tmp` + `os.replace`).
  - `appliquer(event, payload, bul, *, now, branche_fn) -> dict` — PUR : met à jour le bulletin.
  - `nom_depuis_registre(session_id, registry_dir=None) -> str | None`.
  - `resume_tableau(pm_dir=None) -> str` — lit `BOARD.json` en cache, rend `summary(...)` ou `[PM] tableau absent : lancer python -m tools.pm.board`.
  - `session_id_courant(registry_dir=None) -> str | None` — pour `claim` hors hook : remonte les processus parents (psutil) jusqu'à un pid du registre.
  - `main(argv=None) -> int` — TOUJOURS 0 ; erreurs dans `paths.pm_dir("hook_errors.log")`.
- Schéma du bulletin : `{session_id, name, pid, cwd, branch, worktree, started_at, heartbeat_at, ended_at, claims: [], files_touched: [] (plafond 200, FIFO), last_tool_at}`.

- [ ] **Step 1 : écrire les tests (échouent : module absent)**

Créer `tests/sandbox/test_pm_bulletin.py` :

```python
"""Bulletin de session : les hooks l'écrivent, jamais la session ; un hook sort toujours 0."""
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import bulletin as BU  # noqa: E402

NOW = 1_800_000_000.0


def _payload(event, **kw):
    p = {"session_id": "s1", "cwd": "c:/x/agagi", "hook_event_name": event}
    p.update(kw)
    return p


def test_start_cree_le_bulletin_avec_les_champs_du_schema():
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda cwd: ("feat/x", "c:/x/agagi"))
    assert b["session_id"] == "s1" and b["started_at"] == NOW and b["branch"] == "feat/x"
    assert b["claims"] == [] and b["files_touched"] == [] and b["ended_at"] is None


def test_tool_ajoute_le_fichier_edite_sans_doublon_et_plafonne_a_200():
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: (None, None))
    for i in range(205):
        b = BU.appliquer("tool", _payload("PostToolUse", tool_name="Edit", tool_input={"file_path": f"c:/x/agagi/f{i}.py"}),
                         b, now=NOW + i, branche_fn=lambda c: (None, None))
    b = BU.appliquer("tool", _payload("PostToolUse", tool_name="Write", tool_input={"file_path": "c:/x/agagi/f204.py"}),
                     b, now=NOW + 300, branche_fn=lambda c: (None, None))
    assert len(b["files_touched"]) == 200 and b["files_touched"][-1] == "f204.py"     # relatif au cwd, FIFO
    assert b["files_touched"][0] == "f5.py" and b["last_tool_at"] == NOW + 300


def test_tool_sans_file_path_ne_change_rien():
    b0 = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: (None, None))
    b1 = BU.appliquer("tool", _payload("PostToolUse", tool_name="Bash", tool_input={"command": "ls"}), dict(b0), now=NOW + 1,
                      branche_fn=lambda c: (None, None))
    assert b1["files_touched"] == [] and b1["last_tool_at"] == NOW + 1


def test_stop_met_le_heartbeat_et_la_branche_et_end_la_fin():
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: ("a", "w"))
    b = BU.appliquer("stop", _payload("Stop"), b, now=NOW + 60, branche_fn=lambda c: ("feat/y", "c:/x/agagi/.worktrees/w"))
    assert b["heartbeat_at"] == NOW + 60 and b["branch"] == "feat/y" and b["worktree"] == "c:/x/agagi/.worktrees/w"
    b = BU.appliquer("end", _payload("SessionEnd"), b, now=NOW + 120, branche_fn=lambda c: (None, None))
    assert b["ended_at"] == NOW + 120


def test_ecrire_puis_charger_est_identite_et_charger_un_absent_rend_un_dict_vide(tmp_path):
    b = BU.appliquer("start", _payload("SessionStart"), {}, now=NOW, branche_fn=lambda c: (None, None))
    BU.ecrire(b, str(tmp_path))
    assert BU.charger("s1", str(tmp_path)) == b
    assert BU.charger("inconnu", str(tmp_path)) == {}
    assert sorted(os.listdir(tmp_path)) == ["s1.json"]                        # pas de .tmp résiduel


def test_nom_depuis_registre_joint_par_sessionId_et_None_sinon(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps({"pid": 1, "sessionId": "s1", "name": "agagi-11"}), encoding="utf-8")
    assert BU.nom_depuis_registre("s1", str(tmp_path)) == "agagi-11"
    assert BU.nom_depuis_registre("s9", str(tmp_path)) is None
    assert BU.nom_depuis_registre("s1", str(tmp_path / "absent")) is None


def test_main_start_ecrit_le_bulletin_imprime_le_resume_et_sort_0(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    b = json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))
    assert b["session_id"] == "s1" and b["name"] is None
    assert "[PM] tableau absent" in capsys.readouterr().out


def test_main_start_avec_BOARD_en_cache_imprime_le_resume_du_tableau(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    (tmp_path / "pm").mkdir()
    (tmp_path / "pm" / "BOARD.json").write_text(json.dumps({"generated_at": NOW, "aveugle": ["bails (tools/jobs)"], "sessions": [],
                                                           "alertes": [], "charge_connue": {"sims_en_vol": 0, "cpu_5min_pct": 1.0, "bails_vivants": []}}),
                                                encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    out = capsys.readouterr().out
    assert "[PM] AVEUGLE SUR bails" in out and "0 sessions AGAGI" in out


def test_main_avec_stdin_illisible_sort_0_et_journalise(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr("sys.stdin", io.StringIO("{pas du json"))
    assert BU.main(["stop"]) == 0
    log = (tmp_path / "pm" / "hook_errors.log").read_text(encoding="utf-8")
    assert "stop" in log and "JSONDecodeError" in log


def test_main_claim_ajoute_le_P_item_sans_doublon(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    assert BU.main(["claim", "P4.9", "--session", "s1"]) == 0
    assert BU.main(["claim", "P4.9", "--session", "s1"]) == 0
    assert BU.main(["claim", "P2.78", "--session", "s1"]) == 0
    assert json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))["claims"] == ["P4.9", "P2.78"]


def test_main_claim_sans_session_resolue_sort_0_et_l_ecrit(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))         # registre absent -> aucune session
    assert BU.main(["claim", "P4.9"]) == 0
    assert "session introuvable" in capsys.readouterr().out
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_bulletin.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: No module named 'tools.pm.bulletin'`.

- [ ] **Step 3 : implémenter**

`tools/pm/bulletin.py` :

```python
"""Bulletin d'UNE session, écrit par SES hooks — jamais de mémoire (E10 : une règle documentée est violée).

    python -m tools.pm.bulletin start|tool|stop|end     # appelé par .claude/settings.json, JSON du hook sur stdin
    python -m tools.pm.bulletin claim P4.9 [--session <id>]   # revendication volontaire d'un P-item

Le bulletin vit dans paths.sessions_dir("<session_id>.json"). Un hook sort TOUJOURS 0 : une erreur s'écrit dans
paths.pm_dir("hook_errors.log"), jamais dans la session. `start` imprime le résumé de BOARD.json en cache (jamais
recomputé ici : le hook doit rester sous la seconde) — c'est le PULL de la spec §3.1.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import traceback

from src import paths
from tools.pm.snapshot import REGISTRY_DIR_DEFAULT, norm, read_registry

EVENTS = ("start", "tool", "stop", "end")
PLAFOND_FICHIERS = 200
REGISTRY_DIR = REGISTRY_DIR_DEFAULT              # monkeypatchable par les tests


def _vide(session_id):
    return {"session_id": session_id, "name": None, "pid": None, "cwd": None, "branch": None, "worktree": None,
            "started_at": None, "heartbeat_at": None, "ended_at": None, "claims": [], "files_touched": [],
            "last_tool_at": None}


def charger(session_id, sessions_dir=None):
    p = os.path.join(sessions_dir or paths.sessions_dir(), f"{session_id}.json")
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def ecrire(bul, sessions_dir=None):
    d = sessions_dir or paths.sessions_dir()
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"{bul['session_id']}.json")
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(bul, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def branche_git(cwd):
    """(branche, racine du worktree) via git, ou (None, None) hors dépôt / git muet."""
    try:
        b = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True,
                           encoding="utf-8", timeout=5)
        w = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True,
                           encoding="utf-8", timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None, None
    return (b.stdout.strip() if b.returncode == 0 else None), (norm(w.stdout.strip()) if w.returncode == 0 else None)


def appliquer(event, payload, bul, *, now, branche_fn):
    """PUR : applique un événement de hook au bulletin. `branche_fn(cwd) -> (branche, worktree)` est injecté."""
    sid = payload.get("session_id") or bul.get("session_id")
    b = dict(_vide(sid), **bul)
    cwd = payload.get("cwd") or b.get("cwd")
    if event == "start":
        b["started_at"] = now
        b["cwd"] = norm(cwd) if cwd else None
        b["pid"] = payload.get("pid")
        b["branch"], b["worktree"] = branche_fn(cwd)
    elif event == "tool":
        b["last_tool_at"] = now
        fp = (payload.get("tool_input") or {}).get("file_path")
        if fp:
            rel = norm(fp)
            base = b.get("cwd") or (norm(cwd) if cwd else None)
            if base and rel.startswith(base + "/"):
                rel = rel[len(base) + 1:]
            files = [f for f in b["files_touched"] if f != rel] + [rel]
            b["files_touched"] = files[-PLAFOND_FICHIERS:]
    elif event == "stop":
        b["heartbeat_at"] = now
        br, wt = branche_fn(cwd)
        if br:
            b["branch"], b["worktree"] = br, wt
    elif event == "end":
        b["ended_at"] = now
    return b


def nom_depuis_registre(session_id, registry_dir=None):
    for r in (read_registry(registry_dir or REGISTRY_DIR) or []):
        if r.get("session_id") == session_id:
            return r.get("name")
    return None


def session_id_courant(registry_dir=None):
    """Hors hook (sous-commande claim) : le premier ancêtre du processus courant présent au registre."""
    reg = {r.get("pid"): r.get("session_id") for r in (read_registry(registry_dir or REGISTRY_DIR) or []) if r.get("pid")}
    try:
        import psutil
        p = psutil.Process(os.getpid())
        for anc in [p] + p.parents():
            if anc.pid in reg:
                return reg[anc.pid]
    except Exception:                                   # noqa: BLE001 — psutil absent ou processus disparu : inconnu
        return None
    return None


def resume_tableau(pm_dir=None):
    p = os.path.join(pm_dir or paths.pm_dir(), "BOARD.json")
    try:
        with open(p, encoding="utf-8") as fh:
            board = json.load(fh)
    except (OSError, ValueError):
        return "[PM] tableau absent : lancer python -m tools.pm.board (ou la session PM n'a pas encore tourné)"
    from tools.pm.board import summary
    return summary(board)


def _journal(event, exc):
    try:
        os.makedirs(paths.pm_dir(), exist_ok=True)
        with open(paths.pm_dir("hook_errors.log"), "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {event} {type(exc).__name__}: {exc}\n")
            fh.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-2000:] + "\n")
    except OSError:
        pass                                            # le journal lui-même est indisponible : rien ne doit remonter


def _hook(event):
    payload = json.loads(sys.stdin.read() or "{}")
    sid = payload.get("session_id")
    if not sid:
        raise ValueError("hook sans session_id")
    bul = appliquer(event, payload, charger(sid), now=time.time(), branche_fn=branche_git)
    if bul.get("name") is None:
        bul["name"] = nom_depuis_registre(sid)
    ecrire(bul)
    if event == "start":
        print(resume_tableau())


def _claim(p_item, session):
    sid = session or session_id_courant()
    if not sid:
        print("[PM] claim ignoré : session introuvable (passer --session <id> ; le registre natif ne connaît pas ce processus)")
        return
    bul = dict(_vide(sid), **charger(sid))
    if p_item not in bul["claims"]:
        bul["claims"].append(p_item)
    if bul.get("name") is None:
        bul["name"] = nom_depuis_registre(sid)
    ecrire(bul)
    print(f"[PM] {bul.get('name') or sid} revendique {', '.join(bul['claims'])}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("event", choices=EVENTS + ("claim",))
    ap.add_argument("p_item", nargs="?", default=None)
    ap.add_argument("--session", default=None)
    args = ap.parse_args(argv)
    try:                                                # Windows : stdout cp1252 -> les accents du résumé lèveraient
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        if args.event == "claim":
            if not args.p_item:
                raise ValueError("claim exige un P-item (ex. P4.9)")
            _claim(args.p_item, args.session)
        else:
            _hook(args.event)
    except Exception as exc:                            # noqa: BLE001 — un hook ne bloque JAMAIS la session
        _journal(args.event, exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4 : lancer, vérifier le vert + portes**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_bulletin.py -q -p no:cacheprovider`
Expected: 11 passed.
Run: `PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/pm/bulletin.py && PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py --only tools/pm/bulletin.py`
Expected: exit 0 ×2.
Run (essai réel, sans hook) : `echo {"session_id":"essai","cwd":"."} | PYTHONIOENCODING=utf-8 python -m tools.pm.bulletin start`
Expected: une ligne `[PM] …` (résumé ou « tableau absent »), `data/sessions/essai.json` créé ; puis `rm data/sessions/essai.json`.

- [ ] **Step 5 : commit**

```bash
git add tools/pm/bulletin.py tests/sandbox/test_pm_bulletin.py
git commit -m "feat(pm): tools/pm/bulletin.py -- bulletin de session ecrit par les hooks (start/tool/stop/end), claim volontaire, resume du tableau en cache au demarrage ; un hook sort toujours 0" -- tools/pm/bulletin.py tests/sandbox/test_pm_bulletin.py
```

---

### Task 5 : `.claude/settings.json` — brancher les quatre hooks

**Files:**
- Create: `.claude/settings.json`
- Test: `tests/sandbox/test_pm_hooks_config.py`

**Interfaces:**
- Consumes: `python -m tools.pm.bulletin <event>` (Task 4). Le hook tourne avec `cwd` = racine du dépôt (ou du worktree, qui porte aussi `tools/pm/`), donc `-m tools.pm.bulletin` se résout sans `$CLAUDE_PROJECT_DIR` — la forme est identique sous PowerShell et Git Bash, et ne contient ni `$`, ni backtick, ni backslash.
- Produces: quatre hooks. `SessionStart` sans matcher (toutes sources : startup, resume, compact, clear) ; `PostToolUse` matcher `Edit|Write|MultiEdit|NotebookEdit` ; `Stop` ; `SessionEnd`.

- [ ] **Step 1 : écrire le test (échoue : fichier absent)**

Créer `tests/sandbox/test_pm_hooks_config.py` :

```python
"""Les hooks du PM : quatre evenements, une commande portable sans backtick ni variable de shell."""
import json
import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_SETTINGS = os.path.join(_ROOT, ".claude", "settings.json")
_INTERDIT = re.compile(r"[`$\\]")


def _hooks():
    with open(_SETTINGS, encoding="utf-8") as fh:
        return json.load(fh)["hooks"]


def test_les_quatre_evenements_du_bulletin_sont_branches():
    h = _hooks()
    assert {"SessionStart", "PostToolUse", "Stop", "SessionEnd"} <= set(h)
    attendu = {"SessionStart": "start", "PostToolUse": "tool", "Stop": "stop", "SessionEnd": "end"}
    for ev, verbe in attendu.items():
        cmds = [x["command"] for grp in h[ev] for x in grp["hooks"] if x["type"] == "command"]
        assert f"python -m tools.pm.bulletin {verbe}" in cmds, (ev, cmds)


def test_PostToolUse_ne_vise_que_les_outils_qui_ecrivent():
    grp = [g for g in _hooks()["PostToolUse"] if any("tools.pm.bulletin" in x["command"] for x in g["hooks"])][0]
    assert grp["matcher"] == "Edit|Write|MultiEdit|NotebookEdit"


def test_aucune_commande_de_hook_ne_contient_backtick_dollar_ou_backslash():
    for ev, grps in _hooks().items():
        for g in grps:
            for x in g["hooks"]:
                assert not _INTERDIT.search(x["command"]), (ev, x["command"])
                assert x.get("timeout", 10) <= 15, "un hook du bulletin doit rester sous la seconde ; 15 s est le plafond"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_hooks_config.py -q -p no:cacheprovider`
Expected: 3 FAILED — `FileNotFoundError: .claude/settings.json`.

- [ ] **Step 3 : écrire la configuration**

`.claude/settings.json` :

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "python -m tools.pm.bulletin start", "timeout": 10}]}
    ],
    "PostToolUse": [
      {"matcher": "Edit|Write|MultiEdit|NotebookEdit",
       "hooks": [{"type": "command", "command": "python -m tools.pm.bulletin tool", "timeout": 10}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "python -m tools.pm.bulletin stop", "timeout": 10}]}
    ],
    "SessionEnd": [
      {"hooks": [{"type": "command", "command": "python -m tools.pm.bulletin end", "timeout": 10}]}
    ]
  }
}
```

- [ ] **Step 4 : lancer, vérifier le vert, puis l'essai RÉEL**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_hooks_config.py -q -p no:cacheprovider`
Expected: 3 passed.
Essai réel (fait par robla, pas par un sous-agent) : ouvrir une NOUVELLE session Claude Code dans le dépôt ; sa première réponse doit contenir le contexte `[PM] …` injecté ; `ls data/sessions/` montre un JSON dont `name` est le nom de la session ; après un `Edit`, `files_touched` s'allonge ; `cat data/pm/hook_errors.log` est vide ou absent. Si le fichier de log contient une erreur, la corriger AVANT de committer : un hook qui échoue en silence sur 6 sessions est pire qu'aucun hook.

- [ ] **Step 5 : commit**

```bash
git add .claude/settings.json tests/sandbox/test_pm_hooks_config.py
git commit -m "feat(pm): hooks SessionStart/PostToolUse/Stop/SessionEnd -> tools.pm.bulletin ; toute session ecrit son bulletin et lit le tableau en cache a sa naissance" -- .claude/settings.json tests/sandbox/test_pm_hooks_config.py
```

---

### Task 6 : `tools/pm/alerts.py` — journal des alertes : nouvelles, disparues, répétées, compteurs

**Files:**
- Create: `tools/pm/alerts.py`
- Test: `tests/sandbox/test_pm_alerts.py`

**Interfaces:**
- Consumes: le dict `board` (Task 3) ; `paths.pm_dir("alerts.jsonl")`.
- Produces:
  - une ligne du journal = `{"ts": float, "cle": str, "id": str, "gravite": str, "message": str, "statut": "emise"|"suivie"|"repetee"}`
  - `charger(path) -> list[dict]` (lignes illisibles ignorées ET comptées dans `charger.illisibles`)
  - `ouvertes(journal) -> dict[cle, ligne_emise]` — clés émises (ou répétées) sans `suivie` postérieure
  - `deja_suivies(journal) -> set[cle]`
  - `diff(board, journal, now) -> {"nouvelles": [alerte], "disparues": [cle], "repetees": [alerte], "lignes": [ligne]}` — `lignes` = ce qu'il faut APPEND au journal pour ce tick
  - `ajouter(path, lignes) -> None`
  - `compteurs(journal, now, fenetre_s=30*86400, delai_suivi_s=48*3600) -> {"emises", "suivies_48h", "fausses_ou_ignorees", "repetees", "ouvertes"}`

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_pm_alerts.py` :

```python
"""Journal des alertes PM : une alerte est emise UNE fois, marquee suivie quand elle disparait, et une alerte
qui REVIENT apres avoir ete suivie est une repetition (regle du registre : deux fois -> cliquet)."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import alerts as AL  # noqa: E402

T0 = 1_800_000_000.0
H = 3600.0


def _a(cle, gravite="alerte"):
    id_ = cle.split(":")[0]
    return {"id": id_, "cle": cle, "gravite": gravite, "message": f"msg {cle}", "preuve": {}}


def _board(*cles):
    return {"alertes": [_a(c) for c in cles]}


def test_premier_tick_tout_est_nouveau_et_le_journal_recoit_une_ligne_emise_par_alerte():
    d = AL.diff(_board("A1:x.py", "A5:sims"), [], T0)
    assert [a["cle"] for a in d["nouvelles"]] == ["A1:x.py", "A5:sims"] and d["disparues"] == [] and d["repetees"] == []
    assert [(l["cle"], l["statut"], l["ts"]) for l in d["lignes"]] == [("A1:x.py", "emise", T0), ("A5:sims", "emise", T0)]


def test_une_alerte_encore_presente_n_est_PAS_re_emise():
    j = AL.diff(_board("A1:x.py"), [], T0)["lignes"]
    d = AL.diff(_board("A1:x.py"), j, T0 + H)
    assert d["nouvelles"] == [] and d["lignes"] == []


def test_une_alerte_disparue_est_marquee_suivie_avec_l_heure():
    j = AL.diff(_board("A1:x.py"), [], T0)["lignes"]
    d = AL.diff(_board(), j, T0 + 2 * H)
    assert d["disparues"] == ["A1:x.py"]
    assert d["lignes"] == [{"ts": T0 + 2 * H, "cle": "A1:x.py", "id": "A1", "gravite": "alerte", "message": "msg A1:x.py", "statut": "suivie"}]


def test_une_alerte_qui_REVIENT_apres_suivi_est_une_REPETITION():
    j = AL.diff(_board("A1:x.py"), [], T0)["lignes"]
    j += AL.diff(_board(), j, T0 + H)["lignes"]
    d = AL.diff(_board("A1:x.py"), j, T0 + 3 * H)
    assert [a["cle"] for a in d["repetees"]] == ["A1:x.py"] and d["nouvelles"] == []
    assert d["lignes"][0]["statut"] == "repetee"


def test_compteurs_distinguent_suivie_sous_48h_et_fausse_ou_ignoree():
    j = AL.diff(_board("A1:vite", "A1:jamais", "A3:tard"), [], T0)["lignes"]
    j += AL.diff(_board("A1:jamais", "A3:tard"), j, T0 + 10 * H)["lignes"]              # A1:vite suivie a 10 h
    j += AL.diff(_board("A1:jamais"), j, T0 + 60 * H)["lignes"]                          # A3:tard suivie a 60 h
    c = AL.compteurs(j, now=T0 + 100 * H)
    # A1:vite suivie a 10 h ; A3:tard suivie a 60 h (> 48 h) ; A1:jamais ouverte depuis 100 h (> 48 h) -> fausse ou ignoree
    assert c == {"emises": 3, "suivies_48h": 1, "fausses_ou_ignorees": 2, "repetees": 0, "ouvertes": 0}
    c_tot = AL.compteurs(j, now=T0 + 20 * H)
    assert c_tot["ouvertes"] == 2 and c_tot["fausses_ou_ignorees"] == 0            # a 20 h, rien n'est encore perime


def test_compteurs_ne_regardent_que_la_fenetre():
    j = AL.diff(_board("A1:vieille"), [], T0 - 40 * 86400)["lignes"]
    j += AL.diff(_board("A1:vieille", "A1:recente"), j, T0)["lignes"]
    c = AL.compteurs(j, now=T0 + H, fenetre_s=30 * 86400)
    assert c["emises"] == 1                                       # seule la recente est dans la fenetre


def test_charger_et_ajouter_font_l_aller_retour_et_comptent_les_lignes_illisibles(tmp_path):
    p = str(tmp_path / "alerts.jsonl")
    lignes = AL.diff(_board("A1:x.py"), [], T0)["lignes"]
    AL.ajouter(p, lignes)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write("{cassee\n")
    j = AL.charger(p)
    assert j == lignes and AL.charger.illisibles == 1
    assert AL.charger(str(tmp_path / "absent.jsonl")) == []
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_alerts.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: No module named 'tools.pm.alerts'`.

- [ ] **Step 3 : implémenter**

`tools/pm/alerts.py` :

```python
"""Journal des alertes PM (paths.pm_dir("alerts.jsonl"), append-only, writer = la session PM).

Cycle d'une clé d'alerte : `emise` (première apparition au tableau) -> `suivie` (elle a disparu du tableau)
-> `repetee` (elle réapparaît après avoir été suivie). Une alerte répétée est la règle du registre des erreurs
appliquée à l'organisation : deux fois -> le PM inscrit le cliquet manquant au backlog, il ne renvoie pas le
message. Les compteurs publiés (ROLES.md via roles_counts) se RECOMPUTENT d'ici, jamais recopiés.
"""
import json
import os


def charger(path):
    charger.illisibles = 0
    out = []
    try:
        with open(path, encoding="utf-8") as fh:
            for ligne in fh:
                ligne = ligne.strip()
                if not ligne:
                    continue
                try:
                    out.append(json.loads(ligne))
                except ValueError:
                    charger.illisibles += 1
    except OSError:
        return []
    return out


charger.illisibles = 0


def ouvertes(journal):
    """Dernier état par clé : la clé est ouverte si sa dernière ligne n'est pas `suivie`."""
    dernier = {}
    for l in journal:
        dernier[l["cle"]] = l
    return {k: v for k, v in dernier.items() if v["statut"] != "suivie"}


def deja_suivies(journal):
    return {l["cle"] for l in journal if l["statut"] == "suivie"}


def _ligne(a, statut, now):
    return {"ts": now, "cle": a["cle"], "id": a["id"], "gravite": a["gravite"], "message": a["message"], "statut": statut}


def diff(board, journal, now):
    ouv, suivies = ouvertes(journal), deja_suivies(journal)
    presentes = {a["cle"]: a for a in board["alertes"]}
    nouvelles = [a for k, a in presentes.items() if k not in ouv and k not in suivies]
    repetees = [a for k, a in presentes.items() if k not in ouv and k in suivies]
    disparues = sorted(k for k in ouv if k not in presentes)
    lignes = [_ligne(a, "emise", now) for a in nouvelles] + [_ligne(a, "repetee", now) for a in repetees]
    for k in disparues:
        l = dict(ouv[k])
        l.update({"ts": now, "statut": "suivie"})
        lignes.append(l)
    return {"nouvelles": nouvelles, "disparues": disparues, "repetees": repetees, "lignes": lignes}


def ajouter(path, lignes):
    if not lignes:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for l in lignes:
            fh.write(json.dumps(l, ensure_ascii=False) + "\n")


def compteurs(journal, now, fenetre_s=30 * 86400, delai_suivi_s=48 * 3600):
    journal = [l for l in journal if l["ts"] <= now]           # un compteur évalué à `now` ne voit pas l'avenir
    debut = now - fenetre_s
    emissions = [l for l in journal if l["statut"] in ("emise", "repetee") and l["ts"] >= debut]
    suivis = {}
    for l in journal:
        if l["statut"] == "suivie":
            suivis.setdefault(l["cle"], []).append(l["ts"])
    suivies_48h = fausses = ouvertes_n = 0
    for e in emissions:
        apres = [t for t in suivis.get(e["cle"], []) if t >= e["ts"]]
        if apres and min(apres) - e["ts"] <= delai_suivi_s:
            suivies_48h += 1
        elif apres:
            fausses += 1
        elif now - e["ts"] > delai_suivi_s:
            fausses += 1
        else:
            ouvertes_n += 1
    return {"emises": len(emissions), "suivies_48h": suivies_48h, "fausses_ou_ignorees": fausses,
            "repetees": sum(1 for l in emissions if l["statut"] == "repetee"), "ouvertes": ouvertes_n}
```

- [ ] **Step 4 : lancer, vérifier le vert + portes**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_alerts.py -q -p no:cacheprovider`
Expected: 7 passed.
Run: `PYTHONIOENCODING=utf-8 python tools/check_fabricated_defaults.py --only tools/pm/alerts.py && PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py --only tools/pm/alerts.py`
Expected: exit 0 ×2.

- [ ] **Step 5 : commit**

```bash
git add tools/pm/alerts.py tests/sandbox/test_pm_alerts.py
git commit -m "feat(pm): tools/pm/alerts.py -- journal append-only des alertes (emise/suivie/repetee), diff par tick, compteurs recomputes (suivies 48 h, fausses ou ignorees)" -- tools/pm/alerts.py tests/sandbox/test_pm_alerts.py
```

---

### Task 7 : `docs/roadmap/ROLES.md`, porte 21 `check_roles_registry`, `roles_counts.py`

**Files:**
- Create: `docs/roadmap/ROLES.md`
- Create: `tools/check_roles_registry.py`
- Create: `tools/pm/roles_counts.py`
- Modify: `tools/hooks/pre-commit` (avant `[ "$fail" -ne 0 ]`, l.357) ; `tools/check_gate_mutation.py` (dict `PORTES`, après l'entrée `"17"`) ; `tools/check_synthesis_counts.py` (`_DOCS` l.50-59, `COMPTEURS` l.121-136) ; regex `staged_syn` du hook (l.149) ; `CLAUDE.md` (phrase et balise `count:portes_hook`, l.219)
- Test: `tests/sandbox/test_roles_registry_gate.py`, `tests/sandbox/test_pm_roles_counts.py`

**Interfaces:**
- Produces:
  - `check_roles_registry.lignes(txt) -> list[dict]` — `{"role", "statut", "cellules": [7 str], "ligne": int}` pour chaque ligne `| **Nom** | …`
  - `check_roles_registry.defauts(lignes) -> list[dict]` — `{"role", "ligne", "raison"}` ; VERDICT du cliquet, jamais un booléen
  - `check_roles_registry.main(argv=None) -> int` — `--report` ; exit 1 si `defauts` non vide ; pas de baseline (aucune dette tolérée)
  - `roles_counts.bucket(chemin) -> "science"|"methodo"|"autre"`
  - `roles_counts.compute_counts(journal, fichiers, now) -> dict` — `{"alertes": compteurs(...), "fichiers": {"science": n, "methodo": n, "autre": n}, "ratio_science_methodo": float|None, "depuis": "2026-09-16"}`
  - `roles_counts.main(argv=None) -> int` — écrit `paths.pm_dir("ROLES_COUNTS.json")`
  - compteurs porte 8 : `roles_instancies`, `roles_candidats` (lus dans `ROLES.md`)
- Décision consignée (écart à la spec §6.2) : le ratio science/méthodo est une fenêtre GLISSANTE, donc il ne peut pas être une balise `count:` (la porte 8 la vérifie au commit, elle serait périmée chaque jour). Il vit dans `ROLES_COUNTS.json` ; `ROLES.md` ne porte en balise que les comptes STRUCTURELS (instanciés, candidats) et une ligne datée « dernier bilan », réécrite par le PM à chaque revue des rôles.

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_roles_registry_gate.py` :

```python
"""Porte 21 : une ligne de ROLES.md sans ses cinq colonnes est une regle documentee, pas un role."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_roles_registry as R  # noqa: E402

ENTETE = ("| Rôle | Statut | Instrument | Contrôle positif | Coût mesuré | Compteurs | Dissolution / naissance |\n"
          "| --- | --- | --- | --- | --- | --- | --- |\n")
PLEINE = "| **PM** | instancié | `tools/pm/board.py::compute` | fixtures A1-A8 + no-op | tokens/tick : non mesuré | `ROLES_COUNTS.json` | précision < 1/10 sur 30 j |\n"
CREUSE = "| **Stratège** | instancié | workflow figé | témoin périmé tué | — | propositions / acceptées | deux passes sans changement |\n"
CANDIDAT_OK = "| **Régisseur des runs** | candidat | — | — | — | — | deux runs abandonnés en 30 j |\n"
CANDIDAT_NU = "| **Intégrateur** | candidat | — | — | — | — | |\n"
STATUT_INCONNU = "| **X** | en cours | a | b | c | d | e |\n"


def test_lignes_lit_role_statut_et_sept_cellules():
    L = R.lignes(ENTETE + PLEINE)
    assert len(L) == 1 and L[0]["role"] == "PM" and L[0]["statut"] == "instancié" and len(L[0]["cellules"]) == 7


def test_une_ligne_instanciee_COMPLETE_ne_produit_aucun_defaut():
    assert R.defauts(R.lignes(ENTETE + PLEINE)) == []


def test_CONTRE_EXEMPLE_GELE_une_cellule_vide_sur_un_role_instancie_est_un_defaut():
    d = R.defauts(R.lignes(ENTETE + CREUSE))
    assert len(d) == 1 and d[0]["role"] == "Stratège" and "Coût mesuré" in d[0]["raison"]


def test_un_candidat_doit_porter_son_critere_de_naissance_et_rien_d_autre():
    assert R.defauts(R.lignes(ENTETE + CANDIDAT_OK)) == []
    d = R.defauts(R.lignes(ENTETE + CANDIDAT_NU))
    assert len(d) == 1 and "naissance" in d[0]["raison"]


def test_un_statut_hors_vocabulaire_est_un_defaut():
    d = R.defauts(R.lignes(ENTETE + STATUT_INCONNU))
    assert len(d) == 1 and "statut" in d[0]["raison"]


def test_le_registre_REEL_du_depot_passe_la_porte():
    with open(os.path.join(R._ROOT, "docs", "roadmap", "ROLES.md"), encoding="utf-8") as fh:
        L = R.lignes(fh.read())
    assert len(L) >= 3, "le périmètre est vide, le test ne prouverait rien"
    assert R.defauts(L) == []


def test_main_rend_1_sur_un_defaut_et_0_sinon(tmp_path, monkeypatch):
    p = tmp_path / "ROLES.md"
    p.write_text(ENTETE + CREUSE, encoding="utf-8")
    monkeypatch.setattr(R, "_REGISTRE", str(p))
    assert R.main([]) == 1
    p.write_text(ENTETE + PLEINE, encoding="utf-8")
    assert R.main([]) == 0
```

Créer `tests/sandbox/test_pm_roles_counts.py` :

```python
"""Compteurs des roles : recomputes depuis le journal et les fichiers modifies, jamais recopies."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import roles_counts as RC  # noqa: E402

T0 = 1_800_000_000.0


def test_bucket_par_chemin_science_methodo_autre():
    assert RC.bucket("docs/EDR/X.md") == "science" and RC.bucket("results/a.json") == "science"
    assert RC.bucket("docs/preregistrations/R.json") == "science"
    for p in ("tools/check_x.py", "tests/sandbox/test_y.py", "docs/REF/Z.md", "docs/roadmap/P.md", "CLAUDE.md"):
        assert RC.bucket(p) == "methodo", p
    assert RC.bucket("src/agents/x.py") == "autre" and RC.bucket("tools/evo_runs/r.py") == "autre"


def test_compute_counts_ratio_et_None_sans_methodo():
    c = RC.compute_counts([], ["docs/EDR/a.md", "results/b.json", "tools/check_c.py", "src/d.py"], T0)
    assert c["fichiers"] == {"science": 2, "methodo": 1, "autre": 1} and c["ratio_science_methodo"] == 2.0
    c2 = RC.compute_counts([], ["docs/EDR/a.md"], T0)
    assert c2["ratio_science_methodo"] is None                   # pas de dénominateur : « je ne sais pas », pas inf
    assert c["alertes"]["emises"] == 0 and c["depuis"] == RC.DEBUT


def test_main_ecrit_ROLES_COUNTS_sous_pm_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    assert RC.main(["--repo-root", os.getcwd()]) == 0
    j = json.loads((tmp_path / "pm" / "ROLES_COUNTS.json").read_text(encoding="utf-8"))
    assert set(j) >= {"alertes", "fichiers", "ratio_science_methodo", "depuis", "generated_at"}
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_roles_registry_gate.py tests/sandbox/test_pm_roles_counts.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError` ×2.

- [ ] **Step 3 : implémenter la porte, les compteurs, le registre**

`tools/check_roles_registry.py` :

```python
"""Porte 21 — registre des rôles : toute ligne de docs/roadmap/ROLES.md porte ses cinq colonnes.

  python tools/check_roles_registry.py            # cliquet : exit 1 si une ligne est creuse
  python tools/check_roles_registry.py --report   # état, exit 0

Un rôle `instancié` sans instrument, contrôle positif, coût, compteurs ou critère de dissolution est une règle
DOCUMENTÉE (classe E10) ; un `candidat` porte au moins son critère de naissance. Pas de baseline : aucune
dette tolérée, le registre naît complet (spec 2026-09-16 §3.6).
"""
import argparse
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTRE = os.path.join(_ROOT, "docs", "roadmap", "ROLES.md")
_ROW = re.compile(r"^\|\s*\*\*([^*|]+)\*\*\s*\|(.*)$")
COLONNES = ("Rôle", "Statut", "Instrument", "Contrôle positif", "Coût mesuré", "Compteurs", "Dissolution / naissance")
STATUTS = ("instancié", "candidat", "dissous")
_VIDE = ("", "—", "-")


def lignes(txt):
    out = []
    for i, ligne in enumerate(txt.splitlines(), start=1):
        m = _ROW.match(ligne.strip())
        if not m:
            continue
        cellules = [c.strip() for c in ligne.strip().strip("|").split(" | ")]
        out.append({"role": m.group(1).strip(), "statut": cellules[1].strip() if len(cellules) > 1 else "",
                    "cellules": cellules, "ligne": i})
    return out


def defauts(L):
    out = []
    for l in L:
        c = l["cellules"]
        if len(c) != len(COLONNES):
            out.append({"role": l["role"], "ligne": l["ligne"], "raison": f"{len(c)} cellules au lieu de {len(COLONNES)}"})
            continue
        if l["statut"] not in STATUTS:
            out.append({"role": l["role"], "ligne": l["ligne"], "raison": f"statut {l['statut']!r} hors vocabulaire {STATUTS}"})
            continue
        if l["statut"] == "instancié":
            creuses = [COLONNES[i] for i in range(2, 7) if c[i] in _VIDE]
            if creuses:
                out.append({"role": l["role"], "ligne": l["ligne"], "raison": "colonnes creuses : " + ", ".join(creuses)})
        elif l["statut"] == "candidat" and c[6] in _VIDE:
            out.append({"role": l["role"], "ligne": l["ligne"], "raison": "candidat sans critère de naissance (7e colonne)"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true", help="état complet, exit 0")
    args = ap.parse_args(argv)
    with open(_REGISTRE, encoding="utf-8") as fh:
        L = lignes(fh.read())
    d = defauts(L)
    print(f"rôles : {len(L)} | instanciés : {sum(1 for l in L if l['statut'] == 'instancié')} | "
          f"candidats : {sum(1 for l in L if l['statut'] == 'candidat')} | lignes creuses : {len(d)}")
    for x in d:
        print(f"  [CREUSE] {x['role']} (l.{x['ligne']}) : {x['raison']}")
    if args.report:
        return 0
    if d:
        print("Un rôle sans ses cinq colonnes est une règle documentée (E10), pas un rôle. Compléter la ligne.")
        return 1
    print("OK : toutes les lignes de ROLES.md portent leurs cinq colonnes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`tools/pm/roles_counts.py` :

```python
"""Compteurs des rôles, RECOMPUTÉS (spec §6.2) : alertes du PM (journal) et ratio science/méthodo par CHEMINS de
fichiers modifiés depuis DEBUT. Écrit paths.pm_dir("ROLES_COUNTS.json") — jamais recopié dans ROLES.md à la main.
science = docs/EDR, results, docs/preregistrations ; méthodo = tools/check_*, tests/sandbox, docs/REF, docs/roadmap,
CLAUDE.md ; le reste = autre, publié à part. Point de départ publié : 26 / 78 (2026-09-08)."""
import argparse
import json
import os
import subprocess
import sys
import time

from src import paths
from tools.pm import alerts as AL

DEBUT = "2026-09-16"
_SCIENCE = ("docs/EDR/", "results/", "docs/preregistrations/")
_METHODO = ("tools/check_", "tests/sandbox/", "docs/REF/", "docs/roadmap/")


def bucket(chemin):
    c = chemin.replace("\\", "/")
    if c == "CLAUDE.md" or c.startswith(_METHODO):
        return "methodo"
    if c.startswith(_SCIENCE):
        return "science"
    return "autre"


def fichiers_modifies(repo_root, depuis=DEBUT):
    try:
        out = subprocess.run(["git", "log", "--all", f"--since={depuis}", "--name-only", "--format="], cwd=repo_root,
                             capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return sorted({l.strip() for l in out.stdout.splitlines() if l.strip()})


def compute_counts(journal, fichiers, now):
    f = {"science": 0, "methodo": 0, "autre": 0}
    for c in (fichiers or []):
        f[bucket(c)] += 1
    ratio = (f["science"] / f["methodo"]) if f["methodo"] else None
    return {"generated_at": now, "depuis": DEBUT, "alertes": AL.compteurs(journal, now), "fichiers": f,
            "ratio_science_methodo": ratio, "fichiers_disponibles": fichiers is not None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo-root", default=os.getcwd())
    args = ap.parse_args(argv)
    now = time.time()
    c = compute_counts(AL.charger(paths.pm_dir("alerts.jsonl")), fichiers_modifies(args.repo_root), now)
    os.makedirs(paths.pm_dir(), exist_ok=True)
    with open(paths.pm_dir("ROLES_COUNTS.json"), "w", encoding="utf-8") as fh:
        json.dump(c, fh, ensure_ascii=False, indent=1)
    print(f"alertes {c['alertes']} | fichiers {c['fichiers']} | science/méthodo = {c['ratio_science_methodo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`docs/roadmap/ROLES.md` :

```markdown
# ROLES — registre des rôles de la flotte AGAGI

**Writer unique : la session PM.** Une ligne par rôle ou lentille. Statuts : `instancié` · `candidat` · `dissous`.
Cinq colonnes obligatoires pour un rôle instancié (porte 21, `tools/check_roles_registry.py`) : une ligne creuse
est une règle documentée (E10), pas un rôle. Les compteurs VIVANTS (alertes émises / suivies 48 h / fausses,
ratio science/méthodo par chemins) sont recomputés par `python -m tools.pm.roles_counts` dans
`data/pm/ROLES_COUNTS.json` ; ce fichier ne porte en balise que les comptes structurels.

**3 rôles instanciés** <!-- count:roles_instancies=3 --> · **7 candidats** <!-- count:roles_candidats=7 --> ·
dernier bilan : aucun (premier bilan à la première revue des rôles, 30 jours ou 20 records).
Règle 1:1 : tant que le ratio science/méthodo n'a pas franchi 1:1, aucun rôle neuf sans en réduire un autre.
Spec : `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md`.

| Rôle | Statut | Instrument | Contrôle positif | Coût mesuré | Compteurs | Dissolution / naissance |
| --- | --- | --- | --- | --- | --- | --- |
| **PM** | instancié | `tools/pm/board.py::compute`, déterministe, calibré par injection ; tick `/pm` | fixtures A1-A8 + no-op exact (`tests/sandbox/test_pm_board.py`) | tokens/tick : non mesuré au 2026-09-16, à publier au 1er bilan | `ROLES_COUNTS.json` : alertes émises / suivies 48 h / fausses ou ignorées / répétées | précision < 1/10 sur 30 j ; ou toute alerte encore émise attrapable par une porte ; ou tokens > 15 % de la fenêtre sans acte |
| **Stratège** | instancié | `.claude/workflows/strategist.js`, prompts figés, sur événement (plan 3) | candidat PÉRIMÉ connu glissé et tué à chaque passe ; sinon passe NULLE | tokens/passe : non mesuré, à publier au 1er bilan | propositions faites / acceptées par robla / amendées / réfutées par son panel (baseline : reco du 2026-09-08 tombée) | deux passes `full` sans changement de rang accepté ; ou témoin non tué deux fois (re-scellage des prompts) ; ou coût > 15 % |
| **Réfutateur** | instancié | `.claude/workflows/refutateur.js`, 8-10 prompts figés, portes 18/19/20 livrées d'abord (plan 2) | trois records-témoins gelés (GRAB-COST 09-09, S2-BLIND v1, RETAIN-COMPOSE pré-rétractation) + no-op LOCK-002 | tokens/revue : non mesuré, à publier au 1er bilan | critiques émises / confirmées / fausses ; taux de -bis après run (baseline 3/58) | < 1 confirmée sur 10 revues ; ou ≥ 80 % attrapables par une porte ; ou -bis après run ≥ 3/58 après 20 sceaux ; ou coût > 15 % |
| **Régisseur des runs** | candidat | — | — | — | — | réfuté le 2026-09-16 (compte gonflé par un apparieur faillible ; occurrences déjà closes ou déjà cliquets) ; naît sur deux runs abandonnés ou contaminés en 30 j malgré `cost_guard` et le bail |
| **Intégrateur** | candidat | — | — | — | — | réfuté le 2026-09-16 (prémisse périmée : d1/main résolu le 07-28) ; naît sur deux collisions de numéro ou deux merges perdus en 30 j |
| **Greffier-métrologue** | candidat | — | — | — | — | réfuté le 2026-09-16 (la promotion documenté→exécutable A été appliquée, P2.25) ; naît sur deux classes restées `documenté` après deux récidives |
| **Bibliothécaire de la doctrine** | candidat | — | — | — | — | réfuté le 2026-09-16 (rare, bon marché après coup) ; naît sur deux sessions trompées par la même phrase périmée, datées |
| **Auditeur des angles morts** | candidat | — | — | — | — | → cliquet « hors motif » + lentille du stratège sur tout élargissement de détecteur (backlog) ; ne naît pas comme rôle |
| **Archiviste de l'évidence** | candidat | — | — | — | — | constat vrai (69/20/18) devenu la porte 19 (plan 2) ; ne naît pas comme rôle |
| **Greffier de passage** | candidat | — | — | — | — | réfuté le 2026-09-16 (une seule occurrence) ; naît sur deux occurrences datées de travail dupliqué faute de brief |
| **Scribe des records** | dissous | témoin du panel — fonction couverte par la porte 1 | doit être TUÉ à chaque revue des rôles, sinon la passe est nulle | — | — | témoin permanent : ne renaît jamais |
```

Compter les lignes : 3 `instancié`, 7 `candidat`, 1 `dissous` — les balises disent 3 et 7.

Brancher la porte dans `tools/hooks/pre-commit`, avant la ligne `[ "$fail" -ne 0 ] && echo "   (urgence : git commit --no-verify)"` :

```sh
# 21. REGISTRE DES ROLES (2026-09-16) -- spec pm-stratege-refutateur section 3.6 : toute ligne de
# docs/roadmap/ROLES.md porte ses cinq colonnes (instrument, controle positif, cout, compteurs, dissolution).
# Une ligne creuse est une regle documentee (E10). Pas de baseline : le registre nait complet.
staged_roles=$(git diff --cached --name-only --diff-filter=AM | grep -E '^docs/roadmap/ROLES\.md$')
if [ -n "$staged_roles" ]; then
  PYTHONIOENCODING=utf-8 python tools/check_roles_registry.py || {
    echo ""
    echo "-> Une ligne de ROLES.md n'a pas ses cinq colonnes : un role sans instrument, controle positif,"
    echo "   cout, compteurs ou critere de dissolution est une regle documentee, pas un role. Completer."
    fail=1
  }
fi

```

Dans `tools/check_gate_mutation.py`, ajouter après l'entrée `"17": {...},` (avant le `}` qui ferme `PORTES`) :

```python
    "21": {
        "module": "tools.check_roles_registry",
        "titre": "registre des rôles : cinq colonnes obligatoires (spec PM 2026-09-16)",
        "temoins": ["tests/sandbox/test_roles_registry_gate.py"],
        "mutations": [{
            "nom": "une colonne creuse sur un rôle instancié n'est plus un défaut",
            "avant": "            creuses = [COLONNES[i] for i in range(2, 7) if c[i] in _VIDE]",
            "apres": "            creuses = []",
            "motif": ("le verdict du cliquet — un rôle sans instrument ni contrôle positif passerait, c'est-à-dire "
                      "une règle documentée déguisée en rôle (E10)"),
        }],
    },
```

Dans `tools/check_synthesis_counts.py` : ajouter `os.path.join("docs", "roadmap", "ROLES.md"),` au tuple `_DOCS`, et dans `COMPTEURS` :

```python
    "roles_instancies": lambda: _roles("instancié"),
    "roles_candidats": lambda: _roles("candidat"),
```

avec, au-dessus de `COMPTEURS` :

```python
def _roles(statut):
    from tools.check_roles_registry import lignes
    return sum(1 for l in lignes(_lire(os.path.join("docs", "roadmap", "ROLES.md"))) if l["statut"] == statut)
```

Dans la regex `staged_syn` du hook (l.149), ajouter `|docs/roadmap/ROLES\.md` dans le groupe des fichiers déclencheurs (copier la forme des autres alternatives de la même regex).

Dans `CLAUDE.md` l.219, remplacer `**17 gardes** <!-- count:portes_hook=17 -->` par `**18 gardes** <!-- count:portes_hook=18 -->` (18 modules `check_*` distincts dans le hook après ajout). Fichier PARTAGÉ : `snapshot` avant, `verify` avant commit.

- [ ] **Step 4 : lancer les témoins, la mutation, les portes 8 et 15, le recensement**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_roles_registry_gate.py tests/sandbox/test_pm_roles_counts.py tests/sandbox/test_gate_mutation.py tests/sandbox/test_synthesis_counts.py -q -p no:cacheprovider`
Expected: tous PASS (dont `test_toute_porte_du_hook_est_DECLAREE_ici_ou_HORS_PERIMETRE`).
Run: `PYTHONIOENCODING=utf-8 python tools/check_gate_mutation.py --only 21`
Expected: `intact VERT`, mutation `TUEE`.
Run: `PYTHONIOENCODING=utf-8 python tools/check_synthesis_counts.py`
Expected: exit 0 (balises `portes_hook=18`, `roles_instancies=3`, `roles_candidats=7` concordent).
Run: `PYTHONIOENCODING=utf-8 python tools/check_roles_registry.py --report && PYTHONIOENCODING=utf-8 python -m tools.pm.roles_counts`
Expected: `lignes creuses : 0` ; `ROLES_COUNTS.json` écrit.
Run: `PYTHONIOENCODING=utf-8 python tools/check_test_census.py --update-baseline`
Expected: baseline re-gelée avec les 7 nouveaux fichiers de tests (protège leur disparition future).

- [ ] **Step 5 : commit (fichiers PARTAGÉS : `snapshot`/`verify` sur CLAUDE.md, pre-commit, check_gate_mutation, check_synthesis_counts)**

```bash
git add docs/roadmap/ROLES.md tools/check_roles_registry.py tools/pm/roles_counts.py tests/sandbox/test_roles_registry_gate.py tests/sandbox/test_pm_roles_counts.py tools/hooks/pre-commit tools/check_gate_mutation.py tools/check_synthesis_counts.py CLAUDE.md tools/test_census_baseline.json
git commit -m "feat(pm): docs/roadmap/ROLES.md (3 roles, 7 candidats, 1 temoin) + porte 21 check_roles_registry (cinq colonnes, mutation tuee) + roles_counts (alertes, ratio science/methodo par chemins) ; portes_hook 17 -> 18" -- docs/roadmap/ROLES.md tools/check_roles_registry.py tools/pm/roles_counts.py tests/sandbox/test_roles_registry_gate.py tests/sandbox/test_pm_roles_counts.py tools/hooks/pre-commit tools/check_gate_mutation.py tools/check_synthesis_counts.py CLAUDE.md tools/test_census_baseline.json
```

---

### Task 8 : `tools/pm/tick.py` + skill `/pm` — le tick de la session PM

**Files:**
- Create: `tools/pm/tick.py`
- Create: `.claude/skills/pm/SKILL.md`
- Test: `tests/sandbox/test_pm_tick.py`

**Interfaces:**
- Consumes: `board.compute/snapshot/render_md` (Task 3), `alerts.*` (Task 6), `roles_counts.compute_counts` (Task 7), `bulletin.session_id_courant`, `tools.jobs.lease.acquire/read/is_live`, `snapshot.read_registry`.
- Produces:
  - `prendre_bail_pm(owner, pid, *, leases_dir=None, ttl_s=7200.0) -> dict` — `{"ok": bool, "detenteur": str|None}` : lève jamais ; refuse si un bail `pm` VIVANT appartient à un autre pid
  - `digest(board, d, counts) -> str` — ce que la session PM lit : AVEUGLE, nouvelles, répétées (→ cliquet), disparues, charge, compteurs
  - `main(argv=None) -> int` — `--owner`, `--pid`, `--repo-root`, `--registry-dir`, `--sessions-dir`, `--leases-dir` ; exit 0 ; exit 2 si le bail `pm` est tenu par un autre PM VIVANT (rien d'écrit)

- [ ] **Step 1 : écrire les tests**

Créer `tests/sandbox/test_pm_tick.py` :

```python
"""Le tick PM : un seul PM vivant (bail pm porte par le PID de la session), un tableau ecrit, un journal tenu."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.jobs import lease as L  # noqa: E402
from tools.pm import tick as TK  # noqa: E402


def test_le_bail_pm_est_pris_par_le_PID_de_la_session_et_repris_par_le_meme_pid(tmp_path):
    r = TK.prendre_bail_pm("agagi-11", os.getpid(), leases_dir=tmp_path)
    assert r == {"ok": True, "detenteur": None}
    assert TK.prendre_bail_pm("agagi-11", os.getpid(), leases_dir=tmp_path)["ok"] is True      # tick suivant, meme pid
    lz = L.read("pm", leases_dir=tmp_path)
    assert lz.owner == "agagi-11" and lz.pid == os.getpid()


def test_un_second_PM_vivant_est_REFUSE_et_nomme(tmp_path):
    TK.prendre_bail_pm("agagi-11", os.getpid(), leases_dir=tmp_path)
    r = TK.prendre_bail_pm("agagi-52", os.getpid() + 1, leases_dir=tmp_path)
    assert r["ok"] is False and "agagi-11" in r["detenteur"]


def test_un_bail_pm_dont_le_detenteur_est_mort_est_reprenable(tmp_path):
    L.acquire("pm", owner="fantome", leases_dir=tmp_path, pid=999_999)
    assert TK.prendre_bail_pm("agagi-11", os.getpid(), leases_dir=tmp_path)["ok"] is True


def test_digest_nomme_les_repetees_comme_cliquets_a_inscrire():
    board = {"aveugle": ["bails (tools/jobs)"], "charge_connue": {"sims_en_vol": 0, "cpu_5min_pct": 3.0, "bails_vivants": []},
             "alertes": [], "sessions": []}
    d = {"nouvelles": [{"cle": "A1:x.py", "message": "m1", "gravite": "alerte"}],
         "repetees": [{"cle": "A2:kuzu", "message": "m2", "gravite": "alerte"}], "disparues": ["A4:abc"], "lignes": []}
    counts = {"alertes": {"emises": 3, "suivies_48h": 1, "fausses_ou_ignorees": 0, "repetees": 1, "ouvertes": 2},
              "fichiers": {"science": 1, "methodo": 2, "autre": 0}, "ratio_science_methodo": 0.5}
    t = TK.digest(board, d, counts)
    assert "AVEUGLE SUR bails" in t and "NOUVELLE A1:x.py" in t and "REPETEE A2:kuzu" in t and "cliquet" in t
    assert "suivie A4:abc" in t and "science/méthodo = 0.5" in t


def test_main_ecrit_tableau_journal_compteurs_et_sort_0(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    code = TK.main(["--owner", "agagi-test", "--pid", str(os.getpid()), "--repo-root", os.getcwd(),
                    "--registry-dir", str(tmp_path / "aucun"), "--sessions-dir", str(tmp_path / "aucun"),
                    "--leases-dir", str(tmp_path / "leases")])
    assert code == 0
    assert (tmp_path / "pm" / "BOARD.json").exists() and (tmp_path / "pm" / "ROLES_COUNTS.json").exists()
    assert (tmp_path / "pm" / "alerts.jsonl").exists() or True     # aucune alerte sur un registre absent : journal vide admis


def test_main_refuse_quand_un_autre_PM_vit_et_n_ecrit_RIEN(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    L.acquire("pm", owner="agagi-11", leases_dir=tmp_path / "leases", pid=os.getpid())
    code = TK.main(["--owner", "agagi-52", "--pid", str(os.getpid() + 1), "--repo-root", os.getcwd(),
                    "--registry-dir", str(tmp_path / "aucun"), "--sessions-dir", str(tmp_path / "aucun"),
                    "--leases-dir", str(tmp_path / "leases")])
    assert code == 2 and not (tmp_path / "pm").exists()
```

- [ ] **Step 2 : lancer, vérifier l'échec**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_tick.py -q -p no:cacheprovider`
Expected: `ModuleNotFoundError: No module named 'tools.pm.tick'`.

- [ ] **Step 3 : implémenter le tick et le skill**

`tools/pm/tick.py` :

```python
"""Le tick de la session PM — la partie DÉTERMINISTE (spec §3.3) :

    python -m tools.pm.tick [--owner <name>] [--pid <pid de la session Claude>]

1. bail `pm` porté par le PID de la session Claude (unicité : un autre PM VIVANT -> exit 2, rien d'écrit) ;
2. tableau (BOARD.json / BOARD.md) ; 3. diff des alertes contre le journal, append ; 4. compteurs ;
5. un DIGEST pour la session PM : ce qui demande un jugement (message ciblé, investigation, cliquet à inscrire).
La session PM ne tient aucun état en contexte : tout est relu d'ici à chaque tick.
"""
import argparse
import os
import sys
import time

from src import paths
from tools.jobs import lease as L
from tools.pm import alerts as AL
from tools.pm import roles_counts as RC
from tools.pm.board import compute, render_md
from tools.pm.bulletin import session_id_courant
from tools.pm.snapshot import read_registry, snapshot

TTL_PM_S = 7200.0


def prendre_bail_pm(owner, pid, *, leases_dir=None, ttl_s=TTL_PM_S):
    cur = L.read("pm", leases_dir=leases_dir)
    if cur is not None and L.is_live(cur) and cur.pid != pid:
        return {"ok": False, "detenteur": f"{cur.owner or '?'} (pid={cur.pid}, expire dans {cur.expires_at - time.time():.0f} s)"}
    L.acquire("pm", owner=owner, ttl_s=ttl_s, pid=pid, leases_dir=leases_dir)
    return {"ok": True, "detenteur": None}


def _identite(registry_dir):
    """(name, pid) de la session Claude qui lance le tick, via le registre natif ; (None, None) si inconnu."""
    sid = session_id_courant(registry_dir)
    for r in (read_registry(registry_dir) or []):
        if sid and r.get("session_id") == sid:
            return r.get("name"), r.get("pid")
    return None, None


def digest(board, d, counts):
    L_ = [f"[PM] AVEUGLE SUR {a}" for a in board["aveugle"]]
    c = board["charge_connue"]
    L_.append(f"[PM] charge connue : sims={c['sims_en_vol']} cpu5={c['cpu_5min_pct']} bails={c['bails_vivants']}")
    for a in d["nouvelles"]:
        L_.append(f"[PM] NOUVELLE {a['cle']} ({a['gravite']}) — {a['message']} -> décider : message ciblé / investigation / note")
    for a in d["repetees"]:
        L_.append(f"[PM] REPETEE {a['cle']} — {a['message']} -> inscrire le cliquet manquant au backlog (deux fois = promu)")
    for k in d["disparues"]:
        L_.append(f"[PM] suivie {k}")
    ca = counts["alertes"]
    L_.append(f"[PM] compteurs : émises {ca['emises']} · suivies 48 h {ca['suivies_48h']} · fausses/ignorées "
              f"{ca['fausses_ou_ignorees']} · répétées {ca['repetees']} · ouvertes {ca['ouvertes']} ; "
              f"fichiers {counts['fichiers']} ; science/méthodo = {counts['ratio_science_methodo']}")
    if not d["nouvelles"] and not d["repetees"] and not d["disparues"]:
        L_.append("[PM] rien de nouveau (noop)")
    return "\n".join(L_)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--owner", default=None)
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--repo-root", default=os.getcwd())
    ap.add_argument("--registry-dir", default=None)
    ap.add_argument("--sessions-dir", default=None)
    ap.add_argument("--leases-dir", default=None)
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    name, pid = _identite(args.registry_dir)
    owner, pid = args.owner or name or "pm-inconnu", args.pid or pid or os.getpid()
    bail = prendre_bail_pm(owner, pid, leases_dir=args.leases_dir)
    if not bail["ok"]:
        print(f"[PM] REFUS : un PM VIVANT tient déjà le bail pm : {bail['detenteur']}. Cette session ne prend pas le rôle.")
        return 2
    now = time.time()
    board = compute(snapshot(args.repo_root, registry_dir=args.registry_dir, sessions_dir=args.sessions_dir,
                             leases_dir=args.leases_dir, now=now))
    os.makedirs(paths.pm_dir(), exist_ok=True)
    import json
    with open(paths.pm_dir("BOARD.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False, indent=1, default=str)
    with open(paths.pm_dir("BOARD.md"), "w", encoding="utf-8") as fh:
        fh.write(render_md(board))
    journal = AL.charger(paths.pm_dir("alerts.jsonl"))
    d = AL.diff(board, journal, now)
    AL.ajouter(paths.pm_dir("alerts.jsonl"), d["lignes"])
    counts = RC.compute_counts(journal + d["lignes"], RC.fichiers_modifies(args.repo_root), now)
    with open(paths.pm_dir("ROLES_COUNTS.json"), "w", encoding="utf-8") as fh:
        json.dump(counts, fh, ensure_ascii=False, indent=1)
    print(digest(board, d, counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

`.claude/skills/pm/SKILL.md` :

```markdown
---
name: pm
description: Tick de la session PM AGAGI — tableau de la flotte, alertes ciblées, journal, ROLES.md. À lancer dans UNE session dédiée, en boucle auto-rythmée (/loop). Refuse le rôle si un autre PM vit.
---

# /pm — le tick de la session PM

Tu es la session PM (spec `docs/superpowers/specs/2026-09-16-pm-stratege-refutateur-design.md` §2.1, §3.3).
Tu ne pilotes AUCUNE autre session : tu lis, tu préviens, tu journalises, tu nommes les cliquets manquants.
Tu ne tiens aucun état en contexte — tout est relu par le tick.

## À chaque tick

1. `PYTHONIOENCODING=utf-8 python -m tools.pm.tick` — s'il rend `[PM] REFUS`, tu N'ES PAS le PM : dis-le à robla
   et arrête la boucle (`ScheduleWakeup stop`). Le digest imprimé est ta seule entrée.
2. Pour chaque ligne `NOUVELLE`, UNE action, jamais deux :
   - **message ciblé** (A1 fichier partagé, A6 même P-item, A5 charge) : `SendMessage` au `name` de la session
     concernée (la clé et la preuve sont dans `data/pm/BOARD.json`) ; première ligne = la clé et le fait ;
     UNE fois par clé et par session, jamais de relance ;
   - **investigation** (A3 worktree, A4 commit amputé) : un worker en LECTURE (`Agent`, chemins absolus,
     aucun commit) qui rend la preuve ; puis note dans le digest suivant ;
   - **note** (A7, A8 : informations) : rien à envoyer.
3. Pour chaque ligne `REPETEE` : inscrire le CLIQUET manquant dans `docs/roadmap/PRIORITES_ET_DETTES.md`
   (prochain numéro libre, clause `closes_when`, preuve = la clé et ses deux dates depuis `alerts.jsonl`),
   après `check_staged_authorship.snapshot` ; commit path-scoped après accord de robla.
4. Événements pour le stratège (plan 3, quand il existe) : nouveau `docs/EDR/*.md`, entrée passée CLOS,
   `RÉTRACTÉ`/`-bis`, run nul — sinon ignorer ce point.
5. `ScheduleWakeup` 1200-1800 s ; `noop=true` si le digest dit `rien de nouveau`.

## Interdits

- Envoyer deux fois le même message ; demander à une session une action que ta propre session ne pourrait pas
  faire (permission laundering) ; écrire dans un fichier dont tu n'es pas le writer (bulletins, results, records).
- Committer `ROLES.md` sans faire tourner `python tools/check_roles_registry.py` et `check_synthesis_counts.py`.
```

- [ ] **Step 4 : lancer, vérifier le vert + essai réel**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/sandbox/test_pm_tick.py -q -p no:cacheprovider`
Expected: 6 passed.
Run: `PYTHONIOENCODING=utf-8 python tools/check_data_paths.py --only tools/pm/tick.py && PYTHONIOENCODING=utf-8 python tools/check_instrument_calibration.py --only tools/pm/tick.py`
Expected: exit 0 ×2.
Run (réel) : `PYTHONIOENCODING=utf-8 python -m tools.pm.tick --owner essai`
Expected: un digest ; `python -m tools.jobs.doctor` montre le bail `pm` (owner essai) ; puis `python -c "from tools.jobs import lease as L; L.release(L.read('pm'))"` pour le rendre.

- [ ] **Step 5 : commit**

```bash
git add tools/pm/tick.py .claude/skills/pm/SKILL.md tests/sandbox/test_pm_tick.py
git commit -m "feat(pm): tools/pm/tick.py (bail pm porte par le PID de la session, tableau, journal, compteurs, digest) + skill /pm (une action par alerte, repetee -> cliquet, noop)" -- tools/pm/tick.py .claude/skills/pm/SKILL.md tests/sandbox/test_pm_tick.py
```

---

## Auto-revue du plan (faite à la rédaction)

- **Couverture spec** : §3.1 bulletin → Tasks 4-5 ; §3.2 tableau + A1-A8 + AVEUGLE → Task 3 ; §3.3 tick, bail `pm`, une action par alerte, répétée → cliquet → Tasks 6-8 ; §3.6 ROLES.md + cinq colonnes + candidats → Task 7 ; §4 writers → chaque tâche nomme le sien ; §5 erreurs → hooks exit 0 + log (Task 4), AVEUGLE (Task 3), REFUS bail (Task 8) ; §6.1 tests → chaque tâche ; §6.2 compteurs → Task 7 (écart déclaré : ratio glissant hors balise). **Non couvert ici, par conception** : déclencheurs du stratège (plan 3), portes 18-20 et `review:` (plan 2).
- **Écart à la spec, déclaré** : la porte du registre est un module propre (`check_roles_registry`, porte 21) et non une extension de `check_guard_negative_cases` (ancré `**E\d+**` sur le seul REGISTRE) ; le ratio science/méthodo vit dans `ROLES_COUNTS.json`.
- **Cohérence des noms** : `compute`, `render_md`, `summary`, `snapshot`, `norm`, `read_*`, `appliquer`, `charger`, `ecrire`, `nom_depuis_registre`, `session_id_courant`, `resume_tableau`, `diff`, `ajouter`, `compteurs`, `prendre_bail_pm`, `digest`, `lignes`, `defauts`, `bucket`, `compute_counts`, `fichiers_modifies` — mêmes noms dans les tests et les implémentations.
- **Placeholders** : aucun `TBD`/`TODO` ; les seuils sont des constantes nommées (`SEUILS`, `PLAFOND_FICHIERS`, `TTL_PM_S`, `DEBUT`).

