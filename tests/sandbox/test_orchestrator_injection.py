# -*- coding: utf-8 -*-
"""P2.48 (2026-09-07) -- calibration par INJECTION A DOSE CONNUE des ORCHESTRATEURS.

Un orchestrateur ne simule pas : il APPELLE des mesures et les AGREGE en affirmation. La garde
d'ARGUMENTS posee le 2026-09-06 (P2.46) ne couvrait que l'entree ; la couche qui transforme des
mesures en verdict -- appariement, correction de famille, unite de replication, branches de
verdict -- n'avait ete confrontee a aucune reponse connue. C'est exactement la ou un instrument non
calibre ne se contente pas d'echouer : il PRODUIT un resultat.

TECHNIQUE (celle des 13 orchestrateurs de monde du 2026-09-01, generalisee) : on monkeypatche
l'attribut de MODULE que l'orchestrateur appelle, on impose des cellules a DOSE CONNUE, et on exige
le verdict en forme close -- branches NEGATIVES comprises (sans elles, classe E1 : un test qui ne
peut pas echouer). Aucun monde n'est construit : le cout est nul.

CONTROLE E1 PAR MUTATION (2026-09-07) : chaque test passant a ete confronte a un orchestrateur rendu
AVEUGLE A LA DOSE ; 6/6 des tests concernes meurent alors. Un test qui survit a la mutation ne
mesure pas ce qu'il croit.

Les `xfail(strict=True)` qui subsistent sont des DEFAUTS REELS non corriges : ils tiennent la dette
ouverte et tomberont d'eux-memes le jour ou le defaut sera corrige (strict = XPASS est un echec).
Les blocs marques NON-REGRESSION sont d'anciens xfail dont le defaut a ete CORRIGE le 2026-09-07.
"""
import pytest



# ======================================================================================================
# P2.48 : `tools/s2_demand.py::run_s2` -- l'ORCHESTRATEUR qui prononce le verdict S2 EXIGE/VOID publie
# par EDR-124 (le plus cite du depot). Il ne simule pas : il appelle `run_condition` (6 conditions x N
# mondes) et AGREGE en verdict. Sa garde d'ARGUMENTS etait calibree (P2.46) mais AUCUNE de ses branches
# de verdict ne l'etait -- or c'est LA que se decide ce qui est publie.
# Calibre par INJECTION A DOSE CONNUE : on impose les cellules de `run_condition` (aucun monde n'est
# construit, aucune simulation) et on verifie que le verdict tombe JUSTE -- branches NEGATIVES incluses
# (VOID, AMBIGU, absence de `within`), sans lesquelles le test ne prouverait rien (classe E1).
# ======================================================================================================


_INJ0_GENOME = "GENOME-CHAMPION-FACTICE"      # sentinelle : distingue champion (genome) de random_genome
_INJ0_SAVES = []                              # rapports passes a Harness.save (le harnais est factice)


class _Inj0Harness:
    """Harness factice : `run_s2` s'execute DANS un `with Harness(...)` et appelle `h.save(report)`.
    Le vrai ouvre le logger async / KuzuDB et ECRIT dans l'arbre -> on l'injecte (et on verifie que
    le rapport rendu est bien celui qui a ete SAUVE : un rapport enrichi apres le save serait publie
    sans etre archive)."""

    def __init__(self, **kw):
        self.kw = kw

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def save(self, report):
        _INJ0_SAVES.append(report)


def _inj0_cellule(niveau, K=12, n=1, etale=2.0, life=None):
    """Cellule factice de `run_condition` a DOSE CONNUE, portant TOUTES les cles que l'aval lit :
    `survival` / `life_score` (individus pooles -> Cliff delta) et `era_survival` / `era_life`
    (une valeur PAR ERE -> l'appariement seed-a-seed du Wilcoxon, l'unite de replication du depot),
    plus `censored_frac`. Survie etalee de +-`etale` autour de `niveau` ; medianes d'ere legerement
    variables (sinon les rangs du Wilcoxon sont degeneres). Bras volontairement PETIT (n=1
    individu par ere) : le bootstrap de `_compare` est a 2000 tirages et couterait ~2x plus cher a
    24 individus, alors que la dose est choisie pour rendre le verdict en FORME CLOSE (Cliff +-1 ou
    sous-seuil, p=0.0025 a 12 eres) -- pas pour imiter une cohorte."""
    life = (niveau / 10.0) if life is None else life
    m = K * n
    survival = [float(niveau - etale + (2.0 * etale) * i / (m - 1)) for i in range(m)]
    era_survival = [float(niveau + ((i % 3) - 1)) for i in range(K)]
    life_score = [float(life - 0.2 + 0.4 * i / (m - 1)) for i in range(m)]
    era_life = [float(life + 0.1 * ((i % 3) - 1)) for i in range(K)]
    return {"survival": survival, "life_score": life_score, "era_survival": era_survival,
            "era_life": era_life, "censored_frac": 0.0}


def _inj0_grille(champion, random_action=None, random_genome=None, reflex_naive=None,
                 reflex_prudent=None, champion_obs_ablated=None):
    """Les 6 cellules d'UN monde (les 6 cles de CONDITIONS). Defaut = la cellule random_action :
    on ne veut jamais qu'une condition oubliee devienne un `None` silencieux."""
    base = random_action if random_action is not None else champion
    return {"champion": champion,
            "random_action": base,
            "random_genome": random_genome if random_genome is not None else base,
            "reflex_naive": reflex_naive if reflex_naive is not None else base,
            "reflex_prudent": reflex_prudent if reflex_prudent is not None else base,
            "champion_obs_ablated": champion_obs_ablated if champion_obs_ablated is not None else base}


def _inj0_injecte(monkeypatch, grilles, pilote=None, journal=None):
    """Remplace, DANS `tools.s2_demand`, tout ce qui touche le monde ou le disque :
      - `run_condition` -> rend la cellule imposee, identifiee par (batch_model_cls, genome is None)
        via l'inverse de CONDITIONS (si CONDITIONS change, le KeyError le dit tout de suite) ;
      - `load_champion_genome` -> sentinelle (le HoF n'est pas lu) ;
      - `Harness` / `_git_short_commit` -> factices (aucune ecriture, aucun appel git) ;
      - `pilot_required_k` -> INTERDIT si K est fourni (branche exclusive), sinon la dose donnee.
    `grilles` = {nom_du_monde: grille}. Renvoie le module."""
    import tools.s2_demand as S
    inverse = {(spec["batch_model_cls"], spec["fresh_genome"]): nom
               for nom, spec in S.CONDITIONS.items()}
    assert len(inverse) == len(S.CONDITIONS), "deux conditions indiscernables : injection ambigue"
    monde_de = {S.WORLDS[w]: w for w in grilles}

    def _fake_run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20,
                            max_ticks=400, n_eras=1, config=None):
        nom = inverse[(batch_model_cls, genome is None)]
        if journal is not None:
            journal.append({"monde": monde_de[world_cls], "cond": nom, "seed": seed,
                            "n_eras": n_eras, "num_agents": num_agents, "max_ticks": max_ticks,
                            "genome": genome})
        return grilles[monde_de[world_cls]][nom]

    def _pilote_interdit(*a, **kw):
        raise AssertionError("pilot_required_k appele alors que K est FOURNI (branche exclusive)")

    del _INJ0_SAVES[:]
    monkeypatch.setattr(S, "run_condition", _fake_run_condition)
    monkeypatch.setattr(S, "load_champion_genome", lambda: _INJ0_GENOME)
    monkeypatch.setattr(S, "_git_short_commit", lambda: "inj0cal")
    monkeypatch.setattr(S, "Harness", _Inj0Harness)
    monkeypatch.setattr(S, "pilot_required_k", pilote if pilote is not None else _pilote_interdit)
    return S


# ---------------------------------------------------------------------------------------------------
# 1. Les trois verdicts que le code peut rendre, a dose imposee.
# ---------------------------------------------------------------------------------------------------

def test_run_s2_READS_the_dose_of_survival_it_claims(monkeypatch):
    """Reponse connue x3, une par branche de `verdict_from_survival_cmps` telle que `run_s2` la cable :
      EXIGE  : champion 100 ticks vs baselines 20 -> Cliff delta = +1 (aucun chevauchement) et p
               apparie 0.0025 sur 12 eres (forme close du Wilcoxon signe a n=12, tous rangs egaux).
      AMBIGU : champion 50 vs baselines 49, etendue +-12 -> l'effet est REEL et significatif (les 12
               eres sont toutes en faveur du champion) mais le Cliff pooled est SOUS le seuil 0.33.
               C'est la branche qui empeche de publier EXIGE sur un decalage d'un tick.
      VOID   : un baseline DOMINE le champion (Cliff < 0) -> incoherence, pas de verdict.
    Sans les branches negatives, un instrument qui rendrait EXIGE quoi qu'il arrive passerait (E1)."""
    from tools.s2_demand import run_s2

    cas = (
        ("EXIGE", _inj0_grille(champion=_inj0_cellule(100.0), random_action=_inj0_cellule(20.0))),
        ("AMBIGU", _inj0_grille(champion=_inj0_cellule(50.0, etale=12.0),
                                random_action=_inj0_cellule(49.0, etale=12.0))),
        ("VOID", _inj0_grille(champion=_inj0_cellule(20.0), random_action=_inj0_cellule(100.0))),
    )
    for attendu, grille in cas:
        _inj0_injecte(monkeypatch, {"soup": grille})
        rep = run_s2(worlds=["soup"], seed=2026, K=12, num_agents=20, max_ticks=400)
        w = rep["worlds"]["soup"]
        assert w["verdict"] == attendu, (attendu, w["verdict"], w["p_monde"], w["cliff"])
        assert w["coherence_basis"] == "survival"           # addendum 2026-06-30, pas l'ancien gate
        assert w["censored_frac_champion"] == 0.0           # la censure du CHAMPION, pas d'un baseline


def test_run_s2_REFUSES_to_let_the_lifescore_gate_fabricate_a_VOID(monkeypatch):
    """LA raison d'etre de l'addendum date du 2026-06-30 (EDR-124) : `s2_verdict` tranche encore sur
    le life_score et rend VOID des que l'edge life_score est noye (evenements rares/chanceux) ; ici on
    impose EXACTEMENT ce cas -- life_score IDENTIQUE partout (p=1.0, Cliff=0 -> l'ancien gate dit VOID)
    tandis que la survie est 100 vs 20. `run_s2` doit re-rendre le verdict depuis la SURVIE (EXIGE) et
    ne garder le life_score que comme corroborant NON bloquant. Si quelqu'un recablait `run_s2` sur
    `v["verdict"]`, ce test tombe -- et c'est un faux negatif publie sur le record le plus cite."""
    from tools.s2_demand import run_s2

    grille = _inj0_grille(champion=_inj0_cellule(100.0, life=1.0),
                          random_action=_inj0_cellule(20.0, life=1.0))
    _inj0_injecte(monkeypatch, {"soup": grille})
    rep = run_s2(worlds=["soup"], seed=2026, K=12)
    w = rep["worlds"]["soup"]
    assert w["verdict"] == "EXIGE", w
    assert w["coherence_ok_lifescore"] is False             # trace de ce qu'aurait tranche l'ancien gate
    assert w["life_p"] == 1.0 and w["p_monde"] < 0.05       # corroborant nul, verdict porte par la survie


# ---------------------------------------------------------------------------------------------------
# 2. Les decisions d'AGREGATION propres a `run_s2` (ce que les stats en aval ne peuvent pas verifier).
# ---------------------------------------------------------------------------------------------------

def test_run_s2_TAKES_the_high_bound_of_the_reflex_not_the_first_variant(monkeypatch):
    """Spec section 5 : le reflexe oppose au champion est la variante a plus haute survie mediane
    (borne HAUTE), pas `reflex_naive`. Dose choisie pour que les deux lectures soient INCOMPATIBLES :
    naif 20 (le champion 100 le domine) / prudent 200 (il domine le champion).
      - lecture correcte (max) -> le prudent entre dans la famille -> Cliff < 0 -> VOID ;
      - lecture cassee (naif)  -> EXIGE serait publie alors qu'un reflexe cable bat le champion.
    Controle apparie : les MEMES conditions avec prudent ramene a 20 doivent rendre EXIGE (sinon le
    test passerait pour une raison etrangere a la selection)."""
    from tools.s2_demand import run_s2

    champ = _inj0_cellule(100.0)
    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(
        champion=champ, random_action=_inj0_cellule(20.0),
        reflex_naive=_inj0_cellule(20.0), reflex_prudent=_inj0_cellule(200.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "VOID" and w["strongest_baseline"] == "reflex", w

    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(
        champion=champ, random_action=_inj0_cellule(20.0),
        reflex_naive=_inj0_cellule(20.0), reflex_prudent=_inj0_cellule(20.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "EXIGE", w


def test_run_s2_ATTACHES_the_within_block_only_when_the_verdict_is_not_VOID(monkeypatch):
    """Deux choses en une reponse connue.
    (a) Branche : `within` (ablation-perception) n'a de sens que si le champion se comporte en
        champion -> present si non-VOID, ABSENT si VOID. Un bloc causal calcule sous un champion
        incoherent serait un verdict causal fabrique.
    (b) Cablage des 3 bras : la dose separe les mauvais appariements. champion 100, ablate 20,
        random_action 20 (cellule IDENTIQUE a l'ablate -> Cliff residuel EXACTEMENT 0) et
        random_genome 60. Verdict attendu CAUSAL-FULL ; si le 3e bras etait `random_genome`, le
        residuel vaudrait -1 et le verdict serait CAUSAL-CRITIQUE. Les deux lectures sont donc
        discriminees."""
    from tools.s2_demand import run_s2

    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(
        champion=_inj0_cellule(100.0), random_action=_inj0_cellule(20.0),
        random_genome=_inj0_cellule(60.0), reflex_naive=_inj0_cellule(20.0),
        reflex_prudent=_inj0_cellule(20.0), champion_obs_ablated=_inj0_cellule(20.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "EXIGE"
    assert w["within"]["verdict"] == "CAUSAL-FULL", w["within"]
    assert w["within"]["residual_cmp"]["cliff"] == 0.0      # ablate == random_action, pas random_genome

    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(
        champion=_inj0_cellule(20.0), random_action=_inj0_cellule(100.0),
        champion_obs_ablated=_inj0_cellule(5.0))})
    w = run_s2(worlds=["soup"], seed=2026, K=12)["worlds"]["soup"]
    assert w["verdict"] == "VOID" and "within" not in w, w


def test_run_s2_CORRECTS_the_whole_family_of_worlds_including_the_VOID_ones(monkeypatch):
    """Le commentaire du code interdit de selectionner la famille A POSTERIORI sur le non-VOID (ce
    serait du p-hacking). Reponse connue en forme close : 2 mondes decides, p_monde identique p
    -> Holm rend 2p pour les DEUX. Le monde VOID doit compter dans la famille : s'il etait exclu,
    m vaudrait 1 et le monde EXIGE verrait son p NON corrige (2p au lieu de p = la difference
    exacte que ce test mesure)."""
    from tools.s2_demand import run_s2

    grilles = {
        "soup": _inj0_grille(champion=_inj0_cellule(100.0), random_action=_inj0_cellule(20.0)),
        "famine": _inj0_grille(champion=_inj0_cellule(20.0), random_action=_inj0_cellule(100.0)),
    }
    _inj0_injecte(monkeypatch, grilles)
    rep = run_s2(worlds=["soup", "famine"], seed=2026, K=12)
    a, b = rep["worlds"]["soup"], rep["worlds"]["famine"]
    assert a["verdict"] == "EXIGE" and b["verdict"] == "VOID"
    assert a["p_monde"] == pytest.approx(b["p_monde"])                       # dose symetrique
    assert a["p_monde_holm"] == pytest.approx(2.0 * a["p_monde"])            # m=2 -> le VOID compte
    assert b["p_monde_holm"] == pytest.approx(2.0 * b["p_monde"])
    assert _INJ0_SAVES and _INJ0_SAVES[-1] is rep                            # ce qui est rendu EST archive


def test_run_s2_WIRES_the_pilot_K_into_the_runs_it_launches(monkeypatch):
    """K=None -> le K vient du pilote (power analysis) et doit ARRIVER dans les runs : reponse connue
    K_pilote=17 -> les 6 conditions du monde recoivent n_eras=17 et le rapport annonce K=17. Un K
    annonce mais non transmis sous-alimenterait le design sans que rien ne le signale. Controle :
    avec K fourni, le pilote ne doit PAS etre appele (l'injection le fait lever) et n_eras=K.
    On verifie aussi que le genome du champion (sentinelle du HoF) va aux 2 conditions champion et
    a AUCUNE autre -- l'appariement qui distingue `champion` de `random_genome`."""
    from tools.s2_demand import run_s2

    journal, vus = [], []

    def _pilote(world_cls, genome, seed, k_pilot=5):
        vus.append((world_cls, genome, seed))
        return 17

    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(champion=_inj0_cellule(100.0),
                                                    random_action=_inj0_cellule(20.0))},
                  pilote=_pilote, journal=journal)
    rep = run_s2(worlds=["soup"], seed=2026, K=None)
    assert rep["K"]["soup"] == 17
    assert len(journal) == 6 and {j["n_eras"] for j in journal} == {17}
    assert len(vus) == 1 and vus[0][1] == _INJ0_GENOME and vus[0][2] == 2026
    avec_genome = {j["cond"] for j in journal if j["genome"] is _INJ0_GENOME}
    assert avec_genome == {"champion", "champion_obs_ablated"}, avec_genome

    journal2 = []
    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(champion=_inj0_cellule(100.0),
                                                    random_action=_inj0_cellule(20.0))},
                  journal=journal2)
    rep = run_s2(worlds=["soup"], seed=2026, K=9, num_agents=7, max_ticks=33)
    assert rep["K"]["soup"] == 9
    assert {j["n_eras"] for j in journal2} == {9}
    assert {j["num_agents"] for j in journal2} == {7} and {j["max_ticks"] for j in journal2} == {33}
    # le SEED d'appariement doit arriver identique aux 6 conditions : c'est lui qui rend le design
    # apparie (meme monde, meme init) -- un seed decale par condition casserait l'appariement sans
    # rien changer au verdict rendu, donc en silence.
    assert {j["seed"] for j in journal2} == {2026}, journal2


# ---------------------------------------------------------------------------------------------------
# 3. LE CAS DEGENERE -- defaut REEL, expose (regle : une entree degeneree rend INDETERMINE ou leve
#    EXPLICITEMENT, jamais un negatif de fond ni un plantage de cle).
# ---------------------------------------------------------------------------------------------------

# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : `run_s2` DETRUISAIT le seul verdict d'indetermination de la chaine : `s2_verdict` rend INCONCLUSIVE_DEGENERATE sans cle 'survival', et l'orchestrateur la lisait quand meme (KeyError).
def test_run_s2_REPORTS_INCONCLUSIVE_DEGENERATE_when_both_arms_are_constant(monkeypatch):
    """Reponse connue : tout le monde meurt au meme tick (champion 3, baselines 2, variance NULLE des
    deux cotes). Cliff delta y vaut +-1 MECANIQUEMENT et le p est celui d'un vrai signal -- c'est
    exactement le cas mesure le 2026-09-01 qui a fait armer la garde de degenerescence. Le verdict
    attendu est INCONCLUSIVE_DEGENERATE, pas EXIGE et pas une exception de cle."""
    from tools.s2_demand import run_s2

    def _plat(v):
        return {"survival": [float(v)] * 24, "life_score": [1.0] * 24,
                "era_survival": [float(v)] * 12, "era_life": [1.0] * 12, "censored_frac": 0.0}

    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(champion=_plat(3), random_action=_plat(2))})
    rep = run_s2(worlds=["soup"], seed=2026, K=12)
    assert rep["worlds"]["soup"]["verdict"] == "INCONCLUSIVE_DEGENERATE", rep["worlds"]["soup"]


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : MEME defaut, autre porte : cohorte champion VIDE (extinction totale) -> meme KeyError.
def test_run_s2_REPORTS_INCONCLUSIVE_DEGENERATE_on_an_empty_measured_cohort(monkeypatch):
    """Reponse connue : la cellule champion ne contient AUCUN individu. Il n'y a rien a comparer ->
    verdict d'indetermination attendu ; ce que le code fait aujourd'hui, c'est une KeyError (et, si
    la ligne 183 etait corrigee en `v.get('survival', {})`, un `max()` sur dict vide)."""
    from tools.s2_demand import run_s2

    vide = {"survival": [], "life_score": [], "era_survival": [], "era_life": [], "censored_frac": 0.0}
    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(champion=vide,
                                                    random_action=_inj0_cellule(20.0))})
    rep = run_s2(worlds=["soup"], seed=2026, K=12)
    assert rep["worlds"]["soup"]["verdict"] == "INCONCLUSIVE_DEGENERATE", rep["worlds"]["soup"]


# NON-REGRESSION (defaut CORRIGE le 2026-09-07) : worlds=[] lancait la grille COMPLETE (`worlds or list(WORLDS)`).
def test_run_s2_REFUSES_an_EMPTY_world_list_instead_of_running_the_WHOLE_grid(monkeypatch):
    """Reponse connue : une famille de mondes VIDE ne peut produire aucun verdict -> refus attendu.
    Le `run_condition` injecte explose au PREMIER appel : le cout du test est nul, et le message dit
    exactement ce qui se passe aujourd'hui (la grille entiere demarre sur `soup`)."""
    from tools.s2_demand import run_s2

    def _sentinelle(world_cls, *a, **kw):
        raise AssertionError(
            f"worlds=[] a lance un run sur {world_cls.__name__} : la liste vide a ete remplacee par "
            "les 5 mondes du dict WORLDS (des heures de simulation pour une selection vide)")

    _inj0_injecte(monkeypatch, {"soup": _inj0_grille(champion=_inj0_cellule(100.0),
                                                    random_action=_inj0_cellule(20.0))})
    monkeypatch.setattr("tools.s2_demand.run_condition", _sentinelle)
    with pytest.raises(ValueError, match="degenere"):
        run_s2(worlds=[], seed=2026, K=12)


# NON-REGRESSION (defaut CORRIGE le 2026-09-07) : `worlds` etait ITERE DEUX FOIS -> en iterateur, la correction de Holm disparaissait EN SILENCE.
def test_run_s2_KEEPS_the_Holm_correction_when_worlds_is_an_ITERATOR(monkeypatch):
    """Reponse connue : 2 mondes a dose symetrique -> chacun doit recevoir p_monde_holm = 2 x p_monde
    (c'est ce que le test de famille verifie sur une LISTE). Passes en generateur, les deux mondes
    sont mesures normalement mais publient un p NON corrige."""
    from tools.s2_demand import run_s2

    grilles = {
        "soup": _inj0_grille(champion=_inj0_cellule(100.0), random_action=_inj0_cellule(20.0)),
        "famine": _inj0_grille(champion=_inj0_cellule(100.0), random_action=_inj0_cellule(20.0)),
    }
    _inj0_injecte(monkeypatch, grilles)
    rep = run_s2(worlds=(w for w in ("soup", "famine")), seed=2026, K=12)
    assert set(rep["worlds"]) == {"soup", "famine"}          # les mesures, elles, ont bien eu lieu
    for w in ("soup", "famine"):
        v = rep["worlds"][w]
        assert "p_monde_holm" in v, (
            f"{w} publie p_monde={v['p_monde']:.6f} SANS correction de famille : la multiplicite a "
            "ete perdue en silence")
        assert v["p_monde_holm"] == pytest.approx(2.0 * v["p_monde"])


# ---------------------------------------------------------------------------------------------------
# P2.40 (2026-09-07) : `tools/s2_openloop_probe.run_openloop_ladder` -- ORCHESTRATEUR de l'echelle
# S2-003 (permuted -> noise -> zero). Il ne simule PAS : il appelle `run_condition` (attribut de
# MODULE, importe en tete via `from tools.s2_demand import run_condition`) et AGREGE trois dicts
# `ablation_verdict` en UN verdict de monde. Sa garde d'arguments etait testee ; ses QUATRE branches
# de verdict ne l'etaient par rien.
#
# TECHNIQUE : injection a DOSE CONNUE. On monkeypatche `s2_openloop_probe.run_condition` et
# `s2_openloop_probe.load_champion_genome` (les deux seuls seams de simulation) et on laisse REELS
# `ablation_verdict` et `_floor_for` -- c'est justement la couche « mesures -> affirmation » qu'on
# veut calibrer. Les survies par ere sont imposees, donc le ratio de medianes est connu en forme
# close, et chaque branche NEGATIVE est exigee (sans elles le test ne prouverait rien, classe E1).
#
# Regime de mesure : `_floor_for` ne rend un plancher QUE a (num_agents=12, max_ticks=200). Les tests
# qui veulent un plancher ACTIF prennent ce point ; ceux qui veulent l'eteindre prennent 13/200.
# ---------------------------------------------------------------------------------------------------


def _inj1_cellule(era_survival):
    """Cellule factice portant TOUTES les cles que `run_condition` rend et que l'orchestrateur peut
    lire (`era_survival` est la seule lue, les autres documentent le contrat)."""
    era = [float(x) for x in era_survival]
    return {"survival": era, "life_score": era, "era_survival": era, "era_life": era,
            "censored_frac": 0.0}


_INJ1_GENOME = "GENOME-CHAMPION-FACTICE-INJ1"   # sentinelle : les 4 barreaux doivent recevoir CE genome


def _inj1_injecte(monkeypatch, table, compteur=None, journal=None):
    """Impose une survie par ere a CHAQUE barreau de l'echelle, par dispatch sur (monde, barreau).

    `table` : soit {"intact"|"permuted"|"noise"|"zero": [survies par ere]} (la MEME echelle pour tous
    les mondes), soit {nom_de_monde: {barreau: [...]}} -- forme OBLIGATOIRE des qu'on teste plusieurs
    mondes, sinon un croisement de mondes serait INVISIBLE (le premier jet de ce test donnait la meme
    echelle aux deux mondes : il ne prouvait donc pas ce que sa docstring annoncait). Renvoie le module.
    """
    import tools.s2_openloop_probe as P
    par_monde = all(isinstance(v, dict) for v in table.values())
    monde_de = {P.WORLDS[w]: w for w in (table if par_monde else P.WORLDS)}

    def _run_condition(world_cls, batch_model_cls, genome, seed, num_agents=20, max_ticks=400,
                       n_eras=1, config=None):
        if compteur is not None:
            compteur.append((world_cls, batch_model_cls))
        if batch_model_cls is None:
            cle = "intact"
        elif batch_model_cls is P.PerceptionAblatedMamba:
            cle = "permuted"
        elif batch_model_cls is P.NoiseObsMamba:
            cle = "noise"
        elif batch_model_cls is P.ZeroObsMamba:
            cle = "zero"
        else:                                   # pragma: no cover - un 4e barreau non prevu
            raise AssertionError("barreau inconnu : {}".format(batch_model_cls))
        if journal is not None:
            journal.append({"monde": monde_de[world_cls], "barreau": cle, "genome": genome,
                            "seed": seed, "n_eras": n_eras, "num_agents": num_agents,
                            "max_ticks": max_ticks})
        cellules = table[monde_de[world_cls]] if par_monde else table
        return _inj1_cellule(cellules[cle])

    monkeypatch.setattr(P, "run_condition", _run_condition)
    monkeypatch.setattr(P, "load_champion_genome", lambda: _INJ1_GENOME)
    return P


def test_run_openloop_ladder_READS_the_three_rung_ladder_it_claims(monkeypatch):
    """Reponse connue x3, en forme close (ratio = mediane_intact / mediane_ablatee), au regime
    13 agents / 200 ticks ou `_floor_for` rend None -- donc aucun plancher ne peut fabriquer la
    degenerescence, et les trois branches NON degenerees sont isolees.

    * SURVIVAL_NEUTRAL : les 3 barreaux a 40/39 = 1.026, dans [1/1.3, 1.3] -> les 3 sont des leurres.
    * SURVIVAL_SENSITIVE : `zero` a 40/10 = 4.0 >= 1.5 -> au moins un barreau effondre la survie.
      C'est le POSITIF ; sans lui l'instrument pourrait n'avoir qu'une seule issue.
    * MIXED : `noise` a 40/80 = 0.5 < 1/1.3 (INVERSE : l'ablation AMELIORE), les deux autres leurres
      -> ni « tous leurres » ni « un effondrement ». MIXED est la branche que l'on n'atteint QUE par
      un barreau inverse : la verifier interdit qu'elle soit du code mort.
    """
    K = 12                                       # n_floor d'`ablation_verdict` : 12 eres appariees
    cas = (
        ({"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [39.0] * K, "zero": [39.0] * K},
         "SURVIVAL_NEUTRAL"),
        ({"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [39.0] * K, "zero": [10.0] * K},
         "SURVIVAL_SENSITIVE"),
        ({"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [80.0] * K, "zero": [39.0] * K},
         "MIXED"),
    )
    for table, attendu in cas:
        P = _inj1_injecte(monkeypatch, table)
        r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
        assert r["verdict"] == attendu, (attendu, r["verdict"], r["permuted"]["ratio"],
                                         r["noise"]["ratio"], r["zero"]["ratio"])
        assert r["intact_med"] == 40.0, r["intact_med"]


def test_run_openloop_ladder_REFUSES_to_read_a_ladder_whose_intact_arm_is_on_the_floor(monkeypatch):
    """La garde de degenerescence est PRIORITAIRE, et c'est le point le plus fragile de cet
    orchestrateur : un bras intact colle au PLANCHER declare rend les TROIS barreaux illisibles.

    Reponse connue : monde `soup`, plancher no-perception 32.0, ACTIF au seul regime (12, 200).
    Intact a 20.0 (< 32.0) avec `zero` a 5.0 -> le ratio vaut 4.0, donc `collapse` est VRAI : sans la
    priorite, l'instrument publierait SURVIVAL_SENSITIVE (« la perception porte la survie ») a partir
    d'un bras qui n'avait pas d'amplitude. On exige INDETERMINE_DEGENERATE.
    Contre-epreuve du MEME jeu de chiffres HORS du regime de plancher (13 agents) : le plancher
    n'est plus applicable, le verdict redevient SURVIVAL_SENSITIVE -- preuve que c'est bien le
    plancher, et pas les valeurs, qui declenche le refus (garde E8 : jamais un plancher d'ailleurs).
    """
    K = 12
    table = {"intact": [20.0] * K, "permuted": [19.0] * K, "noise": [19.0] * K, "zero": [5.0] * K}
    P = _inj1_injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=12, max_ticks=200)["soup"]
    assert r["verdict"] == "INDETERMINE_DEGENERATE", r["verdict"]
    assert r["zero"]["collapse"] is True and r["zero"]["degenerate"] is True
    assert "PLANCHER" in (r["zero"]["why"] or "")

    P = _inj1_injecte(monkeypatch, table)
    r2 = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r2["verdict"] == "SURVIVAL_SENSITIVE", r2["verdict"]


def test_run_openloop_ladder_REFUSES_a_rung_identical_to_the_intact_arm(monkeypatch):
    """Deuxieme entree de la degenerescence, celle qui ne depend d'AUCUN plancher declare : un
    barreau EXACTEMENT egal au bras intact point par point (S2-007 : matrice identite -> les deux
    bras sont le meme calcul). Reponse connue : `permuted` identique a l'intact et `zero` effondre a
    4.0 -> le verdict de monde doit rester INDETERMINE_DEGENERATE, pas SURVIVAL_SENSITIVE.
    """
    K = 12
    table = {"intact": [40.0] * K, "permuted": [40.0] * K, "noise": [39.0] * K, "zero": [10.0] * K}
    P = _inj1_injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["verdict"] == "INDETERMINE_DEGENERATE", r["verdict"]
    assert r["permuted"]["degenerate"] is True and "IDENTIQUES" in r["permuted"]["why"]


def test_run_openloop_ladder_AGGREGATES_each_world_independently(monkeypatch):
    """Unite de replication : le verdict est par MONDE, pas global. La dose est DIFFERENTE dans chaque
    monde et les deux lectures sont INCOMPATIBLES -- `soup` est plate (les 3 barreaux a 40/39 = 1.026,
    SURVIVAL_NEUTRAL) tandis que `famine` a son barreau `zero` effondre (40/10 = 4.0,
    SURVIVAL_SENSITIVE). Un melange entre mondes (cellules de l'un lues pour l'autre) ou un unique
    verdict global rendrait donc DEUX fois la meme etiquette : c'est ce que ce test interdit.
    NB : la version precedente donnait la MEME echelle aux deux mondes -- elle annoncait cette
    garantie sans pouvoir la tenir (un croisement y etait rigoureusement invisible).
    """
    K = 12
    tables = {
        "soup": {"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [39.0] * K,
                 "zero": [39.0] * K},
        "famine": {"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [39.0] * K,
                   "zero": [10.0] * K},
    }
    appels = []
    P = _inj1_injecte(monkeypatch, tables, compteur=appels)
    out = P.run_openloop_ladder(worlds=["soup", "famine"], K=K, num_agents=13, max_ticks=200)
    assert set(out) == {"soup", "famine"}
    assert out["soup"]["verdict"] == "SURVIVAL_NEUTRAL", out["soup"]
    assert out["famine"]["verdict"] == "SURVIVAL_SENSITIVE", out["famine"]
    assert out["soup"]["zero"]["ratio"] == pytest.approx(40.0 / 39.0)
    assert out["famine"]["zero"]["ratio"] == pytest.approx(4.0)
    assert len(appels) == 8, len(appels)
    assert {P.WORLDS["soup"], P.WORLDS["famine"]} == {w for w, _ in appels}


def test_run_openloop_ladder_WIRES_the_same_champion_and_regime_into_the_FOUR_arms(monkeypatch):
    """L'echelle est WITHIN-SUBJECT : sa validite tient a ce que les 4 bras soient le MEME sujet dans
    le MEME regime, seule la perception changeant. Reponse connue : un appel a K=7 eres, 13 agents,
    111 ticks, seed 4242 doit produire 4 runs portant TOUS la sentinelle du HoF, le meme seed et le
    meme regime, et n'ecrire qu'UNE fois chaque barreau, dans l'ordre declare (intact, permuted,
    noise, zero). Ce que ce test attrape et qu'aucun verdict ne montrerait : un barreau lance avec
    `genome=None` (agents FRAIS) transformerait l'ablation within-subject en comparaison
    between-subject, avec un ratio d'apparence normale ; un `n_eras` qui ne suit pas K
    sous-alimenterait le n_floor=12 sans que rien ne le dise.
    """
    journal = []
    K = 7
    table = {"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [39.0] * K, "zero": [39.0] * K}
    P = _inj1_injecte(monkeypatch, table, journal=journal)
    P.run_openloop_ladder(worlds=["soup"], seed=4242, K=K, num_agents=13, max_ticks=111)

    assert [j["barreau"] for j in journal] == ["intact", "permuted", "noise", "zero"], journal
    assert all(j["genome"] == _INJ1_GENOME for j in journal), (
        "un bras n'a PAS recu le genome du champion : l'ablation n'est plus within-subject")
    assert {j["seed"] for j in journal} == {4242}
    assert {j["n_eras"] for j in journal} == {K}
    assert {j["num_agents"] for j in journal} == {13}
    assert {j["max_ticks"] for j in journal} == {111}


def test_run_openloop_ladder_REFUSES_degenerate_arguments_BEFORE_any_run(monkeypatch):
    """La garde d'arguments doit lever AVANT la moindre simulation : un `run_condition` piege
    (il explose s'il est atteint) prouve OU la garde est posee, pas seulement QU'elle leve. Trois
    doses : K=0, num_agents=0, max_ticks=0.
    """
    import tools.s2_openloop_probe as P

    def _piege(*a, **kw):                        # pragma: no cover - ne doit jamais etre atteint
        raise AssertionError("run_condition atteint : la garde d'arguments est posee TROP TARD")

    monkeypatch.setattr(P, "run_condition", _piege)
    monkeypatch.setattr(P, "load_champion_genome", _piege)
    for kw in ({"K": 0}, {"num_agents": 0}, {"max_ticks": 0}):
        with pytest.raises(ValueError, match="degenere"):
            P.run_openloop_ladder(worlds=["soup"], **kw)


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : une echelle SANS amplitude produisait le verdict de FOND MIXED et publiait intact_med=0.0 comme une MESURE.
def test_run_openloop_ladder_REFUSES_a_ladder_with_no_amplitude_at_all(monkeypatch):
    """Reponse connue : les 4 conditions a survie ~0 (aucune amplitude mesurable). Aucun plancher
    n'est declare a ce regime (13 agents), et les bras ne sont pas point-par-point identiques, donc
    aucune des deux entrees de `_degeneracy` ne mord."""
    K = 12
    table = {"intact": [0.0] * K, "permuted": [0.0] * (K - 1) + [1.0],
             "noise": [0.0] * (K - 1) + [2.0], "zero": [0.0] * (K - 1) + [3.0]}
    P = _inj1_injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert r["verdict"] == "INDETERMINE_DEGENERATE", (r["verdict"], r["intact_med"])


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : l'orchestrateur lisait les booleens BRUTS decoy/collapse, contournant le garde-fou de puissance n_floor=12 : a K=3 les TROIS barreaux etaient INCONCLUSIVE et le monde recevait SURVIVAL_NEUTRAL.
def test_run_openloop_ladder_REFUSES_an_underpowered_ladder(monkeypatch):
    """Reponse connue : meme echelle plate que le cas SURVIVAL_NEUTRAL, mais K=3 au lieu de 12."""
    K = 3
    table = {"intact": [40.0] * K, "permuted": [39.0] * K, "noise": [39.0] * K, "zero": [39.0] * K}
    P = _inj1_injecte(monkeypatch, table)
    r = P.run_openloop_ladder(worlds=["soup"], K=K, num_agents=13, max_ticks=200)["soup"]
    assert all(r[b]["verdict"] == "INCONCLUSIVE" for b in ("permuted", "noise", "zero")), r
    assert r["verdict"] != "SURVIVAL_NEUTRAL", r["verdict"]


# NON-REGRESSION (defaut CORRIGE le 2026-09-07) : worlds=[] rendait {} sans lever -> `main` en tirait DEUX affirmations de fond depuis zero mesure.
def test_run_openloop_ladder_REFUSES_an_EMPTY_world_family(monkeypatch):
    """Reponse connue : sans monde, il n'y a rien a mesurer -> refus attendu. Le `run_condition`
    injecte explose s'il est atteint : le cout du test est nul dans les deux issues."""
    import tools.s2_openloop_probe as P

    def _piege(*a, **kw):                        # pragma: no cover - ne doit jamais etre atteint
        raise AssertionError("run_condition atteint alors que la famille de mondes est VIDE")

    monkeypatch.setattr(P, "run_condition", _piege)
    monkeypatch.setattr(P, "load_champion_genome", lambda: _INJ1_GENOME)
    with pytest.raises(ValueError, match="degenere"):
        P.run_openloop_ladder(worlds=[], K=12, num_agents=13, max_ticks=200)


# P2.40 (2026-09-07) : `tools/dream_causal_probe.py::run_causal` -- l'ORCHESTRATEUR de la sonde
# causale du dreaming (arc DREAM, EDR-093/094/095, porte SDR-G4). Il ne simule pas : il pose
# l'intervention `MambaBatchModel.FORCE_DREAM`, appelle `run_era_organ` par (seed, bras) et AGREGE
# en verdict causal. Sa garde d'arguments etait calibree ; ses BRANCHES DE VERDICT ne l'etaient par
# personne -- `dose_response_verdict` est calibre en PUR (P2.2), mais rien ne prouvait que
# l'orchestrateur lui livre les bonnes cellules, ni qu'il pose reellement l'intervention.
#
# TECHNIQUE : injection a DOSE CONNUE. `run_era_organ` et `survival_competence` sont importes AU
# NIVEAU MODULE (`from tools.dreaming_probe import run_era_organ`) -> l'attribut a monkeypatcher est
# `tools.dream_causal_probe.run_era_organ`, pas le module source. On laisse `survival_competence`
# REELLE (mediane des ages / AGE_REF=200) : la dose s'impose donc en AGES, et une couche de plus est
# testee gratuitement. La fausse ere LIT `MambaBatchModel.FORCE_DREAM` pour connaitre son bras :
# c'est le seul canal par lequel l'intervention voyage, donc un orchestrateur qui oublierait de la
# poser rendrait quatre bras IDENTIQUES -- l'injection le verrait.


_INJ2_AGE_REF = 200.0          # src/curriculum/competence.AGE_REF


def _inj2_stats(competence):
    """Cellule factice : la liste d'agents que `run_era_organ` rend et que `survival_competence`
    (mediane des ages / 200, clampee) transforme en competence de survie. Une seule entree suffit :
    la mediane d'un singleton est exacte, donc la dose imposee est EXACTE."""
    return [{"age": float(competence) * _INJ2_AGE_REF, "founder": True}]


def _inj2_injecte(monkeypatch, doses, journal=None):
    """Remplace `run_era_organ` DANS le module de la sonde par une fausse ere a dose connue.

    `doses` : dict bras -> competence imposee ("off" et les K entiers). La fausse ere LIT
    `MambaBatchModel.FORCE_DREAM` : si l'orchestrateur ne posait pas l'intervention, tous les bras
    recevraient la meme dose."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    def _fausse_ere(target, seed, organ_fraction=None, metab=None, payoff=None,
                    num_agents=None, max_ticks=None, shared_db=None):
        bras = MambaBatchModel.FORCE_DREAM
        if journal is not None:
            journal.append({"seed": seed, "bras": bras, "target": target,
                            "organ_fraction": organ_fraction, "metab": metab, "payoff": payoff,
                            "num_agents": num_agents, "max_ticks": max_ticks})
        if bras is None:
            bras = "off"                      # l'orchestrateur n'a rien pose : bras indistinct
        return _inj2_stats(doses[bras])

    monkeypatch.setattr(M, "run_era_organ", _fausse_ere)
    return M


def _inj2_run(monkeypatch, doses, n_seeds=10, ks=(1, 4, 8), journal=None):
    M = _inj2_injecte(monkeypatch, doses, journal)
    return M.run_causal(seeds=tuple(range(n_seeds)), target="stoneage", num_agents=4,
                        max_ticks=10, shared_db=None, ks=ks)


def test_run_causal_READS_the_dose_response_it_claims(monkeypatch):
    """Reponse connue x4, en FORME CLOSE : la dose-reponse est imposee, le verdict et le ratio
    doivent suivre a la decimale.

    * off=0.10 / K8=0.15 sur 10 seeds -> ratio EXACTEMENT 1.5, sign_p 10/10 = 0.00195
      -> CAUSE_BENEFIQUE.
    * off=0.10 / K8=0.05 -> ratio 0.5 -> CAUSE_NUISIBLE (la branche NEGATIVE : sans elle le test
      ne prouverait rien, classe E1 -- c'est CE verdict-la qu'a publie EDR-095).
    * bras identiques non nuls -> NEUTRE (specificite : un no-op ne fabrique pas d'effet).
    * tous les bras eteints -> INCONCLUSIVE_DEGENERATE, PAS un negatif de fond : l'absence de
      mesure ne doit jamais ressembler a « le reve nuit »."""
    v = _inj2_run(monkeypatch, {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.15})
    assert v["verdict"] == "CAUSE_BENEFIQUE", v
    assert v["ratio"] == pytest.approx(1.5, rel=1e-9)
    assert v["sign_p"] == pytest.approx(0.001953125, rel=1e-9)
    assert v["n"] == 10 and v["n_favorable"] == 10 and v["n_ecartees"] == 0

    v = _inj2_run(monkeypatch, {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.05})
    assert v["verdict"] == "CAUSE_NUISIBLE", v
    assert v["ratio"] == pytest.approx(0.5, rel=1e-9)
    assert v["n_favorable"] == 0

    v = _inj2_run(monkeypatch, {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.10})
    assert v["verdict"] == "NEUTRE" and v["ratio"] == pytest.approx(1.0, rel=1e-9)

    v = _inj2_run(monkeypatch, {"off": 0.0, 1: 0.0, 4: 0.0, 8: 0.0})
    assert v["verdict"] == "INCONCLUSIVE_DEGENERATE", (
        "des bras tous ETEINTS sont une egalite, pas un argument contre le reve")
    assert v["n_ecartees"] == 10 and v["n"] == 0


def test_run_causal_POSES_the_intervention_and_ANCHORS_on_the_deepest_arm(monkeypatch):
    """Reponse connue : dose-reponse MONOTONE imposee par bras (off .10 / K1 .12 / K4 .14 / K8 .20).

    Ce que ce test protege, et que `dose_response_verdict` seul ne peut pas prouver :
    1. l'intervention est POSEE -- la fausse ere ne connait son bras QUE par
       `MambaBatchModel.FORCE_DREAM` ; un orchestrateur qui oublierait de l'ecrire rendrait quatre
       bras identiques et donc un NEUTRE fabrique ;
    2. la courbe est appariee au bon bras -> ratios_par_K = {1: 1.2, 4: 1.4, 8: 2.0} EXACTEMENT
       (un decalage d'indice les intervertirait) ;
    3. le verdict est ANCRE sur le K le plus profond (2.0), pas sur la moyenne des bras ;
    4. l'ordre des bras vu par la fausse ere est bien ["off", 1, 4, 8] a chaque seed, et le regime
       passe est le SWEET SPOT documente (organe 100 %, metab 0.25, payoff 3.0)."""
    journal = []
    v = _inj2_run(monkeypatch, {"off": 0.10, 1: 0.12, 4: 0.14, 8: 0.20},
                  n_seeds=6, journal=journal)

    assert v["verdict"] == "CAUSE_BENEFIQUE", v
    assert v["ratio"] == pytest.approx(2.0, rel=1e-9), "le verdict n'est pas ancre sur le K max"
    assert v["ratios_par_K"]["1"] == pytest.approx(1.2, rel=1e-9)
    assert v["ratios_par_K"]["4"] == pytest.approx(1.4, rel=1e-9)
    assert v["ratios_par_K"]["8"] == pytest.approx(2.0, rel=1e-9)
    assert set(v["per_arm"]) == {"off", "1", "4", "8"}
    assert v["per_arm"]["8"] == [pytest.approx(0.20)] * 6

    assert [e["bras"] for e in journal[:4]] == ["off", 1, 4, 8], journal[:4]
    assert len(journal) == 6 * 4
    assert {e["seed"] for e in journal} == set(range(6))
    assert all(e["organ_fraction"] == 1.0 and e["metab"] == 0.25 and e["payoff"] == 3.0
               for e in journal), "le regime passe n'est PAS le sweet spot documente"


def test_run_causal_RESTORES_the_global_it_writes_even_when_the_era_RAISES(monkeypatch):
    """`FORCE_DREAM` est un ETAT GLOBAL DE CLASSE (classe E5). S'il fuit a 8, TOUTE simulation
    ulterieure du process reve de force -- silencieusement, et la contamination ressemble a un
    resultat. Reponse connue : apres un run normal ET apres une ere qui LEVE, l'attribut doit etre
    remis a None (c'est le role du `finally`)."""
    import tools.dream_causal_probe as M
    from src.agents.mamba_agent import MambaBatchModel

    MambaBatchModel.FORCE_DREAM = None
    _inj2_run(monkeypatch, {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.15}, n_seeds=2)
    assert MambaBatchModel.FORCE_DREAM is None, "l'intervention a FUI apres un run normal"

    def _ere_qui_leve(*a, **kw):
        assert MambaBatchModel.FORCE_DREAM == "off", "l'intervention n'etait meme pas posee"
        raise RuntimeError("ere interrompue (bail kuzu, OOM, kill)")

    monkeypatch.setattr(M, "run_era_organ", _ere_qui_leve)
    with pytest.raises(RuntimeError):
        M.run_causal(seeds=(0,), target="stoneage", num_agents=4, max_ticks=10,
                     shared_db=None, ks=(8,))
    assert MambaBatchModel.FORCE_DREAM is None, (
        "FORCE_DREAM a FUI apres une ere interrompue : toute mesure suivante du process est "
        "contaminee sans le dire")


def test_run_causal_REFUSES_a_degenerate_cohort_BEFORE_touching_the_world(monkeypatch):
    """Garde d'arguments, et surtout OU elle est posee. Reponse connue : une cohorte vide, une liste
    de K vide, 0 agent ou 0 tick doivent LEVER -- instantanement, sans qu'aucune ere ne soit lancee.
    Une agregation vide serait lue par l'aval comme une mesure (le biais negatif systematique du
    depot). Le refus doit etre INSTANTANE : la fausse ere explose si elle est appelee."""
    import tools.dream_causal_probe as M

    def _interdit(*a, **kw):
        raise AssertionError("la garde est posee APRES la construction du monde")

    monkeypatch.setattr(M, "run_era_organ", _interdit)
    base = dict(target="stoneage", num_agents=4, max_ticks=10, shared_db=None, ks=(1, 4, 8))
    for surcharge in ({"seeds": ()}, {"seeds": (0,), "ks": ()},
                      {"seeds": (0,), "num_agents": 0}, {"seeds": (0,), "max_ticks": 0}):
        kw = {**base, **surcharge}
        with pytest.raises(ValueError, match="degenere"):
            M.run_causal(**kw)


def test_run_causal_at_its_DEFAULT_seed_count_cannot_produce_a_causal_verdict(monkeypatch):
    """QUESTION A DU PRE-VOL, et elle tombe NON. Le verdict exige `sign_p < 0.1` ; le test de signe
    bilateral vaut `2 / 2^n` au mieux, donc 0.25 a n=3, 0.125 a n=4 : **structurellement > 0.1 en
    dessous de 5 seeds**. Or `main()` prend `DC_SEEDS=\"0,1,2\"` par defaut.

    Reponse connue : une dose-reponse ECRASANTE (le bras K8 double la survie, 3/3 seeds favorables)
    rend quand meme NEUTRE a 3 seeds, et CAUSE_BENEFIQUE au meme effet des 5 seeds. La configuration
    par defaut de cette sonde ne peut donc rendre qu'une seule des deux issues."""
    doses = {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.20}
    v3 = _inj2_run(monkeypatch, doses, n_seeds=3)
    assert v3["ratio"] == pytest.approx(2.0) and v3["n_favorable"] == 3
    assert v3["verdict"] == "NEUTRE", v3          # effet double, verdict « pas d'effet »
    assert v3["sign_p"] == pytest.approx(0.25)

    v5 = _inj2_run(monkeypatch, doses, n_seeds=5)
    assert v5["verdict"] == "CAUSE_BENEFIQUE" and v5["sign_p"] == pytest.approx(0.0625)


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : sous 5 seeds le verdict ne POUVAIT etre que NEUTRE (sign_p >= 0.125 par construction) sans que rien ne le distingue d'une egalite mesuree.
def test_run_causal_underpowered_neutral_is_NOT_flagged_as_such(monkeypatch):
    """Le cas DEGENERE en PUISSANCE. Un NEUTRE issu de n=1 (sign_p force a 1.0) est indiscernable,
    dans le champ `verdict`, d'un NEUTRE issu de deux bras strictement egaux sur 10 seeds -- alors
    que le premier ne mesure RIEN. C'est la forme (a) du motif du depot : donnee insuffisante ->
    affirmation NEGATIVE de fond."""
    v1 = _inj2_run(monkeypatch, {"off": 0.05, 1: 0.05, 4: 0.05, 8: 0.50}, n_seeds=1)
    assert v1["ratio"] == pytest.approx(10.0)
    assert v1["verdict"] != "NEUTRE", (
        f"n=1, effet x10, et le verdict rendu est {v1['verdict']} avec sign_p {v1['sign_p']}")


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : un bras-K sans AUCUNE information etait publie ratios_par_K=1.0, soit exactement la valeur qui signifie « aucun effet ».
def test_run_causal_uninformative_arm_is_reported_as_no_effect(monkeypatch):
    """Reponse connue : off et K1/K4 tous eteints, K8 seul vivant. La courbe rendue est
    {1: 1.0, 4: 1.0, 8: 5e4} et se lit « K1 et K4 neutres, K8 spectaculaire » -- alors que K1 et K4
    n'ont AUCUNE paire informative (et que le 5e4 est un artefact du plancher eps=1e-6)."""
    v = _inj2_run(monkeypatch, {"off": 0.0, 1: 0.0, 4: 0.0, 8: 0.05}, n_seeds=5)
    assert v["ratios_par_K"]["8"] > 1000.0        # le plancher eps produit ce ratio absurde
    assert v["ratios_par_K"]["1"] != 1.0, (
        f"un bras SANS AUCUNE paire informative est publie comme neutre : {v['ratios_par_K']}")


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : la garde faisait `list(seeds)`/`list(ks)` et CONSOMMAIT ses deux entrees -> verdict NEUTRE fabrique sans qu'aucune ere ne soit comparee, apres avoir PAYE les eres `off`.
def test_run_causal_REFUSES_to_fabricate_a_NEUTRE_from_a_consumed_iterator(monkeypatch):
    """Reponse connue : la dose est ECRASANTE (le bras K8 triple la survie sur 5 seeds, donc
    CAUSE_BENEFIQUE quand elle est lue). Les deux portes d'entree sont exigees dans le meme test pour
    que le message les montre ensemble -- ce sont deux symptomes du meme `list()` destructeur."""
    doses = {"off": 0.10, 1: 0.10, 4: 0.10, 8: 0.30}
    M = _inj2_injecte(monkeypatch, doses)
    r_seeds = M.run_causal((s for s in range(5)), target="stoneage", num_agents=4, max_ticks=10,
                           shared_db=None, ks=(8,))
    r_ks = M.run_causal([0, 1, 2, 3, 4], target="stoneage", num_agents=4, max_ticks=10,
                        shared_db=None, ks=(k for k in (1, 4, 8)))
    assert (r_seeds["verdict"], r_ks["verdict"]) == ("CAUSE_BENEFIQUE", "CAUSE_BENEFIQUE"), (
        "verdicts fabriques a partir d'entrees consommees : seeds -> %r (n=%d, per_arm=%r) ; "
        "ks -> %r (n=%d, courbe=%r)"
        % (r_seeds["verdict"], r_seeds["n"], r_seeds["per_arm"],
           r_ks["verdict"], r_ks["n"], r_ks["ratios_par_K"]))


# ---------------------------------------------------------------------------------------------------
# P2.40 (2026-09-07) : `tools/dreaming_probe.py::run_q1` -- ORCHESTRATEUR de l'arc DREAM Q1. Il ne
# simule pas : il appelle `run_era_organ` (attribut de MODULE, donc injectable) deux fois par seed
# (sweet spot vs letal), convertit chaque ere en PREVALENCE d'organe, retranche la dose semee (0.5)
# et AGREGE en mediane -> `pressure`, la grandeur que la porte `dreaming_verdict` lit pour prononcer
# SURVIT / MORT. Sa garde d'ARGUMENTS existe depuis le 2026-09-06 ; ses branches de VERDICT n'ont
# jamais ete confrontees a une reponse connue.
#
# TECHNIQUE : injection a DOSE CONNUE (celle des 13 orchestrateurs de monde du 2026-09-01). On impose
# des cohortes factices a prevalence CHOISIE et on verifie que `pressure` et le verdict aval tombent
# JUSTE -- branches NEGATIVES incluses (une pression qui ne pourrait pas etre negative ou nulle ne
# prouverait rien, classe E1). Deux cas DEGENERES sont ecrits en `xfail(strict=True)` : ils exposent
# un negatif de fond FABRIQUE a partir de donnees absentes (le biais systematique du depot).
# ---------------------------------------------------------------------------------------------------


def _inj3_agent(has_organ, **over):
    """Cellule-agent factice portant TOUTES les cles que `run_era_organ` produit et que l'aval lit.
    `run_q1` ne lit que `has_organ` -- les autres sont imposees pour que l'injection reste fidele au
    contrat de la fonction remplacee (si l'orchestrateur se met a lire `age`, le test ne ment pas)."""
    c = {"age": 10, "total_dreams": 0, "has_organ": bool(has_organ), "founder": True,
         "altars_solved": 0, "spears_crafted": 0, "preys_eaten": 0}
    c.update(over)
    return c


def _inj3_cohorte(prevalence, n=8):
    """Cohorte de `n` agents dont exactement `prevalence*n` portent l'organe. n=8 -> 0.0/0.25/0.5/
    0.75/1.0 exactement representables : la dose est CONNUE au flottant pres, pas approchee."""
    k = int(round(prevalence * n))
    return [_inj3_agent(i < k) for i in range(n)]


def _inj3_injecte(monkeypatch, fabrique):
    """Remplace `run_era_organ` DANS le module de la sonde par `fabrique(...) -> cohorte`, et rend le
    module. L'appel est un GLOBAL de module (pas un import local) : monkeypatcher l'attribut suffit."""
    import tools.dreaming_probe as DP
    monkeypatch.setattr(DP, "run_era_organ", fabrique)
    return DP


def _inj3_par_regime(prev_sweet, prev_lethal, n=8):
    """Fabrique qui distingue les deux regimes par leur DOSE ENERGETIQUE (metab, payoff), pas par
    l'ordre d'appel : (0.25, 3.0) = sweet spot, (1.0, 1.0) = letal. C'est le seul discriminant que
    `run_q1` fournit -- si l'orchestrateur intervertissait les deux regimes, ce test le verrait."""
    def _f(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        assert organ_fraction == 0.5, "Q1 doit SEMER a 50% dans les DEUX bras"
        sweet = (metab, payoff) == (0.25, 3.0)
        p = prev_sweet if sweet else prev_lethal
        return _inj3_cohorte(p(seed) if callable(p) else p, n=n)
    return _f


def test_run_q1_READS_the_selection_pressure_it_claims(monkeypatch):
    """Reponse connue x3, la DOSE etant la prevalence d'organe imposee apres selection (semee a 0.5).

    POSITIF   -- sweet 0.75 / letal 0.25 : l'organe est enrichi au sweet spot et purge au letal ->
                 delta_sweet=+0.25, delta_letal=-0.25, pressure=+0.50 (pression nette FAVORABLE).
    NEGATIF   -- l'inverse exact (sweet 0.25 / letal 0.75) -> pressure=-0.50. Sans cette branche le
                 test ne prouverait rien : un instrument qui rend `abs()` ou qui intervertit les deux
                 regimes passerait le seul cas positif (classe E1).
    NUL       -- prevalences IDENTIQUES des deux cotes -> pressure=0.0 exactement. C'est la valeur
                 charniere : `dreaming_verdict` exige `pressure > 0` STRICTEMENT."""
    DP = _inj3_injecte(monkeypatch, _inj3_par_regime(0.75, 0.25))
    r = DP.run_q1([0, 1, 2], "stoneage", 8, 5, None)
    assert r["delta_prev_sweet"] == pytest.approx(0.25)
    assert r["delta_prev_lethal"] == pytest.approx(-0.25)
    assert r["pressure"] == pytest.approx(0.50)

    _inj3_injecte(monkeypatch, _inj3_par_regime(0.25, 0.75))
    r = DP.run_q1([0, 1, 2], "stoneage", 8, 5, None)
    assert r["delta_prev_sweet"] == pytest.approx(-0.25)
    assert r["delta_prev_lethal"] == pytest.approx(0.25)
    assert r["pressure"] == pytest.approx(-0.50), "l'organe PLUS purge au sweet doit rendre une pression NEGATIVE"

    _inj3_injecte(monkeypatch, _inj3_par_regime(0.625, 0.625))
    r = DP.run_q1([0, 1, 2], "stoneage", 8, 5, None)
    assert r["pressure"] == pytest.approx(0.0), "prevalences identiques -> pression nette EXACTEMENT nulle"


def test_run_q1_feeds_the_gate_that_reads_it(monkeypatch):
    """La grandeur mesuree est-elle celle qui AGIT ? `run_q1` ne prononce pas de verdict : c'est
    `dreaming_verdict` qui lit ses deux sorties. Reponse connue x3 sur la chaine COMPLETE, Q2 tenu
    fixe a « paye » (q2a=0.10) pour isoler la contribution de Q1 :
      - sweet 0.75 / letal 0.25 -> pressure>0 ET delta_sweet>-0.05  -> SURVIT_ET_PAYE
      - sweet 0.25 / letal 0.75 -> delta_sweet=-0.25 sous -eps      -> PAYE_PAS_SURVIT
      - sweet 0.50 / letal 0.50 -> delta_sweet=0.0 TOLERE mais pression NULLE -> PAYE_PAS_SURVIT.
    Le 3e cas est le piege : l'organe est parfaitement tolere, et pourtant la porte refuse -- elle
    exige une pression nette STRICTEMENT positive, pas une absence de purge."""
    DP = _inj3_injecte(monkeypatch, _inj3_par_regime(0.75, 0.25))
    for prevs, attendu in (((0.75, 0.25), "SURVIT_ET_PAYE"),
                           ((0.25, 0.75), "PAYE_PAS_SURVIT"),
                           ((0.50, 0.50), "PAYE_PAS_SURVIT")):
        _inj3_injecte(monkeypatch, _inj3_par_regime(*prevs))
        q1 = DP.run_q1([0, 1, 2], "stoneage", 8, 5, None)
        v = DP.dreaming_verdict(q1["delta_prev_sweet"], q1["delta_prev_lethal"], 0.10, 1.0)
        assert v == attendu, (prevs, attendu, v, q1["pressure"])


def test_run_q1_READS_the_median_over_seeds_not_the_mean(monkeypatch):
    """Unite de replication = le SEED (pre-vol Q3). Dose imposee : 5 seeds dont UN aberrant --
    prevalences sweet [1.0, 0.5, 0.5, 0.5, 0.5]. Mediane des deltas = 0.0 ; MOYENNE = +0.10.
    Reponse connue : l'instrument doit rendre 0.0. Un passage a la moyenne (ou une agregation sur les
    AGENTS au lieu des seeds) rendrait un signal la ou il n'y en a pas -- et `per_seed_sweet` doit
    contenir exactement 5 valeurs, une par seed, pour que l'aval puisse compter son n.
    Le bras letal est tenu a 0.25 (donc delta -0.25) et NON a 0.5 : sans cela, la pression attendue
    vaudrait 0.0 et le test passerait encore sur un orchestrateur qui confondrait les deux regimes
    (controle E1 verifie par mutation -- c'etait le cas de la premiere version)."""
    prev = {0: 1.0, 1: 0.5, 2: 0.5, 3: 0.5, 4: 0.5}
    DP = _inj3_injecte(monkeypatch, _inj3_par_regime(lambda s: prev[s], 0.25))
    r = DP.run_q1([0, 1, 2, 3, 4], "stoneage", 8, 5, None)
    assert r["per_seed_sweet"] == pytest.approx([0.5, 0.0, 0.0, 0.0, 0.0])
    assert len(r["per_seed_lethal"]) == 5
    assert r["delta_prev_sweet"] == pytest.approx(0.0), "mediane attendue (0.0), pas la moyenne (0.10)"
    assert r["delta_prev_lethal"] == pytest.approx(-0.25)
    assert r["pressure"] == pytest.approx(0.25), "la pression nette doit rester sweet - letal"


def test_run_q1_PAIRS_the_two_regimes_within_the_same_seed(monkeypatch):
    """Appariement WITHIN-SEED : l'affirmation « pression nette » n'a de sens que si sweet et letal
    partagent le seed (meme monde, meme init). Reponse connue : pour 3 seeds on doit voir 6 appels,
    exactement 2 par seed, differant UNIQUEMENT par (metab, payoff), avec organ_fraction=0.5 et le
    `target` / `num_agents` / `max_ticks` passes tels quels. Un instrument qui apparierait entre
    seeds (ou qui ne varierait pas le regime) produirait la meme mediane et resterait invisible ici
    sans ce test."""
    appels = []

    def _mouchard(target, seed, organ_fraction, metab, payoff, num_agents, max_ticks, shared_db):
        appels.append((target, seed, organ_fraction, metab, payoff, num_agents, max_ticks))
        return _inj3_cohorte(0.5)

    DP = _inj3_injecte(monkeypatch, _mouchard)
    DP.run_q1([7, 8, 9], "harsh", 8, 33, "DB")
    assert len(appels) == 6, appels
    for s in (7, 8, 9):
        du_seed = [a for a in appels if a[1] == s]
        assert len(du_seed) == 2, (s, du_seed)
        assert {(a[3], a[4]) for a in du_seed} == {(0.25, 3.0), (1.0, 1.0)}, du_seed
        assert {a[2] for a in du_seed} == {0.5}
        assert {(a[0], a[5], a[6]) for a in du_seed} == {("harsh", 8, 33)}


def test_run_q1_REFUSES_degenerate_arguments_BEFORE_any_era(monkeypatch):
    """La garde d'arguments doit lever, et lever EN TETE : un refus qui a deja fait tourner une ere
    coute une simulation. Reponse connue : pour chacun des 3 arguments degeneres (cohorte de seeds
    vide, num_agents<=0, max_ticks<=0) -> ValueError ET ZERO appel a `run_era_organ`. Contre-epreuve
    dans le meme test : un appel valide passe la garde et appelle bien (2 appels), sans quoi une
    garde qui refuserait TOUT passerait ce test."""
    compteur = {"n": 0}

    def _compte(*a, **kw):
        compteur["n"] += 1
        return _inj3_cohorte(0.5)

    DP = _inj3_injecte(monkeypatch, _compte)
    for args in (([], "stoneage", 8, 5, None),
                 ([0, 1], "stoneage", 0, 5, None),
                 ([0, 1], "stoneage", 8, 0, None)):
        with pytest.raises(ValueError, match="degenere"):
            DP.run_q1(*args)
        assert compteur["n"] == 0, ("la garde doit etre EN TETE, avant toute ere", args)

    DP.run_q1([0], "stoneage", 8, 5, None)
    assert compteur["n"] == 2, "contre-epreuve : un appel valide DOIT franchir la garde"


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : la garde consommait les seeds -> pressure=0.0 rendue comme une MESURE, et un verdict MORT.
def test_run_q1_REFUSES_an_exhausted_seed_iterator(monkeypatch):
    """Reponse connue : les seeds sont (0,1,2) et l'organe est massivement enrichi au sweet spot
    (0.75 vs 0.25) -> pressure DOIT valoir +0.50. Passes en generateur, ils sont manges par la garde
    et l'instrument rend 0.0 sans avoir simule une seule ere."""
    DP = _inj3_injecte(monkeypatch, _inj3_par_regime(0.75, 0.25))
    r = DP.run_q1((s for s in (0, 1, 2)), "stoneage", 8, 5, None)
    assert len(r["per_seed_sweet"]) == 3, "les 3 seeds doivent etre mesures, pas manges par la garde"
    assert r["pressure"] == pytest.approx(0.50)


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : une cohorte VIDE devenait delta=-0.5, soit « l'organe a ete INTEGRALEMENT purge » -> MORT.
def test_run_q1_REFUSES_an_empty_cohort_instead_of_fabricating_total_purge(monkeypatch):
    """Reponse connue : les eres ne rendent AUCUN agent -> il n'y a pas de prevalence, donc pas de
    delta. L'instrument doit le dire (nan ou levee), pas prononcer -0.5."""
    import math
    DP = _inj3_injecte(monkeypatch, lambda *a, **kw: [])
    try:
        r = DP.run_q1([0, 1, 2], "stoneage", 8, 5, None)
    except (ValueError, ZeroDivisionError):
        return
    assert math.isnan(r["delta_prev_sweet"]), (
        "cohorte vide -> INDETERMINE attendu ; mesure = %r, et la porte prononce %r"
        % (r["delta_prev_sweet"],
           DP.dreaming_verdict(r["delta_prev_sweet"], r["delta_prev_lethal"], 0.0, 1.0)))


# ---------------------------------------------------------------------------------------------------
# P2.40 (2026-09-07) : `run_contrast` (tools/evo_memory_inworld.py, EVO-003 « la politique ignore le
# canal de type ») -- ORCHESTRATEUR : il n'evolue ni ne benchmarke lui-meme, il APPELLE `evolve_inworld`
# et `benchmark_discrimination` (deux attributs de MODULE, resolus par nom global au moment de l'appel)
# et AGREGE en contraste ON/OFF par seed, que `main` transforme en affirmation (« mediane sous
# occultation »). Calibre par INJECTION A DOSE CONNUE : on impose les cellules et on verifie
# l'appariement, le regime passe a chaque benchmark, et CHAQUE branche de la synthese -- branches
# NEGATIVES incluses (une synthese qui ne peut rendre que « ON > OFF » ne prouverait rien, E1).
# ---------------------------------------------------------------------------------------------------


_INJ4_CELL_DEFAUT = {
    # toutes les cles que `benchmark_discrimination` renvoie ET que l'orchestrateur relit
    # (`disc` pour la synthese ; `big_kills`/`leurre_hits`/`encounters` pour la trace par seed --
    # une cle manquante y devient un KeyError, c'est ce que ce type de test sert a voir).
    "big_kills": 0, "leurre_hits": 0, "disc": float("nan"), "med_age": 0.0, "encounters": 0,
}


def _inj4_cellule(**over):
    """Cellule factice complete d'un benchmark de champion, surchargeable."""
    c = dict(_INJ4_CELL_DEFAUT)
    c.update(over)
    return c


def _inj4_disc(d, enc=10):
    """Cellule a discrimination IMPOSEE (dose connue) et rencontres coherentes."""
    big = int(round(d * enc))
    return _inj4_cellule(big_kills=big, leurre_hits=enc - big, disc=float(d), encounters=enc)


def _inj4_champion(tag, score=100.0, nodes=12):
    return {"genome": tag, "score": float(score), "nodes": int(nodes)}


def _inj4_injecte(monkeypatch, evolue, benchmarke):
    """Remplace les DEUX attributs de module que `run_contrast` resout par nom global."""
    import tools.evo_memory_inworld as M
    monkeypatch.setattr(M, "evolve_inworld", evolue)
    monkeypatch.setattr(M, "benchmark_discrimination", benchmarke)
    return M


def _inj4_bombe(*a, **k):
    raise AssertionError("appel de run/benchmark APRES un argument degenere : la garde n'est pas EN TETE")


# --------------------------------------------------------------------------------------------------
# 1. Garde d'arguments : refus INSTANTANE (avant toute evolution), pour les 4 formes de degenerescence
# --------------------------------------------------------------------------------------------------

def test_run_contrast_REFUSES_degenerate_arguments_before_any_run(monkeypatch):
    """Reponse connue x4 : aucune de ces configurations ne peut produire UNE mesure, donc aucune ne doit
    produire un contraste. On teste non seulement QUE ca leve mais OU la garde est posee : les deux
    fonctions internes sont des bombes -- un refus doit couter ZERO evolution (cf. CLAUDE.md, garde en
    tete de fonction). Sans ce test, une cohorte vide rendrait `rows=[]` -> mediane « n/a » que l'aval
    lit comme un negatif de fond."""
    import tools.evo_memory_inworld as M
    _inj4_injecte(monkeypatch, _inj4_bombe, _inj4_bombe)

    for kw in ({"seeds": []},
               {"seeds": [0], "eras": 0},
               {"seeds": [0], "max_ticks": 0},
               {"seeds": [0], "num_agents": 0}):
        with pytest.raises(ValueError, match="degenere"):
            M.run_contrast(**kw)


# --------------------------------------------------------------------------------------------------
# 2. Le contraste LIT la dose imposee, bras par bras et seed par seed
# --------------------------------------------------------------------------------------------------

def test_run_contrast_READS_the_per_seed_dose_it_is_given(monkeypatch):
    """Reponse connue : chaque (seed, bras) recoit une discrimination IMPOSEE et distincte. Ce que le
    test protege : (a) le champion ON n'est jamais benchmarke a la place du champion OFF (croisement de
    bras = contraste inverse silencieusement) ; (b) `on_occ`/`off_occ` sont bien mesures sous
    memory_regime=True (occultation, memoire REQUISE) et `on_vis`/`off_vis` sous False (controle
    perception) -- un regime inverse rendrait le contraste ininterpretable sans rien casser ;
    (c) la graine de benchmark est DECALEE (1000+s), donc la mesure n'est pas celle de l'evolution."""
    import tools.evo_memory_inworld as M

    dose = {("ON", True): 0.90, ("ON", False): 0.95, ("OFF", True): 0.20, ("OFF", False): 0.85}
    vus, regimes = [], []

    def _evolue(memory_regime, seed, eras, max_ticks, num_agents, *a, **k):
        bras = "ON" if memory_regime else "OFF"
        regimes.append((bras, seed, eras, max_ticks, num_agents))
        return _inj4_champion(f"GEN-{bras}-s{seed}", score=10.0 * seed + (1 if memory_regime else 2),
                              nodes=20 + seed if memory_regime else 30 + seed)

    def _bench(genome, memory_regime, seed, num_agents=24, ticks=150, ablate=False):
        bras = genome.split("-")[1]
        vus.append((genome, memory_regime, seed, ticks))
        return _inj4_disc(dose[(bras, bool(memory_regime))])

    _inj4_injecte(monkeypatch, _evolue, _bench)
    rows = M.run_contrast([0, 1], eras=3, max_ticks=7, num_agents=5, bench_ticks=11)

    assert len(rows) == 2
    for i, r in enumerate(rows):
        assert r["seed"] == i
        assert r["score_on"] == 10.0 * i + 1 and r["score_off"] == 10.0 * i + 2
        assert r["nodes_on"] == 20 + i and r["nodes_off"] == 30 + i
        assert r["on_occ"]["disc"] == 0.90 and r["on_vis"]["disc"] == 0.95
        assert r["off_occ"]["disc"] == 0.20 and r["off_vis"]["disc"] == 0.85

    # (d) le REGIME demande arrive aux DEUX bras d'evolution, a l'identique : 2 evolutions par seed,
    #     eras=3 / max_ticks=7 / num_agents=5 tels quels. Un bras evolue plus longtemps que l'autre
    #     rendrait le contraste ininterpretable sans rien casser dans les chiffres publies.
    assert regimes == [("ON", 0, 3, 7, 5), ("OFF", 0, 3, 7, 5),
                       ("ON", 1, 3, 7, 5), ("OFF", 1, 3, 7, 5)], regimes

    # (b)+(c) : bon genome, bon regime, graine decalee, ticks de benchmark transmis
    assert vus == [("GEN-ON-s0", True, 1000, 11), ("GEN-ON-s0", False, 1000, 11),
                   ("GEN-OFF-s0", True, 1000, 11), ("GEN-OFF-s0", False, 1000, 11),
                   ("GEN-ON-s1", True, 1001, 11), ("GEN-ON-s1", False, 1001, 11),
                   ("GEN-OFF-s1", True, 1001, 11), ("GEN-OFF-s1", False, 1001, 11)], vus


def test_run_contrast_READS_the_REVERSED_contrast_too(monkeypatch):
    """Branche NEGATIVE de l'appariement (E1) : on inverse la dose (le champion OFF discrimine MIEUX
    sous occultation). Un orchestrateur qui aurait le bras cable en dur rendrait toujours ON > OFF ;
    ici le contraste doit s'inverser, seed par seed."""
    import tools.evo_memory_inworld as M

    def _evolue(memory_regime, seed, *a, **k):
        return _inj4_champion(f"GEN-{'ON' if memory_regime else 'OFF'}-s{seed}")

    def _bench(genome, memory_regime, seed, **k):
        return _inj4_disc(0.15 if genome.split("-")[1] == "ON" else 0.75)

    _inj4_injecte(monkeypatch, _evolue, _bench)
    rows = M.run_contrast([0, 1, 2])
    assert [r["on_occ"]["disc"] for r in rows] == [0.15, 0.15, 0.15]
    assert [r["off_occ"]["disc"] for r in rows] == [0.75, 0.75, 0.75]


# --------------------------------------------------------------------------------------------------
# 3. La COUCHE QUI AFFIRME (`main`) : chaque branche de la synthese, negatives comprises
# --------------------------------------------------------------------------------------------------

def _inj4_synthese(monkeypatch, capsys, doses, n_seeds=3):
    """Fait tourner la chaine complete `main -> run_contrast -> {evolve,benchmark} injectes`.
    `doses[(bras, seed)]` = discrimination sous OCCULTATION ; None = nan (aucune rencontre)."""
    import tools.evo_memory_inworld as M
    monkeypatch.setenv("EVO3_SEEDS", str(n_seeds))
    monkeypatch.setenv("EVO3_ERAS", "2")
    monkeypatch.setenv("EVO3_TICKS", "5")
    monkeypatch.setenv("EVO3_AGENTS", "4")

    def _evolue(memory_regime, seed, *a, **k):
        return _inj4_champion(f"GEN-{'ON' if memory_regime else 'OFF'}-s{seed}")

    def _bench(genome, memory_regime, seed, **k):
        bras = genome.split("-")[1]
        s = int(genome.split("-s")[1])
        if not memory_regime:                      # bras « type visible » : hors synthese
            return _inj4_disc(0.5)
        d = doses.get((bras, s))
        return _inj4_cellule() if d is None else _inj4_disc(d)

    _inj4_injecte(monkeypatch, _evolue, _bench)
    M.main()
    out = capsys.readouterr().out
    ligne_on = [l for l in out.splitlines() if "ÉVOLUÉ-ON" in l][0]
    ligne_off = [l for l in out.splitlines() if "ÉVOLUÉ-OFF" in l][0]
    return ligne_on, ligne_off


def test_evo3_main_READS_the_contrast_in_BOTH_directions(monkeypatch, capsys):
    """Reponse connue x2, dose imposee, mediane calculable a la main. Sens attendu (ON > OFF) ET sens
    OPPOSE (OFF > ON) : sans la seconde, le test ne prouverait rien (E1). La mediane de [0.8,0.9,1.0]
    est 0.90 ; celle de [0.1,0.2,0.3] est 0.20."""
    on_haut = {("ON", 0): 0.8, ("ON", 1): 0.9, ("ON", 2): 1.0,
               ("OFF", 0): 0.1, ("OFF", 1): 0.2, ("OFF", 2): 0.3}
    l_on, l_off = _inj4_synthese(monkeypatch, capsys, on_haut)
    assert "méd=0.90 (n=3)" in l_on and "méd=0.20 (n=3)" in l_off

    off_haut = {("ON", 0): 0.1, ("ON", 1): 0.2, ("ON", 2): 0.3,
                ("OFF", 0): 0.8, ("OFF", 1): 0.9, ("OFF", 2): 1.0}
    l_on, l_off = _inj4_synthese(monkeypatch, capsys, off_haut)
    assert "méd=0.20 (n=3)" in l_on and "méd=0.90 (n=3)" in l_off


def test_evo3_main_REFUSES_to_call_zero_encounters_a_null(monkeypatch, capsys):
    """CAS DEGENERE, reponse connue : AUCUN champion ne rencontre d'apex -> `disc` = nan partout. La
    reponse juste est INDETERMINEE (« n/a », n=0), surtout PAS « disc = 0.00 » : dans un depot dont la
    plupart des resultats sont negatifs, un zero fabrique ressemble a tous les autres. Ce test grave la
    bonne branche (`_isnan` filtre AVANT `_med`, et `_med([])` rend « n/a »)."""
    l_on, l_off = _inj4_synthese(monkeypatch, capsys, {})
    assert "méd=n/a (n=0)" in l_on and "méd=n/a (n=0)" in l_off
    assert "0.00" not in l_on and "0.00" not in l_off


def test_evo3_main_READS_a_single_measurable_seed_as_n_equals_one(monkeypatch, capsys):
    """Cas limite intermediaire : 1 seul seed mesurable sur 3 dans les DEUX bras. Le n imprime doit
    tomber a 1 (et non rester 3) -- sinon la synthese sur-declare son unite de replication."""
    l_on, l_off = _inj4_synthese(monkeypatch, capsys, {("ON", 1): 0.60, ("OFF", 1): 0.40})
    assert "méd=0.60 (n=1)" in l_on and "méd=0.40 (n=1)" in l_off


# --------------------------------------------------------------------------------------------------
# 4. DEFAUTS REELS EXPOSES par l'injection (xfail STRICT : ils doivent echouer tant qu'ils sont la)
# --------------------------------------------------------------------------------------------------

# NON-REGRESSION (defaut CORRIGE le 2026-09-07) : la garde faisait `list(seeds)` et CONSOMMAIT
# l'iterateur -> la garde anti-negatif fabriquait elle-meme le negatif qu'elle refuse.
def test_run_contrast_REFUSES_to_silently_empty_a_consumed_iterator(monkeypatch):
    """Reponse connue : deux seeds sont fournis, donc deux lignes -- ou un refus explicite. Ce que
    l'injection expose : l'orchestrateur rend une agregation VIDE pour une entree NON vide."""
    import tools.evo_memory_inworld as M

    def _evolue(memory_regime, seed, *a, **k):
        return _inj4_champion(f"GEN-{'ON' if memory_regime else 'OFF'}-s{seed}")

    _inj4_injecte(monkeypatch, _evolue, lambda g, r, s, **k: _inj4_disc(0.5))
    rows = M.run_contrast(iter([0, 1]))
    assert len(rows) == 2, f"iterateur consomme par la garde : {len(rows)} ligne(s) au lieu de 2"


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : la synthese filtrait les nan BRAS PAR BRAS, donc comparait des medianes calculees sur des SEEDS DIFFERENTS.
def test_evo3_main_REFUSES_to_contrast_arms_measured_on_DISJOINT_seeds(monkeypatch, capsys):
    """Reponse connue : seed 0 mesurable seulement en ON, seed 1 seulement en OFF -> ZERO paire. Le
    design de ce module declare le SEED comme unite de replication et le contraste comme
    within-subject ; un contraste between-seeds fabrique ici un ecart de 0.80 a partir de rien."""
    l_on, l_off = _inj4_synthese(monkeypatch, capsys, {("ON", 0): 0.90, ("OFF", 1): 0.10}, n_seeds=2)
    assert "n/a" in l_on and "n/a" in l_off, (l_on, l_off)


# NON-REGRESSION (defaut CORRIGE le 2026-09-08) : des seeds DUPLIQUES produisaient des lignes identiques qui gonflaient le n sans ajouter un seul replicat (pseudo-replication).
def test_run_contrast_REFUSES_duplicate_seeds(monkeypatch):
    """Reponse connue : [5, 5] ne contient qu'UN replicat. L'orchestrateur doit lever ou dedupliquer ;
    il rend deux lignes indiscernables, que `main` compte comme n=2."""
    import tools.evo_memory_inworld as M

    def _evolue(memory_regime, seed, *a, **k):
        return _inj4_champion(f"GEN-{'ON' if memory_regime else 'OFF'}-s{seed}")

    _inj4_injecte(monkeypatch, _evolue, lambda g, r, s, **k: _inj4_disc(0.5))
    rows = M.run_contrast([5, 5])
    assert len(rows) == 1, f"pseudo-replication : {len(rows)} lignes pour 1 seul seed distinct"
