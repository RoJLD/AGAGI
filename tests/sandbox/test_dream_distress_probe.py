from tools.dream_distress_probe import dream_rate, distress_split


def test_dream_rate_known_values():
    assert dream_rate({"age": 10, "total_dreams": 5}) == 0.5
    assert dream_rate({"age": 200, "total_dreams": 10}) == 0.05
    assert dream_rate({"age": 0, "total_dreams": 0}) == 0.0      # max(age,1) -> pas de div par zero
    assert dream_rate({"age": 0, "total_dreams": 3}) == 3.0      # age 0 -> denominateur 1


def test_distress_split_short_dream_more():
    """Court-vivants rêvent plus (taux haut) -> delta > 0 = signature de détresse."""
    stats = [
        {"age": 20, "total_dreams": 10},   # court (sous mediane), taux 0.5
        {"age": 25, "total_dreams": 12},   # court, taux 0.48
        {"age": 100, "total_dreams": 5},   # long, taux 0.05
        {"age": 120, "total_dreams": 6},   # long, taux 0.05
    ]
    out = distress_split(stats)
    assert out["n_short"] == 2 and out["n_long"] == 2
    assert out["rate_short"] > out["rate_long"]
    assert out["delta"] > 0


def test_distress_split_age_floor_excludes_tiny():
    """Le filtre age_floor écarte l'artefact petit-âge (mort à 2 ticks avec 1 rêve = taux 0.5)."""
    stats = [
        {"age": 2, "total_dreams": 1},     # ECARTE (age < 10)
        {"age": 50, "total_dreams": 5},
        {"age": 150, "total_dreams": 3},
    ]
    out = distress_split(stats, age_floor=10)
    assert out["n_short"] + out["n_long"] == 2     # l'agent age 2 est exclu


def test_distress_split_empty_no_crash():
    """⚠️ CORRIGÉ le 2026-09-08 (INJ6). Ce test EXIGEAIT que la cohorte vide rende `delta == 0.0`,
    c.-à-d. le contraste NUL comme une MESURE — la forme (a) du biais du dépôt, et le pire état pour
    un défaut : gelé par un test VERT (même histoire que `organ_prevalence`, tools/dreaming_probe.py).
    Agrégé sur 5 seeds, ce zéro publiait NEUTRE : « les rêves ne se concentrent pas chez les
    mourants » — le négatif recherché, obtenu sans une seule mesure. Le contrat est désormais une
    indétermination NOMMÉE, et `delta is None` (pas `nan` : `None > 0` lève, `nan > 0` ment)."""
    out = distress_split([], age_floor=10)
    assert out["status"] == "INDETERMINE_AUCUN_AGENT_MESURABLE", out
    assert out["rate_short"] is None and out["rate_long"] is None and out["delta"] is None
    assert out["n_short"] == 0 and out["n_long"] == 0
    # (b) même indétermination par l'autre porte : tous les agents SOUS le plancher d'âge — ce que
    # le plancher est justement là pour signaler.
    sous_plancher = distress_split([{"age": 3, "total_dreams": 3}, {"age": 4, "total_dreams": 8}],
                                   age_floor=10)
    assert sous_plancher["status"] == "INDETERMINE_AUCUN_AGENT_MESURABLE", sous_plancher
    assert sous_plancher["delta"] is None


def test_distress_split_empty_short_group_is_INDETERMINE_not_a_zero_rate():
    """Extinction totale à `max_ticks` : tous les agents meurent au MÊME âge -> la médiane d'âge ÉGALE
    cet âge -> le groupe court-vivant est VIDE. `r_short = ... if short else 0.0` en faisait un taux
    MESURÉ de 0.0, donc delta = -rate_long : l'affirmation de fond « les long-vivants rêvent plus, le
    rêve protège » (BENEFIQUE) tirée d'un split dont un côté n'existe pas."""
    plat = [{"age": 20, "total_dreams": 20} for _ in range(4)]      # âges identiques, taux 1.0
    out = distress_split(plat, age_floor=10)
    assert out["n_short"] == 0 and out["n_long"] == 4, out
    assert out["status"] == "INDETERMINE_GROUPE_VIDE", out
    assert out["rate_short"] is None and out["delta"] is None, out
    # le côté RÉELLEMENT mesuré reste publié : l'indétermination porte sur le CONTRASTE, pas sur tout.
    assert out["rate_long"] == 1.0, out

    # CONTRE-EXEMPLE APPARIÉ (classe E1) : deux groupes PEUPLÉS, même dose de rêve -> la garde doit
    # se taire et le contraste être MESURÉ. Sans cette moitié, une garde qui refuserait TOUJOURS
    # passerait le test ci-dessus.
    peuple = [{"age": 10, "total_dreams": 10}, {"age": 10, "total_dreams": 10},
              {"age": 30, "total_dreams": 15}, {"age": 30, "total_dreams": 15}]
    ok = distress_split(peuple, age_floor=10)
    assert ok["status"] == "OK" and ok["n_short"] == 2 and ok["n_long"] == 2, ok
    assert ok["delta"] == 0.5, ok       # 1.0 - 0.5


def test_distress_split_zero_dreams_is_INDETERMINE_but_one_rare_dreamer_is_a_MEASURE():
    """Garde d'AMPLITUDE. La grandeur de cette sonde est un TAUX DE RÊVE ; une cohorte entièrement
    porteuse de l'organe qui ne rêve pas UNE SEULE FOIS est une panne d'INTERVENTION, pas un fait sur
    la détresse. `0.0 - 0.0 = 0.0` publiait pourtant NEUTRE, lisible sur un record comme un négatif
    solide (n_favorable=0/12, sign_p=1.0)."""
    sans_reve = [{"age": 10, "total_dreams": 0}, {"age": 10, "total_dreams": 0},
                 {"age": 30, "total_dreams": 0}, {"age": 30, "total_dreams": 0}]
    out = distress_split(sans_reve, age_floor=10)
    assert out["n_short"] == 2 and out["n_long"] == 2, out      # le SPLIT, lui, est valide
    assert out["status"] == "INDETERMINE_AUCUN_REVE", out
    assert out["delta"] is None, out
    assert out["rate_short"] == 0.0 and out["rate_long"] == 0.0, (
        "les taux ONT été mesurés (et valent zéro) : c'est leur DIFFÉRENCE qui n'a pas d'objet")

    # CONTRE-EXEMPLE APPARIÉ (classe E1) : UN SEUL rêve dans toute la cohorte suffit à rendre la
    # mesure légitime -- la garde porte sur l'amplitude de l'INTERVENTION, pas sur le résultat.
    # ⚠️ Ce cas est aussi le LAVAGE PAR LA MÉDIANE d'EDR-094 : les deux taux MÉDIANS valent 0.000
    # alors que la cohorte a rêvé (le rêve est une conduite de MINORITÉ). C'est un défaut d'AGRÉGAT,
    # distinct de celui corrigé ici, et il reste OUVERT : le geler ici évite qu'on l'attrape par
    # accident en croyant corriger l'amplitude, et qu'on retire en silence le NEUTRE publié par
    # EDR-094 (docs/EDR/094_Dream_Distress_Median_Washout_Dreaming_Is_A_Minority_Behavior.md).
    rare = [{"age": 10, "total_dreams": 0}, {"age": 10, "total_dreams": 0},
            {"age": 10, "total_dreams": 5},
            {"age": 30, "total_dreams": 0}, {"age": 30, "total_dreams": 0},
            {"age": 30, "total_dreams": 0}]
    out_rare = distress_split(rare, age_floor=10)
    assert out_rare["status"] == "OK", out_rare
    assert out_rare["rate_short"] == 0.0 and out_rare["rate_long"] == 0.0, out_rare
    assert out_rare["delta"] == 0.0, out_rare


def test_distress_split_a_NON_FINITE_rate_is_never_stamped_OK():
    """4ᵉ défaut de la même famille, trouvé par le RÉFUTATEUR le 2026-09-08 — forme (b) du biais du
    dépôt (l'instrument SAIT et ne le dit pas), sur le chemin que ce module venait de durcir.

    Un `total_dreams` non fini chez l'appelant traversait `distress_split` et ressortait estampillé
    `OK` avec `delta = nan`. Deux conséquences MESURÉES en aval :
      * `run_distress` ne comptait AUCUNE raison (`raisons == {}`) alors que `distress_verdict`
        comptait bien un indéterminé — l'INDÉTERMINÉ devenait ANONYME, ce que le bloc `raisons`
        existe précisément pour empêcher ;
      * `Harness.save` archivait un `NaN` nu, qui n'est PAS du JSON valide. La propriété « JSON
        strict » que ce module revendique ne tenait que sur ses branches `None`."""
    NAN = float("nan")
    casse = [{"age": 10, "total_dreams": NAN}, {"age": 10, "total_dreams": 0},
             {"age": 30, "total_dreams": 15}, {"age": 30, "total_dreams": 15}]
    out = distress_split(casse, age_floor=10)
    assert out["status"] == "INDETERMINE_MESURE_NON_FINIE", out
    assert out["delta"] is None and out["rate_short"] is None, out
    assert out["rate_long"] == 0.5, "le côté RÉELLEMENT fini reste publié"
    assert out["n_short"] == 2 and out["n_long"] == 2, out       # le SPLIT, lui, est valide
    json.dumps(out, allow_nan=False)        # lève si un NaN a survécu -> l'archive resterait STRICTE

    # CONTRE-EXEMPLE APPARIÉ (classe E1) : la MÊME cohorte, le `nan` remplacé par un nombre FINI et
    # volontairement énorme. La garde doit se taire — elle porte sur la FINITUDE, pas sur l'amplitude.
    fini = [{"age": 10, "total_dreams": 1e6}, {"age": 10, "total_dreams": 0},
            {"age": 30, "total_dreams": 15}, {"age": 30, "total_dreams": 15}]
    ok = distress_split(fini, age_floor=10)
    assert ok["status"] == "OK" and ok["delta"] == 50000.0 - 0.5, ok

    # `_sans_mesure` couvre aussi ±inf : `inf > 0` est True EN SILENCE, donc un delta infini
    # ressortait en DETRESSE avec `median_delta=inf` publié à côté. Branche négative appariée : une
    # valeur finie ordinaire, y compris 0.0 et un très grand nombre, reste une MESURE.
    assert _sans_mesure(float("inf")) and _sans_mesure(float("-inf")) and _sans_mesure(NAN)
    assert _sans_mesure(None)
    assert not _sans_mesure(0.0) and not _sans_mesure(-3.5) and not _sans_mesure(1e308)
    assert distress_verdict([float("inf")] * 5)["verdict"] == "INDETERMINE_AUCUNE_MESURE"


from tools.dream_distress_probe import distress_verdict, _sans_mesure


def test_distress_verdict_three_cases():
    # court-vivants revent nettement plus, tous du meme cote -> DETRESSE (sign_p bas)
    assert distress_verdict([0.3, 0.4, 0.35, 0.3, 0.32])["verdict"] == "DETRESSE"
    # long-vivants revent plus -> BENEFIQUE
    assert distress_verdict([-0.3, -0.4, -0.35, -0.3, -0.32])["verdict"] == "BENEFIQUE"
    # mixte / centre sur 0 -> NEUTRE
    assert distress_verdict([0.1, -0.1, 0.05, -0.05])["verdict"] == "NEUTRE"
    # ⚠️ CORRIGÉ le 2026-09-08. Ce test EXIGEAIT que l'entrée VIDE rende "NEUTRE", c.-à-d. le verdict
    # de FOND « le rêve n'a pas d'effet », fabriqué depuis ZÉRO mesure — la forme (a) du biais
    # systématique du dépôt. L'instrument a été corrigé (`INDETERMINE_AUCUN_SEED`) et SON test est
    # resté sur l'ancien contrat, donc rouge, invisible (la CI ne lance pas ce fichier).
    assert distress_verdict([])["verdict"] == "INDETERMINE_AUCUN_SEED"
    # branche NÉGATIVE appariée : un zéro MESURÉ reste un verdict. C'est toute la différence achetée.
    assert distress_verdict([0.0, 0.0, 0.0, 0.0])["verdict"] == "NEUTRE"


def test_distress_verdict_reports_fields():
    v = distress_verdict([0.3, 0.4, 0.35, 0.3, 0.32])
    assert v["n_favorable"] == 5 and "sign_p" in v and v["median_delta"] > 0


def test_distress_verdict_zero_delta_removes_power():
    """Un delta nul est retiré du test de signe : k=4/n=4 -> sign_p=0.125 > 0.1 -> NEUTRE
    malgre une mediane positive (verrouille la frontiere 0.1 qui declenche la Phase 2)."""
    v = distress_verdict([0.3, 0.4, 0.35, 0.32, 0.0])
    assert v["median_delta"] > 0
    assert v["sign_p"] > 0.1
    assert v["verdict"] == "NEUTRE"


def test_distress_verdict_an_UNMEASURED_seed_never_becomes_a_zero():
    """Un seed dont le contraste n'a pas été mesuré (`delta is None`, cf. `distress_split`) n'est PAS
    un delta nul. L'agréger comme tel referait, un cran plus haut, le défaut corrigé en dessous.

    Trois réponses connues + le contre-exemple apparié :
      * TOUS indéterminés          -> INDETERMINE_AUCUNE_MESURE (aucune médiane, aucun sign_p) ;
      * PARTIELLEMENT indéterminés -> INDETERMINE_MESURES_PARTIELLES, avec le compte PUBLIÉ. L'unité
        de réplication est le SEED : laisser tomber en silence ceux qui n'ont rien rendu changerait n
        sans le dire, et ce sont justement les seeds éteints — corrélés au phénomène — qui
        disparaîtraient. La médiane des seeds mesurés reste lisible à côté, mais n'est plus un verdict.
      * `nan` (indétermination ACCIDENTELLE) est traité comme `None` : sans ça il traverserait les
        comparaisons EN SILENCE (`nan > 0` est False) et ressortirait en NEUTRE.
      * CONTRE-EXEMPLE APPARIÉ (classe E1) : la MÊME dose sans aucun trou rend bien DETRESSE."""
    tous = distress_verdict([None] * 5)
    assert tous["verdict"] == "INDETERMINE_AUCUNE_MESURE", tous
    assert tous["median_delta"] is None and tous["sign_p"] is None
    assert tous["n_indetermine"] == 5 and tous["n_mesurable"] == 0

    partiel = distress_verdict([0.5, 0.5, 0.5, 0.5, None])
    assert partiel["verdict"] == "INDETERMINE_MESURES_PARTIELLES", partiel
    assert partiel["n_mesurable"] == 4 and partiel["n_indetermine"] == 1
    assert partiel["median_delta"] == 0.5, "la mesure des seeds mesurés reste publiée"

    nan = distress_verdict([float("nan")] * 5)
    assert nan["verdict"] == "INDETERMINE_AUCUNE_MESURE", nan

    intact = distress_verdict([0.5] * 5)
    assert intact["verdict"] == "DETRESSE", intact
    assert intact["n_indetermine"] == 0 and intact["n_mesurable"] == 5


import json
import glob
import logging


def test_main_writes_provenance(tmp_path, monkeypatch, caplog):
    monkeypatch.chdir(tmp_path)
    caplog.set_level(logging.INFO, logger="AGIseed.DreamDistress")
    import tools.dream_distress_probe as dd
    monkeypatch.setattr(dd, "run_distress", lambda *a, **k: {
        "median_delta": 0.3, "n_favorable": 3, "sign_p": 0.05, "verdict": "DETRESSE",
        "per_seed": [{"seed": 0, "rate_short": 0.5, "rate_long": 0.2, "delta": 0.3,
                      "n_short": 5, "n_long": 5}],
        "config": {"target": "stoneage", "seeds": [0]}})
    monkeypatch.setattr(dd.async_logger, "start", lambda: None)
    monkeypatch.setattr(dd.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dd, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DD_SEEDS", "0")
    # main() pose AGISEED_QUIET_LOG=1 en dur -> monkeypatch POSSEDE la cle (restauree au teardown,
    # sinon fuite vers les autres tests de la session, cf. EDR 093).
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    result = dd.main()
    assert result["verdict"] == "DETRESSE"
    files = glob.glob(str(tmp_path / "results" / "dream_distress_*.json"))
    assert files, "provenance non écrite"
    with open(files[0], encoding="utf-8") as f:
        data = json.loads(f.read())
    assert data["data"]["verdict"] == "DETRESSE"
    assert "commit" in data and "git_dirty" in data
    # BRANCHE NÉGATIVE APPARIÉE du test ci-dessous : quand la mesure EXISTE, le log l'imprime bel et
    # bien formatée. Sans cette moitié, un `_f3` qui rendrait "None" pour tout passerait l'autre test.
    assert "median_delta=0.300" in caplog.text, caplog.text


def test_main_LOGS_and_ARCHIVES_an_INDETERMINATE_verdict_without_printing_a_zero(tmp_path,
                                                                                monkeypatch, caplog):
    """L'unique verdict d'INDÉTERMINATION de la chaîne doit pouvoir S'AFFICHER et S'ARCHIVER.

    Défaut historique : `main` formatait `median_delta=%.3f` / `sign_p=%.3f`, qui LÈVENT sur le
    `None` de ces branches — le seul verdict que la sonde produit quand elle n'a rien mesuré ne
    pouvait même pas être imprimé. Le correctif (`_f3`) était livré SANS test : mesuré par mutation,
    remettre `%.3f` dans `main` ne faisait rougir AUCUN test, alors que la cellule
    `main:affiche-un-verdict-d-indetermination` était DÉCLARÉE calibrée.

    Deux réponses connues : (a) `main` ne lève pas et le log dit `None`, jamais `0.000` — un `0.000`
    imprimé là serait un delta nul FABRIQUÉ, la forme (a) du biais du dépôt jusque dans le journal ;
    (b) l'archive reste du JSON STRICT (pas de `NaN`), donc relisible par n'importe quel parseur."""
    monkeypatch.chdir(tmp_path)
    import tools.dream_distress_probe as dd
    monkeypatch.setattr(dd, "run_distress", lambda *a, **k: {
        "median_delta": None, "n_favorable": 0, "sign_p": None, "n_mesurable": 0,
        "n_indetermine": 5, "verdict": "INDETERMINE_AUCUNE_MESURE",
        "raisons": {"INDETERMINE_AUCUN_REVE": 5},
        "per_seed": [{"seed": s, "rate_short": 0.0, "rate_long": 0.0, "delta": None,
                      "n_short": 2, "n_long": 2, "status": "INDETERMINE_AUCUN_REVE"}
                     for s in range(5)],
        "config": {"target": "stoneage", "seeds": [0, 1, 2, 3, 4]}})
    monkeypatch.setattr(dd.async_logger, "start", lambda: None)
    monkeypatch.setattr(dd.async_logger, "stop", lambda: None)
    monkeypatch.setattr(dd, "_acquire_shared_db", lambda: None)
    monkeypatch.setenv("DD_SEEDS", "0,1,2,3,4")
    monkeypatch.setenv("AGISEED_QUIET_LOG", "0")

    caplog.set_level(logging.INFO, logger="AGIseed.DreamDistress")
    result = dd.main()                       # levait TypeError avant `_f3`
    assert result["verdict"] == "INDETERMINE_AUCUNE_MESURE"

    # `caplog.messages` = le message FORMATE, sans le prefixe logger/fichier/ligne de `caplog.text`.
    ligne = [m for m in caplog.messages if m.startswith("VERDICT=")]
    assert ligne, caplog.messages
    assert "median_delta=None" in ligne[0] and "sign_p=None" in ligne[0], ligne[0]
    assert "0.000" not in ligne[0], (
        "un 0.000 imprime la ou rien n'a ete mesure : le delta nul FABRIQUE, dans le journal", ligne[0])
    assert "INDETERMINE_AUCUN_REVE" in ligne[0], ("la RAISON doit voyager avec l'indetermination",
                                                  ligne[0])

    files = glob.glob(str(tmp_path / "results" / "dream_distress_*.json"))
    assert files, "provenance non écrite"
    brut = open(files[0], encoding="utf-8").read()

    def _interdit(c):
        raise AssertionError(f"JSON NON STRICT : constante {c!r} dans l'archive")
    data = json.loads(brut, parse_constant=_interdit)
    assert data["data"]["verdict"] == "INDETERMINE_AUCUNE_MESURE"
    assert data["data"]["median_delta"] is None and data["data"]["per_seed"][0]["delta"] is None
