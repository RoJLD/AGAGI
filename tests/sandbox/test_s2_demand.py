# tests/sandbox/test_s2_demand.py
import numpy as np
from src.environments.config import WorldConfig
from src.worlds.world_1_stoneage import Biosphere3D
from src.agents.baseline_models import RandomActionBatchModel
from tools.s2_demand import run_condition


def test_run_condition_returns_individual_survival():
    cfg = WorldConfig()
    out = run_condition(Biosphere3D, RandomActionBatchModel, genome=None,
                        seed=2026, num_agents=4, max_ticks=8, n_eras=2)
    assert "survival" in out and "life_score" in out
    assert len(out["survival"]) >= 4 * 2          # un âge PAR agent PAR ère (pas l'extinction-cohorte)
    assert all(s >= 0 for s in out["survival"])
    assert "censored_frac" in out


def test_run_condition_is_reproducible():
    cfg = WorldConfig()
    a = run_condition(Biosphere3D, RandomActionBatchModel, None, seed=7, num_agents=3, max_ticks=6, n_eras=2)
    b = run_condition(Biosphere3D, RandomActionBatchModel, None, seed=7, num_agents=3, max_ticks=6, n_eras=2)
    assert a["survival"] == b["survival"]


from tools.s2_demand import load_champion_genome, CONDITIONS


def test_conditions_cover_the_ladder():
    keys = set(CONDITIONS)
    assert {"champion", "random_action", "random_genome", "reflex_naive", "reflex_prudent"} <= keys


def test_load_champion_raises_on_empty_hof(monkeypatch):
    import tools.s2_demand as s2
    monkeypatch.setattr(s2, "load_hall_of_fame", lambda: (2, []))
    try:
        load_champion_genome()
        assert False, "doit lever si HoF vide"
    except RuntimeError:
        pass


from tools.s2_demand import required_k


def test_required_k_floor_is_12():
    # effet énorme, variance faible -> K calculé petit, mais plancher = 12 (réf EDR 087)
    assert required_k(mean_diff=100.0, std_diff=5.0) == 12


def test_required_k_grows_with_noise():
    k_low = required_k(mean_diff=10.0, std_diff=5.0)
    k_high = required_k(mean_diff=10.0, std_diff=40.0)
    assert k_high > k_low >= 12


from tools.s2_demand import run_s2


def test_run_s2_smoke_one_world(monkeypatch):
    # Smoke : 1 monde, K=2, peu d'agents/ticks -> structure du rapport correcte, sans crash.
    import tools.s2_demand as s2
    monkeypatch.setattr(s2, "load_champion_genome", lambda: __import__(
        "src.agents.mamba_agent", fromlist=["MambaAgent"]).MambaAgent().genome)
    rep = run_s2(worlds=["stoneage"], seed=2026, K=2, num_agents=3, max_ticks=6, with_db=False)
    assert "stoneage" in rep["worlds"]
    w = rep["worlds"]["stoneage"]
    assert "verdict" in w and "survival" in w
    assert rep["seed"] == 2026 and "commit" in rep
    # Câblage addendum 2026-06-30 (EDR 124) : le verdict est porté par la SURVIE, pas life_score
    assert w["coherence_basis"] == "survival"          # verdict_from_survival_cmps, pas s2_verdict
    assert "life_p" in w                               # life_score conservé en corroborant non-bloquant
    assert "coherence_ok_lifescore" in w              # trace de ce qu'aurait tranché l'ancien gate
    assert w["verdict"] in {"EXIGE", "AMBIGU", "ANTI-CORRELE", "VOID"}


# =====================================================================================================
# CALIBRATION — le RÉGIME ILLISIBLE propagé par `run_s2` (défaut corrigé le 2026-09-08, classe E3).
#
# `s2_verdict` pose sa garde de dégénérescence AVANT tout le reste et rend alors un dict SANS clé
# 'survival' ; `run_s2` faisait `verdict_from_survival_cmps(v["survival"])` inconditionnellement ->
# KeyError, et la grille S2 entière s'arrêtait sur une trace de clé au lieu de rapporter
# INCONCLUSIVE_DEGENERATE pour CE monde et de continuer les autres.
#
# Technique : INJECTION À DOSE CONNUE (aucun monde n'est construit, aucune simulation, coût nul) —
# on remplace, DANS le module, les trois seuls seams qui touchent le monde ou le disque.
#
# ⚠️ CHAQUE comportement ajouté est apparié à son cas NÉGATIF (classe E1) : sans lui, un `run_s2` qui
# rendrait INCONCLUSIVE_DEGENERATE QUOI QU'IL ARRIVE passerait tous ces tests. Les paires sont
# construites en ne changeant QUE la dose, jamais le câblage.
# =====================================================================================================
import pytest


class _HarnaisFactice:
    """`run_s2` s'exécute DANS un `with Harness(...)` et appelle `h.save(report)` : le vrai ouvre le
    logger async / KuzuDB et ÉCRIT dans l'arbre. On l'injecte, et on garde les rapports sauvés."""

    saves = []

    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def save(self, report):
        _HarnaisFactice.saves.append(report)


def _cellule(niveau, K=12, etale=2.0):
    """Cellule factice de `run_condition`, portant TOUTES les clés que l'aval lit : `survival` /
    `life_score` (individus poolés -> Cliff δ) et `era_survival` / `era_life` (une valeur PAR ÈRE ->
    l'appariement seed-à-seed du Wilcoxon, unité de réplication du dépôt). Survie ÉTALÉE de ±`etale`
    autour de `niveau` -> le régime est LISIBLE (c'est le cas négatif de la dégénérescence)."""
    m = K
    return {"survival": [float(niveau - etale + (2.0 * etale) * i / (m - 1)) for i in range(m)],
            "life_score": [float(niveau / 10.0 - 0.2 + 0.4 * i / (m - 1)) for i in range(m)],
            "era_survival": [float(niveau + ((i % 3) - 1)) for i in range(K)],
            "era_life": [float(niveau / 10.0 + 0.1 * ((i % 3) - 1)) for i in range(K)],
            "censored_frac": 0.0}


def _cellule_plate(niveau, K=12):
    """Cellule CONSTANTE : tout le monde meurt (ou est censuré) au MÊME tick. C'est le régime mesuré
    le 2026-09-01 où Cliff δ vaut ±1 MÉCANIQUEMENT — la dégénérescence que la garde E3 détecte."""
    return {"survival": [float(niveau)] * K, "life_score": [1.0] * K,
            "era_survival": [float(niveau)] * K, "era_life": [1.0] * K, "censored_frac": 0.0}


_CELLULE_VIDE = {"survival": [], "life_score": [], "era_survival": [], "era_life": [],
                 "censored_frac": 0.0}          # extinction totale : AUCUN individu mesuré


def _grille(champion, base):
    """Les 6 cellules d'UN monde (les 6 clés de CONDITIONS) : le champion, et `base` pour les 5 autres.
    Aucune condition ne peut devenir un `None` silencieux."""
    return {"champion": champion, "random_action": base, "random_genome": base,
            "reflex_naive": base, "reflex_prudent": base, "champion_obs_ablated": base}


def _injecte(monkeypatch, grilles):
    """Remplace dans `tools.s2_demand` : `run_condition` (rend la cellule imposée, identifiée par
    (batch_model_cls, genome is None) via l'inverse de CONDITIONS), `load_champion_genome`,
    `Harness` et `_git_short_commit`. `pilot_required_k` est INTERDIT (tous ces tests passent K)."""
    import tools.s2_demand as S
    inverse = {(spec["batch_model_cls"], spec["fresh_genome"]): nom
               for nom, spec in S.CONDITIONS.items()}
    assert len(inverse) == len(S.CONDITIONS), "deux conditions indiscernables : injection ambigue"
    monde_de = {S.WORLDS[w]: w for w in grilles}

    def _faux_run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20,
                            max_ticks=400, n_eras=1, config=None):
        return grilles[monde_de[world_cls]][inverse[(batch_model_cls, genome is None)]]

    def _pilote_interdit(*a, **kw):
        raise AssertionError("pilot_required_k appele alors que K est FOURNI (branche exclusive)")

    del _HarnaisFactice.saves[:]
    monkeypatch.setattr(S, "run_condition", _faux_run_condition)
    monkeypatch.setattr(S, "load_champion_genome", lambda: "GENOME-FACTICE")
    monkeypatch.setattr(S, "_git_short_commit", lambda: "s2cal")
    monkeypatch.setattr(S, "Harness", _HarnaisFactice)
    monkeypatch.setattr(S, "pilot_required_k", _pilote_interdit)
    return S


def test_run_s2_PROPAGE_INCONCLUSIVE_DEGENERATE_quand_les_deux_bras_sont_constants(monkeypatch):
    """Réponse connue : tout le monde meurt au même tick (champion 3, baselines 2, variance NULLE des
    DEUX côtés). Attendu : INCONCLUSIVE_DEGENERATE porteur de sa RAISON, et RIEN de fabriqué —
    ni p_monde, ni Cliff, ni life_p (une absence de mesure ne doit pas devenir une affirmation).

    NÉGATIF APPARIÉ (E1) : le MÊME câblage, seule la dose change — le champion reçoit une étendue
    (le régime redevient lisible). Le verdict doit alors être un vrai verdict AVEC p_monde. Sans ce
    second bloc, un `run_s2` qui rendrait INCONCLUSIVE_DEGENERATE en toute circonstance passerait."""
    _injecte(monkeypatch, {"soup": _grille(_cellule_plate(3), _cellule_plate(2))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "INCONCLUSIVE_DEGENERATE", w
    assert w["degenerate"] is True and "constants" in w["why"], w
    for fabrique in ("p_monde", "p_monde_holm", "cliff", "life_p", "survival"):
        assert fabrique not in w, f"{fabrique} FABRIQUE depuis un regime illisible : {w}"

    # NÉGATIF : même grille, champion étalé -> régime lisible -> le verdict revient.
    _injecte(monkeypatch, {"soup": _grille(_cellule(3.0, etale=1.0), _cellule_plate(2))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] != "INCONCLUSIVE_DEGENERATE" and "degenerate" not in w, w
    assert w["p_monde"] is not None and w["verdict"] in {"EXIGE", "AMBIGU", "VOID"}, w


def test_run_s2_PROPAGE_INCONCLUSIVE_DEGENERATE_sur_une_cohorte_champion_VIDE(monkeypatch):
    """Seconde porte d'entrée du MÊME défaut : extinction totale -> la cellule champion ne contient
    AUCUN individu. La garde d'ARGUMENTS posée en tête de `run_s2` ne couvre PAS ce cas (elle refuse
    `num_agents<=0` À L'APPEL, pas une cohorte vide MESURÉE) : c'est bien la couche d'agrégation qui
    doit rendre l'indéterminé.

    NÉGATIF APPARIÉ (E1) : la MÊME grille avec une cohorte champion NON vide rend EXIGE."""
    _injecte(monkeypatch, {"soup": _grille(_CELLULE_VIDE, _cellule(20.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "INCONCLUSIVE_DEGENERATE", w
    assert "VIDE" in w["why"], w
    assert "p_monde" not in w and "survival" not in w, w

    # NÉGATIF : cohorte champion remplie -> plus rien de dégénéré.
    _injecte(monkeypatch, {"soup": _grille(_cellule(100.0), _cellule(20.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "EXIGE" and "degenerate" not in w, w


def test_run_s2_CONTINUE_la_grille_apres_un_monde_degenere(monkeypatch):
    """LE comportement que le KeyError détruisait : un monde illisible ne doit pas emporter la grille.
    Réponse connue : `soup` dégénéré, `famine` à dose forte. Attendu : soup indéterminé, famine MESURÉ
    et tranché EXIGE, et le rapport RENDU est bien celui qui a été ARCHIVÉ.

    NÉGATIF APPARIÉ (E1) : les deux mondes à dose forte -> AUCUN indéterminé (le mécanisme sait ne
    pas se déclencher), et les deux sont tranchés."""
    _injecte(monkeypatch, {"soup": _grille(_cellule_plate(3), _cellule_plate(2)),
                           "famine": _grille(_cellule(100.0), _cellule(20.0))})
    rep = run_s2(worlds=["soup", "famine"], seed=2026, K=12)
    assert set(rep["worlds"]) == {"soup", "famine"}, rep["worlds"]
    assert rep["worlds"]["soup"]["verdict"] == "INCONCLUSIVE_DEGENERATE", rep["worlds"]["soup"]
    assert rep["worlds"]["famine"]["verdict"] == "EXIGE", rep["worlds"]["famine"]
    assert _HarnaisFactice.saves and _HarnaisFactice.saves[-1] is rep     # ce qui est rendu EST archivé

    # NÉGATIF : les deux mondes lisibles -> aucun verdict d'indétermination.
    _injecte(monkeypatch, {"soup": _grille(_cellule(100.0), _cellule(20.0)),
                           "famine": _grille(_cellule(100.0), _cellule(20.0))})
    rep = run_s2(worlds=["soup", "famine"], seed=2026, K=12)
    assert [rep["worlds"][w]["verdict"] for w in ("soup", "famine")] == ["EXIGE", "EXIGE"], rep


def test_run_s2_EXCLUT_le_monde_degenere_de_la_famille_Holm(monkeypatch):
    """Un monde sans p-value n'a rien à corriger : il ne doit pas gonfler la multiplicité (m).
    Réponse connue en forme close : 3 mondes, 1 dégénéré + 2 décidés à dose SYMÉTRIQUE -> les deux
    décidés reçoivent p_holm = 2 x p (m=2), et le dégénéré n'a NI p_monde NI p_monde_holm.

    NÉGATIF APPARIÉ (E1) : le monde dégénéré remplacé par un TROISIÈME monde décidé à la même dose
    -> p_holm = 3 x p. La différence 2p vs 3p est exactement ce que ce test mesure ; sans elle, un
    code qui exclurait TOUT (ou n'exclurait RIEN) passerait la première moitié."""
    decide = _grille(_cellule(100.0), _cellule(20.0))
    _injecte(monkeypatch, {"soup": _grille(_cellule_plate(3), _cellule_plate(2)),
                           "famine": decide, "agricultural": decide})
    rep = run_s2(worlds=["soup", "famine", "agricultural"], seed=2026, K=12)["worlds"]
    assert "p_monde" not in rep["soup"] and "p_monde_holm" not in rep["soup"], rep["soup"]
    assert rep["famine"]["p_monde"] == pytest.approx(rep["agricultural"]["p_monde"])
    for w in ("famine", "agricultural"):
        assert rep[w]["p_monde_holm"] == pytest.approx(2.0 * rep[w]["p_monde"]), (w, rep[w])

    # NÉGATIF : 3 mondes DÉCIDÉS -> m=3, donc 3p. Le facteur change bien avec la taille de famille.
    _injecte(monkeypatch, {"soup": decide, "famine": decide, "agricultural": decide})
    rep = run_s2(worlds=["soup", "famine", "agricultural"], seed=2026, K=12)["worlds"]
    for w in ("soup", "famine", "agricultural"):
        assert rep[w]["p_monde_holm"] == pytest.approx(3.0 * rep[w]["p_monde"]), (w, rep[w])


def test_run_s2_N_ATTACHE_PAS_de_bloc_within_sous_un_regime_illisible(monkeypatch):
    """Le bloc `within` (ablation-perception) est un verdict CAUSAL. Le calculer sous un régime dont
    on vient de déclarer qu'il est illisible fabriquerait une causalité — même raison que pour VOID.

    NÉGATIF APPARIÉ (E1) : la même grille rendue lisible DOIT porter un `within` (sinon le test
    passerait pour un `within` qui n'est jamais attaché)."""
    _injecte(monkeypatch, {"soup": _grille(_cellule_plate(3), _cellule_plate(2))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "INCONCLUSIVE_DEGENERATE" and "within" not in w, w

    _injecte(monkeypatch, {"soup": _grille(_cellule(100.0), _cellule(20.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert "within" in w and w["within"]["verdict"].startswith("CAUSAL"), w


def test_print_table_DIT_la_raison_du_refus_au_lieu_d_un_p_fabrique(monkeypatch, capsys):
    """Le tableau imprimé est ce qu'un humain lit. Sous régime illisible il doit dire POURQUOI et
    n'afficher AUCUNE p-value (le mettre à 0.000, ou planter, sont les deux façons de mentir ici).

    NÉGATIF APPARIÉ (E1) : sur un monde lisible, la même ligne DOIT porter `p_monde=`."""
    _injecte(monkeypatch, {"soup": _grille(_cellule_plate(3), _cellule_plate(2))})
    run_s2(worlds=["soup"], seed=2026, K=12)
    ligne = [l for l in capsys.readouterr().out.splitlines() if l.strip().startswith("soup")]
    assert len(ligne) == 1, ligne
    assert "INCONCLUSIVE_DEGENERATE" in ligne[0] and "constants" in ligne[0], ligne[0]
    assert "p_monde=" not in ligne[0], ligne[0]

    _injecte(monkeypatch, {"soup": _grille(_cellule(100.0), _cellule(20.0))})
    run_s2(worlds=["soup"], seed=2026, K=12)
    ligne = [l for l in capsys.readouterr().out.splitlines() if l.strip().startswith("soup")]
    assert len(ligne) == 1 and "p_monde=" in ligne[0], ligne


# =====================================================================================================
# RÉFUTATION du correctif du 2026-09-08 — DEUX portes d'entrée de PLUS vers le même défaut (classe E3),
# trouvées en lançant des sondes contre lui (et non en le relisant). Le correctif fermait la boucle
# monde ; il restait (1) le sous-bloc `within` de la MÊME fonction d'impression, et (2) les deux tiers
# de la famille IUT que la garde n'inspectait pas.
#
# Mêmes outils que ci-dessus : injection à dose connue, aucun monde construit, aucune simulation.
# =====================================================================================================


def _grille_sauf(champion, base, **surcharges):
    """`_grille` avec des cellules DIFFÉRENTES par condition — nécessaire pour viser UN bras précis
    de la famille IUT, ce que `_grille` (même cellule partout) ne permet pas."""
    g = _grille(champion, base)
    inconnues = set(surcharges) - set(g)
    assert not inconnues, f"condition inexistante : {inconnues}"     # pas de surcharge fantôme
    g.update(surcharges)
    return g


def test_run_s2_REFUSE_un_bras_baseline_ILLISIBLE_meme_quand_ce_n_est_PAS_le_plus_fort(monkeypatch):
    """Le verdict de survie est un IUT CONJONCTIF : `p_monde = MAX des p` sur les TROIS baselines.
    `s2_verdict` n'inspecte pourtant QUE la paire (champion, baseline de plus haute médiane) — les
    deux autres membres entrent dans la décision SANS jamais avoir été jugés lisibles.

    Réponse connue : `random_genome` (2e du dict) est un bras VIDE, tout le reste est riche.
    AVANT ce correctif, le rapport publiait « VOID (survie incohérente : random_genome domine,
    p_monde=1.000, Cliff d=+0.00) » avec `ratio_lo=nan` — une affirmation de FOND fabriquée depuis
    ZÉRO individu, et comptée dans la famille Holm par-dessus le marché.

    INVARIANCE D'ORDRE, mesurée : `max(..., key=np.median)` est aveugle aux bras vides (np.median([])
    = nan, et nan ne gagne jamais un `>`), donc le MÊME bras vide donnait INCONCLUSIVE_DEGENERATE en
    1re position et VOID en 2e. Le même fait physique doit donner le même verdict.

    NÉGATIF APPARIÉ (E1) : le même bras, non plus vide mais simplement CONSTANT face à un champion
    étalé — régime parfaitement lisible (`s2_degeneracy` exige que les DEUX bras soient constants).
    Le verdict doit revenir, avec sa p-value. Sans ce bloc, une garde qui refuserait tout passerait."""
    # Les TROIS membres de la famille IUT, dans l'ordre où `run_s2` les insère. Le 3e (« reflex »)
    # n'est pas une condition mais la BORNE HAUTE des deux variantes de réflexe : pour le vider il
    # faut vider les DEUX (cf. le cas négatif 0 ci-dessous, qui fixe ce comportement).
    membres_iut = [(1, "random_action", {"random_action": _CELLULE_VIDE}),
                   (2, "random_genome", {"random_genome": _CELLULE_VIDE}),
                   (3, "reflex", {"reflex_naive": _CELLULE_VIDE, "reflex_prudent": _CELLULE_VIDE})]
    for position, bras, surcharge in membres_iut:
        _injecte(monkeypatch, {"soup": _grille_sauf(_cellule(100.0), _cellule(20.0), **surcharge)})
        w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
        assert w["verdict"] == "INCONCLUSIVE_DEGENERATE", (position, bras, w)
        assert w["degenerate"] is True and "VIDE" in w["why"], (bras, w)
        for fabrique in ("p_monde", "p_monde_holm", "cliff", "ratio_lo", "life_p", "survival"):
            assert fabrique not in w, f"{fabrique} FABRIQUE depuis un bras VIDE ({bras}) : {w}"

    # NÉGATIF 0 — comportement VOULU, mesuré en écrivant ce test et fixé ici pour qu'il ne dérive
    # pas : UNE SEULE variante de réflexe vide n'est PAS une dégénérescence. `run_s2` prend la borne
    # haute des deux variantes (`max`, avec `0.0` pour une variante vide), donc la variante survivante
    # entre seule dans l'IUT et le monde reste mesuré. C'est aussi le cas négatif qui prouve que la
    # garde sait ne pas se déclencher sur un bras qui n'atteint jamais la décision.
    _injecte(monkeypatch, {"soup": _grille_sauf(_cellule(100.0), _cellule(20.0),
                                                reflex_naive=_CELLULE_VIDE)})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert "degenerate" not in w and w["verdict"] == "EXIGE", w

    # NÉGATIF 1 : le bras visé est CONSTANT (non vide) et le champion est étalé -> LISIBLE.
    plat = {"survival": [17.0] * 12, "life_score": [1.7] * 12,
            "era_survival": [17.0] * 12, "era_life": [1.7] * 12, "censored_frac": 0.0}
    _injecte(monkeypatch, {"soup": _grille_sauf(_cellule(100.0), _cellule(20.0), random_genome=plat)})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert "degenerate" not in w and w["p_monde"] is not None, w
    assert w["verdict"] in {"EXIGE", "AMBIGU", "VOID"}, w

    # NÉGATIF 2 : aucune anomalie nulle part -> EXIGE, comme avant le correctif.
    _injecte(monkeypatch, {"soup": _grille(_cellule(100.0), _cellule(20.0))})
    assert run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]["verdict"] == "EXIGE"


def test_print_table_NE_PLANTE_PAS_sur_un_bloc_within_ILLISIBLE(monkeypatch, capsys):
    """3e porte d'entrée du défaut du jour, DANS la fonction que le correctif venait de garder.
    `verdict_within_subject` porte la MÊME garde de dégénérescence et rend alors un dict SANS
    'causal_cmp' / 'residual_cmp' ; `_print_table` faisait `cc = wi["causal_cmp"]` -> KeyError.

    Réponse connue, et c'est le régime le plus banal du dépôt : le champion ET sa version obs-ablée
    censurés au MÊME tick (variance nulle des DEUX côtés) pendant que les baselines meurent. Le monde
    a un verdict de survie parfaitement lisible — c'est le bloc CAUSAL qui ne l'est pas.

    Ce que le test EXIGE : (a) `run_s2` REND son rapport (l'exception tombait APRÈS `h.save`, donc la
    grille était mesurée, archivée, et perdue) ; (b) la ligne `within` dit la RAISON ; (c) elle
    n'imprime NI Cliff NI p ; (d) le monde SUIVANT est encore imprimé — c'est la propriété « la grille
    CONTINUE » que le correctif revendique, prise en défaut par cette porte.

    NÉGATIF APPARIÉ (E1) : within lisible -> la ligne DOIT porter « Cliff d= » et ne PAS porter la
    mention de refus. Sans lui, supprimer purement le bloc `within` de l'impression passerait."""
    plate = _cellule_plate(30)
    _injecte(monkeypatch, {"soup": _grille_sauf(plate, _cellule(20.0), champion_obs_ablated=plate),
                           "famine": _grille(_cellule(100.0), _cellule(20.0))})
    rep = run_s2(worlds=["soup", "famine"], seed=2026, K=12)      # (a) ne doit PAS lever
    sortie = capsys.readouterr().out.splitlines()

    assert rep["worlds"]["soup"]["within"]["verdict"] == "INCONCLUSIVE_DEGENERATE", rep["worlds"]["soup"]
    within = [l for l in sortie if "within (ablation-perception)" in l]
    # 2 lignes attendues : celle de `soup` (illisible) PUIS celle de `famine` (lisible) — leur simple
    # coexistence est déjà la preuve (d) : l'ancienne version levait sur la 1re et la 2e n'existait pas.
    assert len(within) == 2, within
    assert "INCONCLUSIVE_DEGENERATE" in within[0], within[0]                 # (b) la raison
    assert "Cliff d=" not in within[0] and " p=" not in within[0], within[0]  # (c) rien de fabriqué
    assert "Cliff d=" in within[1], within[1]                                # le monde suivant MESURÉ
    assert [l for l in sortie if l.strip().startswith("famine")], sortie      # (d) la grille CONTINUE

    # NÉGATIF : within lisible -> les chiffres reviennent, la mention de refus disparaît.
    _injecte(monkeypatch, {"soup": _grille(_cellule(100.0), _cellule(20.0))})
    run_s2(worlds=["soup"], seed=2026, K=12)
    within = [l for l in capsys.readouterr().out.splitlines() if "within (ablation-perception)" in l]
    assert len(within) == 1 and "Cliff d=" in within[0], within
    assert "aucune comparaison lisible" not in within[0], within[0]
