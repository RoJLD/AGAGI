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
