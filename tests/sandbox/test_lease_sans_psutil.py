"""P2.171 (2026-10-13) — contre-exemples GELÉS : sans psutil, un détenteur de bail n'est JAMAIS jugé mort faute de savoir.

Mesuré par Master 2 le 2026-10-13 : sous le « python » du PATH de la batcave (3.14, sans psutil), `proc_create_time`
rendait None, `is_holder_alive` lisait ce None comme « mort », et le doctor a affiché ORPHELIN le bail VIVANT du run
d'E34, avec « 0 processus » pendant que huit tournaient. Un `--kill` l'aurait réapé ; un `acquire` l'aurait PRIS.
L'absence d'un outil était devenue une affirmation de fond (E4), sur l'outil même qui protège les runs.

Ici psutil est rendu inimportable par `sys.modules["psutil"] = None` (le procédé de test_cost_guard). Les bails vivent
sous `tmp_path`, jamais dans le dossier de la flotte. Les détenteurs sont de VRAIS processus enfants.
"""
import os
import subprocess
import sys
import time

import pytest

from tools.jobs import doctor as D
from tools.jobs import lease as L

_LEASE_GUARD_EXEMPT = True          # ce fichier ne simule aucun monde : la garde de bail ne doit pas le sauter
_LECTURE_SYSTEME = os.name == "nt" or os.path.exists("/proc/self/stat")   # l'API du système lit l'instant de création


@pytest.fixture
def enfant_vivant():
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
    try:
        deadline = time.time() + 15
        while L.identite(p.pid)[0] != "present" and time.time() < deadline:
            time.sleep(0.1)
        yield p
    finally:
        p.kill()
        p.wait(timeout=10)


def _bail(tmp_path, pid, ct, owner="detenteur-temoin", ttl=120.0):
    t = time.time()
    lz = L.Lease(resource="kuzu", pid=pid, proc_create_time=ct, owner=owner, created=t, ttl_s=ttl,
                 expires_at=t + ttl, last_heartbeat=t)
    L._write(lz, tmp_path)
    return lz


def _sans_psutil(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", None)          # import psutil -> ImportError
    with pytest.raises(ImportError):
        import psutil  # noqa: F401


def test_P2_171_CONTRE_EXEMPLE_un_detenteur_VIVANT_sans_psutil_n_est_JAMAIS_juge_mort(tmp_path, monkeypatch,
                                                                                      enfant_vivant):
    ct = L.identite(enfant_vivant.pid)[1]                       # l'identité lue AVANT de couper psutil
    assert ct is not None, "prémisse : l'instant de création du détenteur doit être lisible ici"
    lz = _bail(tmp_path, enfant_vivant.pid, ct)
    _sans_psutil(monkeypatch)
    statut = L.holder_status(lz)
    assert statut in ("vivant", "indetermine"), statut
    if _LECTURE_SYSTEME:
        assert statut == "vivant", f"l'API du système lit l'identité ici : {statut}"
    assert L.is_holder_alive(lz) and L.is_live(lz)
    cls = D.classify_leases(leases_dir=tmp_path)
    assert lz not in cls["orphan"] and lz not in cls["dead"], cls
    with pytest.raises(L.ResourceBusy):                         # personne ne PREND le bail d'un run en cours
        L.acquire("kuzu", owner="intrus", leases_dir=tmp_path)


def test_P2_171_SPECIFICITE_un_detenteur_MORT_sans_psutil_est_juge_mort(tmp_path, monkeypatch):
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    ct = L.identite(p.pid)[1]
    p.wait(timeout=30)
    lz = _bail(tmp_path, p.pid, ct or 0.0)
    _sans_psutil(monkeypatch)
    assert L.holder_status(lz) == "mort"
    assert lz in D.classify_leases(leases_dir=tmp_path)["orphan"]


def test_P2_171_un_PID_REATTRIBUE_sans_psutil_n_est_jamais_juge_vivant(tmp_path, monkeypatch, enfant_vivant):
    """Même PID, autre instant de création : le détenteur du bail est mort, le PID appartient à un autre. Sans moyen de
    lire l'instant, on ne peut pas le prouver : indéterminé — mais jamais « vivant »."""
    ct = L.identite(enfant_vivant.pid)[1]
    lz = _bail(tmp_path, enfant_vivant.pid, (ct or time.time()) - 1000.0)
    _sans_psutil(monkeypatch)
    statut = L.holder_status(lz)
    assert statut != "vivant", statut
    if _LECTURE_SYSTEME:
        assert statut == "mort", statut


def test_P2_171_INCONNU_est_INDETERMINE_et_le_doctor_REFUSE_de_le_reaper(tmp_path, monkeypatch, enfant_vivant, capsys):
    """Ni psutil ni l'API du système : « inconnu ». Le bail est INDÉTERMINÉ, le doctor le DIT, `--kill` le garde, et
    `acquire` refuse de le prendre."""
    lz = _bail(tmp_path, enfant_vivant.pid, 12345.0)
    _sans_psutil(monkeypatch)

    def leve(pid):
        raise OSError("API du système illisible")

    monkeypatch.setattr(L, "_identite_windows", leve)
    monkeypatch.setattr(L, "_identite_posix", leve)
    assert L.identite(enfant_vivant.pid) == ("inconnu", None)
    assert L.holder_status(lz) == "indetermine" and L.is_holder_alive(lz)
    cls = D.classify_leases(leases_dir=tmp_path)
    assert lz in cls["indetermine"] and lz not in cls["dead"], cls
    vrai = D.classify_leases
    monkeypatch.setattr(D, "classify_leases", lambda **kw: vrai(leases_dir=tmp_path))
    monkeypatch.setattr(D, "project_processes", lambda older_min=0.0: [])
    D.main(["--kill"])
    sortie = capsys.readouterr().out
    assert "INDÉTERMINÉ" in sortie and "REFUS" in sortie, sortie
    assert L.read("kuzu", leases_dir=tmp_path) is not None, "le doctor a réapé un bail INDÉTERMINÉ"
    with pytest.raises(L.ResourceBusy):
        L.acquire("kuzu", owner="intrus", leases_dir=tmp_path)


def test_P2_171_sans_psutil_le_doctor_dit_ILLISIBLE_et_jamais_0_processus(tmp_path, monkeypatch, capsys):
    vrai = D.classify_leases
    monkeypatch.setattr(D, "classify_leases", lambda **kw: vrai(leases_dir=tmp_path))
    _sans_psutil(monkeypatch)
    D.main([])
    sortie = capsys.readouterr().out
    assert "ILLISIBLES" in sortie, sortie
    assert "(hors moi et mes ancêtres) : 0" not in sortie, sortie


def test_P2_171_avec_psutil_rien_ne_change_pour_un_vivant_et_un_mort(tmp_path, enfant_vivant):
    """Non-régression : psutil présent, l'identité vient de lui comme avant."""
    pytest.importorskip("psutil")
    vivant = _bail(tmp_path, enfant_vivant.pid, L.proc_create_time(enfant_vivant.pid))
    assert L.holder_status(vivant) == "vivant"
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait(timeout=30)
    assert L.holder_status(L.Lease(resource="x", pid=p.pid, proc_create_time=1.0, owner="", created=0.0, ttl_s=1.0,
                                   expires_at=1.0, last_heartbeat=0.0)) == "mort"
