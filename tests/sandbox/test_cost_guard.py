"""Garde EXÉCUTABLE de la classe E13 — « dépassement de coût non borné au design ».

E13 était la dernière classe du registre sans aucune garde (backlog P3.2). Sa preuve : 4 runs abandonnés,
dont un le 2026-07-27 (EVO-007, 187 min pour 8 seeds sur 36, tué). Ce dernier a montré que la formulation
du backlog — « débit mesuré au smoke + coût projeté » — est **insuffisante** : le débit mesuré était juste
et le run a quand même explosé, parce que le coût dépend du SEED (il suit le succès évolutif). Il faut
donc DEUX gardes, une avant et une pendant, et ces tests vérifient que chacune échoue quand elle le doit.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.cost_guard import (  # noqa: E402
    CostGuard, CostExceeded, project_cost, CostTooHighToStart)


class _Clock:
    """Horloge injectée : les tests d'une garde temporelle ne doivent pas DORMIR."""

    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_projection_accepts_a_tenable_design():
    assert project_cost(unit_s=35.0, n_units=36, budget_s=7200) == pytest.approx(35 * 36 * 3)


def test_projection_REFUSES_before_launching_anything():
    """⚠️ Le cas qui compte : le refus doit arriver AVANT le run, pas après 187 minutes."""
    with pytest.raises(CostTooHighToStart):
        project_cost(unit_s=35.0, n_units=36, budget_s=1200, label="EVO-007")


def test_projection_safety_margin_is_what_catches_the_tail():
    """Sans marge, 36 × 35 s = 21 min passerait sous un budget de 30 min — et c'est exactement le calcul
    que j'ai fait avant EVO-007. La marge ×3 est là parce que le coût par unité est mesuré sur des unités
    TYPIQUES, jamais sur la pire."""
    # 36 × 35 s = 1260 s (21 min). Budget 30 min : sans marge ça passe — c'est EXACTEMENT le calcul que
    # j'avais fait avant EVO-007. Avec la marge ×3 (3780 s = 63 min) le design est refusé.
    project_cost(unit_s=35.0, n_units=36, budget_s=1800, safety=1.0)
    with pytest.raises(CostTooHighToStart):
        project_cost(unit_s=35.0, n_units=36, budget_s=1800, safety=3.0)


def test_guard_raises_once_the_budget_is_crossed():
    c = _Clock()
    g = CostGuard(budget_s=100, label="seed 8", clock=c)
    c.t = 99.0
    g.tick()                                   # sous le budget : ne lève pas
    c.t = 101.0
    with pytest.raises(CostExceeded) as e:
        g.tick()
    assert e.value.label == "seed 8" and e.value.spent_s == pytest.approx(101.0)


def test_guard_reports_what_it_cost_so_the_abort_can_be_COUNTED():
    """Un abandon silencieux est un biais de sélection sur les résultats : l'exception doit porter de quoi
    le rapporter (unité, temps consommé, budget)."""
    c = _Clock()
    g = CostGuard(budget_s=10, label="bras control", clock=c)
    c.t = 42.0
    with pytest.raises(CostExceeded) as e:
        g.tick()
    assert "bras control" in str(e.value) and "42" in str(e.value)


def test_would_exceed_allows_a_clean_abort_without_exception():
    c = _Clock()
    g = CostGuard(budget_s=10, clock=c)
    assert not g.would_exceed()
    c.t = 11.0
    assert g.would_exceed()
