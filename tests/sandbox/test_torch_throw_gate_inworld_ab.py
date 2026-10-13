import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# P2.169 (2026-10-13) — GARDE TORCH, par test. Ces tests construisent le backend torch par le harnais
# (src/agents/backend_torch.py lève NotImplementedError sans torch), sans importer torch eux-mêmes : la CI, qui n'a
# pas torch, les rendait ROUGES d'environnement — invisibles jusqu'à P2.165, le filet de bail fuité les sautant depuis
# le 2026-09-16. Mesurés VERTS avec torch avant d'être gardés (P2.169). Les autres tests du fichier tournent en CI.
import importlib.util  # noqa: E402
import pytest  # noqa: E402
_TORCH = importlib.util.find_spec("torch") is not None
requires_torch = pytest.mark.skipif(not _TORCH, reason="torch absent : le harnais construit le backend torch "
                                    "(src/agents/backend_torch.py) — P2.169")


@requires_torch
def test_run_arm_smoke_keys_and_bounds():
    from tools.torch_throw_gate_inworld_ab import run_arm
    r = run_arm(shuffle=False, seed=0, ticks=40, warmup=20, n_agents=8)
    for k in ("shuffle", "seed", "binding_gap_inworld", "kills_with_tool",
              "spear_n", "nospear_n", "throw_rate"):
        assert k in r
    assert -1.0 <= r["binding_gap_inworld"] <= 1.0
    assert 0.0 <= r["throw_rate"] <= 1.0
    assert r["kills_with_tool"] >= 0


def test_verdict_pure_true_binds_more():
    from tools.substrate_ab import compute_ab_verdict
    rows = [{"diff": d} for d in (0.30, 0.25, 0.40, 0.32, 0.28, 0.35)]   # gap ON - gap SHUFFLE > 0
    v = compute_ab_verdict(rows, band=0.02)
    assert v["verdict"] == "GRADIENT_GAGNE" and v["n"] == 6
