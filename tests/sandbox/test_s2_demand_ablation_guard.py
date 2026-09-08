# -*- coding: utf-8 -*-
"""Garde d'arguments et injection du SUJET pour `tools/s2_demand_ablation.py::run_ablation_map`.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde. `run_condition` est
monkeypatché par une sentinelle qui LÈVE au premier appel — donc si une garde tombe, le test le dit
sans construire quoi que ce soit, et le refus doit être INSTANTANÉ (c'est ce qu'on mesure).
"""
import time

import pytest

_LEASE_GUARD_EXEMPT = True


def _sentinelle(*a, **kw):
    raise AssertionError("un monde a été lancé alors que la garde aurait dû refuser AVANT")


def test_run_ablation_map_REFUSE_une_famille_de_mondes_VIDE(monkeypatch):
    """NON-RÉGRESSION (2026-09-07, rétro-application du correctif de `run_s2`) : `worlds or
    list(WORLDS)` traitait une sélection VIDE comme une absence de choix — demander ZÉRO monde lançait
    la grille COMPLÈTE (3 conditions × 5 mondes × K ères). Recensé par AST : 3 sites du dépôt
    portaient cette forme, celui-ci compris."""
    import tools.s2_demand_ablation as M

    monkeypatch.setattr(M, "run_condition", _sentinelle)
    monkeypatch.setattr(M, "load_champion_genome", lambda *a, **k: "G")
    with pytest.raises(ValueError, match="degenere"):
        M.run_ablation_map(worlds=[], K=12)


def test_run_ablation_map_REFUSE_les_arguments_degeneres_AVANT_tout_monde(monkeypatch):
    """La garde doit être EN TÊTE : un refus doit être instantané. On teste OÙ elle est posée, pas
    seulement qu'elle lève — un refus qui coûte une construction de monde n'est pas une garde."""
    import tools.s2_demand_ablation as M

    monkeypatch.setattr(M, "run_condition", _sentinelle)
    monkeypatch.setattr(M, "load_champion_genome", _sentinelle)
    for kw in ({"K": 0}, {"num_agents": 0}, {"max_ticks": 0}):
        t0 = time.perf_counter()
        with pytest.raises(ValueError, match="degenere"):
            M.run_ablation_map(worlds=["stoneage"], **kw)
        assert time.perf_counter() - t0 < 0.5, f"refus trop lent pour {kw} : la garde n'est pas en tête"


def test_run_ablation_map_MESURE_le_sujet_qu_on_lui_donne(monkeypatch):
    """`subject` (2026-09-07) : S6 a montré que le verdict du marqueur est une propriété du SUJET, pas
    du monde — on ne peut donc pas le tester avec un instrument qui ne sait mesurer QUE le champion.
    Réponse connue : le génome passé doit arriver TEL QUEL aux conditions qui portent un sujet, et
    `load_champion_genome` ne doit PAS être appelée."""
    import tools.s2_demand_ablation as M

    vus = []

    def _capture(wcls, cls, genome, seed, **kw):
        vus.append(genome)
        return {"survival": [10.0] * 12, "era_survival": [10.0] * 12,
                "life_score": [1.0] * 12, "era_life": [1.0] * 12}

    monkeypatch.setattr(M, "run_condition", _capture)
    monkeypatch.setattr(M, "load_champion_genome", _sentinelle)   # ne DOIT pas être appelée
    M.run_ablation_map(worlds=["stoneage"], K=12, subject="SUJET-X")

    assert "SUJET-X" in vus, "le sujet demandé n'a pas été mesuré"
    assert vus.count("SUJET-X") == 2, (
        "intact et ablaté doivent porter le MÊME sujet (within-subject) — sinon le contraste "
        f"compare deux sujets différents ; reçu : {vus}")


def test_run_ablation_map_SANS_sujet_reste_le_champion(monkeypatch):
    """Branche négative appariée : par défaut, l'instrument mesure le champion publié — bit-identique
    pour tous les appelants existants. Sans ce cas, le précédent ne distinguerait pas « le sujet est
    injectable » de « le champion a été perdu »."""
    import tools.s2_demand_ablation as M

    vus = []
    monkeypatch.setattr(M, "run_condition",
                        lambda w, c, g, s, **k: (vus.append(g), {"survival": [10.0] * 12,
                                                                 "era_survival": [10.0] * 12,
                                                                 "life_score": [1.0] * 12,
                                                                 "era_life": [1.0] * 12})[1])
    monkeypatch.setattr(M, "load_champion_genome", lambda *a, **k: "CHAMPION-PUBLIE")
    M.run_ablation_map(worlds=["stoneage"], K=12)
    assert "CHAMPION-PUBLIE" in vus and "SUJET-X" not in vus
