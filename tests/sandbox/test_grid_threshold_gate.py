"""Porte 24 : aucune NOUVELLE comparaison « a OP b ± marge » en flottants nus dans un runner (classe E30, P2.105).

Le cas fondateur (BILINEAR-SHAM-R1) a publié 8/12 pour 9/12 exact ; le second (TD-STEP-PILOT) avait reçu une
rétro-application annoncée « sur ses trois lectures » — MESURÉ en écrivant cette porte : `_lecture_r1` comparait
encore en flottants nus. Ces tests portent sur la couche qui IDENTIFIE (arbre factice, coût nul), sur le cliquet
(baseline, --only, --update-baseline) et sur un ancrage RÉEL : td_step_pilot.py ne porte plus aucun site nu et
appelle le helper.

⚠️ Ce que la porte ne lit PAS, et qui est gelé ici comme tel : la NATURE de la grandeur (une moyenne comparée à une
marge est un site de FORME — à déclarer par `cmp_continu`, jamais deviné) et la forme « barre » (`x < 0.5`).
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_grid_threshold as G  # noqa: E402

NU = "def lecture(db, seeds):\n    return sum(1 for sd in seeds if db[sd] > db['ref'] + 0.05)\n"
NU_NOM = "def verdict(a, b, marge):\n    return a >= b - marge\n"
CONTINU_NU = "import numpy as np\ndef v(a, b):\n    return np.mean(a) > np.mean(b) + 0.15\n"
DECLARE = ("from tools.grid_compare import cmp_grille, cmp_continu\n"
           "def lecture(db, seeds):\n    return sum(1 for sd in seeds if cmp_grille(db[sd], db['ref'], 0.05, 640))\n"
           "def v(a, b):\n    return cmp_continu(a, b, 0.15)\n")
BARRE = "def v(x):\n    return x < 0.5\n"                 # forme « barre » : HORS motif, et c'est dit
ENTIER = "def f(x):\n    return x > 0.5 + 1\n"            # entier à droite : pas une marge flottante
ILLISIBLE = "def (:\n"
_CLE_NU = "tools/a.py::lecture::db[sd] > db['ref'] + 0.05"


def test_CONTRE_EXEMPLE_GELE_une_comparaison_nue_a_marge_est_un_site_dont_la_cle_ignore_le_numero_de_ligne():
    s = G.sites("tools/a.py", NU)
    assert len(s) == 1 and s[0]["cle"] == _CLE_NU and s[0]["ligne"] == 2 and s[0]["fonction"] == "lecture"
    deplace = G.sites("tools/a.py", "\n\n\n" + NU)
    assert deplace[0]["cle"] == _CLE_NU and deplace[0]["ligne"] == 5     # la clé survit aux éditions au-dessus


def test_une_marge_NOMMEE_est_un_site_et_une_moyenne_nue_aussi_la_forme_ne_lit_pas_la_nature():
    assert [x["cle"] for x in G.sites("tools/b.py", NU_NOM)] == ["tools/b.py::verdict::a >= b - marge"]
    assert len(G.sites("tools/c.py", CONTINU_NU)) == 1     # faux positif de FORME : à DÉCLARER (cmp_continu)


def test_un_site_DECLARE_par_le_helper_est_invisible_et_compte_comme_declare():
    assert G.sites("tools/d.py", DECLARE) == []
    assert G.appels_helper(DECLARE) == 2
    assert G.appels_helper("def f():\n    return cmp_grille\n") == 0     # nommé sans être appelé : rien


def test_la_forme_BARRE_et_la_marge_ENTIERE_sont_HORS_motif():
    assert G.sites("tools/e.py", BARRE) == [] and G.sites("tools/e.py", ENTIER) == []


def test_un_fichier_ILLISIBLE_est_RAPPORTE_jamais_compte_zero():
    res = G.scan([("tools/x.py", ILLISIBLE), ("tools/a.py", NU)])
    assert res["illisibles"] == ["tools/x.py"] and len(res["sites"]) == 1


def test_le_helper_lui_meme_est_HORS_perimetre():
    res = G.scan([(G._HELPER, "def cmp_continu(x, y, m):\n    return x > y + m\n")])
    assert res["sites"] == [] and res["illisibles"] == []


def _faux(monkeypatch, tmp_path, sources, min_sites=1):
    monkeypatch.setattr(G, "_sources", lambda: list(sources))
    monkeypatch.setattr(G, "_BASELINE", str(tmp_path / "base.json"))
    monkeypatch.setattr(G, "_MIN_SITES", min_sites)


def test_main_1_nouveau_puis_gel_puis_0(monkeypatch, tmp_path, capsys):
    _faux(monkeypatch, tmp_path, [("tools/a.py", NU)])
    assert G.main([]) == 1
    assert "tools/a.py::lecture" in capsys.readouterr().out
    assert G.main(["--update-baseline"]) == 0
    with open(tmp_path / "base.json", encoding="utf-8") as fh:
        assert json.load(fh)["sites"] == [_CLE_NU]
    assert G.main([]) == 0


def test_update_baseline_REFUSE_sous_le_seuil_et_laisse_le_disque_intact(monkeypatch, tmp_path):
    _faux(monkeypatch, tmp_path, [("tools/a.py", NU)], min_sites=20)
    assert G.main(["--update-baseline"]) == 2
    assert not (tmp_path / "base.json").exists()


def test_only_VIDE_est_refuse_et_only_cible_ne_bloque_que_sa_portee(monkeypatch, tmp_path, capsys):
    _faux(monkeypatch, tmp_path, [("tools/a.py", NU)])
    assert G.main(["--only"]) == 2
    assert G.main(["--only", "tools/b.py"]) == 0                # le nouveau est HORS portée : rapporté, pas bloquant
    assert "HORS PORT" in capsys.readouterr().out
    assert G.main(["--only", "tools/a.py"]) == 1


def test_un_site_gele_qui_disparait_est_RAPPORTE_resorbe(monkeypatch, tmp_path, capsys):
    _faux(monkeypatch, tmp_path, [("tools/a.py", NU)])
    assert G.main(["--update-baseline"]) == 0
    monkeypatch.setattr(G, "_sources", lambda: [("tools/a.py", DECLARE)])
    assert G.main([]) == 0
    assert "résorbé" in capsys.readouterr().out


def test_le_depot_REEL_n_a_aucune_comparaison_nue_hors_baseline_et_td_step_pilot_est_DECLARE():
    """Ancrage réel : aucune nouvelle ; et le second cas d'E30 (td_step_pilot.py, trois lectures) ne porte plus
    AUCUN site nu — son R1 comparait encore en flottants nus le 2026-09-26, trouvé en écrivant la porte."""
    assert G.main([]) == 0
    res = G.scan()
    assert not [s for s in res["sites"] if s["chemin"] == "tools/td_step_pilot.py"]
    assert res["declares"].get("tools/td_step_pilot.py", 0) >= 5       # R0 n_sup/n_inf/barre, R1 n_sup, R2 n_sup
    assert len(G.cles(res)) >= G._MIN_SITES
