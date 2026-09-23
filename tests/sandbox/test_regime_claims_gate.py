"""Porte 19 : une valeur de parametre citee par un record est une MESURE publiee par le runner (bloc regime),
pas un decor recopie de memoire (E8 occ. 4 : forage_payoff = 3.0 alors que le run tournait a 1.0)."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_regime_claims as G  # noqa: E402

GRAB_COST_V1 = ("le régime de famine dure porte `forage_payoff = 3.0` — ramasser un fruit RAPPORTE. "
                "Résultats (`results/p41_grab_mechanism.json`).")
GRAB_COST_RECTIFIE = GRAB_COST_V1 + " Mesuré : `run_condition` construit avec `config=None`, donc `forage_payoff = 1.0`."
CALIB = ("`natural` (tel que publié : `lr = 0,04`), `lr_low` (`lr = 0,004`), `n_agents`=12 ; "
         "(`results/legacy_lr_curve_r2.json`, `cost`).")
REGIME_RACINE = {"regime": {"forage_payoff": 1.0, "num_agents": 20, "max_ticks": 400}}
REGIME_CELLULES = {"_design": {}, "lr=0.04|seed=2026": {"regime": {"num_agents": 12, "forage_payoff": 0.0}},
                   "lr=0.004|seed=2026": {"regime": {"num_agents": 12}}}


def test_claims_lit_les_trois_placements_du_backtick_et_la_virgule_francaise():
    c = G.claims("`forage_payoff = 3.0` ; `lr`=0,05 ; lr=0,002 ; `cog_gain=12.0, base_metabolism=0.75, immortal=True`")
    assert c["forage_payoff"] == {3.0} and c["lr"] == {0.05, 0.002}
    assert c["cog_gain"] == {12.0} and c["base_metabolism"] == {0.75}
    assert "immortal" not in c and "seeds" not in G.claims("3 seeds × 18 ères")


def test_cited_results_ne_retient_que_les_chemins_results_json_en_backtick():
    t = "(`results/a.json`, `results/lock_001_pred2_r{2,3,4}.json`, `docs/preregistrations/X.json`, `témoins `results/b_K{3,4}.json`)"
    assert G.cited_results(t) == ["results/a.json", "results/b_K{3,4}.json", "results/lock_001_pred2_r{2,3,4}.json"]


def test_regime_values_lit_la_racine_les_cellules_et_les_cles_de_cellule():
    r = G.regime_values(REGIME_RACINE)
    assert r["forage_payoff"] == {1.0} and r["num_agents"] == {20.0} and r["max_ticks"] == {400.0}
    c = G.regime_values(REGIME_CELLULES)
    assert c["lr"] == {0.04, 0.004} and c["num_agents"] == {12.0} and c["forage_payoff"] == {0.0}


def test_CONTRE_EXEMPLE_GELE_EDR_GRAB_COST_au_2026_09_09_est_DISCORDE():
    v = G.evaluer(GRAB_COST_V1, lambda p: REGIME_RACINE)
    assert v["statut"] == "DISCORDE" and "forage_payoff" in " ".join(v["detail"])


def test_la_rectification_qui_cite_la_vraie_ET_la_fausse_valeur_CONCORDE():
    assert G.evaluer(GRAB_COST_RECTIFIE, lambda p: REGIME_RACINE)["statut"] == "CONCORDE"


def test_alias_n_agents_num_agents_et_ticks_max_ticks():
    v = G.evaluer("`n_agents`=20 et `ticks`=400 (`results/x.json`)", lambda p: REGIME_RACINE)
    assert v["statut"] == "CONCORDE"


def test_record_sans_parametre_ou_sans_results_ou_sans_regime():
    assert G.evaluer("aucun chiffre ici", lambda p: None)["statut"] == "SANS_PARAMETRE"
    assert G.evaluer("`lr = 0,04` sans fichier", lambda p: None)["statut"] == "SANS_RESULTS"
    assert G.evaluer("`lr = 0,04` (`results/x.json`)", lambda p: {"rows": []})["statut"] == "SANS_REGIME"
    assert G.evaluer("`lr = 0,04` (`results/x.json`)", lambda p: None)["statut"] == "SANS_RESULTS"   # fichier absent -> rapporte


def test_CALIB_LEARNER_concorde_avec_les_cellules_imbriquees():
    assert G.evaluer(CALIB, lambda p: REGIME_CELLULES)["statut"] == "CONCORDE"


def test_analyze_rapporte_les_records_ILLISIBLES_au_lieu_de_les_ignorer(tmp_path):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("`lr = 0,04` (`results/x.json`)", encoding="utf-8")
    (d / "B.md").write_bytes(b"\xff\xfe\x00\x00 pas de l'utf-8 valide \x80")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text(json.dumps({"regime": {"lr": 0.04}}), encoding="utf-8")
    a = G.analyze(str(tmp_path), suivi=lambda root, rel: True)          # tmp_path n'est pas un depot git : suivi injecte
    assert a["records"]["docs/EDR/A.md"]["statut"] == "CONCORDE" and a["illisibles"] == ["docs/EDR/B.md"]


def test_le_depot_REEL_n_a_aucun_record_HORS_baseline_qui_discorde():
    a = G.analyze(G._ROOT)
    assert len(a["records"]) > 100, "le périmètre est vide, le test ne prouverait rien"
    base = set(G._load_baseline())
    hors = {f: v["statut"] for f, v in a["records"].items()
            if f not in base and v["statut"] not in ("SANS_PARAMETRE", "CONCORDE")}
    assert hors == {}, hors


def test_main_rend_1_sur_un_NOUVEAU_record_discordant_et_0_quand_il_est_gele(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text(GRAB_COST_V1, encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "p41_grab_mechanism.json").write_text(json.dumps(REGIME_RACINE), encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": []}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    assert G.main(["--root", str(tmp_path)]) == 1
    assert G.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    assert G.main(["--root", str(tmp_path)]) == 0
