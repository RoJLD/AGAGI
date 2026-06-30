from tools.competence_profile import _tier_fractions, _verdict_craft_wall


def test_measure_profile_fixed_cohort_no_repro():
    # benchmark_mode -> pas de reproduction -> pool = cohorte initiale (pas d'explosion) + cles presentes.
    from tools.competence_profile import _measure_profile
    from tools.map_elites_compare import _make_cfg
    from src.agents.mamba_agent import MambaAgent
    genomes = [MambaAgent().genome for _ in range(3)]
    stats = _measure_profile(_make_cfg(), genomes, max_ticks=40, disable_repro=True)
    assert len(stats) == 3, "cohorte fixe : pas de naissances (pool = genomes initiaux)"
    assert all(k in stats[0] for k in ("age", "preys_eaten", "spears_crafted", "mammoth_kills"))


def test_main_competence_profile_smoke():
    from tools.competence_profile import main_competence_profile
    r = main_competence_profile(R=1, eras=2, num_agents=10, max_ticks=80, seed=99240, _return=True)
    assert r["verdict"] in ("CRAFT_WALL CONFIRME", "ECHELLE MONOTONE", "INDETERMINE")
    assert len(r["per_seed"]) == 1


def test_tier_fractions_binary_per_agent():
    stats = [
        {"preys_eaten": 3, "spears_crafted": 0, "mammoth_kills": 1},
        {"preys_eaten": 1, "spears_crafted": 0, "mammoth_kills": 0},
        {"preys_eaten": 0, "spears_crafted": 1, "mammoth_kills": 0},
        {"preys_eaten": 0, "spears_crafted": 0, "mammoth_kills": 0},
    ]
    f = _tier_fractions(stats)
    assert f["frac_forage"] == 0.5   # 2/4 ont preys_eaten >= 1
    assert f["frac_craft"] == 0.25   # 1/4
    assert f["frac_apex"] == 0.25    # 1/4
    assert f["n"] == 4


def test_verdict_craft_wall_branches():
    confirme = {"frac_forage": 0.80, "frac_craft": 0.02, "frac_apex": 0.22}
    assert _verdict_craft_wall(confirme) == "CRAFT_WALL CONFIRME"
    monotone = {"frac_forage": 0.80, "frac_craft": 0.30, "frac_apex": 0.10}  # apex < craft
    assert _verdict_craft_wall(monotone) == "ECHELLE MONOTONE"
    indet = {"frac_forage": 0.05, "frac_craft": 0.0, "frac_apex": 0.0}
    assert _verdict_craft_wall(indet) == "INDETERMINE"
