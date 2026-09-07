"""Calibration de la clause `closes_when:` du cliquet de fraicheur du backlog (P2.29).

Le cliquet ne voyait que du SYNTAXIQUE. Six entrees ont pu annoncer l'INVERSE de l'etat mesure pendant
qu'il rendait « OK ». La clause rend la peremption SEMANTIQUE decidable — mais seulement si l'auteur
DECLARE sa condition de fermeture : deviner depuis le texte (dates, mot « OUVERTE ») est deja declare
non automatisable (E10 occ. 4).

Autant de cas `spares` que de cas `fires`, et les DEUX sens de violation sont geles : une garde qui
refuse tout passerait les seconds seule.
"""
import os

from tools.check_backlog_freshness import _ROOT, scan, scan_clauses

_OUVERTE = "**P9.1 — ⚠️ OUVERTE (2026-01-01) — quelque chose reste a faire.**\n"
_CLOSE = "**P9.1 — ✅ CLOS (2026-01-01) — c'est fait.**\n"
_VRAI = "<!-- closes_when:path_present=tools/check_backlog_freshness.py -->\n"
_FAUX = "<!-- closes_when:path_present=tools/il_nexiste_pas_ce_fichier.py -->\n"


# --- cas FIRES (reponse connue OUI) -----------------------------------------------------------------

def test_the_clause_FIRES_when_a_closed_condition_is_met_but_the_entry_says_OPEN():
    """Premier sens : la fermeture est ACQUISE et personne ne l'a enregistree. C'est le cas mesure —
    six entrees du backlog annoncaient « a faire » sur du travail deja livre, et elles ont ete trouvees
    en cherchant quoi faire, c'est-a-dire au pire moment possible."""
    viol, _sans = scan_clauses(_OUVERTE + _VRAI)
    assert any(k.startswith("clause-close:P9.1") for k in viol), viol


def test_the_clause_FIRES_when_a_CLOSED_entry_LOST_its_condition():
    """⚠️ LE SENS QUI COMPTE LE PLUS, et qu'aucune relecture ne voit : l'entree s'annonce CLOSE et sa
    condition de fermeture n'est PLUS satisfaite — la fermeture a REGRESSE en silence. C'est ainsi
    qu'une porte de hook peut disparaitre sans que le backlog cesse d'affirmer qu'elle est branchee."""
    viol, _sans = scan_clauses(_CLOSE + _FAUX)
    assert any(k.startswith("clause-rouverte:P9.1") for k in viol), viol


def test_the_clause_REFUSES_an_unknown_predicate_LOUDLY():
    """Vocabulaire FERME. Un predicat inconnu est REFUSE, jamais ignore : un rejet muet ferait croire a
    l'auteur qu'il a declare ce qu'il n'a pas declare — le « drop silencieux » que ce depot a deja paye."""
    viol, _sans = scan_clauses(_CLOSE + "<!-- closes_when:run_command=rm -rf / -->\n")
    assert any(k.startswith("clause-refusee:P9.1") for k in viol), viol
    assert any("INCONNU" in v for v in viol.values()), viol


def test_the_clause_REFUSES_a_grep_on_a_MISSING_file():
    """Une clause invérifiable n'est PAS une clause fausse : la distinguer evite de transformer une
    absence de donnee en affirmation NEGATIVE — le biais systematique mesure une trentaine de fois ici."""
    viol, _sans = scan_clauses(_CLOSE + "<!-- closes_when:grep_present=tools/fantome.py::motif -->\n")
    assert any(k.startswith("clause-refusee:P9.1") for k in viol), viol
    assert any("invérifiable" in v for v in viol.values()), viol


def test_the_clause_REFUSES_a_grep_without_a_pattern():
    """`grep_present` attend `chemin::motif`. Une forme incomplete est refusee, pas devinee."""
    viol, _sans = scan_clauses(_CLOSE + "<!-- closes_when:grep_present=tools/check_backlog_freshness.py -->\n")
    assert any(k.startswith("clause-refusee:P9.1") for k in viol), viol


# --- cas SPARES (reponse connue NON) ----------------------------------------------------------------

def test_the_clause_SPARES_a_closed_entry_whose_condition_HOLDS():
    """POSITIF APPARIE. Sans lui, un cliquet qui crierait sur TOUTE clause passerait les cas `fires`."""
    viol, _sans = scan_clauses(_CLOSE + _VRAI)
    assert viol == {}, viol


def test_the_clause_SPARES_an_open_entry_whose_condition_is_NOT_yet_met():
    """L'etat NORMAL d'une entree ouverte : du travail reste a faire, la clause n'est pas satisfaite.
    Le cliquet doit se taire — sinon il crie sur tout le backlog en cours."""
    viol, _sans = scan_clauses(_OUVERTE + _FAUX)
    assert viol == {}, viol


def test_an_entry_WITHOUT_a_clause_is_OUT_OF_SCOPE_and_is_REPORTED():
    """⚠️ La distinction qui compte : une entree sans clause n'est pas « fraiche », elle est HORS
    PERIMETRE. La compter comme un succes ferait annoncer au cliquet une couverture semantique qu'il
    n'a pas — le faux vert « 100 % quand on en fait 35 » que ce depot a deja mesure sur lui-meme."""
    viol, sans = scan_clauses(_OUVERTE + "du texte, aucune clause.\n")
    assert viol == {} and sans == 1, (viol, sans)


def test_both_predicate_polarities_work():
    """`*_absent` est le miroir de `*_present` — sans lui, on ne peut declarer que des conditions
    d'apparition, jamais de DISPARITION (« ce code mort a bien ete retire »)."""
    viol, _ = scan_clauses(_CLOSE + "<!-- closes_when:path_absent=tools/il_nexiste_pas.py -->\n")
    assert viol == {}, viol
    viol, _ = scan_clauses(_CLOSE + "<!-- closes_when:path_absent=tools/check_backlog_freshness.py -->\n")
    assert any(k.startswith("clause-rouverte") for k in viol), viol


# --- confrontation au BACKLOG REEL ------------------------------------------------------------------

def test_the_REAL_backlog_has_clauses_AND_reports_what_it_cannot_see():
    """Ancrage sur le reel : des clauses existent VRAIMENT (sinon le mecanisme serait decoratif), aucune
    n'est violee, et le hors-perimetre est RAPPORTE."""
    with open(os.path.join(_ROOT, "docs", "roadmap", "PRIORITES_ET_DETTES.md"), encoding="utf-8") as fh:
        txt = fh.read()
    viol, sans = scan_clauses(txt)
    assert viol == {}, f"clause(s) violee(s) dans le backlog reel : {viol}"
    assert txt.count("closes_when:") >= 5, "le mecanisme doit etre UTILISE, pas seulement disponible"
    assert sans > 0, "le hors-perimetre doit etre RAPPORTE, pas avale"
    scan()
    assert getattr(scan, "entrees_sans_clause", None) == sans, "le compte rapporte doit etre le compte reel"


def test_the_hook_gates_claimed_CLOSED_are_STILL_wired():
    """⚠️ CONTRE-EXEMPLE GELE, et c'est la raison d'etre du second sens. Quatre entrees declarent CLOS
    « la garde est branchee sur le hook » ; leurs clauses le VERIFIENT. Si quelqu'un debranche une porte,
    le backlog cesse d'etre vrai — et jusqu'ici rien ne l'aurait dit."""
    with open(os.path.join(_ROOT, "tools", "hooks", "pre-commit"), encoding="utf-8") as fh:
        hook = fh.read()
    for garde in ("check_bar_separation", "check_preregistration_applied",
                  "check_staged_authorship", "check_substrate_pinning"):
        assert garde in hook, f"{garde} n'est plus branche : une entree CLOSE du backlog est devenue fausse"
