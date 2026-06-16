"""Route /api/health/parity — expose le rapport de la gate de parité (tools/parity_check) en JSON.

Transforme les WARN de la gate (endpoints non consommés, EDR orphelins, drift narration) en
données affichables par l'onglet Santé : « détecter → montrer ».
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health/parity")
def parity_report() -> dict:
    try:
        from tools.parity_check import find_repo_root, report_dict

        return report_dict(find_repo_root(None))
    except Exception as exc:  # noqa: BLE001 — garde-fou : la vue Santé ne doit jamais casser l'app
        return {
            "error": str(exc),
            "narration": {"lines": [], "warn": [], "fail": []},
            "dev_parity": {"lines": [], "warn": [], "fail": []},
            "edr_coverage": {},
            "ok": False,
            "warn_count": 0,
        }
