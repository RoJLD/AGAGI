from src.curriculum.competence import _frac_reaching


def test_frac_reaching_basic():
    stats = [{"mammoth_kills": 1}, {"mammoth_kills": 0}, {"mammoth_kills": 2},
             {"mammoth_kills": 0}, {"mammoth_kills": 0}]
    assert _frac_reaching(stats, "mammoth_kills") == 0.4   # 2/5


def test_frac_reaching_inflation_robust():
    # crédit-groupe (EDR 028) : un agent crédité 5x compte UNE fois (binaire >=1)
    five = [{"mammoth_kills": 5}, {"mammoth_kills": 0}]
    one = [{"mammoth_kills": 1}, {"mammoth_kills": 0}]
    assert _frac_reaching(five, "mammoth_kills") == _frac_reaching(one, "mammoth_kills") == 0.5


def test_frac_reaching_empty_and_missing():
    assert _frac_reaching([], "mammoth_kills") == 0.0
    assert _frac_reaching([{"age": 3}], "mammoth_kills") == 0.0   # champ absent -> 0


def test_frac_reaching_threshold_default_one():
    assert _frac_reaching([{"x": 1}], "x") == 1.0
    assert _frac_reaching([{"x": 0}], "x") == 0.0


from src.curriculum.competence import stoneage_competence


def _pop(frac_hunt, frac_apex, frac_tool, n=1000):
    """Construit n agents reproduisant les fractions de participation demandées."""
    return [{"preys_eaten": 1 if i < int(frac_hunt * n) else 0,
             "mammoth_kills": 1 if i < int(frac_apex * n) else 0,
             "spears_crafted": 1 if i < int(frac_tool * n) else 0} for i in range(n)]


def test_stoneage_floor_when_no_behavior():
    stats = [{"preys_eaten": 0, "mammoth_kills": 0, "spears_crafted": 0} for _ in range(10)]
    assert stoneage_competence(stats) == 0.0


def test_stoneage_live_and_graded_edr096():
    # ANTI-THÉÂTRE : fractions réelles EDR 096 (hunt 0.505, apex 0.217, tool 0.016)
    stats = _pop(0.505, 0.217, 0.016)
    comp = stoneage_competence(stats)
    assert comp > 0.15                                   # non-plancher (vs ancienne ~0.07)
    assert comp > stoneage_competence(_pop(0.505, 0.0, 0.016))  # l'apex compte (strictement >)


def test_stoneage_apex_dominates_hunt():
    # franchir l'apex augmente strictement vs chasse seule
    assert stoneage_competence(_pop(0.5, 0.3, 0.0)) > stoneage_competence(_pop(0.5, 0.0, 0.0))


def test_stoneage_bounded_le_one():
    comp = stoneage_competence(_pop(1.0, 1.0, 1.0))
    assert comp <= 1.0 and abs(comp - 1.0) < 1e-9        # 0.4+0.45+0.15 = 1.0
