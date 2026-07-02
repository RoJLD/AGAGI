import numpy as np

from tools.g_bilinear_probe import (
    _split_temporal, _fit_bilinear, _fit_linear_offline, _ratios_for_predictor, _verdict_bilinear,
)


def _toy_triples(n, N, M, seed, move=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        h = rng.standard_normal(N).astype(np.float64)
        dh = h @ M                      # transition VRAIMENT bilineaire (etat-dependante)
        out.append({"H_prev": h, "move": move, "H_next": h + dh,
                    "g_learned": np.zeros(N, dtype=np.float64)})
    return out


def test_split_temporal_proportions():
    tr = [{"move": 0} for _ in range(10)] + [{"move": 1} for _ in range(10)]
    train, test = _split_temporal(tr, 2, frac=0.7)
    assert len(train) == 14 and len(test) == 6


def test_bilinear_fits_state_dependent_map():
    N = 6
    rng = np.random.default_rng(0)
    M = rng.standard_normal((N, N)) * 0.2
    triples = _toy_triples(120, N, M, seed=1)
    train, test = _split_temporal(triples, 1, frac=0.7)
    W = _fit_bilinear(train, 1, N, lam=1e-3)
    ratios = _ratios_for_predictor(test, lambda tr: tr["H_prev"] @ W[tr["move"]])
    # transition purement bilineaire -> le fit doit ecraser la baseline
    assert float(np.median(ratios)) < 0.5


def test_linear_offline_recovers_constant_delta():
    N = 4
    c = np.array([1.0, -2.0, 0.5, 3.0])
    triples = [{"H_prev": np.zeros(N), "move": 0, "H_next": c.copy(),
                "g_learned": np.zeros(N)} for _ in range(10)]
    C = _fit_linear_offline(triples, 1, N)
    assert np.allclose(C[0], c)


def test_verdict_bilinear_fidele():
    # bilineaire fidele (ratios<1) ET bat le learned (median plus bas)
    assert _verdict_bilinear([0.4, 0.5, 0.3, 0.45, 0.5], [1.0, 1.0, 0.98, 1.02, 1.0]) == "BILINEAR_FIDELE"


def test_verdict_bilinear_neutral():
    assert _verdict_bilinear([1.0, 1.01, 0.99, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0, 1.0]) == "BILINEAR_NEUTRAL"


def test_verdict_bilinear_partial():
    # fidele mais NE bat PAS le learned (learned median plus bas)
    assert _verdict_bilinear([0.4, 0.5, 0.3, 0.45, 0.5], [0.1, 0.1, 0.1, 0.1, 0.1]) == "PARTIAL"


from tools.g_bilinear_probe import main_bilinear_check


def test_smoke_bilinear_returns_verdict():
    res = main_bilinear_check(seeds=(0,), warmup=30, measure=60, _return=True)
    assert res["verdict"] in {"BILINEAR_FIDELE", "BILINEAR_NEUTRAL", "PARTIAL", "NO_DATA"}
    assert "median_bilin" in res
