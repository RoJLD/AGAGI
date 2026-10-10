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
            # Cibles
            "PREY": ("TARGET", 1.0),
            "FOOD": ("TARGET", 1.0),
            "FIRE": ("TARGET", 1.0),
            "GRANARY": ("TARGET", 1.0),
            "FURNACE": ("TARGET", 1.0),
            "WOOD": ("TARGET", 0.8),
            "STONE": ("TARGET", 0.8),
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
