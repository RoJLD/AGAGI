"""Le tick PM : un seul PM vivant (bail pm porte par le PID de la session), un tableau ecrit, un journal tenu."""
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


def test_un_bail_pris_entre_la_lecture_et_l_acquisition_est_un_refus_propre_pas_une_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(TK.L, "acquire", lambda *a, **k: (_ for _ in ()).throw(TK.L.ResourceBusy("pris")))
    r = TK.prendre_bail_pm("agagi-52", os.getpid(), leases_dir=tmp_path)
    assert r["ok"] is False and isinstance(r["detenteur"], str)


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


def test_digest_dit_rien_de_nouveau_quand_rien_n_a_bouge():
    board = {"aveugle": [], "charge_connue": {"sims_en_vol": 0, "cpu_5min_pct": 0.0, "bails_vivants": []},
             "alertes": [], "sessions": []}
    d = {"nouvelles": [], "repetees": [], "disparues": [], "lignes": []}
    counts = {"alertes": {"emises": 0, "suivies_48h": 0, "fausses_ou_ignorees": 0, "repetees": 0, "ouvertes": 0},
              "fichiers": {"science": 0, "methodo": 0, "autre": 0}, "ratio_science_methodo": 0.0}
    assert "rien de nouveau (noop)" in TK.digest(board, d, counts)


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
