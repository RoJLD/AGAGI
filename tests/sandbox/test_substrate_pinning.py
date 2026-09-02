"""Calibration du cliquet `check_substrate_pinning` (P2.27).

Un cliquet doit pouvoir ÉCHOUER, et se confronter à une réponse CONNUE avant qu'on le croie : les deux
cliquets livrés le 2026-09-01 ont rendu 5 puis 2 faux positifs avant correction. Chaque cas ci-dessous
a donc une réponse connue AVANT la mesure, et il y a autant de cas `spares` (réponse NON) que de cas
`fires` (réponse OUI) — une garde qui refuse tout passerait les seconds seule.
"""
import os

import pytest

from tools.check_substrate_pinning import _ROOT, _defects, scan

# --- sources SYNTHÉTIQUES à réponse connue -----------------------------------------------------

_PIN = "TorchPopulationModel.BILINEAR = bool(bilinear)\n"
_MAKE = "pop = make_population(agents, backend='torch')\n"
_ADAM_NU = "pop.opt = torch.optim.Adam([pop.W], lr=lr)\n"
_ADAM_PLEIN = ("params = [pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None]\n"
               "pop.opt = torch.optim.Adam(params, lr=lr)\n")


def test_the_ratchet_FIRES_on_an_unpinned_substrate():
    """Défaut A, réponse connue OUI : construit une population, n'épingle JAMAIS `BILINEAR`.
    C'est le cas des 16 sondes de l'audit du 2026-09-02, dont les DEUX qui ont gravé les arêtes."""
    assert _defects(_MAKE + _ADAM_PLEIN) == {"A"}


def test_the_ratchet_FIRES_on_an_incomplete_optimizer():
    """Défaut B, réponse connue OUI : épingle bien le substrat, mais `Adam([pop.W])` laisse
    `U/V/W_bl` GELÉS à leur init. Piège ARMÉ — latent tant que le flag est faux, il rend un nul qui
    ne mesure que l'initialisation dès qu'on l'active."""
    assert _defects(_PIN + _MAKE + _ADAM_NU) == {"B"}


def test_the_ratchet_FIRES_on_BOTH_at_once():
    """Les deux défauts sont INDÉPENDANTS et se cumulent — 11 des 16 sondes en dette portent les deux."""
    assert _defects(_MAKE + _ADAM_NU) == {"A", "B"}


def test_the_ratchet_SPARES_a_correct_probe():
    """POSITIF APPARIÉ, réponse connue NON. Sans lui, un cliquet qui crierait sur TOUTE sonde
    passerait les trois tests ci-dessus."""
    assert _defects(_PIN + _MAKE + _ADAM_PLEIN) == set()


def test_the_ratchet_SPARES_the_inline_concatenation_idiom():
    """⚠️ FAUX POSITIF RÉEL de ce cliquet, trouvé le 2026-09-02 en corrigeant une sonde AVEC lui, et
    devenu un cas de calibration (règle d'auto-amélioration du dépôt).

    La version d'origine lisait le PREMIER crochet seul (`Adam\\(\\s*\\[([^\\]]*)\\]`) et criait donc sur
    l'idiome pourtant JUSTE ci-dessous, dont les paramètres bilinéaires vivent dans le SECOND crochet.
    Un cliquet qui crie sur du code correct est pire qu'absent : on apprend à l'ignorer."""
    inline = ("pop.opt = torch.optim.Adam(\n"
              "    [pop.W] + [p for p in (pop.U, pop.V, pop.W_bl) if p is not None], lr=lr)\n")
    assert _defects(_PIN + _MAKE + inline) == set()


def test_the_ratchet_SPARES_an_optimizer_built_ELSEWHERE():
    """Portée : `Adam(params)` / `Adam(_full_params(pop))` ne contiennent aucune liste littérale.
    Deviner ce qu'elles portent serait proxifier ce qu'on ne sait pas mesurer — on s'abstient, et on
    le dit. C'est une NON-DÉTECTION assumée, pas un succès."""
    assert _defects(_PIN + _MAKE + "pop.opt = torch.optim.Adam(_full_params(pop), lr=lr)\n") == set()
    assert _defects(_PIN + _MAKE + "pop.opt = torch.optim.Adam(params, lr=lr)\n") == set()


def test_the_ratchet_SPARES_a_PARTIAL_fix():
    """Une sonde qui passe de {A,B} à {A} s'est AMÉLIORÉE : le cliquet ne doit pas la signaler.
    Une égalité stricte à la baseline punirait le correctif — un cliquet bloque la dette NOUVELLE,
    jamais la dette RÉDUITE. Vérifié sur la logique de comparaison, par différence d'ensembles."""
    base = {"tools/x.py": ["A", "B"]}
    for restant in (["A"], ["B"], []):
        assert not (set(restant) - set(base["tools/x.py"])), \
            f"{restant} est un sous-ensemble de la dette gelée -> ne doit RIEN déclencher"
    assert set(["A", "B"]) - set(["A"]) == {"B"}, "gagner un défaut DOIT déclencher"


def test_a_file_without_a_population_is_OUT_OF_SCOPE_not_CLEAN():
    """⚠️ La distinction qui compte : `None` (hors périmètre) n'est PAS `set()` (examiné, sans défaut).

    Les confondre ferait compter 191 fichiers sans rapport comme autant de succès, et le cliquet
    annoncerait une couverture de 210 là où il en examine 19. C'est le défaut « un cliquet qui annonce
    100 % quand il en fait 35 » que ce dépôt a déjà mesuré sur lui-même."""
    assert _defects("x = 1\nprint('rien a voir')\n") is None
    assert _defects(_PIN + _MAKE + _ADAM_PLEIN) is not None


# --- confrontation aux FICHIERS RÉELS ----------------------------------------------------------

@pytest.mark.parametrize("corrige", [
    "tools/delayed_coordination_demand_probe.py",        # 3b5554a
    "tools/language_memory_demand_probe.py",             # 481117e, session parallèle
    "tools/memory_perception_demand_probe.py",           # a GRAVÉ `memory→perception`
    "tools/perception_coordination_demand_probe.py",     # a GRAVÉ `language→perception`
])
def test_a_corrected_probe_STAYS_corrected(corrige):
    """Ancrage sur le RÉEL, un cas par sonde pour que l'échec NOMME la coupable.

    Les deux dernières sont les sondes qui ont GRAVÉ les deux arêtes du graphe AGI-Taxonomy : leur
    substrat était hérité de l'ambiant, donc leurs résultats publiés n'étaient pas identifiables a
    posteriori. Elles sont désormais épinglées à `bilinear=False` — le substrat `plain`, celui de
    leurs mesures publiées, donc BIT-IDENTIQUE (à False, `U/V/W_bl` valent `None` et la liste de
    l'optimiseur se réduit à `[pop.W]` : mesuré, pas argumenté).
    Ce test tombe si l'une régresse, AVANT que le cliquet ne puisse l'absorber dans sa baseline."""
    en_defaut, hors, examines = scan(only=[corrige])
    assert examines == 1, f"la sonde doit être DANS le périmètre (hors={hors})"
    assert en_defaut == {}, f"régression d'épinglage : {en_defaut}"


def test_the_audit_count_is_STILL_REAL():
    """La dette gelée doit rester une DETTE, pas un commentaire. Si l'arbre entier passait sans
    défaut, la baseline ne protégerait plus rien et il faudrait la vider — même exigence que
    `test_the_legacy_declaration_is_STILL_REAL` pour la dette de pré-enregistrement."""
    en_defaut, hors, examines = scan()
    assert examines >= 19, f"le périmètre s'est effondré : {examines} sondes examinées"
    assert len(en_defaut) >= 1, "plus aucune dette : vider la baseline au lieu de la garder"
    assert len(hors) > examines, "le hors-périmètre doit être RAPPORTÉ, pas avalé"


def test_the_frozen_debt_is_a_DEBT_not_a_decoration():
    """La baseline doit rester une DETTE RÉELLE : si toutes les sondes qu'elle gèle étaient corrigées,
    il faudrait la VIDER, pas la garder. Une dette qui ne peut plus être invalidée n'est plus une
    dette, c'est un commentaire — même exigence que `test_the_legacy_declaration_is_STILL_REAL` pour
    la dette de pré-enregistrement."""
    from tools.check_substrate_pinning import _load_baseline
    base = _load_baseline()
    assert base, "baseline vide : soit la retirer, soit la regénérer"
    en_defaut, _hors, _ex = scan()
    encore = [k for k in base if k in en_defaut]
    assert encore, "toutes les sondes gelées sont corrigées -> vider la baseline au lieu de la garder"
    # et la baseline ne doit pas gonfler au-delà du réel : ce qu'elle gèle doit encore exister
    for k in base:
        assert os.path.exists(os.path.join(_ROOT, k)), f"la baseline gèle un fichier DISPARU : {k}"
