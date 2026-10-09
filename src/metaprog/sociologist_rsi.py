"""
src/metaprog/sociologist_rsi.py — Boucle RSI pilotée par l'Observatoire Sociologique (EXP-12).
Relie les diagnostics sociologiques (Loi du Sociologue / Commandement 15)
à la métaprogrammation autonome sécurisée (Commandements 6, 7 & 12).
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np

from src.metaprog.rsi_loop import rsi_step, Proposal
from src.graph_rag.async_logger import logger


class SociologistRSILoop:
    """
    Superviseur de méta-évolution :
    1. Analyse les séries temporelles de fitness des campagnes (KuzuDB/JSON).
    2. Détecte les plateaux, régressions ou ruptures de transmission culturelle.
    3. Sollicite la boucle RSI avec un contexte orienté problème.
    4. Valide en sandbox isolée avant acceptation.
    """

    def __init__(self, stagnation_threshold: float = 0.05, graph=None):
        self.stagnation_threshold = stagnation_threshold
        self.graph = graph
        self.history: list = []

    def analyze_campaign_trend(self, era_scores: list) -> Dict[str, Any]:
        """Détermine si la campagne progresse ou stagne."""
        if len(era_scores) < 2:
            return {"direction": "INSUFFICIENT_DATA", "delta": 0.0, "needs_intervention": False}

        arr = np.array(era_scores, dtype=np.float32)
        half = len(arr) // 2
        mean_first_half = float(np.mean(arr[:half]))
        mean_second_half = float(np.mean(arr[half:]))
        delta = mean_second_half - mean_first_half

        if delta < -self.stagnation_threshold:
            direction = "REGRESSION"
            needs_intervention = True
        elif abs(delta) <= self.stagnation_threshold:
            direction = "STAGNATION"
            needs_intervention = True
        else:
            direction = "PROGRESSION"
            needs_intervention = False

        return {
            "direction": direction,
            "delta": float(delta),
            "first_half_mean": mean_first_half,
            "second_half_mean": mean_second_half,
            "needs_intervention": needs_intervention
        }

    def trigger_auto_improvement(self, campaign_scores: list, use_llm: bool = False) -> Tuple[Optional[Proposal], bool, str]:
        """Déclenche un cycle RSI si le diagnostic sociologique montre un plateau."""
        trend = self.analyze_campaign_trend(campaign_scores)
        
        context = {
            "trend": trend,
            "sociologist_diagnosis": f"Tendance: {trend['direction']} (delta={trend['delta']:.3f})",
            "recent": self.history[-3:]
        }

        proposal, ok, reason = rsi_step(
            context=context,
            graph=self.graph,
            use_llm=use_llm
        )

        outcome_record = {
            "proposal_name": proposal.name if proposal else "none",
            "kind": proposal.kind if proposal else "none",
            "ok": ok,
            "reason": reason,
            "trend": trend["direction"],
            "delta": trend["delta"]
        }

        if ok and proposal is not None:
            # Commandement 16 : Journalisation Scientifique (Articles) dans KuzuDB
            article_id = f"art_rsi_{proposal.name}_{len(self.history)}"
            title = f"RSI Innovation : {proposal.name} ({proposal.kind})"
            content = (
                f"Validation de l'intervention RSI suite à une tendance '{trend['direction']}' "
                f"(delta = {trend['delta']:.3f}).\n\n"
                f"Détail de la proposition : {proposal.rationale}\n"
                f"Statut : Validé avec succès sous sandbox de test.\n"
                f"Amélioration attendue : Rupture de plateau et stabilisation de la transmission culturelle."
            )
            logger.emit("PUBLISH_ARTICLE", {
                "id": article_id,
                "title": title,
                "content": content
            })
            outcome_record["article_id"] = article_id

        self.history.append(outcome_record)

        logger.emit("SOCIOLOGIST_RSI_INTERVENTION", {
            "proposal": proposal.name if proposal else "none",
            "kind": proposal.kind if proposal else "none",
            "validated": ok,
            "reason": reason,
            "direction": trend["direction"]
        })

        return proposal, ok, reason
