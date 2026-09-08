# tests/sandbox/test_curriculum_transfer.py
import pytest
from tools.curriculum_transfer import compute_transfer_verdict, _sign_test_p
from src.curriculum.runner import EraResult, GraduationConfig
from tools.curriculum_transfer import run_transfer_experiment


def test_sign_test_p_extremes():
    assert _sign_test_p(0, 0) == 1.0
    assert _sign_test_p(5, 5) < 0.1          # tous du même côté -> significatif
    assert _sign_test_p(3, 6) == 1.0         # 50/50 -> p=1
    assert 0.0 <= _sign_test_p(4, 5) <= 1.0


def test_verdict_transfere_when_ratios_above_one():
    # ⚠️ n=8, PAS 5. Une garde de PUISSANCE (`sign_p < 0.05`) a été ajoutée à ces branches et JAMAIS
    # rétro-appliquée aux fixtures : à n=5 `sign_p` vaut 0.0625 AU MIEUX, donc TRANSFERE et NUIT
    # étaient devenus INATTEIGNABLES par construction et ces tests rouges. Classe E14 — la même,
    # le même jour, dans quatre fichiers différents.
    v = compute_transfer_verdict([1.5, 1.4, 1.6, 1.3, 1.5, 1.45, 1.55, 1.35])
    assert v["verdict"] == "TRANSFERE"
    assert v["n_favorable"] == 8 and v["n"] == 8
    assert v["median_ratio"] > 1.0
    assert v["sign_p"] < 0.05, "la puissance est la CONDITION du verdict, pas un détail"


def test_verdict_nuit_when_ratios_below_one():
    v = compute_transfer_verdict([0.5, 0.6, 0.4, 0.5, 0.55, 0.45, 0.52, 0.48])
    assert v["verdict"] == "NUIT"
    assert v["sign_p"] < 0.05


def test_TRANSFERE_et_NUIT_sont_INATTEIGNABLES_sous_le_plancher_de_puissance():
    """Le plancher, GRAVÉ, dans les DEUX sens : la MÊME dose sur 5 seeds ne peut rendre ni TRANSFERE
    ni NUIT (`sign_p` = 0.0625 par construction). Sans ce cas, la prochaine garde ajoutée re-cassera
    les fixtures en silence — c'est exactement ce qui vient de se produire."""
    haut = compute_transfer_verdict([1.5, 1.4, 1.6, 1.3, 1.5])
    bas = compute_transfer_verdict([0.5, 0.6, 0.4, 0.5, 0.55])
    assert haut["median_ratio"] > 1.0 and haut["n_favorable"] == 5     # la DOSE est là
    assert haut["sign_p"] == 0.0625                                    # la PUISSANCE ne l'est pas
    assert haut["verdict"] == "NEUTRE" and bas["verdict"] == "NEUTRE"


def test_verdict_neutre_in_band_or_mixed():
    assert compute_transfer_verdict([1.01, 0.99, 1.02, 0.98])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([])["sign_p"] == 1.0


def test_two_arms_equal_budget_and_pairing():
    """fake run_era_fn : compétence haute SI un ancêtre est hérité (bras curriculum atteint la cible
    avec transfert), basse sinon (bras tabula-rasa part de zéro). -> ratio > 1, TRANSFERE."""
    seen = []

    def fake(world_type, import_id, keep_mem):
        seen.append((world_type, import_id))
        comp = 0.8 if import_id is not None else 0.4
        return EraResult(competence=comp, champion_agent_id="champ1234")

    res = run_transfer_experiment(
        [0], ladder=["w_easy", "w_target"], target="w_target",
        grad_cfg=GraduationConfig(max_eras=2), run_era_fn=fake, manage_logger=False,
    )
    row = res["per_seed"][0]
    assert row["seed"] == 0
    assert row["C_curr"] == 0.8 and row["C_tabula"] == 0.4
    assert row["ratio"] == 0.8 / 0.4
    # budget égal : le bras tabula-rasa a tourné EXACTEMENT total_eras ères sur la cible.
    # Il est le SEUL à exécuter la cible sans ancêtre hérité (imp is None) : dans le bras
    # curriculum, le stage cible hérite toujours du champion promu (imp == "champ1234").
    tabula_calls = [w for (w, imp) in seen if imp is None and w == "w_target"]
    assert len(tabula_calls) == row["total_eras"]
    assert all(w == "w_target" for w in tabula_calls)
    # ⚠️ CORRIGÉ le 2026-09-08. Ce test tourne sur UN SEUL seed : `sign_p` y vaut 1.0 PAR
    # CONSTRUCTION, donc TRANSFERE est inatteignable quelle que soit la dose (ratio = 2.0 ici). Son
    # sujet est l'APPARIEMENT et le BUDGET, pas le verdict — l'exiger était une assertion que le
    # dispositif ne pouvait pas satisfaire. Le verdict suit bien la dose : c'est vérifié à n
    # suffisant par `tests/sandbox/test_inj_run_transfer_experiment.py`.
    assert res["verdict"] == "NEUTRE"
    assert res["sign_p"] == 1.0 and res["n"] == 1


def test_experiment_handles_zero_tabula_competence():
    """⚠️ RETOURNÉ le 2026-09-08. Ce test BÉNISSAIT le défaut : il vérifiait seulement
    `ratio < 1e9`, c'est-à-dire qu'il BORNAIT l'artefact du plancher epsilon au lieu de le refuser.
    Un bras tabula-rasa ÉTEINT (C=0) devenait un dénominateur 1e-6, donc `C_curr=0.5 -> ratio
    500000`, `median_ratio=500000` et VERDICT='TRANSFERE' publié : le verdict ne naissait pas d'un
    transfert mais d'une division par le plancher. Le rapport n'existe pas quand le dénominateur est
    nul — il doit rester INDÉTERMINÉ et NOMMÉ."""
    def fake(world_type, import_id, keep_mem):
        comp = 0.5 if import_id is not None else 0.0   # tabula -> 0 -> le rapport n'existe pas
        return EraResult(competence=comp, champion_agent_id="c")
    res = run_transfer_experiment([7], ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1), run_era_fn=fake,
                                  manage_logger=False)
    ligne = res["per_seed"][0]
    assert ligne["ratio"] is None                       # aucun nombre FABRIQUÉ
    assert ligne["ratio_indetermine"] == "bras_tabula_eteint"     # ... et le motif est NOMMÉ
    assert ligne["C_curr"] == 0.5 and ligne["C_tabula"] == 0.0    # les mesures brutes sont gardées
    assert res["verdict"] == "INDETERMINE" and res["n"] == 1 and res["n_indetermine"] == 1


def test_un_bras_CURRICULUM_eteint_reste_MESURABLE_et_peut_conclure():
    """⚠️ CAS NÉGATIF APPARIÉ du précédent (classe E1). La garde d'indétermination doit savoir NE PAS
    se déclencher : quand c'est le bras CURRICULUM qui s'éteint et le tabula-rasa qui survit, le
    rapport EXISTE (0/0.5 = 0.0) et l'instrument doit rester capable de dire NUIT. Sans ce cas, un
    correctif qui rendrait tout ratio indéterminé passerait le test ci-dessus tout en rendant le
    verdict négatif INATTEIGNABLE — un contrôle qui ne peut plus se déclencher."""
    def fake(world_type, import_id, keep_mem):
        comp = 0.0 if import_id is not None else 0.5   # curriculum -> 0, tabula -> 0.5
        return EraResult(competence=comp, champion_agent_id="c")
    res = run_transfer_experiment([1, 2, 3, 4, 5, 6], ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1), run_era_fn=fake,
                                  manage_logger=False)
    assert [p["ratio"] for p in res["per_seed"]] == [0.0] * 6     # DÉFINI, pas indéterminé
    assert res["n_indetermine"] == 0
    assert res["verdict"] == "NUIT" and res["sign_p"] == pytest.approx(0.03125)


import json
import glob


def test_main_writes_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import tools.curriculum_transfer as ct
    monkeypatch.setattr(ct, "run_transfer_experiment", lambda *a, **k: {
        "n": 1, "median_ratio": 2.0, "n_favorable": 1, "sign_p": 1.0, "verdict": "TRANSFERE",
        "per_seed": [{"seed": 0, "C_curr": 0.8, "C_tabula": 0.4, "total_eras": 2, "ratio": 2.0}],
        "config": {"ladder": ["a", "b"], "target": "b"}})
    monkeypatch.setenv("CT_SEEDS", "0")
    ct.main()
    files = glob.glob(str(tmp_path / "results" / "curriculum_transfer_*.json"))
    assert files, "fichier de provenance non écrit"
    data = json.loads(open(files[0], encoding="utf-8").read())
    assert data["data"]["verdict"] == "TRANSFERE"          # le résultat est sous data["data"]
    assert "commit" in data and "git_dirty" in data        # provenance ledger (Harness.save)
    assert data["seed"] == 0


# --- Verrou repro : déterminisme opt-in (memory_retriever stoppé + vidé avant la boucle) ---

def test_survival_competence_median_age_normalised():
    """Métrique de transfert re-métricisée : médiane d'âge / AGE_REF, clampée [0,1]."""
    from src.curriculum.competence import survival_competence, AGE_REF
    assert survival_competence([]) == 0.0
    assert survival_competence([{"age": int(AGE_REF)}]) == 1.0          # médiane = réf -> 1.0
    assert survival_competence([{"age": int(AGE_REF * 3)}]) == 1.0      # clampé
    mid = survival_competence([{"age": 10}, {"age": int(AGE_REF / 2)}, {"age": int(AGE_REF)}])
    assert mid == pytest.approx(0.5)                                    # médiane = AGE_REF/2


def test_memory_retriever_clear_returns_zeros():
    """clear() vide les caches -> get_memory_vector/get_rag_memory renvoient des zéros déterministes."""
    from src.graph_rag.memory_retriever import AsyncMemoryRetriever
    r = AsyncMemoryRetriever(async_logger=None)
    r._memory_cache = {"a": [1.0, 2.0, 3.0, 4.0, 5.0]}
    r._agent_matrix_cache = {"a": object()}
    r.clear()
    assert r.get_memory_vector("a") == [0.0] * 5
    assert r.get_rag_memory("a", [1.0] * 5) == [0.0] * 5


def test_prepare_world_deterministic_stops_and_clears_retriever(monkeypatch):
    """deterministic=True -> stop() PUIS clear() AVANT la boucle ; False -> ne touche pas le retriever."""
    import main_curriculum as mc
    events = []

    class _SpyRetr:
        def __init__(self):
            self._memory_cache = {"x": [1.0]}
        def stop(self):
            events.append("stop")
        def clear(self):
            events.append("clear")
            self._memory_cache = {}

    class _SpyWorld:
        def __init__(self, config):
            self.memory_retriever = _SpyRetr()

    monkeypatch.setitem(mc.WORLD_FACTORY, "spytest", _SpyWorld)

    env = mc._prepare_world("spytest", object(), deterministic=True)
    assert events == ["stop", "clear"]                 # stop d'abord (tue le worker), puis clear
    assert env.memory_retriever._memory_cache == {}

    events.clear()
    mc._prepare_world("spytest", object(), deterministic=False)
    assert events == []                                # défaut : mémoire ambiante préservée (feature prod)


# =================================================================================================
# CORRECTIFS DU 2026-09-08 -- chaque comportement AJOUTE avec son cas NEGATIF apparie (classe E1 :
# un correctif qui rend l'instrument incapable de se declencher est PIRE que le defaut).
# Les defauts corriges ici sont ceux qu'exposaient les xfail stricts de
# tests/sandbox/test_inj_run_transfer_experiment.py (injection a dose connue, P2.44).
# =================================================================================================

def _fake_transfert(c_curr=0.8, c_tab=0.4):
    """run_era_fn factice : compétence haute si un ancêtre est hérité (bras curriculum), basse
    sinon (bras tabula-rasa). Aucun monde n'est construit."""
    def fake(world_type, import_id, keep_mem):
        return EraResult(competence=(c_curr if import_id is not None else c_tab),
                         champion_agent_id="c")
    return fake


def _refus_instantane():
    """run_era_fn qui EXPLOSE : sert à prouver qu'un refus précède toute mesure (garde en tête)."""
    def fake(world_type, import_id, keep_mem):
        raise AssertionError("garde posée TROP BAS : une ère a tourné avant le refus")
    return fake


# --- 1. `seeds` : un ITÉRATEUR n'est plus consommé par sa propre garde ---------------------------

def test_un_ITERATEUR_de_seeds_est_MESURE_et_non_avale_par_sa_garde():
    """La garde faisait `list(seeds)` et JETAIT le résultat : un générateur était vidé par la garde,
    la boucle ne voyait plus rien, et n=0 / per_seed=[] sortaient en verdict 'NEUTRE' — une
    affirmation de fond produite par ZÉRO mesure."""
    res = run_transfer_experiment((s for s in (11, 22, 33)), ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1),
                                  run_era_fn=_fake_transfert(), manage_logger=False)
    assert res["n"] == 3 and len(res["per_seed"]) == 3
    assert res["config"]["seeds"] == [11, 22, 33]


def test_un_ITERATEUR_VIDE_reste_REFUSE_avant_toute_ere():
    """CAS NÉGATIF APPARIÉ : matérialiser `seeds` ne doit pas avoir désarmé la garde de cohorte
    vide, et le refus doit rester INSTANTANÉ (aucune ère)."""
    with pytest.raises(ValueError, match="degenere"):
        run_transfer_experiment(iter([]), ladder=["a", "b"], target="b",
                                grad_cfg=GraduationConfig(max_eras=1),
                                run_era_fn=_refus_instantane(), manage_logger=False)


# --- 2. PSEUDO-RÉPLICATION : répéter un seed n'ajoute pas de réplicat ----------------------------

def test_les_seeds_REPETES_ne_creent_aucun_replicat():
    """Six fois le même seed = UNE réplication (les deux bras sont déterministes à seed fixe). Avant
    correctif : n=6, sign_p=0.03125 -> 'TRANSFERE' publié depuis un seul réplicat."""
    res = run_transfer_experiment([7] * 6, ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1),
                                  run_era_fn=_fake_transfert(), manage_logger=False)
    assert res["n"] == 1 and res["config"]["seeds"] == [7]
    assert res["sign_p"] == 1.0 and res["verdict"] == "NEUTRE"


def test_des_seeds_DISTINCTS_ne_sont_PAS_deduplicques():
    """CAS NÉGATIF APPARIÉ : la déduplication doit savoir NE PAS se déclencher, sinon elle rendrait
    tout verdict conclusif inatteignable. Même dose, 6 seeds distincts -> TRANSFERE."""
    res = run_transfer_experiment([1, 2, 3, 4, 5, 6], ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1),
                                  run_era_fn=_fake_transfert(), manage_logger=False)
    assert res["n"] == 6 and res["config"]["seeds"] == [1, 2, 3, 4, 5, 6]
    assert res["median_ratio"] == pytest.approx(2.0)
    assert res["sign_p"] == pytest.approx(0.03125) and res["verdict"] == "TRANSFERE"


# --- 3. `metric` : vocabulaire FERMÉ -------------------------------------------------------------

def test_une_METRIQUE_hors_vocabulaire_est_REFUSEE_avant_toute_ere():
    """`metric` n'était comparé qu'à 'survival' : une faute de frappe retombait EN SILENCE sur la
    métrique par-monde pendant que le ledger republiait la valeur DEMANDÉE — la grandeur publiée
    n'était pas celle qui a agi."""
    with pytest.raises(ValueError, match="metric"):
        run_transfer_experiment([0], ladder=["a"], target="a", metric="survie",
                                grad_cfg=GraduationConfig(max_eras=1),
                                run_era_fn=_refus_instantane(), manage_logger=False)


def test_les_DEUX_metriques_du_vocabulaire_restent_ACCEPTEES():
    """CAS NÉGATIF APPARIÉ : la garde ne doit pas refuser le vocabulaire légitime."""
    for m in ("survival", "world"):
        res = run_transfer_experiment([0], ladder=["a"], target="a", metric=m,
                                      grad_cfg=GraduationConfig(max_eras=1),
                                      run_era_fn=_fake_transfert(), manage_logger=False)
        assert res["config"]["metric"] == m and res["n"] == 1


# --- 4. La CIBLE doit terminer l'ÉCHELLE ---------------------------------------------------------

def test_une_CIBLE_HORS_echelle_est_REFUSEE_avant_toute_ere():
    """`target` n'était jamais confronté à `ladder` : le bras curriculum ne visitait jamais la cible
    et `_competence_on_target` rendait la compétence du DERNIER barreau parcouru — le ratio publié
    divisait la compétence sur le monde A par celle sur le monde B."""
    with pytest.raises(ValueError, match="dernier barreau"):
        run_transfer_experiment([0], ladder=["a", "b"], target="gym",
                                grad_cfg=GraduationConfig(max_eras=1),
                                run_era_fn=_refus_instantane(), manage_logger=False)


def test_une_CIBLE_barreau_INTERMEDIAIRE_est_REFUSEE_aussi():
    """Même défaut, autre forme : la cible est DANS l'échelle mais pas en dernier, donc le bras
    curriculum ne s'y arrête pas."""
    with pytest.raises(ValueError, match="dernier barreau"):
        run_transfer_experiment([0], ladder=["a", "b"], target="a",
                                grad_cfg=GraduationConfig(max_eras=1),
                                run_era_fn=_refus_instantane(), manage_logger=False)


def test_une_CIBLE_qui_TERMINE_l_echelle_est_ACCEPTEE():
    """CAS NÉGATIF APPARIÉ : la garde doit savoir NE PAS se déclencher, cible explicite comme
    implicite (target=None -> dernier barreau)."""
    for cible in ("b", None):
        res = run_transfer_experiment([0], ladder=["a", "b"], target=cible,
                                      grad_cfg=GraduationConfig(max_eras=1),
                                      run_era_fn=_fake_transfert(), manage_logger=False)
        assert res["config"]["target"] == "b" and res["per_seed"][0]["ratio"] == pytest.approx(2.0)


# --- 5. `_competence_on_target` LIT le monde de la ligne ------------------------------------------

def test_competence_on_target_LIT_la_cible_au_lieu_de_prendre_la_derniere_ligne():
    from tools.curriculum_transfer import _competence_on_target
    tc = [{"world": "a", "final_competence": 0.1}, {"world": "b", "final_competence": 0.9}]
    assert _competence_on_target(tc, "b") == 0.9
    assert _competence_on_target(tc, "a") == 0.1            # la LIGNE de la cible, pas `[-1]`
    with pytest.raises(ValueError, match="jamais arrete"):  # bras qui n'a pas vu la cible -> BUG
        _competence_on_target(tc, "gym")
    with pytest.raises(ValueError, match="VIDE"):           # transcript vide -> plus de 0.0 fabriqué
        _competence_on_target([], "b")


# --- 6. `compute_transfer_verdict` : l'indétermination n'est pas remplacée par un nombre ----------

def test_verdict_INDETERMINE_quand_une_mesure_MANQUE():
    import math as _math
    v = compute_transfer_verdict([1.5] * 5, n_indetermine=1)
    assert v["verdict"] == "INDETERMINE"
    assert v["n"] == 6 and v["n_indetermine"] == 1          # le seed manquant COMPTE dans n
    nan = float("nan")
    w = compute_transfer_verdict([nan] * 6)                 # forme (b) : le nan n'est plus AVALÉ
    assert w["verdict"] == "INDETERMINE" and w["n_indetermine"] == 6
    assert _math.isnan(w["median_ratio"])


# --- 7. LE TROISIEME AXE DU BUDGET (refutateur, 2026-09-08) --------------------------------------
# La garde d'arguments couvrait la cohorte, la population et l'horizon, PAS le budget d'ERES -- et
# celui-ci entre en prod par la MEME porte que CT_LADDER / CT_TARGET, que la passe corrective venait
# pourtant de fermer. Avec `max_eras=0`, le bras curriculum ne tourne AUCUNE ère et publie le zéro de
# repli du runner, pendant que le bras tabula reste protégé par `max(1, total_eras)` : l'asymétrie
# transformait une absence de mesure en « NUIT » unanime à sign_p=0.031, à dose CONNUE où la bonne
# réponse était TRANSFERE.

def test_un_BUDGET_D_ERES_nul_est_REFUSE_avant_toute_ere():
    for me in (0, -3):
        with pytest.raises(ValueError, match="degenere"):
            run_transfer_experiment([1, 2, 3, 4, 5, 6], ladder=["a", "b"], target="b",
                                    grad_cfg=GraduationConfig(max_eras=me),
                                    run_era_fn=_refus_instantane(), manage_logger=False)


def test_le_plus_petit_budget_LEGITIME_reste_ACCEPTE():
    """CAS NÉGATIF APPARIÉ : `max_eras=1` est le plus petit budget légitime. Une garde qui le
    refuserait aussi rendrait le budget minimal inatteignable — un contrôle qui ne peut plus se
    déclencher est pire que le défaut (classe E1)."""
    res = run_transfer_experiment([1, 2, 3, 4, 5, 6], ladder=["a", "b"], target="b",
                                  grad_cfg=GraduationConfig(max_eras=1),
                                  run_era_fn=_fake_transfert(), manage_logger=False)
    assert res["verdict"] == "TRANSFERE" and res["median_ratio"] == pytest.approx(2.0)
    assert res["per_seed"][0]["total_eras"] == 2


def test_la_PORTE_DE_PROD_CT_MAX_ERAS_est_fermee(monkeypatch):
    """`main()` lit `CT_MAX_ERAS` sans le borner : c'est la porte par laquelle le défaut arrivait en
    production, la même que `CT_LADDER`/`CT_TARGET`. Le refus doit précéder l'acquisition de la base
    (aucun monde, aucun bail `kuzu`)."""
    import tools.curriculum_transfer as ct

    def _interdit(*a, **kw):
        raise AssertionError("garde posée TROP BAS : la base a été acquise avant le refus")

    monkeypatch.setattr(ct, "_acquire_shared_db", _interdit)
    monkeypatch.setattr(ct, "make_run_era_fn", _interdit)
    monkeypatch.setenv("CT_SEEDS", "0,1,2")
    monkeypatch.setenv("CT_MAX_ERAS", "0")
    with pytest.raises(ValueError, match="degenere"):
        ct.main()


def test_la_LIGNE_PUBLIEE_ne_compte_pas_les_seeds_NON_MESURES(tmp_path, monkeypatch, caplog):
    """La ligne imprimée par `main()` est l'artefact que lit un humain. Elle disait
    « INDETERMINE median_ratio=2.000 (n_fav=11/12, sign_p=0.001) » : le `11/12` se relit « un seed a
    DÉFAVORISÉ le curriculum » alors qu'aucune comparaison n'y a eu lieu — c'est le compte fabriqué
    que l'instrument frère a fermé le même jour (`_absent`, tools/cross_world_transfer.py:330).
    Le dénominateur doit être le nombre de seeds MESURÉS, et l'indétermination doit être NOMMÉE."""
    import logging
    monkeypatch.chdir(tmp_path)
    import tools.curriculum_transfer as ct
    monkeypatch.setattr(ct, "run_transfer_experiment", lambda *a, **k: {
        "n": 12, "median_ratio": 2.0, "n_favorable": 11, "sign_p": 0.001, "n_indetermine": 1,
        "verdict": "INDETERMINE", "per_seed": [], "config": {}})
    monkeypatch.setenv("CT_SEEDS", "0")
    with caplog.at_level(logging.INFO, logger="AGIseed.CurriculumTransfer"):
        ct.main()
    ligne = "\n".join(caplog.messages)
    assert "n_fav=11/11 mesures" in ligne, ligne          # DÉNOMINATEUR = seeds mesurés
    assert "n_fav=11/12" not in ligne
    assert "1/12 seed(s) INDETERMINE(S)" in ligne
    assert "ce n'est PAS un effet nul observe" in ligne


def test_la_LIGNE_PUBLIEE_reste_INCHANGEE_quand_TOUT_est_mesure(tmp_path, monkeypatch, caplog):
    """CAS NÉGATIF APPARIÉ (classe E1) : sans indétermination, la ligne ne doit RIEN annoncer —
    une mention systématique la rendrait illisible et le signal disparaîtrait dans le bruit."""
    import logging
    monkeypatch.chdir(tmp_path)
    import tools.curriculum_transfer as ct
    monkeypatch.setattr(ct, "run_transfer_experiment", lambda *a, **k: {
        "n": 12, "median_ratio": 2.0, "n_favorable": 12, "sign_p": 0.001, "n_indetermine": 0,
        "verdict": "TRANSFERE", "per_seed": [], "config": {}})
    monkeypatch.setenv("CT_SEEDS", "0")
    with caplog.at_level(logging.INFO, logger="AGIseed.CurriculumTransfer"):
        ct.main()
    ligne = "\n".join(caplog.messages)
    assert "n_fav=12/12 mesures" in ligne and "INDETERMINE" not in ligne, ligne


def test_verdict_SANS_indetermination_est_INCHANGE():
    """CAS NÉGATIF APPARIÉ / non-régression : sans indétermination, les trois verdicts de fond
    restent atteignables et la cohorte VIDE garde son comportement historique — ce dernier point est
    un défaut CONNU mais laissé OUVERT à dessein : il est le sujet d'un xfail strict d'un AUTRE
    fichier (tests/sandbox/test_inj_run_direction.py:325, défaut de tools/cross_world_transfer.py)
    et le fermer ici clôturerait cette dette-là à son insu."""
    assert compute_transfer_verdict([1.5] * 6)["verdict"] == "TRANSFERE"
    assert compute_transfer_verdict([0.5] * 6)["verdict"] == "NUIT"
    assert compute_transfer_verdict([1.01] * 6)["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([1.5] * 6)["n_indetermine"] == 0
    assert compute_transfer_verdict([])["verdict"] == "NEUTRE"
