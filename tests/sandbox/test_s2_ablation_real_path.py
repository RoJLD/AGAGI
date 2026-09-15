# -*- coding: utf-8 -*-
"""P2.59 (2026-09-15) -- `run_ablation_map` calibre sur son CHEMIN REEL (genome -> politique -> monde),
a reponse CONNUE, via le seam de POLITIQUE `batch_model_cls`.

Ce que la mesure a dit AVANT d'ecrire ces attentes (stoneage, 6 agents, K = 12) :
  * politique AVEUGLE a l'obs sur le corps du champion : within = 1,000 EXACT, no-op = 1,000 -> DECOY.
    C'est la reponse connue par CONSTRUCTION : ses decisions ne dependent pas de l'entree.
  * lecteur-CHASSEUR (ReflexBatchModel) : within 0,86 contre no-op 0,88 -> DECOY, l'effet est DANS
    la bande ; sous corps insuffisant (metab 0,5, payoff 3) : within 0,66 contre no-op 0,88 ->
    INCONCLUSIVE_INVERTED -- lire pour poursuivre COUTE la survie (EVO-011 : l'acte debloque est
    net-negatif). L'instrument voit un effet reel et le SIGNE.
  * lecteur-FUYARD, lecteur PRUDENT : inertes (le signal hostile ne se presente pas) -> DECOY.
  ⚠️ Le backlog attendait « lecteur cable -> DEMANDED ». Sur stoneage par defaut, AUCUNE lecture
  cablee testee n'est net-positive : le DEMANDED du chemin reel n'existe pas dans ce monde -- c'est
  le fil S2 (S2-002, S2-012) retrouve par le chemin reel. DEMANDED reste calibre par INJECTION
  (tests/test_s2_ablation_wiring.py) ; ce fichier gele DECOY et INVERSE sur le REEL.
"""
import numpy as np
import pytest

from src.environments.config import WorldConfig
from tools.demand_marker import ablation_verdict
from tools.experiment_preflight import PhenotypeMismatch, phenotype_of
from tools.jobs.run import hold
from tools.s2_demand import WORLDS, load_champion_genome, run_condition
from tools.s2_demand_ablation import (NullAblatedMamba, ObsBlindOnBody, ObsReaderOnBody,
                                      PerceptionAblatedMamba, perception_ablated_variant,
                                      perception_null_variant, run_ablation_map)
from src.agents.mamba_agent import MambaBatchModel


# --- les variantes : PURES, aucun monde --------------------------------------------------------------

def test_les_variantes_de_Mamba_sont_les_classes_HISTORIQUES_bit_identiques():
    """Aucun appelant existant ne bouge : pour MambaBatchModel les variantes SONT les classes publiees."""
    assert perception_ablated_variant(MambaBatchModel) is PerceptionAblatedMamba
    assert perception_null_variant(MambaBatchModel) is NullAblatedMamba


def test_une_variante_est_une_SOUS_CLASSE_et_l_operation_est_IDEMPOTENTE():
    v = perception_ablated_variant(ObsBlindOnBody)
    assert issubclass(v, ObsBlindOnBody) and perception_ablated_variant(v) is v
    n = perception_null_variant(ObsBlindOnBody)
    assert issubclass(n, ObsBlindOnBody) and perception_null_variant(n) is n and n is not v


def test_la_garde_E26_REFUSE_un_sujet_au_corps_edite_AVANT_tout_monde():
    """Un sujet dont les lignes 0-9 de W sont annulees (« aveugle ») n'a PAS le corps du champion :
    `reference_body` doit lever AVANT toute construction de monde -- donc sans bail, en < 1 s."""
    import copy
    champ = load_champion_genome()
    aveugle = copy.deepcopy(champ)
    aveugle.W[0:10, :] = 0.0
    assert phenotype_of(aveugle) != phenotype_of(champ), "le corps DOIT differer, sinon le cas ne teste rien"
    with pytest.raises(PhenotypeMismatch):
        run_ablation_map(worlds=["stoneage"], K=1, num_agents=1, max_ticks=1, subject=aveugle,
                         reference_body=champ)


def test_la_garde_E26_LAISSE_PASSER_le_meme_corps():
    """NO-OP APPARIE : le champion contre lui-meme ne leve pas (la garde, elle, tourne)."""
    from tools.experiment_preflight import assert_phenotype_matched
    champ = load_champion_genome()
    assert assert_phenotype_matched(champ, champ) is True


# --- le CHEMIN REEL, sous bail --------------------------------------------------------------------------

@pytest.mark.slow
def test_une_politique_AVEUGLE_sur_le_corps_du_champion_rend_DECOY_EXACT_sur_le_chemin_reel():
    """Reponse connue par CONSTRUCTION : ses decisions ne lisent pas l'obs, deranger l'obs ne change
    RIEN -> within = 1,000 exact, et le no-op publie vaut 1,000 aussi. Corps et politique PUBLIES."""
    champ = load_champion_genome()
    with hold("kuzu", owner="test-p259-blind", ttl_s=900):
        m = run_ablation_map(worlds=["stoneage"], seed=2026, K=12, num_agents=6, max_ticks=60,
                             batch_model_cls=ObsBlindOnBody, between_same_body=True, noop_control=True)
    r = m["stoneage"]
    assert r["verdict"] == "PERCEPTION_DECOY", r
    assert r["within_ratio"] == pytest.approx(1.0, abs=1e-9), r
    assert r["noop"]["ratio"] == pytest.approx(1.0, abs=1e-9), r["noop"]
    assert r["policy"] == "ObsBlindOnBody" and r["between_same_body"] is True
    assert r["phenotype"] == phenotype_of(champ), "le corps publie est celui du champion (E26)"


@pytest.mark.slow
def test_un_lecteur_CHASSEUR_sous_corps_insuffisant_rend_un_effet_INVERSE_HORS_de_la_bande_no_op():
    """Reponse connue par MESURE (2026-09-15) : lire pour poursuivre COUTE la survie -- l'instrument
    voit un effet reel (0,66) hors de la bande du no-op (0,88), et le SIGNE (INVERTED). Le no-op est
    la variante nulle de la MEME politique -- sans elle, il comparait deux politiques (0,68 mesure)."""
    champ = load_champion_genome()
    cfg = WorldConfig(); cfg.base_metabolism = 0.5; cfg.forage_payoff = 3.0
    with hold("kuzu", owner="test-p259-reader", ttl_s=900):
        kw = dict(num_agents=6, max_ticks=120, n_eras=12, config=cfg)
        i = run_condition(WORLDS["stoneage"], ObsReaderOnBody, champ, 2026, **kw)
        a = run_condition(WORLDS["stoneage"], perception_ablated_variant(ObsReaderOnBody), champ, 2026, **kw)
        n = run_condition(WORLDS["stoneage"], perception_null_variant(ObsReaderOnBody), champ, 2026, **kw)
    v = ablation_verdict(i["era_survival"], a["era_survival"], ceiling=120.0)
    vn = ablation_verdict(i["era_survival"], n["era_survival"], ceiling=120.0)
    assert v["verdict"] == "INCONCLUSIVE_INVERTED", v
    assert v["ratio"] < vn["ratio"] - 0.10, ("l'effet doit sortir de la bande du no-op", v["ratio"], vn["ratio"])
    assert np.median(a["era_survival"]) > np.median(i["era_survival"]), "l'able survit PLUS : lire coute"
