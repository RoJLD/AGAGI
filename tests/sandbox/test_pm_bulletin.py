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


def test_tool_sur_bulletin_vide_fixe_le_cwd_des_le_premier_evenement():
    b = BU.appliquer("tool", _payload("PostToolUse", tool_name="Edit", tool_input={"file_path": "c:/x/agagi/f0.py"}),
                     {}, now=NOW, branche_fn=lambda c: (None, None))
    assert b["cwd"] == "c:/x/agagi" and b["files_touched"] == ["f0.py"]


def test_tool_sans_cwd_connu_garde_le_chemin_absolu():
    b = BU.appliquer("tool", _payload("PostToolUse", cwd=None, tool_name="Edit", tool_input={"file_path": "c:/x/agagi/f0.py"}),
                     {}, now=NOW, branche_fn=lambda c: (None, None))
    assert b["cwd"] is None
    assert b["files_touched"] == [BU.norm("c:/x/agagi/f0.py")]


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
    # Horloge INJECTÉE (défaut 1, 2026-09-24) : le résumé dépend désormais de l'âge du tableau, et NOW
    # (2027) est dans le FUTUR de l'horloge réelle — sans injection, ce test aurait changé de verdict
    # selon le jour où il tourne.
    monkeypatch.setattr(BU, "_horloge", lambda: NOW + 600)
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    (tmp_path / "pm").mkdir()
    (tmp_path / "pm" / "BOARD.json").write_text(json.dumps({"generated_at": NOW, "aveugle": ["bails (tools/jobs)"], "sessions": [],
                                                           "alertes": [], "charge_connue": {"sims_en_vol": 0, "cpu_pct": 1.0, "bails_vivants": []}}),
                                                encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    out = capsys.readouterr().out
    assert "[PM] AVEUGLE SUR bails" in out and "0 sessions AGAGI" in out
    assert "âge 10 min (generated_at)" in out and "TABLEAU PÉRIMÉ" not in out


# --- Défaut 1 (2026-09-24) : le tableau en cache PUBLIE son âge, et un tableau périmé n'est pas imprimé comme
# courant. Mesuré à l'essai d'acceptation : un BOARD vieux de ~31 h annonçait à chaque démarrage « AVEUGLE SUR
# bulletin absent pour agagi-11, b0, d7, c9 » alors que ces bulletins existaient.

def _board_cache(tmp_path, **kw):
    d = tmp_path / "pm"
    d.mkdir(exist_ok=True)
    board = {"generated_at": NOW, "aveugle": ["bulletin absent pour 4 session(s) : agagi-11, agagi-b0, agagi-d7, agagi-c9"],
             "sessions": [], "charge_connue": {"sims_en_vol": 0, "cpu_pct": 89.0, "bails_vivants": []},
             "alertes": [{"id": "A5", "cle": "A5:cpu", "gravite": "alerte", "message": "charge CPU = 89 %", "preuve": {}}]}
    board.update(kw)
    (d / "BOARD.json").write_text(json.dumps(board), encoding="utf-8")
    return str(d)


def test_CONTRE_EXEMPLE_tableau_RECENT_imprime_ses_alertes_DATEES_et_VIEUX_de_31_h_les_TAIT_et_dit_PERIME(tmp_path):
    """Les DEUX issues sur le MÊME tableau, seule l'horloge injectée change."""
    pm = _board_cache(tmp_path)
    recent = BU.resume_tableau(pm, now=NOW + 600)
    assert "âge 10 min (generated_at)" in recent
    assert "[PM] AVEUGLE SUR bulletin absent" in recent and "A5:cpu" in recent
    assert "TABLEAU PÉRIMÉ" not in recent
    vieux = BU.resume_tableau(pm, now=NOW + 31 * 3600)
    assert "TABLEAU PÉRIMÉ" in vieux and "il y a 31.0 h (generated_at)" in vieux
    assert "le tick NE TOURNE PAS" in vieux and "python -m tools.pm.board" in vieux and "/pm" in vieux
    assert "1 alerte(s), 1 aveuglement(s)" in vieux and "NON réimprimés comme courants" in vieux
    # le cœur du défaut : l'aveuglement FABRIQUÉ et l'alerte d'hier ne sont PAS présentés comme d'aujourd'hui
    assert "AVEUGLE SUR" not in vieux and "A5:cpu" not in vieux


def test_le_seuil_de_peremption_EST_le_TTL_du_bail_pm_et_tranche_a_la_seconde(tmp_path):
    from tools.pm import board as B
    from tools.pm import tick as TK
    assert B.PEREMPTION_S == TK.TTL_PM_S == 7200.0            # une seule source : le tick relit celle du tableau
    pm = _board_cache(tmp_path)
    assert "TABLEAU PÉRIMÉ" not in BU.resume_tableau(pm, now=NOW + B.PEREMPTION_S - 1)
    assert "TABLEAU PÉRIMÉ" in BU.resume_tableau(pm, now=NOW + B.PEREMPTION_S + 1)


def test_un_tableau_DATE_DU_FUTUR_n_est_pas_courant_mais_une_minute_de_gigue_l_est(tmp_path):
    pm = _board_cache(tmp_path)
    futur = BU.resume_tableau(pm, now=NOW - 3600)
    assert "DATÉ DU FUTUR de 60 min" in futur and "A5:cpu" not in futur and "AVEUGLE SUR" not in futur
    assert "A5:cpu" in BU.resume_tableau(pm, now=NOW - 30)                 # sous TOLERANCE_FUTUR_S : courant


def test_sans_generated_at_l_age_vient_du_MTIME_et_le_DIT(tmp_path):
    """Le repli existe et se nomme : un tableau sans `generated_at` est illisible par `summary`, mais son âge
    reste publié — lu du mtime, annoncé comme borne BASSE (le fichier est écrit APRÈS la mesure)."""
    pm = _board_cache(tmp_path)
    p = os.path.join(pm, "BOARD.json")
    with open(p, encoding="utf-8") as fh:
        b = json.load(fh)
    del b["generated_at"]
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(b, fh)
    os.utime(p, (NOW, NOW))
    t = BU.resume_tableau(pm, now=NOW + 31 * 3600)
    assert t.startswith("[PM] tableau illisible") and "31.0 h (mtime du fichier" in t and "borne BASSE" in t


def test_main_start_avec_un_BOARD_de_31_h_imprime_PERIME_et_pas_ses_alertes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(BU, "_horloge", lambda: NOW + 31 * 3600)
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "reg"))
    _board_cache(tmp_path)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    out = capsys.readouterr().out
    assert "TABLEAU PÉRIMÉ" in out and "AVEUGLE SUR" not in out and "A5:cpu" not in out
    assert not (tmp_path / "pm" / "hook_errors.log").exists()


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


def test_main_avec_argv_malforme_sort_0_et_journalise_argv(tmp_path, monkeypatch):
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    assert BU.main(["bogus"]) == 0
    log = (tmp_path / "pm" / "hook_errors.log").read_text(encoding="utf-8")
    assert "argv" in log


def test_main_HELP_sort_0_et_n_est_PAS_journalise_comme_un_echec(tmp_path, monkeypatch, capsys):
    """`--help` lève SystemExit(0) : le journaliser inventait un échec de hook, qu'A9 aurait fini par
    signaler. Un code de sortie 0 n'est pas une erreur."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    assert BU.main(["--help"]) == 0
    capsys.readouterr()
    assert not (tmp_path / "pm" / "hook_errors.log").exists()


def test_journal_des_hooks_TOURNE_au_dela_du_plafond_et_garde_la_QUEUE(tmp_path, monkeypatch):
    """Un hook cassé écrit ~2 ko à CHAQUE outil : sans rotation, le journal grossit sans borne dans
    `data/`. La QUEUE est ce qu'on garde — `read_hook_errors` ne regarde que 24 h."""
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "MAX_JOURNAL_O", 4000)
    monkeypatch.setattr(BU, "GARDE_JOURNAL_O", 1000)
    p = tmp_path / "pm" / "hook_errors.log"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"VIEILLE LIGNE A JETER\n" + b"x" * 5000 + b"\nDERNIERE LIGNE AVANT ROTATION\n")
    avant = p.stat().st_size
    BU._journal("stop", ValueError("boum"))
    txt = p.read_text(encoding="utf-8", errors="replace")
    assert p.stat().st_size < avant
    assert "DERNIERE LIGNE AVANT ROTATION" in txt and "VIEILLE LIGNE A JETER" not in txt
    assert "stop ValueError: boum" in txt                       # l'échec courant est bien ajouté APRÈS
    assert not (tmp_path / "pm" / "hook_errors.log.tmp").exists()

    # no-op EXACT : sous le plafond, le journal n'est PAS touché (rien de perdu par excès de zèle)
    petit = tmp_path / "pm" / "petit.log"
    petit.write_text("une ligne\n", encoding="utf-8")
    BU._rotation(str(petit), max_o=4000, garde_o=1000)
    assert petit.read_text(encoding="utf-8") == "une ligne\n"


def test_resume_tableau_BOARD_illisible_par_summary_dit_illisible_au_lieu_de_se_taire(tmp_path, monkeypatch):
    """`summary(board)` vivait HORS du try/except qui charge BOARD.json : un BOARD écrit par une autre
    version (clé manquante) faisait lever `summary`, le hook journalisait et n'imprimait RIEN."""
    from src import paths
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    d = paths.pm_dir()
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "BOARD.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_at": 1.0}, fh)
    assert BU.resume_tableau().startswith("[PM] tableau illisible")


# --- Défauts 2 et 5 (2026-09-24) : le NOM n'est pas une identité, et le pid ne venait de nulle part.
# Mesuré : au redémarrage de la flotte, TOUS les noms ont changé (agagi-11 -> agagi-e4, agagi-52 -> agagi-00…) et le
# bulletin gardait le PREMIER nom lu (`if name is None`) — le tableau adressait ses alertes à des noms morts ;
# `pid` valait null sur 11 bulletins sur 12 (le payload SessionStart n'en porte pas). Registre INJECTÉ (répertoire
# jetable), horloge INJECTÉE (`now`) : jamais le vrai registre, jamais l'horloge du jour.

def _registre(rep, fichiers):
    """Registre natif jetable sous `rep/reg` : {nom de fichier: entrée (dict) ou texte brut (entrée illisible)}."""
    d = rep / "reg"
    d.mkdir(parents=True, exist_ok=True)
    for nom, e in fichiers.items():
        (d / nom).write_text(e if isinstance(e, str) else json.dumps(e), encoding="utf-8")
    return str(d)


def _natif(sid, name, pid, started_ms=1_790_000_000_000):
    return {"pid": pid, "sessionId": sid, "name": name, "cwd": "c:/x/agagi", "startedAt": started_ms}


def test_identite_prend_l_entree_la_plus_RECENTE_du_meme_session_id_meme_si_l_ancien_pid_trie_DEVANT(tmp_path):
    """Une session reprise laisse au registre l'entrée de son ANCIEN pid, même sessionId. L'ordre du glob est celui
    des noms de fichiers, donc des pids : ici l'ancien (100) trie devant le nouveau (200)."""
    reg = _registre(tmp_path / "a", {"100.json": _natif("s1", "agagi-11", 100, started_ms=1_000_000),
                                     "200.json": _natif("s1", "agagi-e4", 200, started_ms=2_000_000)})
    assert BU.identite_depuis_registre("s1", reg) == {"statut": "registre", "name": "agagi-e4", "pid": 200}
    # l'autre sens : c'est `started_at` qui tranche, PAS l'ordre des fichiers — dates inversées, même ordre de glob
    reg2 = _registre(tmp_path / "b", {"100.json": _natif("s1", "agagi-11", 100, started_ms=2_000_000),
                                      "200.json": _natif("s1", "agagi-e4", 200, started_ms=1_000_000)})
    assert BU.identite_depuis_registre("s1", reg2) == {"statut": "registre", "name": "agagi-11", "pid": 100}


def test_identite_dit_INDISPONIBLE_ABSENTE_ou_PARTIELLEMENT_ILLISIBLE_et_n_affirme_l_absence_que_sur_un_registre_ENTIER(tmp_path):
    vide = {"name": None, "pid": None}
    assert BU.identite_depuis_registre("s1", str(tmp_path / "nulle_part")) == dict(vide, statut="registre indisponible")
    autre = {"7.json": _natif("s7", "agagi-52", 7)}
    assert BU.identite_depuis_registre("s1", _registre(tmp_path / "a", autre)) == dict(vide, statut="absente du registre")
    # une entrée illisible : la session y est PEUT-ÊTRE — l'absence n'est pas affirmée
    partiel = dict(autre, **{"casse.json": "{pas du json"})
    assert BU.identite_depuis_registre("s1", _registre(tmp_path / "b", partiel)) == \
        dict(vide, statut="registre partiellement illisible")
    # contrôle positif : l'entrée illisible ne masque pas une entrée LISIBLE de la session
    trouve = dict(partiel, **{"9.json": _natif("s1", "agagi-11", 9)})
    assert BU.identite_depuis_registre("s1", _registre(tmp_path / "c", trouve)) == \
        {"statut": "registre", "name": "agagi-11", "pid": 9}


def test_resoudre_identite_REMPLACE_nom_et_pid_pousse_l_ancien_nom_dans_noms_precedents_et_ne_mute_pas_l_entree():
    bul = dict(BU._vide("s1"), name="agagi-11", pid=100, identite="registre", identite_at=NOW - 3600)
    avant = json.dumps(bul, sort_keys=True)
    b = BU.resoudre_identite(bul, {"statut": "registre", "name": "agagi-e4", "pid": 200}, NOW)
    assert (b["name"], b["pid"], b["identite"], b["identite_at"]) == ("agagi-e4", 200, "registre", NOW)
    assert b["noms_precedents"] == ["agagi-11"]
    assert json.dumps(bul, sort_keys=True) == avant                          # PURE : l'entrée n'est pas mutée
    # no-op EXACT : le même nom relu ne pousse rien, seule la date de lecture avance
    b2 = BU.resoudre_identite(b, {"statut": "registre", "name": "agagi-e4", "pid": 200}, NOW + 1)
    assert b2["noms_precedents"] == ["agagi-11"] and b2["identite_at"] == NOW + 1
    # plafond : 10 noms gardés, le plus récent en QUEUE, jamais de doublon
    for i in range(12):
        b2 = BU.resoudre_identite(b2, {"statut": "registre", "name": f"n{i}", "pid": 1}, NOW + 2 + i)
    assert len(b2["noms_precedents"]) == 10 and b2["noms_precedents"][-1] == "n10" and b2["name"] == "n11"
    assert len(set(b2["noms_precedents"])) == 10


def test_resoudre_identite_GARDE_le_nom_sur_registre_INDISPONIBLE_ou_PARTIEL_et_le_RETIRE_sur_absence_d_un_registre_ENTIER():
    bul = dict(BU._vide("s1"), name="agagi-11", pid=100, identite="registre", identite_at=NOW - 3600)
    for statut in ("registre indisponible", "registre partiellement illisible"):
        b = BU.resoudre_identite(bul, {"statut": statut, "name": None, "pid": None}, NOW)
        assert (b["name"], b["pid"]) == ("agagi-11", 100), statut               # GARDÉS
        assert b["identite"] == statut and b["identite_at"] == NOW - 3600        # datés de leur LECTURE, pas de maintenant
        assert b["noms_precedents"] == []
    b = BU.resoudre_identite(bul, {"statut": "absente du registre", "name": None, "pid": None}, NOW)
    assert (b["name"], b["pid"], b["identite"], b["identite_at"]) == (None, None, "absente du registre", NOW)
    assert b["noms_precedents"] == ["agagi-11"]                                  # le nom perdu reste LISIBLE


def test_main_RE_RESOUT_nom_et_pid_depuis_le_registre_a_CHAQUE_ecriture_pas_seulement_la_premiere(tmp_path, monkeypatch):
    """Le défaut : `if name is None` gelait le nom au PREMIER hook. Le pid vient du registre, jamais du payload."""
    monkeypatch.setattr(BU, "_horloge", lambda: NOW)
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", _registre(tmp_path, {"100.json": _natif("s1", "agagi-11", 100)}))

    def lire():
        return json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart", pid=999))))   # pid du payload IGNORÉ
    assert BU.main(["start"]) == 0
    b = lire()
    assert (b["name"], b["pid"], b["identite"], b["identite_at"]) == ("agagi-11", 100, "registre", NOW)
    # no-op : registre inchangé, second hook -> même nom, rien dans noms_precedents
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("Stop"))))
    assert BU.main(["stop"]) == 0
    assert lire()["name"] == "agagi-11" and lire()["noms_precedents"] == []
    # la session est REPRISE : nouveau pid, nouveau nom ; l'ancienne entrée reste au registre et trie DEVANT
    (tmp_path / "reg" / "200.json").write_text(json.dumps(_natif("s1", "agagi-e4", 200, started_ms=1_790_000_001_000)),
                                               encoding="utf-8")
    monkeypatch.setattr(BU, "_horloge", lambda: NOW + 60)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("PostToolUse", tool_name="Edit",
                                                                     tool_input={"file_path": "c:/x/agagi/f.py"}))))
    assert BU.main(["tool"]) == 0
    b = lire()
    assert (b["name"], b["pid"], b["identite_at"], b["noms_precedents"]) == ("agagi-e4", 200, NOW + 60, ["agagi-11"])
    # `claim` ré-résout aussi (il écrivait lui aussi sous `if name is None`)
    (tmp_path / "reg" / "200.json").write_text(json.dumps(_natif("s1", "looper", 200, started_ms=1_790_000_001_000)),
                                               encoding="utf-8")
    assert BU.main(["claim", "P4.9", "--session", "s1"]) == 0
    b = lire()
    assert b["name"] == "looper" and b["noms_precedents"] == ["agagi-11", "agagi-e4"] and b["claims"] == ["P4.9"]


def test_un_pid_INCONNU_s_accompagne_d_une_identite_qui_l_explique(tmp_path, monkeypatch):
    """Un `pid` à null ne passe jamais pour une valeur : `identite` dit pourquoi il manque."""
    monkeypatch.setattr(BU, "_horloge", lambda: NOW)
    monkeypatch.setenv("AGAGI_DATA_ROOT", str(tmp_path).replace("\\", "/"))
    monkeypatch.setattr(BU, "REGISTRY_DIR", str(tmp_path / "nulle_part"))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("SessionStart"))))
    assert BU.main(["start"]) == 0
    b = json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))
    assert (b["pid"], b["identite"], b["identite_at"]) == (None, "registre indisponible", None)
    # le registre apparaît, SANS cette session : absence affirmée, datée
    monkeypatch.setattr(BU, "REGISTRY_DIR", _registre(tmp_path, {"7.json": _natif("s7", "agagi-52", 7)}))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_payload("Stop"))))
    assert BU.main(["stop"]) == 0
    b = json.loads((tmp_path / "sessions" / "s1.json").read_text(encoding="utf-8"))
    assert (b["pid"], b["identite"], b["identite_at"]) == (None, "absente du registre", NOW)
