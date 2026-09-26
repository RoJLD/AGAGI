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
