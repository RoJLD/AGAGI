"""Smoke de FORME de la sonde Lewis DIFFÉRÉE (DELAYED-COORD, Task 2).

Ne teste PAS la science (c'est le crible fail-fast + la calibration de Task 3 qui le font) : seulement
que les deux bras tournent, renvoient des accuracies bornées et exposent `_params`, et que le levier
`choice_decoy` fait EXACTEMENT ce que sa docstring annonce (défaut inchangé ; un seul tick mis à zéro).
"""
import numpy as np
import pytest

pytest.importorskip("torch")


def test_probe_returns_both_arms_smoke():
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe
    r = run_delayed_coordination_demand_probe(seeds=[0, 1], D=1, episodes=30, n_agents=4, K=6, V=8)
    for arm in ("RETAIN", "PRESENT"):
        assert len(r[arm + "_intact"]) == 2, r
        assert len(r[arm + "_ablated"]) == 2, r
        for v in r[arm + "_intact"] + r[arm + "_ablated"]:
            assert 0.0 <= v <= 1.0, r
    assert r["n"] == 2
    assert r["_params"]["D"] == 1
    assert r["_params"]["choice_decoy"] is True          # défaut = design d'origine


_D, _V, _I, _N = 2, 8, 12, 4
_SIG_FIRST = np.array([1, 2, 3])
_SIG_LAST = np.array([4, 5, 6])


def _seq(arm, choice_decoy):
    from tools.delayed_coordination_demand_probe import _receiver_seq
    return _receiver_seq(arm, _SIG_FIRST, _SIG_LAST, _V, _I, len(_SIG_FIRST), _D, choice_decoy)


@pytest.mark.parametrize("arm", ["RETAIN", "PRESENT"])
def test_choice_decoy_default_presents_both_symbols(arm):
    """Défaut : séquence D+2, un symbole aux DEUX dates, symbole porté à l'index 0 (design d'origine)."""
    seq, carried = _seq(arm, True)
    assert len(seq) == _D + 2
    assert carried == 0
    assert seq[0][np.arange(3), _SIG_FIRST % _V].tolist() == [1.0, 1.0, 1.0]
    assert seq[-1][np.arange(3), _SIG_LAST % _V].tolist() == [1.0, 1.0, 1.0]
    assert all(not x.any() for x in seq[1:-1])           # ticks de délai = nuls


@pytest.mark.parametrize("arm,zeroed,kept,carried", [("RETAIN", -1, 0, 0), ("PRESENT", 0, -1, None)])
def test_choice_decoy_false_zeroes_only_the_decoy_tick(arm, zeroed, kept, carried):
    """`choice_decoy=False` : le tick du LEURRE devient nul, TOUT le reste est inchangé.

    Le leurre est au tick de CHOIX dans RETAIN (`last = decoy`) et au tick 0 dans PRESENT
    (`first = decoy`) — d'où l'inversion des index. La longueur reste D+2 : une seule variable change.
    `carried is None` pour PRESENT = plus aucun symbole dans le préfixe (l'ablation y est un no-op)."""
    ref, _ = _seq(arm, True)
    seq, got_carried = _seq(arm, False)
    assert len(seq) == _D + 2                            # longueur INCHANGÉE (pas un tick retiré)
    assert got_carried == carried
    assert not seq[zeroed].any(), "le tick du leurre doit être un vecteur NUL"
    assert np.array_equal(seq[kept], ref[kept]), "le tick de la CIBLE doit être inchangé"
    assert all(not x.any() for x in seq[1:-1])


def test_prefix_ablation_is_exact_noop_without_carried_symbol():
    """`carried_idx is None` -> `deranged` ne change RIEN et ne consomme même pas le RNG.
    C'est la conséquence documentée du levier : sous `choice_decoy=False`, l'ablation de PRESENT est
    un no-op EXACT, donc son critère « contrôle inerte » est VACUEUX et ne doit pas être lu comme un pass."""
    from tools.delayed_coordination_demand_probe import _prefix_state

    class _Stub:
        N = _N

        def __init__(self):
            self.seen, self.H = [], None

        def forward(self, x):
            self.seen.append(np.asarray(x).copy())
            return None, 0

    prefix = [np.zeros((3, _I), dtype=np.float32) for _ in range(2)]
    runs = []
    for deranged in (False, True):
        stub, rng = _Stub(), np.random.RandomState(7)
        _prefix_state(stub, prefix, None, _V, _I, 3, deranged, rng)
        runs.append((stub.seen, rng.get_state()[2]))
    assert len(runs[0][0]) == len(prefix)
    assert all(np.array_equal(a, b) for a, b in zip(runs[0][0], runs[1][0]))
    assert runs[0][1] == runs[1][1], "le RNG ne doit pas être consommé quand il n'y a rien à substituer"
