"""Calibration de la PORTE du graphe AGI-Taxonomy — `tools/check_agi_taxonomy.validate_edge`.

Contre-exemple GELÉ (revue adversariale du 2026-09-01). L'ancienne règle (`check_agi_taxonomy.py`
avant durcissement) acceptait `functional_aliasing == 'pass'` SEUL et n'exigeait `specificity_control`
que dans la branche `'n/a'`. Une 3e arête aurait donc été gravée à un standard de preuve STRICTEMENT
INFÉRIEUR à celui des deux arêtes déjà gravées :

  - Le bras PRINCIPAL d'une arête de demande est arithmétiquement FORCÉ : une fois l'entrée nécessaire
    ablatée, l'agent ne peut pas dépasser 1/K, donc `X_DEMANDED` tombe mécaniquement dès que le bras
    intact est vivant. Ce bras ne peut PAS produire l'issue négative -> il ne prouve rien (motif du
    pré-vol : « un contrôle qui ne peut pas échouer ne prouve rien »).
  - Le seul bras dont l'issue négative est RÉELLEMENT atteignable est le contrôle de demande
    (`specificity_control` : NO-COORD pour language->perception, PRESENT pour memory->perception —
    même ablation, information redondante disponible ailleurs). Preuve directe que l'alternative
    existe : l'itération 1 de MEM-PERCEPTION a ÉCHOUÉ ce contrôle (ratio 4.329) et a dû être corrigée.

Ces tests sont PUREMENT NUMÉRIQUES (aucun entraînement, aucun monde, aucun bail `kuzu`) : ils testent
la LOGIQUE de la porte sur des arêtes synthétiques, plus la non-régression sur les arêtes RÉELLES
lues depuis `data/agi_taxonomy/demands.json`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.check_agi_taxonomy import validate_edge, validate_graph  # noqa: E402

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DATA = os.path.join(_ROOT, "data", "agi_taxonomy")
_IDS = {"perception", "memory", "language", "generalization"}
# Record réel : `validate_edge` vérifie son existence sur disque, une preuve fictive doit donc pointer
# un fichier qui existe pour que le test isole bien la règle visée (et pas la règle `record`).
_REAL_RECORD = "docs/EDR/S2-001_Within_Subject_Perception_Ablation_Is_The_Sound_Demand_Marker.md"


def _load(name):
    with open(os.path.join(_DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def _edge(**evidence_over):
    """Arête synthétique conforme sur TOUS les autres axes (verdict, n, record, ids). Chaque test
    n'écrase que le champ dont il éprouve la règle."""
    # ⚠️ 2026-09-08 : `coord_intact` + la declaration P2.15 font desormais partie du socle CONFORME.
    # Elles etaient absentes tant que les 2 aretes gravees etaient EXEMPTEES ; l'exemption a ete LEVEE
    # PAR LA MESURE (plafond d'un agent non entraine, au regime publie), donc plus aucune arete n'y
    # echappe. Un helper qui garderait l'ancien socle testerait un contrat qui n'existe plus.
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "record": _REAL_RECORD,
          "coord_intact": 0.6547, "emergence_bar": 0.2431, "incapable_ceiling": 0.2266,
          "ceiling_provenance": "plafond d un agent NON ENTRAINE au regime publie, MAX sur 12 seeds"}
    ev.update(evidence_over)
    return {"capability": "memory", "prerequisite": "perception", "strength": "hard", "evidence": ev}


# --------------------------------------------------------------------------------------------------
# 1. LE CONTRE-EXEMPLE GELÉ — le trou réel de la porte
# --------------------------------------------------------------------------------------------------

def test_gate_REFUSES_aliasing_pass_without_specificity_control():
    """⚠️ Le cas qui compte. C'est EXACTEMENT la configuration que l'ancienne règle acceptait
    (`check_agi_taxonomy.py:64-72` avant durcissement : branche `fa == 'pass'` -> `pass  # ok`), et
    donc exactement le standard inférieur qui aurait été appliqué à la 3e arête : garde d'aliasing
    verte, AUCUN contrôle de demande. Sans `specificity_control`, l'arête ne repose que sur son bras
    arithmétiquement forcé — une affirmation invérifiable, pas une mesure."""
    v = validate_edge(_edge(functional_aliasing="pass"), _IDS)
    assert any("specificity_control" in x for x in v), (
        "l'arête sans contrôle de demande DOIT être refusée, même avec functional_aliasing='pass'")


def test_gate_REFUSES_aliasing_pass_with_FAILED_specificity_control():
    """Variante mesurée du même trou : le contrôle a été LANCÉ et a ÉCHOUÉ (cas réel de l'itération 1
    de MEM-PERCEPTION). Un échec explicite ne doit pas être moins bloquant qu'une absence."""
    v = validate_edge(_edge(functional_aliasing="pass", specificity_control="fail"), _IDS)
    assert any("specificity_control" in x for x in v)


def test_gate_accepts_aliasing_pass_WITH_specificity_control():
    """Contrôle positif de la règle précédente : la porte n'est pas devenue un refus systématique."""
    assert validate_edge(_edge(functional_aliasing="pass", specificity_control="pass"), _IDS) == []


# --------------------------------------------------------------------------------------------------
# 2. `n/a` NE COUVRE QU'UNE ABLATION D'ENTRÉE
# --------------------------------------------------------------------------------------------------

def test_gate_REFUSES_na_aliasing_on_a_SUBSTRATE_ablation():
    """`functional_aliasing='n/a'` n'est légitime que pour une ablation d'ENTRÉE (rien n'est écrit
    dans le substrat, il n'y a pas de fuite à garder). Couper dans le SUBSTRAT peut dégrader du calcul
    hors-demande : la garde CALIB-ALIAS doit alors être mesurée `pass`, jamais déclarée sans objet."""
    e = _edge(functional_aliasing="n/a", specificity_control="pass", ablation_target="substrate")
    v = validate_edge(e, _IDS)
    assert any("functional_aliasing" in x and "substrate" in x for x in v)


def test_gate_accepts_a_well_formed_SUBSTRATE_edge():
    """Contrôle positif : une ablation de substrat correctement gardée (aliasing mesuré `pass` ET
    contrôle de demande `pass`) passe. La règle interdit le `n/a`, pas l'ablation de substrat."""
    e = _edge(functional_aliasing="pass", specificity_control="pass", ablation_target="substrate")
    assert validate_edge(e, _IDS) == []


def test_gate_accepts_na_aliasing_on_an_INPUT_ablation():
    """Le chemin des 2 arêtes gravées, rendu explicite."""
    e = _edge(functional_aliasing="n/a", specificity_control="pass", ablation_target="input")
    assert validate_edge(e, _IDS) == []


def test_absent_ablation_target_defaults_to_input():
    """Compatibilité légataire : `ablation_target` absent == 'input'. Les 2 arêtes déjà gravées ne
    portent pas le champ et ablatent bien l'entrée (cf. `tools/memory_perception_demand_probe.py:21`
    « ablation d'entrée, pas d'écriture substrat -> pas de fuite à garder »)."""
    assert validate_edge(_edge(functional_aliasing="n/a", specificity_control="pass"), _IDS) == []


def test_gate_REFUSES_an_unknown_ablation_target():
    """Un `ablation_target` inconnu ne doit pas silencieusement retomber sur le défaut permissif."""
    e = _edge(functional_aliasing="n/a", specificity_control="pass", ablation_target="ablatuff")
    v = validate_edge(e, _IDS)
    assert any("ablation_target" in x for x in v)


# --------------------------------------------------------------------------------------------------
# 3. NON-RÉGRESSION — les 2 arêtes RÉELLES survivent au durcissement
# --------------------------------------------------------------------------------------------------

def test_every_GRAVEN_edge_remains_valid_after_hardening():
    """Non-régression OBLIGATOIRE : durcir la porte ne doit invalider AUCUNE arête gravée.
    Les valeurs sont LUES sur disque, jamais recopiées — un changement de `demands.json` repasse ici.

    ⚠️ Le compte n'est PAS assené ici (il l'était : « exactement 2 »). L'ensemble ATTENDU est énuméré
    dans le test suivant, ce qui est strictement plus fort : un compte laisse passer une arête
    SUBSTITUÉE. On ne garde ici qu'un plancher, contre un `demands.json` tronqué ou vide."""
    demands = _load("demands.json")
    assert len(demands) >= 2, "graphe tronqué ou vide — la non-régression ne teste plus rien"
    for e in demands:
        lbl = f"{e['capability']}->{e['prerequisite']}"
        assert validate_edge(e, _IDS) == [], f"arête gravée invalidée par le durcissement : {lbl}"


def test_the_shipped_graph_still_validates_end_to_end():
    """Même non-régression au niveau graphe (nœuds + arêtes), comme le cliquet l'exécute."""
    assert validate_graph(_load("capabilities.json"), _load("demands.json")) == []


def test_the_REAL_edges_are_exactly_the_expected_ones():
    """Ancre la précondition vérifiée par la revue : chaque arête gravée porte DÉJÀ
    `specificity_control='pass'` — c'est pourquoi le durcissement est gratuit pour elles. Si cette
    assertion casse, la non-régression ci-dessus ne teste plus ce qu'elle prétend tester.

    ⚠️ L'ensemble est ÉNUMÉRÉ, jamais compté : un compte accepterait une arête substituée.
    ⚠️ Et `functional_aliasing` n'est plus figé à `'n/a'` — la 3ᵉ arête (2026-09-02) est la première
    par ablation de SUBSTRAT, donc `'pass'`. On assène l'INVARIANT de la porte (l'aliasing dépend de
    la cible d'ablation) et non la valeur littérale qui se trouvait valoir pour les deux premières :
    un littéral aurait obligé à ré-éditer ce test à chaque arête, et c'est précisément ce qui l'a
    laissé ROUGE à HEAD entre le 2026-09-02 et le 2026-09-07 (dette P2.30)."""
    seen = {(e["capability"], e["prerequisite"]): e["evidence"] for e in _load("demands.json")}
    assert set(seen) == {("language", "perception"), ("memory", "perception"), ("language", "memory")}
    for lbl, ev in seen.items():
        assert ev["ablation_verdict"] == "X_DEMANDED", lbl
        assert ev["n"] >= 12, lbl                      # garde d'évaporation de puissance
        assert ev["specificity_control"] == "pass", lbl  # le SEUL bras dont l'issue négative est atteignable
        cible = ev.get("ablation_target", "input")
        attendu = "n/a" if cible == "input" else "pass"
        assert ev["functional_aliasing"] == attendu, (
            f"{lbl} : ablation_target={cible!r} impose functional_aliasing={attendu!r}, "
            f"trouvé {ev['functional_aliasing']!r}")


# --------------------------------------------------------------------------------------------------
# 4. SPÉCIFICITÉ DE LA PORTE — le durcissement n'a pas avalé les autres règles
# --------------------------------------------------------------------------------------------------

def test_other_rules_still_fire_independently():
    """No-op EXACT sur les règles voisines : n_floor, verdict et record échouent toujours SEULS,
    sur une arête par ailleurs conforme à la nouvelle règle de spécificité."""
    ok = {"functional_aliasing": "pass", "specificity_control": "pass"}
    assert any("n=" in x for x in validate_edge(_edge(n=8, **ok), _IDS))
    assert any("X_DEMANDED" in x for x in validate_edge(_edge(ablation_verdict="INCONCLUSIVE", **ok), _IDS))
    assert any("record" in x for x in validate_edge(_edge(record="docs/EDR/NOPE.md", **ok), _IDS))
    assert any("functional_aliasing" in x for x in validate_edge(_edge(functional_aliasing="fail",
                                                                      specificity_control="pass"), _IDS))


# --------------------------------------------------------------------------------------------------
# M4 (brainstorm taxonomies, 2026-09-02) : la porte lit desormais le bras INTACT.
# La paire synthetique historique (memory->perception) est LEGATAIRE (_LEGATAIRES_SANS_COORD) --
# les cas ci-dessous utilisent une paire NON legataire pour exercer la regle.
# --------------------------------------------------------------------------------------------------

def _edge_nouvelle(**evidence_over):
    """Arete NON legataire (language->memory : la 3e arete attendue), conforme partout ailleurs."""
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "record": _REAL_RECORD,
          "specificity_control": "pass", "functional_aliasing": "pass",
          "ablation_target": "substrate", "coord_intact": 0.92, "emergence_bar": 0.55,
          # 2026-09-08 : `language->memory` n'est plus exemptee -- le socle CONFORME porte donc aussi
          # la declaration P2.15. Son plafond REEL a ete mesure (0.1859, agent non entraine, D=0).
          "incapable_ceiling": 0.1859,
          "ceiling_provenance": "plafond d un agent NON ENTRAINE au regime publie D=0, MAX 12 seeds"}
    ev.update(evidence_over)
    return {"capability": "language", "prerequisite": "memory", "strength": "hard", "evidence": ev}


def test_gate_REFUSES_new_edge_without_coord_intact():
    """⚠️ CONTRE-EXEMPLE GELE — le trou M4 : un bras intact AU PLANCHER passait la porte, car
    X_DEMANDED est arithmetiquement force des que l'able est plafonne au hasard. Sans coord_intact,
    l'arete peut mesurer la « demande » d'une competence qui n'a jamais emerge."""
    e = _edge_nouvelle(); del e["evidence"]["coord_intact"]; del e["evidence"]["emergence_bar"]
    v = validate_edge(e, _IDS)
    assert any("coord_intact" in x for x in v), "arete neuve sans bras intact declare : DOIT etre refusee"


def test_gate_REFUSES_intact_arm_below_emergence_bar():
    """Le cas qui motive M4 : intact SOUS la barre declaree -> la competence n'a pas emerge, la
    demande mesuree est celle d'une competence absente."""
    v = validate_edge(_edge_nouvelle(coord_intact=0.21, emergence_bar=0.55), _IDS)
    assert any("SOUS emergence_bar" in x for x in v)


def test_gate_accepts_new_edge_with_emerged_intact_arm():
    """Controle positif : une arete neuve COMPLETE (intact au-dessus de la barre) passe -- la porte
    n'est pas devenue un refus systematique."""
    assert validate_edge(_edge_nouvelle(), _IDS) == []


def test_the_legacy_exemption_is_LIFTED_by_MEASUREMENT():
    """⚠️ L'exemption legataire n'existe plus, et elle a ete levee PAR LA MESURE, pas par decret.

    Les 2 aretes gravees avant M4 etaient lisibles sans `coord_intact` ni barre : personne ne savait ce
    que leur barre de vitalite separait. Mesure du 2026-09-08, agent NON ENTRAINE (zero episode) au
    REGIME PUBLIE (flip_p=0.3), MAX sur 12 seeds : plafond 0.1836 (coord) et 0.2266 (delayed), contre
    des valeurs publiees de 0.3438 et 0.6547 -- des marges de 1.87x et 2.89x. Les deux aretes declarent
    donc desormais leur barre, DERIVEE de ce plafond.

    Une exemption qui survit a la mesure qui pourrait la lever devient une DECORATION : l'ensemble doit
    rester VIDE."""
    from tools.check_agi_taxonomy import _LEGATAIRES_SANS_COORD
    assert _LEGATAIRES_SANS_COORD == frozenset(), _LEGATAIRES_SANS_COORD
    # socle complet (le helper porte desormais la declaration P2.15) -> accepte
    assert validate_edge(_edge(functional_aliasing="pass", specificity_control="pass"), _IDS) == []
    # ...et une arete SANS `coord_intact` n'est plus exemptee, meme sur un label legataire
    e = _edge(functional_aliasing="pass", specificity_control="pass")
    del e["evidence"]["coord_intact"]
    assert any("coord_intact" in x for x in validate_edge(e, _IDS)), "plus AUCUNE arete n'est exemptee"


def test_the_REAL_graph_declares_a_MEASURED_bar_on_every_edge():
    """Ancrage sur le reel : les 3 aretes gravees portent une barre, et pour les 2 anciennes cette barre
    vient d'une mesure d'incapable au regime publie. Si quelqu'un retirait ces champs, l'arete
    redeviendrait ininterpretable et la porte le dirait."""
    import json
    import os

    from tools.check_agi_taxonomy import _DATA
    with open(os.path.join(_DATA, "demands.json"), encoding="utf-8") as fh:
        dem = json.load(fh)
    for e in dem:
        lbl = f"{e['capability']}->{e['prerequisite']}"
        ev = e["evidence"]
        assert isinstance(ev.get("coord_intact"), (int, float)), lbl
        assert isinstance(ev.get("emergence_bar"), (int, float)), lbl
        assert ev["coord_intact"] > ev["emergence_bar"], lbl
        # 2026-09-08 : plus AUCUNE exception -- les 3 aretes declarent leur plafond d'incapable.
        assert ev["emergence_bar"] > ev["incapable_ceiling"], lbl
        assert len(ev["ceiling_provenance"].strip()) >= 20, lbl
        assert ev["coord_intact"] / ev["incapable_ceiling"] > 1.5, (
            f"{lbl} : le bras intact doit dominer NETTEMENT le plafond de l'incapable "
            f"({ev['coord_intact']} / {ev['incapable_ceiling']})")


# --------------------------------------------------------------------------------------------------
# 4. P2.15 (2026-09-07) — LA BARRE DOIT SEPARER, pas seulement etre coherente
# --------------------------------------------------------------------------------------------------
# La porte lisait `emergence_bar` sans jamais demander ce qu'elle separe. Une arete pouvait declarer
# `emergence_bar: 0.3167` — la barre de vitalite historique du depot — et passer, alors qu'un substrat
# PROUVABLEMENT INCAPABLE de la tache la franchit deja : le bras intact aurait « emerge » sans savoir
# rien faire. C'est le defaut symetrique de M4 (qui, lui, verifiait que l'intact atteint la barre).

def _edge_hors_gel(**evidence_over):
    """Arete NON legataire ET hors du gel P2.15 — `_edge_nouvelle` construit `language->memory`, qui
    est justement l'arete gelee : la regle P2.15 n'y serait JAMAIS eprouvee. Piege reel, trouve en
    ecrivant ces tests."""
    ev = {"ablation_verdict": "X_DEMANDED", "ratio": 2.4, "n": 12, "record": _REAL_RECORD,
          "specificity_control": "pass", "functional_aliasing": "pass",
          "ablation_target": "substrate", "coord_intact": 0.92, "emergence_bar": 0.55,
          "incapable_ceiling": 0.3889,
          "ceiling_provenance": "forme close du substrat plain a H_in=0, mesuree avec controle positif apparie"}
    ev.update(evidence_over)
    return {"capability": "memory", "prerequisite": "language", "strength": "hard", "evidence": ev}


def test_gate_REFUSES_a_bar_that_separates_NOTHING():
    """⚠️ CONTRE-EXEMPLE GELE de P2.15 : la barre historique du depot, declaree sur une arete neuve.
    0.3167 est SOUS le plafond du substrat incapable -> la franchir n'etablit aucune capacite."""
    v = validate_edge(_edge_hors_gel(emergence_bar=0.3167, coord_intact=0.35), _IDS)
    assert any("NE SEPARE RIEN" in x for x in v), v


def test_gate_REFUSES_a_bar_declared_without_an_incapable_ceiling():
    """Sans plafond declare, la porte ne PEUT pas savoir si la barre separe. Elle refuse au lieu de
    deviner : deviner reviendrait a passer le niveau de CHANCE, ce qui EST l'erreur P2.15."""
    e = _edge_hors_gel(); del e["evidence"]["incapable_ceiling"]
    assert any("incapable_ceiling" in x for x in validate_edge(e, _IDS))


def test_gate_REFUSES_an_undeclared_provenance():
    """Un plafond sans provenance est invérifiable — rien ne le distingue d'un niveau de chance passe
    par reflexe. Meme regle que `demand_marker._degeneracy` : on fait DECLARER, on ne devine pas."""
    e = _edge_hors_gel(ceiling_provenance="1/K")     # trop court ET c'est justement l'erreur
    assert any("ceiling_provenance" in x for x in validate_edge(e, _IDS))


def test_gate_ACCEPTS_a_bar_above_the_incapable_ceiling():
    """POSITIF APPARIE — sans lui, une porte qui refuserait TOUTE arete passerait les trois tests
    ci-dessus. Barre 0.55 au-dessus du plafond 0.3889, provenance ecrite : acceptee."""
    assert validate_edge(_edge_hors_gel(), _IDS) == []


def test_NO_edge_escapes_the_proof_anymore():
    """⚠️ LES DEUX ENSEMBLES D'EXEMPTION SONT VIDES depuis le 2026-09-08, et ils l'ont ete PAR LA MESURE.

    Le gel de `language->memory` disait : « ni la forme close du plain ni le bras able (~1/K) ne
    fournissent le plafond ». C'etait vrai des deux candidats envisages, et faux de la QUESTION : le
    plafond pertinent est celui d'un agent qui n'a RIEN APPRIS, mesurable a COUT NUL (zero episode).
    Mesure au regime publie (D=0, K=6, bilineaire) : 0.1859 sur 12 seeds -- au-dessus du hasard 1/K,
    donc ce n'est pas le niveau de chance passe par reflexe.

    Une exemption qui survit a la mesure qui pourrait la lever est une DECORATION, et un cliquet qui
    decore ment sur sa couverture. Ce test interdit qu'elles reviennent en silence."""
    from tools.check_agi_taxonomy import _LEGATAIRES_SANS_COORD, _LEGATAIRES_SANS_PLAFOND
    assert _LEGATAIRES_SANS_COORD == frozenset(), _LEGATAIRES_SANS_COORD
    assert _LEGATAIRES_SANS_PLAFOND == frozenset(), _LEGATAIRES_SANS_PLAFOND
    # POSITIF APPARIE : la porte refuse toujours une arete sans plafond, sur n'importe quel label
    for e in (_edge_hors_gel(), _edge_nouvelle()):
        del e["evidence"]["incapable_ceiling"]
        assert any("incapable_ceiling" in x for x in validate_edge(e, _IDS)), (
            f"{e['capability']}->{e['prerequisite']} sans plafond doit etre REFUSEE")


def test_the_graven_graph_STILL_PASSES_the_hardened_gate():
    """Non-regression sur le REEL : les 3 aretes gravees passent la porte durcie. Si ce test tombe, la
    porte a rendu ININTERPRETABLE une arete deja publiee — et c'est un probleme de la PORTE."""
    import json
    import os
    from tools.check_agi_taxonomy import _DATA, validate_graph
    with open(os.path.join(_DATA, "capabilities.json"), encoding="utf-8") as fh:
        caps = json.load(fh)
    with open(os.path.join(_DATA, "demands.json"), encoding="utf-8") as fh:
        dem = json.load(fh)
    assert validate_graph(caps, dem) == []
