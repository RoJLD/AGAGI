# -*- coding: utf-8 -*-
# P2.44 (2026-09-08) -- INJECTION A DOSE CONNUE, suite de `test_orchestrator_injection.py` (les 5
# prioritaires, la veille). Meme technique : monkeypatch de l'attribut de MODULE appele, cellules
# imposees a DOSE CONNUE, verdict exige en forme close, branches NEGATIVES comprises. AUCUN monde
# construit -> cout nul. Controle E1 PAR MUTATION effectue : l'orchestrateur rendu aveugle a la dose
# fait MOURIR les tests passants. Il ne reste AUCUN `xfail` : les blocs NON-REGRESSION sont d'anciens
# xfail dont le defaut a ete corrige, et ils portent le comportement corrige en dur.
# -*- coding: utf-8 -*-
"""INJ-6 (2026-09-08) -- calibration par INJECTION A DOSE CONNUE de
`tools/cross_world_transfer.py::run_direction`.

`run_direction` est un ORCHESTRATEUR : il ne simule pas, il APPELLE `measure_in_world` (deux bras) et
AGREGE les mesures en verdict de transfert zero-shot (KPI `transfer_ratio`, spec SDR-G1, publie par
EDR-156/129). Sa garde d'ARGUMENTS etait calibree
(`tests/sandbox/test_instrument_calibration.py:84` -- "empty-cohort:raises", "guard-before-world").
Ce que RIEN ne calibrait, c'est la couche qui transforme des mesures en affirmation : appariement
seed-a-seed, unite de replication, cablage du regime, et surtout les TROIS BRANCHES DE VERDICT
(TRANSFERE / NUIT / NEUTRE). C'est la que se decide ce qui est publie.

TECHNIQUE. Les deux seuls seams de simulation/disque sont importes/definis AU NIVEAU MODULE et
appeles par recherche globale depuis `run_direction` : `measure_in_world` (ligne 112 et 114) et
`_load_genome` (ligne 111). On monkeypatche donc `tools.cross_world_transfer.measure_in_world` et
`tools.cross_world_transfer._load_genome` -- PAS un module source. On laisse REELS `paired_ratios` et
`compute_transfer_verdict` : c'est precisement la couche "mesures -> affirmation" qu'on calibre.
AUCUN monde n'est construit, aucun HoF n'est lu, aucun bail `kuzu` n'est requis ; le fichier entier
coute moins de 2 s, dont ~0.8 s d'import.

DOSES. Toutes choisies pour que le verdict soit en FORME CLOSE (test de signe binomial exact a
n tirages, bande neutre 0.05) -- y compris les branches NEGATIVES, sans lesquelles un instrument qui
rendrait TRANSFERE quoi qu'il arrive passerait (classe E1).

CONTROLE E1 PAR MUTATION (mesure du 2026-09-08, `tools/cross_world_transfer.py` restaure a l'octet
pres, sha256 032fd29f... identique avant/apres) :
  M1 -- orchestrateur rendu AVEUGLE A LA DOSE (`champ_meds` et `tabula_meds` remplaces par
        `[1.0] * k_eval`, les deux `measure_in_world` sautes) : les 8 tests passants MEURENT (8/8),
        et le xfail EXTINCTION devient XPASS(strict) -> il est lui aussi dose-sensible.
        Bilan pytest : "9 failed, 2 xfailed".
  M2 -- garde d'arguments DEPLACEE apres `_load_genome` (elle leve toujours, mais le refus n'est
        plus instantane) : SEUL le test de position de la garde meurt (1/1), les 7 autres restent
        verts. Bilan pytest : "1 failed, 7 passed, 3 xfailed".
Un test qui survit a la mutation qui le concerne ne mesure pas ce qu'il croit ; aucun ne survit ici.

Les `xfail(strict=True)` sont des DEFAUTS REELS NON CORRIGES (l'auteur de cette passe n'a pas le
droit de toucher `tools/cross_world_transfer.py`) : ils tiennent la dette ouverte et tomberont
d'eux-memes le jour ou le defaut sera corrige (strict -> un XPASS est un echec).

ADDENDUM 2026-09-08 -- LES TROIS DEFAUTS DE LA SECTION 3 SONT CORRIGES. Le correctif est dans
`run_direction` (garde de baseline en TETE + exclusion des paires doublement eteintes) et NON dans
`paired_ratios`, dont la troncature `min()` et le plancher epsilon sont le contrat PUBLIE fige par
`tests/test_cross_world_transfer.py` (qui n'appartient pas a cette passe). La section 4 porte les
CAS NEGATIFS APPARIES (classe E1) de chaque comportement ajoute.

ADDENDUM 2 (REFUTATEUR, meme jour) -- LES TROIS `xfail(strict)` DE LA SECTION 3 SONT CONVERTIS.
Ils etaient devenus XPASS, c.-a-d. **FAILED** : la passe precedente a livre le correctif en laissant
la suite ROUGE ("3 failed, 12 passed"), avec les marqueurs "a convertir" -- un test rouge laisse
derriere un correctif EST le correctif incomplet (classe E14 : relancer et corriger les tests
EXISTANTS fait partie du correctif, pas du nettoyage). Les trois portent desormais le comportement
CORRIGE en dur, plus un cas negatif apparie chacun. La SECTION 5 porte trois defauts de PLUS trouves
sur le correctif lui-meme, dont DEUX qu'il avait ouverts (medianes publiees hors du perimetre du
verdict ; puissance detruite par l'ecart) et un qu'il n'avait pas vu (aucune garde de DOMAINE :
+inf -> 'NEUTRE', survie NEGATIVE -> 'TRANSFERE' a p<0.001).

CONTROLE E1 PAR MUTATION, 3e serie (refutateur) : la POST-CONDITION de longueur posee apres la
mesure etait **DECORATIVE** -- la supprimer ne faisait rougir AUCUN test ("3 failed, 12 passed",
c.-a-d. exactement les 3 rouges pre-existants), parce que le faux d'injection impose lui-meme
`len(dose) == k_eval` et qu'aucun cas ne tournait donc dans son regime.
`..._REFUSES_a_MEASURED_arm_that_is_degenerate` la fait desormais travailler dans ses deux branches.

CONTROLE E1 PAR MUTATION DU CORRECTIF (meme protocole, `tools/cross_world_transfer.py` restaure a
l'octet pres, sha256 b68f5542... identique avant/apres) :
  M3 -- exclusion rendue INCREVABLE (`paires_informatives` ecarte TOUTES les paires) :
        "14 failed, 1 passed" -- une garde qui refuse tout est attrapee par 14 tests sur 15.
  M4 -- exclusion rendue MORTE (n'ecarte JAMAIS rien = comportement d'avant le correctif) :
        "4 failed, 10 passed, 1 xfailed" -- le xfail EXTINCTION redevient XFAIL (le defaut est bien
        restaure), les DEUX tests qui LISENT l'exclusion meurent, et les xfails baseline restent
        XPASS : les deux gardes sont ORTHOGONALES. Le cas NEGATIF apparie
        (`..._when_ONE_arm_still_lives`) SURVIT a M4, comme il le doit : il mesure que la garde sait
        NE PAS se declencher, donc la desarmer ne peut pas le casser -- seule M3 le tue.
  M5 -- gardes de baseline DESARMEES en tete (elles ne s'executent plus) : SEUL le test de POSITION
        meurt ("4 failed, 11 passed") -- les deux xfails baseline restent XPASS parce que la
        POST-CONDITION de longueur, posee apres la mesure, les rattrape. C'est exactement ce que ce
        test-la mesure : OU la garde est posee, pas seulement qu'elle leve.
"""
import statistics

import pytest


# ======================================================================================================
# Injection
# ======================================================================================================

_INJ6_GENOME = "GENOME-CHAMPION-FACTICE-INJ6"     # sentinelle : distingue le bras champion du bras tabula


def _inj6_injecte(monkeypatch, champ, tabula=None, journal=None):
    """Remplace, DANS `tools.cross_world_transfer`, les deux seuls seams qui touchent le monde ou le
    disque :
      - `measure_in_world` -> rend la LISTE DE MEDIANES imposee (c'est tout ce que la vraie fonction
        renvoie : `List[float]`, une mediane de survie PAR seed d'eval -- l'unite d'appariement) ;
      - `_load_genome` -> sentinelle (le HoF n'est ni lu ni recharge, et `os.environ['HOF_PATH']`
        n'est pas mute).
    `tabula=None` signifie "le bras tabula ne DOIT PAS etre mesure" : le faux leve si on l'appelle,
    ce qui transforme la reutilisation de baseline en assertion gratuite.
    Le faux exige `len(dose) == k_eval` : si l'orchestrateur demandait un k different a chaque bras,
    le test le dirait au lieu de mentir. Renvoie le module."""
    import tools.cross_world_transfer as C

    def _fake_measure_in_world(world_key, genome, seed, k_eval=12, num_agents=12, max_ticks=300):
        bras = "champion" if genome is not None else "tabula"
        if journal is not None:
            journal.append({"bras": bras, "monde": world_key, "seed": seed, "k_eval": k_eval,
                            "num_agents": num_agents, "max_ticks": max_ticks, "genome": genome})
        if bras == "tabula" and tabula is None:
            raise AssertionError(
                "le bras tabula a ete MESURE alors qu'une baseline reutilisable etait fournie : "
                "la baseline est re-simulee a chaque champion (cout x2 pour la meme mesure)")
        dose = champ if bras == "champion" else tabula
        assert len(dose) == int(k_eval), (
            f"bras {bras} : k_eval={k_eval} demande mais la dose imposee a {len(dose)} valeurs -- "
            "les deux bras doivent recevoir le MEME k_eval (unite de replication)")
        return [float(x) for x in dose]

    def _fake_load_genome(hof_path):
        if journal is not None:
            journal.append({"bras": "_load_genome", "hof": hof_path})
        return _INJ6_GENOME

    monkeypatch.setattr(C, "measure_in_world", _fake_measure_in_world)
    monkeypatch.setattr(C, "_load_genome", _fake_load_genome)
    return C


def _inj6_run(C, champ_dose, **kw):
    """Appel standard : k_eval deduit de la dose champion (sinon le faux leve)."""
    kw.setdefault("seed", 42)
    kw.setdefault("k_eval", len(champ_dose))
    return C.run_direction("famine[hof_famine.pkl]", "data/hall_of_fame_famine.pkl", "stoneage", **kw)


# ======================================================================================================
# 1. LES TROIS BRANCHES DE VERDICT, a dose imposee (reponse connue en forme close)
# ======================================================================================================

def test_run_direction_READS_the_dose_of_transfer_it_publishes(monkeypatch):
    """Reponse connue x3, une par branche de `compute_transfer_verdict` telle que `run_direction` la
    cable (bande neutre 0.05, majorite stricte, garde de puissance sign_p<0.05) :

      TRANSFERE : champion 2x tabula sur les 12 seeds -> ratios tous 2.0, mediane 2.0 > 1.05,
                  n_fav=12 > 6, sign_p = 2/2^12 = 0.00048828125.
      NUIT      : champion 10 vs tabula 20 -> ratios tous 0.5, mediane 0.5 < 0.95, n_fav=0 < 6,
                  meme sign_p exact (le test de signe est symetrique).
      NEUTRE    : champion 1.02x -> l'effet est REEL et SIGNIFICATIF (12/12 seeds favorables,
                  sign_p=0.00048828125) mais la mediane 1.02 reste DANS la bande neutre. C'est la
                  branche qui empeche de publier TRANSFERE sur un decalage de 2 %.

    Sans les deux dernieres, un instrument qui rendrait TRANSFERE quoi qu'il arrive passerait (E1)."""
    cas = (
        ("TRANSFERE", [2.0] * 12, [1.0] * 12, 2.0, 12, 0.00048828125),
        ("NUIT", [10.0] * 12, [20.0] * 12, 0.5, 0, 0.00048828125),
        ("NEUTRE", [1.02] * 12, [1.0] * 12, 1.02, 12, 0.00048828125),
    )
    for attendu, champ, tabula, med, n_fav, p in cas:
        C = _inj6_injecte(monkeypatch, champ, tabula)
        r = _inj6_run(C, champ)
        assert r["verdict"] == attendu, (attendu, r)
        assert r["n"] == 12
        assert r["median_ratio"] == pytest.approx(med)
        assert r["n_favorable"] == n_fav
        assert r["sign_p"] == pytest.approx(p)
        # les grandeurs PUBLIEES a cote du verdict doivent etre celles qui ont servi
        assert r["champ_median"] == pytest.approx(statistics.median(champ))
        assert r["tabula_median"] == pytest.approx(statistics.median(tabula))
        assert r["ratios"] == [pytest.approx(c / t) for c, t in zip(champ, tabula)]
        assert r["source"] == "famine[hof_famine.pkl]" and r["target"] == "stoneage"


def test_run_direction_KEEPS_the_neutral_band_load_bearing(monkeypatch):
    """Dose-reponse appariee, tout le reste IDENTIQUE (meme n, meme n_fav, meme sign_p) : seule la
    TAILLE de l'effet change. 1.02x -> NEUTRE, 1.20x -> TRANSFERE. Le point qui compte : le bras
    NEUTRE a sign_p = 0.00048828125, donc la significativite SEULE ne suffit pas a publier -- si
    quelqu'un retirait la bande, le premier bras deviendrait TRANSFERE sur 2 % d'ecart."""
    C = _inj6_injecte(monkeypatch, [1.02] * 12, [1.0] * 12)
    faible = _inj6_run(C, [1.02] * 12)
    C = _inj6_injecte(monkeypatch, [1.20] * 12, [1.0] * 12)
    fort = _inj6_run(C, [1.20] * 12)

    assert faible["verdict"] == "NEUTRE" and fort["verdict"] == "TRANSFERE", (faible, fort)
    assert faible["n"] == fort["n"] == 12
    assert faible["n_favorable"] == fort["n_favorable"] == 12
    assert faible["sign_p"] == fort["sign_p"] == pytest.approx(0.00048828125)
    assert faible["sign_p"] < 0.05          # significatif ET pourtant non publie : c'est la bande


def test_run_direction_READS_sign_p_and_refuses_the_SAME_dose_under_power(monkeypatch):
    """NON-REGRESSION E14 (le `sign_p` calcule puis JETE). Meme dose EXACTE (champion 2x tabula sur
    tous les seeds), seule l'unite de replication change :
      n=5 -> sign_p = 2/2^5 = 0.0625 >= 0.05 -> NEUTRE (malgre mediane 2.0 et 5/5 favorables) ;
      n=6 -> sign_p = 2/2^6 = 0.03125 < 0.05 -> TRANSFERE.
    La bascule est EXACTEMENT au n, pas a l'amplitude : c'est la preuve que la garde de puissance est
    LUE. Si `sign_p` etait recalcule mais non branche au verdict, le bras n=5 publierait TRANSFERE
    sur 5 seeds -- exactement la recidive d'E14 mesuree le 2026-09-01."""
    C = _inj6_injecte(monkeypatch, [2.0] * 5, [1.0] * 5)
    petit = _inj6_run(C, [2.0] * 5)
    C = _inj6_injecte(monkeypatch, [2.0] * 6, [1.0] * 6)
    grand = _inj6_run(C, [2.0] * 6)

    assert petit["verdict"] == "NEUTRE", petit
    assert petit["median_ratio"] == pytest.approx(2.0) and petit["n_favorable"] == 5
    assert petit["sign_p"] == pytest.approx(0.0625)
    assert grand["verdict"] == "TRANSFERE", grand
    assert grand["median_ratio"] == pytest.approx(2.0) and grand["n_favorable"] == 6
    assert grand["sign_p"] == pytest.approx(0.03125)


def test_run_direction_DEMANDS_a_majority_not_only_a_median(monkeypatch):
    """La mediane des ratios peut etre > 1.05 sans qu'une MAJORITE de seeds soit favorable (loi de
    ratios tres asymetrique : quelques seeds spectaculaires, la moitie defavorable).
      dose A : champion [3,3,3,0.1,0.1,0.1] vs tabula 1 -> mediane 1.55 > 1.05 MAIS n_fav = 3 et
               2*3 = 6 n'est pas > 6 -> NEUTRE (et sign_p = 1.0, le signe ne tranche pas).
      dose B (controle apparie) : les trois seeds defavorables ramenes a 1.5 -> 6/6 favorables,
               mediane 2.25, sign_p = 0.03125 -> TRANSFERE.
    Sans la condition de majorite, la dose A publierait TRANSFERE sur trois seeds sur six."""
    C = _inj6_injecte(monkeypatch, [3.0, 3.0, 3.0, 0.1, 0.1, 0.1], [1.0] * 6)
    asym = _inj6_run(C, [3.0, 3.0, 3.0, 0.1, 0.1, 0.1])
    C = _inj6_injecte(monkeypatch, [3.0, 3.0, 3.0, 1.5, 1.5, 1.5], [1.0] * 6)
    net = _inj6_run(C, [3.0, 3.0, 3.0, 1.5, 1.5, 1.5])

    assert asym["verdict"] == "NEUTRE", asym
    assert asym["median_ratio"] == pytest.approx(1.55) and asym["median_ratio"] > 1.05
    assert asym["n_favorable"] == 3 and 2 * asym["n_favorable"] == asym["n"]
    assert net["verdict"] == "TRANSFERE", net
    assert net["n_favorable"] == 6 and net["sign_p"] == pytest.approx(0.03125)


# ======================================================================================================
# 2. APPARIEMENT et CABLAGE (ce que les stats en aval ne peuvent pas verifier)
# ======================================================================================================

def test_run_direction_PAIRS_seed_by_seed_and_NOT_by_aggregate(monkeypatch):
    """LA propriete de design de ce KPI : "appariee par seed d'eval" (docstring du module). Dose
    construite pour que l'appariement soit DISCRIMINANT -- champion FIXE [8,8,8,2,2,2], baseline de
    MULTISET IDENTIQUE dans les deux bras, seul l'ORDRE change :
      ordre X = [4,4,4,1,1,1] -> ratios [2,2,2,2,2,2] -> TRANSFERE (sign_p = 0.03125) ;
      ordre Y = [1,1,1,4,4,4] -> ratios [8,8,8,.5,.5,.5] -> mediane 4.25 mais n_fav = 3 -> NEUTRE.
    Un estimateur NON apparie (ratio des medianes) vaut 5/2.5 = 2.0 dans LES DEUX ordres et rendrait
    donc le meme verdict : ce test separe donc exactement l'appariement de l'agregat. Et il verifie
    au passage que les deux bras sont mesures sur le MEME seed de base (sinon l'index i ne designe
    plus le meme seed d'eval `seed_at(seed, i)` et l'appariement n'est qu'un alignement de listes)."""
    champ = [8.0, 8.0, 8.0, 2.0, 2.0, 2.0]
    assert statistics.median(champ) / statistics.median([4.0, 4.0, 4.0, 1.0, 1.0, 1.0]) == 2.0
    assert statistics.median(champ) / statistics.median([1.0, 1.0, 1.0, 4.0, 4.0, 4.0]) == 2.0

    jx, jy = [], []
    C = _inj6_injecte(monkeypatch, champ, [4.0, 4.0, 4.0, 1.0, 1.0, 1.0], journal=jx)
    x = _inj6_run(C, champ)
    C = _inj6_injecte(monkeypatch, champ, [1.0, 1.0, 1.0, 4.0, 4.0, 4.0], journal=jy)
    y = _inj6_run(C, champ)

    assert x["verdict"] == "TRANSFERE" and x["ratios"] == [pytest.approx(2.0)] * 6, x
    assert y["verdict"] == "NEUTRE" and y["n_favorable"] == 3, y
    # meme seed de base pour les deux bras -> l'index i designe le meme seed d'eval des deux cotes
    for j in (jx, jy):
        seeds = {e["seed"] for e in j if e["bras"] in ("champion", "tabula")}
        assert seeds == {42}, j


def test_run_direction_WIRES_the_requested_regime_IDENTICALLY_to_both_arms(monkeypatch):
    """Le regime demande doit ARRIVER, identique, aux deux bras : meme monde CIBLE (pas le monde
    source), meme seed, meme k_eval / num_agents / max_ticks. Un bras sous-alimente (moins d'agents,
    horizon plus court) fabriquerait un ratio sans que rien ne le signale -- le rapport ne publie
    aucun de ces parametres.
    On verifie aussi l'IDENTITE des bras : le genome du champion (sentinelle du HoF) va au bras
    champion et a AUCUN autre, le bras tabula recoit None (tabula-rasa), et le HoF ouvert est bien
    `source_hof`. Controle apparie : les deux bras sont mesures EXACTEMENT une fois chacun."""
    journal = []
    C = _inj6_injecte(monkeypatch, [2.0] * 12, [1.0] * 12, journal=journal)
    r = C.run_direction("famine[hof_famine.pkl]", "data/hall_of_fame_famine.pkl", "stoneage",
                        seed=7, k_eval=12, num_agents=5, max_ticks=33)
    assert r["verdict"] == "TRANSFERE"

    charge = [e for e in journal if e["bras"] == "_load_genome"]
    mesures = [e for e in journal if e["bras"] != "_load_genome"]
    assert [e["hof"] for e in charge] == ["data/hall_of_fame_famine.pkl"], journal
    assert [e["bras"] for e in mesures] == ["champion", "tabula"], journal
    assert charge and journal.index(charge[0]) < journal.index(mesures[0])   # HoF lu AVANT de mesurer
    for e in mesures:
        assert e["monde"] == "stoneage", e          # le monde CIBLE, jamais le monde source
        assert e["seed"] == 7 and e["k_eval"] == 12
        assert e["num_agents"] == 5 and e["max_ticks"] == 33
    assert [e["genome"] for e in mesures] == [_INJ6_GENOME, None], journal


def test_run_direction_REUSES_a_supplied_baseline_and_REPUBLISHES_it_unchanged(monkeypatch):
    """Le parametre `tabula_meds` existe pour ne pas re-mesurer la baseline a chaque champion
    (main() la mesure UNE fois pour 3 champions famine). Reponse connue :
      - fourni  -> UN SEUL appel a `measure_in_world` (le champion), et la baseline republiee est
                   EXACTEMENT celle fournie (si l'orchestrateur la re-mesurait ou la reordonnait,
                   les 3 directions ne partageraient plus la meme reference) ;
      - absent (controle apparie) -> DEUX appels, dont le bras tabula avec genome=None.
    L'injection rend le premier cas auto-verifiant : `tabula=None` fait LEVER le faux si le bras
    tabula est mesure."""
    baseline = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    journal = []
    C = _inj6_injecte(monkeypatch, [2.0] * 6, tabula=None, journal=journal)
    r = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=6,
                        tabula_meds=baseline)
    mesures = [e for e in journal if e["bras"] != "_load_genome"]
    assert [e["bras"] for e in mesures] == ["champion"], journal
    assert r["tabula_meds"] == baseline and r["_tabula_meds"] == baseline
    assert r["tabula_median"] == pytest.approx(1.0)
    assert r["verdict"] == "TRANSFERE"

    journal2 = []
    C = _inj6_injecte(monkeypatch, [2.0] * 6, baseline, journal=journal2)
    r2 = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=6)
    mesures2 = [e for e in journal2 if e["bras"] != "_load_genome"]
    assert [e["bras"] for e in mesures2] == ["champion", "tabula"], journal2
    assert r2["verdict"] == r["verdict"] and r2["ratios"] == r["ratios"]


def test_run_direction_REFUSES_a_degenerate_argument_BEFORE_touching_the_HoF(monkeypatch):
    """Ou la garde est posee, pas seulement qu'elle leve : le refus doit etre INSTANTANE. Les trois
    arguments degeneres doivent lever AVANT `_load_genome` (qui, en vrai, ecrit `os.environ` et
    RECHARGE `src.seed_ai.persistence` -- un effet de bord global) et donc AVANT toute mesure.
    Controle apparie OBLIGATOIRE (E1) : a k_eval=num_agents=max_ticks=1 la garde ne se declenche PAS
    et l'orchestrateur mesure normalement -- une garde qui refuserait tout serait pire que rien."""
    journal = []
    C = _inj6_injecte(monkeypatch, [2.0], [1.0], journal=journal)
    for kw in ({"k_eval": 0}, {"num_agents": 0}, {"max_ticks": 0},
               {"k_eval": -1}, {"num_agents": -3}, {"max_ticks": -7}):
        appel = {"seed": 42, "k_eval": 1, "num_agents": 1, "max_ticks": 1}
        appel.update(kw)
        with pytest.raises(ValueError, match="degenere"):
            C.run_direction("famine[a]", "hof_a.pkl", "stoneage", **appel)
        assert journal == [], (
            f"{kw} : le refus a coute un acces au HoF ou une mesure ({journal}) -- la garde n'est "
            "pas en TETE de fonction")

    r = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=1,
                        num_agents=1, max_ticks=1)
    assert r["n"] == 1 and r["verdict"] == "NEUTRE"          # la garde sait NE PAS se declencher
    assert [e["bras"] for e in journal] == ["_load_genome", "champion", "tabula"], journal


# ======================================================================================================
# 3. DEFAUTS REELS -- exposes, non corriges (regle du depot : une entree ABSENTE ou DEGENEREE rend
#    INDETERMINE ou LEVE, jamais une affirmation de FOND)
# ======================================================================================================

def test_run_direction_REFUSES_to_publish_NEUTRE_on_an_EMPTY_baseline(monkeypatch):
    """NON-REGRESSION (ex-xfail strict, defaut CORRIGE le 2026-09-08). Reponse connue : le champion
    survit 10 sur les 12 seeds, la baseline fournie est VIDE. Il n'y a rien a comparer.

    AVANT : 'NEUTRE', n=0, median_ratio=0.0, sign_p=1.0, tabula_median=0.0 -- et main() imprimait
    'famine[...] -> stoneage | NEUTRE | ratio_med=0.00 (n_fav=0/0, sign_p=1.0000) | champ=10.0
    tabula=0.0'. Sur le KPI transfer_ratio (SDR-G1), 'pas de transfert' est le resultat ATTENDU du
    depot : un negatif fabrique y ressemble a tous les autres.
    APRES : refus explicite, AVANT tout acces au HoF (le journal reste vide)."""
    journal = []
    C = _inj6_injecte(monkeypatch, [10.0] * 12, tabula=None, journal=journal)
    with pytest.raises(ValueError, match="degenere"):
        C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12, tabula_meds=[])
    assert journal == [], journal
    # CAS NEGATIF APPARIE : une baseline NON vide de la longueur declaree passe et publie un verdict
    r = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12,
                        tabula_meds=[5.0] * 12)
    assert r["verdict"] == "TRANSFERE" and r["n"] == 12


def test_run_direction_REFUSES_to_publish_NUIT_on_a_TOTAL_EXTINCTION(monkeypatch):
    """NON-REGRESSION (ex-xfail strict, defaut CORRIGE le 2026-09-08). Reponse connue : tout le
    monde meurt au premier tick dans LES DEUX bras (survie mediane 0.0 partout, variance nulle).

    AVANT : le plancher epsilon de `paired_ratios` faisait 0/1e-6 = 0.0 sur chaque paire -> mediane
    0.0, n_fav 0/12, sign_p = 2/2^12 = 0.00048828125 -> **'NUIT' (p<0.001) alors que rien n'avait
    ete mesure des deux cotes**. Le docstring du module attendait justement l'inverse ('au plancher
    letal tout ratio vaut ~1 par artefact') : le garde-fou humain lui-meme se trompait de signe.
    APRES : INDETERMINE_EXTINCTION_TOTALE, et AUCUNE grandeur fabriquee."""
    C = _inj6_injecte(monkeypatch, [0.0] * 12, [0.0] * 12)
    r = _inj6_run(C, [0.0] * 12)
    assert r["verdict"] == "INDETERMINE_EXTINCTION_TOTALE", r
    assert r["verdict"] not in ("NUIT", "NEUTRE", "TRANSFERE")
    assert r["median_ratio"] is None and r["sign_p"] is None and r["n"] == 0
    # CAS NEGATIF APPARIE : la MEME dose a un seul seed pres ou le champion survit -> le verdict
    # revient, et il est NEGATIF quand il doit l'etre (l'indetermination n'a pas mange la branche).
    C = _inj6_injecte(monkeypatch, [0.0] * 12, [20.0] * 12)
    vivant = _inj6_run(C, [0.0] * 12)
    assert vivant["verdict"] == "NUIT" and vivant["n"] == 12, vivant


def test_run_direction_REFUSES_a_baseline_whose_length_does_not_match_k_eval(monkeypatch):
    """NON-REGRESSION (ex-xfail strict, defaut CORRIGE le 2026-09-08). Une baseline reutilisee dont
    la LONGUEUR ne correspond pas a k_eval etait acceptee EN SILENCE (troncature par `min()`), dans
    les DEUX sens, avec deux consequences publiables :
      (a) plus COURTE (2 valeurs pour k_eval=12) -> n tombait a 2 ; or a n < 6 le test de signe ne
          peut JAMAIS descendre sous 0.05 (plancher 2/2^n = 0.5 a n=2) : l'instrument devenait
          STRUCTURELLEMENT incapable de rendre autre chose que NEUTRE quelle que soit la dose
          (classe E1), sans aucun signal ;
      (b) plus LONGUE (12 valeurs pour k_eval=6) -> le rapport publiait tabula_median=500.5 (les 12
          FOURNIES) alors que les denominateurs UTILISES avaient pour mediane 1.0 :
          'TRANSFERE | ratio_med=2.00 | champ=2.0 tabula=500.5', incoherent en interne.
    APRES : les deux sens LEVENT, avant le HoF. L'appelant DECLARE son k_eval, on ne devine pas."""
    journal = []
    C = _inj6_injecte(monkeypatch, [2.0] * 12, tabula=None, journal=journal)
    with pytest.raises(ValueError, match="degenere"):
        C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12,
                        tabula_meds=[1.0, 1.0])
    longue = [1.0] * 6 + [1000.0] * 6
    with pytest.raises(ValueError, match="degenere"):
        C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=6,
                        tabula_meds=longue)
    assert journal == [], journal          # refus INSTANTANE, aucun acces au HoF

    # CAS NEGATIF APPARIE : la MEME baseline tronquee a la longueur DECLAREE passe, et le rapport
    # publie alors la mediane des valeurs REELLEMENT utilisees (1.0), pas 500.5.
    C = _inj6_injecte(monkeypatch, [2.0] * 6, tabula=None, journal=journal)
    ok = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=6,
                         tabula_meds=longue[:6])
    assert ok["verdict"] == "TRANSFERE" and ok["n"] == 6
    assert ok["tabula_median"] == pytest.approx(statistics.median(longue[:6]))


# ======================================================================================================
# 4. CAS NEGATIFS APPARIES des gardes ajoutees le 2026-09-08 (classe E1)
#
#    Les trois defauts de la section 3 sont CORRIGES. Une garde qui rend un controle INCREVABLE est
#    PIRE que le defaut qu'elle ferme : pour CHAQUE comportement ajoute, on prouve ici qu'il sait
#    encore NE PAS se declencher, et que l'instrument publie toujours ses DEUX issues.
# ======================================================================================================

def test_extinction_guard_KNOWS_HOW_TO_STAY_DOWN_when_ONE_arm_still_lives(monkeypatch):
    """CAS NEGATIF APPARIE de l'ecart des paires doublement eteintes. Une paire dont UN SEUL bras est
    eteint porte le SIGNE le plus tranche qui soit -- l'ecarter rendrait l'instrument aveugle
    exactement la ou le transfert est maximal ou catastrophique. Reponse connue x2, en forme close :

      champion ETEINT contre baseline vivante (0 vs 20 sur 12 seeds) -> ratios tous 0.0, mediane 0.0
        < 0.95, n_fav 0/12, sign_p = 2/2^12 -> **NUIT** doit toujours etre publie ;
      baseline ETEINTE contre champion vivant (20 vs 0) -> ratios tous 2e7, n_fav 12/12,
        meme sign_p -> **TRANSFERE** doit toujours etre publie.

    Dans les deux cas AUCUNE paire n'est ecartee : `n_ecartees == 0` et `n == 12`."""
    C = _inj6_injecte(monkeypatch, [0.0] * 12, [20.0] * 12)
    mort = _inj6_run(C, [0.0] * 12)
    C = _inj6_injecte(monkeypatch, [20.0] * 12, [0.0] * 12)
    seul_vivant = _inj6_run(C, [20.0] * 12)

    assert mort["verdict"] == "NUIT", mort
    assert mort["n"] == 12 and mort["n_ecartees"] == 0
    assert mort["median_ratio"] == pytest.approx(0.0)
    assert mort["sign_p"] == pytest.approx(0.00048828125)
    assert mort["n_denominateurs_eteints"] == 0 and "why" not in mort, mort

    assert seul_vivant["verdict"] == "TRANSFERE", seul_vivant
    assert seul_vivant["n"] == 12 and seul_vivant["n_ecartees"] == 0
    assert seul_vivant["n_favorable"] == 12
    assert seul_vivant["sign_p"] == pytest.approx(0.00048828125)
    # ...mais l'AMPLITUDE y est fabriquee par le plancher epsilon (20 / 1e-6 = 2e7), et c'est DIT.
    # Le verdict ne lit qu'un SEUIL et un test de SIGNE, tous deux reels ; `median_ratio` non.
    assert seul_vivant["median_ratio"] == pytest.approx(2e7)
    assert seul_vivant["n_denominateurs_eteints"] == 12
    assert "DENOMINATEUR eteint" in seul_vivant["why"], seul_vivant["why"]


def test_run_direction_DROPS_ONLY_the_doubly_extinct_pairs_and_PUBLISHES_their_count(monkeypatch):
    """Le defaut du plancher epsilon agissait dans les DEUX sens, et ce test mesure le second : une
    extinction PARTIELLE n'exagerait pas le negatif, elle EMPOISONNAIT la mediane et gonflait le
    denominateur du test de signe -> un vrai transfert devenait NEUTRE.

    Dose : 6 seeds ou les deux bras sont eteints (0 vs 0) + 6 seeds ou le champion double la survie
    (10 vs 5). Reponse connue en forme close, AVANT / APRES :
      AVANT (verifie ici sur les primitives brutes) : ratios [0,0,0,0,0,0,2,2,2,2,2,2] -> mediane
        1.0, ni > 1.05 ni < 0.95 -> **NEUTRE** ;
      APRES : 6 paires ecartees, 6 retenues a 2.0 -> mediane 2.0, 6/6 favorables,
        sign_p = 2/2^6 = 0.03125 -> **TRANSFERE**, avec `n=6`, `n_ecartees=6` et un `why` qui dit que
        le sign_p publie porte sur le n REDUIT (la puissance perdue est annoncee, pas dissimulee)."""
    import tools.cross_world_transfer as CW
    from tools.curriculum_transfer import compute_transfer_verdict

    champ = [0.0] * 6 + [10.0] * 6
    tabula = [0.0] * 6 + [5.0] * 6
    avant = compute_transfer_verdict(CW.paired_ratios(champ, tabula))
    assert avant["verdict"] == "NEUTRE" and avant["n"] == 12, avant   # le defaut, en forme close

    C = _inj6_injecte(monkeypatch, champ, tabula)
    r = _inj6_run(C, champ)
    assert r["verdict"] == "TRANSFERE", r
    assert r["n"] == 6 and r["n_ecartees"] == 6 and r["n_paires"] == 12
    assert r["median_ratio"] == pytest.approx(2.0) and r["n_favorable"] == 6
    assert r["sign_p"] == pytest.approx(0.03125)
    assert r["ratios"] == [pytest.approx(2.0)] * 6, r
    assert "ECARTEE" in r["why"] and "n REDUIT" in r["why"], r["why"]
    # les mesures BRUTES restent publiees telles quelles : l'ecart est verifiable par un lecteur
    assert r["champ_meds"] == champ and r["tabula_meds"] == tabula


def test_total_extinction_publishes_a_NAMED_indeterminate_and_NOT_a_zero(monkeypatch):
    """Ce que l'INDETERMINE doit contenir, en plus de ne pas etre 'NUIT' : un nom, un compte, et des
    grandeurs ABSENTES plutot que remplacees par 0.0 (un 0.0 de remplacement se relit comme une
    mesure -- c'est le defaut qu'on vient de fermer, pas sa correction). `None` et pas `nan` :
    serialisable en JSON, et toute arithmetique faite dessus par megarde LEVE au lieu d'avaler."""
    import json
    import tools.cross_world_transfer as CW

    C = _inj6_injecte(monkeypatch, [0.0] * 12, [0.0] * 12)
    r = _inj6_run(C, [0.0] * 12)
    assert r["verdict"] == "INDETERMINE_EXTINCTION_TOTALE", r
    assert r["n"] == 0 and r["n_ecartees"] == 12 and r["n_paires"] == 12
    assert r["median_ratio"] is None and r["sign_p"] is None, r
    assert r["ratios"] == []
    assert "rien n'a ete mesure" in r["why"], r["why"]
    # la ligne PUBLIEE ne plante pas et ne fabrique aucun chiffre
    assert CW._fmt(r["median_ratio"]) == "n/a" and CW._fmt(r["sign_p"], "{:.4f}") == "n/a"
    assert CW._fmt(2.0) == "2.00" and CW._fmt(0.0) == "0.00"   # apparie : un 0.0 MESURE s'imprime
    json.dumps({k: v for k, v in r.items() if k != "_tabula_meds"})   # serialisable (None -> null)


def test_baseline_guards_REFUSE_BEFORE_the_HoF_and_KNOW_HOW_TO_STAY_DOWN(monkeypatch):
    """OU les deux nouvelles gardes de baseline sont posees (refus INSTANTANE, avant `_load_genome`
    qui ecrit `os.environ` et RECHARGE un module), ET leur cas negatif apparie : une baseline de la
    longueur DECLAREE passe et rend le verdict attendu a dose connue. Une garde qui refuserait toute
    baseline reutilisee condamnerait l'usage normal de `main()` (une baseline pour 3 champions)."""
    import time

    journal = []
    C = _inj6_injecte(monkeypatch, [2.0] * 6, tabula=None, journal=journal)
    t0 = time.time()
    for quoi, kw in (("baseline VIDE", {"tabula_meds": []}),
                     ("baseline trop COURTE", {"tabula_meds": [1.0, 1.0]}),
                     ("baseline trop LONGUE", {"tabula_meds": [1.0] * 12})):
        with pytest.raises(ValueError, match="degenere"):
            C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=6, **kw)
        assert journal == [], (
            f"{quoi} : le refus a coute un acces au HoF ou une mesure ({journal}) -- la garde n'est "
            "pas en TETE de fonction")
    assert time.time() - t0 < 0.5, "refus trop lent : la garde n'est plus en tete"

    # CAS NEGATIF APPARIE : longueur == k_eval -> la garde ne se declenche PAS
    r = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=6,
                        tabula_meds=[1.0] * 6)
    assert r["verdict"] == "TRANSFERE" and r["n"] == 6 and r["n_ecartees"] == 0
    assert [e["bras"] for e in journal] == ["_load_genome", "champion"], journal

    # et jusqu'au cas limite k_eval=1 : une baseline d'UNE valeur n'est pas une baseline VIDE
    journal.clear()
    C = _inj6_injecte(monkeypatch, [2.0], tabula=None, journal=journal)
    petit = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=1,
                            num_agents=1, max_ticks=1, tabula_meds=[1.0])
    assert petit["n"] == 1 and petit["verdict"] == "NEUTRE" and petit["n_ecartees"] == 0


# ======================================================================================================
# 5. TROIS DEFAUTS DE PLUS, trouves par le REFUTATEUR le 2026-09-08 -- dont DEUX ouverts par le
#    correctif de la section 3 lui-meme (une garde qui DEPLACE un defaut ne le ferme pas).
#    Chaque comportement ajoute porte ici son cas NEGATIF apparie (classe E1).
# ======================================================================================================

def test_report_PUBLISHES_the_medians_of_the_pairs_the_VERDICT_SPEAKS_OF(monkeypatch):
    """DEFAUT 4 -- REOUVERTURE, par l'ecart des paires eteintes, du defaut (b) que la garde de
    longueur venait de fermer : `champ_median` / `tabula_median` portaient sur les k_eval paires
    pendant que le verdict portait sur les seules RETENUES.

    Dose (reponse connue en forme close) : 8 paires doublement eteintes + 6 paires a 10 vs 5.
      verdict = TRANSFERE (mediane 2.0, 6/6 favorables, sign_p = 2/2^6 = 0.03125) ;
      AVANT : `champ_median = 0.0` et `tabula_median = 0.0` (medianes des 14 paires, dominees par
              les 8 zeros) -> main() imprimait
              'TRANSFERE | ratio_med=2.00 (n_fav=6/6, ecartees=8, sign_p=0.0312) | champ=0.0
               tabula=0.0' : un transfert POSITIF a cote d'un champion de survie NULLE ;
      APRES : 10.0 et 5.0 -- les paires dont le verdict parle -- et les brutes restent publiees
              sous `*_toutes_paires`.
    Mesure de l'ampleur : sur 4000 doses tirees au sort en extinction partielle, 950 verdicts de
    fond publiaient des medianes incluant les paires ECARTEES, dont 54 a champ_median = 0.0."""
    champ = [0.0] * 8 + [10.0] * 6
    tabula = [0.0] * 8 + [5.0] * 6
    C = _inj6_injecte(monkeypatch, champ, tabula)
    r = _inj6_run(C, champ)

    assert r["verdict"] == "TRANSFERE" and r["n"] == 6 and r["n_ecartees"] == 8, r
    assert r["sign_p"] == pytest.approx(0.03125)
    assert r["champ_median"] == pytest.approx(10.0), r        # AVANT : 0.0
    assert r["tabula_median"] == pytest.approx(5.0), r        # AVANT : 0.0
    # le ratio des medianes PUBLIEES est enfin coherent avec le ratio median publie
    assert r["champ_median"] / r["tabula_median"] == pytest.approx(r["median_ratio"])
    # les brutes ne sont pas perdues, elles sont NOMMEES pour ce qu'elles sont
    assert r["champ_median_toutes_paires"] == pytest.approx(0.0)
    assert r["tabula_median_toutes_paires"] == pytest.approx(0.0)
    assert "champ_median_toutes_paires" in r["why"], r["why"]

    # CAS NEGATIF APPARIE : sans paire ecartee, les medianes publiees sont EXACTEMENT les brutes
    # (aucun re-calcul silencieux, et la valeur publiee par EDR-156/129 est inchangee).
    C = _inj6_injecte(monkeypatch, [20.0] * 12, [10.0] * 12)
    plein = _inj6_run(C, [20.0] * 12)
    assert plein["n_ecartees"] == 0 and plein["verdict"] == "TRANSFERE"
    assert plein["champ_median"] == plein["champ_median_toutes_paires"] == pytest.approx(20.0)
    assert plein["tabula_median"] == plein["tabula_median_toutes_paires"] == pytest.approx(10.0)


def test_dropping_pairs_BELOW_the_sign_test_floor_is_a_NAMED_indeterminate(monkeypatch):
    """DEFAUT 5 -- l'ecart des paires eteintes pouvait faire tomber le n sous le plancher du test de
    signe, et l'instrument publiait alors 'NEUTRE'. C'est MOT POUR MOT l'argument de classe E1 qui
    fait LEVER sur une baseline trop courte (sous 6 paires, sign_p ne peut JAMAIS franchir 0.05,
    donc NEUTRE par construction), rentre par la porte de derriere.

    Dose : 11 paires doublement eteintes + 1 paire a 10 vs 5.
      AVANT : 'NEUTRE | ratio_med=2.00 (n_fav=1/1, ecartees=11, sign_p=1.0000)' -- sur un KPI dont
              'pas de transfert' est le resultat ATTENDU, ce negatif fabrique est indiscernable ;
      APRES : INDETERMINE_PUISSANCE_DETRUITE, aucune grandeur fabriquee."""
    from tools.cross_world_transfer import N_MIN_SIGNE
    assert N_MIN_SIGNE == 6 and 2.0 / 2 ** 5 >= 0.05 > 2.0 / 2 ** 6   # le plancher, en forme close

    champ = [0.0] * 11 + [10.0]
    C = _inj6_injecte(monkeypatch, champ, [0.0] * 11 + [5.0])
    r = _inj6_run(C, champ)
    assert r["verdict"] == "INDETERMINE_PUISSANCE_DETRUITE", r
    assert r["n"] == 1 and r["n_ecartees"] == 11 and r["n_paires"] == 12
    assert r["median_ratio"] is None and r["sign_p"] is None and r["n_favorable"] is None
    assert "QUELLE QUE SOIT la dose" in r["why"], r["why"]

    # CAS NEGATIF APPARIE 1 : EXACTEMENT N_MIN_SIGNE paires informatives -> le verdict revient.
    champ = [0.0] * 6 + [10.0] * 6
    C = _inj6_injecte(monkeypatch, champ, [0.0] * 6 + [5.0] * 6)
    limite = _inj6_run(C, champ)
    assert limite["verdict"] == "TRANSFERE" and limite["n"] == N_MIN_SIGNE, limite
    assert limite["sign_p"] == pytest.approx(0.03125)

    # CAS NEGATIF APPARIE 2 (E14) : un appelant qui DECLARE k_eval=5, sans aucune paire ecartee,
    # garde son NEUTRE sous-puissant -- c'est SON plan d'experience, pas une perte silencieuse.
    # La garde est bornee a `n_ecartees > 0` precisement pour ne pas re-ecrire ce contrat-la.
    C = _inj6_injecte(monkeypatch, [2.0] * 5, [1.0] * 5)
    declare = _inj6_run(C, [2.0] * 5)
    assert declare["verdict"] == "NEUTRE" and declare["n"] == 5 and declare["n_ecartees"] == 0
    assert declare["sign_p"] == pytest.approx(0.0625)


def test_run_direction_REFUSES_a_baseline_OUT_OF_DOMAIN_and_ACCEPTS_a_measured_zero(monkeypatch):
    """DEFAUT 6 -- aucune garde de DOMAINE : une survie mediane est une mediane d'ages ENTIERS >= 0,
    donc finie et non negative. nan / +-inf / negatif passaient la garde de longueur et
    PRODUISAIENT un verdict de fond (reponses connues, mesurees) :
      +inf -> ratio = x/inf = 0.0, **fini**, donc invisible pour le filtre de non-finitude de
              `compute_transfer_verdict` -> 'NEUTRE' publie a cote de tabula_median=inf ;
      < 0  -> ramene au plancher epsilon -> ratio 2e7 sur les 12 seeds -> 'TRANSFERE' (p<0.001),
              le resultat le PLUS FORT de l'instrument, produit par une survie NEGATIVE.
    Le refus doit etre INSTANTANE (avant `_load_genome`, qui ecrit os.environ et recharge un module).
    """
    journal = []
    C = _inj6_injecte(monkeypatch, [20.0] * 12, tabula=None, journal=journal)
    for quoi in (float("nan"), float("inf"), float("-inf"), -5.0, -1e-9):
        with pytest.raises(ValueError, match="degenere"):
            C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12,
                            tabula_meds=[10.0] * 6 + [quoi] * 6)
    with pytest.raises(ValueError, match="degenere"):        # pas meme un nombre
        C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12,
                        tabula_meds=[10.0] * 11 + ["mort"])
    assert journal == [], journal

    # CAS NEGATIF APPARIE : 0.0 est une extinction MESUREE, pas une entree corrompue -- une garde
    # qui refuserait le zero rendrait l'instrument aveugle au regime letal, qu'il DOIT publier.
    r = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12,
                        tabula_meds=[0.0] * 12)
    assert r["verdict"] == "TRANSFERE" and r["n"] == 12 and r["n_denominateurs_eteints"] == 12
    assert [e["bras"] for e in journal] == ["_load_genome", "champion"], journal


def test_run_direction_REFUSES_a_MEASURED_arm_that_is_degenerate(monkeypatch):
    """La POST-CONDITION posee APRES la mesure etait DECORATIVE : la mutation qui la supprimait ne
    faisait rougir AUCUN test (mesure du 2026-09-08 -- le faux d'injection impose lui-meme
    `len(dose) == k_eval`, donc aucun cas ne tournait dans le regime ou elle s'active ; c'est
    exactement la forme d'erreur du 2026-09-08, 'la garde passe pour verte parce que tous les cas
    tournent hors de son regime'). On la fait donc travailler ici, dans ses DEUX branches, avec un
    faux qui contourne l'invariant du faux standard."""
    import tools.cross_world_transfer as C
    monkeypatch.setattr(C, "_load_genome", lambda p: _INJ6_GENOME)

    # (a) longueur : le bras MESURE ne couvre pas les k_eval seeds -> troncature silencieuse evitee
    monkeypatch.setattr(C, "measure_in_world",
                        lambda w, g, s, k=12, n=12, t=300: [2.0, 2.0])
    with pytest.raises(ValueError, match="mesure degeneree"):
        C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12)

    # (b) domaine : un bras MESURE non fini -- impossible aujourd'hui, mais la garde de tete ne
    # protege que la baseline FOURNIE ; sans celle-ci le prochain refactoring rouvre la porte.
    monkeypatch.setattr(C, "measure_in_world",
                        lambda w, g, s, k=12, n=12, t=300: [2.0] * 11 + [float("nan")])
    with pytest.raises(ValueError, match="degenere"):
        C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12)

    # CAS NEGATIF APPARIE : une mesure de la bonne longueur et dans le domaine passe.
    monkeypatch.setattr(C, "measure_in_world",
                        lambda w, g, s, k=12, n=12, t=300: ([2.0] * 12 if g is not None else [1.0] * 12))
    r = C.run_direction("famine[a]", "hof_a.pkl", "stoneage", seed=42, k_eval=12)
    assert r["verdict"] == "TRANSFERE" and r["n"] == 12


def test_every_verdict_branch_publishes_the_SAME_KEYS_and_fabricates_NO_count(monkeypatch):
    """Le schema de CWT_JSON doit etre STABLE d'une branche a l'autre : un consommateur qui lit
    `n_indetermine` ne doit pas rencontrer un KeyError sur la branche indeterminee, et surtout
    aucune branche ne doit remplacer une grandeur ABSENTE par un chiffre. `n_favorable = 0` sur un
    INDETERMINE se relisait comme une mesure ('aucun seed n'a favorise le champion') alors
    qu'aucun seed n'avait ete compare -- exactement le defaut ferme pour `median_ratio`, laisse
    ouvert sur le compte a cote."""
    import json
    import tools.cross_world_transfer as CW

    C = _inj6_injecte(monkeypatch, [20.0] * 12, [10.0] * 12)
    normal = _inj6_run(C, [20.0] * 12)
    C = _inj6_injecte(monkeypatch, [0.0] * 12, [0.0] * 12)
    total = _inj6_run(C, [0.0] * 12)
    champ = [0.0] * 11 + [10.0]
    C = _inj6_injecte(monkeypatch, champ, [0.0] * 11 + [5.0])
    puissance = _inj6_run(C, champ)

    attendu = set(normal) | {"why"}
    for r in (total, puissance):
        assert set(r) == attendu, sorted(attendu.symmetric_difference(set(r)))
        assert r["median_ratio"] is None and r["sign_p"] is None and r["n_favorable"] is None, r
        assert r["verdict"].startswith("INDETERMINE_")
        json.dumps({k: v for k, v in r.items() if k != "_tabula_meds"})     # None -> null
        # la ligne PUBLIEE ne fabrique aucun compte : 'n_fav=n/a', jamais 'n_fav=0'
        assert CW._fmt(r["n_favorable"], "{:d}") == "n/a"
    assert CW._fmt(normal["n_favorable"], "{:d}") == "12"       # apparie : un compte REEL s'imprime
    assert normal["n_indetermine"] == 0 and total["n_indetermine"] == 12
