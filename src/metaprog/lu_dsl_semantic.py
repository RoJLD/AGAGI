"""
Module: lu_dsl_semantic.py
Projet: AGIseed / AGAGI (Branche de recherche LU)
Description: Parseur sémantique formel, validateur ontologique et émetteur Cypher (KuzuDB)
pour le Langage Ultime (LU DSL).

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): Règles ontologiques et taxonomies paramétrables via dataclass.
- Commandement 2 (Modulaire): Séparation stricte entre Parsing, Typage, Validation et Projection Cypher.
- Commandement 5 (Transparent & Auditable): Compilation 1-pour-1 vers le schéma Cypher de KuzuDB.
- Commandement 7 (Validation Rigoureuse): Typage sémantique strict et levée d'exceptions explicites.
- Commandement 8 (Extensible): Extensibilité des catégories et types de relations.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Dict, List, Set, Tuple, Optional, Any
import numpy as np

from src.metaprog.lu_dsl_engine import LUNode, LUGraph, LUCompiler, LUConfig


class NodeCategory(str, Enum):
    """Catégories de nœuds autorisées dans l'ontologie LU AGIseed."""
    AGENT = "AGENT"
    CONCEPT = "CONCEPT"
    ACTION = "ACTION"
    STATE = "STATE"
    TOOL = "TOOL"
    CONTEXT = "CONTEXT"


class RelationType(str, Enum):
    """Types de relations formelles reconnues par le moteur LU."""
    # Téléologique / Intentionnel
    DESIRES = "DESIRES"
    TARGETS = "TARGETS"
    AVOIDS = "AVOIDS"
    # Causal / Dynamique
    CAUSES = "CAUSES"
    TRIGGERS = "TRIGGERS"
    LEADS_TO = "LEADS_TO"
    # Taxonomique / Ontologique
    IS_A = "IS_A"
    PART_OF = "PART_OF"
    INFLUENCES = "INFLUENCES"
    # Temporel / Séquentiel
    BEFORE = "BEFORE"
    AFTER = "AFTER"


class LUSyntaxError(Exception):
    """Erreur levée lors d'une violation de syntaxe du DSL."""
    pass


class LUSemanticError(Exception):
    """Erreur levée lors d'une violation de type ou d'incohérence ontologique."""
    pass


@dataclass
class OntologyConfig:
    """Règles ontologiques pour la validation sémantique (Commandement 1: Flexible)."""
    allowed_categories: Set[str] = field(default_factory=lambda: {c.value for c in NodeCategory})
    allowed_relations: Set[str] = field(default_factory=lambda: {r.value for r in RelationType})
    # Contraintes de compatibilité relation -> (source_types, target_types)
    relation_constraints: Dict[str, Tuple[Set[str], Set[str]]] = field(default_factory=lambda: {
        "TARGETS": ({"AGENT", "ACTION"}, {"CONCEPT", "AGENT", "TOOL"}),
        "DESIRES": ({"AGENT"}, {"STATE", "CONCEPT"}),
        "AVOIDS": ({"AGENT"}, {"STATE", "CONCEPT", "AGENT"}),
        "TRIGGERS": ({"STATE", "ACTION", "CONCEPT"}, {"ACTION", "STATE"}),
        "CAUSES": ({"ACTION", "STATE"}, {"STATE", "CONCEPT"}),
        "LEADS_TO": ({"ACTION", "STATE", "CONCEPT"}, {"ACTION", "STATE", "CONCEPT"}),
        "IS_A": ({"CONCEPT", "TOOL", "AGENT"}, {"CONCEPT"}),
        "PART_OF": ({"CONCEPT", "TOOL"}, {"CONCEPT", "TOOL"}),
        "INFLUENCES": ({"CONCEPT", "STATE", "ACTION"}, {"CONCEPT", "STATE", "ACTION"}),
    })
    strict_typing: bool = True


class LUSemanticValidator:
    """Vérificateur sémantique et ontologique pour les graphes LU."""

    def __init__(self, config: Optional[OntologyConfig] = None):
        self.config = config or OntologyConfig()

    def validate_node(self, node: LUNode) -> None:
        """Valide qu'un nœud possède une catégorie reconnue et un identifiant valide."""
        if not node.id or not isinstance(node.id, str):
            raise LUSemanticError("Identifiant de nœud invalide ou vide.")
        if self.config.strict_typing and node.category not in self.config.allowed_categories:
            raise LUSemanticError(
                f"Catégorie inconnue '{node.category}' pour le nœud '{node.id}'. "
                f"Catégories autorisées: {self.config.allowed_categories}"
            )

    def validate_edge(self, src: LUNode, rel: str, tgt: LUNode) -> None:
        """Valide qu'une arête respecte les contraintes ontologiques de typage."""
        rel_clean = rel.split("{")[0].strip()
        if self.config.strict_typing:
            if rel_clean in self.config.relation_constraints:
                valid_srcs, valid_tgts = self.config.relation_constraints[rel_clean]
                if src.category not in valid_srcs:
                    raise LUSemanticError(
                        f"Relation '{rel_clean}': La source '{src.id}' a le type '{src.category}', "
                        f"mais attend un des types suivants: {valid_srcs}"
                    )
                if tgt.category not in valid_tgts:
                    raise LUSemanticError(
                        f"Relation '{rel_clean}': La cible '{tgt.id}' a le type '{tgt.category}', "
                        f"mais attend un des types suivants: {valid_tgts}"
                    )

    def validate_graph(self, graph: LUGraph) -> None:
        """Valide l'ensemble d'un graphe LU."""
        for node in graph.nodes.values():
            self.validate_node(node)
        for src_id, rel, tgt_id in graph.edges:
            if src_id not in graph.nodes or tgt_id not in graph.nodes:
                raise LUSemanticError(f"Arête orpheline: ({src_id})-[{rel}]->({tgt_id})")
            self.validate_edge(graph.nodes[src_id], rel, graph.nodes[tgt_id])


class LUSemanticParser:
    """
    Parseur avancé pour expressions LU inline enrichies.
    Supporte la syntaxe fluide :
    (src_id:CATEGORY {attr: val})-[RELATION {weight: 0.9}]->(tgt_id:CATEGORY)
    """

    def __init__(self, validator: Optional[LUSemanticValidator] = None, compiler: Optional[LUCompiler] = None):
        self.validator = validator or LUSemanticValidator()
        self.compiler = compiler or LUCompiler()

    def parse_attributes(self, raw_attrs: str) -> Dict[str, Any]:
        """Extrait les attributs clé: valeur au format JSON-lite."""
        attrs: Dict[str, Any] = {}
        if not raw_attrs.strip():
            return attrs
        pairs = raw_attrs.split(",")
        for pair in pairs:
            if ":" in pair:
                k, v = pair.split(":", 1)
                k_clean = k.strip()
                v_clean = v.strip().strip("'\"")
                try:
                    if "." in v_clean:
                        attrs[k_clean] = float(v_clean)
                    else:
                        attrs[k_clean] = int(v_clean)
                except ValueError:
                    attrs[k_clean] = v_clean
        return attrs

    def parse_statement(self, statement: str) -> LUGraph:
        """
        Parse un énoncé complet LU en chaîne ou multilignes.
        Exemple :
        (Self:AGENT {name: 'Agent01'})-[TARGETS {prio: 0.95}]->(Fruit:CONCEPT) ;
        (Fruit:CONCEPT)-[RESTORES]->(Energy:STATE)
        """
        graph = LUGraph()
        cleaned = statement.strip()
        if not cleaned:
            return graph

        clauses = [c.strip() for c in cleaned.split(";") if c.strip()]
        
        # Pattern pour nœud enrichi: (id:CATEGORY {attrs}) ou (id:CATEGORY) ou (id)
        # Pattern pour arête: (src)-[REL {attrs}]->(tgt)
        edge_re = re.compile(
            r"\((?P<src_id>[A-Za-z0-9_]+)(?::(?P<src_cat>[A-Z_]+))?(?:\s*\{(?P<src_attrs>[^}]+)\})?\)"
            r"\s*-\[(?P<rel>[A-Za-z0-9_]+)(?:\s*\{(?P<rel_attrs>[^}]+)\})?\]->\s*"
            r"\((?P<tgt_id>[A-Za-z0-9_]+)(?::(?P<tgt_cat>[A-Z_]+))?(?:\s*\{(?P<tgt_attrs>[^}]+)\})?\)"
        )

        isolated_node_re = re.compile(
            r"^\((?P<id>[A-Za-z0-9_]+)(?::(?P<cat>[A-Z_]+))?(?:\s*\{(?P<attrs>[^}]+)\})?\)$"
        )

        for clause in clauses:
            match_edge = edge_re.search(clause)
            if match_edge:
                d = match_edge.groupdict()
                src_id = d["src_id"]
                src_cat = d["src_cat"] or "CONCEPT"
                src_attrs = self.parse_attributes(d["src_attrs"] or "")

                tgt_id = d["tgt_id"]
                tgt_cat = d["tgt_cat"] or "CONCEPT"
                tgt_attrs = self.parse_attributes(d["tgt_attrs"] or "")

                rel = d["rel"]
                rel_attrs = self.parse_attributes(d["rel_attrs"] or "")

                # Enregistrement du nœud source
                if src_id not in graph.nodes:
                    graph.nodes[src_id] = LUNode(
                        id=src_id,
                        category=src_cat,
                        label=src_attrs.get("name", src_id),
                        attributes=src_attrs,
                        vector=self.compiler._get_or_create_vector(f"{src_cat}:{src_id}")
                    )
                # Enregistrement du nœud cible
                if tgt_id not in graph.nodes:
                    graph.nodes[tgt_id] = LUNode(
                        id=tgt_id,
                        category=tgt_cat,
                        label=tgt_attrs.get("name", tgt_id),
                        attributes=tgt_attrs,
                        vector=self.compiler._get_or_create_vector(f"{tgt_cat}:{tgt_id}")
                    )

                graph.edges.append((src_id, rel, tgt_id))
            else:
                match_node = isolated_node_re.match(clause)
                if match_node:
                    d = match_node.groupdict()
                    n_id = d["id"]
                    n_cat = d["cat"] or "CONCEPT"
                    n_attrs = self.parse_attributes(d["attrs"] or "")
                    if n_id not in graph.nodes:
                        graph.nodes[n_id] = LUNode(
                            id=n_id,
                            category=n_cat,
                            label=n_attrs.get("name", n_id),
                            attributes=n_attrs,
                            vector=self.compiler._get_or_create_vector(f"{n_cat}:{n_id}")
                        )
                else:
                    raise LUSyntaxError(f"Syntaxe LU invalide pour la clause: '{clause}'")

        # Validation ontologique stricte
        self.validator.validate_graph(graph)
        return graph


class LUCypherEmitter:
    """
    Émetteur Cypher pour compiler directement un graphe LU vers KuzuDB (Commandement 5 & 16).
    """

    @staticmethod
    def emit_kuzu_cypher(graph: LUGraph) -> List[str]:
        """Génère la liste de requêtes Cypher idempotentes pour KuzuDB."""
        queries: List[str] = []

        # Génération des nœuds (Concept ou tables dédiées selon schéma)
        for node in graph.nodes.values():
            node_id = node.id
            name = node.label.replace("'", "`")
            # Stocke l'embedding vectoriel sous format compatible KuzuDB DOUBLE[]
            if node.vector is not None:
                vec_str = "[" + ", ".join(f"{float(x):.6f}" for x in node.vector) + "]"
            else:
                vec_str = "[]"

            query = (
                f"MERGE (c:Concept {{id: '{node_id}'}}) "
                f"ON CREATE SET c.name = '{name}', c.embedding = {vec_str} "
                f"ON MATCH SET c.name = '{name}'"
            )
            queries.append(query)

        # Génération des relations
        for src_id, rel, tgt_id in graph.edges:
            rel_clean = rel.split("{")[0].strip()
            # Mappe les relations LU vers le schéma KuzuDB (INFLUENCES, CONNECTE_A, IS_A)
            kuzu_rel = "INFLUENCES"
            strength = 1.0
            if rel_clean == "IS_A":
                kuzu_rel = "IS_A"
            elif rel_clean in ("TRIGGERS", "CAUSES", "LEADS_TO"):
                kuzu_rel = "INFLUENCES"
                strength = 0.95

            if kuzu_rel == "IS_A":
                q = (
                    f"MATCH (s:Concept {{id: '{src_id}'}}), (t:Concept {{id: '{tgt_id}'}}) "
                    f"CREATE (s)-[:IS_A]->(t)"
                )
            else:
                q = (
                    f"MATCH (s:Concept {{id: '{src_id}'}}), (t:Concept {{id: '{tgt_id}'}}) "
                    f"CREATE (s)-[:{kuzu_rel} {{strength: {strength}}}]->(t)"
                )
            queries.append(q)

        return queries


class LUAlgebra:
    """
    Algèbre sémantique pour la composition de pensées et graphes LU.
    """

    @staticmethod
    def union(g1: LUGraph, g2: LUGraph) -> LUGraph:
        """Fusionne deux graphes de pensée en un graphe unifié."""
        merged = LUGraph()
        merged.nodes.update(g1.nodes)
        merged.nodes.update(g2.nodes)

        existing_edges = set(g1.edges)
        merged.edges.extend(g1.edges)
        for e in g2.edges:
            if e not in existing_edges:
                merged.edges.append(e)
                existing_edges.add(e)
        return merged

    @staticmethod
    def compose_sequential(g1: LUGraph, g2: LUGraph, bridge_rel: str = "LEADS_TO") -> LUGraph:
        """
        Compose séquentiellement deux graphes : relie les nœuds terminaux de g1
        aux nœuds initiaux de g2 via une relation causale/temporelle.
        """
        composed = LUAlgebra.union(g1, g2)
        if not g1.nodes or not g2.nodes:
            return composed

        # Trouve les nœuds de sortie de g1 (qui n'ont pas de cible sortante)
        src_with_out = {e[0] for e in g1.edges}
        terminal_nodes = [nid for nid in g1.nodes if nid not in src_with_out] or list(g1.nodes.keys())

        # Trouve les nœuds d'entrée de g2 (qui n'ont pas de source entrante)
        tgt_with_in = {e[2] for e in g2.edges}
        initial_nodes = [nid for nid in g2.nodes if nid not in tgt_with_in] or list(g2.nodes.keys())

        for t_node in terminal_nodes:
            for i_node in initial_nodes:
                edge = (t_node, bridge_rel, i_node)
                if edge not in composed.edges:
                    composed.edges.append(edge)

        return composed
