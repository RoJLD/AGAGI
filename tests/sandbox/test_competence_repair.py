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
