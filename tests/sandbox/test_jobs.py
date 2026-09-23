"""Tests du job manager. Chaque test encode une VIOLATION RÉELLE du 2026-07-21 ou une garde de sûreté :
si un test échoue, la protection correspondante ne tient plus."""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.jobs import lease as L          # noqa: E402
from tools.jobs.run import hold, run, kill_tree  # noqa: E402
from tools.jobs import doctor as D         # noqa: E402


def test_named_resource_is_exclusive(tmp_path):
    """VIOLATION RÉELLE (2×) : deux sondes monde concurrentes -> contention KuzuDB -> mesure contaminée.
    Le bail doit rendre ça IMPOSSIBLE, pas déconseillé."""
    a = L.acquire("kuzu", owner="sondeA", leases_dir=tmp_path, pid=os.getpid())
    with pytest.raises(L.ResourceBusy, match="kuzu"):
        L.acquire("kuzu", owner="sondeB", leases_dir=tmp_path, pid=os.getpid() + 1)
    L.release(a, leases_dir=tmp_path)
    L.acquire("kuzu", owner="sondeB", leases_dir=tmp_path, pid=os.getpid() + 1)  # libéré -> reprenable


def test_distinct_resources_do_not_block_each_other(tmp_path):
    """Un cap global à 1 sérialiserait des jobs indépendants : c'est précisément ce qu'on refuse."""
    L.acquire("kuzu", leases_dir=tmp_path, pid=os.getpid())
    L.acquire("gpu", leases_dir=tmp_path, pid=os.getpid() + 1)   # ne doit PAS lever
    # 2026-09-02 : asserter que les DEUX bails coexistent reellement -- « n'a pas leve » ne
    # distingue pas « les deux tiennent » de « le second a ecrase le premier ».
    assert L.read("kuzu", leases_dir=tmp_path) is not None
    assert L.read("gpu", leases_dir=tmp_path) is not None


def test_dead_holder_lease_is_reclaimable(tmp_path):
    """Crash-recovery : un bail dont le détenteur a disparu ne doit pas bloquer la ressource à vie."""
    fantome = 999_999                                   # PID quasi certainement inexistant
    L.acquire("kuzu", owner="crashé", leases_dir=tmp_path, pid=fantome)
    lz = L.read("kuzu", leases_dir=tmp_path)
    assert L.is_holder_alive(lz) is False
    assert L.is_live(lz) is False
    L.acquire("kuzu", owner="nouveau", leases_dir=tmp_path, pid=os.getpid())   # récupérable


def test_pid_reuse_is_not_mistaken_for_the_holder(tmp_path):
    """ANTI-RÉUTILISATION DE PID : même PID, autre processus -> le détenteur est mort. Sans ce contrôle,
    le doctor pourrait TUER un processus étranger ayant hérité du PID."""
    lz = L.acquire("kuzu", leases_dir=tmp_path, pid=os.getpid())
    assert L.is_holder_alive(lz) is True
    lz.proc_create_time = (lz.proc_create_time or time.time()) - 10_000.0     # simule la réutilisation
    assert L.is_holder_alive(lz) is False


def test_expired_lease_is_not_live_even_if_process_runs(tmp_path):
    """TTL expiré = heartbeat manquant. Le bail n'est plus vivant, mais le doctor ne doit pas tuer
    (cf. test suivant) : les deux notions sont distinctes."""
    lz = L.acquire("kuzu", ttl_s=1.0, leases_dir=tmp_path, pid=os.getpid(), now=1000.0)
    assert L.is_expired(lz, now=1002.0) is True
    assert L.is_live(lz, now=1002.0) is False
    assert L.is_holder_alive(lz) is True                # le processus, lui, tourne toujours


def test_doctor_never_kills_a_live_holder(tmp_path, capsys):
    """GARDE DE SÛRETÉ : un bail expiré dont le détenteur VIT signale un heartbeat manquant, pas un
    orphelin. Le doctor doit REFUSER de le tuer."""
    L.acquire("kuzu", owner="lent", ttl_s=-1.0, leases_dir=tmp_path, pid=os.getpid())
    cls = D.classify_leases(leases_dir=tmp_path)
    assert len(cls["dead"]) == 1 and L.is_holder_alive(cls["dead"][0]) is True


def test_doctor_never_targets_self_or_ancestors():
    """On ne se scie pas la branche : le processus courant et ses ancêtres sont exclus."""
    prot = D._protected_pids()
    assert os.getpid() in prot
    assert all(p["pid"] not in prot for p in D.project_processes())


def test_hold_releases_even_on_exception(tmp_path):
    """Un bail orphelin bloquerait la ressource : la libération doit survivre à une exception."""
    with pytest.raises(ValueError):
        with hold("kuzu", owner="boom", leases_dir=tmp_path):
            raise ValueError("boom")
    assert L.read("kuzu", leases_dir=tmp_path) is None


def test_run_times_out_and_kills_the_tree(tmp_path):
    """VIOLATION documentée sans implémentation jusqu'ici : un job qui dépasse doit être tué AVEC sa
    descendance, et son bail libéré (sinon la ressource reste bloquée)."""
    r = run("dormeur", [sys.executable, "-c", "import time; time.sleep(60)"],
            resources=["kuzu"], timeout_s=2.0, leases_dir=tmp_path)
    assert r.timed_out is True and r.duration_s < 30
    assert L.read("kuzu", leases_dir=tmp_path) is None, "bail non libéré après timeout"


def test_run_succeeds_and_returns_output(tmp_path):
    r = run("ok", [sys.executable, "-c", "print('bonjour')"], resources=["kuzu"],
            timeout_s=60, leases_dir=tmp_path)
    assert r.timed_out is False and r.returncode == 0 and "bonjour" in r.stdout


def test_kill_tree_is_tolerant_of_dead_pid():
    """Idempotence : tuer un PID déjà mort n'est pas une erreur."""
    assert kill_tree(999_999) == 0


# --------------------------------------------------------------------------------------------------
# CALIBRATION de `classify_leases` (2026-09-07). Révélée par l'élargissement RÉCURSIF du périmètre du
# cliquet (8e angle mort : `tools/jobs/` était invisible). Un seul cas existait -- la branche `dead`.
# Une classification qui rendrait TOUT mort passait ce cas, et le doctor `--kill` en dépend.
# --------------------------------------------------------------------------------------------------

def test_classify_leases_met_un_bail_VIVANT_du_bon_cote(tmp_path):
    """Branche `live`, appariée à `test_doctor_never_kills_a_live_holder` (qui ne couvre que `dead`).
    Sans elle, une classification dégénérée « tout est mort » passerait la suite -- et le doctor
    `--kill` réaperait un bail parfaitement sain."""
    L.acquire("kuzu", owner="vivant", ttl_s=3600.0, leases_dir=tmp_path, pid=os.getpid())
    cls = D.classify_leases(leases_dir=tmp_path)
    assert len(cls["live"]) == 1 and cls["dead"] == []
    assert cls["live"][0].resource == "kuzu"    # `Lease` est un objet, pas un dict


def test_classify_leases_sur_un_repertoire_VIDE_ne_classe_RIEN(tmp_path):
    """Spécificité : aucune entrée -> AUCUN état n'est peuplé. C'est la forme (a) du biais du dépôt
    (entrée absente -> affirmation de fond) : ici, rendre un bail « mort » depuis zéro donnée
    autoriserait un kill sans détenteur.

    ⚠️ 2026-09-22 : cette assertion gelait la FORME du dict (`== {"live": [], "dead": []}`) et non
    l'invariant — elle a rougi quand `classify_leases` a séparé `expired_alive` d'`orphan` (E4 occ.
    doctor), alors que la propriété testée tenait toujours. Reformulée sur l'INVARIANT (E25), elle est
    désormais plus forte : tout état présent doit être vide, et les trois états doivent exister."""
    cls = D.classify_leases(leases_dir=tmp_path)
    assert {"live", "expired_alive", "orphan"} <= set(cls)
    assert all(v == [] for v in cls.values()), cls


# --------------------------------------------------------------------------------------------------
# P2.69 (i), 2026-09-15 — le bail est ANCRÉ AU DÉPÔT (parent du `.git` commun), plus au cwd : un
# worktree voit le bail tenu dans l'arbre principal. Sans git : le cwd, comme avant.
# --------------------------------------------------------------------------------------------------

def test_default_leases_dir_is_anchored_to_the_repository_root_not_the_cwd():
    """Le répertoire des baux est ancré à la racine COMMUNE du dépôt — le parent du `.git` partagé par tous
    les worktrees (P2.69 i) — jamais au worktree courant.

    ⚠️ CORRIGÉ le 2026-09-23 (5e rouge de la suite de nuit du PM, mesuré depuis un worktree) : ce test
    comparait à `git rev-parse --show-toplevel`, c'est-à-dire au sommet du worktree COURANT. Depuis l'arbre
    principal les deux coïncident (vert) ; depuis un worktree, `--show-toplevel` rend le worktree alors que
    `_repo_root` rend, par design, l'arbre principal (rouge). Le test contredisait le design qu'il garde —
    reproduit : `_dir(None)` = C:/…/AGAGI/runs/leases, toplevel = C:/…/AGAGI/.claude/worktrees/<wt>. La
    référence est désormais `--git-common-dir`, la même que l'implémentation lit — mais mesurée ICI par git,
    pas recopiée d'elle."""
    import subprocess
    from pathlib import Path
    L._reset_repo_root_cache()
    try:
        d = L._dir(None)
        assert d.is_absolute()
        common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], text=True).strip()
        racine_commune = Path(common).resolve().parent
        assert d.resolve() == (racine_commune / L.DEFAULT_LEASES_DIR).resolve()
    finally:
        L._reset_repo_root_cache()


class _FauxGit:
    """Remplace `subprocess.run` pour les seuls appels `git rev-parse` ; tout le reste passe."""

    def __init__(self, returncode, stdout):
        import subprocess
        self.orig = subprocess.run
        self.returncode, self.stdout = returncode, stdout

    def __call__(self, cmd, **kw):
        if list(cmd[:2]) == ["git", "rev-parse"]:
            rc, out = self.returncode, self.stdout

            class R:
                returncode = rc
                stdout = out
                stderr = ""
            return R()
        return self.orig(cmd, **kw)


def test_repo_root_from_a_worktree_is_the_MAIN_tree(tmp_path):
    """Simule un worktree : un cwd ailleurs, dont `git rev-parse --git-common-dir` rend le `.git` ABSOLU
    de l'arbre principal -> la racine est le parent de ce `.git`, pas le cwd."""
    import subprocess
    principal = tmp_path / "principal"
    (principal / ".git").mkdir(parents=True)
    wt = tmp_path / "wt"
    wt.mkdir()
    faux = _FauxGit(0, str(principal / ".git") + "\n")
    subprocess.run = faux
    try:
        assert L._repo_root(cwd=wt).resolve() == principal.resolve()
    finally:
        subprocess.run = faux.orig


def test_repo_root_from_a_REAL_worktree_is_the_main_tree(tmp_path):
    """CONTRE-EXEMPLE RÉEL (2026-09-23, 5e rouge de la suite de nuit du PM). Le mock ci-dessus ne peut pas
    contredire l'implémentation : il répond ce qu'on lui dit — c'est ainsi que le test d'ancrage a pu
    rester vert tout en contredisant le design. Ici un VRAI worktree jetable (`git worktree add --detach
    --no-checkout` : aucun fichier extrait, donc aucun chemin long Windows ; seule la métadonnée `.git` du
    worktree existe), interrogé par le VRAI git : `--show-toplevel` y rend le worktree — l'ancienne
    référence, fausse — et `_repo_root(cwd=wt)` rend l'arbre principal, le design (P2.69 i). La racine de
    référence est le parent de `--git-common-dir`, donc le test tient AUSSI quand la suite tourne déjà
    depuis un worktree (le cas du PM). Retiré en teardown ; git absent ou `worktree add` refusé -> skip
    explicite, jamais un vert fabriqué."""
    import subprocess
    from pathlib import Path
    import pytest
    try:
        common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], text=True).strip()
    except (OSError, subprocess.CalledProcessError) as e:
        pytest.skip(f"git indisponible : {e}")
    racine_commune = Path(common).resolve().parent
    wt = tmp_path / "wt"
    r = subprocess.run(["git", "worktree", "add", "--detach", "--no-checkout", str(wt), "HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"worktree jetable refusé par git : {r.stderr.strip()[:160]}")
    try:
        toplevel_wt = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=str(wt),
                                                   text=True).strip()).resolve()
        assert toplevel_wt == wt.resolve() and toplevel_wt != racine_commune, (
            "prémisse : depuis le worktree, --show-toplevel doit rendre le worktree, pas l'arbre principal")
        r_wt = L._repo_root(cwd=wt).resolve()
        assert r_wt == racine_commune, f"_repo_root depuis un worktree doit rendre l'arbre principal, or {r_wt}"
        assert r_wt != toplevel_wt, "l'ancienne référence (toplevel) aurait rougi ici : c'est le contre-exemple"
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], capture_output=True)


def test_repo_root_without_git_falls_back_to_the_cwd(tmp_path):
    """NO-OP apparié : hors dépôt (git rend un code non nul), la racine est le cwd — l'ancien comportement."""
    import subprocess
    hors = tmp_path / "hors_depot"
    hors.mkdir()
    faux = _FauxGit(128, "")
    subprocess.run = faux
    try:
        assert L._repo_root(cwd=hors).resolve() == hors.resolve()
    finally:
        subprocess.run = faux.orig
