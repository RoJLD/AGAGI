import pytest

pytest.importorskip("torch")


def test_probe_shapes_smoke():
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0, 1], episodes=40, n_agents=8, K=4, rank=8)
    assert set(r) >= {"plain_median", "bilinear_median", "unlocked", "per_seed",
                      "bar_status", "ceiling_is_proven"}
    assert r["n"] == 2 and len(r["per_seed"]["plain"]) == 2 and len(r["per_seed"]["bilinear"]) == 2
    # ⚠️ P2.15 (2026-09-07) : ce test assertait `isinstance(r["unlocked"], bool)`. La sonde ne CERTIFIE
    # plus tant qu'aucune borne SUPÉRIEURE PROUVÉE du bras incapable n'est déclarée — elle rend `None`
    # et le DIT dans `bar_status`. Un `bool` ici voudrait dire « verdict rendu », ce qui serait un
    # mensonge : le plafond du plain a monté trois fois en une journée (14/36 -> 30/36 -> 34/36).
    assert r["unlocked"] is None and r["bar_status"] in ("CEILING_IS_MINORANT", "UNVALIDATED")
    assert r["ceiling_is_proven"] is False
    # ...et le verdict REDEVIENT un booléen dès qu'une borne prouvée est déclarée : sans ce second
    # volet, « ne certifie jamais » serait indiscernable de « ne sait pas certifier ».
    r2 = run_bilinear_composition_probe(
        seeds=[0], episodes=10, n_agents=4, K=4, rank=8,
        incapable_ceiling=0.30, ceiling_is_proven=True,
        ceiling_provenance="borne superieure PROUVEE par MILP a gap nul, cas de test")
    assert isinstance(r2["unlocked"], bool) and r2["bar_status"] == "SEPARATES_PROVEN"
