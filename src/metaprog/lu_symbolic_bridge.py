"""
src/metaprog/lu_symbolic_bridge.py — Pont Symbolique-Neuronal entre LangGraph, KuzuDB et Gigatokens LU (Phase 2 - Jalon M3).

Conforme aux 12 Commandements AGIseed :
- 1. Flexible : Configurable via LUSymbolicBridgeConfig.
- 2. Modulaire : Découplage strict entre la base de graphe symbolique et les tenseurs continus.
- 5. Transparent & Auditable : Enregistre le dictionnaire évolutif de lexèmes dans KuzuDB.
- 8. Extensible : Permet l'injection descendante de directives LangGraph vers les agents.
- 9. Stabilité Numérique : Vecteurs normalisés sur la sphère unité S^{D-1}.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from pathlib import Path

from src.metaprog.lu_algebra import LUCompositionalGrammar, LUAlgebraConfig, cosine_similarity, bundle_vectors
from src.graph_rag.database import KuzuDatabase, DatabaseConfig
from src.graph_rag.async_logger import logger


@dataclass
class LUSharedDream:
    """Modèle de persistance pour un rêve sémantique partagé dans KuzuDB (Phase 11 M1)."""
    id: str
    creator_id: str
    target_goal: str
    counterfactual_gain: float
    is_ratified: bool = False
    tick: int = 0


@dataclass
class LUCounterfactualRollout:
    """Modèle de persistance pour une trajectoire contrefactuelle déroulée (Phase 11 M1)."""
    id: str
    dream_id: str
    horizon: int
    ceg_score: float
    is_fatal: bool = False
    tick: int = 0


@dataclass
class LUSymbolicBridgeConfig:
    """Configuration du pont symbolique-neuronal LU."""
    dim: int = 16
    db_path: Optional[str] = None
    similarity_match_threshold: float = 0.25
    seed: int = 42


class LUSymbolicBridge:
    """
    Assure l'interface bidirectionnelle entre le monde symbolique (KuzuDB/LangGraph)
    et le monde neuro-continu (Gigatokens LU) :
    1. Top-Down : Traduit une consigne humaine ou de superviseur en Gigatoken composite.
    2. Bottom-Up : Indexe et décompile les vecteurs latents émergents en lexèmes auditables.
    """

    def __init__(self, config: Optional[LUSymbolicBridgeConfig] = None, db: Optional[KuzuDatabase] = None):
        self.config = config or LUSymbolicBridgeConfig()
        self.dim = self.config.dim
        self.grammar = LUCompositionalGrammar(LUAlgebraConfig(dim=self.dim, seed=self.config.seed))
        
        # Connexion KuzuDB optionnelle (robuste si pas de base active)
        self.db = db
        if self.db is None and self.config.db_path:
            try:
                self.db = KuzuDatabase(DatabaseConfig(db_path=self.config.db_path))
                self._ensure_schema()
            except Exception as e:
                logger.warning(f"LUSymbolicBridge: Mode mémoire pur (KuzuDB non initialisé: {e})")
                self.db = None

        # Dictionnaire mémoire de lexèmes canoniques (pour calculs sub-milliseconde)
        self.lexicon: Dict[str, Dict[str, Any]] = {}
        self._init_canonical_lexemes()

    def _ensure_schema(self):
        """Assure que la table LULexeme existe dans KuzuDB."""
        if self.db is None:
            return
        query = "CREATE NODE TABLE LULexeme (id STRING, label STRING, category STRING, usage_count INT64, PRIMARY KEY (id))"
        try:
            self.db.execute_cypher(query)
        except Exception:
            pass  # Déjà existant

    def _init_canonical_lexemes(self):
        """Initialise les concepts de base du langage de la biosphère."""
        rng = np.random.default_rng(self.config.seed)
        
        concepts = {
            # Sujets
            "AGENT": ("SUBJECT", 1.0),
            "TRIBE": ("SUBJECT", 1.0),
            "SCOUT": ("SUBJECT", 1.0),
            "HUNTER": ("SUBJECT", 1.0),
            "CRAFTER": ("SUBJECT", 1.0),
            # Prédicats
            "HUNT": ("PREDICATE", 1.0),
            "GATHER": ("PREDICATE", 1.0),
            "CRAFT": ("PREDICATE", 1.0),
            "DEFEND": ("PREDICATE", 1.0),
            "REST": ("PREDICATE", 0.5),
            "INFORMS": ("PREDICATE", 1.0),
            "BELIEVES": ("PREDICATE", 1.0),
            "DELIBERATE": ("PREDICATE", 1.0),
            # Cibles
            "PREY": ("TARGET", 1.0),
            "FOOD": ("TARGET", 1.0),
            "FIRE": ("TARGET", 1.0),
            "GRANARY": ("TARGET", 1.0),
            "FURNACE": ("TARGET", 1.0),
            "SHELTER": ("TARGET", 1.0),
            "EXPEDITION": ("TARGET", 1.0),
            "WOOD": ("TARGET", 0.8),
            "STONE": ("TARGET", 0.8),
            # Phase 4 : Lexèmes de troc et contrats de marché (placés à la fin pour préserver le tirage RNG)
            "TRADE": ("PREDICATE", 1.0),
            "BARTER": ("PREDICATE", 1.0),
            "OFFER": ("PREDICATE", 1.0),
            "GRAIN": ("TARGET", 1.0),
            "FRUIT": ("TARGET", 1.0),
            "SPEAR": ("TARGET", 1.0),
            "TOOL": ("TARGET", 1.0),
            # Phase 5 : Gouvernance juridique, arbitrage & métallurgie du Monde 3
            "ORE": ("TARGET", 1.0),
            "COAL": ("TARGET", 1.0),
            "STEEL": ("TARGET", 1.0),
            "INGOT": ("TARGET", 1.0),
            "PICKAXE": ("TARGET", 1.0),
            "SANCTION": ("PREDICATE", 1.0),
            "TRUST": ("TARGET", 1.0),
            "LAW": ("TARGET", 1.0),
            # Phase 6 : Écriture stigmargique, arithmétique vectorielle & sciences
            "INSCRIPTION": ("TARGET", 1.0),
            "TABLET": ("TARGET", 1.0),
            "STELE": ("TARGET", 1.0),
            "RATIO": ("PREDICATE", 1.0),
            "RECIPE": ("TARGET", 1.0),
            "NUMBER": ("MODIFIER", 1.0),
            "READ": ("ACTION", 1.0),
            "WRITE": ("ACTION", 1.0),
            "SCIENCE": ("TARGET", 1.0),
            "DEBT": ("TARGET", 1.0),
            "CREDIT": ("TARGET", 1.0),
            # Phase 7 : Métalangage RSI, Preuve Formelle & Diplomatie Fédérale
            "DEFINE_ROLE": ("META", 1.0),
            "AXIOM": ("META", 1.0),
            "THEOREM": ("META", 1.0),
            "CONTRADICTION": ("META", 1.0),
            "FEDERAL_TREATY": ("TREATY", 1.0),
            "CONSTITUTION": ("TREATY", 1.0),
            "PEACE": ("TREATY", 1.0),
            "FEDERATION": ("TREATY", 1.0),
            # Phase 8 : Neural VM, Do-Calculus & Consensus BFT
            "EXECUTE_CONTRACT": ("ACTION", 1.0),
            "DO_INTERVENE": ("CAUSAL", 1.0),
            "CAUSAL_TEST": ("CAUSAL", 1.0),
            "BFT_CONSENSUS": ("CONSENSUS", 1.0),
            "ESCROW": ("TARGET", 1.0),
            "NEURAL_VM": ("META", 1.0),
            # Phase 9 : Synthèse de Programmes Latents, LTL & Analogies Multivers
            "SYNTHESIZE_PROGRAM": ("ACTION", 1.0),
            "TEMPORAL_ASSERT": ("TEMPORAL", 1.0),
            "TRANSFER_ANALOGY": ("ACTION", 1.0),
            "LOOP": ("META", 1.0),
            "BRANCH": ("META", 1.0),
            "NEXT": ("TEMPORAL", 1.0),
            "ALWAYS": ("TEMPORAL", 1.0),
            "EVENTUALLY": ("TEMPORAL", 1.0),
            # Phase 10 : Auto-Compilation Récursive, Logique de Hoare & Seed AI
            "SELF_COMPILE_CONNECTOME": ("ACTION", 1.0),
            "HOARE_ASSERT": ("META", 1.0),
            "DISASSEMBLE": ("ACTION", 1.0),
            "INSPECT_WEIGHTS": ("ACTION", 1.0),
            "PRECONDITION": ("META", 1.0),
            "POSTCONDITION": ("META", 1.0),
            # Phase 11 : Méta-Simulation Contrefactuelle & Rêve Sémantique Partagé
            "DREAM_SCENARIO": ("ACTION", 1.0),
            "WHAT_IF": ("MODIFIER", 1.0),
            "ROLLOUT_ASSERT": ("META", 1.0),
            "EVALUATE_DREAM": ("ACTION", 1.0),
            "CAMPFIRE_COUNCIL": ("CONCEPT", 1.0),
        }
        
        for name, (cat, weight) in concepts.items():
            vec = rng.normal(0, 1.0, self.dim).astype(np.float32)
            vec /= (np.linalg.norm(vec) + 1e-12)
            self.lexicon[name] = {
                "id": f"lex_{name.lower()}",
                "label": name,
                "category": cat,
                "vector": vec,
                "weight": weight,
                "usage_count": 0
            }

    def register_emergent_lexeme(self, label: str, category: str, vector: np.ndarray) -> str:
        """Enregistre un nouveau lexème émergent en mémoire et dans KuzuDB."""
        v_norm = (vector / (np.linalg.norm(vector) + 1e-12)).astype(np.float32)
        lex_id = f"lex_{label.lower()}_{len(self.lexicon)}"
        
        self.lexicon[label.upper()] = {
            "id": lex_id,
            "label": label.upper(),
            "category": category,
            "vector": v_norm,
            "weight": 1.0,
            "usage_count": 1
        }
        
        if self.db is not None:
            try:
                q = f"CREATE (l:LULexeme {{id: '{lex_id}', label: '{label.upper()}', category: '{category}', usage_count: 1}})"
                self.db.execute_cypher(q)
            except Exception as e:
                logger.debug(f"Persistence LULexeme ignorée : {e}")
                
        return lex_id

    def compile_directive_to_gigatoken(self, directive_text: str) -> np.ndarray:
        """
        Top-Down : Traduit une consigne symbolique en Gigatoken composite pour la biosphère.
        Ex: 'TRIBE GATHER GRANARY' -> compose(TRIBE, GATHER, GRANARY)
        """
        words = [w.strip().upper() for w in directive_text.replace(",", " ").split() if w.strip()]
        
        subj = None
        pred = None
        tgt = None

        for w in words:
            if w in self.lexicon:
                cat = self.lexicon[w]["category"]
                vec = self.lexicon[w]["vector"]
                if cat == "SUBJECT" and subj is None:
                    subj = vec
                elif cat == "PREDICATE" and pred is None:
                    pred = vec
                elif cat == "TARGET" and tgt is None:
                    tgt = vec

        # Défauts si non spécifié
        if subj is None:
            subj = self.lexicon.get("TRIBE", {}).get("vector", np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim))
        if pred is None:
            pred = self.lexicon.get("GATHER", {}).get("vector", np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim))

        return self.grammar.compose(subject=subj, predicate=pred, target=tgt)

    def compile_recursive_directive(self, outer_directive: str, inner_directive: str) -> np.ndarray:
        """
        Top-Down Récursif (Phase 3 M1) :
        Compose une proposition enveloppante englobant une sous-clause complète.
        Ex: outer='SCOUT INFORMS', inner='PREY HUNT SHELTER'.
        """
        inner_token = self.compile_directive_to_gigatoken(inner_directive)
        words_out = [w.strip().upper() for w in outer_directive.replace(",", " ").split() if w.strip()]

        s_out = None
        p_out = None
        for w in words_out:
            if w in self.lexicon:
                cat = self.lexicon[w]["category"]
                vec = self.lexicon[w]["vector"]
                if cat == "SUBJECT" and s_out is None:
                    s_out = vec
                elif cat == "PREDICATE" and p_out is None:
                    p_out = vec

        if s_out is None:
            s_out = self.lexicon.get("SCOUT", {}).get("vector", np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim))
        if p_out is None:
            p_out = self.lexicon.get("INFORMS", {}).get("vector", np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim))

        return self.grammar.compose_hierarchical(outer_subject=s_out, outer_predicate=p_out, inner_proposition=inner_token)

    def decode_gigatoken_to_symbolic(self, token: np.ndarray) -> Dict[str, Any]:
        """
        Bottom-Up : Trouve les lexèmes les plus proches par décomposition sémantique.
        """
        sub_vec = self.grammar.extract_subject(token)
        pred_vec = self.grammar.extract_predicate(token)
        tgt_vec = self.grammar.extract_target(token)

        def best_match(query_vec: np.ndarray, cat: str) -> Tuple[str, float]:
            best_label = "INCONNU"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                if data["category"] == cat:
                    sim = cosine_similarity(query_vec, data["vector"])
                    if sim > best_sim:
                        best_sim = sim
                        best_label = name
            return best_label, best_sim

        best_subj, sim_s = best_match(sub_vec, "SUBJECT")
        best_pred, sim_p = best_match(pred_vec, "PREDICATE")
        best_tgt, sim_t = best_match(tgt_vec, "TARGET")

        return {
            "subject": best_subj if sim_s >= self.config.similarity_match_threshold else "UNKNOWN_SUBJECT",
            "predicate": best_pred if sim_p >= self.config.similarity_match_threshold else "UNKNOWN_PREDICATE",
            "target": best_tgt if sim_t >= self.config.similarity_match_threshold else "UNKNOWN_TARGET",
            "scores": {
                "subject_sim": round(sim_s, 3),
                "predicate_sim": round(sim_p, 3),
                "target_sim": round(sim_t, 3),
            }
        }

    def decode_recursive_gigatoken(self, token: np.ndarray) -> Dict[str, Any]:
        """
        Bottom-Up Récursif (Phase 3 M1) :
        Décompose une proposition hiérarchique en constituants externes et sous-clause interne.
        """
        s_out_vec, p_out_vec, inner_vec = self.grammar.extract_hierarchical(token)

        def best_match(query_vec: np.ndarray, cat: str) -> Tuple[str, float]:
            best_label = "INCONNU"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                if data["category"] == cat:
                    sim = cosine_similarity(query_vec, data["vector"])
                    if sim > best_sim:
                        best_sim = sim
                        best_label = name
            return best_label, best_sim

        outer_s, sim_os = best_match(s_out_vec, "SUBJECT")
        outer_p, sim_op = best_match(p_out_vec, "PREDICATE")
        inner_decoded = self.decode_gigatoken_to_symbolic(inner_vec)

        return {
            "outer_subject": outer_s,
            "outer_predicate": outer_p,
            "outer_scores": {"subject_sim": round(sim_os, 3), "predicate_sim": round(sim_op, 3)},
            "inner_clause": inner_decoded,
        }

    def register_deliberation_consensus(
        self,
        deliberation_id: str,
        topic: str,
        participants: List[str],
        consensus_vector: np.ndarray,
        rounds: int = 3,
        agreement_score: float = 0.85
    ) -> str:
        """
        Consigne un consensus délibéré au coin du feu dans la mémoire Lattice KuzuDB (Phase 3 M3).
        """
        v_norm = (consensus_vector / (np.linalg.norm(consensus_vector) + 1e-12)).astype(np.float32)
        decoded = self.decode_gigatoken_to_symbolic(v_norm)
        summary = f"{decoded['subject']} {decoded['predicate']} {decoded['target']}"

        if self.db is not None:
            try:
                # Création table LUDeliberation si nécessaire
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUDeliberation (id STRING, topic STRING, summary STRING, rounds INT64, agreement_score DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                topic_safe = topic.replace("'", "\\'")
                summary_safe = summary.replace("'", "\\'")
                q = (
                    f"CREATE (d:LUDeliberation {{id: '{deliberation_id}', topic: '{topic_safe}', "
                    f"summary: '{summary_safe}', rounds: {rounds}, agreement_score: {agreement_score}}})"
                )
                self.db.execute_cypher(q)
            except Exception as e:
                logger.debug(f"Persistence LUDeliberation ignorée : {e}")

        return summary

    def compile_trade_contract(
        self,
        give_item: str,
        demand_item: str,
        quorum_val: float = 1.0
    ) -> np.ndarray:
        """
        Compile un contrat de troc bilatéral en Gigatoken (Phase 4 M2) :
        ex: give='GRAIN', demand='TOOL'.
        """
        give_key = give_item.strip().upper()
        demand_key = demand_item.strip().upper()

        give_vec = self.lexicon.get(give_key, {}).get("vector")
        if give_vec is None:
            give_vec = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)

        demand_vec = self.lexicon.get(demand_key, {}).get("vector")
        if demand_vec is None:
            demand_vec = np.ones(self.dim, dtype=np.float32) / np.sqrt(self.dim)

        quorum_vec = np.full(self.dim, float(quorum_val) / 5.0, dtype=np.float32)
        quorum_vec /= (np.linalg.norm(quorum_vec) + 1e-12)

        return self.grammar.compose_contract(give_vec, demand_vec, quorum_vec)

    def decode_trade_contract(self, token: np.ndarray) -> Dict[str, Any]:
        """
        Décompilation ascendante d'un contrat de troc latent :
        Identifie les ressources offertes et exigées.
        """
        give_vec, demand_vec = self.grammar.extract_contract(token)

        def best_match(query_vec: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = cosine_similarity(query_vec, data["vector"])
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        give_label, sim_g = best_match(give_vec)
        demand_label, sim_d = best_match(demand_vec)

        return {
            "give": give_label,
            "give_sim": round(sim_g, 3),
            "demand": demand_label,
            "demand_sim": round(sim_d, 3),
            "is_valid": (sim_g >= 0.40 and sim_d >= 0.40),
        }

    def compile_consortium_contract(
        self,
        wood_concept: str = "WOOD",
        food_concept: str = "FOOD",
        ore_concept: str = "ORE",
        product_concept: str = "STEEL"
    ) -> np.ndarray:
        """
        Compile un contrat tripartite de consortium pour la métallurgie (Phase 5 M3).
        """
        def get_v(c: str) -> np.ndarray:
            key = c.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        v_wood = get_v(wood_concept)
        v_food = get_v(food_concept)
        v_ore = get_v(ore_concept)
        v_prod = get_v(product_concept)

        return self.grammar.compose_consortium_contract(v_wood, v_food, v_ore, v_prod)

    def decode_consortium_contract(self, token: np.ndarray) -> Dict[str, Any]:
        """
        Décompile un token de consortium tripartite en concepts auditables.
        """
        v_wood = self.grammar.extract_consortium_part(token, self.grammar.ROLE_SUPPLIER_WOOD)
        v_food = self.grammar.extract_consortium_part(token, self.grammar.ROLE_SUPPLIER_FOOD)
        v_ore = self.grammar.extract_consortium_part(token, self.grammar.ROLE_SMELTER_ORE)
        v_prod = self.grammar.extract_consortium_part(token, self.grammar.ROLE_FORGE_OUTPUT)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = cosine_similarity(qv, data["vector"])
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        w_name, w_sim = best_match(v_wood)
        f_name, f_sim = best_match(v_food)
        o_name, o_sim = best_match(v_ore)
        p_name, p_sim = best_match(v_prod)

        return {
            "wood": w_name,
            "wood_sim": round(w_sim, 3),
            "food": f_name,
            "food_sim": round(f_sim, 3),
            "ore": o_name,
            "ore_sim": round(o_sim, 3),
            "product": p_name,
            "product_sim": round(p_sim, 3),
            "is_valid": (w_sim >= 0.35 and f_sim >= 0.35 and o_sim >= 0.35),
        }

    def register_trade_contract(
        self,
        contract_id: str,
        party_a: str,
        party_b: str,
        give_item: str,
        demand_item: str,
        agreement_score: float,
        settled: bool = True
    ) -> bool:
        """
        Consigne un contrat de troc dans la table LUContract de KuzuDB (Phase 4 M3).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUContract (id STRING, party_a STRING, party_b STRING, "
                    "give_item STRING, demand_item STRING, agreement_score DOUBLE, settled BOOLEAN, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (c:LUContract {{id: '{contract_id}', party_a: '{party_a}', party_b: '{party_b}', "
                    f"give_item: '{give_item}', demand_item: '{demand_item}', agreement_score: {agreement_score}, settled: {str(settled).lower()}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUContract ignorée : {e}")
        return False

    def register_clan_dialect(
        self,
        dialect_id: str,
        clan_name: str,
        grassmann_divergence: float,
        speakers_count: int
    ) -> bool:
        """
        Consigne les métriques de dialecte de clan dans la table LUDialect de KuzuDB.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUDialect (id STRING, clan_name STRING, "
                    "grassmann_divergence DOUBLE, speakers_count INT64, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (d:LUDialect {{id: '{dialect_id}', clan_name: '{clan_name}', "
                    f"grassmann_divergence: {grassmann_divergence}, speakers_count: {speakers_count}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUDialect ignorée : {e}")
        return False

    def register_legal_rule(
        self,
        rule_id: str,
        title: str,
        description: str,
        quorum_threshold: float = 0.60
    ) -> bool:
        """
        Consigne une règle de droit coutumier dans la table LULaw de KuzuDB (Phase 5 M3).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LULaw (id STRING, title STRING, "
                    "description STRING, quorum_threshold DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (l:LULaw {{id: '{rule_id}', title: '{title}', "
                    f"description: '{description}', quorum_threshold: {quorum_threshold}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LULaw ignorée : {e}")
        return False

    def register_sanction_event(
        self,
        sanction_id: str,
        agent_id: str,
        reason: str,
        penalty: float = 1.0
    ) -> bool:
        """
        Consigne un arbitrage / sanction dans la table LUSanction de KuzuDB (Phase 5 M3).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUSanction (id STRING, agent_id STRING, "
                    "reason STRING, penalty DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (s:LUSanction {{id: '{sanction_id}', agent_id: '{agent_id}', "
                    f"reason: '{reason}', penalty: {penalty}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUSanction ignorée : {e}")
        return False

    def register_consortium(
        self,
        consortium_id: str,
        name: str,
        members_count: int,
        output_product: str,
        surplus_energy: float
    ) -> bool:
        """
        Consigne un traité de consortium métallurgique dans la table LUConsortium de KuzuDB (Phase 5 M3).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUConsortium (id STRING, name STRING, "
                    "members_count INT64, output_product STRING, surplus_energy DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (c:LUConsortium {{id: '{consortium_id}', name: '{name}', "
                    f"members_count: {members_count}, output_product: '{output_product}', surplus_energy: {surplus_energy}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUConsortium ignorée : {e}")
        return False

    def register_scripture(
        self,
        scripture_id: str,
        stele_type: str,
        topic: str,
        content_summary: str,
        author_id: str,
        creation_tick: int = 0
    ) -> bool:
        """
        Consigne une inscription stigmargique durable dans la table LUScripture de KuzuDB (Phase 6 M1/M2).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUScripture (id STRING, stele_type STRING, "
                    "topic STRING, content_summary STRING, author_id STRING, creation_tick INT64, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (s:LUScripture {{id: '{scripture_id}', stele_type: '{stele_type}', "
                    f"topic: '{topic}', content_summary: '{content_summary}', author_id: '{author_id}', creation_tick: {creation_tick}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUScripture ignorée : {e}")
        return False

    def register_mathematics_record(
        self,
        math_id: str,
        operation_type: str,
        input_values: str,
        result_value: str
    ) -> bool:
        """
        Consigne une transaction comptable ou opération arithmétique dans LUMathematics (Phase 6 M1/M2).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUMathematics (id STRING, operation_type STRING, "
                    "input_values STRING, result_value STRING, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (m:LUMathematics {{id: '{math_id}', operation_type: '{operation_type}', "
                    f"input_values: '{input_values}', result_value: '{result_value}'}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUMathematics ignorée : {e}")
        return False

    def register_science_theorem(
        self,
        theorem_id: str,
        theorem_name: str,
        domain: str,
        formula_dsl: str
    ) -> bool:
        """
        Consigne un théorème ou loi causale empirique dans LUScience (Phase 6 M3).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUScience (id STRING, theorem_name STRING, "
                    "domain STRING, formula_dsl STRING, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (sc:LUScience {{id: '{theorem_id}', theorem_name: '{theorem_name}', "
                    f"domain: '{domain}', formula_dsl: '{formula_dsl}'}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUScience ignorée : {e}")
        return False

    def compile_recipe_directive(
        self,
        inputs: List[Tuple[float, str]],
        outputs: List[Tuple[float, str]]
    ) -> np.ndarray:
        """
        Compile une recette stœchiométrique symbolique en vecteur ratio HRR quantifié.
        Ex: inputs=[(3.0, "WOOD"), (1.0, "ORE")], outputs=[(1.0, "INGOT")]
        """
        in_vectors = []
        for q, label in inputs:
            vec = self.lexicon.get(label.upper(), {}).get("vector")
            if vec is None:
                vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(label)) % (2**31 - 1)))
            in_vectors.append((float(q), vec))

        out_vectors = []
        for q, label in outputs:
            vec = self.lexicon.get(label.upper(), {}).get("vector")
            if vec is None:
                vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(label)) % (2**31 - 1)))
            out_vectors.append((float(q), vec))

        return self.grammar.compose_recipe_ratio(in_vectors, out_vectors)

    def compile_inscription_directive(
        self,
        topic: str,
        content_text: str,
        author_id: Optional[str] = None
    ) -> np.ndarray:
        """
        Compile une inscription stigmargique complète en vecteur gravable sur stèle.
        """
        topic_vec = self.lexicon.get(topic.upper(), {}).get("vector")
        if topic_vec is None:
            topic_vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(topic)) % (2**31 - 1)))

        content_vec = self.compile_directive_to_gigatoken(content_text)

        author_vec = None
        if author_id:
            rng_a = np.random.default_rng(abs(hash(author_id)) % (2**31 - 1))
            author_vec = self.grammar._generate_canonical_unit_vector(rng_a)

        return self.grammar.compose_inscription(topic_vec, content_vec, author_vec)

    def decode_inscription_vector(self, inscription_vector: np.ndarray) -> Dict[str, Any]:
        """
        Lit et décode un vecteur gravé d'inscription stigmargique.
        Extrait le topic le plus proche et le contenu décompilé.
        """
        t_vec = self.grammar.extract_inscription_topic(inscription_vector)
        c_vec = self.grammar.extract_inscription_content(inscription_vector)

        # Match du topic avec le lexique
        best_topic = "UNKNOWN"
        best_sim = -1.0
        for name, data in self.lexicon.items():
            sim = float(cosine_similarity(t_vec, data["vector"]))
            if sim > best_sim:
                best_sim = sim
                best_topic = name

        content_decompiled = self.decompile_gigatoken_to_dsl(c_vec)

        return {
            "topic": best_topic,
            "topic_confidence": round(best_sim, 3),
            "content_dsl": content_decompiled.get("dsl", ""),
            "matched_lexemes": content_decompiled.get("matched_lexemes", []),
        }

    # =========================================================================
    # Méthodes Métasémantiques, Preuve et Fédération KuzuDB (Phase 7 M1)
    # =========================================================================

    def register_meta_grammar_rule(
        self,
        rule_id: str,
        rule_name: str,
        input_role: str,
        operator: str,
        output_role: str,
    ) -> bool:
        """
        Consigne une règle métagrammaticale d'ordre supérieur dans LUMetaGrammar (Phase 7 M1).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUMetaGrammar (id STRING, rule_name STRING, "
                    "input_role STRING, operator STRING, output_role STRING, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (mg:LUMetaGrammar {{id: '{rule_id}', rule_name: '{rule_name}', "
                    f"input_role: '{input_role}', operator: '{operator}', output_role: '{output_role}'}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUMetaGrammar ignorée : {e}")
        return False

    def register_proof_check(
        self,
        check_id: str,
        theorem_id: str,
        is_consistent: bool,
        min_similarity: float,
        conflict_count: int,
    ) -> bool:
        """
        Consigne le résultat d'un contrôle de consistance logique vectoriel dans LUProofCheck.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUProofCheck (id STRING, theorem_id STRING, "
                    "is_consistent BOOLEAN, min_similarity DOUBLE, conflict_count INT64, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                consistent_str = "true" if is_consistent else "false"
                q = (
                    f"CREATE (pc:LUProofCheck {{id: '{check_id}', theorem_id: '{theorem_id}', "
                    f"is_consistent: {consistent_str}, min_similarity: {min_similarity}, conflict_count: {conflict_count}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUProofCheck ignorée : {e}")
        return False

    def register_federal_treaty(
        self,
        treaty_id: str,
        treaty_name: str,
        clause_summary: str,
        signatories: List[str],
    ) -> bool:
        """
        Consigne un traité constitutionnel fédéral inter-mondes dans LUFederalTreaty.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUFederalTreaty (id STRING, treaty_name STRING, "
                    "clause_summary STRING, signatories STRING, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                sigs_str = ";".join(signatories)
                q = (
                    f"CREATE (ft:LUFederalTreaty {{id: '{treaty_id}', treaty_name: '{treaty_name}', "
                    f"clause_summary: '{clause_summary}', signatories: '{sigs_str}'}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUFederalTreaty ignorée : {e}")
        return False

    def compile_meta_rule_directive(
        self,
        rule_name: str,
        input_role: str,
        operator: str,
        output_role: str,
    ) -> np.ndarray:
        """
        Compile une règle métagrammaticale symbolique en Gigatoken d'ordre supérieur.
        """
        name_vec = self.lexicon.get(rule_name.upper(), {}).get("vector")
        if name_vec is None:
            name_vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(rule_name)) % (2**31 - 1)))

        in_vec = self.lexicon.get(input_role.upper(), {}).get("vector")
        if in_vec is None:
            in_vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(input_role)) % (2**31 - 1)))

        op_vec = self.lexicon.get(operator.upper(), {}).get("vector")
        if op_vec is None:
            op_vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(operator)) % (2**31 - 1)))

        out_vec = self.lexicon.get(output_role.upper(), {}).get("vector")
        if out_vec is None:
            out_vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(output_role)) % (2**31 - 1)))

        return self.grammar.compose_meta_rule(name_vec, in_vec, op_vec, out_vec)

    def compile_federal_treaty_directive(
        self,
        clause_text: str,
        signatory_names: List[str],
    ) -> np.ndarray:
        """
        Compile un traité fédéral symbolique multilatéral en Gigatoken constitutionnel.
        """
        clause_vec = self.lexicon.get(clause_text.upper(), {}).get("vector")
        if clause_vec is None:
            clause_decomp = self.compile_directive_to_gigatoken(clause_text)
            clause_vec = clause_decomp

        sigs = []
        for name in signatory_names:
            sig_vec = self.lexicon.get(name.upper(), {}).get("vector")
            if sig_vec is None:
                sig_vec = self.grammar._generate_canonical_unit_vector(np.random.default_rng(abs(hash(name)) % (2**31 - 1)))
            sigs.append(sig_vec)

        return self.grammar.compose_federal_treaty(clause_vec, sigs)

    def decode_meta_rule_vector(self, meta_rule_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile une métarègle vectorielle en composantes symboliques.
        """
        comps = self.grammar.extract_meta_rule_components(meta_rule_vector)
        res = {}
        for k, v in comps.items():
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(v, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            res[k] = best_label
            res[f"{k}_confidence"] = round(best_sim, 3)
        return res

    def decode_federal_treaty_vector(self, treaty_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile un traité fédéral vectoriel : clause constitutionnelle et signataires reconnus.
        """
        clause_vec = self.grammar.extract_treaty_clause(treaty_vector)
        clause_decomp = self.decompile_gigatoken_to_dsl(clause_vec)

        signatory_clause = self.grammar.query_role(treaty_vector, self.grammar.ROLE_TREATY_SIGNATORY)
        matched_signatories = []
        for name, data in self.lexicon.items():
            sim = float(cosine_similarity(signatory_clause, data["vector"]))
            if sim >= self.config.similarity_match_threshold:
                matched_signatories.append((name, round(sim, 3)))

        return {
            "clause_dsl": clause_decomp.get("dsl", ""),
            "matched_signatories": matched_signatories,
        }

    # =========================================================================
    # Méthodes Neural VM, Do-Calculus & Consensus BFT (LU Phase 8 M1)
    # =========================================================================

    def register_neural_vm_state(
        self,
        vm_id: str,
        state_label: str,
        trigger_label: str,
        target_state_label: str,
        escrow_action: Optional[str] = None
    ) -> bool:
        """
        Consigne un état ou transition de la Machine Virtuelle Latente dans LUNeuralVM.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUNeuralVM (id STRING, state_label STRING, "
                    "trigger_label STRING, target_state_label STRING, escrow_action STRING, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                esc_str = escrow_action or "NONE"
                q = (
                    f"CREATE (vm:LUNeuralVM {{id: '{vm_id}', state_label: '{state_label}', "
                    f"trigger_label: '{trigger_label}', target_state_label: '{target_state_label}', "
                    f"escrow_action: '{esc_str}'}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUNeuralVM ignorée : {e}")
        return False

    def register_causal_inference(
        self,
        inference_id: str,
        cause_label: str,
        effect_label: str,
        ate_score: float,
        r_obs: float,
        discrepancy: float
    ) -> bool:
        """
        Consigne une inférence ou test expérimental causal dans LUCausalInference.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUCausalInference (id STRING, cause_label STRING, "
                    "effect_label STRING, ate_score DOUBLE, r_obs DOUBLE, discrepancy DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (ci:LUCausalInference {{id: '{inference_id}', cause_label: '{cause_label}', "
                    f"effect_label: '{effect_label}', ate_score: {ate_score}, r_obs: {r_obs}, discrepancy: {discrepancy}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUCausalInference ignorée : {e}")
        return False

    def register_bft_consensus(
        self,
        consensus_id: str,
        topic: str,
        agreement_score: float,
        honest_count: int,
        byzantine_count: int,
        byzantine_ids: str
    ) -> bool:
        """
        Consigne un résultat de consensus sphérique byzantin dans LUBFTConsensus.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUBFTConsensus (id STRING, topic STRING, "
                    "agreement_score DOUBLE, honest_count INT64, byzantine_count INT64, byzantine_ids STRING, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (bc:LUBFTConsensus {{id: '{consensus_id}', topic: '{topic}', "
                    f"agreement_score: {agreement_score}, honest_count: {honest_count}, "
                    f"byzantine_count: {byzantine_count}, byzantine_ids: '{byzantine_ids}'}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUBFTConsensus ignorée : {e}")
        return False

    def compile_smart_contract_directive(
        self,
        initial_state_label: str,
        trigger_label: str,
        target_state_label: str,
        escrow_label: Optional[str] = None
    ) -> np.ndarray:
        """
        Compile un contrat intelligent symbolique en Gigatoken FSM vectoriel.
        """
        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        v_init = get_v(initial_state_label)
        v_trig = get_v(trigger_label)
        v_target = get_v(target_state_label)
        v_escrow = get_v(escrow_label) if escrow_label else None

        return self.grammar.compose_smart_contract(v_init, v_trig, v_target, v_escrow)

    def decode_smart_contract_vector(self, contract_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile un vecteur de Smart Contract FSM en labels compréhensibles.
        """
        parts = self.grammar.extract_smart_contract_parts(contract_vector)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        init_name, init_sim = best_match(parts["initial_state"])
        trig_name, trig_sim = best_match(parts["trigger"])
        tgt_name, tgt_sim = best_match(parts["target_state"])
        esc_name, esc_sim = best_match(parts["escrow"])

        return {
            "initial_state": init_name,
            "initial_state_sim": round(init_sim, 3),
            "trigger": trig_name,
            "trigger_sim": round(trig_sim, 3),
            "target_state": tgt_name,
            "target_state_sim": round(tgt_sim, 3),
            "escrow": esc_name,
            "escrow_sim": round(esc_sim, 3),
            "is_valid": (init_sim >= 0.30 and trig_sim >= 0.30 and tgt_sim >= 0.30),
        }

    def compile_causal_test_directive(
        self,
        cause_label: str,
        effect_label: str
    ) -> np.ndarray:
        """
        Compile une directive d'hypothèse causale symbolique en Gigatoken formel.
        """
        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        v_cause = get_v(cause_label)
        v_effect = get_v(effect_label)
        return self.grammar.compose_causal_statement(v_cause, v_effect)

    def decode_causal_statement_vector(self, causal_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile une assertion causale formelle en labels symboliques.
        """
        parts = self.grammar.extract_causal_parts(causal_vector)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        c_name, c_sim = best_match(parts["cause"])
        e_name, e_sim = best_match(parts["effect"])

        return {
            "cause": c_name,
            "cause_sim": round(c_sim, 3),
            "effect": e_name,
            "effect_sim": round(e_sim, 3),
            "is_valid": (c_sim >= 0.35 and e_sim >= 0.35),
        }

    # =========================================================================
    # Méthodes Synthèse de Programmes, Logique LTL & Analogies (Phase 9 M1)
    # =========================================================================

    def register_synthesized_program(
        self,
        program_id: str,
        entry_label: str,
        loop_label: str,
        branch_label: str,
        term_label: str,
        lipschitz_l: float,
        is_contracting: bool
    ) -> bool:
        """
        Consigne un macro-programme latent synthétisé dans LUSynthesizedProgram.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUSynthesizedProgram (id STRING, entry_label STRING, "
                    "loop_label STRING, branch_label STRING, term_label STRING, "
                    "lipschitz_l DOUBLE, is_contracting BOOLEAN, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (p:LUSynthesizedProgram {{id: '{program_id}', entry_label: '{entry_label}', "
                    f"loop_label: '{loop_label}', branch_label: '{branch_label}', term_label: '{term_label}', "
                    f"lipschitz_l: {lipschitz_l}, is_contracting: {str(is_contracting).lower()}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUSynthesizedProgram ignorée : {e}")
        return False

    def register_temporal_clause(
        self,
        clause_id: str,
        predicate_label: str,
        operator_type: str,
        horizon: int,
        is_satisfied: bool
    ) -> bool:
        """
        Consigne une clause de Logique Temporelle Diachronique (LTL) dans LUTemporalClause.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUTemporalClause (id STRING, predicate_label STRING, "
                    "operator_type STRING, horizon INT64, is_satisfied BOOLEAN, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (tc:LUTemporalClause {{id: '{clause_id}', predicate_label: '{predicate_label}', "
                    f"operator_type: '{operator_type}', horizon: {horizon}, is_satisfied: {str(is_satisfied).lower()}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUTemporalClause ignorée : {e}")
        return False

    def register_analogy_transfer(
        self,
        analogy_id: str,
        a_label: str,
        b_label: str,
        c_label: str,
        d_label: str,
        fidelity_score: float
    ) -> bool:
        """
        Consigne un transfert analogique multivers dans LUAnalogyTransfer.
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUAnalogyTransfer (id STRING, a_label STRING, b_label STRING, "
                    "c_label STRING, d_label STRING, fidelity_score DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (at:LUAnalogyTransfer {{id: '{analogy_id}', a_label: '{a_label}', "
                    f"b_label: '{b_label}', c_label: '{c_label}', d_label: '{d_label}', "
                    f"fidelity_score: {fidelity_score}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUAnalogyTransfer ignorée : {e}")
        return False

    def compile_synthesized_program_directive(
        self,
        entry_label: str,
        loop_label: str,
        branch_label: str,
        term_label: str
    ) -> np.ndarray:
        """
        Compile un programme latent symbolique en Gigatoken unitaire.
        """
        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        v_entry = get_v(entry_label)
        v_loop = get_v(loop_label)
        v_branch = get_v(branch_label)
        v_term = get_v(term_label)

        return self.grammar.compose_synthesized_program(v_entry, v_loop, v_branch, v_term)

    def decode_synthesized_program_vector(self, program_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile un programme latent vectoriel en labels symboliques.
        """
        parts = self.grammar.extract_synthesized_program_parts(program_vector)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        e_name, e_sim = best_match(parts["entry_state"])
        l_name, l_sim = best_match(parts["loop_operator"])
        b_name, b_sim = best_match(parts["branch_condition"])
        t_name, t_sim = best_match(parts["terminal_state"])

        return {
            "entry_state": e_name,
            "entry_sim": round(e_sim, 3),
            "loop_operator": l_name,
            "loop_sim": round(l_sim, 3),
            "branch_condition": b_name,
            "branch_sim": round(b_sim, 3),
            "terminal_state": t_name,
            "terminal_sim": round(t_sim, 3),
            "is_valid": (e_sim >= 0.25 and l_sim >= 0.25 and b_sim >= 0.25 and t_sim >= 0.25),
        }

    def compile_temporal_directive(
        self,
        predicate_label: str,
        operator_type: str = "ALWAYS",
        horizon: int = 5
    ) -> np.ndarray:
        """
        Compile une directive de Logique Temporelle Diachronique en Gigatoken unitaire.
        """
        key = predicate_label.upper()
        if key in self.lexicon:
            v_pred = self.lexicon[key]["vector"]
        else:
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            v_pred = self.grammar._generate_canonical_unit_vector(rng)

        return self.grammar.compose_temporal_clause(v_pred, operator_type=operator_type, horizon=horizon)

    def decode_temporal_vector(self, temporal_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile une clause LTL vectorielle en composantes symboliques.
        """
        parts = self.grammar.extract_temporal_clause_parts(temporal_vector)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        pred_name, pred_sim = best_match(parts["predicate"])
        return {
            "operator": parts["operator"],
            "predicate": pred_name,
            "predicate_sim": round(pred_sim, 3),
            "is_valid": (pred_sim >= 0.25),
        }

    def compile_analogy_directive(
        self,
        a_label: str,
        b_label: str,
        c_label: str,
        d_label: str
    ) -> np.ndarray:
        """
        Compile un quadruplet d'analogie A : B :: C : D en Gigatoken unitaire.
        """
        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        va = get_v(a_label)
        vb = get_v(b_label)
        vc = get_v(c_label)
        vd = get_v(d_label)
        return self.grammar.compose_analogy_statement(va, vb, vc, vd)

    def decode_analogy_vector(self, analogy_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile un énoncé d'analogie vectorielle en 4 pôles symboliques.
        """
        parts = self.grammar.extract_analogy_parts(analogy_vector)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        a_name, a_sim = best_match(parts["a"])
        b_name, b_sim = best_match(parts["b"])
        c_name, c_sim = best_match(parts["c"])
        d_name, d_sim = best_match(parts["d"])

        return {
            "a": a_name, "a_sim": round(a_sim, 3),
            "b": b_name, "b_sim": round(b_sim, 3),
            "c": c_name, "c_sim": round(c_sim, 3),
            "d": d_name, "d_sim": round(d_sim, 3),
            "is_valid": (a_sim >= 0.25 and b_sim >= 0.25 and c_sim >= 0.25 and d_sim >= 0.25),
        }

    # =========================================================================
    # Méthodes Auto-Compilation de Connectome & Logique de Hoare (Phase 10 M1)
    # =========================================================================

    def register_self_compiled_mutation(
        self,
        mutation_id: str,
        agent_id: str,
        program_id: str,
        spectral_radius: float,
        approved: bool,
        score: float
    ) -> bool:
        """
        Consigne une auto-modification de connectome dans LUSelfCompiledMutation (Phase 10 M1).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUSelfCompiledMutation (id STRING, agent_id STRING, "
                    "program_id STRING, spectral_radius DOUBLE, approved BOOLEAN, score DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (m:LUSelfCompiledMutation {{id: '{mutation_id}', agent_id: '{agent_id}', "
                    f"program_id: '{program_id}', spectral_radius: {spectral_radius}, "
                    f"approved: {str(approved).lower()}, score: {score}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUSelfCompiledMutation ignorée : {e}")
        return False

    def register_hoare_proof(
        self,
        proof_id: str,
        mutation_id: str,
        pre_label: str,
        post_label: str,
        is_valid: bool,
        confidence: float
    ) -> bool:
        """
        Consigne une preuve de sécurité de Hoare dans LUHoareProof (Phase 10 M1).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUHoareProof (id STRING, mutation_id STRING, "
                    "pre_label STRING, post_label STRING, is_valid BOOLEAN, confidence DOUBLE, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (hp:LUHoareProof {{id: '{proof_id}', mutation_id: '{mutation_id}', "
                    f"pre_label: '{pre_label}', post_label: '{post_label}', "
                    f"is_valid: {str(is_valid).lower()}, confidence: {confidence}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUHoareProof ignorée : {e}")
        return False

    def compile_hoare_triple_directive(
        self,
        pre_label: str,
        cmd_label: str,
        post_label: str
    ) -> np.ndarray:
        """
        Compile un triplet de Hoare {P} C {Q} en Gigatoken formel de vérification.
        """
        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        vp = get_v(pre_label)
        vc = get_v(cmd_label)
        vq = get_v(post_label)
        return self.grammar.compose_hoare_triple(vp, vc, vq)

    def decode_hoare_triple_vector(self, hoare_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile un triplet formel de Hoare vectoriel en composantes symboliques.
        """
        qp = self.grammar.query_role(hoare_vector, self.grammar.ROLE_HOARE_PRE)
        qc = self.grammar.query_role(hoare_vector, self.grammar.ROLE_HOARE_CMD)
        qq = self.grammar.query_role(hoare_vector, self.grammar.ROLE_HOARE_POST)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        p_name, p_sim = best_match(qp)
        c_name, c_sim = best_match(qc)
        q_name, q_sim = best_match(qq)

        return {
            "precondition": p_name,
            "precondition_sim": round(p_sim, 3),
            "command": c_name,
            "command_sim": round(c_sim, 3),
            "postcondition": q_name,
            "postcondition_sim": round(q_sim, 3),
            "is_valid": (p_sim >= 0.25 and c_sim >= 0.25 and q_sim >= 0.25)
        }

    # =========================================================================
    # Méthodes Méta-Simulation Contrefactuelle & Rêve Sémantique (Phase 11 M1)
    # =========================================================================

    def register_shared_dream(
        self,
        dream_id: str,
        creator_id: str,
        scenario_label: str,
        goal_label: str,
        counterfactual_gain: float,
        is_ratified: bool = False
    ) -> bool:
        """
        Consigne un rêve sémantique partagé dans LUSharedDream (Phase 11 M1).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUSharedDream (id STRING, creator_id STRING, "
                    "scenario_label STRING, goal_label STRING, counterfactual_gain DOUBLE, is_ratified BOOLEAN, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (d:LUSharedDream {{id: '{dream_id}', creator_id: '{creator_id}', "
                    f"scenario_label: '{scenario_label}', goal_label: '{goal_label}', "
                    f"counterfactual_gain: {counterfactual_gain}, is_ratified: {str(is_ratified).lower()}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUSharedDream ignorée : {e}")
        return False

    def register_counterfactual_rollout(
        self,
        rollout_id: str,
        dream_id: str,
        horizon: int,
        final_gain: float,
        converged: bool
    ) -> bool:
        """
        Consigne un déroulé contrefactuel dans LUCounterfactualRollout (Phase 11 M1).
        """
        if self.db is not None:
            try:
                self.db.execute_cypher(
                    "CREATE NODE TABLE LUCounterfactualRollout (id STRING, dream_id STRING, "
                    "horizon INT64, final_gain DOUBLE, converged BOOLEAN, PRIMARY KEY (id))"
                )
            except Exception:
                pass
            try:
                q = (
                    f"CREATE (r:LUCounterfactualRollout {{id: '{rollout_id}', dream_id: '{dream_id}', "
                    f"horizon: {horizon}, final_gain: {final_gain}, converged: {str(converged).lower()}}})"
                )
                self.db.execute_cypher(q)
                return True
            except Exception as e:
                logger.debug(f"Persistence LUCounterfactualRollout ignorée : {e}")
        return False

    def compile_dream_hypothesis_directive(
        self,
        scenario_label: str,
        goal_label: str,
        what_if_label: str = "WHAT_IF"
    ) -> np.ndarray:
        """
        Compile une directive de rêve contrefactuel en Gigatoken unitaire composite.
        """
        def get_v(lbl: str) -> np.ndarray:
            key = lbl.upper()
            if key in self.lexicon:
                return self.lexicon[key]["vector"]
            rng = np.random.default_rng(abs(hash(key)) % (2**31 - 1))
            return self.grammar._generate_canonical_unit_vector(rng)

        v_scen = get_v(scenario_label)
        v_goal = get_v(goal_label)
        v_whatif = get_v(what_if_label)
        return self.grammar.compose_dream_hypothesis(v_scen, v_goal, v_whatif)

    def decode_dream_hypothesis_vector(self, dream_vector: np.ndarray) -> Dict[str, Any]:
        """
        Décompile une hypothèse de rêve vectorielle en labels symboliques.
        """
        v_scen = self.grammar.extract_dream_scenario(dream_vector)

        def best_match(qv: np.ndarray) -> Tuple[str, float]:
            best_label = "UNKNOWN"
            best_sim = -1.0
            for name, data in self.lexicon.items():
                sim = float(cosine_similarity(qv, data["vector"]))
                if sim > best_sim:
                    best_sim = sim
                    best_label = name
            return best_label, best_sim

        scen_name, scen_sim = best_match(v_scen)
        return {
            "scenario": scen_name,
            "scenario_sim": round(scen_sim, 3),
            "is_valid": (scen_sim >= 0.25)
        }


class MultiTribalTranslator:
    """
    Traducteur multi-variétés et pivot Lingua Franca pour clans hétérogènes (Phase 4 M3).
    Permet à N clans avec sous-espaces de projection distincts de communiquer via :
    - Des projections directes SVD Procruste entre clans adjacents.
    - Un sous-espace pivot (Lingua Franca de marché) commun U_pivot in Gr(k, D).
    """

    def __init__(self, dim: int = 16, k: int = 4, seed: int = 42):
        self.dim = dim
        self.k = k
        self.rng = np.random.default_rng(seed)
        self.clan_subspaces: Dict[str, np.ndarray] = {}
        # Sous-espace pivot canonique (Marché / Lingua Franca)
        raw_pivot = self.rng.standard_normal((self.dim, self.k))
        q, _ = np.linalg.qr(raw_pivot)
        self.pivot_subspace: np.ndarray = q.astype(np.float32)

    def register_clan(self, clan_id: str, subspace: np.ndarray) -> None:
        """Enregistre ou met à jour la base orthonormale d'un clan."""
        u = np.asarray(subspace, dtype=np.float32)
        if u.shape[0] != self.dim or u.shape[1] < self.k:
            q, _ = np.linalg.qr(np.random.randn(self.dim, self.k))
            u = q.astype(np.float32)
        self.clan_subspaces[clan_id] = u[:, :self.k]

    def translate_to_pivot(self, vector: np.ndarray, source_clan: str) -> np.ndarray:
        """Projette un Gigatoken d'un clan dans la Lingua Franca pivot."""
        u_src = self.clan_subspaces.get(source_clan, self.pivot_subspace)
        coords = np.dot(u_src.T, vector)  # Coordonnées dans la base source
        v_pivot = np.dot(self.pivot_subspace, coords)  # Reconstruction dans la base pivot
        norm = np.linalg.norm(v_pivot) + 1e-12
        return (v_pivot / norm).astype(np.float32)

    def translate_from_pivot(self, pivot_vector: np.ndarray, target_clan: str) -> np.ndarray:
        """Projette depuis la Lingua Franca pivot vers le dialecte d'un clan cible."""
        u_tgt = self.clan_subspaces.get(target_clan, self.pivot_subspace)
        coords = np.dot(self.pivot_subspace.T, pivot_vector)
        v_tgt = np.dot(u_tgt, coords)
        norm = np.linalg.norm(v_tgt) + 1e-12
        return (v_tgt / norm).astype(np.float32)

    def translate_between_clans(
        self,
        vector: np.ndarray,
        source_clan: str,
        target_clan: str
    ) -> np.ndarray:
        """Traduction de clan à clan via le pivot ou projection orthogonale directe."""
        if source_clan == target_clan:
            return vector.copy()
        pivot_vec = self.translate_to_pivot(vector, source_clan)
        return self.translate_from_pivot(pivot_vec, target_clan)


class FederalDiplomaticBridge:
    """
    Pont Diplomatique Inter-Connectomes Asymétrique (LU Phase 7 M2).
    Permet à des populations issues de connectomes à dimensions latentes différentes
    (ex: D_A = 16, D_B = 32 ou 64) d'établir des accords et traités constitutionnels communs.
    Utilise une projection de Procruste asymétrique avec complétion orthogonale SVD :
    T_A_to_B: R^{D_A} -> R^{D_B} et T_B_to_A: R^{D_B} -> R^{D_A}.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.projections: Dict[Tuple[int, int], np.ndarray] = {}

    def get_or_create_projection(self, dim_in: int, dim_out: int) -> np.ndarray:
        key = (dim_in, dim_out)
        if key in self.projections:
            return self.projections[key]

        if dim_in == dim_out:
            mat = np.eye(dim_in, dtype=np.float32)
        else:
            # Matrice d'isométrie partielle via SVD d'une matrice aléatoire
            raw = self.rng.standard_normal((dim_out, dim_in))
            u, _, vh = np.linalg.svd(raw, full_matrices=False)
            mat = np.dot(u, vh).astype(np.float32)

        self.projections[key] = mat
        return mat

    def project(self, vector: np.ndarray, target_dim: int) -> np.ndarray:
        v = np.asarray(vector, dtype=np.float32)
        source_dim = v.shape[-1]
        if source_dim == target_dim:
            return v.copy()

        proj_mat = self.get_or_create_projection(source_dim, target_dim)
        res = np.dot(proj_mat, v)
        norm = np.linalg.norm(res, axis=-1, keepdims=True) + 1e-12
        return (res / norm).astype(np.float32)

    def compute_asymmetric_alignment_cka(
        self,
        vectors_a: np.ndarray,
        vectors_b: np.ndarray
    ) -> float:
        """
        Calcule le CKA linéaire (Centered Kernel Alignment) entre deux représentations
        vectorielles hétérogènes pour évaluer la fidélité de l'accord diplomatique.
        """
        x = np.asarray(vectors_a, dtype=np.float64)
        y = np.asarray(vectors_b, dtype=np.float64)
        if x.shape[0] != y.shape[0]:
            min_n = min(x.shape[0], y.shape[0])
            x = x[:min_n]
            y = y[:min_n]

        # Centrage
        x_c = x - np.mean(x, axis=0, keepdims=True)
        y_c = y - np.mean(y, axis=0, keepdims=True)

        k = np.dot(x_c, x_c.T)
        l = np.dot(y_c, y_c.T)

        hsic_xy = np.sum(k * l)
        hsic_xx = np.sum(k * k)
        hsic_yy = np.sum(l * l)

        denom = np.sqrt(hsic_xx * hsic_yy) + 1e-12
        return float(hsic_xy / denom)

    def compile_dream_hypothesis_directive(
        self,
        scenario_name: str,
        goal_name: str,
        expected_gain: float = 0.5
    ) -> str:
        """Compile une directive symbolique de rêve contrefactuel (Phase 11 M1)."""
        return f"DREAM_SCENARIO({scenario_name}) ⊛ WHAT_IF({goal_name}) [EXPECTED_GAIN={expected_gain:.2f}]"

    def decode_dream_hypothesis_vector(self, dream_vector: np.ndarray) -> Dict[str, Any]:
        """Décode un vecteur d'hypothèse de rêve en directive lisible."""
        norm = float(np.linalg.norm(dream_vector))
        gain = float(np.clip(float(dream_vector[0]), -1.0, 1.0))
        return {
            "directive": f"DREAM_HYPOTHESIS(norm={norm:.2f})",
            "expected_gain": gain,
            "confidence": 0.85
        }

