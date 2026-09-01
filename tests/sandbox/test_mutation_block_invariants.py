"""Contrat de BLOC des opérateurs de mutation — et il se découvre TOUT SEUL.

Le contrat : les ENTRÉES sont les `num_inputs` PREMIERS nœuds, les SORTIES les `num_outputs` DERNIERS.
Tout opérateur qui insère un nœud doit le faire dans la région cachée, sinon l'indice sémantique de
chaque sortie glisse et une arête câblée se met à piloter une AUTRE décision (56 % de désalignement
mesuré, [[EDR-EVO-021]]).

⚠️ **Ce fichier ne teste pas une liste d'opérateurs : il la DÉCOUVRE.** `_growth_operators()` balaie
`src/seed_ai/mutation.py` et retient toute fonction publique qui fait grandir `num_nodes`. Un opérateur
ajouté demain est donc couvert sans que personne y pense — c'est le seul moyen d'éviter que la dette se
reforme ailleurs. Le défaut d'origine avait justement DEUX porteurs (`add_node` ET `add_meso_gated_unit`),
et je n'avais vu que le premier : le pré-vol d'[[EDR-EVO-023]] a dû m'apprendre l'existence du second.

`preserve_io_blocks` est **désactivé par défaut** : off = bit-identique à l'historique, parce que les
records EVO-005→023 ont été mesurés avec le défaut ([[EDR-EVO-024]]).
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


def _genome(reflex=True):
    """Génome à AUTO-BOUCLES : `j` y est uniforme sur TOUS les nœuds, donc les blocs sont atteignables.
    (Sur une soupe fraîche `j >= num_inputs` toujours — c'est ce qui masquait le défaut, classe E9.)

    Chaque nœud de SORTIE porte un MARQUEUR unique sur sa diagonale (100+k). C'est ce marqueur qui
    teste l'identité sémantique : « le nœud qui était la sortie k est-il toujours la sortie k ? ».
    ⚠️ Ne PAS tester la survie d'une arête : `add_node` la SCINDE par construction (3 -> nouveau ->
    sortie), et une scission n'est pas un désalignement."""
    W = np.zeros((N, N), dtype=np.float32)
    if reflex:
        np.fill_diagonal(W, 1.0)
    for k in range(O):
        W[N - O + k, N - O + k] = 100.0 + k      # marqueur d'identite de la sortie k
    W[3, N - O + 2] = 0.7
    W[5, N - O + 5] = -0.4
    return Genome(W, I, O)


def _outputs_still_themselves(g):
    """Le bloc de sortie a-t-il GLISSÉ ?

    ⚠️ Discriminer deux choses que le marqueur seul confond : l'opérateur peut légitimement SCINDER
    l'auto-boucle qui sert de marqueur (elle passe alors à 0) — ce n'est pas un décalage. Un vrai
    décalage, lui, déplace TOUS les marqueurs d'un cran à la fois.
    Critère : au plus UN marqueur faux = scission tolérée ; DEUX ou plus = le bloc a glissé."""
    base = g.num_nodes - g.num_outputs
    faux = sum(1 for k in range(g.num_outputs)
               if float(g.W[base + k, base + k]) != 100.0 + k)
    return faux <= 1


def _growth_operators():
    """DÉCOUVERTE automatique : toute fonction publique de `mutation` qui fait grandir num_nodes."""
    found = []
    for name, fn in vars(MUT).items():
        if name.startswith("_") or not inspect.isfunction(fn):
            continue
        if fn.__module__ != MUT.__name__:
            continue
        try:
            params = list(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            continue
        if params[:2] != ["genome", "config"]:
            continue
        g = _genome()
        n0 = g.num_nodes
        cfg = MutationConfig()
        np.random.seed(0)
        try:
            fn(g, cfg)
        except Exception:
            continue
        if g.num_nodes > n0:
            found.append((name, fn))
    return found


def test_growth_operators_are_actually_discovered():
    """Garde de la garde : si la découverte rend une liste VIDE, tous les tests ci-dessous passeraient
    sans rien vérifier (classe E4 — vérification vide)."""
    ops = _growth_operators()
    names = sorted(n for n, _ in ops)
    assert len(ops) >= 2, f"découverte suspecte : {names}"
    assert "add_node" in names and "add_meso_gated_unit" in names, (
        f"les deux porteurs connus du défaut doivent être découverts : {names}")


@pytest.mark.parametrize("op_name", [n for n, _ in _growth_operators()])
def test_block_contract_is_preserved_when_the_flag_is_ON(op_name):
    """⚠️ LE CONTRAT. Avec `preserve_io_blocks`, une arête câblée doit continuer à piloter LA MÊME
    sortie après insertion — pour CHAQUE opérateur de croissance, découvert ou futur."""
    fn = dict(_growth_operators())[op_name]
    cfg = MutationConfig()
    cfg.preserve_io_blocks = True
    desaligne = 0
    TRIALS = 120
    for s in range(TRIALS):
        g = _genome()
        np.random.seed(s)
        fn(g, cfg)
        if not _outputs_still_themselves(g):
            desaligne += 1
    assert desaligne == 0, (
        f"{op_name} : {desaligne}/{TRIALS} désalignements malgré preserve_io_blocks — "
        f"l'opérateur insère encore dans un bloc d'E/S")


@pytest.mark.parametrize("op_name", [n for n, _ in _growth_operators()])
def test_input_and_output_block_sizes_are_never_violated(op_name):
    """Les bornes déclarées doivent rester cohérentes avec la matrice, flag ON."""
    fn = dict(_growth_operators())[op_name]
    cfg = MutationConfig()
    cfg.preserve_io_blocks = True
    for s in range(60):
        g = _genome()
        np.random.seed(s)
        fn(g, cfg)
        assert g.W.shape[0] == g.W.shape[1] == g.num_nodes
        assert g.num_inputs + g.num_outputs <= g.num_nodes, (
            f"{op_name} : les blocs se chevauchent (I={g.num_inputs} O={g.num_outputs} N={g.num_nodes})")


@pytest.mark.parametrize("op_name", [n for n, _ in _growth_operators()])
def test_flag_OFF_reproduces_the_legacy_defect(op_name):
    """⚠️ CONTRE-EXEMPLE GELÉ — `off` doit rester le comportement HISTORIQUE.

    Les records EVO-005→023 ont été mesurés avec le défaut. Si ce test tombe, `off` n'est plus
    bit-identique et **tout l'arc devient incomparable** : il faut alors re-mesurer, pas ajuster le test."""
    fn = dict(_growth_operators())[op_name]
    cfg = MutationConfig()          # flag absent -> comportement historique
    assert cfg.preserve_io_blocks is False, "le flag DOIT rester désactivé par défaut"
    desaligne = 0
    TRIALS = 120
    for s in range(TRIALS):
        g = _genome()
        np.random.seed(s)
        fn(g, cfg)
        if not _outputs_still_themselves(g):
            desaligne += 1
    assert desaligne > 0, (
        f"{op_name} : le défaut historique a DISPARU alors que le flag est off. "
        f"`off` n'est plus bit-identique -> les records EVO-005..023 sont incomparables, "
        f"il faut les RE-MESURER (cf. EDR-EVO-024).")
