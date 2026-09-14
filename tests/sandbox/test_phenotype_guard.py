"""P1.7 — le CORPS est dérivé des lignes 0-9 de W : toute édition de W est AUSSI une intervention
métabolique (backlog, bloc « 🧭 2026-09-14 », fait neuf n° 2 ; classe E26 du registre).

`src/agents/mamba_agent.py:47-50` : `hp_bonus = 10·Σ|W[0:5]|`, `inv_capacity = max(3, Σ|W[5:10]|)`,
`drain = 1 + hp_bonus/100 + 0,1·inv_capacity (+0,5 si organe MCTS)`. Les MÊMES lignes portent
l'observation dans le réseau. `make_blind` (annule `W[:num_inputs, :]`) annonçait « corps, biais et
récurrence restent identiques » : FAUX par construction — le drain tombe avec les lignes. Les deux
records arrêtés du 2026-09-08 (S2-BLIND-CHAMPION, S2-SUBJECT-VARIANCE) ont comparé des sujets à corps
différents sans le savoir.

Trois outils, calibrés ici sur des réponses EXACTES (aucun monde, aucun RNG de simulation) :
  phenotype_of              la formule du monde, mot pour mot
  assert_phenotype_matched  REFUSE un contraste entre sujets à corps différents (la garde E26)
  ballast_phenotype         rend à un génome édité le corps de sa référence, EXACTEMENT, par un canal
                            INERTE sur la politique : la diagonale des nœuds d'ENTRÉE (leur état est
                            écrasé par l'observation à chaque tick, `mamba_agent.py:562`, et la
                            diagonale ne nourrit jamais l'excitation, `W_no_diag`) — et REFUSE quand ce
                            canal n'est pas inerte (sorties qui chevauchent les entrées, E24) ou quand
                            le corps devrait BAISSER (impossible sans toucher la politique).
"""
import copy
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.agents.backend import make_population  # noqa: E402
from src.agents.mamba_agent import MambaAgent  # noqa: E402
from src.seed_ai.mutation import Genome  # noqa: E402
from tools.evo_runs.s2_blind_champion import make_blind  # noqa: E402
from tools.experiment_preflight import (  # noqa: E402
    PhenotypeMismatch, PreflightError, assert_phenotype_matched, ballast_phenotype, phenotype_of)

N, I, O = 40, 12, 10


def _genome(seed=0):
    rng = np.random.RandomState(seed)
    return Genome(W=rng.uniform(-1.0, 1.0, (N, N)).astype(np.float32), num_inputs=I, num_outputs=O)


def _agent(g):
    a = MambaAgent()
    a.from_genome(g)
    return a


def test_phenotype_of_is_the_world_formula_exactly():
    W = np.zeros((N, N), dtype=np.float32)
    W[0, 3], W[2, 7] = 0.5, -1.5            # Σ|W[0:5]| = 2.0  -> hp_bonus 20.0
    W[5, 1], W[9, 9] = 3.0, 4.0             # Σ|W[5:10]| = 7.0 -> inv_capacity 7
    g = Genome(W=W, num_inputs=I, num_outputs=O)
    ph = phenotype_of(g)
    assert ph == {"hp_bonus": 20.0, "inv_capacity": 7, "energy_drain": 1.0 + 0.2 + 0.7}
    a = _agent(g)                            # la formule du MONDE, sur l'agent vivant
    assert (a.phenotype_hp_bonus, a.phenotype_inv_capacity, a.phenotype_energy_drain) == (
        ph["hp_bonus"], ph["inv_capacity"], ph["energy_drain"])


def test_assert_phenotype_matched_REFUSES_make_blind():
    g = _genome()
    b = make_blind(g)
    assert phenotype_of(b)["energy_drain"] < phenotype_of(g)["energy_drain"], "aveugler MAIGRIT le corps"
    with pytest.raises(PhenotypeMismatch) as e:
        assert_phenotype_matched(b, g, label="aveugle vs champion")
    assert "drain" in str(e.value) and "E26" in str(e.value)
    assert isinstance(e.value, PreflightError)
    assert assert_phenotype_matched(g, copy.deepcopy(g)) is True


def test_assert_phenotype_matched_tolerance_is_explicit_never_implicit():
    """`tol` borne l'écart de DRAIN (la grandeur qui agit à chaque tick) ; `inv_capacity`, entier qui
    gate le craft et le portage, est exigé ÉGAL quelle que soit la tolérance."""
    g = _genome()
    h = copy.deepcopy(g)
    h.W[0, 3] += 0.01                        # Σ|W[0:5]| +0.01 -> hp +0.1 -> drain +0.001
    with pytest.raises(PhenotypeMismatch):
        assert_phenotype_matched(h, g)       # tol=0 par défaut : EXACT
    assert assert_phenotype_matched(h, g, tol=0.01) is True
    k = copy.deepcopy(g)
    k.W[5, 2] += 1.0                         # Σ|W[5:10]| +1 -> inv_capacity +1 : un ENTIER qui change le monde
    with pytest.raises(PhenotypeMismatch):
        assert_phenotype_matched(k, g, tol=1.0)


def test_ballast_restores_the_phenotype_EXACTLY_and_keeps_the_subject_blind():
    g = _genome()
    b = make_blind(g)
    bb = ballast_phenotype(b, reference=g)
    assert phenotype_of(bb) == phenotype_of(g)
    off = ~np.eye(N, dtype=bool)
    assert np.all(bb.W[:I, :][off[:I, :]] == 0.0), "hors diagonale, les lignes d'entrée restent NULLES : toujours aveugle"
    assert np.array_equal(bb.W[I:, :], b.W[I:, :]), "rien d'autre que les lignes d'entrée n'a bougé"
    assert assert_phenotype_matched(bb, g) is True


def test_ballast_is_bit_identical_on_the_policy_it_does_not_touch():
    """Sur un génome aux VRAIES dimensions du monde (le forward legacy lit des colonnes d'observation
    fixes, au-delà d'un petit `num_inputs`) : aveugle et aveugle-lesté rendent des logits
    BIT-IDENTIQUES sur quatre ticks — le canal du lest ne touche pas la politique."""
    np.random.seed(3)
    g = MambaAgent().genome                  # dimensions de production (pas de chevauchement E24)
    assert g.num_inputs + g.num_outputs <= g.num_nodes
    b = make_blind(g)
    bb = ballast_phenotype(b, reference=g)
    assert phenotype_of(bb) == phenotype_of(g)
    obs = np.random.RandomState(7).uniform(-1.0, 1.0, (3, g.num_inputs)).astype(np.float32)
    logits = []
    for genome in (b, bb):
        pop = make_population([_agent(genome) for _ in range(3)], backend="legacy")
        np.random.seed(11)
        logits.append([np.asarray(pop.forward(obs)[0]).copy() for _ in range(4)])
    for t in range(4):
        assert np.array_equal(logits[0][t], logits[1][t]), f"tick {t} : le lest a changé la politique"


def test_ballast_REFUSES_when_outputs_overlap_inputs():
    rng = np.random.RandomState(1)
    g = Genome(W=rng.uniform(-1.0, 1.0, (N, N)).astype(np.float32), num_inputs=30, num_outputs=20)   # 30+20 > 40
    with pytest.raises(PreflightError) as e:
        ballast_phenotype(make_blind(g), reference=g)
    assert "E24" in str(e.value)


def test_ballast_REFUSES_to_shrink_a_body():
    g = _genome()
    with pytest.raises(PreflightError) as e:
        ballast_phenotype(g, reference=make_blind(g))   # il faudrait RETIRER du poids : toucher la politique
    assert "baisser" in str(e.value).lower() or "reduire" in str(e.value).lower() or "réduire" in str(e.value).lower()
