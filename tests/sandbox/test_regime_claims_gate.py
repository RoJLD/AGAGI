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
    # DURCI (2026-09-24) : jusqu'ici ce temoin n'assertait que le NOM du parametre, donc RIEN ne
    # testait que la porte nomme la valeur qu'elle a pourtant LUE. Le cas FONDATEUR (E8 occ. 4) est
    # une CONTRADICTION -- cite 3.0, publie 1.0 -- et le detail doit le dire, sinon il est
    # indiscernable d'une absence.
    assert "3.0" in v["detail"][0] and "1.0" in v["detail"][0]
    assert "results/p41_grab_mechanism.json" in v["detail"][0]


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
    assert G.main(["--root", G._ROOT]) == 0, "un NOUVEAU discordant ou une REGRESSION hors baseline"


def test_main_rend_1_sur_un_NOUVEAU_record_discordant_et_0_quand_il_est_gele(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text(GRAB_COST_V1, encoding="utf-8")
    for i in range(60):     # sous le seuil minor (i) : un --root a 1 seul record refuserait --update-baseline
        (d / f"PADDING-{i:02d}.md").write_text("rien ici, juste pour depasser le seuil de 50 records.", encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "p41_grab_mechanism.json").write_text(json.dumps(REGIME_RACINE), encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": []}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    assert G.main(["--root", str(tmp_path)]) == 1
    assert G.main(["--root", str(tmp_path), "--update-baseline"]) == 0
    assert G.main(["--root", str(tmp_path)]) == 0


# ---------------------------------------------------------------------------------------------------
# Corrections de revue (2026-09-23) -- 5 Important tranches reels par le controleur.


def test_1_regime_imbrique_a_deux_niveaux_est_CONCORDE():
    """(a) `regime_values` descend RECURSIVEMENT -- pas seulement racine + 1er niveau de cellule."""
    data = {"outer": {"inner": {"regime": {"forage_payoff": 1.0}}}}
    v = G.evaluer("`forage_payoff = 1.0` (`results/x.json`)", lambda p: data)
    assert v["statut"] == "CONCORDE"


def test_1_valeur_publiee_SEULEMENT_hors_du_bloc_regime_est_CONCORDE_HORS_REGIME():
    """(b)(c) cas fondateur de la revue : S2-CREDIT-ABLATION cite `reward_scale`, publie par le runner
    dans `arms/<bras>/<seed>/learning/reward_scale`, jamais dans un bloc `regime` (le VOISIN
    S2-REWARD-ABLATION, lui, cite `reward_scale = 0` comme hypothese jamais mesuree -- reste DISCORDE,
    verifie contre le JSON reel dans le rapport de correction)."""
    data = {"regime": {}, "arms": {"b_full": {"2026": {"learning": {"reward_scale": 1.0}}}}}
    v = G.evaluer("`reward_scale = 1.0` (`results/x.json`)", lambda p: data)
    assert v["statut"] == "CONCORDE_HORS_REGIME"
    assert any("hors du bloc regime" in d and "results/x.json" in d for d in v["detail"])
    assert "CONCORDE_HORS_REGIME" in G.OK


def test_1_valeur_CONTREDITE_par_le_regime_ET_par_le_hors_regime_est_DISCORDE():
    """RENOMME le 2026-09-24. Il s'appelait `test_1_valeur_introuvable_nulle_part_reste_DISCORDE`
    alors que ses donnees PUBLIENT `forage_payoff: 1.0`, deux fois : ce n'est pas une introuvable,
    c'est une CONTRADICTION. Le nom mentait sur ce que le temoin teste -- et ce mensonge est la
    forme MINIATURE du defaut de la porte, qui disait « introuvable » d'une valeur qu'elle lisait."""
    data = {"regime": {"forage_payoff": 1.0}, "arms": {"a": {"forage_payoff": 1.0}}}
    v = G.evaluer("`forage_payoff = 3.0` (`results/x.json`)", lambda p: data)
    assert v["statut"] == "DISCORDE"
    assert "3.0" in v["detail"][0] and "1.0" in v["detail"][0]


def test_2_baseline_gele_un_STATUT_et_une_REGRESSION_vers_DISCORDE_bloque(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "R.md").write_text("`lr = 0,04` (`results/r.json`)", encoding="utf-8")
    (tmp_path / "results").mkdir()
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {"docs/EDR/R.md": "SANS_RESULTS"}}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    # results/r.json absent -> SANS_RESULTS, IDENTIQUE au gel -> ne bloque pas.
    assert G.main(["--root", str(tmp_path)]) == 0
    # Le fichier apparait, avec un regime qui NE PORTE PAS la valeur citee -> DISCORDE, PIRE que
    # SANS_RESULTS gele -> bloque, meme legataire.
    (tmp_path / "results" / "r.json").write_text(json.dumps({"regime": {"lr": 0.09}}), encoding="utf-8")
    assert G.main(["--root", str(tmp_path)]) == 1


def _bloc_porte_19_du_hook():
    hook = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "hooks", "pre-commit")
    with open(hook, encoding="utf-8") as fh:
        src = fh.read()
    i = src.index("# 19. REGIME")
    j = src.index("\nfi\n", i) + len("\nfi\n")
    return src[i:j]


def test_3_le_hook_ne_scope_PAS_only_quand_un_results_est_stage():
    """Test de FORME (aucun temoin executable ne lit le hook comme un sous-processus -- limite deja
    documentee dans CLAUDE.md/E14) : la condition qui autorise `--only` doit exiger l'ABSENCE de tout
    fichier stage hors docs/EDR (results/*.json, la baseline, ou le module lui-meme) -- sinon un bloc
    regime modifie pourrait invalider les affirmations d'AUTRES records sans re-verification."""
    bloc = _bloc_porte_19_du_hook()
    assert 'non_edr_rc=$(echo "$staged_rc" | grep -vE ' in bloc
    assert 'if [ -n "$only_rc" ] && [ -z "$non_edr_rc" ]; then' in bloc


def test_5a_le_hook_se_declenche_sur_SON_PROPRE_module():
    """Une nouvelle porte doit figurer dans sa PROPRE regex declenchante (comme les portes 5/8/13/21) --
    sinon editer le CHECKER sans toucher un docs/EDR ni un results/ ne re-executerait jamais rien."""
    bloc = _bloc_porte_19_du_hook()
    assert "tools/check_regime_claims\\.py" in bloc


def test_4_CONCORDE_nomme_le_FICHIER_qui_porte_la_valeur_parmi_plusieurs_cites():
    data_a = {"regime": {"forage_payoff": 3.0}}   # ne concorde PAS avec la valeur citee
    data_b = {"regime": {"forage_payoff": 1.0}}   # concorde

    def lecteur(p):
        return data_a if p == "results/a.json" else data_b
    v = G.evaluer("`forage_payoff = 1.0` (`results/a.json`, `results/b.json`)", lecteur)
    assert v["statut"] == "CONCORDE"
    assert any("results/b.json" in d for d in v["detail"])
    assert not any("results/a.json" in d for d in v["detail"])


def test_5_main_rend_1_sur_un_NOUVEAU_SANS_RESULTS(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text("`lr = 0,04` (`results/absent.json`)", encoding="utf-8")
    (tmp_path / "results").mkdir()
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    assert G.main(["--root", str(tmp_path)]) == 1


def test_5_main_rend_1_sur_un_NOUVEAU_SANS_REGIME(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text("`lr = 0,04` (`results/x.json`)", encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "x.json").write_text(json.dumps({"rows": []}), encoding="utf-8")
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    assert G.main(["--root", str(tmp_path)]) == 1


def test_minor_i_update_baseline_refuse_sous_50_records(tmp_path, monkeypatch):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("rien ici", encoding="utf-8")
    b = tmp_path / "base.json"
    monkeypatch.setattr(G, "_BASELINE", str(b))
    assert G.main(["--root", str(tmp_path), "--update-baseline"]) == 1
    assert not b.exists()


def test_minor_iii_SANS_RESULTS_distingue_absent_non_suivi_et_json_invalide(tmp_path):
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("`lr = 0,04` (`results/absent.json`)", encoding="utf-8")
    (d / "B.md").write_text("`lr = 0,04` (`results/present.json`)", encoding="utf-8")
    (d / "C.md").write_text("`lr = 0,04` (`results/mauvais.json`)", encoding="utf-8")
    (d / "D.md").write_text("`lr = 0,04` sans aucun fichier cite", encoding="utf-8")
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "present.json").write_text(json.dumps({"regime": {}}), encoding="utf-8")
    (tmp_path / "results" / "mauvais.json").write_text("{ceci n'est pas du JSON", encoding="utf-8")
    a = G.analyze(str(tmp_path), suivi=lambda root, rel: rel != "results/present.json")
    assert "fichier absent" in " ".join(a["records"]["docs/EDR/A.md"]["detail"])
    assert "non suivi par git" in " ".join(a["records"]["docs/EDR/B.md"]["detail"])
    assert "JSON invalide" in " ".join(a["records"]["docs/EDR/C.md"]["detail"])
    assert "aucun chemin" in " ".join(a["records"]["docs/EDR/D.md"]["detail"])


# ---------------------------------------------------------------------------------------------------
# 2026-09-24 -- TROIS SITUATIONS NE SE DISENT PLUS SOUS UN SEUL MOT.
#
# Defaut mesure en faisant tourner la porte sur son PROPRE cas fondateur : « cite 3.0, publie 1.0 » et
# « cite base_metabolism, jamais lu » rendaient la MEME chaine, au caractere pres, sous le MEME mot
# `DISCORDE` -- un mot qui AFFIRME un desaccord la ou la mesure est une non-lecture. Les trois temoins
# DISCORDE geles jusqu'ici (GRAB_COST l.40, le renomme ci-dessus, la regression de phase 2) sont TOUS
# des contradictions : la branche MAJORITAIRE -- 6 des 8 records fautifs du depot -- n'avait AUCUN
# temoin. C'est pour ca que le defaut a tenu une revue.


def test_deux_valeurs_lues_differentes_restent_DISCORDE_et_le_detail_NOMME_les_deux():
    # Cas FONDATEUR de la porte (E8 occ. 4) : le record annonce 3.0, le runner publie 1.0.
    bt = chr(96)
    texte = "Le regime porte forage_payoff = 3.0.\nResultats : " + bt + "results/t.json" + bt + "\n"
    r = G.evaluer(texte, lambda c: {"regime": {"forage_payoff": 1.0}})
    assert r["statut"] == "DISCORDE"
    assert "3.0" in r["detail"][0] and "1.0" in r["detail"][0]
    assert "results/t.json" in r["detail"][0]


def test_aucune_valeur_lue_rend_SANS_VALEUR_LUE_et_PUBLIE_ou_il_a_regarde():
    """La branche MAJORITAIRE, celle qui n'avait aucun temoin.

    ECART ASSUME AU BRIEF, mesure : le fixture prescrit ne portait QUE `base_metabolism_initial`, donc
    AUCUN parametre connu -- la garde amont (« aucun bloc regime ni parametre connu publie ») le classe
    SANS_REGIME avant d'arriver ici, et le brief interdit explicitement de recouvrir un cas deja gere en
    amont. Un `num_agents` publie suffit a placer le cas dans le domaine que le nouveau bareme gouverne ;
    les trois assertions sont celles du brief, mot pour mot. La frontiere est gelee juste en dessous."""
    bt = chr(96)
    texte = "Le regime porte base_metabolism = 0.7.\nResultats : " + bt + "results/t.json" + bt + "\n"
    r = G.evaluer(texte, lambda c: {"regime": {"base_metabolism_initial": 0.75, "num_agents": 12}})
    assert r["statut"] == "SANS_VALEUR_LUE"
    assert "1" in r["detail"][0]                        # le nombre de results LUS
    assert "base_metabolism_initial" in r["detail"][0]  # la CLE VOISINE, publiee


def test_FRONTIERE_un_results_sans_aucun_parametre_connu_reste_SANS_REGIME():
    """Le fixture VERBATIM du brief. SANS_REGIME est deja un « je n'ai rien pu confronter » de rang 2 :
    le recouvrir par SANS_VALEUR_LUE fabriquerait un verdict par-dessus une garde amont saine. Gele ici
    pour que l'ecart ci-dessus soit une DECISION mesuree, jamais un effet de bord."""
    bt = chr(96)
    texte = "Le regime porte base_metabolism = 0.7.\nResultats : " + bt + "results/t.json" + bt + "\n"
    r = G.evaluer(texte, lambda c: {"regime": {"base_metabolism_initial": 0.75}})
    assert r["statut"] == "SANS_REGIME"


def test_controle_positif_la_concordance_reste_CONCORDE():
    # Sans ce cas, les deux tests ci-dessus passeraient sur un instrument qui rend
    # DISCORDE pour TOUT -- un instrument qui ne peut pas produire les deux issues.
    bt = chr(96)
    texte = "Le regime porte forage_payoff = 1.0.\nResultats : " + bt + "results/t.json" + bt + "\n"
    r = G.evaluer(texte, lambda c: {"regime": {"forage_payoff": 1.0}})
    assert r["statut"] == "CONCORDE"


def test_la_valeur_lue_HORS_du_bloc_regime_est_nommee_elle_aussi():
    """Le cas 107 du depot : `max_ticks` cite 80, publie 12 sous `data/max_ticks` -- hors bloc regime.
    Une contradiction hors-regime est une contradiction ; le detail doit dire OU il a lu."""
    data = {"regime": {"num_agents": 24}, "data": {"max_ticks": 12}}
    r = G.evaluer("`max_ticks = 80` (`results/x.json`)", lambda p: data)
    assert r["statut"] == "DISCORDE"
    assert "80" in r["detail"][0] and "12" in r["detail"][0] and "results/x.json" in r["detail"][0]


def test_SANS_VALEUR_LUE_est_rang_2_comme_les_autres_non_lectures_et_reste_HORS_de_OK():
    """Un inconnu ne devient pas un vert : il cesse seulement d'AFFIRMER. Rang 2 = strictement meilleur
    que DISCORDE, donc la migration de baseline ne peut pas fabriquer de faux rouge."""
    assert G._RANG["SANS_VALEUR_LUE"] == 2 == G._RANG["SANS_RESULTS"] == G._RANG["SANS_REGIME"]
    assert G._RANG["DISCORDE"] == 3
    assert "SANS_VALEUR_LUE" not in G.OK and "DISCORDE" not in G.OK


def test_cles_voisines_ne_rend_QUE_les_cles_qui_portent_le_nom_et_jamais_le_nom_exact():
    data = {"regime": {"lr": 0.04, "frozen_phase2_lr": 0.0}, "_regime": {"lr_td": [0.1]}, "autre": 1}
    v = G.cles_voisines(data, "lr")
    assert "frozen_phase2_lr" in v and "lr_td" in v
    assert "lr" not in v and "autre" not in v
    assert G.cles_voisines(data, "forage_payoff") == []          # aucune voisine : liste VIDE, pas un verdict
    # l'alias inverse est cherche aussi : un record qui cite `n_agents` doit voir `num_agents_max`
    assert "num_agents_max" in G.cles_voisines({"num_agents_max": 30}, "num_agents")


def test_STEP5_contre_exemple_gele_un_NOUVEAU_DISCORDE_bloque_et_sa_correction_PASSE(tmp_path, monkeypatch):
    """Les DEUX issues sur le MEME dispositif : seule la valeur PUBLIEE change. Sans l'issue verte, un
    cliquet qui refuse tout aurait l'air de discriminer."""
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "N.md").write_text(GRAB_COST_V1, encoding="utf-8")
    (tmp_path / "results").mkdir()
    r = tmp_path / "results" / "p41_grab_mechanism.json"
    b = tmp_path / "base.json"
    b.write_text(json.dumps({"legataires": {}}), encoding="utf-8")
    monkeypatch.setattr(G, "_BASELINE", str(b))
    monkeypatch.setattr(G, "_tracked", lambda root, rel: True)
    r.write_text(json.dumps({"regime": {"forage_payoff": 1.0}}), encoding="utf-8")   # cite 3.0, publie 1.0
    assert G.main(["--root", str(tmp_path)]) == 1
    r.write_text(json.dumps({"regime": {"forage_payoff": 3.0}}), encoding="utf-8")   # la contradiction disparait
    assert G.main(["--root", str(tmp_path)]) == 0


def test_la_porte_PUBLIE_sa_cecite_une_citation_n_est_pas_forcement_une_PREMISSE(tmp_path, capsys):
    """`claims()` racle la prose sans distinguer une premisse d'une PREDICTION (S2-REWARD-ABLATION :
    `reward_scale = 0` est un bras DELIBEREMENT non couru), d'un contrefactuel, ou de la citation du
    regime d'un AUTRE record. La porte ne sait pas le voir -- elle doit donc le DIRE."""
    assert any("prediction" in c.lower() for c in G.CECITES)
    d = tmp_path / "docs" / "EDR"
    d.mkdir(parents=True)
    (d / "A.md").write_text("rien ici", encoding="utf-8")
    G.main(["--root", str(tmp_path), "--report"])
    sortie = capsys.readouterr().out.lower()
    assert "prediction" in sortie and "premisse" in sortie
