"""TDD C2 — la composition (chaîner un moyen non-récompensé vers une fin) est survival-porteuse SSI
corps insuffisant + chaîne ≥2 + énergie. Ablation = module de plan (identité du moyen → 0)."""
import numpy as np
from tools.composition_demand_world_probe import survive, probe


def test_sufficient_body_survives_without_plan():
    # réflexe corps suffisant (1.2>metab) : survit au cap même plan ablaté
    K = 5
    W = np.zeros((K, 2 * K)); b = np.zeros(K); b[0] = 10.0     # force a=0 (corps)
    s = survive(W, b, "ablated", body_gain=1.2, cog_gain=3.0, currency="energy", chain_len=2,
                K=K, rng=np.random.RandomState(1), ticks=200)
    assert s == 200


def test_recipe_insufficient_chain2_energy_is_composition_sensitive():
    # RECETTE : corps insuffisant + chaîne 2 (moyen requis) + énergie -> survie exige de composer
    r = probe(body_gain=0.5, cog_gain=3.0, currency="energy", chain_len=2, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_COMPOSITION_SENSITIVE"


def test_chain1_no_means_is_neutral():
    # chaîne 1 (fin directe, pas de moyen) : le plan est vide -> ablation inerte -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=3.0, currency="energy", chain_len=1, K=5, seed=2, n_eval=16, ticks=200)
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
    assert r["verdict"] != "SURVIVAL_COMPOSITION_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)


def test_separate_currency_is_neutral():
    # devise séparée : composer ne paie pas la survie -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=20.0, currency="separate", chain_len=2, K=5, seed=2, n_eval=16, ticks=200)
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
    assert r["verdict"] != "SURVIVAL_COMPOSITION_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)
