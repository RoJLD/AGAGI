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

from tools.check_fabricated_defaults import (_BASELINE, _load_baseline, scan, sites_a_corriger,
                                             sites_dans)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- cas FIRES (reponse connue : OUI, c'est un defaut fabrique) --------------------------------------

def test_it_FIRES_on_a_zero_default_over_an_empty_cohort():
    """Le cas nominal, et de loin le plus frequent parmi les sites legataires."""
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
    desarmee sur un depot qui en compte plus de cent), et l'arbre courant ne doit contenir aucun
    NOUVEAU. Le seuil est un PLANCHER et non le compte exact : figer 115 ferait ECHOUER ce test a
    la premiere correction, c'est-a-dire punir le progres."""
    base = _load_baseline()
    assert len(base) >= 100, ("la dette legataire mesuree etait de 121, ramenee a 115", len(base))
    # ⚠️ `sites_a_corriger` et non `scan` : la SOURCE UNIQUE, qui retire les declares non-mesure.
    # Mes deux premieres versions appelaient `scan` et voyaient donc le site DECLARE comme NOUVEAU --
    # un filtre duplique est un filtre qui divergera.
    nouveaux = {k for k in sites_a_corriger() if k not in base}
    assert not nouveaux, f"nouveaux defauts fabriques : {sorted(nouveaux)[:5]}"


def test_correcting_a_site_does_NOT_break_the_ratchet():
    """⚠️ COMPARAISON PAR DIFFERENCE D'ENSEMBLES, jamais par egalite. Trois de mes propres tests
    ont deja PUNI un correctif dans ce depot en exigeant qu'une dette reste non vide. Ici : une
    baseline plus LARGE que le reel doit passer -- corriger un site est un progres, pas un echec."""
    base = dict(_load_baseline())
    base["fichier/inexistant.py:1"] = "site corrige depuis le gel"
    reel = sites_a_corriger()
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
    assert all("::" in k and "#" in k for k in d["legataires"]), (
        "les cles sont `chemin::fonction#rang` -- STABLES sous decalage de ligne")


# --- LA CLE DOIT SURVIVRE AUX DECALAGES DE LIGNE (defaut mesure sur le cliquet LUI-MEME) ------------

def test_the_KEY_survives_an_insertion_ABOVE_the_site():
    """⚠️ DEFAUT MESURE SUR CE CLIQUET, LE JOUR DE SA LIVRAISON. Keye par NUMERO DE LIGNE, il a
    signale TROIS faux NOUVEAUX apres qu'on eut corrige six sites dans le meme fichier : les
    legataires situes plus bas s'etaient simplement DECALES.

    Un cliquet qui crie sur une edition sans rapport finit desarme -- c'est ecrit dans ce fichier meme
    (`test_it_SPARES_sum_...`), et il a fallu qu'il se le fasse a lui-meme pour que ce soit corrige.
    La cle est desormais `chemin::fonction#rang`."""
    src = "def f(v):\n    return float(np.mean(v)) if v else 0.0\n"
    avant = set(sites_dans(src, "f.py"))
    apres = set(sites_dans("# une ligne ajoutee\n# et une autre\n" + src, "f.py"))
    assert avant == apres == {"f.py::f#0"}, (avant, apres)


def test_the_KEY_distinguishes_TWO_sites_in_the_SAME_function():
    """NO-OP APPARIE de la stabilite : une cle trop grossiere confondrait deux sites de la meme
    fonction, et corriger l'un ferait croire que l'autre a disparu. Le rang les separe."""
    src = ("def f(a, b):\n"
           "    x = float(np.mean(a)) if a else 0.0\n"
           "    y = float(np.median(b)) if b else 1.0\n"
           "    return x, y\n")
    assert set(sites_dans(src, "f.py")) == {"f.py::f#0", "f.py::f#1"}


def test_the_KEY_names_the_ENCLOSING_function_not_just_the_file():
    """Deux fonctions du meme fichier ne doivent pas se confondre : la cle porte le nom de la
    fonction englobante, ce qui la rend aussi plus LISIBLE qu'un numero dans un rapport."""
    src = ("def alpha(v):\n    return float(np.mean(v)) if v else 0.0\n\n"
           "def beta(v):\n    return float(np.mean(v)) if v else 0.0\n")
    assert set(sites_dans(src, "f.py")) == {"f.py::alpha#0", "f.py::beta#0"}


# --- DECLARATIONS NON-MESURE (2026-09-09) : trouve en UTILISANT le cliquet --------------------------
#
# Toutes les agregations a defaut constant ne fabriquent pas une mesure. `src/swarm/consensus.py`
# remplit les NaN d'un vecteur de logits AVANT un softmax : quand TOUT est NaN, remplir par 0.0 rend
# le softmax UNIFORME, c'est-a-dire aucune preference -- la reponse correcte d'un vote sans
# information. Aucune grandeur du monde n'y est affirmee.
#
# Le cliquet ne sait pas distinguer « agregation qui MESURE » de « agregation qui REMPLIT », et un
# cliquet a faux positifs finit desarme (c'est ecrit plus haut dans ce fichier). La doctrine du depot
# tranche : faire DECLARER l'auteur plutot que deviner -- comme `NOT_AN_INSTRUMENT`.

def test_a_DECLARED_non_measure_leaves_the_debt_but_is_REPORTED():
    """Un site declare sort du COMPTE de dette -- sinon le chiffre publie serait faux -- mais il est
    RAPPORTE. Une exemption avalee en silence ferait croire a une couverture qu'on n'a pas : c'est le
    faux vert « 100 % quand on en fait 35 » que ce depot a deja mesure sur lui-meme."""
    from tools.check_fabricated_defaults import NOT_A_MEASURE, scan
    assert NOT_A_MEASURE, "le mecanisme doit etre UTILISE, pas seulement disponible"
    reel = scan()
    for cle in NOT_A_MEASURE:
        assert cle in reel, (
            f"{cle} est declare non-mesure mais n'existe plus : une declaration MORTE donne "
            "l'illusion d'une exemption utile", sorted(reel)[:3])


def test_a_DECLARATION_without_a_written_MOTIVE_is_REFUSED():
    """⚠️ UNE EXEMPTION SANS RAISON EST UNE EXEMPTION QU'ON NE PEUT PAS RELIRE. Le cliquet exige un
    motif d'au moins 60 caracteres et ECHOUE sinon -- il ne se contente pas de l'ignorer, ce qui
    laisserait l'auteur croire qu'il a declare ce qu'il n'a pas declare."""
    import sys

    import tools.check_fabricated_defaults as m
    ancien = dict(m.NOT_A_MEASURE)
    argv = list(sys.argv)
    try:
        m.NOT_A_MEASURE["src/swarm/consensus.py::_safe_softmax#0"] = "trop court"
        sys.argv = ["check_fabricated_defaults.py"]
        assert m.main([]) == 1, "un motif indigent doit faire ECHOUER le cliquet"
    finally:
        m.NOT_A_MEASURE.clear()
        m.NOT_A_MEASURE.update(ancien)
        sys.argv = argv


def test_an_UNDECLARED_site_still_FIRES():
    """NO-OP APPARIE du mecanisme : declarer un site ne doit pas desarmer le cliquet pour les autres.
    Sans ce cas, une exemption trop large passerait inapercue."""
    from tools.check_fabricated_defaults import NOT_A_MEASURE, sites_dans
    trouve = sites_dans("def f(v):\n    return float(np.mean(v)) if v else 0.0\n", "neuf.py")
    assert trouve and not any(k in NOT_A_MEASURE for k in trouve)
