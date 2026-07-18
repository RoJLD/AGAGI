import numpy as np

from tools.g_bilinear_probe import (
    _split_temporal, _fit_bilinear, _fit_linear_offline, _ratios_for_predictor,
    _hidden_idx, _verdict_decomposition,
)


def _toy_triples(n, N, M, seed, move=0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        h = rng.standard_normal(N).astype(np.float64)
        dh = h @ M
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
    assert float(np.median(ratios)) < 0.5


def test_linear_offline_recovers_constant_delta():
    N = 4
    c = np.array([1.0, -2.0, 0.5, 3.0])
    triples = [{"H_prev": np.zeros(N), "move": 0, "H_next": c.copy(),
                "g_learned": np.zeros(N)} for _ in range(10)]
    C = _fit_linear_offline(triples, 1, N)
    assert np.allclose(C[0], c)


def test_hidden_idx():
    idx = _hidden_idx(172, 14, 108)
    assert idx[0] == 14 and idx[-1] == 63 and len(idx) == 50


def test_ratios_masked_isolates_dims():
    # dim 0 parfaitement predite (delta connu), dim 1 = pur bruit non predit.
    # FULL melange les deux ; masque sur dim 1 seule -> ratio ~1 (aucune prediction utile).
    test = [{"H_prev": np.array([1.0, 1.0]), "move": 0, "H_next": np.array([2.0, 5.0]),
             "g_learned": np.zeros(2)}]
    pred = lambda tr: np.array([1.0, 0.0])   # predit exactement dim0 (delta=+1), rien sur dim1
    r_full = _ratios_for_predictor(test, pred)                 # (0 + 16)/(1+16) ~ 0.94
    r_hid = _ratios_for_predictor(test, pred, idx=np.array([1]))  # 16/16 = 1.0
    assert r_hid[0] == 1.0 and r_full[0] < 1.0


def test_verdict_encoding_artifact():
    # FULL fidele (both), HIDDEN neutre (both >=0.95) -> ARTIFACT
    fid = [0.4, 0.5, 0.3, 0.45, 0.5]
    neu = [1.0, 1.01, 0.99, 1.0, 1.0]
    assert _verdict_decomposition(fid, fid, neu, neu) == "ENCODING_ARTIFACT"


def test_verdict_latent_bilinear():
    # HIDDEN : bilin fidele ET bat learned -> LATENT_BILINEAR
    learned_h = [0.9, 0.85, 0.92, 0.88, 0.9]
    bilin_h = [0.4, 0.5, 0.3, 0.45, 0.5]
    fid = [0.5, 0.5, 0.5, 0.5, 0.5]
    assert _verdict_decomposition(fid, fid, learned_h, bilin_h) == "LATENT_BILINEAR"


def test_verdict_latent_linear():
    # HIDDEN : learned fidele, bilin NE bat PAS -> LATENT_LINEAR
    learned_h = [0.4, 0.5, 0.3, 0.45, 0.5]
    bilin_h = [0.6, 0.65, 0.55, 0.6, 0.6]
    fid = [0.5, 0.5, 0.5, 0.5, 0.5]
    assert _verdict_decomposition(fid, fid, learned_h, bilin_h) == "LATENT_LINEAR"


from tools.g_bilinear_probe import main_bilinear_check


def test_smoke_decomposition_returns_verdict():
    res = main_bilinear_check(seeds=(0,), warmup=30, measure=90, _return=True)
    assert res["verdict"] in {"ENCODING_ARTIFACT", "LATENT_BILINEAR", "LATENT_LINEAR", "PARTIAL", "NO_DATA"}
    assert "med_learned_hidden" in res and "med_bilin_hidden" in res
