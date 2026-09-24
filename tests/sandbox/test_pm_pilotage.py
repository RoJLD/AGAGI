# -*- coding: utf-8 -*-
"""Pilotage : `compute_pilotage` est PURE et `parse_roadmap` réutilise le cliquet du backlog.
EXEMPTION DÉCLARÉE de la garde de bail : aucun test ici ne simule un monde ni ne prend de bail."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import pilotage as P  # noqa: E402

_LEASE_GUARD_EXEMPT = True

NOW = 1_800_000_000.0


def test_la_racine_est_ancree_sur_le_module_et_en_POSIX():
    """`find_repo_root` essaie `Path.cwd()` EN PREMIER (tools/parity_check.py:44-47) : lancé depuis un autre
    dépôt il rend l'autre dépôt, et le pilotage accuserait alors les bons fichiers d'être absents — un
    négatif FABRIQUÉ. La racine s'ancre donc sur le MODULE, et se publie en POSIX (un antislash dans un
    href est encodé %5C et VS Code ne le résout pas)."""
    r = P.racine_depot()
    assert "\\" not in r, f"la racine doit être en POSIX : {r!r}"
    assert os.path.isdir(os.path.join(r, "tools", "pm")), r
    assert os.path.isfile(os.path.join(r, "docs", "roadmap", "PRIORITES_ET_DETTES.md")), r


_BACKLOG_SYNTH = """# Backlog synthétique

**P2.10 — ⚠️ OUVERTE (2026-09-01) — une entrée ouverte qui cite `tools/cost_guard.py`.**
Corps de l'entrée.
<!-- closes_when:grep_present=tools/cost_guard.py::process_time -->

**P2.11 — rang 3 — ✅ CLOSE le 2026-09-02 — une entrée close.**
Corps.

**P2.12 — 🗑️ PÉRIMÉE (2026-09-03) — une entrée périmée.**
Corps.

**P2.0 / P2.1 — rang 14 ter — OUVERTE (2026-09-04) — une tête COMPOSITE.**
Corps de la composite.

**P4.9 — OUVERTE (2026-09-05) —
rang 4 quinquies — le rang est sur la DEUXIÈME ligne, et porte un suffixe long.**
Corps.
"""


def test_la_parite_porte_sur_les_BLOCS_pas_sur_les_entrees():
    """DÉFAUT BLOQUANT trouvé en revue (spec §2.2) : `compter_entrees` compte des LIGNES de tête, donc une
    tête composite `P2.0 / P2.1` vaut UN. Asserter la parité sur les ENTRÉES la ferait lever au premier
    composite, `compute_pilotage` tomberait dans le `except` du service et TOUT le pilotage deviendrait
    aveugle à cause d'une seule tête."""
    from tools.check_backlog_freshness import compter_entrees
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    assert out["comptes"]["blocs"] == compter_entrees(_BACKLOG_SYNTH) == 5
    assert out["comptes"]["numeros"] == 6, "la composite donne DEUX entrées après l'assertion"
    assert len(out["entrees"]) == 6


def test_tete_composite_une_entree_par_numero_memes_bornes():
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    comp = [e for e in out["entrees"] if e["num"] in ("P2.0", "P2.1")]
    assert [e["num"] for e in comp] == ["P2.0", "P2.1"]
    assert comp[0]["nums"] == comp[1]["nums"] == ["P2.0", "P2.1"]
    assert comp[0]["bloc"] == comp[1]["bloc"]
    assert comp[0]["lignes"] == comp[1]["lignes"]


def test_statuts_rang_et_date():
    out = P.parse_roadmap(_BACKLOG_SYNTH, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    par = {e["num"]: e for e in out["entrees"]}
    assert par["P2.10"]["statut"] == "ouverte" and par["P2.10"]["date"] == "2026-09-01"
    assert par["P2.11"]["statut"] == "close" and par["P2.11"]["rang"] == "3"
    assert par["P2.12"]["statut"] == "perimee"
    assert par["P2.0"]["rang"] == "14 ter"
    assert par["P4.9"]["rang"] == "4 quinquies", "rang sur la 2e ligne, suffixe NON tronqué"
    assert par["P2.10"]["priorite"] == "P2" and par["P4.9"]["priorite"] == "P4"


def test_ordre_des_rangs_par_base_puis_suffixe():
    """Un tri de CHAÎNES mettrait `14 quater` avant `14 ter` et `10` avant `2` : la vue centrale de
    l'avancement serait illisible. Et un rang n'est pas unique — 5 rangs sont portés par deux entrées sur
    le backlog réel —, donc la direction est une liste par rang."""
    txt = _BACKLOG_SYNTH + """
**P2.20 — rang 14 quater — OUVERTE (2026-09-06) — après ter.**
Corps.

**P2.21 — rang 2 — OUVERTE (2026-09-07) — avant dix.**
Corps.

**P2.22 — rang 10 — OUVERTE (2026-09-08) — après deux.**
Corps.
"""
    out = P.parse_roadmap(txt, P.racine_depot(), NOW, evaluer_clause=lambda p, a: (True, None))
    rangs = [r["rang"] for r in out["direction"]["rangs"]]
    assert rangs == ["2", "3", "4 quinquies", "10", "14 ter", "14 quater"], rangs
    assert all(isinstance(r["p_items"], list) for r in out["direction"]["rangs"])
