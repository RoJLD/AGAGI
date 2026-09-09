"""Calibration du cliquet des DEFAUTS FABRIQUES (porte 14, 2026-09-09, P2.49).

LA FORME TRAQUEE : `float(np.median(ages)) if ages else 0.0`. Une cohorte VIDE n'est pas une cohorte
qui a survecu 0 tick -- le premier cas est une ABSENCE DE MESURE, le second une MESURE, et cette
ecriture les rend INDISCERNABLES. Dans un depot dont la plupart des resultats sont NEGATIFS, un
negatif fabrique ressemble a tous les autres : c'est la forme (a) des trois documentees dans
CLAUDE.md, celle qui a produit `PAS DE RUNG`, `AUTEL MORT`, `N_EMERGE_PAS`.

⚠️ Le pire cas MESURE dans le depot est un defaut a **1.0 sur un RATIO** (`tools/g_fidelity_probe.py`)
ou l'absence de donnee prend EXACTEMENT la valeur du resultat nul : « l'ablation n'a rien fait ».
L'absence n'y devient pas seulement un chiffre, elle devient LA conclusion.

Autant de cas `spares` que de cas `fires`, et les deux sens sont geles : une garde qui refuserait
TOUT passerait les premiers sans rien mesurer.
"""
import io
import json
import os

from tools.check_fabricated_defaults import _BASELINE, _load_baseline, scan, sites_dans

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- cas FIRES (reponse connue : OUI, c'est un defaut fabrique) --------------------------------------

def test_it_FIRES_on_a_zero_default_over_an_empty_cohort():
    """Le cas nominal, et le plus frequent : 88 des 121 sites legataires sont a `0.0`."""
    assert sites_dans("x = float(np.median(ages)) if ages else 0.0", "f.py")


def test_it_FIRES_on_a_ONE_default_over_a_RATIO_which_is_the_WORST_case():
    """⚠️ LE PIRE CAS, et il est reel (`tools/g_fidelity_probe.py`). Un ratio dont le defaut vaut 1.0
    fait prendre a l'absence de donnee EXACTEMENT la valeur du resultat nul -- « l'ablation n'a rien
    fait ». Ce n'est plus un chiffre fabrique, c'est une CONCLUSION fabriquee."""
    assert sites_dans("r = float(np.median(ratios)) if ratios else 1.0", "f.py")


def test_it_FIRES_across_LINES_which_is_why_the_detection_is_by_AST():
    """⚠️ RAISON D'ETRE DE L'AST. Un `if ... else` peut s'ecrire sur plusieurs lignes ; une regex y
    verrait moins que ce que sa docstring promet -- l'angle mort qui a coute HUIT elargissements au
    cliquet de calibration. Mesure : la regex trouvait 98 sites, l'AST en trouve 121."""
    src = "x = (float(np.mean(vals))\n     if vals\n     else 0.0)"
    assert sites_dans(src, "f.py")


def test_it_FIRES_through_a_float_wrapper_and_on_statistics_too():
    """`float(...)`, `int(...)`, `round(...)` autour de l'agregation ne doivent pas la cacher ; et
    `statistics` compte autant que `numpy` -- les deux sont utilises dans le depot."""
    assert sites_dans("x = round(statistics.mean(v), 2) if v else 0.0", "f.py")
    assert sites_dans("x = statistics.median(v) if v else 0", "f.py")


# --- cas SPARES (reponse connue : NON) ---------------------------------------------------------------

def test_it_SPARES_None_and_nan_because_they_SAY_they_do_not_know():
    """⚠️ CE N'EST PAS UNE TOLERANCE, C'EST LA BONNE REPONSE. `None` et `nan` DISENT « je ne sais
    pas » -- ils ne fabriquent rien. Le depot a deja corrige un site dans ce sens
    (`tools/s2_openloop_probe.py`, dont le commentaire explique la faute) : ce cliquet generalise ce
    correctif au lieu de le laisser isole. 49 des 147 sites sont deja honnetes."""
    assert not sites_dans('x = float(np.median(a)) if a else float("nan")', "f.py")
    assert not sites_dans("x = statistics.median(v) if v else None", "f.py")
    assert not sites_dans("x = float(np.mean(v)) if v else np.nan", "f.py")


def test_it_SPARES_sum_because_the_empty_sum_is_ARITHMETICALLY_TRUE():
    """`sum([])` vaut 0 et c'est JUSTE : la somme d'un ensemble vide EST zero. `median([])` n'a pas de
    valeur. Confondre les deux ferait crier le cliquet sur du code correct, et un cliquet qui crie a
    tort finit desarme."""
    assert not sites_dans("x = sum(v) if v else 0.0", "f.py")
    assert not sites_dans("x = len(v) if v else 0", "f.py")


def test_it_SPARES_a_default_that_is_NOT_a_constant():
    """Un defaut calcule (variable, appel, autre agregation) n'est pas une constante fabriquee : il
    peut porter du sens. Le cliquet ne vise que la CONSTANTE NUE."""
    assert not sites_dans("x = float(np.mean(v)) if v else plancher", "f.py")
    assert not sites_dans("x = float(np.mean(v)) if v else compute_floor()", "f.py")


def test_it_SPARES_a_boolean_which_is_not_a_measurement():
    """`True`/`False` sont des `bool`, sous-classe d'`int` en Python : sans exclusion explicite ils
    passeraient pour des constantes numeriques. Ce cas gele l'exclusion."""
    assert not sites_dans("x = float(np.mean(v)) if v else False", "f.py")


# --- l'ARBRE REEL, et la garde de la garde ------------------------------------------------------------

def test_the_REAL_tree_has_NO_new_site_and_a_NON_EMPTY_baseline():
    """Ancrage. La baseline doit etre gelee et NON VIDE (une baseline a zero serait une garde
    desarmee sur un depot qui compte 121 sites), et l'arbre courant ne doit contenir aucun NOUVEAU."""
    base = _load_baseline()
    assert len(base) >= 100, ("la dette legataire mesuree est de 121 sites", len(base))
    nouveaux = {k for k in scan() if k not in base}
    assert not nouveaux, f"nouveaux defauts fabriques : {sorted(nouveaux)[:5]}"


def test_correcting_a_site_does_NOT_break_the_ratchet():
    """⚠️ COMPARAISON PAR DIFFERENCE D'ENSEMBLES, jamais par egalite. Trois de mes propres tests
    ont deja PUNI un correctif dans ce depot en exigeant qu'une dette reste non vide. Ici : une
    baseline plus LARGE que le reel doit passer -- corriger un site est un progres, pas un echec."""
    base = dict(_load_baseline())
    base["fichier/inexistant.py:1"] = "site corrige depuis le gel"
    reel = scan()
    nouveaux = {k for k in reel if k not in base}
    assert not nouveaux, "une baseline elargie ne doit JAMAIS produire de nouveau"


def test_the_gate_is_WIRED_into_the_hook_and_its_BASELINE_triggers_it():
    """GARDE DE LA GARDE. Une porte non branchee est une porte documentee. ⚠️ Et sa baseline doit
    faire partie du DECLENCHEUR : sinon l'elargir et la committer SEULE ne verifierait rien -- faux
    vert mesure sur ce depot le 2026-09-01 (classe E4 occ. 5).

    Controle POSITIF sur une porte connue comme branchee : sans lui, un motif faux rendrait ce test
    vert par absence de correspondance."""
    hook = io.open(os.path.join(_ROOT, "tools", "hooks", "pre-commit"), encoding="utf-8").read()
    assert "check_bar_separation" in hook, "CONTROLE POSITIF en echec : le motif ne sait pas lire"
    assert "check_fabricated_defaults" in hook, "la porte 14 n'est plus branchee"
    decl = [l for l in hook.splitlines() if "staged_fd=" in l]
    assert len(decl) == 1, decl
    assert "fabricated_defaults_baseline" in decl[0], (
        "la baseline doit declencher la garde, sinon la geler seule ne verifie rien")


def test_the_baseline_file_is_readable_and_shaped_as_expected():
    """Un cliquet dont la baseline est illisible ou vide se tairait sur TOUT. On le verifie ici
    plutot que de le decouvrir a la premiere regression."""
    assert os.path.exists(_BASELINE)
    with io.open(_BASELINE, encoding="utf-8") as fh:
        d = json.load(fh)
    assert isinstance(d.get("legataires"), dict) and d["legataires"], d.keys()
    assert all(":" in k for k in d["legataires"]), "les cles sont `chemin:ligne`"
