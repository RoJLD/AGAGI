"""9e ELARGISSEMENT du cliquet de calibration (2026-09-09) : `src` entier + les .py de la RACINE.

Les huit elargissements precedents ont chacun revele de la dette REELLE. Celui-ci ne fait pas
exception, et sa dette vise le CLIQUET LUI-MEME.

⚠️ **LE DEFAUT QUI DONNE SON SENS A CE FICHIER.** `tools/hcm_analyzer.py::run_hcm_analysis` etait
DECLARE CALIBRE -- deux cas, `empty-cohort:raises` et `guard-before-world` -- et **ne pouvait pas
s'executer** : `load_hall_of_fame()` rend `(version, entries)`, donc `[g for g in hof if g[1]...]`
levait `TypeError: 'int' object is not subscriptable` a la ligne 29, a CHAQUE appel. Ses deux cas
n'exercent que la garde d'arguments posee en tete, qui leve AVANT cette ligne. **La calibration
passait sans jamais entrer dans le corps.**

Exposition MESUREE, et c'est le chiffre a retenir : **92 des 248 declarations (37 %) sont calibrees
uniquement par des cas de la famille garde** (`*:raises`, `guard-before-world`). Cela ne dit pas
qu'elles sont cassees -- cela dit qu'aucun de leurs cas n'atteint leur corps, donc que leur
certification ne porte que sur leur porte d'entree. La 7e passe (famille `run_*`, 72 fonctions) a
ete fermee par des gardes d'en-tete ; c'est la limite de cette technique, et elle se voit ici.

D'ou la forme des cas ci-dessous : chacun qui compte est marque CORPS-ATTEINT, et ceux-la appellent
la fonction avec des arguments VALIDES pour verifier qu'elle depasse sa garde. Aucun ne construit de
monde (les gardes et les contrats sont atteints avant).

`src/paths.py::assert_roots_exist` n'est pas re-teste ici : ses trois cas existent deja et sont
collectibles dans `tests/sandbox/test_paths.py`
(`test_une_racine_ABSENTE_leve_en_NOMMANT_sa_variable`,
`test_la_verification_est_CIBLEE_et_ne_crie_pas_sur_ce_qu_on_ne_lui_demande_pas`). Les dupliquer
donnerait deux verites concurrentes sur la meme garde.
"""
import time

import pytest


# --- LE CONTRE-EXEMPLE GELE : une garde d'en-tete ne certifie pas le corps -------------------------

def test_the_HEAD_guard_alone_CANNOT_certify_the_body():
    """⚠️ CONTRE-EXEMPLE GELE, rejoue tel quel. On reconstitue la situation exacte du 2026-09-09 :
    l'ancien code de `tools/hcm_analyzer.py` traitait le retour de `load_hall_of_fame()` comme une
    LISTE. Les deux cas declares (`empty-cohort:raises`, `guard-before-world`) passaient, parce
    qu'ils levent sur la garde d'arguments AVANT d'atteindre cette ligne.

    Le test montre les DEUX faits en meme temps : l'ancienne forme leve `TypeError` sur un retour
    conforme au contrat, et la garde d'en-tete leve plus tot -- donc les masque."""
    hof_conforme = (2, [object()])          # (version:int, entries:list) -- le contrat REEL
    with pytest.raises(TypeError, match="not subscriptable"):
        _ = [g for g in hof_conforme if g[1] is not None]     # l'ANCIENNE forme, rejouee
    # ... et la garde d'arguments, elle, leve AVANT : c'est ce qui rendait le defaut invisible.
    from tools.hcm_analyzer import run_hcm_analysis
    with pytest.raises(ValueError, match="degenere"):
        run_hcm_analysis(num_ticks=0, n_clusters=2)


def test_the_measured_EXPOSURE_of_head_guard_only_calibration_is_PUBLISHED():
    """La lecon ne vaut que chiffree, et le chiffre doit se RECOMPUTER -- sinon c'est une opinion.

    On recompte les declarations dont AUCUN cas n'atteint le corps. Le chiffre ne se fige pas, il se
    RECOMPUTE : 92 sur 248 au 2026-09-09, puis resorbe par P2.56 (injection d'orchestrateurs) jusqu'a 0 sur
    323 -- P2.49 CLOSE. Il vaut donc 0. La porte 18 (tools/check_calibration_reach.py, baseline VIDE) refuse
    toute NOUVELLE garde-seule MUETTE ; ce test tient le reste -- une garde-seule qu'un test importe ET appelle
    passe la porte 18, et fait rougir ce test. P2.113 (b), 2026-09-26 : ce test
    exigeait encore « au moins une », il etait rouge partout ou il tournait, et la CI ne le voyait pas --
    il importait la suite de calibration, dont le saut de MODULE sans torch le faisait sauter (P2.121
    famille 1). Il garde son nom : P2.49 et P2.113 (b) le citent."""
    import re

    from tests.sandbox.test_instrument_calibration import CALIBRATED
    garde = re.compile(r"(:raises$|^guard-before-world$|^regime-degenere|^plan-vide|^empty-cohort|"
                       r"^entree-vide|^cohorte-vide|^selection-vide|^argument-degenere|^echelle-vide)")
    seulement = [n for n, cas in CALIBRATED.items()
                 if isinstance(cas, list) and cas and all(garde.search(c) for c in cas)]
    assert len(seulement) == 0, (
        f"{len(seulement)} declaration(s) garde-seule sont REAPPARUES ({sorted(seulement)[:5]}) : l'exposition "
        "publiee par P2.49 (0/323) a change. La porte 18 (tools/check_calibration_reach.py) ne refuse que les "
        "MUETTES : une garde-seule qu'un test importe ET appelle la passe. Calibrer son corps, ou mettre a jour "
        "le chiffre publie AVANT de toucher ce test")
    assert len(seulement) < len(CALIBRATED), (
        "toutes les declarations seraient garde-seule : aucun corps d'instrument ne serait teste")


# --- src/graph_rag/hcm_analyzer.py : le DOUBLON de juin, hors perimetre jusqu'ici -----------------

def test_the_graph_rag_analyzer_REFUSES_a_degenerate_argument_before_any_world():
    """Garde en TETE : le refus doit etre instantane. Une garde posee apres `extract_h_history`
    leverait aussi -- apres 200 ticks de simulation."""
    from src.graph_rag.hcm_analyzer import run_hcm_analysis
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        run_hcm_analysis(n_clusters=0)
    assert time.time() - t0 < 0.5, "la garde n'est pas en tete : un monde a ete construit avant le refus"


def test_the_graph_rag_analyzer_RAISES_on_an_empty_HoF_instead_of_returning_None(monkeypatch):
    """CORPS-ATTEINT. Avant correction, un HoF vide faisait `print` puis `return None` : une
    affirmation NEGATIVE de fond (« Hall of Fame vide. Lancez d'abord la simulation. ») fabriquee a
    partir d'une absence, et un `None` que l'aval ne distingue pas d'un resultat.

    ⚠️ Et la garde qui etait censee l'attraper ne POUVAIT PAS lever : `if not hof` sur
    `(version, entries)` teste un 2-uplet, toujours vrai. Un controle incapable d'echouer (E1)."""
    import src.graph_rag.hcm_analyzer as mod
    monkeypatch.setattr(mod, "load_hall_of_fame", lambda: (1, []))
    with pytest.raises(ValueError, match="VIDE"):
        mod.run_hcm_analysis(n_clusters=2)


def test_the_INERT_guard_is_the_frozen_counter_example():
    """⚠️ CONTRE-EXEMPLE GELE de la garde inerte. `if not hof` ne peut PAS lever sur un 2-uplet, quel
    que soit le contenu de `entries` -- y compris VIDE. C'est ce qui distingue « la garde a rate » de
    « la garde ne pouvait pas se declencher », et seule la seconde est la classe E1."""
    assert bool((1, [])) is True, "un 2-uplet a entries VIDE est TOUJOURS vrai : la garde etait inerte"
    assert not (1, [])[1], "alors que le contenu qu'elle devait garder, lui, est bien vide"


# --- tools/hcm_analyzer.py : l'instrument DECLARE CALIBRE qui ne pouvait pas tourner ---------------

def test_the_tools_analyzer_now_REACHES_its_body_on_valid_arguments():
    """⚠️ LE CAS QUI MANQUAIT, et le seul qui aurait attrape le defaut. On appelle avec des arguments
    VALIDES -- la garde d'en-tete ne peut donc plus masquer le corps. Le contrat du HoF doit etre
    respecte : plus aucun `TypeError`.

    Le HoF reel du depot ne contient aucun genome a 32 entrees (format « V13 » disparu), donc la
    reponse CONNUE de ce cas est le refus explicite -- qui CHIFFRE combien d'entrees ont ete lues,
    au lieu d'annoncer un vide."""
    from tools.hcm_analyzer import run_hcm_analysis
    with pytest.raises(ValueError) as exc:
        run_hcm_analysis(num_ticks=5, n_clusters=2)
    msg = str(exc.value)
    assert "aucun genome a 32 entrees" in msg
    assert "entree(s) chargee(s)" in msg, "le refus doit CHIFFRER ce qui a ete lu, sinon il ressemble a un vide"


def test_the_tools_analyzer_still_REFUSES_degenerate_arguments():
    """Non-regression de la garde existante : corriger le corps ne doit pas desarmer la porte."""
    from tools.hcm_analyzer import run_hcm_analysis
    for kw in (dict(num_ticks=0, n_clusters=2), dict(num_ticks=5, n_clusters=0)):
        with pytest.raises(ValueError, match="degenere"):
            run_hcm_analysis(**kw)


# --- RACINE du depot : deux instruments jamais balayes ---------------------------------------------

def test_the_root_curriculum_REFUSES_a_degenerate_regime_before_any_world():
    """`main_curriculum.py` est a la RACINE : `_SCAN_DIRS` ne contenait que des DOSSIERS, donc aucun
    fichier racine n'a jamais ete balaye. Un instrument depose la n'aurait jamais declenche le
    cliquet, quel que soit son contenu -- meme famille que le 8e angle mort (`os.listdir` plat)."""
    from main_curriculum import run_curriculum
    t0 = time.time()
    for kw in (dict(num_agents=0), dict(max_ticks=0)):
        with pytest.raises(ValueError, match="degenere"):
            run_curriculum(**kw)
    assert time.time() - t0 < 1.0, "la garde n'est pas en tete du curriculum"


def test_the_root_curriculum_REFUSES_an_EMPTY_ladder():
    """Une echelle sans barreau ne peut produire aucun transcript. Sans cette garde, le curriculum
    rendrait une liste VIDE -- que l'aval lirait comme « le curriculum a echoue partout », alors que
    rien n'a ete tente. Deuxieme forme du biais negatif du depot."""
    from main_curriculum import run_curriculum
    with pytest.raises(ValueError, match="VIDE"):
        run_curriculum(ladder=[])


def test_the_multiverse_era_REFUSES_a_degenerate_regime():
    """`multiverse_runner.py::run_world_era` construit un monde et rend des stats d'ere. Meme famille,
    meme garde. C'est dans ce fichier que l'`except Exception` avalait la `TypeError` du contrat du
    HoF en imprimant « Erreur lors du chargement de KuzuDB » -- un diagnostic qui envoie chercher la
    cause a l'oppose."""
    from multiverse_runner import run_world_era
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        run_world_era((0, [], 400))
    with pytest.raises(ValueError, match="degenere"):
        run_world_era((0, [object()], 0))
    assert time.time() - t0 < 1.0, "la garde n'est pas en tete"


def test_the_multiverse_HoF_loading_no_longer_MISATTRIBUTES_its_failure(monkeypatch):
    """⚠️ CONTRE-EXEMPLE GELE du diagnostic FAUX. Avant correction, la `TypeError` du contrat etait
    avalee par `except Exception` et rapportee comme « Erreur lors du chargement de KuzuDB », puis la
    soupe primordiale partait SANS ancetre -- silencieusement, en accusant la base de donnees.
    Ici : sur un HoF conforme, aucun ancetre n'est perdu par erreur de contrat."""
    import multiverse_runner as mod

    class _G:                                   # genome factice : seul `num_inputs` est lu par le filtre
        num_inputs = 35

    class _Snap:                                # AgentSnapshot factice : acces par ATTRIBUT, pas par index
        def __init__(self):
            self.genome = _G()

    ancetres = [_Snap(), _Snap()]

    class _Agent:                               # l'agent est bouchonne : ce test porte sur le CONTRAT du
        def __init__(self, **kw):               # HoF, pas sur la construction d'un connectome
            self.genome = None

        def from_genome(self, g):
            self.genome = g

        def mutate(self):
            pass

    monkeypatch.setattr(mod, "load_hall_of_fame", lambda: (2, ancetres))
    monkeypatch.setattr(mod, "MambaAgent", _Agent)
    genomes = mod.init_primordial_genomes(num_agents=2)
    assert len(genomes) == 2, "les ancetres conformes doivent etre RETENUS, pas perdus dans un except"
    assert all(g is ancetres[0].genome or g is ancetres[1].genome for g in genomes), (
        "les genomes rendus doivent venir du HoF -- si le contrat cassait, on retomberait sur la "
        "branche `else` qui engendre une soupe ALEATOIRE, silencieusement")


# --- PERIMETRE : la garde de la garde --------------------------------------------------------------

def test_the_widened_perimeter_actually_SEES_the_new_files():
    """GARDE DE LA GARDE. Le cliquet doit VOIR les fichiers qu'on vient de lui donner : sans ce test,
    un futur remaniement de `_SCAN_DIRS` rouvrirait le trou en silence, et le compteur resterait vert
    puisqu'il ne compte que ce qu'il voit."""
    from tools.check_instrument_calibration import _iter_sources
    vus = {p for p, _ in _iter_sources()}
    for attendu in ("src/graph_rag/hcm_analyzer.py", "src/paths.py",
                    "src/metaprog/secure_sandbox.py", "main_curriculum.py", "multiverse_runner.py"):
        assert attendu in vus, f"{attendu} est retombe HORS du perimetre du cliquet"
    assert not any(p.startswith(("docs/", "frontend/", "tests/")) for p in vus), (
        "le balayage de la racine ne doit pas descendre dans les dossiers non-code")
