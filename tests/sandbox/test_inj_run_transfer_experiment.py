# -*- coding: utf-8 -*-
# P2.44 (2026-09-08) -- INJECTION A DOSE CONNUE, suite de `test_orchestrator_injection.py` (les 5
# prioritaires, la veille). Meme technique : monkeypatch de l'attribut de MODULE appele, cellules
# imposees a DOSE CONNUE, verdict exige en forme close, branches NEGATIVES comprises. AUCUN monde
# construit -> cout nul. Controle E1 PAR MUTATION effectue : l'orchestrateur rendu aveugle a la dose
# fait MOURIR les tests passants. Il ne reste AUCUN `xfail` : les blocs NON-REGRESSION sont d'anciens
# xfail dont le defaut a ete corrige, et ils portent le comportement corrige EN DUR.
# -*- coding: utf-8 -*-
"""INJ-6 -- calibration par INJECTION A DOSE CONNUE de
`tools/curriculum_transfer.py::run_transfer_experiment`.

CE QUI N'ETAIT CALIBRE PAR RIEN. Cet orchestrateur ne simule pas : il APPELLE une mesure d'ere
(`run_era_fn`) et AGREGE deux bras apparies en un verdict TRANSFERE / NUIT / NEUTRE publie dans un
ledger de provenance (`main()` -> `Harness.save`). Sa garde d'ARGUMENTS est calibree depuis le
2026-09-06 (`empty-cohort:raises`, `guard-before-world`). La couche qui transforme des mesures en
AFFIRMATION -- appariement seed-a-seed, budget egal, unite de replication, cablage du regime, et
surtout les BRANCHES DE VERDICT -- ne l'etait pas. C'est exactement la ou un instrument non calibre
ne se contente pas d'echouer : il PRODUIT un resultat.

TECHNIQUE (celle de `tests/sandbox/test_orchestrator_injection.py`). On monkeypatche, DANS
`tools.curriculum_transfer`, les trois seams de module -- `SeedManager` (qui identifie le seed),
`CurriculumRunner` (qui identifie le BRAS et porte sa config de graduation), `make_run_era_fn` /
`_acquire_shared_db` / `async_logger` (le cote monde/disque) -- et on impose des cellules `EraResult`
a DOSE CONNUE, choisies pour que le verdict tombe en FORME CLOSE :
  - `GraduationConfig(max_eras=3)` avec la fenetre par defaut W=5 : l'historique n'atteint jamais W,
    donc AUCUN stage ne diplome et le nombre d'eres est exactement 3 par monde. Le bras tabula-rasa
    (c_floor=1.1 > toute competence <= 1.0) ne diplome jamais non plus -> il tourne exactement T eres.
  - la competence est CONSTANTE dans un bras, donc `final_competence` = la dose imposee, et le
    ratio publie = dose_curr / dose_tab, exactement.
  - n=6 seeds unanimes -> sign_p = 2 * C(6,6)/2^6 = 0.03125 (< 0.05) ; n=5 -> 0.0625 (>= 0.05).
AUCUN monde n'est construit, aucune ere n'est simulee : les 24 cas s'EXECUTENT en < 0.1 s cumulees
(`--durations` : le plus lent est a 0.03 s). Les ~25 s de la commande sont l'IMPORT du module cible
(`tools.curriculum_transfer` -> `main_curriculum` -> les mondes), pas la mesure.

BRANCHES NEGATIVES (classe E1). Un test qui ne peut rendre qu'un verdict positif ne prouve rien :
les branches NEUTRE-dans-la-bande, NEUTRE-faute-de-puissance (la garde E14 reellement LUE) et
NEUTRE-quand-les-seeds-se-contredisent sont calibrees au meme titre que TRANSFERE et NUIT ; chaque
assertion de cablage a son cas apparie qui prouve qu'elle sait encore NE PAS se declencher
(metric='world' -> PAS de survival_competence ; run_era_fn injecte -> AUCUN monde, AUCUN logger).

CONTROLE E1 PAR MUTATION -- reproductible depuis ce fichier, en MEMOIRE (le fichier du depot n'est
jamais touche) :
    INJ6_MUT_TRANSFERT=dose PYTHONPATH=. python -m pytest <ce_fichier> -q -p no:cacheprovider --noconftest
Le hook ci-dessous recharge `tools.curriculum_transfer` depuis sa source avec UNE substitution
textuelle avant tout import (`--noconftest` : le dossier est PARTAGE avec une autre voie du workflow
dont le conftest capture, lui, la variable `INJ6_MUTATION`).

MATRICE DES MORTS MESUREE (9 mutations ; les 16 cas passants meurent, 16/16, chacun sous au moins
une mutation -- et aucune mutation ne tue un cas qu'elle ne vise pas) :
    dose            (ratio <- 1.0)                 -> 8/8 des cas de DOSE meurent
    appariement     (2e reseed supprime)           -> 1 (les deux bras partent du meme seed)
    budget          (max_eras <- 1)                -> 1 (budget egal)
    regime          (competence_fn <- None)        -> 1 (regime cable)  [le cas NEGATIF survit]
    regime-inverse  (competence_fn <- survival)    -> 1 (cas NEGATIF metric='world')
    cible           (bras tabula <- echelle)       -> 10 (dose + budget + mondes annonces)
    garde           (garde <- if False)            -> 1 (garde avant construction)
    moteur          (owns_engine <- True)          -> 1 (aucun monde construit ; run restreint -k)
    logger          (finally <- if False)          -> 2 (regime cable, logger rendu sur levee)
Sous `dose`, trois xfail deviennent XPASS et donc ROUGES : c'est correct -- la mutation supprime
aussi les defauts (un ratio constant n'a plus ni denominateur plancher, ni NaN, ni extinction).

MISE A JOUR DU 2026-09-08 -- LES DEFAUTS SONT CORRIGES DANS `tools/curriculum_transfer.py`.
Deux ancres de mutation ont du etre REPOINTEES (`dose`, `garde`) : le correctif a reecrit les lignes
qu'elles visaient, et une ancre morte fait lever `_applique_mutation` -- le controle E1 serait
devenu inerte. CINQ mutations ont ete AJOUTEES, une par comportement livre. Matrice re-mesuree
(passe 1 : `-k "not DEFAUT"`, baseline 16 verts ; passe 2 : `-k DEFAUT`, ou un cas corrige est
XPASS(strict) donc ROUGE et ou une mutation qui ROUVRE son defaut le fait redevenir XFAIL) :
    dose / appariement / budget / regime / regime-inverse / cible / garde / moteur / logger
        -> inchangees : 8 / 1 / 1 / 1 / 1 / 10 / 1 / 12 / 2 morts, baseline 16 verts preservee
    indetermine  (verdict INDETERMINE <- desarme)  -> rouvre EXACTEMENT le cas NaN
    dedup        (seeds repetes <- regonflent n)   -> rouvre EXACTEMENT le cas seeds dupliques
    metric       (vocabulaire <- rouvert)          -> rouvre EXACTEMENT le cas metric inconnu
    base         (shared_db None <- tolere)        -> rouvre EXACTEMENT le cas base indisponible
    cible-echelle (garde d'arguments <- desarmee)  -> ne rouvre RIEN, et c'est MESURE : il y a DEUX
        gardes independantes (la garde d'arguments, et `_competence_on_target` qui LIT le monde de
        la ligne). Neutraliser la seule premiere laisse la seconde refuser ; neutraliser LES DEUX
        fait revenir le defaut d'origine a l'identique (ratio 3.0 = C sur w_cible / C sur w_gym).
Aucune mutation ne tue un cas qu'elle ne vise pas. La matrice historique ci-dessus reste vraie pour
les 9 mutations d'origine ; les comptes globaux seront a re-mesurer apres conversion des marqueurs.

ADDENDUM 2 (REFUTATEUR, meme jour) -- LES HUIT `xfail(strict)` SONT CONVERTIS. Ils etaient devenus
XPASS(strict), c.-a-d. **FAILED** : la passe corrective a livre le correctif en laissant la suite a
"8 failed, 16 passed", en renvoyant la conversion des marqueurs a plus tard. Un test rouge laisse
derriere un correctif EST le correctif incomplet (classe E14 : relancer et corriger les tests
EXISTANTS fait partie du correctif, pas du nettoyage). Les huit portent desormais le comportement
CORRIGE en dur -- et non plus une NEGATION du defaut : `verdict != 'NUIT'` etait satisfait par
n'importe quoi, y compris par un 'TRANSFERE' tout aussi fabrique ; `except Exception: return`
acceptait n'importe quelle levee, AttributeError de faute de frappe comprise, et n'importe quand,
y compris apres des heures de simulation.

SECTION 5 -- UN DEFAUT DE PLUS, trouve par le REFUTATEUR sur le correctif lui-meme : le TROISIEME
axe du BUDGET. La garde d'arguments couvrait la cohorte (n_seeds), la population (num_agents) et
l'horizon (max_ticks), PAS le budget d'ERES -- alors qu'il entre en prod par la MEME porte que
CT_LADDER/CT_TARGET, que le correctif venait pourtant de fermer (`main()` lit `CT_MAX_ERAS`). Avec
`max_eras <= 0`, `CurriculumRunner.run` ne tourne AUCUNE ere et publie son zero de repli
(`final_competence = history[-1] if history else 0.0`, src/curriculum/runner.py:154) sur chaque
barreau du bras curriculum, pendant que le bras tabula reste protege par `max(1, total_eras)` et
mesure VRAIMENT. A dose connue (bras curriculum 2x MEILLEUR, 6 seeds) :
    max_eras=1  -> TRANSFERE  median=2.0  sign_p=0.031     (la bonne reponse)
    max_eras=0  -> NUIT       median=0.0  sign_p=0.031     (le curriculum declare NUISIBLE)
Direction constante du biais du depot -- une absence de mesure en affirmation NEGATIVE de fond --
et elle survivait au correctif du matin. Trois autres gardes DECORATIVES (aucun test ne rougissait
quand on les supprimait) sont couvertes dans la meme section : le barreau a ZERO ere lu comme une
competence nulle, l'echelle VIDE, et le compte d'indeterminations NEGATIF.
"""
import math
import os
import sys

import pytest

# ------------------------------------------------------------------------------------------------
# CONTROLE E1 : mutation EN MEMOIRE de l'orchestrateur (opt-in par INJ6_MUT_TRANSFERT). Rien n'est ecrit
# sur disque -- `git diff tools/curriculum_transfer.py` reste vide par construction.
# ------------------------------------------------------------------------------------------------
_MUTATIONS = {
    # AVEUGLE A LA DOSE : le ratio ne lit plus les competences mesurees.
    # ⚠️ ANCRE REPOINTEE le 2026-09-08 : le correctif a remplace `ratio = c_curr / max(c_tabula,
    # 1e-6)` par `_ratio_apparie` (le plancher epsilon FABRIQUAIT un verdict depuis une extinction).
    # Sans ce repointage l'assert de `_applique_mutation` aurait leve et le controle E1 serait mort.
    "dose": ("ratio, motif = _ratio_apparie(c_curr, c_tabula)", "ratio, motif = 1.0, None"),
    # AVEUGLE A L'APPARIEMENT : le bras tabula-rasa ne repose plus le seed du bras curriculum.
    "appariement": ("SeedManager(seed).seed_boundary(0)                              # bras tabula-rasa",
                    "pass  # MUTATION-appariement : bras tabula-rasa"),
    # AVEUGLE AU BUDGET : le bras tabula-rasa ne recoit plus le budget d'eres du bras curriculum.
    "budget": ("max_eras=max(1, total_eras))", "max_eras=1)"),
    # AVEUGLE AU REGIME : la metrique demandee n'est plus cablee dans le moteur.
    "regime": ('competence_fn = survival_competence if metric == "survival" else None',
               "competence_fn = None"),
    # REGIME TOUJOURS IMPOSE : mutation APPARIEE de la precedente -- elle doit tuer le cas NEGATIF
    # (metric='world' doit pouvoir ne PAS cabler survival_competence) sans toucher le cas positif.
    "regime-inverse": ('competence_fn = survival_competence if metric == "survival" else None',
                       "competence_fn = survival_competence"),
    # AVEUGLE A LA CIBLE : le bras tabula-rasa ne tourne plus la cible mais l'echelle entiere.
    "cible": ("tt = CurriculumRunner([WorldStage(target)], run_era_fn, no_grad).run()",
              "tt = CurriculumRunner([WorldStage(w) for w in ladder], run_era_fn, no_grad).run()"),
    # GARDE NEUTRALISEE : la cohorte degeneree n'est plus refusee.
    # ⚠️ ANCRE REPOINTEE DEUX FOIS le 2026-09-08 : (1) `seeds` est desormais MATERIALISE avant la
    # garde (un iterateur etait consomme par sa propre garde), donc la garde ne dit plus
    # `list(seeds)` ; (2) le refutateur y a ajoute le TROISIEME axe du budget (`max_eras <= 0`).
    "garde": ("if not seeds or int(num_agents) <= 0 or int(max_ticks) <= 0 or max_eras <= 0:",
              "if False:"),
    # AVEUGLE AU BUDGET D'ERES DEGENERE : seule la clause `max_eras` est retiree de la garde, les
    # trois autres restent armees. Doit tuer EXACTEMENT les cas du budget d'eres nul, et eux seuls.
    "garde-max-eras": ("int(max_ticks) <= 0 or max_eras <= 0:", "int(max_ticks) <= 0:"),
    # ZERO DE REPLI DU RUNNER TOLERE : la 2e garde, independante, qui refuse un barreau a 0 ere.
    "barreau-sans-ere": ('            if int(row.get("eras", 1)) <= 0:',
                         '            if False and int(row.get("eras", 1)) <= 0:'),
    # COMPTE D'INDETERMINATIONS NEGATIF TOLERE.
    "n-indetermine-negatif": ("    if n_indetermine < 0:", "    if False and n_indetermine < 0:"),
    # --- mutations des comportements AJOUTES le 2026-09-08 (chacune doit tuer SES cas, et eux
    # seuls). Elles rendent l'instrument aveugle a exactement une des indeterminations refusees. ---
    # AVEUGLE A L'INDETERMINATION : un ratio non defini redevient un verdict de fond.
    "indetermine": ("    if n_indetermine:\n        verdict = INDETERMINE",
                    "    if False:\n        verdict = INDETERMINE"),
    # PSEUDO-REPLICATION RETABLIE : les seeds repetes regonflent `n`.
    "dedup": ("        seeds = uniques", "        pass  # MUTATION-dedup"),
    # CIBLE NON CONFRONTEE A L'ECHELLE : le ratio peut de nouveau comparer deux mondes.
    "cible-echelle": ("    if target != ladder[-1]:", "    if False and target != ladder[-1]:"),
    # VOCABULAIRE ROUVERT : une metrique inconnue retombe de nouveau en silence.
    "metric": ("    if metric not in METRIQUES:", "    if False and metric not in METRIQUES:"),
    # BASE ABSENTE TOLEREE : le canal de promotion peut de nouveau etre mort sans que rien ne le dise.
    "base": ("            if shared_db is None:", "            if False and shared_db is None:"),
    # AVEUGLE AU SEAM : l'orchestrateur reconstruit un moteur meme quand on lui en injecte un.
    "moteur": ("owns_engine = run_era_fn is None", "owns_engine = True"),
    # LOGGER JAMAIS ARRETE : le `finally` ne rend plus la ressource.
    "logger": ("        if owns_engine and manage_logger:\n            async_logger.stop()",
               "        if False:\n            async_logger.stop()"),
}


def _applique_mutation(nom):
    """Recharge `tools.curriculum_transfer` depuis sa SOURCE avec une substitution unique."""
    import importlib
    import types
    paquet = importlib.import_module("tools")             # paquet-espace-de-noms : pas de __file__
    chemin = os.path.join(os.path.abspath(list(paquet.__path__)[0]), "curriculum_transfer.py")
    with open(chemin, encoding="utf-8") as f:
        src = f.read()
    vieux, neuf = _MUTATIONS[nom]
    assert src.count(vieux) == 1, (
        f"mutation '{nom}' : motif absent ou ambigu ({src.count(vieux)} occurrences) -- "
        "le fichier a change, la mutation ne prouve plus rien")
    mod = types.ModuleType("tools.curriculum_transfer")
    mod.__file__ = chemin
    sys.modules["tools.curriculum_transfer"] = mod
    exec(compile(src.replace(vieux, neuf, 1), chemin, "exec"), mod.__dict__)


if os.environ.get("INJ6_MUT_TRANSFERT"):
    _applique_mutation(os.environ["INJ6_MUT_TRANSFERT"])

import tools.curriculum_transfer as CT                                          # noqa: E402
from src.curriculum.runner import CurriculumRunner as _VraiRunner               # noqa: E402
from src.curriculum.runner import EraResult, GraduationConfig                   # noqa: E402
from src.curriculum.competence import survival_competence                       # noqa: E402


# ================================================================================================
# Pupitre d'injection
# ================================================================================================

_CHAMPION = "INJ6-CHAMP"          # sentinelle : distingue un ancetre herite d'une genese fraiche


class _Pupitre:
    """Journal de tout ce que l'orchestrateur DEMANDE, et source de la dose qu'il RECOIT.

    `dose(seed, bras, monde, import_id) -> float` est fournie par le test : c'est la reponse
    connue. Le pupitre enregistre, sans rien interpreter : les frontieres de seed posees, les
    CurriculumRunner construits (avec leur config de graduation), et chaque appel d'ere.
    """

    def __init__(self, dose, ladder, cible):
        self.dose = dose
        self.ladder = list(ladder)
        self.cible = cible
        self.frontieres = []      # (base_seed, i) de chaque SeedManager(...).seed_boundary(i)
        self.runners = []         # {"bras", "mondes", "grad", "seed"} par CurriculumRunner construit
        self.eres = []            # une entree par appel de run_era_fn
        self.seed = None          # seed courant (pose par le spy de SeedManager)
        self.bras = None          # "curr" | "tab" (pose par le spy de CurriculumRunner)

    def eres_de(self, seed=None, bras=None):
        return [e for e in self.eres
                if (seed is None or e["seed"] == seed) and (bras is None or e["bras"] == bras)]


def _cellule(competence, n=20, ticks=300):
    """Cellule factice de `run_era_fn`, portant TOUTES les cles que la VRAIE mesure renvoie
    (`main_curriculum.make_run_era_fn` : competence, champion_agent_id, raw_stats{n,ticks}) --
    pas seulement celles lues aujourd'hui : si l'orchestrateur se met a lire `raw_stats`, le test
    ne doit pas mentir."""
    return EraResult(competence=float(competence), champion_agent_id=_CHAMPION,
                     raw_stats={"n": int(n), "ticks": int(ticks)})


def _installe(monkeypatch, dose, ladder, cible):
    """Remplace, DANS `tools.curriculum_transfer`, tout ce qui identifie le seed et le bras, et
    tout ce qui touche le monde ou le disque. Le VRAI `CurriculumRunner` est conserve (la logique
    de graduation est donc reellement exercee) : on ne fait que l'observer."""
    pup = _Pupitre(dose, ladder, cible)

    class _SeedSpy:
        def __init__(self, base):
            self.base = int(base)

        def seed_boundary(self, i=0):
            pup.frontieres.append((self.base, int(i)))
            pup.seed = self.base
            return (self.base + int(i)) % (2 ** 32)

    def _runner_spy(stages, run_era_fn, grad_cfg=None, keep_memory=False):
        mondes = [s.world_type for s in stages]
        if mondes == pup.ladder:
            pup.bras = "curr"
        elif mondes == [pup.cible]:
            pup.bras = "tab"
        else:
            pup.bras = "?" + "/".join(mondes)
        pup.runners.append({"bras": pup.bras, "mondes": mondes, "grad": grad_cfg,
                            "seed": pup.seed, "keep_memory": keep_memory})
        return _VraiRunner(stages, run_era_fn, grad_cfg, keep_memory)

    def _moteur(world_type, import_agent_id, keep_mem):
        c = pup.dose(pup.seed, pup.bras, world_type, import_agent_id)
        pup.eres.append({"seed": pup.seed, "bras": pup.bras, "monde": world_type,
                         "import_id": import_agent_id, "keep_mem": keep_mem, "competence": c})
        return _cellule(c)

    def _interdit(*a, **kw):
        raise AssertionError("le cote MONDE a ete touche alors que run_era_fn est injecte")

    monkeypatch.setattr(CT, "SeedManager", _SeedSpy)
    monkeypatch.setattr(CT, "CurriculumRunner", _runner_spy)
    monkeypatch.setattr(CT, "make_run_era_fn", _interdit)
    monkeypatch.setattr(CT, "_acquire_shared_db", _interdit)
    return pup, _moteur


def _dose_par_bras(par_seed):
    """{seed: (C_curriculum, C_tabula)} -> dose constante dans chaque bras."""
    def f(seed, bras, monde, import_id):
        assert seed in par_seed, f"dose non imposee pour le seed {seed!r} : injection incomplete"
        assert bras in ("curr", "tab"), f"bras non identifie ({bras!r}) : appariement casse"
        return par_seed[seed][0 if bras == "curr" else 1]
    return f


_LADDER = ["w_facile", "w_cible"]
_CIBLE = "w_cible"
_GRAD = GraduationConfig(max_eras=3)      # < window=5 -> aucun diplome, 3 eres par monde, exactement


def _experience(monkeypatch, par_seed, ladder=_LADDER, cible=_CIBLE, grad=None, **kw):
    pup, moteur = _installe(monkeypatch, _dose_par_bras(par_seed), ladder, cible)
    res = CT.run_transfer_experiment(list(par_seed), ladder=ladder, target=cible,
                                     grad_cfg=grad or _GRAD, run_era_fn=moteur,
                                     manage_logger=False, **kw)
    return pup, res


# ================================================================================================
# 1. LES BRANCHES DE VERDICT, a dose imposee, en forme close (positives ET negatives)
# ================================================================================================

def test_verdict_TRANSFERE_lit_la_dose_qu_il_pretend_lire(monkeypatch):
    """6 seeds unanimes a 0.5/0.4 = 1.25. Forme close : median 1.25, n_fav 6/6,
    sign_p = 2*C(6,6)/2^6 = 0.03125 < 0.05 -> TRANSFERE."""
    _, res = _experience(monkeypatch, {s: (0.5, 0.4) for s in (11, 22, 33, 44, 55, 66)})
    assert res["verdict"] == "TRANSFERE"
    assert res["n"] == 6 and res["n_favorable"] == 6
    assert res["median_ratio"] == pytest.approx(1.25)
    assert res["sign_p"] == pytest.approx(0.03125)
    assert [p["ratio"] for p in res["per_seed"]] == [pytest.approx(1.25)] * 6


def test_verdict_NUIT_lit_la_dose_qu_il_pretend_lire(monkeypatch):
    """Dose INVERSEE (0.4/0.5 = 0.8) : la meme machinerie doit rendre l'affirmation OPPOSEE.
    Sans ce cas, un instrument qui rendrait TRANSFERE quoi qu'il arrive passerait (E1)."""
    _, res = _experience(monkeypatch, {s: (0.4, 0.5) for s in (11, 22, 33, 44, 55, 66)})
    assert res["verdict"] == "NUIT"
    assert res["n"] == 6 and res["n_favorable"] == 0
    assert res["median_ratio"] == pytest.approx(0.8)
    assert res["sign_p"] == pytest.approx(0.03125)


def test_verdict_NEUTRE_quand_l_effet_est_DANS_la_bande(monkeypatch):
    """Branche NEGATIVE : effet REEL et unanime (6/6, sign_p 0.031) mais +2 % seulement, sous la
    bande neutre de 5 %. C'est elle qui empeche de publier TRANSFERE sur un decalage minuscule."""
    _, res = _experience(monkeypatch, {s: (0.51, 0.5) for s in (11, 22, 33, 44, 55, 66)})
    assert res["verdict"] == "NEUTRE"
    assert res["n_favorable"] == 6 and res["sign_p"] == pytest.approx(0.03125)
    assert res["median_ratio"] == pytest.approx(1.02)


def test_verdict_NEUTRE_quand_la_PUISSANCE_manque_garde_E14(monkeypatch):
    """Branche NEGATIVE, et la seule qui prouve que `sign_p` est LU et pas seulement CALCULE
    (classe E14, cf. tools/curriculum_transfer.py:50-52). 5 seeds unanimes a +50 % : l'amplitude
    ecrase la bande, mais sign_p = 2*C(5,5)/2^5 = 0.0625 >= 0.05 -> NEUTRE, pas TRANSFERE."""
    _, res = _experience(monkeypatch, {s: (0.75, 0.5) for s in (11, 22, 33, 44, 55)})
    assert res["n"] == 5 and res["n_favorable"] == 5
    assert res["median_ratio"] == pytest.approx(1.5)
    assert res["sign_p"] == pytest.approx(0.0625)
    assert res["verdict"] == "NEUTRE", "amplitude publiee sans puissance : garde E14 non lue"


def test_verdict_NEUTRE_quand_les_seeds_se_CONTREDISENT(monkeypatch):
    """Branche NEGATIVE : mediane 1.5 (bien au-dessus de la bande) mais 4 seeds sur 6 seulement
    du bon cote -> sign_p = 2*(C(6,4)+C(6,5)+C(6,6))/2^6 = 0.6875 -> NEUTRE. L'unite de
    replication (le seed) prime sur l'amplitude agregee."""
    par_seed = {11: (0.75, 0.5), 22: (0.75, 0.5), 33: (0.75, 0.5), 44: (0.75, 0.5),
                55: (0.25, 0.5), 66: (0.25, 0.5)}
    _, res = _experience(monkeypatch, par_seed)
    assert res["median_ratio"] == pytest.approx(1.5)
    assert res["n_favorable"] == 4 and res["n"] == 6
    assert res["sign_p"] == pytest.approx(0.6875)
    assert res["verdict"] == "NEUTRE"


def test_le_verdict_suit_la_DOSE_seed_par_seed(monkeypatch):
    """Dose VARIABLE : chaque seed recoit son propre couple, le verdict doit etre la forme close
    de CES ratios-la. Pin aussi le traitement des EGALITES : le seed a ratio exactement 1.0 compte
    dans `n` mais est exclu du test de signe (effective) -> sign_p sur 5, pas 6."""
    par_seed = {11: (0.9, 0.3),    # 3.0
                22: (0.8, 0.4),    # 2.0
                33: (0.6, 0.4),    # 1.5
                44: (0.5, 0.5),    # 1.0  <- egalite exacte
                55: (0.4, 0.8),    # 0.5
                66: (0.3, 0.6)}    # 0.5
    _, res = _experience(monkeypatch, par_seed)
    attendus = [3.0, 2.0, 1.5, 1.0, 0.5, 0.5]
    assert [p["ratio"] for p in res["per_seed"]] == [pytest.approx(a) for a in attendus]
    assert res["median_ratio"] == pytest.approx(1.25)          # (1.0 + 1.5) / 2
    assert res["n_favorable"] == 3 and res["n"] == 6
    assert res["sign_p"] == pytest.approx(1.0)                 # k=3 sur 5 effectifs -> p = 1.0
    assert res["verdict"] == "NEUTRE"


# ================================================================================================
# 2. APPARIEMENT, BUDGET, UNITE DE REPLICATION
# ================================================================================================

def test_les_deux_bras_partent_du_MEME_seed(monkeypatch):
    """Appariement : exactement DEUX frontieres de seed par seed, a la MEME graine et au MEME
    indice de frontiere. Un seul reseed (ou deux graines differentes) rendrait les bras non
    comparables tout en laissant le verdict s'imprimer."""
    seeds = (11, 22, 33)
    pup, _ = _experience(monkeypatch, {s: (0.6, 0.5) for s in seeds})
    assert pup.frontieres == [(s, 0) for s in seeds for _ in range(2)]


def test_budget_EGAL_le_bras_tabula_tourne_exactement_T_eres(monkeypatch):
    """Budget compute egal : le bras tabula-rasa recoit `max_eras = total_eras` du bras curriculum
    ET un `c_floor` de 1.1 qui lui interdit de diplomer (sinon il s'arreterait tot et le budget
    serait faux). Forme close : 3 eres x 2 mondes = 6 eres dans chaque bras."""
    pup, res = _experience(monkeypatch, {11: (0.6, 0.5)})
    row = res["per_seed"][0]
    assert row["total_eras"] == 6                                     # 3 eres x 2 mondes
    assert len(pup.eres_de(11, "curr")) == 6
    assert len(pup.eres_de(11, "tab")) == row["total_eras"] == 6
    grad_tab = [r["grad"] for r in pup.runners if r["bras"] == "tab"][0]
    assert grad_tab.max_eras == row["total_eras"]
    assert grad_tab.c_floor == 1.1, "sans plancher inatteignable, le bras tabula peut diplomer tot"
    assert (grad_tab.window, grad_tab.eps_plateau, grad_tab.patience) == (
        _GRAD.window, _GRAD.eps_plateau, _GRAD.patience)


def test_chaque_bras_tourne_les_mondes_qu_il_annonce(monkeypatch):
    """Cablage des mondes : le bras curriculum parcourt l'echelle DANS L'ORDRE ; le bras
    tabula-rasa ne touche QUE la cible. Et il est le seul a l'aborder sans ancetre herite."""
    pup, _ = _experience(monkeypatch, {11: (0.6, 0.5)})
    assert [r["mondes"] for r in pup.runners] == [_LADDER, [_CIBLE]]
    assert [e["monde"] for e in pup.eres_de(11, "curr")] == ["w_facile"] * 3 + ["w_cible"] * 3
    assert {e["monde"] for e in pup.eres_de(11, "tab")} == {_CIBLE}
    assert all(e["import_id"] is None for e in pup.eres_de(11, "tab"))
    herites = [e["import_id"] for e in pup.eres_de(11, "curr") if e["monde"] == _CIBLE]
    assert herites == [_CHAMPION] * 3, "le bras curriculum n'herite pas du champion promu"


def test_l_unite_de_replication_est_le_SEED(monkeypatch):
    """`n` = nombre de seeds (pas d'eres, pas d'agents) : une ligne par seed, dans l'ordre, et le
    ratio de la ligne est bien le quotient des deux competences de CE seed."""
    par_seed = {11: (0.9, 0.3), 22: (0.6, 0.4), 33: (0.4, 0.8)}
    _, res = _experience(monkeypatch, par_seed)
    assert res["n"] == 3 == len(res["per_seed"])
    assert [p["seed"] for p in res["per_seed"]] == [11, 22, 33]
    for p in res["per_seed"]:
        assert (p["C_curr"], p["C_tabula"]) == par_seed[p["seed"]]
        assert p["ratio"] == pytest.approx(p["C_curr"] / p["C_tabula"])
    assert res["config"]["seeds"] == [11, 22, 33]


def test_le_ratio_apparie_les_deux_bras_du_MEME_seed(monkeypatch):
    """Un decalage d'un cran dans l'appariement (curr du seed i / tab du seed i+1) est invisible
    sur des doses uniformes : on impose ici des doses CROISEES telles qu'un tel decalage rendrait
    1.0 partout au lieu de 3.0 et 1/3."""
    _, res = _experience(monkeypatch, {11: (0.9, 0.3), 22: (0.3, 0.9)})
    assert res["per_seed"][0]["ratio"] == pytest.approx(3.0)
    assert res["per_seed"][1]["ratio"] == pytest.approx(1.0 / 3.0)
    assert res["verdict"] == "NEUTRE", "deux seeds ne peuvent pas conclure (sign_p = 1.0)"


# ================================================================================================
# 3. CABLAGE DU REGIME (le chemin owns_engine, sans qu'aucun monde ne soit construit)
# ================================================================================================

class _FauxLogger:
    def __init__(self):
        self.evenements = []

    def start(self):
        self.evenements.append("start")

    def stop(self):
        self.evenements.append("stop")


class _FausseConfig:
    """Substitut de WorldConfig : ne retient que ce que l'orchestrateur y ECRIT."""


def _installe_moteur(monkeypatch, competence=0.5, db="DB-SENTINELLE"):
    """Chemin owns_engine : on intercepte la FABRIQUE du moteur (`make_run_era_fn`) au lieu du
    moteur -- c'est la que le regime demande est cable. Aucun monde n'est construit."""
    vu = {}

    def _fabrique(shared_db, cfg, num_agents=60, max_ticks=400, deterministic=False,
                  competence_fn=None):
        vu.update(shared_db=shared_db, cfg=cfg, num_agents=num_agents, max_ticks=max_ticks,
                  deterministic=deterministic, competence_fn=competence_fn)
        return lambda world_type, import_id, keep_mem: _cellule(competence)

    journal = _FauxLogger()
    monkeypatch.setattr(CT, "make_run_era_fn", _fabrique)
    monkeypatch.setattr(CT, "_acquire_shared_db", lambda: db)
    monkeypatch.setattr(CT, "WorldConfig", _FausseConfig)
    monkeypatch.setattr(CT, "async_logger", journal)
    return vu, journal


def test_le_regime_demande_est_CABLE_dans_le_moteur(monkeypatch):
    """Ce que l'appelant demande (cohorte, horizon, economie d'energie, metrique de survie,
    determinisme) doit arriver INTACT a la fabrique du moteur -- et le ledger doit republier les
    memes valeurs."""
    vu, journal = _installe_moteur(monkeypatch)
    res = CT.run_transfer_experiment([11], ladder=["w_a"], target="w_a", num_agents=7,
                                     max_ticks=13, metric="survival", base_metabolism=0.25,
                                     forage_payoff=3.0, grad_cfg=GraduationConfig(max_eras=1))
    assert (vu["num_agents"], vu["max_ticks"]) == (7, 13)
    assert vu["deterministic"] is True, "verrou repro Dev #3 : bras apparies non reproductibles"
    assert vu["competence_fn"] is survival_competence
    assert (vu["cfg"].base_metabolism, vu["cfg"].forage_payoff) == (0.25, 3.0)
    assert vu["shared_db"] == "DB-SENTINELLE"
    assert journal.evenements == ["start", "stop"]
    assert res["config"]["num_agents"] == 7 and res["config"]["max_ticks"] == 13
    assert res["config"]["base_metabolism"] == 0.25 and res["config"]["forage_payoff"] == 3.0


def test_metric_world_ne_cable_PAS_la_metrique_de_survie(monkeypatch):
    """Cas NEGATIF apparie du precedent (E1) : la meme assertion doit savoir NE PAS se declencher.
    metric='world' -> aucune fonction de competence imposee, la metrique par-monde reprend."""
    vu, _ = _installe_moteur(monkeypatch)
    res = CT.run_transfer_experiment([11], ladder=["w_a"], target="w_a", metric="world",
                                     grad_cfg=GraduationConfig(max_eras=1))
    assert vu["competence_fn"] is None
    assert res["config"]["metric"] == "world"


def test_run_era_fn_injecte_ne_construit_AUCUN_monde(monkeypatch):
    """Cas NEGATIF du cablage : moteur injecte -> ni fabrique, ni base, ni logger, meme avec
    manage_logger=True. C'est ce qui rend cette calibration gratuite ; si ca cassait, tous les
    cas ci-dessus construiraient des mondes en silence."""
    journal = _FauxLogger()

    def _interdit(*a, **kw):
        raise AssertionError("cote monde touche alors que run_era_fn est injecte")

    monkeypatch.setattr(CT, "make_run_era_fn", _interdit)
    monkeypatch.setattr(CT, "_acquire_shared_db", _interdit)
    monkeypatch.setattr(CT, "async_logger", journal)
    res = CT.run_transfer_experiment(
        [11], ladder=["w_a"], target="w_a", grad_cfg=GraduationConfig(max_eras=1),
        manage_logger=True,
        run_era_fn=lambda world_type, import_id, keep_mem: _cellule(0.5))
    assert journal.evenements == []
    assert res["n"] == 1


def test_le_logger_est_rendu_meme_quand_la_mesure_LEVE(monkeypatch):
    """La ressource est rendue dans le `finally` : une ere qui explose ne doit pas laisser le
    worker async ouvert (contention KuzuDB pour la session suivante)."""
    _, journal = _installe_moteur(monkeypatch)

    def _fabrique_qui_explose(*a, **kw):
        def _boum(*aa, **kk):
            raise RuntimeError("ere en echec")
        return _boum

    monkeypatch.setattr(CT, "make_run_era_fn", _fabrique_qui_explose)
    with pytest.raises(RuntimeError, match="ere en echec"):
        CT.run_transfer_experiment([11], ladder=["w_a"], target="w_a",
                                   grad_cfg=GraduationConfig(max_eras=1))
    assert journal.evenements == ["start", "stop"]


def test_la_garde_d_arguments_precede_TOUTE_construction(monkeypatch):
    """Ou la garde est posee, pas seulement qu'elle leve : cohorte vide / cohorte d'agents nulle /
    horizon nul -> refus AVANT la fabrique du moteur, la base et le logger."""
    def _interdit(*a, **kw):
        raise AssertionError("garde posee TROP BAS : le monde a ete touche avant le refus")

    journal = _FauxLogger()
    monkeypatch.setattr(CT, "make_run_era_fn", _interdit)
    monkeypatch.setattr(CT, "_acquire_shared_db", _interdit)
    monkeypatch.setattr(CT, "async_logger", journal)
    for kw in ({"seeds": []}, {"seeds": [0], "num_agents": 0}, {"seeds": [0], "max_ticks": 0}):
        seeds = kw.pop("seeds")
        with pytest.raises(ValueError, match="degenere"):
            CT.run_transfer_experiment(seeds, ladder=["w_a"], target="w_a", **kw)
    assert journal.evenements == [], "le logger a ete demarre avant le refus"


# ================================================================================================
# 4. NON-REGRESSION -- huit DEFAUTS REELS, exposes ici en xfail strict le 2026-09-08 puis CORRIGES
#    dans `tools/curriculum_transfer.py` le meme jour. Les marqueurs sont CONVERTIS : ils etaient
#    devenus XPASS(strict), c.-a-d. FAILED, et la passe corrective avait laisse la suite a
#    "8 failed, 16 passed". Un test rouge laisse derriere un correctif EST le correctif incomplet
#    (classe E14 : relancer et corriger les tests EXISTANTS fait partie du correctif). Chaque cas
#    porte desormais le comportement CORRIGE en dur -- et non plus une simple negation du defaut
#    (`verdict != 'NUIT'` etait satisfait par n'importe quoi, y compris par un 'TRANSFERE' tout
#    aussi fabrique).
# ================================================================================================

def test_NONREG_seeds_iterateur_MESURE_et_non_avale_par_sa_propre_garde(monkeypatch):
    """DEFAUT CORRIGE. La garde materialisait `seeds` par `list(seeds)` et JETAIT le resultat : un
    ITERATEUR etait consomme par la garde, la boucle `for seed in seeds` ne voyait plus rien, et
    n=0 / per_seed=[] / config.seeds=[] sortaient en verdict 'NEUTRE' -- une affirmation de fond
    produite par ZERO mesure."""
    pup, moteur = _installe(monkeypatch, _dose_par_bras({s: (0.6, 0.5) for s in (11, 22, 33)}),
                            _LADDER, _CIBLE)
    res = CT.run_transfer_experiment((s for s in (11, 22, 33)), ladder=_LADDER, target=_CIBLE,
                                     grad_cfg=_GRAD, run_era_fn=moteur, manage_logger=False)
    assert res["n"] == 3, "un iterateur de seeds doit etre mesure, ou refuse -- jamais avale"
    assert [p["seed"] for p in res["per_seed"]] == [11, 22, 33]
    assert res["config"]["seeds"] == [11, 22, 33]
    assert len(pup.eres_de(11, "curr")) == 6, "le seed lu par la garde doit avoir REELLEMENT tourne"


def test_NONREG_cible_hors_echelle_REFUSEE_avant_toute_ere(monkeypatch):
    """DEFAUT CORRIGE. `target` n'etait jamais confronte a `ladder` : quand la cible n'est pas le
    dernier barreau, le bras curriculum ne la visite JAMAIS et `_competence_on_target` rendait la
    competence du DERNIER barreau parcouru -- un « ratio de transfert » qui divise la competence sur
    le monde A par celle sur le monde B (mesure : ladder=[a,b], target=gym -> 0.9/0.3 = 3.0 publie).
    Atteignable en prod par CT_LADDER / CT_TARGET.

    ⚠️ Le cas d'origine acceptait `except ValueError: return` -- donc n'importe quelle levee, y
    compris une levee TARDIVE au fond de la boucle, apres des heures de simulation. On exige
    desormais le MESSAGE de la garde d'arguments ET le refus INSTANTANE (aucune ere n'a tourne),
    c.-a-d. OU la garde est posee et pas seulement qu'elle leve."""
    doses = {"w_facile": 0.1, "w_cible": 0.9, "w_gym": 0.3}

    def dose(seed, bras, monde, import_id):
        return doses[monde]

    pup, moteur = _installe(monkeypatch, dose, _LADDER, "w_gym")
    with pytest.raises(ValueError, match="dernier barreau"):
        CT.run_transfer_experiment([11], ladder=_LADDER, target="w_gym", grad_cfg=_GRAD,
                                   run_era_fn=moteur, manage_logger=False)
    assert pup.eres == [] and pup.runners == [], (
        "refus TARDIF : des eres ont tourne avant que la cible hors echelle soit refusee")


def test_NONREG_la_SECONDE_garde_refuse_la_cible_meme_si_la_premiere_est_desarmee(monkeypatch):
    """CAS APPARIE du precedent : il y a DEUX gardes independantes, et celle-ci est mesuree ici
    SANS toucher au module. `_competence_on_target` LIT le monde de la ligne au lieu de prendre
    `[-1]` en aveugle -- c'est elle qui empeche le ratio de comparer deux mondes quand la garde
    d'arguments est contournee (echelle et cible coherentes a l'entree, transcript qui ne visite
    pas la cible). Sans ce cas, la mutation `cible-echelle` ne tuerait AUCUN test et la seconde
    garde serait decorative (classe E1)."""
    tc = [{"world": "w_facile", "eras": 3, "final_competence": 0.9}]
    with pytest.raises(ValueError, match="jamais arrete"):
        CT._competence_on_target(tc, "w_cible")
    # ... et elle sait NE PAS se declencher quand la cible EST visitee.
    tc.append({"world": "w_cible", "eras": 3, "final_competence": 0.3})
    assert CT._competence_on_target(tc, "w_cible") == 0.3


def test_NONREG_extinction_des_DEUX_bras_rend_INDETERMINE_NOMME(monkeypatch):
    """DEFAUT CORRIGE, le plus grave. `max(c_tabula, 1e-6)` traitait l'EXTINCTION comme une mesure :
    les deux bras eteints (0/0) publiaient ratio=0.0 sur 6 seeds, median 0.0, sign_p 0.031 et
    VERDICT='NUIT' -- le curriculum declare NUISIBLE par une ABSENCE de donnee.

    ⚠️ L'assertion d'origine (`verdict != 'NUIT'`) etait satisfaite par n'importe quel autre
    verdict, 'TRANSFERE' fabrique compris. On exige le verdict NOMME, son COMPTE, et le motif."""
    _, res = _experience(monkeypatch, {s: (0.0, 0.0) for s in (11, 22, 33, 44, 55, 66)})
    assert res["verdict"] == CT.INDETERMINE
    assert res["n"] == 6 and res["n_indetermine"] == 6
    assert [p["ratio"] for p in res["per_seed"]] == [None] * 6
    assert {p["ratio_indetermine"] for p in res["per_seed"]} == {"bras_tabula_eteint"}
    assert [p["C_curr"] for p in res["per_seed"]] == [0.0] * 6    # la mesure BRUTE est conservee


def test_NONREG_denominateur_eteint_ne_fabrique_plus_TRANSFERE(monkeypatch):
    """DEFAUT CORRIGE, face SYMETRIQUE du precedent : un bras tabula ETEINT devenait un
    denominateur plancher 1e-6 -> ratio 500000 -> median_ratio=500000 et VERDICT='TRANSFERE'. Le
    verdict ne naissait pas d'un transfert mais d'une division par le plancher."""
    _, res = _experience(monkeypatch, {s: (0.5, 0.0) for s in (11, 22, 33, 44, 55, 66)})
    assert res["verdict"] == CT.INDETERMINE and res["n_indetermine"] == 6
    assert all(p["ratio"] is None and p["ratio_indetermine"] == "bras_tabula_eteint"
               for p in res["per_seed"])
    assert not any(isinstance(p["ratio"], float) and p["ratio"] > 1e3 for p in res["per_seed"]), (
        "une amplitude fabriquee par le plancher epsilon est encore publiee")


def test_NONREG_competence_NaN_n_est_plus_AVALEE_en_verdict_NEUTRE(monkeypatch):
    """DEFAUT CORRIGE (forme (b) du catalogue : le nan avale). `r > 1.0` est faux pour NaN, et
    `med > 1.0+band` / `med < 1.0-band` aussi -> la branche `else` rendait 'NEUTRE' avec
    median_ratio=nan publie a cote : l'instrument SAIT que la mesure est cassee et affirme
    « pas d'effet ». Le motif publie doit distinguer la NON-FINITUDE de l'extinction."""
    nan = float("nan")
    _, res = _experience(monkeypatch, {s: (nan, 0.5) for s in (11, 22, 33, 44, 55, 66)})
    assert res["verdict"] == CT.INDETERMINE and res["n_indetermine"] == 6
    assert {p["ratio_indetermine"] for p in res["per_seed"]} == {"competence_non_finie"}
    assert all(p["ratio"] is None for p in res["per_seed"]), (
        "un NaN est encore publie comme ratio dans le ledger de provenance")
    assert math.isnan(res["median_ratio"])          # convention du depot : nan quand rien n'est defini


def test_NONREG_UN_SEUL_seed_non_fini_suffit_a_rendre_le_verdict_INDETERMINE(monkeypatch):
    """REGIME que le cas ci-dessus ne visite pas : la garde ne doit pas exiger que TOUS les seeds
    soient casses. 5 seeds mesures et unanimes (ratio 2.0, sign_p 0.0625) + 1 seed NaN -> le
    verdict ne peut pas etre un verdict de fond. Sans ce cas, une garde qui n'agirait que sur la
    cohorte ENTIEREMENT cassee passerait pour verte."""
    nan = float("nan")
    par_seed = {s: (0.8, 0.4) for s in (11, 22, 33, 44, 55)}
    par_seed[66] = (nan, 0.4)
    _, res = _experience(monkeypatch, par_seed)
    assert res["verdict"] == CT.INDETERMINE
    assert res["n"] == 6 and res["n_indetermine"] == 1
    assert res["median_ratio"] == pytest.approx(2.0)      # les 5 mesures restent LISIBLES


def test_NONREG_seeds_dupliques_ne_gonflent_plus_le_n(monkeypatch):
    """DEFAUT CORRIGE (pseudo-replication). La garde refusait la cohorte VIDE mais pas la cohorte
    REPETEE : six fois le meme seed = UNE seule replication independante (les deux bras sont
    deterministes a seed fixe), et pourtant n=6, sign_p=0.03125 -> 'TRANSFERE' publie depuis UN
    replicat. On exige en plus que le monde n'ait tourne qu'UNE fois par bras : de-dupliquer le
    `n` publie sans de-dupliquer la MESURE laisserait le cout x6 et le meme ratio six fois."""
    pup, moteur = _installe(monkeypatch, _dose_par_bras({7: (0.5, 0.4)}), _LADDER, _CIBLE)
    res = CT.run_transfer_experiment([7] * 6, ladder=_LADDER, target=_CIBLE, grad_cfg=_GRAD,
                                     run_era_fn=moteur, manage_logger=False)
    assert res["n"] == 1 and res["config"]["seeds"] == [7]
    assert len(res["per_seed"]) == 1
    assert res["sign_p"] == 1.0 and res["verdict"] == "NEUTRE", (
        "un seul replicat ne peut rien conclure : sign_p=1.0 par construction")
    assert pup.frontieres == [(7, 0), (7, 0)], "le seed repete a ete RE-SIMULE (cout x6 pour rien)"


def test_NONREG_metric_hors_vocabulaire_REFUSEE_avant_toute_construction(monkeypatch):
    """DEFAUT CORRIGE. `metric` n'etait compare qu'a 'survival' : toute autre valeur (faute de
    frappe comprise) retombait EN SILENCE sur la metrique par-monde pendant que le ledger
    republiait la valeur DEMANDEE -- la grandeur publiee n'etait pas celle qui a agi. Atteignable
    en prod par CT_METRIC. On exige le message ET le refus AVANT la fabrique du moteur."""
    vu, journal = _installe_moteur(monkeypatch)
    with pytest.raises(ValueError, match="metric"):
        CT.run_transfer_experiment([11], ladder=["w_a"], target="w_a", metric="survie",
                                   grad_cfg=GraduationConfig(max_eras=1))
    assert vu == {} and journal.evenements == [], (
        "refus TARDIF : le moteur ou le logger ont ete touches avant que la metrique soit refusee")


def test_NONREG_base_indisponible_LEVE_au_lieu_de_publier_un_verdict(monkeypatch):
    """DEFAUT CORRIGE. `_acquire_shared_db()` peut rendre None (timeout de 5 s,
    main_curriculum.py:151-158) et le retour n'etait PAS teste, alors que `run_curriculum` traite
    le meme None comme FATAL. Sans base, `init_primordial_soup` saute l'import du champion : le
    canal de PROMOTION -- l'objet meme de l'experience -- est mort, les deux bras deviennent
    structurellement identiques, et le « pas de transfert » publie ne mesure que l'absence de base.

    ⚠️ Le cas d'origine acceptait `except Exception: return`, donc AUSSI une AttributeError due a
    une faute de frappe. On exige le type et le message, et que la ressource soit rendue."""
    vu, journal = _installe_moteur(monkeypatch, db=None)
    with pytest.raises(RuntimeError, match="KuzuDB indisponible"):
        CT.run_transfer_experiment([11], ladder=["w_a"], target="w_a",
                                   grad_cfg=GraduationConfig(max_eras=1))
    assert journal.evenements == ["start", "stop"], (
        "le logger async n'a pas ete rendu par le `finally` : contention KuzuDB pour la suite")
    assert vu == {}, "le moteur a ete fabrique malgre l'absence de base"


def test_NONREG_une_base_PRESENTE_ne_declenche_PAS_le_refus(monkeypatch):
    """CAS NEGATIF APPARIE du precedent (classe E1) : la garde doit savoir NE PAS se declencher.
    Sans lui, `if True: raise` passerait le cas ci-dessus tout en rendant l'instrument inutilisable."""
    vu, journal = _installe_moteur(monkeypatch, db="DB-SENTINELLE")
    res = CT.run_transfer_experiment([11], ladder=["w_a"], target="w_a",
                                     grad_cfg=GraduationConfig(max_eras=1))
    assert vu["shared_db"] == "DB-SENTINELLE" and res["n"] == 1
    assert journal.evenements == ["start", "stop"]


# ------------------------------------------------------------------------------------------------
# 5. DEFAUT TROUVE PAR LE REFUTATEUR SUR LE CORRECTIF LUI-MEME (2026-09-08) -- le TROISIEME axe du
#    budget. La garde d'arguments couvrait la cohorte, la population et l'horizon, PAS le budget
#    d'eres, alors qu'il entre en prod par la meme porte (`CT_MAX_ERAS`).
# ------------------------------------------------------------------------------------------------

def test_DEFAUT_budget_d_eres_NUL_fabriquait_un_verdict_NUIT(monkeypatch):
    """REPONSE CONNUE : la dose est choisie pour que la BONNE reponse soit 'TRANSFERE' (le bras
    curriculum vaut 2x le tabula). Avec `max_eras=0`, `CurriculumRunner.run` ne tourne AUCUNE ere
    et publie son zero de repli (`final_competence = history[-1] if history else 0.0`) sur chaque
    barreau du bras curriculum, tandis que le bras tabula reste protege par `max(1, total_eras)` et
    mesure VRAIMENT. L'asymetrie transformait l'absence de mesure en 'NUIT' unanime a sign_p=0.031.
    La garde doit refuser EN TETE, avant toute construction."""
    pup, moteur = _installe(monkeypatch, _dose_par_bras({s: (0.8, 0.4) for s in (11, 22, 33)}),
                            _LADDER, _CIBLE)
    for me in (0, -5):
        with pytest.raises(ValueError, match="degenere"):
            CT.run_transfer_experiment([11, 22, 33], ladder=_LADDER, target=_CIBLE,
                                       grad_cfg=GraduationConfig(max_eras=me),
                                       run_era_fn=moteur, manage_logger=False)
    assert pup.eres == [] and pup.runners == [], "refus TARDIF : des eres ont tourne avant le refus"


def test_DEFAUT_budget_d_eres_NUL_le_cas_NEGATIF_apparie(monkeypatch):
    """CAS NEGATIF APPARIE (classe E1) : `max_eras=1` est le plus petit budget LEGITIME et doit
    passer, en rendant la reponse connue. Une garde qui refuserait aussi 1 rendrait le budget
    minimal inatteignable."""
    _, res = _experience(monkeypatch, {s: (0.8, 0.4) for s in (11, 22, 33, 44, 55, 66)},
                         grad=GraduationConfig(max_eras=1))
    assert res["verdict"] == "TRANSFERE" and res["median_ratio"] == pytest.approx(2.0)
    assert res["per_seed"][0]["total_eras"] == 2               # 1 ere x 2 barreaux


def test_DEFAUT_un_barreau_a_ZERO_ere_ne_se_lit_pas_comme_une_competence_nulle():
    """SECONDE garde, INDEPENDANTE de celle du budget : `_competence_on_target` refuse un barreau
    qui declare `eras <= 0`, quelle que soit la facon dont le transcript a ete produit. C'est le
    zero de repli du runner (src/curriculum/runner.py:154) qu'on refuse de lire comme une mesure.
    Le cas NEGATIF apparie est dans les deux dernieres assertions."""
    zero = [{"world": "w_cible", "eras": 0, "final_competence": 0.0}]
    with pytest.raises(ValueError, match="AUCUNE ere"):
        CT._competence_on_target(zero, "w_cible")
    # NEGATIF 1 : une extinction MESUREE (des eres ont tourne) reste une mesure legale.
    assert CT._competence_on_target(
        [{"world": "w_cible", "eras": 3, "final_competence": 0.0}], "w_cible") == 0.0
    # NEGATIF 2 : un transcript qui ne DECLARE pas `eras` n'est pas refuse depuis une cle ABSENTE.
    assert CT._competence_on_target(
        [{"world": "w_cible", "final_competence": 0.7}], "w_cible") == 0.7


def test_DEFAUT_compute_transfer_verdict_refuse_un_compte_NEGATIF():
    """`n_indetermine` negatif FABRIQUAIT un verdict : le `n` publie ne decrivait plus la cohorte
    (8 ratios lus, n=4 publie) et la condition de majorite `2*n_fav > n` devenait trivialement
    vraie. Cas NEGATIF apparie : 0 et un positif restent acceptes."""
    with pytest.raises(ValueError, match="negatif"):
        CT.compute_transfer_verdict([1.5] * 8, n_indetermine=-4)
    assert CT.compute_transfer_verdict([1.5] * 8, n_indetermine=0)["verdict"] == "TRANSFERE"
    assert CT.compute_transfer_verdict([1.5] * 8, n_indetermine=1)["n"] == 9


def test_DEFAUT_une_echelle_VIDE_est_refusee(monkeypatch):
    """La garde `echelle VIDE` n'etait couverte par AUCUN test : la mutation qui la supprime ne
    faisait rougir personne (garde DECORATIVE, classe E1). Son regime est etroit mais reel --
    `ladder = list(ladder) if ladder else DEFAULT_LADDER` : un ITERATEUR vide est TRUTHY, donc il
    passe la branche `if ladder` et rend une echelle vide. Sans la garde, c'est un IndexError sur
    `ladder[-1]`, pas un refus nomme. Cas NEGATIF apparie : un iterateur NON vide est accepte."""
    def _interdit(*a, **kw):
        raise AssertionError("garde posee TROP BAS : le monde a ete touche avant le refus")

    monkeypatch.setattr(CT, "make_run_era_fn", _interdit)
    monkeypatch.setattr(CT, "_acquire_shared_db", _interdit)
    with pytest.raises(ValueError, match="echelle VIDE"):
        CT.run_transfer_experiment([11], ladder=iter([]), target=None,
                                   grad_cfg=GraduationConfig(max_eras=1), manage_logger=False,
                                   run_era_fn=lambda w, i, k: _cellule(0.5))
    res = CT.run_transfer_experiment([11], ladder=iter(["w_a"]), target=None,
                                     grad_cfg=GraduationConfig(max_eras=1), manage_logger=False,
                                     run_era_fn=lambda w, i, k: _cellule(0.5))
    assert res["config"]["ladder"] == ["w_a"] and res["config"]["target"] == "w_a"
