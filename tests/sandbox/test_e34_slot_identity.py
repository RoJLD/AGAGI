"""E34 (P2.132) — l'identité portée par une POSITION qui bouge : invariant slot W ↔ corps de la cohorte immortelle.

Ce fichier calibre, à réponse CONNUE :
  (1) l'invariant `slot_identity_violations` et la remise en ordre `restore_slot_order` (tools/slot_identity.py),
      sur une cohorte FACTICE (sans torch, sans monde) : le contre-exemple gelé est la mort en TÊTE de liste sous
      la recette publiée, qui fait tourner TOUTES les positions ; la mort en queue n'en fait tourner aucune ;
  (2) `immortal_after_step` (tools/evo_runs/s2_credit_retention.py) : ses défauts sont EXACTEMENT la recette
      publiée ; sous drapeau, l'invariant est tenu et vérifié à chaque tick ;
  (3) dans le MONDE réel (torch, bassin DAgger cloné, ≤ 16 ticks, morts FORCÉES) : la recette publiée désaligne
      après une mort en tête ; le drapeau tient l'invariant ; drapeau éteint et audit sont BIT-IDENTIQUES à une
      copie VERBATIM de la recette d'origine (gelée ci-dessous au sha 5d534d44) ; sans mort, le drapeau est un
      no-op au bit. Les tests (3) simulent un monde : sautés par conftest quand un run tient `kuzu`.
"""
import hashlib
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.slot_identity import SlotIdentityError, restore_slot_order, slot_identity_violations  # noqa: E402

# --------------------------------------------------------------------------------------------------
# 0. Cohorte FACTICE : un monde réduit à ce que l'invariant lit (e.agents, e.dead_agents, e._torch_pop).
# --------------------------------------------------------------------------------------------------


class _Pop:
    def __init__(self, models):
        self.agents = list(models)
        self.B = len(models)


class _World:
    def __init__(self, n):
        self.models = [object() for _ in range(n)]
        self.agents = [{"id": f"a{j}", "model": m, "energy": 80.0, "hp": 100.0} for j, m in enumerate(self.models)]
        self.dead_agents = []
        self._torch_pop = _Pop(self.models)

    def kill(self, pos):
        """Ce que fait `Biosphere3D.step` à une mort : le corps sort de `agents` (survivors), entre dans
        `dead_agents` ; la population n'est pas touchée."""
        a = self.agents.pop(pos)
        a["hp"] = -1.0
        self.dead_agents.append(a)
        return a


def _published_refill(e):
    from tools.evo_runs.s2_credit_retention import immortal_refill
    return immortal_refill(e)


def test_head_death_under_the_published_refill_misaligns_every_slot():
    """CONTRE-EXEMPLE GELÉ : mort en TÊTE, recette publiée -> le mort revient en FIN, toutes les positions tournent,
    et chaque tranche j de la population pilote le corps d'un autre."""
    e = _World(4)
    assert slot_identity_violations(e) == []
    e.kill(0)
    assert _published_refill(e) == 1
    assert [a["id"] for a in e.agents] == ["a1", "a2", "a3", "a0"]
    assert slot_identity_violations(e) == [0, 1, 2, 3]


def test_tail_death_under_the_published_refill_keeps_alignment():
    """Réponse connue dans l'autre sens : le mort de la DERNIÈRE position revient à sa place — aucun désalignement.
    L'instrument peut donc rendre les deux issues."""
    e = _World(4)
    e.kill(3)
    _published_refill(e)
    assert slot_identity_violations(e) == []


def test_middle_death_misaligns_only_the_positions_at_and_after_it():
    e = _World(5)
    e.kill(2)
    _published_refill(e)
    assert slot_identity_violations(e) == [2, 3, 4]


def test_restore_slot_order_gives_each_slot_back_its_own_body():
    e = _World(4)
    avant = list(e.agents)
    e.kill(0)
    _published_refill(e)
    assert restore_slot_order(e) == 4
    assert slot_identity_violations(e) == []
    assert all(e.agents[j] is avant[j] for j in range(4))            # l'agent du slot j est le même objet qu'avant
    assert all(e.agents[j]["model"] is e._torch_pop.agents[j] for j in range(4))
    assert restore_slot_order(e) == 0                                 # idempotent : rien à déplacer


def test_violations_is_None_not_empty_when_the_pairing_is_undefined():
    """Une absence de mesure n'est pas un alignement mesuré : pas de population, ou taille différente (le monde
    reconstruira), rendent None — jamais []."""
    e = _World(3)
    e._torch_pop = None
    assert slot_identity_violations(e) is None
    assert restore_slot_order(e) is None
    e = _World(3)
    e.kill(1)                                                         # B = 3, cohorte = 2 : reconstruction à venir
    assert slot_identity_violations(e) is None
    assert restore_slot_order(e) is None


def test_restore_refuses_a_foreign_or_a_duplicated_body():
    e = _World(3)
    e.agents[1] = dict(e.agents[1], model=object())                   # modèle absent de toute tranche
    with pytest.raises(SlotIdentityError):
        restore_slot_order(e)
    e = _World(3)
    e.agents[2] = dict(e.agents[2], model=e.agents[0]["model"])       # deux corps, un modèle
    with pytest.raises(SlotIdentityError):
        restore_slot_order(e)


# --------------------------------------------------------------------------------------------------
# 1. `immortal_after_step` : défauts = recette publiée ; drapeau = invariant tenu ; audit = compteurs connus.
# --------------------------------------------------------------------------------------------------


def test_immortal_after_step_defaults_are_exactly_the_published_refill():
    from tools.evo_runs.s2_credit_retention import immortal_after_step
    a, b = _World(4), _World(4)
    for w in (a, b):
        w.kill(0)
        w.agents[0]["energy"] = 10.0                                  # recharge d'énergie aussi exercée
    assert immortal_after_step(a) == _published_refill(b) == 1
    assert [x["id"] for x in a.agents] == [x["id"] for x in b.agents] == ["a1", "a2", "a3", "a0"]
    assert [x["energy"] for x in a.agents] == [x["energy"] for x in b.agents]


def test_immortal_after_step_fix_restores_order_and_counts_it():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e = _World(4)
    ident = _identity_counters()
    e.kill(0)
    assert immortal_after_step(e, slot_order_fix=True, identity=ident, tick=7) == 1
    assert slot_identity_violations(e) == []
    assert ident["ticks_reordered"] == 1 and ident["positions_reordered"] == 4
    assert ident["slot_ticks_misaligned"] == 0 and ident["ticks_known"] == 1 and ident["slot_ticks_total"] == 4


def test_immortal_after_step_audit_counts_a_known_dose_of_misalignment():
    """Dose CONNUE : 4 corps, mort en tête au tick 3, puis 2 ticks sans mort -> 3 ticks × 4 tranches désalignées."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e = _World(4)
    ident = _identity_counters()
    for t in range(6):
        if t == 3:
            e.kill(0)
        immortal_after_step(e, identity=ident, tick=t)
    assert ident["ticks_known"] == 6 and ident["ticks_unknown"] == 0 and ident["slot_ticks_total"] == 24
    assert ident["slot_ticks_misaligned"] == 12 and ident["ticks_misaligned"] == 3
    assert ident["first_misaligned_tick"] == 3 and ident["max_misaligned_slots"] == 4
    # la DOSE qui agit : UNE commutation par tranche au tick de la mort, puis un ré-étiquetage qui persiste sans rien
    # commuter (revue v1, P8.a/P10.a) -- 4 commutations, pas 12 slot-ticks
    assert ident["slot_switches"] == 4 and ident["ticks_with_switch"] == 1 and ident["first_switch_tick"] == 3


def test_switches_compose_and_a_tail_death_commutes_nothing():
    """Réponses connues : mort en QUEUE depuis l'ordre aligné -> 0 commutation ; puis mort en tête -> 4 ; puis une
    nouvelle mort en tête sur l'ordre DÉJÀ permuté -> encore 4 (les permutations se composent, la loi « B − p »
    ne vaut que depuis un ordre aligné)."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e = _World(4)
    ident = _identity_counters()
    for t, pos in ((0, 3), (1, None), (2, 0), (3, None), (4, 0)):
        if pos is not None:
            e.kill(pos)
        immortal_after_step(e, identity=ident, tick=t)
    assert ident["slot_switches"] == 8 and ident["ticks_with_switch"] == 2 and ident["first_switch_tick"] == 2
    assert ident["first_misaligned_tick"] == 2
    assert ident["order_changes"] == 2 and ident["first_order_change_tick"] == 2
    assert ident["switch_events"] == [[2, 4], [4, 4]]


def test_the_fix_never_commutes_and_records_its_first_reorder_tick():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e = _World(4)
    ident = _identity_counters()
    for t, pos in ((0, None), (1, 0), (2, None), (3, 2)):
        if pos is not None:
            e.kill(pos)
        immortal_after_step(e, slot_order_fix=True, identity=ident, tick=t)
    assert ident["slot_switches"] == 0 and ident["slot_ticks_misaligned"] == 0
    assert ident["first_reorder_tick"] == 1 and ident["ticks_reordered"] == 2


def test_the_published_identity_hides_the_working_state():
    from tools.evo_runs.s2_credit_retention import _identity_counters, _published_identity
    ident = _identity_counters()
    ident["_pairing"] = {1: "a"}
    ident["_order"] = ["a"]
    ident["_relabel_rng"] = np.random.RandomState(1)
    pub = _published_identity(ident)
    assert not any(k.startswith("_") for k in pub) and pub["slot_switches"] == 0 and "_pairing" in ident


class _TorchPop:
    """Population FACTICE à tenseurs torch réels : W (paramètre de l'optimiseur), H, `_last`, `_prev`, SGD sans momentum
    -- ce que `permute_population_rows` touche, rien d'autre."""

    def __init__(self, models, n=3):
        import torch
        B = len(models)
        self.agents, self.B = list(models), B
        self.W = torch.nn.Parameter(torch.arange(B * n * n, dtype=torch.float32).reshape(B, n, n))
        self.H = torch.arange(B * n, dtype=torch.float32).reshape(B, n) + 100.0
        self._last = (torch.arange(B, dtype=torch.float32).reshape(B, 1), self.H.clone())
        self._prev = {"obs": torch.arange(B, dtype=torch.float32).reshape(B, 1), "H_in": self.H.clone(),
                      "act": [{"move": j} for j in range(B)], "reward": np.arange(B, dtype=np.float32)}
        self.opt = torch.optim.SGD([self.W], lr=0.1)
        self.e_a = self.e_v = None
        self.U = self.V = self.W_bl = None


def _torch_world(n):
    torch = pytest.importorskip("torch")
    e = _World(n)
    e._torch_pop = _TorchPop(e.models)
    return e, torch


def test_permute_population_rows_moves_every_row_and_keeps_the_optimizer_parameter():
    from tools.slot_identity import permute_population_rows
    e, torch = _torch_world(4)
    pop = e._torch_pop
    w0, h0, param = pop.W.detach().clone(), pop.H.clone(), pop.W
    models = list(pop.agents)
    perm = [2, 0, 3, 1]
    permute_population_rows(pop, perm)
    assert pop.W is param and pop.opt.param_groups[0]["params"][0] is param          # même paramètre, en place
    for j, k in enumerate(perm):
        assert torch.equal(pop.W[j], w0[k]) and torch.equal(pop.H[j], h0[k])
        assert pop.agents[j] is models[k] and pop._prev["act"][j] == {"move": k}
        assert float(pop._prev["reward"][j]) == float(k) and float(pop._last[0][j, 0]) == float(k)


def test_permute_population_rows_refuses_outside_the_certified_perimeter():
    """Périmètre certifié (décision Master 2) : SGD sans momentum, traces non allouées, pas de bilinéaire ; et une
    permutation de range(B)."""
    from tools.slot_identity import SlotIdentityError, permute_population_rows
    e, torch = _torch_world(3)
    with pytest.raises(SlotIdentityError):
        permute_population_rows(e._torch_pop, [0, 0, 1])
    e._torch_pop.e_a = [torch.zeros(1)]
    with pytest.raises(SlotIdentityError):
        permute_population_rows(e._torch_pop, [1, 0, 2])
    e, torch = _torch_world(3)
    e._torch_pop.opt = torch.optim.SGD([e._torch_pop.W], lr=0.1, momentum=0.9)
    with pytest.raises(SlotIdentityError):
        permute_population_rows(e._torch_pop, [1, 0, 2])


def test_reindex_fix_keeps_the_published_body_order_and_moves_the_brains():
    """RÉINDEXATION (revue v3, P1.a) : après une mort en tête, les corps restent dans l'ordre de la recharge PUBLIÉE (le
    mort en queue) et ce sont les lignes qui suivent : invariant tenu, zéro commutation, ordre de service inchangé."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e, torch = _torch_world(4)
    ident = _identity_counters()
    np.random.seed(11)
    ref_global = np.random.RandomState(11)
    torch_state = torch.get_rng_state().clone()
    for t, pos in ((0, None), (1, 0), (2, None), (3, 2)):
        if pos is not None:
            e.kill(pos)
        attendu = None
        if pos is not None:
            attendu = [a["id"] for a in e.agents] + [a["id"] for a in e.dead_agents]
        immortal_after_step(e, slot_reindex=True, identity=ident, tick=t)
        if attendu is not None:
            assert [a["id"] for a in e.agents] == attendu                 # ordre des CORPS = recharge publiée
        assert slot_identity_violations(e) == []
    assert ident["slot_switches"] == 0 and ident["ticks_body_reordered"] == 0
    assert ident["first_reindex_tick"] == 1 and ident["reindex_events"] == 2 and ident["order_changes"] == 2
    assert np.random.random() == ref_global.random() and torch.equal(torch.get_rng_state(), torch_state)


def test_relabel_sham_shuffles_only_the_moved_rows_with_its_private_rng():
    """RÉÉTIQUETAGE (revues v3 P1.b/P5.d, v4 P4.b/P7.a) : à chaque changement d'ordre, seules les lignes des positions
    DÉPLACÉES sont permutées, par RandomState(k), en DÉRANGEMENT relatif à la réindexation (aucune position déplacée ne
    reçoit le cerveau de son corps : tirage par rejet) ; l'ordre des corps reste celui de la recharge publiée ; RNG
    global et torch intacts."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e, torch = _torch_world(5)
    ident = _identity_counters()
    np.random.seed(7)
    ref_global = np.random.RandomState(7)
    torch_state = torch.get_rng_state().clone()
    prive = np.random.RandomState(3)
    avant = list(e._torch_pop.agents)
    e.kill(1)                                                        # positions 1..4 déplacées
    immortal_after_step(e, identity=ident, tick=0, sham_relabel=3)
    deplacees = [1, 2, 3, 4]
    propre = {1: 2, 2: 3, 3: 4, 4: 1}                                # après recharge : corps a2, a3, a4, a1
    tirages = 0
    while True:                                                      # même rejet que le harnais
        tirages += 1
        melange = prive.permutation(4)
        cible = {j: deplacees[int(melange[i])] for i, j in enumerate(deplacees)}
        if all(cible[j] != propre[j] for j in deplacees):
            break
    for j in deplacees:
        assert e._torch_pop.agents[j] is avant[cible[j]]
        assert e._torch_pop.agents[j] is not e.agents[j]["model"]    # aucun cerveau déplacé sur son corps
    assert ident["relabel_draws"] == tirages
    assert e._torch_pop.agents[0] is avant[0]                        # position non déplacée : ligne intacte
    assert [a["id"] for a in e.agents] == ["a0", "a2", "a3", "a4", "a1"]  # corps : recharge publiée
    assert ident["relabel_events"] == 1 and ident["first_relabel_tick"] == 0 and ident["sham_relabel"] == 3
    assert ident["positions_moved"] == 4 and ident["ticks_body_reordered"] == 0
    assert np.random.random() == ref_global.random() and torch.equal(torch.get_rng_state(), torch_state)
    assert 0 < ident["slot_switches"] <= 4


def test_relabel_sham_at_two_moved_rows_can_only_keep_the_off_assignment():
    """Revue v4, P4.b : à m = 2 lignes déplacées depuis un ordre aligné, la seule permutation non réparatrice est
    celle du bras éteint -- le sham ne tire RIEN d'autre (et ne peut jamais appliquer la réindexation)."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e, _ = _torch_world(4)
    ident = _identity_counters()
    avant = list(e._torch_pop.agents)
    e.kill(2)                                                        # positions 2 et 3 déplacées
    immortal_after_step(e, identity=ident, tick=0, sham_relabel=9)
    assert [a["id"] for a in e.agents] == ["a0", "a1", "a3", "a2"]
    assert all(e._torch_pop.agents[j] is avant[j] for j in range(4))  # lignes inchangées : l'affectation du bras éteint
    assert slot_identity_violations(e) == [2, 3] and ident["rows_relabeled"] == 0


def test_body_order_is_measured_and_only_the_body_fix_moves_it():
    """Revue v4, P10.a : `ticks_body_reordered` est MESURÉ (ordre final contre ordre laissé par la recharge) : nul pour
    les traitements qui ne touchent que les lignes, positif pour la remise en ordre des CORPS."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    for kw, attendu in (({"slot_reindex": True}, 0), ({"sham_relabel": 4}, 0), ({"cut_credit_at_t1": True}, 0),
                        ({}, 0), ({"slot_order_fix": True}, 1)):
        e, _ = _torch_world(4)
        ident = _identity_counters()
        e.kill(0)
        immortal_after_step(e, identity=ident, tick=0, **kw)
        assert ident["ticks_body_reordered"] == attendu, kw


def test_positive_control_cuts_the_credit_at_the_first_order_change():
    """CONTRÔLE POSITIF (revue v2, P5.c) : au premier tick où la recharge change l'ordre (t1), learn et learn_episode de
    la population rendent None ; rien avant, rien d'autre."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e = _World(4)
    ident = _identity_counters()
    np.random.seed(5)
    ref_global = np.random.RandomState(5)
    for t, pos in ((0, 3), (1, None), (2, 0), (3, 1)):
        if pos is not None:
            e.kill(pos)
        immortal_after_step(e, identity=ident, tick=t, cut_credit_at_t1=True)
        if t < 2:
            assert not hasattr(e._torch_pop, "learn")               # mort en queue : aucune coupe
    assert ident["credit_cut_tick"] == 2
    assert e._torch_pop.learn([1.0], [{}]) is None and e._torch_pop.learn_episode([], [], []) is None
    assert np.random.random() == ref_global.random()                # aucun tirage du RNG global (revue v4, P10.c)
    assert ident["relabel_events"] == 0 and ident["reindex_events"] == 0 and ident["positions_reordered"] == 0


def test_treatments_are_refused_before_the_refill_without_audit_combined_or_negative():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    for kw in ({"sham_relabel": 2}, {"slot_reindex": True}, {"cut_credit_at_t1": True},
               {"sham_relabel": -1, "identity": _identity_counters()},
               {"sham_relabel": 2, "slot_reindex": True, "identity": _identity_counters()},
               {"slot_reindex": True, "slot_order_fix": True, "identity": _identity_counters()},
               {"cut_credit_at_t1": True, "sham_relabel": 3, "identity": _identity_counters()}):
        e = _World(3)
        e.kill(0)
        with pytest.raises(ValueError):
            immortal_after_step(e, tick=0, **kw)
        assert len(e.agents) == 2 and len(e.dead_agents) == 1        # la recharge n'a pas eu lieu


def test_immortal_after_step_audit_without_tick_is_refused_before_the_refill():
    """Sans `tick`, `first_misaligned_tick` resterait None après un désalignement : refus, et AVANT tout effet."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    e = _World(3)
    e.kill(0)
    with pytest.raises(ValueError):
        immortal_after_step(e, identity=_identity_counters())
    assert len(e.agents) == 2 and len(e.dead_agents) == 1              # la recharge n'a pas eu lieu


def test_immortal_after_step_fix_raises_when_the_invariant_cannot_hold():
    from tools.evo_runs.s2_credit_retention import immortal_after_step
    e = _World(3)
    e.agents[1] = dict(e.agents[1], model=object())
    with pytest.raises(SlotIdentityError):
        immortal_after_step(e, slot_order_fix=True, tick=0)
    e = _World(3)
    e._torch_pop = None                                               # appariement non défini : refus, pas un vert
    with pytest.raises(SlotIdentityError):
        immortal_after_step(e, slot_order_fix=True, tick=0)


# --------------------------------------------------------------------------------------------------
# 2. Le MONDE réel (torch) : morts FORCÉES, digest des poids appris, âges, dose.
# --------------------------------------------------------------------------------------------------


def _refill_reference_5d534d44(e, refill_below=30.0, refill_to=80.0, hp_refill_below=50.0):
    """COPIE VERBATIM de `immortal_refill` au sha 5d534d44 (tools/evo_runs/s2_credit_retention.py:97-114) :
    l'oracle du « drapeau éteint = comportement publié au bit », valable sur toute plateforme (même process)."""
    for a in e.agents:
        if a["energy"] < refill_below:
            a["energy"] = refill_to
        if a["hp"] < hp_refill_below:
            a["hp"] = 100.0 + float(getattr(a["model"], "phenotype_hp_bonus", 0.0))
    dead = list(getattr(e, "dead_agents", []))
    for a in dead:
        a["energy"] = refill_to
        a["hp"] = 100.0 + float(getattr(a["model"], "phenotype_hp_bonus", 0.0))
        e.agents.append(a)
    if dead:
        e.dead_agents.clear()
    return len(dead)


def _trace(after_step, seed=2026, n=3, ticks=16, kills=((2, 0), (6, 1))):
    """Phase 1 immortelle réduite, morts FORCÉES (hp très négatif avant le pas : la mort est certaine dans le
    tick). `after_step(e, t)` remplace la ligne de résurrection. Rend un digest (W appris par modèle dans l'ordre
    de construction, âges par modèle, dose) et l'invariant relevé après chaque tick."""
    pytest.importorskip("torch")
    from tools.cognitive_demand_inworld import _pinned_substrate
    from tools.evo_runs.s2_credit_retention import _world
    from tools.evo_runs.s2_reward_ablation import _bassin_cohort
    from tools.learning_events import count_learning_events
    agents = _bassin_cohort(seed, n)
    kills = dict(kills)
    per_tick, res = [], 0
    with _pinned_substrate(), count_learning_events() as ev:
        e = _world(seed, 0)
        for a in agents:
            e.add_agent(a, energy=80.0)
        for t in range(ticks):
            if t in kills:
                e.agents[kills[t]]["hp"] = -1e9
            e.step()
            res += after_step(e, t)
            per_tick.append(slot_identity_violations(e))
        if hasattr(e, "memory_retriever"):
            e.memory_retriever.stop()
    summ = ev.summary()
    by_model = {id(d["model"]): d for d in e.agents}
    ages = [int(by_model[id(a)]["age"]) for a in agents]
    h = hashlib.sha256()
    for a in agents:
        h.update(np.asarray(a.genome.W, dtype=np.float32).tobytes())
    h.update(json.dumps(ages).encode())
    h.update(json.dumps({k: summ[k] for k in ("td_updates", "episode_updates", "dW_abs_sum")}).encode())
    return {"digest": h.hexdigest(), "ages": ages, "res": res, "summary": summ, "per_tick": per_tick}


def test_real_world_head_death_misaligns_every_slot_under_the_published_refill():
    from tools.evo_runs.s2_credit_retention import immortal_refill
    tr = _trace(lambda e, t: immortal_refill(e))
    assert tr["res"] == 2
    assert tr["per_tick"][:2] == [[], []]
    assert tr["per_tick"][2] == [0, 1, 2]                             # la mort en tête au tick 2 fait tout tourner
    assert all(v for v in tr["per_tick"][2:])                         # et rien ne réaligne ensuite
    assert tr["summary"]["td_updates"] == 15                          # aucune reconstruction (preuve publiée)


def test_real_world_slot_order_fix_holds_the_invariant_every_tick():
    from tools.evo_runs.s2_credit_retention import immortal_after_step
    tr = _trace(lambda e, t: immortal_after_step(e, slot_order_fix=True, tick=t))
    assert tr["res"] == 2
    assert all(v == [] for v in tr["per_tick"])
    assert tr["summary"]["td_updates"] == 15


def test_flag_off_and_audit_are_bit_identical_to_the_frozen_reference_refill():
    """No-op EXACT au bit, drapeau éteint ET audit (lecture seule), contre la copie verbatim de la recette."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e))
    off = _trace(lambda e, t: immortal_after_step(e, tick=t))
    ident = _identity_counters()
    aud = _trace(lambda e, t: immortal_after_step(e, identity=ident, tick=t))
    assert off["digest"] == ref["digest"] == aud["digest"]
    assert off["summary"]["dW_abs_sum"] == ref["summary"]["dW_abs_sum"] > 0.0
    assert ident["slot_ticks_misaligned"] == sum(len(v) for v in ref["per_tick"]) > 0


def test_without_death_the_fix_is_a_bit_exact_noop():
    """Les âges et les poids d'un bras SANS mort restent bit-identiques sous le drapeau."""
    from tools.evo_runs.s2_credit_retention import immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e), kills=())
    fix = _trace(lambda e, t: immortal_after_step(e, slot_order_fix=True, tick=t), kills=())
    assert ref["res"] == fix["res"] == 0
    assert fix["digest"] == ref["digest"]


def test_real_world_relabel_shams_diverge_from_off_and_from_each_other():
    """Revue v2, P5.b : dans le MONDE réel, les réétiquetages changent ce qui est appris (la bande ne peut pas être inerte
    par construction) et l'ordre des CORPS n'est jamais touché. En DÉRANGEMENT (revue v4), le nombre d'affectations
    permises est petit sur une petite cohorte (2 pour 3 corps, 9 pour 4) : deux RNG peuvent tirer la même, et
    l'affectation du bras éteint est elle-même permise -- on exige donc, sur trois RNG et 4 corps, au moins deux
    trajectoires distinctes et au moins une distincte du bras éteint (mesuré : 3 corps et 2 RNG tiraient la même)."""
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e), n=4)
    digests = []
    for k in (1, 2, 3):
        ident = _identity_counters()
        tr = _trace(lambda e, t, ident=ident, k=k: immortal_after_step(e, identity=ident, tick=t, sham_relabel=k), n=4)
        digests.append(tr["digest"])
        assert ident["first_relabel_tick"] == 2 and ident["relabel_events"] >= 2 and ident["ticks_body_reordered"] == 0
    assert len(set(digests)) >= 2 and any(d != ref["digest"] for d in digests)


def test_real_world_reindex_fix_holds_the_invariant_every_tick_and_keeps_the_body_order():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    ident = _identity_counters()
    tr = _trace(lambda e, t: immortal_after_step(e, slot_reindex=True, identity=ident, tick=t))
    assert tr["res"] == 2 and all(v == [] for v in tr["per_tick"])
    assert ident["slot_switches"] == 0 and ident["ticks_body_reordered"] == 0 and ident["first_reindex_tick"] == 2
    assert tr["summary"]["td_updates"] == 15


def test_without_death_the_reindex_fix_is_a_bit_exact_noop():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e), kills=())
    ident = _identity_counters()
    fix = _trace(lambda e, t: immortal_after_step(e, slot_reindex=True, identity=ident, tick=t), kills=())
    assert ref["res"] == fix["res"] == 0 and ident["reindex_events"] == 0
    assert fix["digest"] == ref["digest"]


def test_with_a_head_death_the_reindex_fix_changes_what_is_learned():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e))
    ident = _identity_counters()
    fix = _trace(lambda e, t: immortal_after_step(e, slot_reindex=True, identity=ident, tick=t))
    assert fix["digest"] != ref["digest"]


def test_real_world_positive_control_stops_the_credit_at_t1():
    from tools.evo_runs.s2_credit_retention import _identity_counters, immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e))
    ident = _identity_counters()
    pos = _trace(lambda e, t: immortal_after_step(e, identity=ident, tick=t, cut_credit_at_t1=True))
    assert ident["credit_cut_tick"] == 2
    assert pos["summary"]["td_updates"] < ref["summary"]["td_updates"] and pos["digest"] != ref["digest"]


def test_with_a_head_death_the_fix_changes_what_is_learned():
    """Contrôle POSITIF : le drapeau n'est pas un no-op quand une mort en tête a lieu — l'instrument de re-mesure
    peut donc rendre une différence."""
    from tools.evo_runs.s2_credit_retention import immortal_after_step
    ref = _trace(lambda e, t: _refill_reference_5d534d44(e))
    fix = _trace(lambda e, t: immortal_after_step(e, slot_order_fix=True, tick=t))
    assert fix["digest"] != ref["digest"]


def test_phase1_defaults_publish_no_new_key_and_the_flags_publish_slot_identity():
    pytest.importorskip("torch")
    from tools.evo_runs.s2_credit_retention import phase1_learn_immortal
    from tools.evo_runs.s2_reward_ablation import _bassin_cohort
    base = phase1_learn_immortal(_bassin_cohort(2026, 2), 2026, 3)
    aud = phase1_learn_immortal(_bassin_cohort(2026, 2), 2026, 3, identity_audit=True)
    fix = phase1_learn_immortal(_bassin_cohort(2026, 2), 2026, 3, slot_order_fix=True)
    assert "slot_identity" not in base
    assert {k: v for k, v in aud.items() if k != "slot_identity"} == base
    assert aud["slot_identity"]["slot_order_fix"] is False and aud["slot_identity"]["ticks_known"] == 3
    assert fix["slot_identity"]["slot_order_fix"] is True and fix["slot_identity"]["slot_ticks_misaligned"] == 0
