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


@pytest.mark.parametrize("arm,choice_decoy", [("RETAIN", True), ("PRESENT", False)])
def test_eval_every_is_an_exact_noop_on_the_measurement(arm, choice_decoy):
    """CALIBRATION (spécificité, forme « no-op EXACT ») : observer la trajectoire ne doit pas la déplacer.

    ⚠️ DEUX CONFIGURATIONS, et c'est délibéré : `("RETAIN", True)` est le design d'ORIGINE, mais les
    balayages tournent en `("PRESENT", False)` — où le préfixe ne porte AUCUN symbole, donc où
    `_prefix_state` ne consomme pas de RNG pour la substitution (`carried is None`). Une garde calibrée
    sur une seule configuration ne dit rien de celle qu'on utilise réellement : c'est la classe E19
    (un réglage validé sur le régime FACILE puis appliqué au régime testé) transposée à un test.

    `eval_every` insère des évaluations DANS la boucle d'entraînement. Le seul canal par lequel elles
    pourraient déplacer la mesure est le RNG — d'où `eval_rng` séparé. La propriété est EXACTE, donc elle
    se teste exactement : `(intact, ablated)` doit être bit-identique à `eval_every=None`.

    ⚠️ POURQUOI TROIS VALEURS ET PAS DEUX. C'est ce qui rend le test capable d'ÉCHOUER. Si l'éval
    périodique consommait `rng` (le flux d'entraînement), chaque réglage en consommerait une quantité
    DIFFÉRENTE — 4 évals à `eval_every=5`, 2 à `eval_every=7`, 0 sans — et les trois résultats
    divergeraient. Avec deux valeurs seulement, un décalage identique passerait inaperçu.
    Contre-exemple gelé : remplacer `eval_rng` par `rng` dans `_train_and_eval_arm` fait échouer ce test.
    """
    from tools.delayed_coordination_demand_probe import _train_and_eval_arm

    kw = dict(D=1, episodes=20, n_agents=4, K=6, V=8, lr=0.05, flip_p=0.0, eval_batches=5,
              choice_decoy=choice_decoy)
    ref_i, ref_a, ref_traj = _train_and_eval_arm(0, arm, eval_every=None, **kw)
    assert ref_traj == [], "sans `eval_every`, aucune trajectoire n'est produite"

    for every, expected_points in ((5, [5, 10, 15, 20]), (7, [7, 14])):
        got_i, got_a, traj = _train_and_eval_arm(0, arm, eval_every=every, **kw)
        assert (got_i, got_a) == (ref_i, ref_a), (
            f"eval_every={every} a DÉPLACÉ la mesure : {(got_i, got_a)} != {(ref_i, ref_a)} — "
            "l'éval périodique fuit dans le RNG d'entraînement")
        assert [p[0] for p in traj] == expected_points, traj
        assert all(0.0 <= v <= 1.0 for _, i, a in traj for v in (i, a)), traj


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
