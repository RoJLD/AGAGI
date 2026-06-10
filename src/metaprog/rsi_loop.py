"""
src/metaprog/rsi_loop.py — Architecture de la boucle RSI (#8), CÂBLÉE MAIS NON ARMÉE (EDR 044).

La boucle d'auto-amélioration, en 5 temps :

    DÉTECTER  (superviseur réflexif, plateau/famine — EDR 036)
      -> PROPOSER  (un `Proposer` : générateur de changement)
      -> VALIDER   (sandbox sécurisée — gate AST + exécution isolée, EDR 035)
      -> MESURER   (le changement améliore-t-il vraiment ? — discipline EDR 039/041)
      -> ENREGISTRER (ontologie KuzuDB : Hypothesis/Fact — EDR 032/034)

Le GÉNÉRATEUR est une **abstraction** (`Proposer`), pas un appel LLM en dur :
  - `TemplateProposer` : sûr, non-LLM, le DÉFAUT (fait tourner la boucle sans dépendance).
  - `LLMProposer`      : >>> LE SEAM DU #8, NON ARMÉ <<< — y brancher un vrai LLM le jour venu.

Périmètre minimal (volontaire) : fonctions d'**activation** pures numpy `f(x)->x`. On élargira
prudemment (termes de récompense, règles de monde, architecture/NAS) une fois la boucle éprouvée.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.metaprog.secure_sandbox import run_sandboxed, first_def_name

# Périmètre du #8 — on commence par le plus borné/sûr. Élargir un cran à la fois.
ALLOWED_KINDS = {"activation"}


@dataclass
class Proposal:
    """Le contrat de sortie du générateur. Format stable que le LLM devra respecter (#8)."""
    kind: str            # "activation" (périmètre minimal actuel)
    name: str            # ex. "swish"
    code: str            # code Python pur (numpy), une fonction f(x)->x
    rationale: str = ""  # pourquoi (lisible ; va dans l'ontologie)


class Proposer(ABC):
    """Le GÉNÉRATEUR de nouveauté. `context` = {"trend": ..., "recent": [...]}."""
    @abstractmethod
    def propose(self, context: dict) -> Proposal:
        ...


class TemplateProposer(Proposer):
    """Générateur SÛR, non-LLM (défaut, non armé) : pioche dans un catalogue d'activations.
    Permet d'exécuter et tester TOUTE la boucle RSI sans aucune dépendance externe."""
    CATALOG = [
        ("swish",
         "import numpy as np\n\ndef swish(x):\n    return x / (1.0 + np.exp(-x))\n"),
        ("gelu_approx",
         "import numpy as np\n\ndef gelu_approx(x):\n"
         "    return 0.5 * x * (1.0 + np.tanh(0.7978845608 * (x + 0.044715 * x ** 3)))\n"),
        ("softsign",
         "import numpy as np\n\ndef softsign(x):\n    return x / (1.0 + np.abs(x))\n"),
    ]

    def __init__(self):
        self._i = 0

    def propose(self, context: dict) -> Proposal:
        name, code = self.CATALOG[self._i % len(self.CATALOG)]
        self._i += 1
        direction = (context or {}).get("trend", {}).get("direction", "?")
        return Proposal("activation", name, code, rationale=f"catalogue (tendance={direction})")


class LLMProposer(Proposer):
    """>>> SEAM DU #8 — NON ARMÉ <<<

    Brancher ICI un vrai LLM (dans un CONTENEUR JETABLE) : il reçoit `context` (la tendance
    multi-ères + les propositions déjà tentées/réfutées via l'ontologie), et renvoie une `Proposal`
    respectant le format ci-dessus. Tant que non armé, lève NotImplementedError -> la boucle
    retombe automatiquement sur le `TemplateProposer` (aucun risque).

    Prérequis pour armer (cf. EDR 035/044) : conteneur jetable, périmètre borné (ALLOWED_KINDS),
    et FALSIFICATION systématique (le code doit *mesurablement* améliorer, pas seulement compiler).
    """
    def propose(self, context: dict) -> Proposal:
        raise NotImplementedError(
            "ARMER LE #8 : brancher l'appel LLM ici (conteneur jetable, perimetre borne, "
            "falsification systematique). Voir docs/EDR/044.")


def evaluate_proposal(proposal: Proposal):
    """VALIDE une proposition (périmètre + gate AST + test isolé). N'INSTALLE PAS. -> (ok, raison)."""
    if proposal.kind not in ALLOWED_KINDS:
        return False, f"kind hors perimetre: {proposal.kind}"
    fn = first_def_name(proposal.code)
    if fn is None:
        return False, "aucune fonction definie"
    test = (
        "import numpy as np\n"
        f"_r = {fn}(np.array([-1.0, 0.0, 1.0]))\n"
        "assert _r.shape == (3,)\n"
        "assert not np.isnan(_r).any() and not np.isinf(_r).any()\n"
        "print('ok')\n"
    )
    return run_sandboxed(proposal.code, test)


def rsi_step(context: dict, proposer: Proposer = None, graph=None):
    """UN pas de la boucle #8 : PROPOSER -> VALIDER -> ENREGISTRER (ontologie si `graph`).
    NON ARMÉ par défaut (TemplateProposer). L'INSTALLATION du code validé reste au caller
    (pour garder l'effet de bord explicite). Renvoie (proposal, ok, reason)."""
    if proposer is None:
        proposer = TemplateProposer()
    try:
        proposal = proposer.propose(context)
    except NotImplementedError:
        proposal = TemplateProposer().propose(context)      # repli sûr : LLM non armé
        proposal.rationale += " [repli: LLM non arme]"

    ok, reason = evaluate_proposal(proposal)

    if graph is not None:
        hid = f"rsi_{proposal.kind}_{proposal.name}"
        graph.log_hypothesis(hid, f"La proposition {proposal.name} ({proposal.kind}) ameliore le systeme",
                             status="proposed")
        graph.log_fact(f"rsi_eval_{proposal.name}", f"validation sandbox: ok={ok} ({reason})",
                       hid, relation="SUPPORTS" if ok else "REFUTES")
    return proposal, ok, reason
