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
