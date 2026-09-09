"""TDD C1 — l'anticipation (application d'un forward-model) est survival-porteuse SSI corps insuffisant +
dynamique non-triviale (shift≠0) + énergie. Ablation = module M→identité."""
import numpy as np
from tools.anticipation_demand_world_probe import survive, probe, _model_matrix, _shifted


def test_model_matrix_implements_shift():
    K, shift = 5, 1
    M = _model_matrix(shift, K)
    for s in range(1, K):
        o = np.zeros(K); o[s] = 1.0
        assert int(np.argmax(M @ o)) == _shifted(s, shift, K)   # M applique la dynamique
    assert M[0, 0] == 1.0                                        # identité sur le corps


def test_recipe_insufficient_dynamic_energy_is_anticipation_sensitive():
    # RECETTE : corps insuffisant + shift=1 (futur) + énergie -> survie exige le modèle -> ablation effondre
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", shift=1, K=5, seed=2, n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_ANTICIPATION_SENSITIVE"


def test_static_dynamics_is_neutral():
    # shift=0 (nourriture statique) : le réactif (identité) suffit -> ablation du module inerte -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", shift=0, K=5, seed=2, n_eval=16, ticks=200)
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
    assert r["verdict"] != "SURVIVAL_ANTICIPATION_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)


def test_separate_currency_is_neutral():
    # devise séparée : anticiper ne paie pas la survie -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=20.0, currency="separate", shift=1, K=5, seed=2, n_eval=16, ticks=200)
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
    assert r["verdict"] != "SURVIVAL_ANTICIPATION_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)
