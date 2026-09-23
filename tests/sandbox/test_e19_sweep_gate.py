"""Porte 22 : un runner scelle qui compare des bras SOUS GRADIENT appelle la garde E19 -- un nul a pas
fixe s'est deja retourne (RETAIN-COMPOSE 0,173 -> 0,923 au seul lr) ; la garde existe et n'a qu'UN
appelant reel (tools/learner_calibration.py:120) sur onze points d'entree d'apprentissage.

⚠️ Ce runner reel N'APPELLE JAMAIS `verify(...)` -- ses bras sont des litteraux Python (`ARMS`), pas
une regle JSON scellee. Un perimetre borne aux appelants de `verify` le RATERAIT ENTIEREMENT : c'est
exactement le trou que ce cliquet doit fermer, donc le test dedie (plus bas) l'exige explicitement en
donnees REELLES, pas seulement en source synthetique."""
import ast
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_e19_optimizer_sweep as E  # noqa: E402

NU = '''
from tools.preregister import verify
RULE = "LEGACY-LR-CURVE-R2"
def main():
    regle = verify(RULE)
'''
GARDE = NU + '''
    from tools.experiment_preflight import assert_verdict_invariant_to_optimizer
    assert_verdict_invariant_to_optimizer(lambda lr: (0.1, 0.5), lrs=(0.04, 0.004))
'''
ARGV = '''
from tools.preregister import verify
def main(argv):
    nom = argv[argv.index("--regle") + 1]
    regle = verify(nom)
'''
IFEXP = '''
from tools import preregister
SMOKE = False
rule = preregister.verify("EVO-028-SMOKE" if SMOKE else "EVO-028")
'''
# Un runner qui appelle la garde DIRECTEMENT, sans jamais sceller de regle JSON -- la forme du seul
# appelant reel du depot (tools/learner_calibration.py).
GARDE_SEULE = '''
def mesure(lr):
    return 0.1, 0.5
from tools.experiment_preflight import assert_verdict_invariant_to_optimizer
assert_verdict_invariant_to_optimizer(mesure, lrs=(0.04, 0.004))
'''
REGLE_ABSENTE_SRC = '''
from tools.preregister import verify
RULE = "N-EXISTE-NULLE-PART"
def main():
    regle = verify(RULE)
'''
REGLES = {"LEGACY-LR-CURVE-R2": {"cellule": {"lr": [0.0, 0.04, 0.004]}},
          "EVO-028": {"arms": {"a": "x", "b": "y"}},
          "EVO-028-SMOKE": {"design": "smoke"},
          "LOCK": {"cellules": [{"lr": 0.0005, "episodes": 14400}, {"lr": 0.002, "episodes": 1600}]},
          "COORD": {"sender_lr": 0.05}, "CLAUSE": {"clause_E19": "..."}}


def test_noms_regles_resout_constante_nom_de_module_et_ifexp_et_RAPPORTE_argv():
    assert E.noms_regles(ast.parse(NU)) == {"resolus": ["LEGACY-LR-CURVE-R2"], "non_resolus": []}
    assert E.noms_regles(ast.parse(IFEXP))["resolus"] == ["EVO-028", "EVO-028-SMOKE"]
    r = E.noms_regles(ast.parse(ARGV))
    assert r["resolus"] == [] and len(r["non_resolus"]) == 1


def test_sous_gradient_reconnait_les_cinq_formes_et_pas_une_comparaison_evolutive():
    assert E.sous_gradient(REGLES["LEGACY-LR-CURVE-R2"])[0] is True
    assert E.sous_gradient(REGLES["LOCK"])[0] is True and E.sous_gradient(REGLES["COORD"])[0] is True
    assert E.sous_gradient(REGLES["CLAUSE"])[0] is True
    assert E.sous_gradient({"cellule": {"bras": {"lr0_reference": 0.0, "natural": None}}})[0] is True
    assert E.sous_gradient(REGLES["EVO-028"])[0] is False
    assert E.sous_gradient({"cellule": {"lr": [0.04]}})[0] is False                   # un seul pas : rien à balayer


def test_CONTRE_EXEMPLE_GELE_un_runner_sous_gradient_SANS_garde_est_NU_et_avec_garde_ne_l_est_pas():
    et = E.etat([("tools/a.py", NU), ("tools/b.py", GARDE)], REGLES)
    assert E.runners_nus(et) == ["tools/a.py"]
    assert et["tools/b.py"]["garde"] is True and et["tools/b.py"]["sous_gradient"] is True


def test_un_runner_evolutif_n_est_pas_concerne_et_un_argv_est_rapporte_non_resolu():
    et = E.etat([("tools/e.py", IFEXP), ("tools/f.py", ARGV)], REGLES)
    assert et["tools/e.py"]["sous_gradient"] is False and E.runners_nus(et) == []
    assert et["tools/f.py"]["non_resolus"] and et["tools/f.py"]["regles"] == []


def test_un_module_qui_appelle_directement_la_garde_est_dans_le_perimetre_et_couvert_SANS_verify():
    """La forme du seul appelant reel (tools/learner_calibration.py) : AUCUN `verify(...)`, la garde
    seule prouve le design sous gradient. Sans cette branche, le perimetre le RATERAIT."""
    et = E.etat([("tools/g.py", GARDE_SEULE)], {})
    assert et["tools/g.py"]["regles"] == [] and et["tools/g.py"]["non_resolus"] == []
    assert et["tools/g.py"]["sous_gradient"] is True and et["tools/g.py"]["garde"] is True
    assert E.runners_nus(et) == []


def test_regle_absente_est_DISTINCTE_de_non_resolu_et_n_est_jamais_comptee_nue():
    et = E.etat([("tools/h.py", REGLE_ABSENTE_SRC)], {})            # dict de regles VIDE -> introuvable
    assert et["tools/h.py"]["regle_absente"] == ["N-EXISTE-NULLE-PART"]
    assert et["tools/h.py"]["non_resolus"] == []
    assert et["tools/h.py"]["sous_gradient"] is False
    assert E.runners_nus(et) == []
    assert E.classer(et) == {"tools/h.py": "regle_absente"}


def test_classer_donne_un_rang_ET_la_baseline_le_conserve_PAR_raison(tmp_path):
    et = E.etat([("tools/a.py", NU), ("tools/f.py", ARGV), ("tools/h.py", REGLE_ABSENTE_SRC)],
                {**REGLES})
    c = E.classer(et)
    assert c["tools/a.py"] == "nu" and c["tools/f.py"] == "non_resolu" and c["tools/h.py"] == "regle_absente"
    assert E._RANG["non_resolu"] < E._RANG["regle_absente"] < E._RANG["nu"]


def test_le_depot_REEL_n_a_aucun_runner_nu_HORS_baseline():
    et = E.etat(list(E._sources()), E.charger_regles(E._ROOT))
    assert len(et) >= 15, "le périmètre est vide, le test ne prouverait rien"
    assert sorted(set(E.runners_nus(et)) - set(p for p, r in E._load_baseline().items() if r == "nu")) == []


def test_temoin_REEL_learner_calibration_est_dans_le_perimetre_sous_gradient_ET_couvert():
    """Le CONTRÔLE POSITIF sur données réelles exigé par la revue : le seul appelant réel de la garde
    E19 doit être classé COUVERT, pas absent du périmètre ni faussement nu."""
    et = E.etat(list(E._sources()), E.charger_regles(E._ROOT))
    assert "tools/learner_calibration.py" in et, "le seul appelant réel de la garde E19 est hors périmètre"
    v = et["tools/learner_calibration.py"]
    assert v["sous_gradient"] is True and v["garde"] is True
    assert "tools/learner_calibration.py" not in E.runners_nus(et)
    assert E.classer(et).get("tools/learner_calibration.py") is None            # couvert : jamais gelé


def test_main_1_puis_gel_puis_0(tmp_path, monkeypatch):
    # >= _MIN_SCELLES sources : 1 vrai nu + 9 factices "regle_absente" (chacune un appel verify() a un
    # nom introuvable) pour que le scope depasse le seuil de la garde de compte sans polluer le nu.
    factices = [(f"tools/dummy_{i}.py",
                 'from tools.preregister import verify\nRULE = "DUMMY-%d"\ndef main():\n    verify(RULE)\n' % i)
                for i in range(9)]
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/a.py", NU)] + factices)
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main([]) == 1
    assert E.main(["--update-baseline"]) == 0
    assert E.main([]) == 0


def test_update_baseline_REFUSE_sous_le_seuil_et_ne_touche_PAS_le_disque(tmp_path, monkeypatch):
    b = tmp_path / "base.json"
    contenu_avant = json.dumps({"legataires": {"tools/x.py": "nu"}})
    b.write_text(contenu_avant, encoding="utf-8")
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/a.py", NU)])           # 1 seul < _MIN_SCELLES
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main(["--update-baseline"]) == 1
    assert b.read_text(encoding="utf-8") == contenu_avant


def test_un_legataire_qui_EMPIRE_de_non_resolu_a_nu_bloque_meme_deja_connu(tmp_path, monkeypatch):
    """La forme nommee par la revue : un legataire connu `non_resolu` qui devient resolument `nu` doit
    bloquer, pas passer inapercu parce que le CHEMIN etait deja dans la baseline."""
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {"tools/a.py": "non_resolu"}}), encoding="utf-8")
    factices = [(f"tools/dummy_{i}.py",
                 'from tools.preregister import verify\nRULE = "DUMMY-%d"\ndef main():\n    verify(RULE)\n' % i)
                for i in range(9)]
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/a.py", NU)] + factices)   # tools/a.py est un VRAI nu
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main([]) == 1
