"""TDD B2 — la mémoire n'est survival-porteuse que si corps insuffisant ET rappel différé ET énergie."""
import numpy as np
from tools.memory_demand_world_probe import survive, probe


def test_sufficient_body_survives_without_memory():
    # réflexe corps suffisant (1.2>metab) : survit au cap même mémoire ablatée
    K = 5
    W = np.zeros((K, 2 * K)); b = np.zeros(K); b[0] = 10.0     # force a=0 (réflexe corps)
    s = survive(W, b, "ablated", body_gain=1.2, cog_gain=5.0, currency="energy", recall="delayed",
                K=K, rng=np.random.RandomState(1), ticks=200)
    assert s == 200


def test_recipe_insufficient_delayed_energy_is_memory_sensitive():
    # RECETTE : corps insuffisant + rappel DIFFÉRÉ + énergie -> survie exige la mémoire -> ablation effondre
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", recall="delayed", K=5, seed=2,
              n_eval=16, ticks=200)
    assert r["verdict"] == "SURVIVAL_MEMORY_SENSITIVE"
    assert r["mem_weight"] > 0.05                              # la politique PÈSE la mémoire


def test_present_recall_is_neutral():
    # rappel PRÉSENT (l'obs montre l'action correcte) : la mémoire est inutile -> ablation inerte -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=2.0, currency="energy", recall="present", K=5, seed=2,
              n_eval=16, ticks=200)
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
    assert r["verdict"] != "SURVIVAL_MEMORY_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)


def test_separate_currency_is_neutral():
    # devise séparée : réussir le rappel ne paie pas la survie -> NEUTRE
    r = probe(body_gain=0.5, cog_gain=20.0, currency="separate", recall="delayed", K=5, seed=2,
              n_eval=16, ticks=200)
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
    assert r["verdict"] != "SURVIVAL_MEMORY_SENSITIVE", "ce qui TIENT : aucune demande n'est detectee"
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (
        "ce qui NE TIENT PLUS : la cellule de controle est INDECIDABLE, pas neutre -- "
        "elle ne peut donc pas etablir la SPECIFICITE de la demande", r)
