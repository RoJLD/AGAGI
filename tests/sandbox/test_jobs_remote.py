# -*- coding: utf-8 -*-
"""Tests du déport nexus (tools/jobs/remote.py + remote_entry.py) — SANS cluster.

Chaque garde est confrontée aux DEUX issues : un cas qui doit passer et un cas qui doit refuser. Les tests
qui exécutent réellement le chemin (archive au sha → remote_entry → MANIFEST → installation) le font sur un
dépôt git JETABLE, en local : c'est le chemin même du pod, moins kubectl."""
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools._git_env import env_isole          # noqa: E402
from tools.jobs import remote as R            # noqa: E402
from tools.jobs import remote_entry as E      # noqa: E402

RUNNER = '''import json, os, sys
seed = int(sys.argv[sys.argv.index("--seed") + 1])
os.makedirs("results", exist_ok=True)
with open(os.path.join("results", f"fake_{seed}.json"), "w") as f:
    json.dump({"seed": seed, "valeur": seed * 3}, f)
with open("modifie.txt", "a") as f:
    f.write("ajout\\n")
print("runner ok", seed)
sys.exit(int(os.environ.get("FAKE_RC", "0")))
'''


def _git(repo, *args):
    # identité EN LIGNE (-c), jamais `git config` ; environnement isolé (cf. test_evidence_provenance_gate).
    r = subprocess.run(["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                       capture_output=True, text=True, env=env_isole())
    assert r.returncode == 0, f"git {args} : {r.stderr}"
    return r.stdout.strip()


@pytest.fixture()
def depot(tmp_path):
    repo = tmp_path / "depot"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "pkg" / "runner.py").write_text(RUNNER, encoding="utf-8")
    (repo / "modifie.txt").write_text("base\n", encoding="utf-8")
    (repo / "inchange.txt").write_text("fixe\n", encoding="utf-8")
    (repo / "requirements.txt").write_text("numpy\n", encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo, _git(repo, "rev-parse", "HEAD")


# ------------------------------------------------------------------------------------------ cgroup
@pytest.mark.parametrize("brut,attendu", [("200000 100000", 2.0), ("150000 100000", 1.5), ("max 100000", None)])
def test_cpu_max_lu(brut, attendu):
    assert E.parse_cpu_max(brut) == attendu


@pytest.mark.parametrize("brut", ["", "200000", "abc 100000", "0 100000", "100000 0"])
def test_cpu_max_illisible_LEVE_au_lieu_de_rendre_none(brut):
    """None veut dire « pas de limite » : un contenu illisible ne doit JAMAIS le devenir en silence."""
    with pytest.raises(ValueError):
        E.parse_cpu_max(brut)


def test_limite_cpu_trois_issues_distinctes(tmp_path):
    v2 = tmp_path / "v2"
    v2.mkdir()
    (v2 / "cpu.max").write_text("200000 100000\n")
    assert E.lire_limite_cpu(str(v2))["limite_cpu"] == 2.0
    assert E.lire_limite_cpu(str(v2))["source"] == "cgroup2"
    cassé = tmp_path / "casse"
    cassé.mkdir()
    (cassé / "cpu.max").write_text("n'importe quoi")
    r = E.lire_limite_cpu(str(cassé))
    assert r["source"] == "illisible" and r["limite_cpu"] is None and r["erreur"]
    assert E.lire_limite_cpu(str(tmp_path / "rien"))["source"] == "absente"
    v1 = tmp_path / "v1" / "cpu"
    v1.mkdir(parents=True)
    (v1 / "cpu.cfs_quota_us").write_text("300000")
    (v1 / "cpu.cfs_period_us").write_text("100000")
    assert E.lire_limite_cpu(str(tmp_path / "v1"))["limite_cpu"] == 3.0


def test_threads_poses_sur_la_limite_et_git_retire(tmp_path):
    env, _ = E.env_du_runner({"GIT_DIR": "/ailleurs/.git", "PATH": "x"}, "/src", {"limite_cpu": 2.0})
    assert "GIT_DIR" not in env
    assert env["OMP_NUM_THREADS"] == env["OPENBLAS_NUM_THREADS"] == "2"
    assert env["PYTHONPATH"].startswith("/src")
    sans, _ = E.env_du_runner({"PATH": "x"}, "/src", {"limite_cpu": None})
    assert "OMP_NUM_THREADS" not in sans        # limite inconnue : on ne pose RIEN, on ne devine pas


# ------------------------------------------------------------------------------------------ source au sha
def _tgz(racine):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        tf.add(str(racine), arcname=".")
    return buf.getvalue()


def test_source_refusee_si_elle_porte_un_autre_sha(depot, tmp_path):
    repo, sha = depot
    arc = tmp_path / "s.tar.gz"
    arc.write_bytes(R.preparer_source(sha, repo))
    E.extraire_au_sha(str(arc), sha, str(tmp_path / "ok"))
    assert (tmp_path / "ok" / "pkg" / "runner.py").is_file()
    assert b"\r\n" not in (tmp_path / "ok" / "pkg" / "runner.py").read_bytes()   # blobs du commit, pas CRLF
    with pytest.raises(E.Refus, match="au commit"):
        E.extraire_au_sha(str(arc), "0" * 40, str(tmp_path / "ko"))


def test_source_sans_git_refusee(depot, tmp_path):
    """Un arbre sans `.git` ferait publier `git_sha: None` aux runners : refus, pas un run sans provenance."""
    repo, sha = depot
    nu = tmp_path / "nu"
    (nu / "pkg").mkdir(parents=True)
    (nu / "pkg" / "runner.py").write_text("x")
    arc = tmp_path / "nu.tar.gz"
    arc.write_bytes(_tgz(nu))
    with pytest.raises(E.Refus, match="pas un dépôt git"):
        E.extraire_au_sha(str(arc), sha, str(tmp_path / "x"))


def test_source_d_arbre_SALE_refusee(depot, tmp_path):
    """Le bon HEAD mais un fichier suivi modifié : ce n'est pas le code du commit."""
    repo, sha = depot
    arc = tmp_path / "s.tar.gz"
    arc.write_bytes(R.preparer_source(sha, repo))
    ext = tmp_path / "ext"
    with tarfile.open(arc) as tf:
        tf.extractall(ext, filter="data")
    (ext / "inchange.txt").write_bytes(b"altere\n")
    sale = tmp_path / "sale.tar.gz"
    sale.write_bytes(_tgz(ext))
    with pytest.raises(E.Refus, match="propre"):
        E.extraire_au_sha(str(sale), sha, str(tmp_path / "y"))


def test_le_runner_voit_un_vrai_depot_au_sha(depot, tmp_path):
    """La provenance des runners (git rev-parse HEAD) doit rendre le sha DANS l'arbre déporté."""
    repo, sha = depot
    (repo / "pkg" / "prov.py").write_text(
        "import subprocess, json, os\n"
        "h = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()\n"
        "os.makedirs('results', exist_ok=True)\n"
        "json.dump({'git_sha': h}, open(os.path.join('results', 'prov.json'), 'w'))\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "prov")
    sha2 = _git(repo, "rev-parse", "HEAD")
    into = tmp_path / "into"
    R.executer_local(bail_dir=tmp_path / 'bails', commande=["-m", "pkg.prov"], sha=sha2, into=str(into), racine=repo, sortie=lambda *_: None)
    assert json.loads((into / "results" / "prov.json").read_text()) == {"git_sha": sha2}


# ------------------------------------------------------------------------------------------ chemin complet
def test_executer_local_bout_en_bout(depot, tmp_path):
    repo, sha = depot
    into = tmp_path / "into"
    bilan = R.executer_local(bail_dir=tmp_path / 'bails', commande=["-m", "pkg.runner", "--seed", "7"], sha=sha, into=str(into), racine=repo,
                             sortie=lambda *_: None)
    assert bilan["returncode"] == 0
    assert json.loads((into / "results" / "fake_7.json").read_text()) == {"seed": 7, "valeur": 21}
    m = bilan["manifeste"]
    assert m["sha"] == sha and m["sha_verifie"] is True
    assert m["sorties"] == ["modifie.txt", "results/fake_7.json"]      # créé ET modifié ; l'inchangé non
    assert "inchange.txt" not in m["fichiers"]
    assert m["duree_mur_s"] > 0 and m["cpu_user_s"] is not None
    journal = into / "runs" / "deport" / bilan["job"]
    assert (journal / "MANIFEST.json").is_file()
    assert "runner ok 7" in (journal / "_deport" / "stdout.txt").read_text()
    # le même run, rapatrié au même endroit : sorties IDENTIQUES → rien de copié, aucun refus
    again = R.executer_local(bail_dir=tmp_path / 'bails', commande=["-m", "pkg.runner", "--seed", "7"], sha=sha, into=str(into), racine=repo,
                             sortie=lambda *_: None)
    assert again["copies"] == [] and sorted(again["identiques"]) == ["modifie.txt", "results/fake_7.json"]


def test_echec_du_runner_est_rapatrie_avec_son_code(depot, tmp_path):
    repo, sha = depot
    bilan = R.executer_local(bail_dir=tmp_path / 'bails', commande=["-m", "pkg.runner", "--seed", "1"], sha=sha,
                             into=str(tmp_path / "i"), racine=repo, sortie=lambda *_: None, env={"FAKE_RC": "3"})
    assert bilan["returncode"] == 3            # un échec n'est pas avalé : il est rapporté ET ses journaux gardés
    assert bilan["manifeste"]["env_declare"] == {"FAKE_RC": "3"}


def test_l_environnement_de_la_session_n_atteint_PAS_le_runner(depot, tmp_path, monkeypatch):
    """Revue 2026-09-26 (C1) : `SRA_SMOKE=1` exporté sur la batcave aurait changé le run en local mais pas
    dans le pod. Rien d'implicite : une variable NON déclarée n'arrive pas au runner, des deux côtés."""
    repo, sha = depot
    monkeypatch.setenv("FAKE_RC", "3")
    bilan = R.executer_local(bail_dir=tmp_path / 'bails', commande=["-m", "pkg.runner", "--seed", "1"], sha=sha,
                             into=str(tmp_path / "i"), racine=repo, sortie=lambda *_: None)
    assert bilan["returncode"] == 0 and bilan["manifeste"]["env_declare"] == {}


def test_un_code_2_du_RUNNER_n_est_pas_un_refus_d_entree(depot, tmp_path):
    """Revue (I1) : argparse sort en 2 ; l'ancien code de refus était 2, le run était jeté comme « refusé »."""
    repo, sha = depot
    bilan = R.executer_local(bail_dir=tmp_path / 'bails', commande=["-m", "pkg.runner", "--seed", "8"], sha=sha,
                             into=str(tmp_path / "i"), racine=repo, sortie=lambda *_: None, env={"FAKE_RC": "2"})
    assert bilan["returncode"] == 2 and (tmp_path / "i" / "results" / "fake_8.json").is_file()
    assert E.REFUS not in (0, 1, 2, 75) and E.NON_RAPATRIE not in (0, 1, 2, 75)


@pytest.mark.parametrize("paire", ["AGAGI_RESULTS_ROOT=/ailleurs", "AGAGI_DATA_ROOT=x", "GIT_DIR=x", "HOME=/x",
                                   "AGAGI_MUTATION_SPEC=x", "PAS_DE_SIGNE", "1ABC=x"])
def test_env_declaree_interdite_refusee(paire):
    with pytest.raises(R.Refus):
        R.valider_env([paire])


def test_env_local_minimal():
    base = {"PATH": "p", "SystemRoot": "C:\\Windows", "SRA_SMOKE": "1", "AGAGI_RESULTS_ROOT": "/x", "GIT_DIR": "g"}
    env = R.env_local({"A": "1"}, base=base)
    assert env["PATH"] == "p" and env["SystemRoot"] and env["A"] == "1" and env["PYTHONIOENCODING"] == "utf-8"
    assert not {"SRA_SMOKE", "AGAGI_RESULTS_ROOT", "GIT_DIR"} & set(env)


def test_entry_retire_les_racines_qui_deplaceraient_les_ecritures():
    env, retirees = E.env_du_runner({"AGAGI_RESULTS_ROOT": "/x", "AGAGI_ROOT": "/y", "GIT_DIR": "g", "PATH": "p"},
                                    "/src", {"limite_cpu": None})
    assert retirees == ["AGAGI_RESULTS_ROOT", "AGAGI_ROOT", "GIT_DIR"] and "AGAGI_RESULTS_ROOT" not in env


def test_entry_refuse_une_commande_hors_forme_module(depot, tmp_path):
    repo, sha = depot
    arc = tmp_path / "s.tar.gz"
    arc.write_bytes(R.preparer_source(sha, repo))
    for mauvaise in (["pkg/runner.py"], ["-c", "print(1)"], ["-m", "pkg;rm -rf /"]):
        rc = E.main(["--source", str(arc), "--sha", sha, "--work", str(tmp_path / "w"),
                     "--out", str(tmp_path / "o"), "--", *mauvaise])
        assert rc == E.REFUS


def test_entry_refuse_une_archive_tronquee(depot, tmp_path):
    repo, sha = depot
    arc = tmp_path / "s.tar.gz"
    arc.write_bytes(R.preparer_source(sha, repo))
    rc = E.main(["--source", str(arc), "--sha", sha, "--source-sha256", "0" * 64, "--work", str(tmp_path / "w"),
                 "--out", str(tmp_path / "o"), "--", "-m", "pkg.runner", "--seed", "1"])
    assert rc == E.REFUS and not (tmp_path / "w" / "src").exists()


# ------------------------------------------------------------------------------------------ dépôt atomique
def test_depot_MANIFEST_en_dernier_et_jamais_reecrit(tmp_path, monkeypatch):
    sortie, depot = tmp_path / "out", tmp_path / "depot"
    (sortie / "results").mkdir(parents=True)
    (sortie / "results" / "a.json").write_text("{}")
    (sortie / E.MANIFEST).write_text("{}")
    ordre = []
    vrai = E.ecrire_atomique
    monkeypatch.setattr(E, "ecrire_atomique", lambda d, dest: (ordre.append(os.path.basename(dest)), vrai(d, dest)))
    assert E.deposer(str(sortie), str(depot)) == 2
    assert ordre[-1] == E.MANIFEST            # la marque de complétude arrive EN DERNIER
    assert not [f for f in os.listdir(depot / "results") if f.startswith(".")]   # aucun .part résiduel
    with pytest.raises(E.Refus, match="déjà complet"):
        E.deposer(str(sortie), str(depot))


# ------------------------------------------------------------------------------------------ installation
def _sortie(tmp_path, contenu=b'{"x": 1}'):
    s = tmp_path / "sortie"
    (s / "results").mkdir(parents=True)
    (s / "results" / "r.json").write_bytes(contenu)
    (s / "_deport").mkdir()
    (s / "_deport" / "stdout.txt").write_text("log")
    fichiers = {r: {"sha256": h, "octets": 0} for r, h in E.empreinte(str(s)).items()}
    (s / E.MANIFEST).write_text(json.dumps({"schema": E.SCHEMA, "sha": "a" * 40, "job": "j",
                                            "sorties": ["results/r.json"], "fichiers": fichiers, "returncode": 0}))
    return s


def test_conflit_rien_n_est_ecrase_ET_rien_n_est_perdu(tmp_path):
    """Revue (C2) : le refus détruisait la sortie avec le répertoire temporaire. Désormais : destination
    intacte, sortie VÉRIFIÉE conservée sous runs/deport/<job>/sortie_non_installee, installable ensuite."""
    s = _sortie(tmp_path)
    dest = tmp_path / "dest"
    (dest / "results").mkdir(parents=True)
    (dest / "results" / "r.json").write_text("autre contenu")
    with pytest.raises(R.Refus, match="DIFFÉRENT"):
        R.installer_sorties(s, dest, "job-x")
    assert (dest / "results" / "r.json").read_text() == "autre contenu"
    garde = dest / "runs" / "deport" / "job-x" / "sortie_non_installee"
    assert (garde / "results" / "r.json").read_bytes() == b'{"x": 1}'
    assert not (dest / "runs" / "deport" / "job-x" / "MANIFEST.json").exists()   # rien d'INSTALLÉ
    b = R.installer_sorties(garde, tmp_path / "ailleurs", "job-x")                 # et installable ailleurs
    assert b["copies"] == ["results/r.json"]


def test_un_fichier_SUIVI_et_propre_se_remplace_un_modifie_non(tmp_path):
    """git garde la version d'un fichier suivi et propre : le remplacer ne perd rien. Modifié : conflit."""
    dest = tmp_path / "dest"
    (dest / "results").mkdir(parents=True)
    (dest / "results" / "r.json").write_text("ancien resultat")
    _git(dest, "init", "-q", "-b", "main")
    _git(dest, "add", "-A")
    _git(dest, "commit", "-q", "-m", "x")
    b = R.installer_sorties(_sortie(tmp_path / "a"), dest, "job-1")
    assert b["copies"] == ["results/r.json"] and (dest / "results" / "r.json").read_bytes() == b'{"x": 1}'
    (dest / "results" / "r.json").write_text("modifie a la main")                  # désormais MODIFIÉ
    with pytest.raises(R.Refus, match="DIFFÉRENT"):
        R.installer_sorties(_sortie(tmp_path / "b", contenu=b'{"x": 2}'), dest, "job-2")
    assert (dest / "results" / "r.json").read_text() == "modifie a la main"


def test_manifest_etranger_ou_d_un_autre_run_refuse(tmp_path):
    """Revue (M1, M9) : un MANIFEST `{}` rendait un succès ; un MANIFEST d'un autre sha passait."""
    s = _sortie(tmp_path)
    with pytest.raises(R.Refus, match="attendait"):
        R.controler_sortie(s, "j", {"sha": "b" * 40})
    m = json.loads((s / E.MANIFEST).read_text())
    m.pop("schema")
    (s / E.MANIFEST).write_text(json.dumps(m))
    with pytest.raises(R.Refus, match="schéma"):
        R.controler_sortie(s, "j")
    s2 = _sortie(tmp_path / "z")
    (s2 / "REFUS.json").write_text('{"refus": "x"}')
    with pytest.raises(R.Refus, match="REFUSÉ"):
        R.controler_sortie(s2, "j")


def test_installation_refuse_une_sortie_corrompue_ou_inconnue_ou_sans_manifest(tmp_path):
    s = _sortie(tmp_path)
    (s / "results" / "r.json").write_bytes(b"altere")
    with pytest.raises(R.Refus, match="empreinte"):
        R.installer_sorties(s, tmp_path / "d1", "j")
    s2 = _sortie(tmp_path / "b")
    (s2 / "results" / "intrus.json").write_text("{}")
    with pytest.raises(R.Refus, match="hors MANIFEST"):
        R.installer_sorties(s2, tmp_path / "d2", "j")
    s3 = _sortie(tmp_path / "c")
    (s3 / E.MANIFEST).unlink()
    with pytest.raises(R.Refus, match="incomplet"):
        R.installer_sorties(s3, tmp_path / "d3", "j")


def test_installation_nominale(tmp_path):
    s = _sortie(tmp_path)
    b = R.installer_sorties(s, tmp_path / "dest", "job-y")
    assert b["copies"] == ["results/r.json"]
    assert (tmp_path / "dest" / "runs" / "deport" / "job-y" / "_deport" / "stdout.txt").read_text() == "log"


# ------------------------------------------------------------------------------------------ manifeste du Job
IMG = "192.168.1.21:5443/elysium/agagi-runner:py3.13.12-abc@sha256:" + "0" * 64


def _job(**kw):
    base = dict(nom="agagi-x-1234567-ab12", sha="a" * 40, image=IMG, commande=["-m", "tools.evo_runs.x"])
    base.update(kw)
    return R.manifeste_job(**base)


def test_job_conforme_aux_normes_enforce_d_elysium():
    """CNCE-1 (priorityClass), CNCE-3 (tag explicite, pas :latest), CNCE-8 (labels) sont en Enforce : un pod
    refusé ne crée qu'un Job `0/1` muet. On les vérifie AVANT de soumettre."""
    j = _job()
    pod = j["spec"]["template"]
    for meta in (j["metadata"], pod["metadata"]):
        assert meta["labels"]["app.kubernetes.io/name"]
        assert meta["labels"]["elysium.io/criticality"] in ("vital", "important", "standard", "disposable")
    spec = pod["spec"]
    assert spec["priorityClassName"] == "elysium-disposable"
    assert spec["nodeSelector"] == {"kubernetes.io/hostname": "nexus"}
    assert spec["securityContext"]["runAsNonRoot"] is True and spec["automountServiceAccountToken"] is False
    for c in spec["containers"] + spec["initContainers"]:
        assert ":" in c["image"] and not c["image"].endswith(":latest")
        assert c["securityContext"]["readOnlyRootFilesystem"] is True
        assert c["resources"]["limits"] and c["resources"]["requests"]
    assert j["spec"]["backoffLimit"] == 0 and j["spec"]["ttlSecondsAfterFinished"] > 0
    assert j["metadata"]["namespace"] == "elysium-agagi"


def test_aucun_montage_NFS_dans_un_pod_de_run():
    """Un `nfs:` en ligne est `hard` : un atlas à terre fige le pod puis le kubelet (incident ELYSIUM 01/09).
    SIGIL-1764 : atlas n'est plus une dépendance. Aucun volume réseau, seulement des emptyDir."""
    spec = _job()["spec"]["template"]["spec"]
    assert all(set(v) == {"name", "emptyDir"} for v in spec["volumes"])
    assert "--attendre-rapatriement" in spec["containers"][0]["args"]


def test_labels_de_propriete_elysium():
    """Σ-MANIFEST-MYCORHIZE : sans eux, l'objet est une zone d'ombre pour la carte de propriété ELYSIUM."""
    j = _job()
    for meta in (j["metadata"], j["spec"]["template"]["metadata"]):
        assert meta["labels"]["elysium.io/managed-by"] == "agagi"
        assert meta["labels"]["elysium.io/source-repo"]


@pytest.mark.parametrize("kw", [dict(cpu=3.0), dict(mem="8Gi"), dict(req_cpu=2.0, cpu=1.0),
                                dict(req_mem="2Gi", mem="1Gi"), dict(mem="4G"), dict(cpu=0.0, req_cpu=0.0)])
def test_ressources_hors_limitrange_refusees_avant_soumission(kw):
    with pytest.raises(R.Refus):
        _job(**kw)


def test_nom_de_job_dns_1123():
    import re
    n = R.nom_job(["-m", "tools.evo_runs.Un_Runner_Au_Nom_Tres_Long_Qui_Deborde_Largement"], "f" * 40)
    assert len(n) <= 63 and re.fullmatch(r"[a-z0-9]([-a-z0-9]*[a-z0-9])?", n)


def test_paquet_ready_en_DERNIER():
    brut = R.paquet_de_transfert(b"arc", b"entry")
    with tarfile.open(fileobj=io.BytesIO(brut)) as tf:
        assert [m.name for m in tf.getmembers()] == ["source.tar.gz", "remote_entry.py", ".ready"]


# ------------------------------------------------------------------------------------------ nœud et refus
class KubeFactice:
    def __init__(self, noeud):
        self.noeud, self.appels = noeud, []

    def json(self, args, ns=True):
        self.appels.append(("json", tuple(args)))
        if args[:2] == ["get", "node"]:
            return self.noeud
        raise AssertionError(f"appel inattendu {args}")

    def creer(self, objet):
        self.appels.append(("creer", objet["metadata"]["name"]))


def _noeud(ready="True", unsched=False):
    return {"spec": {"unschedulable": unsched}, "status": {"conditions": [{"type": "Ready", "status": ready}]}}


def test_noeud_pret_deux_issues():
    assert R.noeud_pret(KubeFactice(_noeud()), "nexus")[0] is True
    assert R.noeud_pret(KubeFactice(_noeud(ready="Unknown")), "nexus")[0] is False
    assert R.noeud_pret(KubeFactice(_noeud(unsched=True)), "nexus")[0] is False


def test_soumission_refusee_nexus_endormi_RIEN_n_est_cree(depot):
    """nexus s'éteint par intermittence (elysium-8d, 2026-09-26) : un Job épinglé sur un nœud absent resterait
    Pending sans bruit. Refus AVANT toute création, avec la voie d'allumage nommée."""
    repo, sha = depot
    (repo / "deploy" / "nexus" / "runner").mkdir(parents=True)
    # l'empreinte du blob COMMITTÉ, pas du disque (fins de ligne converties sous Windows)
    req = hashlib.sha256(R.fichier_au_sha(sha, "requirements.txt", repo)).hexdigest()
    (repo / R.IMAGE_JSON).write_text(json.dumps({"image": "r", "tag": "t", "digest": "sha256:" + "0" * 64,
                                                 "requirements_sha256": req}))
    kube = KubeFactice(_noeud(ready="False"))
    with pytest.raises(R.Refus, match="power nexus on"):
        R.soumettre(["-m", "pkg.runner", "--seed", "1"], sha=sha, kube=kube, racine=repo, sortie=lambda *_: None,
                    maintenant=_paris(10, 0))
    assert not [a for a in kube.appels if a[0] == "creer"]


def test_soumission_refusee_si_l_image_ne_correspond_pas_aux_requirements_du_sha(depot):
    repo, sha = depot
    (repo / "deploy" / "nexus" / "runner").mkdir(parents=True)
    (repo / R.IMAGE_JSON).write_text(json.dumps({"image": "r", "tag": "t", "digest": "d",
                                                 "requirements_sha256": "autre"}))
    kube = KubeFactice(_noeud())
    with pytest.raises(R.Refus, match="requirements"):
        R.soumettre(["-m", "pkg.runner"], sha=sha, kube=kube, racine=repo, sortie=lambda *_: None,
                    maintenant=_paris(10, 0))
    assert kube.appels == []                   # refus avant même d'interroger le cluster


def _paris(h, m):
    import datetime as dt
    from zoneinfo import ZoneInfo
    return dt.datetime(2026, 9, 26, h, m, tzinfo=ZoneInfo("Europe/Paris"))


def test_fenetre_de_nexus_minuit_dur():
    """nexus s'éteint DUR à 00:00 (IPMI, sans drain) et n'est garanti qu'à partir de 08:00 (elysium-91)."""
    assert R.fenetre_restante_s(_paris(7, 59)) == 0
    assert R.fenetre_restante_s(_paris(12, 0)) == 12 * 3600 - R.MARGE_MINUIT_S
    assert R.fenetre_restante_s(_paris(23, 50)) == 0


def test_soumission_refusee_si_le_run_deborde_minuit_RIEN_n_est_cree(depot):
    repo, sha = depot
    kube = KubeFactice(_noeud())
    with pytest.raises(R.Refus, match="minuit"):
        R.soumettre(["-m", "pkg.runner"], sha=sha, kube=kube, racine=repo, sortie=lambda *_: None,
                    maintenant=_paris(22, 30))
    assert kube.appels == []


def test_code_de_sortie_absent_n_est_pas_un_succes():
    assert R.code_de_sortie(0) == 0 and R.code_de_sortie(3) == 3
    assert R.code_de_sortie(None) == 1 and R.code_de_sortie("0") == 1 and R.code_de_sortie(True) == 1


def test_local_tient_le_bail_kuzu_de_la_batcave(depot, tmp_path):
    """Le runner prend son bail dans l'arbre EXTRAIT, invisible au doctor : sans le bail de la batcave, un
    run local échapperait à « un seul run lourd à la fois ». Bail tenu par un vivant -> refus, rien ne tourne."""
    from tools.jobs import lease as L
    repo, sha = depot
    L.acquire("kuzu", owner="autre-run", pid=os.getppid(), leases_dir=tmp_path / "bails")
    with pytest.raises(L.ResourceBusy):
        R.executer_local(bail_dir=tmp_path / "bails", commande=["-m", "pkg.runner", "--seed", "2"], sha=sha,
                         into=str(tmp_path / "i"), racine=repo, sortie=lambda *_: None)
    assert not (tmp_path / "i").exists()


def test_ecarts_hors_volatils_deux_issues():
    """Instrument du témoin batcave/nexus : identique hors volatils DÉCLARÉS, et un seul chiffre d'écart
    ailleurs doit le faire tomber."""
    a = b'{\n "elapsed_s": 2.08,\n "r": 0.5,\n "rows": [\n  {"elapsed_s": 1.4, "x": 1}\n ]\n}'
    b = b'{\n "elapsed_s": 2.48,\n "r": 0.5,\n "rows": [\n  {"elapsed_s": 1.4, "x": 1}\n ]\n}'
    assert R.ecarts_hors_volatils(a, b) == []
    c = b.replace(b'"r": 0.5', b'"r": 0.6')
    assert [e[0] for e in R.ecarts_hors_volatils(a, c)] == [3]
    assert R.ecarts_hors_volatils(a, a + b"\n")[0][0] == 0          # nombre de lignes différent
    # une clé volatile n'excuse que SA ligne : une valeur changée sur une ligne mixte est un écart
    d = a.replace(b'{"elapsed_s": 1.4, "x": 1}', b'{"elapsed_s": 1.4, "x": 2}')
    assert R.ecarts_hors_volatils(a, d) != []
    assert R.ecarts_hors_volatils(a, b, volatils=()) != []           # rien de déclaré : tout compte


def test_reecriture_a_l_identique_est_une_sortie_attestee(depot, tmp_path):
    """Revue (S3) : un runner qui reproduit à l'octet un fichier suivi ne laissait AUCUNE trace."""
    repo, sha = depot
    (repo / "pkg" / "repro.py").write_text("open('inchange.txt', 'wb').write(('fixe' + chr(10)).encode())\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "repro")
    sha2 = _git(repo, "rev-parse", "HEAD")
    b = R.executer_local(bail_dir=tmp_path / "bails", commande=["-m", "pkg.repro"], sha=sha2,
                         into=str(tmp_path / "i"), racine=repo, sortie=lambda *_: None)
    assert b["manifeste"]["reecrits_identiques"] == ["inchange.txt"]
    assert "inchange.txt" in b["manifeste"]["sorties"] and "inchange.txt" in b["manifeste"]["fichiers"]


def test_garde_d_image_compare_le_CONTEXTE_quand_le_sha_le_porte(depot):
    """Revue (I2) : seule requirements.txt était comparée ; une contrainte numpy changée passait."""
    repo, sha = depot
    d = repo / "deploy" / "nexus" / "runner"
    d.mkdir(parents=True)
    for n in ("Dockerfile", "constraints.txt", "build-job.yaml"):
        (d / n).write_text(f"{n}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "ctx")
    sha2 = _git(repo, "rev-parse", "HEAD")
    info = {"tag": "t", "ctx_hash12": R.contexte_image(sha2, repo)["hash12"]}
    assert R.garde_image(info, sha2, repo) == "contexte-complet"
    (d / "constraints.txt").write_text("numpy==1.26.4\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "numpy")
    with pytest.raises(R.Refus, match="contexte"):
        R.garde_image(info, _git(repo, "rev-parse", "HEAD"), repo)
    # sha antérieur au déport : garde réduite, et DITE
    req = hashlib.sha256(R.fichier_au_sha(sha, "requirements.txt", repo)).hexdigest()
    assert R.garde_image({"requirements_sha256": req}, sha, repo).startswith("requirements-seul")


def _pod(**st):
    return {"spec": {"nodeName": "nexus"}, "status": st}


@pytest.mark.parametrize("pod,job,pret,attendu", [
    (None, {}, True, "pod_disparu"),
    (_pod(conditions=[{"type": "DisruptionTarget", "reason": "PreemptionByScheduler"}]), {}, True, "preempte"),
    (_pod(conditions=[{"type": "DisruptionTarget", "reason": "TerminationByKubelet"}]), {}, True, "noeud_perdu"),
    (_pod(reason="Evicted"), {}, True, "evince"),
    (_pod(), {"status": {"conditions": [{"type": "Failed", "status": "True", "reason": "DeadlineExceeded"}]}}, True,
     "delai_depasse"),
    (_pod(containerStatuses=[{"name": "run", "state": {"terminated": {"exitCode": 137, "reason": "OOMKilled"}}}]),
     {}, True, "oom"),
    (_pod(containerStatuses=[{"name": "run", "state": {"terminated": {"exitCode": 86}}}]), {}, True, "refus_entree"),
    (_pod(containerStatuses=[{"name": "run", "state": {"terminated": {"exitCode": 87}}}]), {}, True, "non_rapatrie"),
    (_pod(), {}, False, "noeud_perdu"),
    (_pod(), {}, True, "inconnu"),
])
def test_fin_d_un_job_lue_sur_ce_qui_est_ARRIVE_au_pod(pod, job, pret, attendu):
    """Revue (I3) : l'état était déduit du nœud MAINTENANT ; un nexus éteint puis rallumé se lisait « echec »."""
    assert R.lire_fin(job, pod, pret)["etat"] == attendu


def test_job_env_declaree_et_shm_et_attente_minimale():
    j = _job(env_declare={"SRA_SMOKE": "1"})
    c = j["spec"]["template"]["spec"]["containers"][0]
    assert {"name": "SRA_SMOKE", "value": "1"} in c["env"]
    assert c["args"][c["args"].index("--env-declare") + 1] == "SRA_SMOKE"
    assert json.loads(j["metadata"]["annotations"]["agagi.io/env"]) == {"SRA_SMOKE": "1"}
    assert any(v.get("emptyDir", {}).get("medium") == "Memory" for v in j["spec"]["template"]["spec"]["volumes"])
    with pytest.raises(R.Refus, match="attente"):
        _job(attente_s=0)
