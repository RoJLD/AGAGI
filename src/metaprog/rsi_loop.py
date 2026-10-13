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


def build_demand_prompt(context: dict) -> str:
    """Construit le prompt du #8 à partir du contexte : tendance + demandes déjà essayées et leurs
    scores MESURÉS (via l'ontologie). Le LLM lit les échecs passés pour ne pas se répéter (EDR 059)."""
    trend = (context or {}).get("trend", {})
    past = (context or {}).get("recent", [])
    lines = [
        "Tu es le générateur d'un système d'auto-amélioration (RSI). Propose UNE *demande de monde*",
        "qui fasse ÉMERGER une capacité (langage référentiel, ou capacité mémoire/architecture).",
        "Principe (prouvé empiriquement) : on ne fabrique pas une capacité en l'ajoutant — il faut que",
        "le monde l'EXIGE, de façon CIBLÉE et SURVIVABLE.",
        f"Tendance actuelle : {trend}.",
        "Demandes déjà essayées et leur score MESURÉ (multi-seed) — n'en répète pas une ratée :",
    ]
    for p in past:
        lines.append(f"  - {p.get('name')}: params={p.get('params')} -> score={p.get('score')}")
    lines += [
        "Paramètres de monde disponibles : lewis(bool), referential_scale(float), speaker_reward(float),",
        "align_selection(float), transient_apex(bool).",
        'Réponds UNIQUEMENT en JSON : {"name": "...", "params": {...}, "rationale": "..."}',
    ]
    return "\n".join(lines)


# >>> FRONTIÈRE DE SÛRETÉ du #8 `world_demand` (EDR 065) <<<
# Le LLM ne peut proposer QUE ces paramètres de monde, typés et bornés. Tout le reste est REJETÉ.
# C'est ce qui rend l'armement SÛR SANS conteneur : aucun code généré/exécuté, surface d'attaque nulle
# (au pire un réglage inutile). Le conteneur (EDR 044) ne reste requis que pour le kind `activation`.
ALLOWED_DEMAND_PARAMS = {
    "lewis": ("bool", None),
    "referential_scale": ("float", (0.0, 2.0)),
    "speaker_reward": ("float", (0.0, 20.0)),
    "align_selection": ("float", (0.0, 20.0)),
    "transient_apex": ("bool", None),
}


def sanitize_demand_params(params: dict) -> dict:
    """Ne garde QUE les params de l'allow-list, typés et clampés. Rejette tout le reste (sûreté)."""
    clean = {}
    for k, v in (params or {}).items():
        if k not in ALLOWED_DEMAND_PARAMS:
            continue
        typ, rng = ALLOWED_DEMAND_PARAMS[k]
        try:
            if typ == "bool":
                v = v.strip().lower() in ("true", "1", "yes") if isinstance(v, str) else bool(v)
            else:
                v = float(v)
        except (TypeError, ValueError):
            continue
        if rng:
            v = max(rng[0], min(rng[1], v))
        clean[k] = v
    return clean


def parse_demand_response(text: str) -> Proposal:
    """Parse la réponse LLM (JSON) en Proposal `world_demand`, params SANITISÉS (allow-list bornée).
    Lève ValueError si pas de JSON valide."""
    import json
    import re
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        raise ValueError("reponse LLM sans JSON")
    d = json.loads(m.group(0))
    params = d.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("params n'est pas un objet")
    return Proposal("world_demand", str(d.get("name", "llm_demand")),
                    rationale=str(d.get("rationale", "")), params=sanitize_demand_params(params))


class LLMProposer(Proposer):
    """>>> SEAM DU #8 <<< — ARMABLE par injection, NON ARMÉ par défaut.

    Le LLM est injecté comme une **fonction** `llm_fn(prompt:str) -> str` :
      - défaut `llm_fn=None` -> `propose` lève NotImplementedError (la boucle retombe sur le
        TemplateProposer ; aucun risque, verrou EDR 044 préservé) ;
      - en prod : injecter une `llm_fn` qui appelle un vrai LLM **dans un conteneur jetable**
        (prérequis EDR 035/044) ; `propose` construit le prompt (contexte+échecs passés), appelle,
        et parse la réponse en `Proposal` world_demand.

    Armer le #8 = (1) fournir `llm_fn` (conteneur+clé) + (2) évaluer chaque proposition via le
    HARNAIS PUISSANT (multi-seed, EDR 052) — sinon la boucle optimise le bruit (EDR 051). Voir EDR 059.
    """
    def __init__(self, llm_fn=None):
        self.llm_fn = llm_fn

    def propose(self, context: dict) -> Proposal:
        if self.llm_fn is None:
            raise NotImplementedError(
                "ARMER LE #8 : injecter llm_fn (conteneur jetable + cle) + mesure puissante "
                "(harnais EDR 052). Voir docs/EDR/059.")
        return parse_demand_response(self.llm_fn(build_demand_prompt(context)))


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


def make_powered_measure(run_seed_fn, seeds=(0, 1, 2)):
    """Fabrique un `measure_fn` PUISSANT pour `rsi_demand_step` — le 2ᵉ prérequis d'armement du #8
    (EDR 059/061). Évalue chaque demande en MULTI-SEED via le harnais (EDR 052) au lieu d'un run
    unique : sans ça, la boucle CLASSE LE BRUIT (EDR 051, démontré). World-agnostique : `run_seed_fn`
    (params, seed) -> float (le gain mesuré d'UN réplicat) est injecté par le caller.

    Renvoie measure(proposal) -> (score=moyenne sur seeds, detail='moy±σ (n)')."""
    from src.seed_ai.eval_harness import powered_eval

    def measure(proposal):
        res = powered_eval({proposal.name: proposal.params}, run_seed_fn, seeds=seeds)
        d = res[proposal.name]
        return d["mean"], f"gain={d['mean']:.4f}+/-{d['std']:.4f} (n={d['n']})"

    return measure


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
