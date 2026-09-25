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
    CostGuard, CostExceeded, Stopwatch, project_cost, CostTooHighToStart)


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


# ---- P2.78 : la garde de queue porte sur le CPU, le mur est publié à côté ----------------------------------
def test_default_gated_clock_is_process_cpu_and_wall_is_published_beside_it():
    import time
    g = CostGuard(budget_s=1.0)
    assert g._clock is time.process_time and g._wall is time.monotonic and g.gated_on == "cpu"
    r = g.report()
    assert set(r) == {"spent_s", "spent_wall_s", "gated_on", "wall_over_cpu"} and r["spent_s"] >= 0.0 and r["spent_wall_s"] >= 0.0


def test_a_machine_suspension_does_NOT_kill_the_unit_but_is_READABLE_in_the_report():
    """Le cas de P4.9 (33 060 s de mur) et de DECOMP (510 334 s) : le mur explose, le CPU non. La garde ne
    lève pas ; le rapport montre le rapport mur/CPU."""
    cpu, mur = _Clock(), _Clock()
    g = CostGuard(budget_s=10, label="seed dormeur", clock=cpu, wall_clock=mur)
    cpu.t, mur.t = 5.0, 5000.0
    g.tick()                                   # 5 s de CPU sous un budget de 10 s : rien ne lève
    assert not g.would_exceed()
    r = g.report()
    assert r["spent_s"] == 5.0 and r["spent_wall_s"] == 5000.0 and r["gated_on"] == "injected" and r["wall_over_cpu"] is None
    cpu.t = 11.0                               # le CPU franchit : la garde lève, ET dit le mur à côté
    with pytest.raises(CostExceeded) as e:
        g.tick()
    assert e.value.spent_s == 11.0 and e.value.spent_wall_s == 5000.0 and "mur 5000.0s" in str(e.value)


def test_wall_over_cpu_is_computed_only_on_a_cpu_gated_guard_and_never_divides_by_zero():
    import time
    g = CostGuard(budget_s=1.0, clock=time.process_time, wall_clock=time.monotonic)
    r = g.report()
    assert r["gated_on"] == "cpu" and (r["wall_over_cpu"] is None or r["wall_over_cpu"] > 0.0)
    h = CostGuard(budget_s=1.0, clock=time.monotonic)
    assert h.gated_on == "wall" and h.report()["wall_over_cpu"] is None


def test_stopwatch_publishes_wall_AND_cpu_and_predicts_the_ratio_exactly():
    mur, cpu = _Clock(), _Clock()
    sw = Stopwatch(wall_clock=mur, cpu_clock=cpu)
    mur.t, cpu.t = 600.0, 120.0
    assert sw.elapsed() == {"elapsed_s": 600.0, "elapsed_cpu_s": 120.0, "wall_over_cpu": 5.0}
    cpu.t = 0.0
    assert sw.elapsed()["wall_over_cpu"] is None       # CPU nul : pas de ratio fabriqué
    real = Stopwatch().elapsed()
    assert real["elapsed_s"] >= 0.0 and real["elapsed_cpu_s"] >= 0.0


# ---- P2.110 : POURQUOI le cliquet coupe, PAR LIGNE, et la marge des DEUX côtés du seuil ----------------------------
# Constantes FIGÉES en littéraux, jamais relues depuis results/ (M-M10) : l'histoire de TD-STEP-PILOT-R2.
#   passe 1 (commit f2d017fd) : unité 217.44147491455078 s sur `lam099|lr=4.0|seed=1`, 107 unités restantes ;
#   reprise (commit 3d7c22b3) : unité 196.35169649124146 s sur `lam05|lr=2.0|seed=1`, 95 unités restantes.
# Règle scellée docs/preregistrations/TD-STEP-PILOT-R2.json : budget 14 400 s, marge 1,5.
import math  # noqa: E402

from tools.cost_guard import (  # noqa: E402
    COEURS_EXTERIEURS_LIBRE_MAX, NATURES_COUPE, LoadWindow, classify_cut_nature, cost_per_arm, cut_geometry,
    cut_record, margin_to_budget, project_cost_per_arm)

U_PASSE1, U_REPRISE, BUDGET, SAFETY = 217.44147491455078, 196.35169649124146, 14400, 1.5
D_LR1 = cut_geometry(U_PASSE1, 107, BUDGET, SAFETY)["depassement"]      # lr 1,0 coupée à 107 unités : 2,42 × le budget
D_LR2 = cut_geometry(U_PASSE1, 47, BUDGET, SAFETY)["depassement"]       # lr 2,0 coupée à 47 unités : 1,065 × le budget


def test_natures_coupe_is_a_CLOSED_vocabulary_and_an_unknown_nature_is_refused_loudly():
    """`indeterminee`, jamais `budget` (I-VOCAB-BUDGET) : TOUTE coupe est causée par le budget ; le libellé de la charge
    NON mesurée doit dire l'absence, pas ressembler à une cause de fond (biais « absence -> affirmation », CLAUDE.md)."""
    assert NATURES_COUPE == ("contention", "structure", "indeterminee")
    base = dict(raison="r", lr=1.0, cles=["k"], unit_s=U_PASSE1, n_units=107, budget_s=BUDGET, safety=SAFETY)
    assert cut_record(nature="structure", **base)["nature"] == "structure"
    for faux in ("budget", "STRUCTURE", "", None):
        with pytest.raises(ValueError):
            cut_record(nature=faux, **base)
    with pytest.raises(ValueError):
        cut_record(nature="contention", **dict(base, raison=""))          # une coupe sans raison n'est pas publiée


def test_cut_geometry_publishes_BOTH_sides_of_the_threshold_on_the_first_pass_of_R2():
    """M-M7 / I-FRAGILITE-MARGE : la fragilité de P2.110 (« à 6 % de son seuil ») était dans la projection REFUSÉE de
    la ligne lr 2,0 (47 unités, 1,065 × le budget), pas dans la projection acceptée (marge 0,751). Chaque ligne coupée
    porte donc sa projection refusée, son dépassement et l'unité de BASCULE en dessous de laquelle elle serait gardée."""
    g1, g2 = cut_geometry(U_PASSE1, 107, BUDGET, SAFETY), cut_geometry(U_PASSE1, 47, BUDGET, SAFETY)
    assert g1["projection_si_gardee_s"] == U_PASSE1 * 107 * SAFETY          # MÊME expression que project_cost
    assert g1["depassement"] == pytest.approx(2.4235, abs=1e-4) and g2["depassement"] == pytest.approx(1.0646, abs=1e-4)
    assert g1["unite_de_bascule_s"] == pytest.approx(89.720, abs=1e-3) and g2["unite_de_bascule_s"] == pytest.approx(204.255, abs=1e-3)
    assert g2["marge"] == pytest.approx(-0.0646, abs=1e-4) and g2["marge"] < 0     # négative : au-dessus du seuil
    # l'unité LIBRE de la reprise (196,35 s) est SOUS la bascule de lr 2,0 et au-dessus de celle de lr 1,0 : c'est
    # toute l'histoire de la passe 1, lisible sur deux nombres publiés.
    assert g1["unite_de_bascule_s"] < U_REPRISE < g2["unite_de_bascule_s"] < U_PASSE1
    with pytest.raises(ValueError):
        cut_geometry(U_PASSE1, 0, BUDGET, SAFETY)                            # une ligne vide n'a pas de bascule


def test_margin_to_budget_on_the_accepted_projection_and_its_refusals():
    assert margin_to_budget(3587.784336090088, BUDGET) == pytest.approx(0.7508, abs=1e-4)      # passe 1, 11 unités
    assert margin_to_budget(10308.464065790176, BUDGET) == pytest.approx(0.2841, abs=1e-4)     # reprise, 35 unités
    for mauvais in ((1.0, 0.0), (1.0, -5.0), (float("nan"), BUDGET), (1.0, float("nan")), (float("inf"), BUDGET)):
        with pytest.raises(ValueError):
            margin_to_budget(*mauvais)


def test_project_cost_REFUSES_a_nan_or_negative_unit_instead_of_passing_it_silently():
    """M-M8 / I-NAN-UNITE (E1, forme (b)) : `nan > budget` vaut False — une unité NaN (médiane d'un bras vide) passait
    la garde SANS exception, qui ne pouvait donc pas échouer. Aucune unité légitime n'est NaN ni négative : le durcissement
    ne change aucune décision légitime (l'unité 0 reste acceptée, elle n'est pas un défaut fabriqué)."""
    for u, n in ((float("nan"), 107), (-5.0, 107), (U_PASSE1, -1)):
        with pytest.raises(ValueError):
            project_cost(unit_s=u, n_units=n, budget_s=BUDGET, safety=SAFETY)
    assert project_cost(unit_s=0.0, n_units=107, budget_s=BUDGET, safety=SAFETY) == 0.0
    assert project_cost(unit_s=U_PASSE1, n_units=11, budget_s=BUDGET, safety=SAFETY) == 3587.784336090088


def test_project_cost_per_arm_sums_exactly_and_equals_project_cost_on_a_single_arm():
    assert project_cost_per_arm({"lam05": U_PASSE1}, {"lam05": 11}, BUDGET, safety=SAFETY) == \
        project_cost(unit_s=U_PASSE1, n_units=11, budget_s=BUDGET, safety=SAFETY) == 3587.784336090088
    # grille hétérogène de P2.110 (ii) : lam05 161,9 s, lam099 157,6 s, td0_d0 56,2 s (2,8×) -- valeurs à dose CONNUE
    p = project_cost_per_arm({"lam05": 161.9, "lam099": 157.6, "td0_d0": 56.2}, {"lam05": 12, "lam099": 12, "td0_d0": 12},
                             BUDGET, safety=SAFETY)
    assert p == pytest.approx((161.9 + 157.6 + 56.2) * 12 * SAFETY)
    assert project_cost_per_arm({"a": 10.0}, {"a": 3, "b": 0}, 1e9, safety=1.0) == 30.0     # n = 0 : aucune unité exigée


def test_cost_per_arm_is_the_NON_raising_computation_and_details_every_arm():
    """M-M9 : le calcul pur (publiable à côté d'une décision, sans jamais l'interrompre) est séparé du barrage."""
    c = cost_per_arm({"lent": 200.0, "rapide": 50.0}, {"lent": 10, "rapide": 10}, safety=2.0)
    assert c == {"projection_s": 5000.0, "par_bras": {"lent": 4000.0, "rapide": 1000.0}}
    with pytest.raises(CostTooHighToStart) as e:
        project_cost_per_arm({"lent": 200.0, "rapide": 50.0}, {"lent": 10, "rapide": 10}, 4000.0, safety=2.0, label="X")
    assert "lent" in str(e.value) and "rapide" in str(e.value) and "X" in str(e.value)


@pytest.mark.parametrize("units,ns", [
    ({}, {}),                                          # rien à projeter : refus, jamais 0.0 (porte 14 ne voit pas sum)
    ({"a": 10.0}, {"a": 3, "b": 2}),                   # bras SANS unité mesurée : jamais une unité par défaut
    ({"a": float("nan")}, {"a": 3}),                   # médiane d'un bras vide
    ({"a": 0.0}, {"a": 3}),                            # unité nulle pour un bras à mesurer : un défaut fabriqué
    ({"a": -1.0}, {"a": 3}),
    ({"a": None}, {"a": 3}),
    ({"a": 10.0}, {"a": -1}),
    ({"a": 10.0}, {"a": 2.5}),
    ({"a": 10.0}, {"a": True}),
])
def test_project_cost_per_arm_refuses_every_degenerate_input(units, ns):
    with pytest.raises(ValueError):
        cost_per_arm(units, ns, safety=SAFETY)
    with pytest.raises(ValueError):
        project_cost_per_arm(units, ns, 1e12, safety=SAFETY)


# ---- la charge EXTÉRIEURE, intégrée sur la fenêtre de la cellule (M-M4, I-A1) ----------------------------------------
def _fenetre(ext, propres, lecteur_fixe=None):
    """Horloges injectées : `propres` cœurs pour le processus, `ext` cœurs pour les autres -- dose CONNUE."""
    clk = _Clock()
    busy = (lambda: lecteur_fixe) if lecteur_fixe is not None else (lambda: (ext + propres) * clk.t)
    lw = LoadWindow(busy_reader=busy, cpu_clock=lambda: propres * clk.t, wall_clock=clk)
    return clk, lw


def test_load_window_subtracts_its_OWN_load_exactly_and_predicts_a_known_exterior_dose():
    """No-op EXACT : un processus qui brûle seul ses cœurs ne se compte pas comme charge extérieure (une boucle mono-thread
    qui s'auto-déclarerait « contention » ne pourrait jamais certifier une machine libre). Puis prédiction : la dose
    extérieure injectée est rendue à l'identique, à toute dose."""
    for propres in (0.0, 0.94, 1.8):
        clk, lw = _fenetre(0.0, propres)
        clk.t = 200.0
        r = lw.close()
        assert r["coeurs_exterieurs"] == pytest.approx(0.0, abs=1e-12) and r["mur_s"] == 200.0
    for ext in (0.5, 3.0, 12.0, 18.5):
        clk, lw = _fenetre(ext, 0.94)
        clk.t = 217.0
        r = lw.close()
        assert r["coeurs_exterieurs"] == pytest.approx(ext) and r["coeurs_propres"] == pytest.approx(0.94)


def test_load_window_says_I_DO_NOT_KNOW_and_never_fabricates_a_zero():
    """Porte 14 : `len(project_processes())` rendait 0 quand psutil manquait -- une machine illisible passait pour libre.
    Ici toute source illisible rend None pour CE champ (jamais 0.0), et le mur reste publié."""
    def leve():
        raise OSError("compteur illisible")
    clk = _Clock()
    for lecteur in (leve, lambda: None, lambda: float("nan")):
        lw = LoadWindow(busy_reader=lecteur, cpu_clock=clk, wall_clock=clk)
        clk.t += 100.0
        r = lw.close()
        assert r["coeurs_exterieurs"] is None and r["mur_s"] == 100.0
    clk, lw = _fenetre(3.0, 1.0)                                  # fenêtre de mur NUL : aucun ratio fabriqué
    r = lw.close()
    assert r["coeurs_exterieurs"] is None and r["coeurs_propres"] is None


def test_the_real_busy_reader_is_readable_on_this_machine_and_None_without_psutil(monkeypatch):
    """Garde de la garde : si la formule (celle de psutil `_cpu_busy_time`, recopiée sans l'API privée) cessait de lire,
    toutes les charges deviendraient None EN SILENCE et aucune coupe ne serait jamais qualifiée."""
    from tools.cost_guard import _system_busy_cpu_s
    v = _system_busy_cpu_s()
    assert isinstance(v, float) and math.isfinite(v) and v > 0.0
    monkeypatch.setitem(sys.modules, "psutil", None)               # import psutil -> ImportError
    assert _system_busy_cpu_s() is None


def test_the_free_machine_threshold_is_declared_in_CORES_not_borrowed_from_the_PM_alert():
    """I-CPU80 : le seuil A5 du PM (80 % instantané) est une ALERTE de saturation (17,6 cœurs sur 22) ; réutilisé comme
    CERTIFICAT de machine libre, une machine à 79 % passerait libre. Le seuil d'ici est en cœurs extérieurs INTÉGRÉS,
    déclaré provisoire -- la réponse connue reste la réplication d'une cellule bit-identique."""
    assert isinstance(COEURS_EXTERIEURS_LIBRE_MAX, float) and 0.0 < COEURS_EXTERIEURS_LIBRE_MAX < 22 * 0.80
    import tools.cost_guard as cg
    assert "provisoire" in cg.__dict__["COEURS_EXTERIEURS_LIBRE_MAX_PROVENANCE"].lower()


# ---- classify_cut_nature : nature d'UNE LIGNE coupée -- calibration à réponse connue ---------------------------------
# Déclaration : tests/sandbox/test_instrument_calibration.py::CALIBRATED["tools/cost_guard.py::classify_cut_nature"].
SEUIL = COEURS_EXTERIEURS_LIBRE_MAX


def test_nature_unknown_load_is_indeterminee_measured_load_is_contention_free_machine_is_structure():
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=None) == "indeterminee"
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=float("nan")) == "indeterminee"      # nan DIT « je ne sais pas »
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=SEUIL + 0.5) == "contention"
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=SEUIL - 0.5) == "structure"
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=SEUIL) == "structure"                 # seuil INCLUS : libre


def test_nature_is_decided_PER_LINE_two_lines_of_the_SAME_pass_can_differ():
    """M-M1 / I-A4 (le cas qui motive P2.110 (i)) : les deux lignes de la passe 1 ont été coupées sur la MÊME unité ; un
    classifieur de la MESURE leur rend forcément la même nature. Par ligne, la bande de contamination DÉCLARÉE les
    sépare : lr 1,0 (2,42 × le budget) tient même si l'unité était gonflée de 90 % ; lr 2,0 (1,065 ×) non."""
    charge = SEUIL + 4.0                                           # unité mesurée sous charge
    assert [classify_cut_nature(d, coeurs_exterieurs=charge, bande_contamination=0.9) for d in (D_LR1, D_LR2)] == \
        ["structure", "contention"]
    assert [classify_cut_nature(d, coeurs_exterieurs=None, bande_contamination=0.9) for d in (D_LR1, D_LR2)] == \
        ["structure", "indeterminee"]
    # SANS bande déclarée, pas de voie par la marge : même nature pour les deux (on ne devine pas la contamination)
    assert {classify_cut_nature(d, coeurs_exterieurs=charge) for d in (D_LR1, D_LR2)} == {"contention"}


def test_nature_by_REPLICATION_of_the_same_cell_is_the_known_answer():
    """M-M6 / I-REQUALIF (CLAUDE.md : « la charge se mesurant par la réplication d'une cellule bit-identique ») : la MÊME
    cellule re-chronométrée machine libre. Si elle coupe encore la ligne -> structure ; sinon la coupe venait de l'écart
    de chronométrage de la même computation -> contention ÉTABLIE. Une réplique elle-même chargée ne prouve rien."""
    charge = SEUIL + 4.0
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=charge, depassement_replique=1.02,
                               coeurs_exterieurs_replique=SEUIL - 1.0) == "structure"
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=charge, depassement_replique=0.96,
                               coeurs_exterieurs_replique=SEUIL - 1.0) == "contention"
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=None, depassement_replique=0.96,
                               coeurs_exterieurs_replique=SEUIL - 1.0) == "contention"
    for rep_chargee in (SEUIL + 1.0, None):                        # réplique chargée ou illisible : ignorée
        assert classify_cut_nature(D_LR2, coeurs_exterieurs=None, depassement_replique=0.96,
                                   coeurs_exterieurs_replique=rep_chargee) == "indeterminee"


def test_nature_hypothetical_replica_at_the_reprise_unit_would_split_the_first_pass():
    """HYPOTHÉTIQUE, nommé comme tel (M-M2 : aucune charge fabriquée présentée comme historique) : SI 196,35 s avait été
    la réplique LIBRE de la cellule d'unité de la passe 1, la classification rendrait {lr 1,0 : structure ; lr 2,0 :
    contention} -- ce que le record affirme. Les dépassements sous 196,35 s viennent de nombres committés."""
    libre = SEUIL - 3.0
    d_rep = {lr: cut_geometry(U_REPRISE, n, BUDGET, SAFETY)["depassement"] for lr, n in ((1.0, 107), (2.0, 47))}
    assert d_rep[1.0] > 1.0 >= d_rep[2.0]
    assert classify_cut_nature(D_LR1, coeurs_exterieurs=None, depassement_replique=d_rep[1.0],
                               coeurs_exterieurs_replique=libre) == "structure"
    assert classify_cut_nature(D_LR2, coeurs_exterieurs=None, depassement_replique=d_rep[2.0],
                               coeurs_exterieurs_replique=libre) == "contention"


def test_nature_on_the_LITERAL_history_of_R2_is_indeterminee_it_does_NOT_confirm_the_record():
    """M-M2 / I-A4 : l'entrée RÉELLE. Le JSON committé ne publie AUCUNE charge ; le record dit « 0 bail / 0 processus »,
    jamais un CPU, et l'unité de la reprise est une AUTRE cellule (lam05|lr=2.0) que celle de la passe 1
    (lam099|lr=4.0) : aucune réplique. Le classificateur rend `indeterminee` pour les DEUX lignes -- il ne confirme PAS
    l'étiquette « structure » que le record attribue à lr 1,0 (E33 : conclusion peut-être juste, preuve absente)."""
    assert [classify_cut_nature(d, coeurs_exterieurs=None) for d in (D_LR1, D_LR2)] == ["indeterminee", "indeterminee"]
    d_reprise = cut_geometry(U_REPRISE, 95, BUDGET, SAFETY)["depassement"]        # la coupe COURANTE de lr 1,0
    assert classify_cut_nature(d_reprise, coeurs_exterieurs=None) == "indeterminee"


def test_nature_noop_a_measure_passed_as_its_own_replica_changes_nothing():
    """No-op EXACT : fournir la mesure d'origine comme sa propre « réplique » ne peut pas changer la nature."""
    for x in (None, SEUIL - 1.0, SEUIL + 1.0):
        for d in (D_LR1, D_LR2):
            seul = classify_cut_nature(d, coeurs_exterieurs=x)
            assert classify_cut_nature(d, coeurs_exterieurs=x, depassement_replique=d, coeurs_exterieurs_replique=x) == seul
            assert classify_cut_nature(d, coeurs_exterieurs=x) == seul                 # déterministe


def test_nature_is_monotone_more_margin_never_loses_structure_more_load_never_gains_it():
    rang = {"structure": 2, "indeterminee": 1, "contention": 0}
    ds = [1.0001, 1.05, 1.5, 1.9, 1.9001, 2.5, 10.0]
    for x in (None, SEUIL - 1.0, SEUIL + 1.0):
        for b in (None, 0.0, 0.9):
            nat = [classify_cut_nature(d, coeurs_exterieurs=x, bande_contamination=b) for d in ds]
            assert all(not (a == "structure" and c != "structure") for a, c in zip(nat, nat[1:]))
    xs = [0.0, SEUIL - 0.1, SEUIL, SEUIL + 0.1, 20.0]
    for d in (D_LR1, D_LR2):
        nat = [classify_cut_nature(d, coeurs_exterieurs=x, bande_contamination=0.9) for x in xs]
        assert all(rang[a] >= rang[c] for a, c in zip(nat, nat[1:]))


@pytest.mark.parametrize("args,kw", [
    ((1.0,), {"coeurs_exterieurs": None}),                         # ligne NON coupée (projection == budget) : rien à qualifier
    ((0.96,), {"coeurs_exterieurs": None}),
    ((float("nan"),), {"coeurs_exterieurs": None}),
    ((1.5,), {"coeurs_exterieurs": True}),                          # un booléen n'est pas une charge
    ((1.5,), {"coeurs_exterieurs": "12"}),
    ((1.5,), {"coeurs_exterieurs": None, "bande_contamination": -0.1}),
    ((1.5,), {"coeurs_exterieurs": None, "seuil_coeurs_libre": float("nan")}),
    ((1.5,), {"coeurs_exterieurs": None, "depassement_replique": float("nan"), "coeurs_exterieurs_replique": 1.0}),
    ((1.5,), {"coeurs_exterieurs": None, "depassement_replique": 0.0, "coeurs_exterieurs_replique": 1.0}),
])
def test_nature_refuses_degenerate_inputs(args, kw):
    with pytest.raises(ValueError):
        classify_cut_nature(*args, **kw)
