"""
Module: lu_human_explainer.py
Projet: AGIseed / AGAGI (Branche de recherche LU)
Description: Décompilateur et traducteur de pensées latentes/Gigatokens vers le langage humain naturel.
Garantit l'auditabilité et la transparence cognitive (Commandement 5: Transparent & Auditable).

Transforme les structures géométriques et graphes LU en explications claires en français et anglais.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from src.metaprog.lu_dsl_engine import LUGraph, LUNode, LUCompiler
from src.metaprog.lu_dsl_semantic import LUSemanticParser


@dataclass
class LUExplanationReport:
    """Rapport d'explicabilité humaine pour une pensée LU."""
    human_text_fr: str
    human_text_en: str
    primary_intent: str
    causal_chain: List[str]
    confidence_score: float
    nodes_count: int
    edges_count: int


class LUHumanExplainer:
    """
    Décompilateur sémantique traduisant les pensées machines LU en langage humain clair.
    """

    def __init__(self, parser: Optional[LUSemanticParser] = None):
        self.parser = parser or LUSemanticParser()
        self.compiler = LUCompiler()

        # Dictionnaire sémantique de traduction des relations
        self.rel_glossary_fr = {
            "TARGETS": "a pour cible prioritaire",
            "DESIRES": "cherche à atteindre l'état",
            "AVOIDS": "cherche activement à fuir",
            "TRIGGERS": "déclenche l'action",
            "CAUSES": "provoque directement",
            "LEADS_TO": "mène séquentiellement à",
            "IS_A": "est une instance de",
            "PART_OF": "constitue un sous-élément de",
            "INFLUENCES": "exerce une influence sur",
        }

        self.rel_glossary_en = {
            "TARGETS": "actively targets",
            "DESIRES": "desires to reach state",
            "AVOIDS": "actively avoids",
            "TRIGGERS": "triggers action",
            "CAUSES": "directly causes",
            "LEADS_TO": "leads sequentially to",
            "IS_A": "is an instance of",
            "PART_OF": "is a component of",
            "INFLUENCES": "influences",
        }

    def explain_graph(self, graph: LUGraph, confidence: float = 1.0) -> LUExplanationReport:
        """
        Décompile un LUGraph en explication humaine fluide.
        """
        if not graph.nodes:
            return LUExplanationReport(
                human_text_fr="État mental neutre : aucune intention active.",
                human_text_en="Neutral mental state: no active intent.",
                primary_intent="Repos / Inaction",
                causal_chain=[],
                confidence_score=0.0,
                nodes_count=0,
                edges_count=0,
            )

        fr_sentences = []
        en_sentences = []
        causal_steps = []

        # Identifier les agents initiateurs
        agents = [n for n in graph.nodes.values() if n.category == "AGENT"]
        primary_agent = agents[0].label if agents else "L'agent"

        for src_id, rel, tgt_id in graph.edges:
            src_node = graph.nodes.get(src_id)
            tgt_node = graph.nodes.get(tgt_id)

            if not src_node or not tgt_node:
                continue

            rel_clean = rel.split("{")[0].strip()
            src_name = src_node.label or src_id
            tgt_name = tgt_node.label or tgt_id

            gloss_fr = self.rel_glossary_fr.get(rel_clean, f"est lié via {rel_clean} à")
            gloss_en = self.rel_glossary_en.get(rel_clean, f"is linked via {rel_clean} to")

            fr_sentences.append(f"{src_name} {gloss_fr} {tgt_name}.")
            en_sentences.append(f"{src_name} {gloss_en} {tgt_name}.")
            causal_steps.append(f"{src_name} -> [{rel_clean}] -> {tgt_name}")

        if not fr_sentences:
            # Graphe avec nœuds isolés
            node_labels = [n.label or n.id for n in graph.nodes.values()]
            fr_text = f"Perception passive des concepts : {', '.join(node_labels)}."
            en_text = f"Passive perception of concepts: {', '.join(node_labels)}."
            primary_intent = f"Observation ({', '.join(node_labels)})"
        else:
            fr_text = " ".join(fr_sentences)
            en_text = " ".join(en_sentences)
            primary_intent = f"{primary_agent} en action : {causal_steps[0] if causal_steps else 'Interaction'}"

        return LUExplanationReport(
            human_text_fr=fr_text,
            human_text_en=en_text,
            primary_intent=primary_intent,
            causal_chain=causal_steps,
            confidence_score=float(confidence),
            nodes_count=len(graph.nodes),
            edges_count=len(graph.edges),
        )

    def explain_dsl_string(self, dsl_statement: str) -> LUExplanationReport:
        """Parse une chaîne DSL et génère l'explication humaine."""
        graph = self.parser.parse_statement(dsl_statement)
        return self.explain_graph(graph, confidence=0.98)
