"""
Phase 8: Closed-Loop Metaprogramming - Sandbox Execution (durci EDR 035).

Commandement 6: Sécurité & Isolation. Commandement 7: Validation Rigoureuse.
Délègue au `secure_sandbox` : gate AST + exécution isolée dans un dossier temporaire
HORS-repo (ne pollue plus `tests/sandbox/`, qui sert à la non-régression).
"""
import logging

from src.metaprog.secure_sandbox import run_sandboxed, first_def_name

logger = logging.getLogger(__name__)


def inject_and_test(code_string: str) -> bool:
    """Valide (gate AST) et teste le code généré de façon ISOLÉE. Renvoie True si sûr & correct."""
    fn = first_def_name(code_string) or "new_activation"
    test_code = (
        "import numpy as np\n"
        f"_r = {fn}(np.array([-1.0, 0.0, 1.0]))\n"
        "assert _r.shape == (3,)\n"
        "assert not np.isnan(_r).any() and not np.isinf(_r).any()\n"
        "print('ok')\n"
    )
    ok, reason = run_sandboxed(code_string, test_code)
    if ok:
        logger.info("Sandbox test passed (secure).")
    else:
        logger.error(f"Sandbox test failed/blocked: {reason}")
    return ok
