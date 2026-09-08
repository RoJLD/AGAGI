"""Calibration de `tools/s2_openloop_probe.py` — l'ORCHESTRATEUR de l'échelle S2-003 (intact ->
permuted -> noise -> zero), par INJECTION À DOSE CONNUE.

Deux défauts corrigés le 2026-09-08, tous deux de la forme #1 du dépôt (« une absence de mesure
produit une affirmation NÉGATIVE de fond ») :

* (a) SANS AMPLITUDE — hors du régime où `_floor_for` déclare un plancher MESURÉ, une échelle dont
  les 4 conditions ont une survie médiane NULLE rendait `ratio = 0/eps = 0.0` sur les 3 barreaux,
  donc `inverted`, donc ni `decoy` ni `collapse`, donc le verdict de FOND `MIXED`. Correctif :
  `floor=0.0` quand aucun plancher mesuré n'est applicable — 0.0 n'est pas un plancher importé d'un
  autre régime (garde E8), c'est la borne INFÉRIEURE du support de la métrique.
* (b) SOUS-PUISSANCE — l'agrégation lisait les booléens BRUTS `decoy`/`collapse`, vrais quel que soit
  `n`, donc le garde-fou `n_floor=12` d'`ablation_verdict` était INERTE : à K=3 ères les 3 barreaux
  rendaient `INCONCLUSIVE` et le monde recevait quand même SURVIVAL_NEUTRAL. Correctif : consommer
  `verdict` / `degenerate` / `n`, et propager INDETERMINE_UNDERPOWERED.

⚠️ CHAQUE comportement ajouté porte ici son cas NÉGATIF APPARIÉ (classe E1) : un refus qui ne sait
plus se taire est pire que le défaut qu'il corrige. Les paires sont explicitement nommées
`..._is_REFUSED` / `..._is_STILL_READ`.

Coût : ZÉRO monde construit. `run_condition` et `load_champion_genome` sont les deux seuls seams de
simulation ; `ablation_verdict` et `_floor_for` restent RÉELS — c'est justement la couche
« mesures -> affirmation » qu'on calibre.
"""
import io
import contextlib

import pytest


_GENOME = "GENOME-CHAMPION-FACTICE-S2OL"     # sentinelle : aucun HoF n'est lu


def _cellule(era):
    """Cellule factice portant les clés que `run_condition` rend (`era_survival` est la seule lue)."""
    era = [float(x) for x in era]
    return {"survival": era, "life_score": era, "era_survival": era, "era_life": era,
            "censored_frac": 0.0}


def _injecte(monkeypatch, table):
    """Impose une survie PAR ÈRE à chaque barreau : `table` = {"intact"|"permuted"|"noise"|"zero":
    [survies]}. Renvoie le module. Un barreau non prévu explose (le dispatch ne peut pas glisser)."""
    import tools.s2_openloop_probe as P

    def _run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400,
                       n_eras=1, config=None):
        cles = {None: "intact", P.PerceptionAblatedMamba: "permuted",
                P.NoiseObsMamba: "noise", P.ZeroObsMamba: "zero"}
        if batch_model_cls not in cles:          # pragma: no cover - un 5e barreau non prévu
            raise AssertionError(f"barreau inconnu : {batch_model_cls}")
        return _cellule(table[cles[batch_model_cls]])

    monkeypatch.setattr(P, "run_condition", _run_condition)
    monkeypatch.setattr(P, "load_champion_genome", lambda: _GENOME)
    return P


def _plate(K, intact=40.0, rung=39.0):
    """Échelle PLATE : ratio 40/39 = 1.026, dans [1/1.3, 1.3] -> les 3 barreaux sont des leurres."""
    return {"intact": [intact] * K, "permuted": [rung] * K, "noise": [rung] * K, "zero": [rung] * K}


# --- (a) AMPLITUDE -----------------------------------------------------------------------------
# Régime 13 agents / 200 ticks : `_floor_for` rend None (garde E8), donc AUCUN plancher mesuré ne
# peut fabriquer la dégénérescence — ce qui est refusé ci-dessous l'est par l'amplitude SEULE.

def test_a_ladder_WITHOUT_ANY_amplitude_is_REFUSED(monkeypatch):
    """Réponse connue : les 4 conditions à survie médiane 0 (aucun agent n'a vécu). Les bras ne sont
    PAS identiques point par point, donc l'autre entrée de `_degeneracy` ne mord pas : sans la
    déclaration `floor=0.0`, le monde recevait le verdict de FOND MIXED."""
    K = 12
    table = {"intact": [0.0] * K, "permuted": [0.0] * (K - 1) + [1.0],
             "noise": [0.0] * (K - 1) + [2.0], "zero": [0.0] * (K - 1) + [3.0]}
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (r["verdict"], r["intact_med"])
    for barreau in ("permuted", "noise", "zero"):
        assert r[barreau]["degenerate"] is True, barreau
        assert "PLANCHER" in (r[barreau]["why"] or ""), r[barreau]["why"]


def test_the_SMALLEST_NON_ZERO_amplitude_is_STILL_READ(monkeypatch):
    """⚠️ CAS NÉGATIF APPARIÉ du précédent (E1). MÊME forme, dose minimale au-dessus de zéro :
    intact médian 1.0. Un refus posé sur `med_i <= floor` avec floor > 0 (ou une garde « amplitude
    faible ») avalerait ce cas ; il doit rester LU et rendre le verdict de fond SURVIVAL_NEUTRAL.
    C'est ce test qui interdit que le correctif (a) devienne un refus increvable."""
    K = 12
    table = {"intact": [1.0] * K, "permuted": [1.0] * (K - 1) + [2.0],
             "noise": [1.0] * (K - 1) + [2.0], "zero": [1.0] * (K - 1) + [2.0]}
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["intact_med"] == 1.0
    assert r["verdict"] == "SURVIVAL_NEUTRAL", (r["verdict"], r["permuted"])
    assert all(r[b]["degenerate"] is False for b in ("permuted", "noise", "zero"))


def test_a_TINY_but_REAL_collapse_is_STILL_a_POSITIVE(monkeypatch):
    """⚠️ Deuxième cas négatif apparié : le correctif (a) ne doit pas non plus éteindre le POSITIF.
    Bras intact à 1.0 (minuscule mais NON nul), barreau `zero` à 0.0 -> ratio 1e9 >= 1.5 -> X_DEMANDED
    -> SURVIVAL_SENSITIVE. Sans ce cas, « tout est indéterminé » passerait pour un correctif."""
    K = 12
    table = {"intact": [1.0] * K, "permuted": [1.0] * (K - 1) + [2.0],
             "noise": [1.0] * (K - 1) + [2.0], "zero": [0.0] * K}
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["zero"]["verdict"] == "X_DEMANDED", r["zero"]
    assert r["verdict"] == "SURVIVAL_SENSITIVE", r["verdict"]


# --- (b) PUISSANCE -----------------------------------------------------------------------------

def test_an_UNDERPOWERED_ladder_is_REFUSED(monkeypatch):
    """Réponse connue : échelle PLATE (donc `decoy` BRUT vrai sur les 3 barreaux) mais K=3 ères. Les
    trois barreaux rendent `INCONCLUSIVE` ; le monde ne doit prononcer AUCUN verdict de fond."""
    K = 3
    P = _injecte(monkeypatch, _plate(K))
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert all(r[b]["decoy"] is True for b in ("permuted", "noise", "zero")), (
        "le booléen BRUT doit rester vrai : c'est bien lui que l'ancien code lisait")
    assert all(r[b]["verdict"] == "INCONCLUSIVE" for b in ("permuted", "noise", "zero")), r
    assert r["verdict"] == "INDETERMINE_UNDERPOWERED", r["verdict"]


def test_an_underpowered_COLLAPSE_is_ALSO_refused(monkeypatch):
    """Le garde-fou de puissance bloque les TROIS verdicts, pas seulement le nul : un effondrement
    massif (ratio 4.0) sur 3 ères n'établit pas davantage la sensibilité que la platitude n'établit
    la neutralité. Sans ce cas, le correctif (b) ne serait qu'un filtre sur le NÉGATIF."""
    K = 3
    table = _plate(K)
    table["zero"] = [10.0] * K
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["zero"]["collapse"] is True and r["zero"]["verdict"] == "INCONCLUSIVE"
    assert r["verdict"] == "INDETERMINE_UNDERPOWERED", r["verdict"]


def test_a_ladder_AT_the_declared_n_floor_is_STILL_READ(monkeypatch):
    """⚠️ CAS NÉGATIF APPARIÉ des deux précédents (E1), et PINCE la constante en forme close : à
    K = N_FLOOR - 1 le monde est refusé, à K = N_FLOOR il rend un verdict de fond. Les deux issues
    encadrent la valeur exactement -> `N_FLOOR` est bien le `n_floor` passé aux barreaux, et ne peut
    pas dériver en silence de celui d'`ablation_verdict`."""
    import tools.s2_openloop_probe as Pmod
    n_floor = Pmod.N_FLOOR

    P = _injecte(monkeypatch, _plate(n_floor - 1))
    juste_en_dessous = P.run_openloop_ladder(worlds=["soup"], K=n_floor - 1, num_agents=13,
                                             max_ticks=200)["soup"]
    assert juste_en_dessous["verdict"] == "INDETERMINE_UNDERPOWERED", juste_en_dessous["verdict"]

    P = _injecte(monkeypatch, _plate(n_floor))
    pile_au_seuil = P.run_openloop_ladder(worlds=["soup"], K=n_floor, num_agents=13,
                                          max_ticks=200)["soup"]
    assert pile_au_seuil["verdict"] == "SURVIVAL_NEUTRAL", pile_au_seuil["verdict"]
    assert all(pile_au_seuil[b]["verdict"] == "X_DECOY" for b in ("permuted", "noise", "zero"))


def test_MIXED_survives_the_switch_to_guarded_verdicts(monkeypatch):
    """NON-RÉGRESSION de la bascule « booléens bruts -> verdicts gardés » : la branche MIXED (au moins
    un barreau INVERSÉ, aucun effondrement) doit rester atteignable, sinon la bascule aurait
    transformé un verdict de fond en code mort. `noise` à 40/80 = 0.5 < 1/1.3."""
    K = 12
    table = _plate(K)
    table["noise"] = [80.0] * K
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["noise"]["verdict"] == "INCONCLUSIVE_INVERTED", r["noise"]
    assert r["verdict"] == "MIXED", r["verdict"]


# --- (a-bis) UNE CELLULE SANS AUCUNE ÈRE ---------------------------------------------------------

@pytest.mark.parametrize("bras", ["intact", "permuted", "noise", "zero"])
def test_an_arm_with_ZERO_era_RAISES(monkeypatch, bras):
    """Une cellule dont `era_survival` est VIDE n'est pas une survie nulle observée : c'est une
    absence de mesure. Côté `intact`, l'ancien `float(np.median(era)) if era else 0.0` fabriquait un
    `intact_med` de fond ; côté ABLATÉ c'est pire — `med_a = 0.0` donne un ratio géant, donc
    `collapse`, donc SURVIVAL_SENSITIVE (« la perception PORTE la survie ») tirée de RIEN. Les
    QUATRE bras sont couverts : le défaut n'est pas symétrique, seul l'intact était nommé."""
    K = 12
    table = _plate(K)
    table[bras] = []
    P = _injecte(monkeypatch, table)
    with pytest.raises(ValueError, match="AUCUNE ere"):
        P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)


def test_a_SINGLE_era_does_NOT_raise_but_is_REFUSED_as_underpowered(monkeypatch):
    """⚠️ CAS NÉGATIF APPARIÉ du précédent (E1) : la levée doit tenir à l'ABSENCE d'ère, pas à leur
    petit nombre. Une SEULE ère par bras est une mesure — pauvre, donc refusée pour SOUS-PUISSANCE
    (pas d'exception), et surtout PAS convertie en verdict de fond."""
    P = _injecte(monkeypatch, _plate(1))
    r = P.run_openloop_ladder(worlds=["soup"], K=1, num_agents=13, max_ticks=200)["soup"]
    assert r["intact_med"] == 40.0
    assert r["verdict"] == "INDETERMINE_UNDERPOWERED", r["verdict"]


# --- main() : ne pas refabriquer « aucun » depuis un indéterminé --------------------------------

def _rung(ratio):
    return {"ratio": ratio, "n": 12, "collapse": False, "decoy": True, "corroborant": None,
            "verdict": "X_DECOY", "degenerate": False, "why": None, "censored": False,
            "inverted": False}


def _monde(verdict):
    return {"intact_med": 40.0, "permuted": _rung(1.0), "noise": _rung(1.0), "zero": _rung(1.0),
            "verdict": verdict}


def _sortie_de_main(monkeypatch, mesures):
    import tools.s2_openloop_probe as P
    for var in ("S2OL_SEED", "S2OL_K", "S2OL_AGENTS", "S2OL_TICKS", "S2OL_WORLDS"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(P, "run_openloop_ladder", lambda *a, **kw: mesures)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        P.main()
    return buf.getvalue()


def test_main_does_NOT_turn_an_INDETERMINE_family_into_two_bare_aucun(monkeypatch):
    """Réponse connue : les 2 mondes mesurés sont INDÉTERMINÉS. Les deux listes de `main` sont donc
    vides — et `or 'aucun'` publiait « aucun » DEUX fois, c.-à-d. deux affirmations de FOND (« aucun
    monde n'est neutre », « aucun n'est sensible ») tirées de ZÉRO monde lisible."""
    sortie = _sortie_de_main(monkeypatch, {"soup": _monde("INDETERMINE_DEGENERATE"),
                                           "famine": _monde("INDETERMINE_UNDERPOWERED")})
    assert "AUCUN monde LISIBLE" in sortie, sortie
    assert "aucun PARMI 0 monde(s) LISIBLE(s) sur 2 mesuré(s)" in sortie, sortie
    assert "INDÉTERMINÉS" in sortie and "soup" in sortie and "famine" in sortie
    assert "-> Rédiger EDR-S2-003" not in sortie, "un EDR ne se rédige pas sur zéro monde lisible"


def test_main_STILL_reports_a_readable_family_normally(monkeypatch):
    """⚠️ CAS NÉGATIF APPARIÉ (E1) : sur une famille LISIBLE, `main` doit continuer à nommer les
    mondes, à ne PAS crier à l'illisibilité, et à inviter à rédiger l'EDR. Sans ce cas, l'avertissement
    ajouté ci-dessus pourrait être inconditionnel — un cri qui ne sait plus se taire."""
    sortie = _sortie_de_main(monkeypatch, {"soup": _monde("SURVIVAL_NEUTRAL"),
                                           "famine": _monde("SURVIVAL_SENSITIVE")})
    assert "AUCUN monde LISIBLE" not in sortie, sortie
    assert "INDÉTERMINÉS" not in sortie, sortie
    assert "['soup']" in sortie and "['famine']" in sortie, sortie
    assert "-> Rédiger EDR-S2-003" in sortie


def test_main_counts_the_READABLE_worlds_when_only_SOME_are_indetermined(monkeypatch):
    """Famille MIXTE : 1 lisible (sensible) + 1 indéterminé. « aucun » doit alors dire de combien de
    mondes LISIBLES il parle (1 sur 2) — un « aucun » sans dénominateur reste une affirmation de fond
    dont on ne peut pas savoir si elle porte sur 1 monde ou sur 0."""
    sortie = _sortie_de_main(monkeypatch, {"soup": _monde("SURVIVAL_SENSITIVE"),
                                           "famine": _monde("INDETERMINE_DEGENERATE")})
    assert "aucun PARMI 1 monde(s) LISIBLE(s) sur 2 mesuré(s)" in sortie, sortie
    assert "['soup']" in sortie
    assert "INDÉTERMINÉS" in sortie and "famine" in sortie
    assert "-> Rédiger EDR-S2-003" in sortie


# --- AJOUTS DE LA REVUE ADVERSARIALE (2026-09-08) ------------------------------------------------
# Trois trous trouvés par TEST DE MUTATION : on casse à la main, dans une copie EN MÉMOIRE du module,
# chaque comportement que le correctif dit avoir posé, et on regarde si un test rougit. Trois
# mutations laissaient ce fichier ENTIÈREMENT VERT — donc trois gardes décoratives (classe E1) :
#   M7  le plancher MESURÉ n'est plus lu du tout (_floor_for court-circuité)   : 15 passed
#   M11 le n_floor explicite retiré des trois appels au marqueur              : 15 passed
#   M6b le plancher de PUISSANCE divisé par deux (12 -> 6)                    : 15 passed
# Chacune des fonctions ci-dessous est écrite CONTRE une de ces mutations, et chaque garde nouvelle
# porte son cas négatif apparié.


def test_the_MEASURED_floor_still_WINS_over_the_declared_zero(monkeypatch):
    """Le correctif (a) déclare un plancher 0.0 UNIQUEMENT là où `_floor_for` ne rend rien. Ce
    « uniquement » n'était testé par AUCUN cas de ce fichier : les 15 tests précédents tournent tous
    à 13 agents, c.-à-d. HORS du régime de mesure, donc le plancher MESURÉ n'y est jamais exercé —
    le supprimer complètement les laissait tous verts (mutation M7).

    Réponse connue : `soup` au régime GRAVÉ (12 agents / 200 ticks) a un plancher no-perception
    MESURÉ de 32.0. Intact à 20.0 (sous le plancher) avec `zero` à 5.0 -> ratio 4.0, donc `collapse` :
    sans la priorité du plancher mesuré, l'instrument publierait le POSITIF SURVIVAL_SENSITIVE depuis
    un bras qui n'avait pas d'amplitude. Le 0.0 du correctif (a) ne l'attraperait PAS (20.0 > 0)."""
    K = 12
    table = {"intact": [20.0] * K, "permuted": [19.0] * K, "noise": [19.0] * K, "zero": [5.0] * K}
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=12, max_ticks=200)["soup"]
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (r["verdict"], r["zero"])
    assert r["zero"]["collapse"] is True, "le collapse BRUT doit rester vrai : c'est lui qu'on refuse"
    assert "32" in (r["zero"]["why"] or ""), (
        "le refus doit citer le plancher MESURÉ (32.0), pas le 0.0 déclaré par défaut : "
        "why={!r}".format(r["zero"]["why"]))


def test_a_ladder_ABOVE_the_measured_floor_is_STILL_READ(monkeypatch):
    """CAS NÉGATIF APPARIÉ du précédent (E1) : MÊME régime, MÊME plancher mesuré (32.0), dose
    au-DESSUS (intact 40.0). Le plancher doit alors se taire et l'échelle rendre son verdict de fond.
    Sans ce cas, « refuser tout ce qui touche au régime 12/200 » passerait pour un correctif."""
    K = 12
    P = _injecte(monkeypatch, _plate(K, intact=40.0, rung=39.0))
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=12, max_ticks=200)["soup"]
    assert r["verdict"] == "SURVIVAL_NEUTRAL", (r["verdict"], r["permuted"])
    assert all(r[b]["degenerate"] is False for b in ("permuted", "noise", "zero"))


def test_the_THREE_rungs_receive_the_SAME_n_floor_the_aggregation_reads(monkeypatch):
    """Le correctif (b) affirme que l'agrégation et les barreaux « ne peuvent pas dériver l'une de
    l'autre » parce que c'est la MÊME constante qui circule. Mesuré : c'est FAUX tant que rien ne
    vérifie le passage — retirer les trois n_floor explicites laissait la suite verte (mutation M11),
    parce que le défaut du marqueur vaut lui aussi 12 AUJOURD'HUI. Le jour où l'un des deux bouge, la
    divergence est SILENCIEUSE et rejoue exactement le défaut (b) : mesuré en les faisant diverger
    (agrégation 6 / barreaux 12), une échelle PLATE à K=8 dont les TROIS barreaux disent
    `INCONCLUSIVE` ressort en `MIXED` — un verdict de FOND sur une échelle sous-puissante.

    On espionne donc le passage lui-même. Le vrai `ablation_verdict` reste appelé : c'est un espion,
    pas un bouchon, donc le test ne peut pas rendre l'instrument aveugle."""
    import tools.demand_marker as M
    vus = []

    def _espion(intact, ablated, **kw):
        vus.append(kw.get("n_floor", "ABSENT"))
        return M.ablation_verdict(intact, ablated, **kw)

    K = 12
    P = _injecte(monkeypatch, _plate(K))
    monkeypatch.setattr(P, "ablation_verdict", _espion)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert vus == [P.N_FLOOR] * 3, (
        "les barreaux n'ont pas tous recu EXPLICITEMENT le n_floor que l'agregation lit : "
        "{}".format(vus))
    assert r["verdict"] == "SURVIVAL_NEUTRAL", "l'espion ne doit rien changer au verdict"


def test_N_FLOOR_is_never_BELOW_the_declared_power_floor_of_the_marker():
    """La « pince » du correctif (b) est RELATIVE : ses deux bornes sont K = N_FLOOR-1 et K = N_FLOOR,
    donc elles suivent la constante partout où elle va. Mesuré : N_FLOOR = 6 (passé aux barreaux, donc
    cohérent) laisse les 15 tests VERTS — l'instrument prononcerait alors SURVIVAL_NEUTRAL sur 6 ères,
    la moitié du plancher de puissance du dépôt (`ablation_verdict` : « aucun verdict SOUS n<12 — les
    petits n s'évaporent dans les deux sens »). On épingle donc la VALEUR, pas seulement la cohérence,
    et par le DÉFAUT DÉCLARÉ du marqueur plutôt que par un nombre recopié.

    Sens de l'inégalité : monter le plancher est CONSERVATEUR (moins de verdicts de fond) et reste
    permis ; le baisser est la seule direction dangereuse, et c'est celle qui rougit."""
    import inspect
    import tools.s2_openloop_probe as P
    from tools.demand_marker import ablation_verdict

    declare = inspect.signature(ablation_verdict).parameters["n_floor"].default
    assert declare == 12, "le plancher de puissance du depot a bouge ({}) : re-decider ici".format(declare)
    assert P.N_FLOOR >= declare, (
        "N_FLOOR={} est SOUS le plancher de puissance declare du marqueur ({}) : l'echelle "
        "prononcerait un verdict de fond sur un n que le marqueur refuse".format(P.N_FLOOR, declare))


# --- (a-ter) UNE ÈRE NON FINIE : la deuxième porte de l'« absence de mesure » ---------------------

@pytest.mark.parametrize("bras", ["intact", "permuted", "noise", "zero"])
@pytest.mark.parametrize("dose", [float("nan"), float("inf"), float("-inf")])
def test_a_NON_FINITE_era_RAISES(monkeypatch, bras, dose):
    """`_eras` refusait l'ère ABSENTE mais laissait passer l'ère CORROMPUE. Réponses connues mesurées
    AVANT ce correctif (K=12, 13 agents) : intact = 11 ères à 40 + une à nan -> SURVIVAL_NEUTRAL, avec
    `intact_med` PUBLIÉ à nan alors que le ratio, lui, était calculé sur 40.0 (`statistics.median`
    contre `np.median`) — le nombre publié n'était même pas la grandeur qui a agi ; intact tout-nan
    -> MIXED ; intact à +inf -> SURVIVAL_SENSITIVE, le POSITIF fabriqué depuis une non-mesure."""
    K = 12
    table = _plate(K)
    table[bras] = [40.0] * (K - 1) + [dose]
    P = _injecte(monkeypatch, table)
    with pytest.raises(ValueError, match="NON FINIE"):
        P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)


def test_a_ZERO_era_is_a_MEASURE_and_does_NOT_raise(monkeypatch):
    """CAS NÉGATIF APPARIÉ du précédent (E1), et c'est LA distinction que tout ce fichier défend :
    0.0 est une survie OBSERVÉE (l'agent est mort au tick 0), pas une absence de mesure. Elle ne doit
    donc PAS lever — elle doit être LUE, puis refusée par l'amplitude, en INDETERMINE_DEGENERATE. Une
    garde écrite `if not all(vals)` au lieu de `math.isfinite` avalerait exactement ce cas."""
    K = 12
    table = {"intact": [0.0] * K, "permuted": [0.0] * (K - 1) + [1.0],
             "noise": [0.0] * (K - 1) + [2.0], "zero": [0.0] * (K - 1) + [3.0]}
    P = _injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["verdict"] == "INDETERMINE_DEGENERATE", r["verdict"]
    assert r["intact_med"] == 0.0
