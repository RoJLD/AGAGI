"""Cliquet : le record MESURE-t-il la DV que sa règle scellée EXIGE ? (classe E11, occurrence 4)

Le sceau de `preregister.py` prouve que la RÈGLE n'a pas bougé ; il ne dit rien sur la FIDÉLITÉ de son
application. EDR-EVO-019 l'a démontré : règle « le plafond doit RÉDUIRE `|logit|` médian », record qui
substitue une réduction de FAN-IN — sceau intact, mot « logit » absent du record.

⚠️ Ces tests vérifient surtout que le cliquet **ÉCHOUE quand il le doit**. Un cliquet qui n'a jamais vu
un cas positif est une vérification vide (classe E4).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import tools.check_preregistration_applied as C  # noqa: E402


def _mk(tmp_path, rule, record_text, name="EVO-999"):
    pre = tmp_path / "preregistrations"; pre.mkdir(exist_ok=True)
    edr = tmp_path / "EDR"; edr.mkdir(exist_ok=True)
    (pre / f"{name}.json").write_text(json.dumps({"name": name, "rule": rule, "seal": "x"}),
                                      encoding="utf-8")
    (edr / f"{name}_Un_Record.md").write_text(record_text, encoding="utf-8")
    C._PREREG, C._EDR = str(pre), str(edr)
    return C.scan()


def test_substituted_dv_is_DETECTED(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELÉ — la configuration EXACTE d'EDR-EVO-019 avant correction.

    La règle exige `|logit|` médian ; le record ne parle que de fan-in. Le sceau serait intact et
    l'ancienne garde ne verrait rien."""
    rule = {"controle_de_manipulation_OBLIGATOIRE":
            "(b) le plafond doit REDUIRE |logit| median par rapport au bras volume-seul."}
    record = ("## Controles de manipulation\n\nLe plafond ramene le fan-in de 10.05 a 2.92. "
              "Les deux conditions exigees sont satisfaites.\n")
    problems = _mk(tmp_path, rule, record)
    assert problems, "la DV substituee doit etre DETECTEE — sinon le cliquet est une verification vide"
    assert "logit" in " ".join(problems[0][2]).lower()


def test_record_that_measures_the_sealed_dv_passes(tmp_path):
    """SPÉCIFICITÉ : un record qui mesure bien la grandeur scellée ne doit pas être signalé."""
    rule = {"controle_de_manipulation_OBLIGATOIRE": "le plafond doit REDUIRE |logit| median"}
    record = "Le |logit| median passe de 10.2 a 0.5 dans le bras traite.\n"
    assert _mk(tmp_path, rule, record) == []


def test_backticked_quantity_is_also_required(tmp_path):
    """Les grandeurs citees entre backticks comptent autant que les motifs |x|."""
    rule = {"dv_primaire": "taux de bascule de `measure_decision_saliency` sur la sous-tache la plus haute"}
    assert _mk(tmp_path, rule, "On rapporte le taux de lecteurs.\n"), "grandeur backtickee non exigee"
    assert _mk(tmp_path, rule, "measure_decision_saliency donne 0.982.\n") == []


def test_generic_tokens_do_not_create_false_positives(tmp_path):
    """La garde ne doit pas exiger des termes generiques (`raw`, `n`, `seed`) — sinon elle crie tout le
    temps et on cesse de la lire, ce qui la rend equivalente a une garde absente."""
    rule = {"dv_primaire": "le `raw` median par `seed`, sur `n` bras"}
    assert _mk(tmp_path, rule, "Resultats par bras.\n") == []


def test_repository_preregistrations_are_all_applied():
    """Cliquet sur le depot REEL : chaque regle scellee doit etre mesuree dans son record."""
    import importlib
    importlib.reload(C)
    problems = C.scan()
    assert not problems, f"DV scellees non mesurees : {problems}"


# ======================================================================================================
# 2026-09-02 — le cliquet SURDECLARAIT sa propre couverture.
#
# Il imprimait « OK : 23 regles scellees, chacune mesuree dans son record » alors que 8 sur 23 seulement
# etaient REELLEMENT inspectees. Un cliquet qui annonce 100 % quand il en fait 35 est un faux vert sur
# lui-meme -- et c'est la troisieme liste blanche silencieuse trouvee en deux jours (apres `_LIST_KEYS`
# du frontmatter et `_INSTRUMENT_PATTERNS` du nommage).
#
# ⚠️ La cause n'etait PAS les champs. Les elargir de 10 a 20 n'a recupere qu'UNE regle. Les 13 autres
# sont anterieures a la convention « backticker les grandeurs » : leurs clauses sont en prose
# (`dv_primaire` d'EVO-007 = « raw = succes/essais du champion »). Deviner des identifiants nus
# produirait des faux positifs -> on DECLARE ces regles non inspectables plutot que de les compter.
# ======================================================================================================

def test_the_ratchet_reports_its_REAL_coverage_not_the_total():
    """⚠️ La couverture annoncee doit etre celle qui est VERIFIEE, pas le nombre de fichiers presents."""
    import tools.check_preregistration_applied as C
    insp, sans_qty, sans_rec, total = C.couverture()
    assert insp + sans_qty + sans_rec == total, "la decomposition doit couvrir tout le corpus"
    assert insp < total, (
        "si toutes les regles devenaient inspectables, retirer les legataires de "
        "`_LEGATAIRES_SANS_BACKTICK` et resserrer ce test")


def test_a_NEW_rule_without_named_quantities_is_REFUSED():
    """⚠️ Cliquet AVANT : une regle scellee recente dont aucune grandeur n'est extractible n'est pas
    verifiable. La dette legataire est nommee ; les nouvelles doivent suivre la convention."""
    import tools.check_preregistration_applied as C
    assert C.nouvelles_sans_grandeur() == [], (
        f"regle(s) recente(s) sans grandeur backtickee : {C.nouvelles_sans_grandeur()}")


def test_the_legacy_declaration_is_STILL_REAL():
    """L'inverse : si une regle legataire recoit des backticks, la retirer de la dette. Une dette qui
    ne peut plus etre invalidee n'est plus une dette."""
    import json
    import os
    import tools.check_preregistration_applied as C
    resorbees = []
    for name in C._LEGATAIRES_SANS_BACKTICK:
        f = os.path.join(C._PREREG, name + ".json")
        if not os.path.exists(f):
            continue
        rule = json.load(open(f, encoding="utf-8")).get("rule", {})
        if C._quantities(rule):
            resorbees.append(name)
    assert not resorbees, f"{resorbees} nomme(nt) desormais des grandeurs -> retirer de la dette"


def test_family_with_backticked_bis_is_NOT_flagged(tmp_path):
    """Semantique de FAMILLE (2026-09-02) : une pre-inscription ne se corrige pas — l'amendement passe
    par -bis. Si l'original n'a pas de backticks mais que son -bis (markup-only) en a, la famille est
    verifiable : la flagger a jamais rendrait l'erreur INEPARABLE. Cas reel : S2-FLOOR-PRONOSTIC,
    mordu par ce cliquet le jour meme de son scellement."""
    import json
    pre = tmp_path / "preregistrations"; pre.mkdir()
    (pre / "EVO-998.json").write_text(json.dumps(
        {"name": "EVO-998", "rule": {"dv_primaire": "verdict de run_ablation_map par monde"}, "seal": "x"}),
        encoding="utf-8")
    (pre / "EVO-998-bis.json").write_text(json.dumps(
        {"name": "EVO-998-bis", "rule": {"dv_primaire": "verdict de `run_ablation_map` par monde",
                                         "amendement": "markup uniquement"}, "seal": "x"}),
        encoding="utf-8")
    C._PREREG = str(pre)
    assert C.nouvelles_sans_grandeur() == []


def test_family_without_any_backtick_STILL_fails(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELE de la semantique de famille : le cliquet doit encore pouvoir ECHOUER.
    Une famille (base + -bis) dont AUCUN membre n'a de grandeur extractible est flaggee — tous ses
    membres non legataires. Sans ce cas, l'elargissement famille serait un faux vert structurel."""
    import json
    pre = tmp_path / "preregistrations"; pre.mkdir()
    for n in ("EVO-998", "EVO-998-bis"):
        (pre / f"{n}.json").write_text(json.dumps(
            {"name": n, "rule": {"dv_primaire": "verdict par monde, sans grandeur nommee"}, "seal": "x"}),
            encoding="utf-8")
    C._PREREG = str(pre)
    assert sorted(C.nouvelles_sans_grandeur()) == ["EVO-998", "EVO-998-bis"]


# ======================================================================================================
# 2026-09-06 -- P2.28 : une FAMILLE passait TOUTES les portes en n'etant verifiee par AUCUNE.
#
# La semantique de famille (base + -bis) etait appliquee a « la regle NOMME-t-elle des grandeurs ? » mais
# PAS a « le record les MESURE-t-il ? ». Mesure sur DELAYED-COORD-LR-N12 : la base a 0 grandeur (scan la
# sautait), la -bis en a 7 mais son record `EDR-DELAYED-COORD_*` ne prefixe aucun des deux noms (scan la
# sautait aussi) -- alors que le record EXISTE et CITE `docs/preregistrations/DELAYED-COORD-LR-N12.json`.
# Correctif : scan/couverture jugent par famille (UNION des grandeurs, UNION des records) ; le record se
# rattache par DECLARATION (`record:`), par CITATION du chemin de la regle, puis par prefixe -- jamais
# par mention nue du nom.
# ======================================================================================================

def _fam(tmp_path, rules, records):
    """rules : {name: payload sans seal} ; records : {nom_de_fichier: texte}. Cumulatif sur tmp_path."""
    pre = tmp_path / "preregistrations"; pre.mkdir(exist_ok=True)
    edr = tmp_path / "EDR"; edr.mkdir(exist_ok=True)
    for name, payload in rules.items():
        (pre / f"{name}.json").write_text(json.dumps({"name": name, "seal": "x", **payload}),
                                          encoding="utf-8")
    for fn, text in records.items():
        (edr / fn).write_text(text, encoding="utf-8")
    C._PREREG, C._EDR = str(pre), str(edr)


_BASE_PROSE = {"rule": {"variable_dependante_scellee": "RETAIN_intact -- accuracy du bras RETAIN"}}
_BIS_BACKTICK = {"rule": {"dv_primaire": "`RETAIN_intact` appariee entre `lr=0.05` et `lr=0.002`"}}


def test_family_reached_through_a_CITING_record_is_INSPECTED_and_can_FAIL(tmp_path):
    """⚠️ CONTRE-EXEMPLE GELE de P2.28 (configuration exacte, noms compris) : base sans backtick, -bis
    avec grandeurs, record dont le NOM ne prefixe aucun membre mais qui CITE la regle. Avant : scan()
    rendait [] et couverture comptait 1 « sans grandeur » + 1 « sans record » -- verifiee par personne.
    Apres : la famille est inspectee sur l'UNION, et elle DOIT pouvoir echouer."""
    rec = "Regle scellee : docs/preregistrations/DELAYED-COORD-LR-N12.json. Verdict MONTEE_ETABLIE.\n"
    _fam(tmp_path, {"DELAYED-COORD-LR-N12": _BASE_PROSE, "DELAYED-COORD-LR-N12-bis": _BIS_BACKTICK},
         {"EDR-DELAYED-COORD_Un_Record.md": rec})
    problems = C.scan()
    assert problems and problems[0][0] == "DELAYED-COORD-LR-N12", problems
    assert "RETAIN_intact" in problems[0][2]
    assert C.couverture() == (1, 0, 0, 1)
    # le meme record, qui MESURE la grandeur : la famille passe
    _fam(tmp_path, {}, {"EDR-DELAYED-COORD_Un_Record.md": rec + "`RETAIN_intact` monte 12/12.\n"})
    assert C.scan() == []


def test_repository_DELAYED_COORD_family_is_now_ATTACHED_to_its_record():
    """Le cas MESURE de P2.28, sur le depot REEL : la famille est rattachee et inspectee, pas sautee."""
    import importlib
    importlib.reload(C)
    par_base = {base: (qty, recs) for base, _, qty, recs, _, _ in C._inspection()}
    qty, recs = par_base["DELAYED-COORD-LR-N12"]
    assert qty and any(os.path.basename(r).startswith("EDR-DELAYED-COORD_") for r in recs), recs
    assert not [p for p in C.scan() if p[0] == "DELAYED-COORD-LR-N12"]


def test_prefix_attached_rule_keeps_its_fate(tmp_path):
    """SPARES : une regle deja rattachee par PREFIXE ne change pas de sort -- detectee si la DV manque,
    epargnee si le record la mesure, comptee inspectee UNE fois."""
    rule = {"rule": {"controle_de_manipulation_OBLIGATOIRE": "le plafond doit REDUIRE |logit| median"}}
    _fam(tmp_path, {"EVO-999": rule}, {"EVO-999_Un_Record.md": "Le fan-in passe de 10 a 3.\n"})
    problems = C.scan()
    assert problems and problems[0][0] == "EVO-999" and "logit" in problems[0][2]
    assert C.couverture() == (1, 0, 0, 1)
    _fam(tmp_path, {}, {"EVO-999_Un_Record.md": "Le |logit| median passe de 10.2 a 0.5.\n"})
    assert C.scan() == [] and C.couverture() == (1, 0, 0, 1)


def test_a_level_of_a_quantity_is_not_a_quantity():
    """SPARES : `lr=0.002` nomme la grandeur `lr` a un NIVEAU. L'ancienne normalisation en faisait le
    token `lr0002`, introuvable dans tout record honnete -> DELAYED-COORD aurait ete flaggee A TORT le
    jour de son rattachement (mesure : missing=['lr0002', 'lr005'])."""
    assert C._quantities({"dv_primaire": "`RETAIN_intact` entre `lr=0.05` et `lr=0.002`"}) == {"RETAIN_intact"}


def test_a_bare_mention_of_the_name_does_NOT_attach_and_the_family_is_NAMED(tmp_path):
    """SCOPE : un record qui cite le nom en prose (« comme EVO-999 l'a montre ») ne mesure pas EVO-999.
    Seuls rattachent : `record:` declare, la citation `docs/preregistrations/<nom>.json`, le prefixe.
    Et la famille non rattachee est NOMMEE dans la sortie -- pas fondue dans un compteur."""
    _fam(tmp_path, {"EVO-999": _BIS_BACKTICK}, {"AUTRE_Record.md": "Comme EVO-999 l'a montre, rien.\n"})
    assert C.scan() == []
    assert C.couverture() == (0, 0, 1, 1)
    assert C.familles_sans_record() == ["EVO-999"]


def test_declared_record_key_attaches_BEFORE_any_naming_and_a_dangling_one_CRIES(tmp_path):
    """Regle du depot : declarer, pas deviner. `record:` au niveau du payload (HORS sceau) rattache un
    record au nom quelconque ; declare mais INTROUVABLE -> probleme, pas silence."""
    _fam(tmp_path, {"EVO-999": {**_BIS_BACKTICK, "record": "Nom_Quelconque.md"}},
         {"Nom_Quelconque.md": "`RETAIN_intact` mesuree.\n"})
    assert C.scan() == [] and C.couverture() == (1, 0, 0, 1)
    _fam(tmp_path, {"EVO-998": {**_BIS_BACKTICK, "record": "Introuvable.md"}}, {})
    problems = C.scan()
    assert any(p[0] == "EVO-998" and p[1] == "Introuvable.md" for p in problems), problems

def test_la_normalisation_est_SYMETRIQUE_regle_et_record(tmp_path, monkeypatch):
    """DÉFAUT RÉEL corrigé le 2026-09-07. Les grandeurs de la règle sont normalisées
    (`env.big_kills` -> `envbig_kills`, `W[4, o+8]` -> `W[4o8]`) mais le record était confronté en
    texte BRUT : un record écrivant honnêtement `env.big_kills` ne pouvait JAMAIS satisfaire le
    cliquet — le seul moyen de passer était d'y coller le token MUTILÉ, c.-à-d. de dégrader le record
    pour plaire à l'outil. Réponse connue : le record honnête doit PASSER."""
    import re
    txt = "Le record écrit `env.big_kills` et `W[4, o+8]` comme un humain les écrit."
    low, low_norm = txt.lower(), re.sub(r"[^A-Za-z0-9_\[\]]", "", txt).lower()
    for q in ("envbig_kills", "W[4o8]"):
        assert q.lower() not in low, "le pré-requis du test a disparu : la grandeur n'est plus mutilée"
        assert q.lower() in low_norm, f"{q} reste introuvable : la normalisation n'est pas symétrique"


def test_la_normalisation_symetrique_ne_rend_PAS_le_cliquet_INCREVABLE():
    """BRANCHE NÉGATIVE appariée : normaliser les deux côtés ne doit pas faire passer une grandeur
    RÉELLEMENT absente. Sans ce cas, le correctif serait un contrôle qui ne peut plus échouer (E1)."""
    import re
    txt = "Ce record ne parle que de la survie et du ratio r."
    low, low_norm = txt.lower(), re.sub(r"[^A-Za-z0-9_\[\]]", "", txt).lower()
    for q in ("envbig_kills", "throw_prey_hits", "W[4o8]"):
        assert q.lower() not in low and q.lower() not in low_norm
