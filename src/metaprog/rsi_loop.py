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
from dataclasses import dataclass, field

from src.metaprog.secure_sandbox import run_sandboxed, first_def_name

# Périmètre du #8. EDR 044 : "activation" (sûr, sandbox). EDR 046/051 : "world_demand" — proposer
# une DEMANDE de monde (le vrai levier d'émergence : langage, architecture). On élargit un cran.
ALLOWED_KINDS = {"activation", "world_demand"}


@dataclass
class Proposal:
    """Le contrat de sortie du générateur. Format stable que le LLM devra respecter (#8)."""
    kind: str            # "activation" | "world_demand"
    name: str            # ex. "swish" | "lewis_2ref"
    code: str = ""       # (activation) code Python pur (numpy), une fonction f(x)->x
    rationale: str = ""  # pourquoi (lisible ; va dans l'ontologie)
    params: dict = field(default_factory=dict)  # (world_demand) attrs à poser sur le monde


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


class WorldDemandProposer(Proposer):
    """Générateur DIRIGÉ (non-LLM) de DEMANDES de monde — le périmètre le plus puissant (EDR 051).

    Catalogue des demandes qu'on a conçues/mesurées à la main (047 succès, 045/050 échecs). La
    boucle les ré-essaie et les CLASSE par la mesure — exactement la recherche que la conception
    manuelle rate (cf. EDR 050 : 4 designs, 3+ échecs). Le LLMProposer s'y substituerait pour en
    INVENTER de nouvelles, en lisant les échecs passés via l'ontologie.

    Chaque demande = des `params` à poser sur le monde + une métrique cible. L'évaluation (évoluer
    sous la demande + mesurer) est injectée par le caller (rsi_loop reste agnostique du monde)."""
    CATALOG = [
        ("lewis_2ref", {"lewis": True}, "demande referentielle reelle (Lewis 2 ref, EDR 047 succes)"),
        ("referential_pressure", {"lewis": True, "referential_scale": 0.5}, "pression scriptee (EDR 045 echec)"),
        ("speaker_reciprocity", {"lewis": True, "speaker_reward": 5.0}, "reciprocite du locuteur (EDR 050 echec)"),
    ]

    def __init__(self):
        self._i = 0

    def propose(self, context: dict) -> Proposal:
        name, params, rationale = self.CATALOG[self._i % len(self.CATALOG)]
        self._i += 1
        return Proposal("world_demand", name, rationale=rationale, params=dict(params))


def rsi_demand_step(context: dict, measure_fn, proposer: Proposer = None, graph=None):
    """UN pas de la boucle #8 sur les DEMANDES de monde : PROPOSER -> MESURER (via `measure_fn`,
    injecté : il applique la demande, évolue, et renvoie un score) -> ENREGISTRER (ontologie).
    `measure_fn(proposal) -> (score: float, detail: str)`. Renvoie (proposal, score, detail)."""
    if proposer is None:
        proposer = WorldDemandProposer()
    proposal = proposer.propose(context)
    score, detail = measure_fn(proposal)
    if graph is not None:
        hid = f"rsi_demand_{proposal.name}"
        graph.log_hypothesis(hid, f"La demande {proposal.name} fait emerger la capacite cible",
                             status="proposed")
        graph.log_fact(f"rsi_demand_eval_{proposal.name}", f"score mesure={score:.4f} ({detail})",
                       hid, relation="SUPPORTS" if score > 0 else "REFUTES")
    return proposal, score, detail


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
