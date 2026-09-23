"""Porte 22 : un runner scelle qui compare des bras SOUS GRADIENT appelle la garde E19 -- un nul a pas
fixe s'est deja retourne (RETAIN-COMPOSE 0,173 -> 0,923 au seul lr) ; la garde existe et n'a qu'UN
appelant reel (tools/learner_calibration.py:120) sur onze points d'entree d'apprentissage.

⚠️ Ce runner reel N'APPELLE JAMAIS `verify(...)` -- ses bras sont des litteraux Python (`ARMS`), pas
une regle JSON scellee. Un perimetre borne aux appelants de `verify` le RATERAIT ENTIEREMENT : c'est
exactement le trou que ce cliquet doit fermer, donc le test dedie (plus bas) l'exige explicitement en
donnees REELLES, pas seulement en source synthetique.

⚠️ DEFAUT trouve en REVUE le 2026-09-23, corrige dans cette passe : `sous_gradient` rendait "aucune
grille de pas" -- une affirmation NEGATIVE de fond -- pour des regles dont la PROSE SCELLEE nomme
explicitement `lr`/`E19` sans exposer une forme structuree (S2-CREDIT-ABLATION et deux voisines,
runners VIVANTS, sortaient `couvert` sans ligne de rapport ni entree de baseline). Trois corrections :
(1) l'etat `indetermine` (rang entre couvert et nu) pour toute regle qui MENTIONNE le pas hors des cles
structurees ; (2) `cellule.lr=null` et les cles `lr_*` (prefixe) rejoignent les formes RECONNUES ;
(3) la baseline gele aussi la LISTE des appelants REELS de la garde -- sans ca, le seul controle
positif de cette porte (learner_calibration.py) pouvait perdre son appel sans que rien ne le refute."""
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

# Forme du VRAI runner vivant nomme par la revue (S2-CREDIT-ABLATION) : bras decrits en PROSE, aucune
# cle structuree -- mentionne "lr" et "E19" mais ne doit JAMAIS rendre "aucune grille de pas" en silence.
REGLE_PROSE_INDETERMINEE = {
    "mesure": "(b_lr) lr=0,004 (E19, pas 10x plus petit, meme signal)",
    "discrimination": {"6a": "PAS_OU_BRUIT -- le pas / le bruit d'estimation est le destructeur (E19)"},
}
REGLE_LR_UNIQUE = {"cellule": {"lr": [0.04]}}                      # un seul pas : deja inspectee, SILENCE legitime
REGLE_LR_NULL = {"cellule": {"lr": None, "policy": "legacy"}}
REGLE_LR_PREFIXE = {"cellule": {"lr_importe": 4.0, "lr_nouveau": 2.0, "lr_nouveau_par_agent": 0.125}}
SRC_PROSE = '''
from tools.preregister import verify
RULE = "PROSE-INDETERMINEE"
def main():
    regle = verify(RULE)
'''
SRC_ABSENTE_ET_PROSE = '''
from tools.preregister import verify
def main():
    verify("N-EXISTE-NULLE-PART")
    verify("PROSE-INDETERMINEE")
'''
SRC_ILLISIBLE_PERTINENT = '''
from tools.preregister import verify
def main(:
    regle = verify("X")
'''
SRC_ILLISIBLE_HORS_SUJET = '''
def main(:
    return 1 +
'''


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


# ---------------------------------------------------------------------------------------------------
# DEFAUT DE REVUE (2026-09-23) : indetermine, cellule.lr=null, cles lr_*, illisible, appelants_garde,
# --only vide refuse, cliquet NOMME les nouveaux non-bloquants.
# ---------------------------------------------------------------------------------------------------

def test_une_regle_EN_PROSE_qui_mentionne_lr_ET_E19_est_INDETERMINEE_jamais_silencieuse():
    """Forme EXACTE du defaut trouve en revue (S2-CREDIT-ABLATION) : bras decrits en PROSE, aucune cle
    structuree. `sous_gradient` doit rester False (rien de STRUCTURE ne tire) mais ne doit jamais faire
    croire a une negation confiante -- `mentionne_le_pas` doit dire vrai."""
    ok, raison = E.sous_gradient(REGLE_PROSE_INDETERMINEE)
    assert ok is False
    assert E.mentionne_le_pas(REGLE_PROSE_INDETERMINEE) is True
    et = E.etat([("tools/p.py", SRC_PROSE)], {"PROSE-INDETERMINEE": REGLE_PROSE_INDETERMINEE})
    assert et["tools/p.py"]["indetermines"] == ["PROSE-INDETERMINEE"]
    assert et["tools/p.py"]["sous_gradient"] is False
    assert E.runners_nus(et) == []                          # indetermine n'est JAMAIS compte nu
    assert E.classer(et) == {"tools/p.py": "indetermine"}
    assert "sans forme reconnue" in et["tools/p.py"]["raison"]


def test_mentionne_le_pas_ne_se_REDECLENCHE_PAS_sur_une_cle_DEJA_inspectee():
    """Une seule valeur de `cellule.lr` est une negation CONFIANTE (deja lue, deja jugee insuffisante),
    pas une cecite -- sinon TOUTE regle portant `cellule.lr` deviendrait indeterminee, y compris celles
    qui ont sincerement un seul pas."""
    assert E.sous_gradient(REGLE_LR_UNIQUE) == (False, "aucune grille de pas")
    assert E.mentionne_le_pas(REGLE_LR_UNIQUE) is False


def test_cellule_lr_null_et_cles_lr_prefixees_rejoignent_les_formes_RECONNUES():
    ok, raison = E.sous_gradient(REGLE_LR_NULL)
    assert ok is True and "null" in raison
    assert E.mentionne_le_pas(REGLE_LR_NULL) is False        # deja RECONNUE : pas une indetermination
    ok2, raison2 = E.sous_gradient(REGLE_LR_PREFIXE)
    assert ok2 is True and "3 pas distincts" in raison2


def test_classer_choisit_TOUJOURS_la_PIRE_categorie_quand_un_runner_en_cumule_plusieurs():
    et = E.etat([("tools/q.py", SRC_ABSENTE_ET_PROSE)],
                {"PROSE-INDETERMINEE": REGLE_PROSE_INDETERMINEE})   # N-EXISTE-NULLE-PART absente du dict
    assert et["tools/q.py"]["regle_absente"] == ["N-EXISTE-NULLE-PART"]
    assert et["tools/q.py"]["indetermines"] == ["PROSE-INDETERMINEE"]
    # indetermine (rang 4) est PIRE que regle_absente (rang 3) : c'est lui qui doit sortir, jamais le premier trouve.
    assert E.classer(et) == {"tools/q.py": "indetermine"}
    assert E._RANG["couvert"] < E._RANG["indetermine"] < E._RANG["nu"]
    assert E._RANG["non_resolu"] < E._RANG["regle_absente"] < E._RANG["indetermine"]


def test_un_fichier_ILLISIBLE_mais_PERTINENT_est_RAPPORTE_jamais_avale():
    et = E.etat([("tools/z.py", SRC_ILLISIBLE_PERTINENT), ("tools/w.py", SRC_ILLISIBLE_HORS_SUJET)], {})
    assert et["tools/z.py"]["illisible"] is True
    assert E.classer(et) == {"tools/z.py": "illisible"}
    assert "tools/w.py" not in et                            # hors sujet (ne mentionne ni verify ni la garde) : ignore comme avant


def test_REEL_trois_runners_VIVANTS_ne_sortent_plus_couvert_en_silence():
    """Les trois runners nommes par la revue -- S2-CREDIT-ABLATION, -2, S2-REWARD-ABLATION -- doivent
    etre INDETERMINES sur donnees REELLES, pas `couvert`."""
    et = E.etat(list(E._sources()), E.charger_regles(E._ROOT))
    for chemin in ("tools/evo_runs/s2_credit_ablation.py", "tools/evo_runs/s2_credit_ablation_2.py",
                  "tools/evo_runs/s2_reward_ablation.py"):
        assert chemin in et, chemin
        assert et[chemin]["indetermines"], f"{chemin} devrait mentionner le pas sans forme reconnue"
        assert E.classer(et).get(chemin) in ("indetermine", "nu"), chemin    # jamais absent, jamais couvert


def test_baseline_gele_les_APPELANTS_de_la_garde_et_une_PERTE_bloque(tmp_path, monkeypatch):
    """Minor (i) : sans ce gel dedie, le SEUL controle positif de la porte (learner_calibration.py) peut
    perdre son appel a la garde sans qu'aucun signal ne le dise -- `sous_gradient` retomberait a False
    (aucune regle JSON referencee) et le chemin sortirait simplement du perimetre, invisible."""
    b = tmp_path / "base.json"
    factices = [(f"tools/dummy_{i}.py",
                 'from tools.preregister import verify\nRULE = "DUMMY-%d"\ndef main():\n    verify(RULE)\n' % i)
                for i in range(9)]
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/g.py", GARDE_SEULE)] + factices)
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main(["--update-baseline"]) == 0
    assert json.loads(b.read_text(encoding="utf-8"))["appelants_garde"] == ["tools/g.py"]
    assert E.main([]) == 0                                    # rien n'a change : toujours vert
    # tools/g.py perd son appel (le fichier n'appelle plus la garde) -> le controle positif DISPARAIT.
    monkeypatch.setattr(E, "_sources", lambda: [("tools/g.py", "x = 1\n")] + factices)
    assert E.main([]) == 1


def test_baseline_ecrite_se_termine_par_un_saut_de_ligne(tmp_path, monkeypatch):
    b = tmp_path / "base.json"
    factices = [(f"tools/dummy_{i}.py",
                 'from tools.preregister import verify\nRULE = "DUMMY-%d"\ndef main():\n    verify(RULE)\n' % i)
                for i in range(9)]
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/a.py", GARDE)] + factices)
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main(["--update-baseline"]) == 0
    assert b.read_text(encoding="utf-8").endswith("\n")


def test_only_VIDE_est_REFUSE_jamais_un_vert_trompeur():
    assert E.main(["--only"]) == 1
    assert E.main(["--report", "--only"]) == 1


def test_un_NOUVEAU_indetermine_BLOQUE_comme_un_nu_couvert_vers_indetermine(tmp_path, monkeypatch):
    """Exigence LITTERALE de la revue : indetermine est de rang ENTRE couvert et nu, « couvert ->
    indetermine bloque » -- une regle toute neuve qui mentionne le pas sans forme reconnue bloque
    IMMEDIATEMENT, pas seulement signalee au prochain --update-baseline (contrairement a non_resolu/
    regle_absente, des limites de l'ANALYSE, pas des choix de l'auteur)."""
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    factices = [(f"tools/dummy_{i}.py",
                 'from tools.preregister import verify\nRULE = "DUMMY-%d"\ndef main():\n    verify(RULE)\n' % i)
                for i in range(9)]
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/p.py", SRC_PROSE)] + factices)
    monkeypatch.setattr(E, "charger_regles",
                        lambda root: {**REGLES, "PROSE-INDETERMINEE": REGLE_PROSE_INDETERMINEE})
    assert E.main([]) == 1


def test_cliquet_NOMME_les_non_resolu_et_regle_absente_NOUVEAUX_hors_baseline(tmp_path, monkeypatch, capsys):
    """Minor (ii) : aujourd'hui seul le compteur AGREGE sortait en mode cliquet -- un nouveau runner non
    resolu ou a regle absente etait invisible pour qui committe, il ne voit que le chiffre de tete."""
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    factices = [(f"tools/dummy_{i}.py",
                 'from tools.preregister import verify\nRULE = "DUMMY-%d"\ndef main():\n    verify(RULE)\n' % i)
                for i in range(8)]
    monkeypatch.setattr(E, "_BASELINE", str(b))
    monkeypatch.setattr(E, "_sources", lambda: [("tools/f.py", ARGV), ("tools/h.py", REGLE_ABSENTE_SRC)] + factices)
    monkeypatch.setattr(E, "charger_regles", lambda root: REGLES)
    assert E.main([]) == 0                                    # ni non_resolu ni regle_absente ne bloquent seuls
    sortie = capsys.readouterr().out
    assert "tools/f.py" in sortie and "tools/h.py" in sortie
