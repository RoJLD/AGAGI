"""Calibration du cliquet `check_bar_separation` (P2.15).

Un cliquet doit pouvoir ECHOUER, et se confronter a une reponse CONNUE avant qu'on le croie : les
cliquets livres dans ce depot ont rendu 5, 2 puis 4 faux positifs avant correction. Chaque cas ci-dessous
a donc une reponse connue AVANT la mesure, et il y a autant de cas `spares` que de cas `fires` — une
garde qui refuserait TOUT passerait les seconds seule.
"""
import os

from tools.check_bar_separation import _ROOT, _defects, _load_baseline, scan

_BAR = "bar = 1.0 / K + 0.15\n"
_VERDICT = "unlocked = (pm <= bar) and (bm > bar)\n"
_GUARD = ("assert_bar_separates_the_incapable(bar, 0.75, 'forme close du substrat plain, mesuree "
          "avec controle positif apparie')\n")


# --- cas FIRES (reponse connue OUI) -----------------------------------------------------------------

def test_the_ratchet_FIRES_on_a_chance_plus_margin_bar():
    """Le defaut P2.15 exactement : une barre batie sur le niveau de chance, jamais confrontee au
    plafond du bras qu'elle declare incapable."""
    assert _defects(_BAR + _VERDICT) == {"S"}


def test_the_ratchet_FIRES_on_a_named_chance_level():
    """Meme defaut ecrit autrement — `chance + 0.12` vit dans plusieurs sondes du depot. Un cliquet qui
    ne verrait qu'UNE orthographe annoncerait une couverture qu'il n'a pas."""
    assert _defects("chance = 1.0 / K\ncomp = z > chance + 0.12\n") == {"S"}


def test_the_ratchet_FIRES_on_a_literal_denominator():
    """`1/6 + 0.15` : la forme qu'on trouve dans les tests geles, ou K est deja substitue."""
    assert _defects("bar = 1 / 6 + 0.15\nok = m > bar\n") == {"S"}


def test_the_ratchet_FIRES_when_the_guard_is_IMPORTED_but_never_CALLED():
    """⚠️ Importer une garde n'est pas l'appeler — c'est la classe E10 dans sa definition meme, et c'est
    l'etat exact dans lequel `assert_bar_separates_the_incapable` a vecu du 2026-09-02 au 2026-09-07 :
    ecrite, testee, branchee NULLE PART. La detection porte donc sur l'APPEL (noeud ast.Call), jamais
    sur la presence du nom dans le fichier."""
    imported = "from tools.experiment_preflight import assert_bar_separates_the_incapable\n"
    assert _defects(imported + _BAR + _VERDICT) == {"S"}


def test_the_ratchet_DISTINGUISHES_a_guard_that_may_never_RUN():
    """⚠️ TROU REEL de ce cliquet, trouve par un refutateur independant le jour de sa livraison, et
    devenu un cas de calibration (regle d'auto-amelioration du depot).

    La version d'origine rendait « propre » des qu'un appel a la garde EXISTAIT dans le fichier. Or
    `retain_compose_diagnostic_probe` l'appelle sous `if ceil is not None:` avec `incapable_ceiling=None`
    PAR DEFAUT : la garde ne tourne JAMAIS au reglage par defaut. Ce n'est pas un defaut vivant la-bas
    (la sonde refuse AUSSI de rendre son verdict dans cette branche), mais une NOUVELLE sonde pourrait
    garder l'appel eteint et rendre quand meme -- le cliquet la benirait. D'ou le code `C`, distinct
    de `S` : « la garde existe, rien ne montre qu'elle TOURNE »."""
    conditionnel = "bar = 1.0 / K + 0.15\nif c is not None:\n    " + _GUARD.strip()
    assert _defects(conditionnel) == {"C"}, "un appel purement CONDITIONNEL ne vaut pas validation"
    assert _defects(_BAR + _GUARD) == set(), "un appel INCONDITIONNEL, lui, vaut validation"
    assert _defects(_BAR + _VERDICT) == {"S"}, "aucun appel du tout reste `S`"


def test_the_ratchet_FIRES_on_a_PARTIAL_validation():
    """⚠️ QUATRIEME defaut reel de ce cliquet, et je l'ai FABRIQUE moi-meme le 2026-09-08.

    En recablant `referential_community_probe` sur son bras FIXED, j'ai valide UNE de ses deux barres.
    Le cliquet, qui jugeait au FICHIER, l'a aussitot declaree PROPRE -- rendant INVISIBLE la seconde
    (`learned = within > chance + 0.05`), dans le geste meme qui corrigeait la premiere. Un correctif
    partiel ne doit pas effacer ce qui reste.

    La regle est ETROITE a dessein : on ne signale que `0 < appels < barres`. Exiger un appel PAR
    expression punirait les fichiers ou une meme garde en couvre plusieurs (boucle sur des conditions)
    et compterait comme barres des expressions qui n'en sont pas -- un `print`, une garde de
    denominateur. Mesure a l'appui : `compositional_language_probe` porte 5 expressions pour 2 verdicts
    reels."""
    deux_barres = "a = 1.0 / K + 0.15\nb = 1.0 / K + 0.05\n"
    assert _defects(deux_barres + _GUARD) == {"P"}, "une barre validee sur deux = PARTIEL"
    assert _defects(deux_barres) == {"S"}, "aucune validee = S, pas P (l'auteur n'a pas commence)"
    assert _defects(_BAR + _GUARD) == set(), "une seule barre, validee = PROPRE"


def test_the_FIRST_FIX_of_that_hole_was_ITSELF_WRONG():
    """⚠️ Et le correctif a d'abord ete FAUX, attrape par cette calibration meme. Il parcourait le corps
    du MODULE, ou une `FunctionDef` est un statement non conditionnel : tout appel, meme profondement
    enfoui dans un `if`, ressortait INCONDITIONNEL, et les deux sondes rendaient (True, True). La
    detection descend desormais en portant un drapeau. Le cas qui l'a revele est gele ici : un appel
    enfoui de DEUX niveaux dans une fonction reste CONDITIONNEL."""
    import ast

    from tools.check_bar_separation import _guard_calls
    profond = ("def f():\n"
               "    bar = 1.0 / K + 0.15\n"
               "    if a:\n"
               "        if b:\n"
               "            " + _GUARD.strip())
    assert _guard_calls(ast.parse(profond)) == (False, True), "enfoui dans deux `if` = CONDITIONNEL"
    plat = "def f():\n    bar = 1.0 / K + 0.15\n    " + _GUARD.strip()
    assert _guard_calls(ast.parse(plat)) == (True, False), "au corps de la fonction = INCONDITIONNEL"


# --- cas SPARES (reponse connue NON) ----------------------------------------------------------------

def test_the_ratchet_SPARES_a_bar_validated_by_the_guard():
    """POSITIF APPARIE. Sans lui, un cliquet qui crierait sur TOUTE barre passerait les cas `fires`."""
    assert _defects(_BAR + _GUARD + _VERDICT) == set()


def test_the_ratchet_SPARES_the_idiom_QUOTED_IN_PROSE():
    """⚠️ LE faux positif a eviter, et il n'est pas hypothetique : ce depot CITE `1/K + 0.15` en prose
    dans des dizaines de docstrings — y compris dans les fichiers qui DENONCENT la dette. Un regex les
    compterait tous comme dette et le cliquet deviendrait du bruit qu'on apprend a ignorer. D'ou l'AST :
    une chaine de caracteres n'est jamais un `BinOp`."""
    prose = ('"""La barre 1/K + 0.15 = 0.3167 est MAL PLACEE (voir P2.15)."""\n'
             "# meme remarque en commentaire : chance + 0.15\n"
             "x = mesure()\n")
    assert _defects(prose) is None


def test_the_ratchet_SPARES_a_chance_level_without_a_margin():
    """`floor = 1/K` NU est un PLANCHER, pas une barre de verdict : il ne pretend separer personne.
    Le defaut P2.15 est la MARGE arbitraire ajoutee au plancher, pas le plancher."""
    assert _defects("floor = 1.0 / K\nv = ablation_verdict(a, b, floor=floor, ceiling=1.0)\n") is None


def test_the_ratchet_SPARES_a_margin_that_is_not_a_proportion():
    """`1/K + 1.5` n'est pas une barre d'accuracy (une proportion ne depasse pas 1) : hors sujet.
    Restreindre a ]0,1[ evite de juger des expressions arithmetiques sans rapport."""
    assert _defects("scale = 1.0 / K + 1.5\n") is None


def test_the_ratchet_SPARES_a_progress_bar():
    """La collision de NOMS est un axe de faillibilite MESURE de ce depot (8 definitions invisibles sur
    le cliquet de calibration). `bar = '#' * n` s'appelle `bar` et n'est pas une barre de verdict :
    c'est la FORME de l'expression qui decide, jamais le nom de la variable."""
    assert _defects("bar = '#' * int(g * 400)\nprint(bar)\n") is None


def test_a_file_without_a_bar_is_OUT_OF_SCOPE_not_CLEAN():
    """⚠️ La distinction qui compte : `None` (hors perimetre) n'est PAS `set()` (examine, sans defaut).
    Les confondre ferait compter 222 fichiers sans rapport comme autant de succes."""
    assert _defects("x = 1\nprint('rien a voir')\n") is None
    assert _defects(_BAR + _VERDICT) is not None


def test_an_unparsable_file_is_OUT_OF_SCOPE_and_says_so():
    """Non-detection ASSUMEE : un fichier qui ne parse pas n'est pas juge propre, il est hors perimetre."""
    assert _defects("def f(:\n") is None


# --- semantique de comparaison a la baseline --------------------------------------------------------

def test_the_ratchet_SPARES_a_PARTIAL_fix():
    """Une egalite stricte a la baseline PUNIRAIT un correctif : un cliquet bloque la dette NOUVELLE,
    jamais la dette REDUITE. Verifie sur la logique de comparaison elle-meme."""
    base = {"tools/x.py": ["S"]}
    assert not (set([]) - set(base["tools/x.py"])), "perdre le defaut ne doit RIEN declencher"
    assert not (set(["S"]) - set(base["tools/x.py"])), "dette inchangee ne doit RIEN declencher"
    assert set(["S"]) - set([]) == {"S"}, "une dette ABSENTE de la baseline DOIT declencher"


def test_the_ratchet_CAN_FAIL_on_a_new_file():
    """CONTRE-EXEMPLE GELE — un cliquet qu'on n'a jamais vu refuser est indiscernable d'un cliquet
    absent. Un fichier en defaut ABSENT de la baseline doit produire un signalement."""
    base = _load_baseline()
    assert "tools/__nouvelle_sonde_fictive__.py" not in base
    d = _defects(_BAR + _VERDICT)
    nouveaux = set(d) - set(base.get("tools/__nouvelle_sonde_fictive__.py", []))
    assert nouveaux == {"S"}, "une sonde neuve en defaut doit bloquer"


# --- confrontation aux FICHIERS REELS ---------------------------------------------------------------

def test_the_perimeter_is_REAL():
    """Le perimetre doit rester reel : des sondes rendent VRAIMENT un verdict contre une barre de cette
    forme, et le hors-perimetre est RAPPORTE, pas avale. Si `examines` s'effondrait, un « 0 en dette »
    ne voudrait plus rien dire."""
    # ⚠️ TROISIEME fois que ce fichier punit un correctif, et le motif est desormais nomme :
    # UNE ASSERTION SUR UN COMPTE VIVANT PUNIT LE PROGRES. `examines >= 8` etait vrai a l'audit
    # fondateur ; corriger deux sondes les a fait SORTIR du perimetre (elles n'ont plus AUCUNE barre
    # `chance + constante`), donc le compte est tombe a 6 et le test a rougi sur une AMELIORATION.
    # Regle : geler le FAIT HISTORIQUE, asserter l'INVARIANT. L'invariant est que le cliquet voit
    # encore quelque chose de reel et rapporte son hors-perimetre.
    _AUDIT_FONDATEUR_TAILLE = 8          # 2026-09-07, gele : ne bouge plus jamais
    en_defaut, hors, examines = scan()
    assert examines >= 1, "le cliquet ne voit plus AUCUNE barre : detecteur casse ou perimetre vide"
    assert examines <= _AUDIT_FONDATEUR_TAILLE, (
        f"{examines} sondes en perimetre pour {_AUDIT_FONDATEUR_TAILLE} a l'audit fondateur : "
        "le perimetre ne peut que se REDUIRE par correction, jamais grandir sans nouvelle dette")
    assert len(hors) > examines, "le hors-perimetre doit etre RAPPORTE, pas avale"
    # ⚠️ Ce test assertait `en_defaut` NON VIDE. Un refutateur a montre que c'etait un test qui PUNIT
    # LE CORRECTIF : corriger les 6 sondes restantes -- le but meme de P2.15 -- l'aurait fait echouer.
    # Un cliquet doit bloquer la dette NOUVELLE, jamais la dette REDUITE, et son test non plus.
    # Ce qui doit rester vrai est le PERIMETRE, pas la dette.


def test_the_baseline_is_CONSISTENT():
    """La baseline ne gele JAMAIS une dette qui n'existe plus, ni un fichier disparu : une entree
    perimee serait une DECORATION, et un cliquet qui decore ment sur sa couverture."""
    base = _load_baseline()
    en_defaut, _hors, _ex = scan()
    assert set(base) <= set(en_defaut), f"la baseline gele une dette DISPARUE : {set(base) - set(en_defaut)}"
    for k in base:
        assert os.path.exists(os.path.join(_ROOT, k)), f"la baseline gele un fichier DISPARU : {k}"


def test_the_two_edge_carving_probes_are_IN_the_founding_audit():
    """Ancrage sur le REEL. Les deux sondes qui ont GRAVE `language->perception` et `memory->perception`
    posent leur barre de vitalite a `1/K + 0.15` sans l'avoir jamais confrontee au plafond de
    l'incapable — le meme motif que l'audit d'epinglage du substrat, sur les MEMES fichiers."""
    # ⚠️ Ce test assertait que ces deux sondes sont DANS la baseline courante. C'etait un test qui PUNIT
    # LE CORRECTIF : relever leur barre au-dessus du plafond de l'incapable -- l'action que P2.15 EXIGE
    # -- les sortait de la dette et faisait echouer le test cense la faire corriger. On gele donc le
    # FAIT HISTORIQUE (elles etaient dans l'audit fondateur du 2026-09-07) et on verifie qu'elles sont
    # dans le PERIMETRE, ce qui reste vrai apres correction.
    # 2026-09-08 : les DEUX sondes graveuses sont CORRIGEES (barre derivee d'un plafond mesure), donc
    # sorties du perimetre. Le fait HISTORIQUE reste gele ; l'etat courant est verifie par l'invariant.
    _AUDIT_FONDATEUR = ("tools/memory_perception_demand_probe.py",
                        "tools/perception_coordination_demand_probe.py")
    base = _load_baseline()
    for sonde in _AUDIT_FONDATEUR:
        assert os.path.exists(os.path.join(_ROOT, sonde)), sonde
        _d = _defects(open(os.path.join(_ROOT, sonde), encoding="utf-8").read())
        # ⚠️ Trois etats sont LEGITIMES apres correction, et le troisieme est le MEILLEUR :
        #   `{"S"}`/`{"C"}` = encore en dette (doit alors etre gelee) ; `set()` = barre validee par la
        #   garde ; `None` = HORS PERIMETRE, c.-a-d. plus AUCUNE barre `chance + constante` -- la sonde
        #   derive desormais sa barre d'une MESURE. C'est ce qui est arrive a ces deux sondes le
        #   2026-09-08 : leur barre vient du plafond d'un agent NON ENTRAINE, mesure dans le dispositif.
        # Ce qui reste interdit : etre en dette SANS etre gelee.
        assert _d in (None, set()) or sonde in base, (
            f"{sonde} : en dette ({_d}) sans etre gelee dans la baseline")


def test_the_founding_debt_is_ALMOST_CLOSED_and_what_REMAINS_is_STRUCTURAL():
    """CLOTURE MESUREE de P2.15 cote barres : 8 sondes a l'audit fondateur (2026-09-07) -> 1 le
    2026-09-08. Les sept fermetures se sont faites par une MESURE de l'incapable, jamais par un gel :
      * plafond d'un agent NON ENTRAINE, au regime publie (memory_perception, perception_coordination) ;
      * une barre PAR CONDITION, les incapables differant (retain_compose) ;
      * le bras BROUILLE deja present dans le run (referential_game) ;
      * le bras FIXED = code prive (referential_community) ;
      * un bras a MESSAGE BROUILLE ajoute en EVAL SEULE (compositional_language, _curriculum).

    Ce qui RESTE est structurel et doit le rester : `bilinear_composition_probe` porte `C` parce
    qu'AUCUNE borne SUPERIEURE PROUVEE n'existe pour sa forme -- sa garde ne peut donc pas s'executer,
    et la sonde REFUSE de certifier (`unlocked=None`). Un `C` gele y est la description exacte de
    l'etat des connaissances, pas une dette qu'on remettrait a plus tard."""
    base = _load_baseline()
    assert set(base) == {"tools/bilinear_composition_probe.py"}, sorted(base)
    assert base["tools/bilinear_composition_probe.py"] == ["C"], base
    en_defaut, _hors, _ex = scan()
    assert set(en_defaut) <= set(base), f"dette NOUVELLE : {set(en_defaut) - set(base)}"

