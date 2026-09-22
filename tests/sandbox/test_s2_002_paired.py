"""S2-002-PAIRED-R1 — la lecture scellée (`tools/evo_runs/s2_002_paired.py::s2_paired_lecture`) confrontée à des bases
synthétiques, dans l'ORDRE IMPOSÉ (INCOMPLET, HARNAIS par monde, CARTE_INCHANGEE, CARTE_MODIFIEE, MIXTE), le fait
post-hoc (signe de within − 1) publié hors verdict, et le runner par injection d'un `map_fn` factice (0 monde :
bande appariée et no-op DEMANDÉS, clés (monde, seed), reprise respectée, garde en tête). Le résultat publié, s'il
existe, est relu contre la règle.

EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_LEASE_GUARD_EXEMPT = True

from tools.evo_runs.s2_002_paired import PUBLIE, run_s2_paired, s2_paired_lecture  # noqa: E402
from tools.preregister import verify  # noqa: E402

RULE = verify("S2-002-PAIRED-R1")
C = RULE["cellule"]


def _cell(within=1.0, noop=1.0, verdict="PERCEPTION_DECOY", intact=27.5, floor=24.0):
    return {"within_ratio": within, "noop": {"ratio": noop}, "verdict": verdict, "intact_median": intact, "floor": floor}


def _db(per=None):
    db = {}
    for w in C["worlds"]:
        for sd in C["seeds"]:
            db[f"{w}|seed={sd}"] = _cell(**(per(w, sd) if per else {}))
    return db


def test_incomplete_gives_no_reading():
    db = _db()
    del db["famine|seed=3027"]
    assert s2_paired_lecture(db, RULE) == {"branche": "INCOMPLET", "manquantes": 1}


def test_unchanged_map_and_the_post_hoc_sign_is_published_not_judged():
    lec = s2_paired_lecture(_db(per=lambda w, sd: {"within": 0.93} if w == "stoneage" else {}), RULE)
    assert lec["branche"] == "CARTE_INCHANGEE" and lec["inchanges"] == list(C["worlds"]) and lec["harnais"] == []
    assert lec["par_monde"]["stoneage"]["signe_post_hoc"] == "survit PLUS derange"
    assert lec["par_monde"]["soup"]["signe_post_hoc"] == "dans la marge" and lec["par_monde"]["soup"]["noop_exact"] == "3/3"


def test_a_world_whose_paired_noop_is_not_exact_on_two_seeds_is_HARNAIS_and_not_read():
    lec = s2_paired_lecture(_db(per=lambda w, sd: {"noop": 1.03} if (w == "famine" and sd != 2026) else {}), RULE)
    assert lec["harnais"] == ["famine"] and lec["par_monde"]["famine"]["lecture"] == "HARNAIS"
    assert lec["branche"] == "CARTE_INCHANGEE" and "famine" not in lec["inchanges"]     # les 4 autres sont lus
    lec = s2_paired_lecture(_db(per=lambda w, sd: {"noop": 0.9}), RULE)
    assert lec["branche"] == "HARNAIS" and len(lec["harnais"]) == 5


def test_a_world_changing_verdict_on_two_seeds_is_CARTE_MODIFIEE_and_names_the_new_verdict():
    lec = s2_paired_lecture(_db(per=lambda w, sd: {"within": 1.6, "verdict": "PERCEPTION_DEMANDED"}
                               if (w == "agricultural" and sd != 3027) else {}), RULE)
    assert lec["branche"] == "CARTE_MODIFIEE" and lec["modifies"] == {"agricultural": "PERCEPTION_DEMANDED"}
    assert lec["par_monde"]["agricultural"]["lecture"] == "MODIFIE -> PERCEPTION_DEMANDED"
    assert lec["par_monde"]["agricultural"]["signe_post_hoc"] == "survit MOINS derange"


def test_seeds_in_disagreement_are_MIXTE_reported_without_inference():
    lec = s2_paired_lecture(_db(per=lambda w, sd: {"verdict": {2026: "PERCEPTION_DECOY", 3026: "INCONCLUSIVE_INVERTED",
                                                              3027: "INCONCLUSIVE_DEGENERATE"}[sd]} if w == "soup" else {}), RULE)
    assert lec["branche"] == "MIXTE" and lec["mixtes"] == ["soup"] and lec["par_monde"]["soup"]["lecture"] == "MIXTE"


def test_modifie_takes_precedence_over_mixte_in_the_imposed_order():
    def per(w, sd):
        if w == "agricultural" and sd != 3027:
            return {"verdict": "PERCEPTION_DEMANDED"}
        if w == "soup":
            return {"verdict": {2026: "PERCEPTION_DECOY", 3026: "INCONCLUSIVE_INVERTED", 3027: "INCONCLUSIVE_DEGENERATE"}[sd]}
        return {}
    assert s2_paired_lecture(_db(per=per), RULE)["branche"] == "CARTE_MODIFIEE"


def test_runner_requests_paired_band_and_noop_per_cell_and_respects_a_resumed_base():
    seen = []

    def _map(worlds, seed, K, paired_band, noop_control, **regime):
        seen.append((worlds[0], seed, K, paired_band, noop_control, regime["num_agents"], regime["max_ticks"]))
        return {worlds[0]: {"within_ratio": 0.98, "between_ratio": 2.0, "verdict": "PERCEPTION_DECOY", "n": K,
                            "noop": {"ratio": 1.0, "verdict": "PERCEPTION_DECOY", "median": 27.0}, "intact_median": 27.0,
                            "floor": 24.0, "reference": "paired_band", "policy": "MambaBatchModel"}}
    deja = {"soup|seed=2026": _cell(within=0.5)}
    db = run_s2_paired(seeds=[2026, 3026], worlds=["soup", "famine"], k=3, map_fn=_map, db=deja, verbose=False)
    assert len(seen) == 3 and all(s[3] and s[4] and s[2] == 3 and s[5] == 12 and s[6] == 200 for s in seen)
    assert db["soup|seed=2026"]["within_ratio"] == 0.5, "une cellule déjà mesurée n'est pas re-mesurée (reprise)"
    assert db["famine|seed=3026"]["reference"] == "paired_band" and db["famine|seed=3026"]["noop"]["ratio"] == 1.0
    with pytest.raises(ValueError):
        run_s2_paired(seeds=[], worlds=["soup"], map_fn=_map)


def test_published_reference_is_DECOY_on_the_five_worlds():
    assert set(PUBLIE) == set(C["worlds"]) and set(PUBLIE.values()) == {"PERCEPTION_DECOY"}


_PUB = os.path.join(os.path.dirname(__file__), "..", "..", "results", "s2_002_paired_r1.json")


def _publie():
    if not os.path.exists(_PUB):
        return None
    db = json.load(open(_PUB, encoding="utf-8"))
    return db if "_lecture" in db else None


@pytest.mark.skipif(_publie() is None, reason="run S2-002-PAIRED-R1 non encore publié (ou en cours)")
def test_published_result_rereads_to_its_sealed_branch():
    db = _publie()
    cells = {k: v for k, v in db.items() if not k.startswith("_")}
    assert s2_paired_lecture(cells, RULE)["branche"] == db["_lecture"]["branche"] != "INCOMPLET"
