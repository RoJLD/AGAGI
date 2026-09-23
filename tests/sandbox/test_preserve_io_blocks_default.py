"""P2.63 — `preserve_io_blocks` est ACTIVÉ PAR DÉFAUT (bascule datée du 2026-09-15).

Non-régression de la DÉCISION : un `MutationConfig()` construit SANS passer le paramètre doit préserver
les blocs d'entrée/sortie sous chaque opérateur de croissance. Avant la bascule, ces tests sont ROUGES
(défaut historique : 26/120 désalignements par opérateur, cf. `test_mutation_block_invariants.py`).

Contexte : le correctif existe depuis le 2026-08-04 derrière un flag OFF (off = bit-identique à
l'historique, [[EDR-EVO-024]] l'a validé NEUTRE : 0/12 vs 0/12, Fisher p = 1.000). La bascule était une
DÉCISION, pas une tâche — prise le 2026-09-14 (backlog P2.63). Le régime HISTORIQUE reste accessible en
passant `preserve_io_blocks=False` EXPLICITEMENT ; son contre-exemple gelé vit dans
`test_mutation_block_invariants.py::test_flag_OFF_reproduces_the_legacy_defect`.

⚠️ Comme son voisin, ce fichier DÉCOUVRE les opérateurs de croissance au lieu d'en tenir une liste :
un opérateur ajouté demain est soumis au contrat par défaut sans que personne y pense.
"""
import inspect
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import src.seed_ai.mutation as MUT  # noqa: E402
from src.seed_ai.mutation import MutationConfig, Genome  # noqa: E402

I, O, N = 12, 8, 40
TRIALS = 120


def _genome():
    """Génome à AUTO-BOUCLES (j uniforme sur TOUS les nœuds, blocs atteignables — classe E9 sinon),
    chaque sortie k portant le marqueur d'identité 100+k sur sa diagonale."""
    W = np.zeros((N, N), dtype=np.float32)
    np.fill_diagonal(W, 1.0)
    for k in range(O):
        W[N - O + k, N - O + k] = 100.0 + k
    W[3, N - O + 2] = 0.7
    W[5, N - O + 5] = -0.4
    return Genome(W, I, O)


def _outputs_still_themselves(g):
    """Au plus UN marqueur faux = scission légitime ; DEUX ou plus = le bloc a GLISSÉ."""
    base = g.num_nodes - g.num_outputs
    faux = sum(1 for k in range(g.num_outputs)
               if float(g.W[base + k, base + k]) != 100.0 + k)
    return faux <= 1


def _growth_operators():
    """DÉCOUVERTE : toute fonction publique de `mutation` (genome, config) qui fait grandir num_nodes."""
    found = []
    for name, fn in vars(MUT).items():
        if name.startswith("_") or not inspect.isfunction(fn) or fn.__module__ != MUT.__name__:
            continue
        try:
            params = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            continue
        if params[:2] != ["genome", "config"]:
            continue
        g = _genome()
        n0 = g.num_nodes
        np.random.seed(0)
        try:
            fn(g, MutationConfig())
        except Exception:
            continue
        if g.num_nodes > n0:
            found.append((name, fn))
    return found


def _desalignements(fn, cfg):
    d = 0
    for s in range(TRIALS):
        g = _genome()
        np.random.seed(s)
        fn(g, cfg)
        if not _outputs_still_themselves(g):
            d += 1
    return d


def test_discovery_is_not_empty():
    """Garde de la garde : une liste vide rendrait les tests paramétrés SAUTÉS, donc verts par absence."""
    names = sorted(n for n, _ in _growth_operators())
    assert "add_node" in names and "add_meso_gated_unit" in names, f"découverte suspecte : {names}"


def test_default_config_declares_preserve_io_blocks_true():
    """La clause de fermeture de P2.63 : le DÉFAUT, sans rien passer, est True."""
    cfg = MutationConfig()
    assert cfg.preserve_io_blocks is True, (
        "P2.63 : preserve_io_blocks doit être ACTIVÉ par défaut (décision du 2026-09-14) — "
        f"trouvé {cfg.preserve_io_blocks!r}")


@pytest.mark.parametrize("op_name", [n for n, _ in _growth_operators()])
def test_growth_operators_preserve_io_blocks_by_default(op_name):
    """Le CONTRAT par défaut : sans passer le flag, aucune insertion ne fait glisser le bloc de sortie."""
    fn = dict(_growth_operators())[op_name]
    d = _desalignements(fn, MutationConfig())          # le paramètre n'est PAS passé
    assert d == 0, (
        f"{op_name} : {d}/{TRIALS} désalignements avec MutationConfig() nu — le défaut est encore "
        f"le régime HISTORIQUE (attendu 0 : preserve_io_blocks=True par défaut, P2.63)")


@pytest.mark.parametrize("op_name", [n for n, _ in _growth_operators()])
def test_default_is_bit_identical_to_explicit_true(op_name):
    """Le défaut EST le correctif, pas « zéro désalignement par hasard » : à graine égale, la matrice
    obtenue sans passer le flag est bit-identique à celle obtenue avec `preserve_io_blocks=True`."""
    fn = dict(_growth_operators())[op_name]
    for s in range(30):
        g_def, g_on = _genome(), _genome()
        np.random.seed(s)
        fn(g_def, MutationConfig())
        np.random.seed(s)
        fn(g_on, MutationConfig(preserve_io_blocks=True))
        assert g_def.W.shape == g_on.W.shape and np.array_equal(g_def.W, g_on.W), (
            f"{op_name}, graine {s} : le défaut ne rend pas la matrice du régime CORRIGÉ")
