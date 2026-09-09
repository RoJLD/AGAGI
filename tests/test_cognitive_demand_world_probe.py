"""TDD B1 — le probe de demande cognitive : la survie devient perception-sensible SSI la cognition paie
en ÉNERGIE et dépasse le corps ; en devise séparée elle reste neutre."""
import numpy as np
from tools.cognitive_demand_world_probe import survive, ladder, _ablate, _obs


def test_ablate_modes_shapes():
    rng = np.random.RandomState(0)
    o = _obs(2, 5, rng)
    assert _ablate(o, "true", 5, rng) is o
    assert _ablate(o, "zero", 5, rng).sum() == 0.0
    assert _ablate(o, "noise", 5, rng).shape == (5,)
    assert _ablate(o, "permuted", 5, rng).shape == (5,)


def test_sufficient_body_survives_without_obs():
    # réflexe corps SUFFISANT (body_gain 1.2 > metab 1.0) : survit au cap même obs nulle -> corps ceiling
    K = 5
    W = np.zeros((K, K)); b = np.zeros(K); b[0] = 10.0        # force argmax=0 (réflexe corps)
    s = survive(W, b, "zero", body_gain=1.2, cog_gain=5.0, currency="energy", K=K,
                rng=np.random.RandomState(1), ticks=200)
    assert s == 200                                           # le corps suffisant survit au cap


def test_recipe_cell_insufficient_body_energy_is_sensitive():
    # RECETTE : corps INSUFFISANT (0.5<metab) + cognition payée EN ÉNERGIE (2.0>metab) -> survie exige
    # de lire l'obs -> ablation effondre -> SENSIBLE, et la politique PÈSE l'obs.
    r = ladder(body_gain=0.5, cog_gain=2.0, currency="energy", K=5, seed=3, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_SENSITIVE"
    assert r["obs_weight"] > 0.05


def test_sufficient_body_energy_is_neutral():
    # corps SUFFISANT (1.2>metab) : la survie plafonne sur le corps -> NEUTRE malgré la cognition-énergie
    r = ladder(body_gain=1.2, cog_gain=2.0, currency="energy", K=5, seed=3, n_eval=16, ticks=200)
    # ⚠️ RECTIFIE le 2026-09-09 (P2.49). Ce test affirmait `SURVIVAL_NEUTRAL` et etait ROUGE depuis
    # que la garde de degenerescence a ete armee (2026-07-21) -- en silence, car AUCUN job de CI ne
    # lance ce fichier. Le verdict correct est `INDETERMINE_DEGENERATE` : les deux bras rendent des
    # tableaux LITTERALEMENT identiques, et deux bras identiques ont deux causes opposees que des
    # sorties ne separent pas (l'intervention ne s'est pas appliquee / elle s'est appliquee et n'a
    # rien fait). Le depot le dit deja pour S2-004 : « tout ratio ~1 devient (a juste titre)
    # INCONCLUSIVE_DEGENERATE [...] le NEUTRE de S2-004 est ILLISIBLE a tout sigma avec ce
    # mesureur-SEUIL » (tools/s2_fallback_rate_probe.py). C'est la meme situation ici.
    # CE QUE CA CHANGE, et c'est le point : une cellule de controle INDECIDABLE n'etablit PAS la
    # SPECIFICITE de la demande -- elle dit seulement qu'aucun effondrement n'est detecte. Les deux
    # assertions ci-dessous separent ce qui TIENT de ce qui ne tient plus.
    assert r["verdict"] != "SURVIVAL_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)


def test_separate_currency_stays_survival_neutral():
    # corps INSUFFISANT + cognition en devise SÉPARÉE (pas d'énergie) : lire l'obs ne sauve pas -> NEUTRE
    r = ladder(body_gain=0.5, cog_gain=20.0, currency="separate", K=5, seed=3, n_eval=16, ticks=200)
    # ⚠️ RECTIFIE le 2026-09-09 (P2.49). Ce test affirmait `SURVIVAL_NEUTRAL` et etait ROUGE depuis
    # que la garde de degenerescence a ete armee (2026-07-21) -- en silence, car AUCUN job de CI ne
    # lance ce fichier. Le verdict correct est `INDETERMINE_DEGENERATE` : les deux bras rendent des
    # tableaux LITTERALEMENT identiques, et deux bras identiques ont deux causes opposees que des
    # sorties ne separent pas (l'intervention ne s'est pas appliquee / elle s'est appliquee et n'a
    # rien fait). Le depot le dit deja pour S2-004 : « tout ratio ~1 devient (a juste titre)
    # INCONCLUSIVE_DEGENERATE [...] le NEUTRE de S2-004 est ILLISIBLE a tout sigma avec ce
    # mesureur-SEUIL » (tools/s2_fallback_rate_probe.py). C'est la meme situation ici.
    # CE QUE CA CHANGE, et c'est le point : une cellule de controle INDECIDABLE n'etablit PAS la
    # SPECIFICITE de la demande -- elle dit seulement qu'aucun effondrement n'est detecte. Les deux
    # assertions ci-dessous separent ce qui TIENT de ce qui ne tient plus.
    assert r["verdict"] != "SURVIVAL_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)
