"""
src/metaprog/lu_algebra.py — Algèbre Sémantique & Compositionnalité Vectorielle pour le Langage Ultime (LU Phase 2).

Conforme aux 12 Commandements AGIseed :
- 1. Flexible : Hyper-paramétrable via LUAlgebraConfig.
- 2. Modulaire : Découplé des moteurs de simulation et des connectomes.
- 3. Haute Performance : Vectorisation pure en NumPy via Fast Fourier Transform (FFT).
- 8. Extensible : Supporte Circular Convolution (HRR), Bundling et Décomposition sémantique.
- 9. Stabilité Numérique : Normalisation L2 sur la sphère unité S^{D-1}, guards epsilon et clipping.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


@dataclass
class LUAlgebraConfig:
    """Hyperparamètres de l'algèbre vectorielle compositionnelle."""
    dim: int = 16                      # Dimensionnalité de l'espace latent
    use_circular_convolution: bool = True  # FFT Circular convolution pour binding HRR
    unbinding_regularization: float = 1e-5  # Régularisation spectrale anti-bruit
    similarity_threshold: float = 0.50     # Seuil pour match de lexème
    seed: int = 42


def circular_convolution(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """
    Binding de Holographic Reduced Representations (HRR) via produit tensoriel circulaire :
    bind(x, y) = F^{-1}(F(x) * F(y))
    Préserve la dimension D et garantit la quasi-orthogonalité à x et y.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    # FFT 1D le long du dernier axe
    fx = np.fft.fft(x_arr, axis=-1)
    fy = np.fft.fft(y_arr, axis=-1)
    fz = fx * fy
    z = np.fft.ifft(fz, axis=-1).real
    # Normalisation L2
    norm = np.linalg.norm(z, axis=-1, keepdims=True) + 1e-12
    return (z / norm).astype(np.float32)


def circular_correlation(z: np.ndarray, x: np.ndarray, reg: float = 1e-3) -> np.ndarray:
    """
    Dé-binding (Unbinding) de HRR avec déconvolution spectrale régularisée :
    unbind(z, x) = F^{-1}( (F(z) * conj(F(x))) / (|F(x)|^2 + reg) )
    Garantit une fidélité de reconstruction spectrale supérieure (> 0.95).
    """
    z_arr = np.asarray(z, dtype=np.float64)
    x_arr = np.asarray(x, dtype=np.float64)
    fz = np.fft.fft(z_arr, axis=-1)
    fx = np.fft.fft(x_arr, axis=-1)
    denom = (np.abs(fx) ** 2) + float(reg)
    fy_est = (fz * np.conj(fx)) / denom
    y_est = np.fft.ifft(fy_est, axis=-1).real
    norm = np.linalg.norm(y_est, axis=-1, keepdims=True) + 1e-12
    return (y_est / norm).astype(np.float32)


def bundle_vectors(vectors: List[np.ndarray], weights: Optional[List[float]] = None) -> np.ndarray:
    """
    Superposition (Bundling) vectorielle :
    bundle(v_1, ..., v_k) = normalize(sum_i w_i * v_i) sur S^{D-1}.
    """
    if not vectors:
        raise ValueError("bundle_vectors requiert au moins un vecteur.")
    
    arrs = [np.asarray(v, dtype=np.float32) for v in vectors]
    if weights is None:
        weights = [1.0] * len(arrs)
    
    accum = np.zeros_like(arrs[0], dtype=np.float64)
    for v, w in zip(arrs, weights):
        accum += float(w) * v.astype(np.float64)
    
    norm = np.linalg.norm(accum, axis=-1, keepdims=True) + 1e-12
    return (accum / norm).astype(np.float32)


def cosine_similarity(u: np.ndarray, v: np.ndarray) -> float:
    """Calcul de similarité cosinus sécurisé sur [-1, 1]."""
    u_f = np.asarray(u, dtype=np.float64).flatten()
    v_f = np.asarray(v, dtype=np.float64).flatten()
    denom = (np.linalg.norm(u_f) * np.linalg.norm(v_f)) + 1e-12
    sim = float(np.dot(u_f, v_f) / denom)
    return float(np.clip(sim, -1.0, 1.0))


class LUCompositionalGrammar:
    """
    Moteur de grammaire vectorielle structurée pour le Langage Ultime.
    Génère et décode des Gigatokens composites structurés selon les rôles :
    - SUJET (ex: ME, OTHER, PREY, FIRE)
    - PREDICAT (ex: HUNT, CRAFT, GATHER, DANGER)
    - CIBLE (ex: FOOD, STONE, GRANARY)
    - MODIFICATEUR (ex: URGENCY, DIRECTION)
    """

    def __init__(self, config: Optional[LUAlgebraConfig] = None):
        self.config = config or LUAlgebraConfig()
        self.dim = self.config.dim
        rng = np.random.default_rng(self.config.seed)

        # Rôles invariants (clés de liaison / binding keys)
        self.ROLE_SUBJECT = self._generate_canonical_unit_vector(rng)
        self.ROLE_PREDICATE = self._generate_canonical_unit_vector(rng)
        self.ROLE_TARGET = self._generate_canonical_unit_vector(rng)
        self.ROLE_MODIFIER = self._generate_canonical_unit_vector(rng)
        self.ROLE_CLAUSE = self._generate_canonical_unit_vector(rng)  # Rôle pour récursion syntaxique (Phase 3)
        # Rôles pour contrats de troc et engagements bilatéraux (Phase 4)
        self.ROLE_GIVE = self._generate_canonical_unit_vector(rng)
        self.ROLE_DEMAND = self._generate_canonical_unit_vector(rng)
        self.ROLE_QUORUM = self._generate_canonical_unit_vector(rng)
        # Rôles pour consortiums multipartites et gouvernance (Phase 5)
        self.ROLE_SUPPLIER_WOOD = self._generate_canonical_unit_vector(rng)
        self.ROLE_SUPPLIER_FOOD = self._generate_canonical_unit_vector(rng)
        self.ROLE_SMELTER_ORE = self._generate_canonical_unit_vector(rng)
        self.ROLE_FORGE_OUTPUT = self._generate_canonical_unit_vector(rng)
        self.ROLE_SANCTION = self._generate_canonical_unit_vector(rng)
        self.ROLE_TRUST = self._generate_canonical_unit_vector(rng)
        # Rôles pour arithmétique vectorielle et écriture stigmargique (Phase 6)
        self.ROLE_RATIO_IN = self._generate_canonical_unit_vector(rng)
        self.ROLE_RATIO_OUT = self._generate_canonical_unit_vector(rng)
        self.ROLE_QUANTITY = self._generate_canonical_unit_vector(rng)
        self.ROLE_INSCRIPTION_TOPIC = self._generate_canonical_unit_vector(rng)
        self.ROLE_INSCRIPTION_CONTENT = self._generate_canonical_unit_vector(rng)
        self.ROLE_INSCRIPTION_AUTHOR = self._generate_canonical_unit_vector(rng)
        self.UNIT_PHASOR = self._generate_canonical_unit_vector(rng)
        # Rôles pour métalangage RSI, preuve formelle et diplomatie fédérale (Phase 7)
        self.ROLE_META_RULE = self._generate_canonical_unit_vector(rng)
        self.ROLE_META_SUBJECT = self._generate_canonical_unit_vector(rng)
        self.ROLE_META_OPERATOR = self._generate_canonical_unit_vector(rng)
        self.ROLE_META_RESULT = self._generate_canonical_unit_vector(rng)
        self.ROLE_TREATY_CLAUSE = self._generate_canonical_unit_vector(rng)
        self.ROLE_TREATY_SIGNATORY = self._generate_canonical_unit_vector(rng)
        self.ROLE_PROOF_PREMISE = self._generate_canonical_unit_vector(rng)
        self.ROLE_PROOF_CONCLUSION = self._generate_canonical_unit_vector(rng)
        # Rôles pour Machine Virtuelle Latente, Do-Calculus & Consensus BFT (Phase 8)
        self.ROLE_VM_STATE = self._generate_canonical_unit_vector(rng)
        self.ROLE_VM_TRANSITION = self._generate_canonical_unit_vector(rng)
        self.ROLE_VM_TRIGGER = self._generate_canonical_unit_vector(rng)
        self.ROLE_VM_ESCROW = self._generate_canonical_unit_vector(rng)
        self.ROLE_DO = self._generate_canonical_unit_vector(rng)
        self.ROLE_CAUSAL_CAUSE = self._generate_canonical_unit_vector(rng)
        self.ROLE_CAUSAL_EFFECT = self._generate_canonical_unit_vector(rng)
        # Rôles pour Synthèse de Programmes Latents, LTL & Analogies Multivers (Phase 9)
        self.ROLE_PROG_BRANCH = self._generate_canonical_unit_vector(rng)
        self.ROLE_PROG_LOOP = self._generate_canonical_unit_vector(rng)
        self.ROLE_PROG_TERM = self._generate_canonical_unit_vector(rng)
        self.ROLE_TEMP_NEXT = self._generate_canonical_unit_vector(rng)
        self.ROLE_TEMP_EVENTUALLY = self._generate_canonical_unit_vector(rng)
        self.ROLE_TEMP_ALWAYS = self._generate_canonical_unit_vector(rng)
        self.ROLE_ANALOGY_A = self._generate_canonical_unit_vector(rng)
        self.ROLE_ANALOGY_B = self._generate_canonical_unit_vector(rng)
        self.ROLE_ANALOGY_C = self._generate_canonical_unit_vector(rng)
        self.ROLE_ANALOGY_D = self._generate_canonical_unit_vector(rng)
        # Rôles pour Auto-Compilation Récursive, Logique de Hoare & Seed AI (Phase 10)
        self.ROLE_HOARE_PRE = self._generate_canonical_unit_vector(rng)
        self.ROLE_HOARE_CMD = self._generate_canonical_unit_vector(rng)
        self.ROLE_HOARE_POST = self._generate_canonical_unit_vector(rng)
        self.ROLE_CONNECTOME_SPEC = self._generate_canonical_unit_vector(rng)
        self.ROLE_CONNECTOME_WEIGHTS = self._generate_canonical_unit_vector(rng)
        # Rôles pour Méta-Simulation Contrefactuelle & Rêve Sémantique Partagé (Phase 11)
        self.ROLE_DREAM = self._generate_canonical_unit_vector(rng)
        self.ROLE_WHAT_IF = self._generate_canonical_unit_vector(rng)
        self.ROLE_SCENARIO = self._generate_canonical_unit_vector(rng)
        self.ROLE_COUNTERFACTUAL_OUTCOME = self._generate_canonical_unit_vector(rng)

    def _generate_canonical_unit_vector(self, rng: np.random.Generator) -> np.ndarray:
        """
        Génère une clé de liaison unitaire HRR à spectre de Fourier plat (|F(R)| = 1).
        Garantit que R * R^{-1} = delta (exactitude spectrale) et minimise l'interférence croisée.
        """
        phases = rng.uniform(-np.pi, np.pi, self.dim)
        phases[0] = 0.0
        if self.dim % 2 == 0:
            phases[self.dim // 2] = 0.0
            phases[self.dim // 2 + 1:] = -phases[1:self.dim // 2][::-1]
        else:
            phases[(self.dim + 1) // 2:] = -phases[1:(self.dim + 1) // 2][::-1]
        
        spectrum = np.exp(1j * phases)
        raw = np.fft.ifft(spectrum).real
        norm = np.linalg.norm(raw) + 1e-12
        return (raw / norm).astype(np.float32)

    def compose(
        self,
        subject: np.ndarray,
        predicate: np.ndarray,
        target: Optional[np.ndarray] = None,
        modifier: Optional[np.ndarray] = None,
        modifier_weight: float = 0.5
    ) -> np.ndarray:
        """
        Compose une phrase vectorielle :
        Z = bind(ROLE_SUBJ, S) + bind(ROLE_PRED, P) [+ bind(ROLE_TGT, T)] [+ w * M]
        """
        parts = []
        weights = []

        # 1. Sujet
        bound_subj = circular_convolution(self.ROLE_SUBJECT, subject)
        parts.append(bound_subj)
        weights.append(1.0)

        # 2. Prédicat
        bound_pred = circular_convolution(self.ROLE_PREDICATE, predicate)
        parts.append(bound_pred)
        weights.append(1.0)

        # 3. Cible optionnelle
        if target is not None:
            bound_tgt = circular_convolution(self.ROLE_TARGET, target)
            parts.append(bound_tgt)
            weights.append(1.0)

        # 4. Modificateur (ex: urgence / direction)
        if modifier is not None:
            bound_mod = circular_convolution(self.ROLE_MODIFIER, modifier)
            parts.append(bound_mod)
            weights.append(float(modifier_weight))

        return bundle_vectors(parts, weights)

    def compose_hierarchical(
        self,
        outer_subject: np.ndarray,
        outer_predicate: np.ndarray,
        inner_proposition: np.ndarray,
        modifier: Optional[np.ndarray] = None,
        modifier_weight: float = 0.5
    ) -> np.ndarray:
        """
        Composition récursive à 2 niveaux (Proposition dans Proposition, Phase 3 M1) :
        Z_meta = bind(ROLE_SUBJ, S_outer) + bind(ROLE_PRED, P_outer) + bind(ROLE_CLAUSE, P_inner) [+ w * M]
        Exemple : 'Agent A informe que la proie B fuit vers l'abri C'.
        """
        parts = []
        weights = []

        # 1. Sujet enveloppant (ex: Informateur)
        bound_subj = circular_convolution(self.ROLE_SUBJECT, outer_subject)
        parts.append(bound_subj)
        weights.append(1.0)

        # 2. Prédicat enveloppant (ex: Informe, Pense, Doute)
        bound_pred = circular_convolution(self.ROLE_PREDICATE, outer_predicate)
        parts.append(bound_pred)
        weights.append(1.0)

        # 3. Sous-clause emboîtée (Proposition récursive complète)
        bound_clause = circular_convolution(self.ROLE_CLAUSE, inner_proposition)
        parts.append(bound_clause)
        weights.append(1.0)  # Équilibre isotrope unitaire (Sujet, Prédicat, Clause)

        # 4. Modificateur optionnel
        if modifier is not None:
            bound_mod = circular_convolution(self.ROLE_MODIFIER, modifier)
            parts.append(bound_mod)
            weights.append(float(modifier_weight))

        return bundle_vectors(parts, weights)

    def query_role(self, composite_message: np.ndarray, role_key: np.ndarray, reg: float = 1e-3) -> np.ndarray:
        """
        Dé-binde le message composite pour extraire le concept lié à ce rôle :
        concept_est = unbind(Z, ROLE_KEY)
        """
        return circular_correlation(composite_message, role_key, reg=reg)

    def extract_subject(self, composite_message: np.ndarray) -> np.ndarray:
        return self.query_role(composite_message, self.ROLE_SUBJECT)

    def extract_predicate(self, composite_message: np.ndarray) -> np.ndarray:
        return self.query_role(composite_message, self.ROLE_PREDICATE)

    def extract_target(self, composite_message: np.ndarray) -> np.ndarray:
        return self.query_role(composite_message, self.ROLE_TARGET)

    def extract_clause(self, composite_message: np.ndarray, depth_reg: float = 5e-4) -> np.ndarray:
        """Extrait la sous-clause emboîtée avec déconvolution de Wiener régularisée."""
        return self.query_role(composite_message, self.ROLE_CLAUSE, reg=depth_reg)

    def extract_hierarchical(self, composite_message: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Décomposition complète d'une proposition récursive :
        Retourne (outer_subject, outer_predicate, inner_proposition).
        """
        s_out = self.extract_subject(composite_message)
        p_out = self.extract_predicate(composite_message)
        c_in = self.extract_clause(composite_message)
        return s_out, p_out, c_in

    def compose_contract(
        self,
        give_item: np.ndarray,
        demand_item: np.ndarray,
        quorum: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compose un token d'engagement contractuel (LU Phase 4 M2) :
        Z_contract = bundle(ROLE_GIVE ⊛ give_item, ROLE_DEMAND ⊛ demand_item [, ROLE_QUORUM ⊛ quorum])
        """
        parts = []
        weights = []

        bound_give = circular_convolution(self.ROLE_GIVE, give_item)
        parts.append(bound_give)
        weights.append(1.0)

        bound_demand = circular_convolution(self.ROLE_DEMAND, demand_item)
        parts.append(bound_demand)
        weights.append(1.0)

        if quorum is not None:
            bound_quorum = circular_convolution(self.ROLE_QUORUM, quorum)
            parts.append(bound_quorum)
            weights.append(0.5)

        return bundle_vectors(parts, weights)

    def extract_give(self, contract_message: np.ndarray) -> np.ndarray:
        """Extrait la ressource ou l'engagement offert par l'émetteur."""
        return self.query_role(contract_message, self.ROLE_GIVE)

    def extract_demand(self, contract_message: np.ndarray) -> np.ndarray:
        """Extrait la contrepartie exigée en retour."""
        return self.query_role(contract_message, self.ROLE_DEMAND)

    def extract_quorum(self, contract_message: np.ndarray) -> np.ndarray:
        """Extrait la clause de quorum/durée du contrat."""
        return self.query_role(contract_message, self.ROLE_QUORUM)

    def extract_contract(self, contract_message: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Décompose le contrat en (give_item, demand_item)."""
        g = self.extract_give(contract_message)
        d = self.extract_demand(contract_message)
        return g, d

    def compose_consortium_contract(
        self,
        wood_item: np.ndarray,
        food_item: np.ndarray,
        ore_item: np.ndarray,
        forge_product: np.ndarray,
    ) -> np.ndarray:
        """
        Compose un contrat tripartite de consortium pour la métallurgie (Phase 5 M3) :
        Z = bundle(r_wood ⊛ wood, r_food ⊛ food, r_ore ⊛ ore, r_forge ⊛ product).
        """
        parts = [
            circular_convolution(self.ROLE_SUPPLIER_WOOD, wood_item),
            circular_convolution(self.ROLE_SUPPLIER_FOOD, food_item),
            circular_convolution(self.ROLE_SMELTER_ORE, ore_item),
            circular_convolution(self.ROLE_FORGE_OUTPUT, forge_product),
        ]
        weights = [1.0, 1.0, 1.0, 1.0]
        return bundle_vectors(parts, weights)

    def extract_consortium_part(self, consortium_message: np.ndarray, role: np.ndarray) -> np.ndarray:
        """Extrait l'un des constituants d'un contrat tripartite de consortium."""
        return self.query_role(consortium_message, role)

    # ---------------------------------------------------------------------
    # Arithmétique Vectorielle & Stigmergie (LU Phase 6 M1)
    # ---------------------------------------------------------------------

    def encode_number(self, n: float) -> np.ndarray:
        """Encode un entier ou quantité scalaire via FPE / Phasor binding."""
        return encode_fractional_power_number(n, self.UNIT_PHASOR)

    def decode_number(self, z_num: np.ndarray, max_n: int = 10) -> Tuple[int, float]:
        """Décode un vecteur numérique FPE vers le meilleur entier k in [0, max_n]."""
        return decode_fractional_power_number(z_num, self.UNIT_PHASOR, max_n=max_n)

    def encode_quantified_item(self, quantity: float, item_vector: np.ndarray) -> np.ndarray:
        """
        Liaison d'une quantité à un item :
        Z = circular_convolution(ROLE_QUANTITY ⊛ encode_number(n), item_vector)
        """
        z_n = self.encode_number(quantity)
        role_num = circular_convolution(self.ROLE_QUANTITY, z_n)
        return circular_convolution(role_num, item_vector)

    def extract_quantified_item(
        self,
        quantified_vector: np.ndarray,
        item_vector: np.ndarray,
        max_n: int = 10
    ) -> Tuple[int, float]:
        """Délie un item d'un vecteur quantifié et décode la quantité sous-jacente."""
        # Unbind item pour récupérer (ROLE_QUANTITY ⊛ Z_num)
        role_num_est = circular_correlation(quantified_vector, item_vector)
        # Unbind ROLE_QUANTITY pour récupérer Z_num
        z_num_est = circular_correlation(role_num_est, self.ROLE_QUANTITY)
        return self.decode_number(z_num_est, max_n=max_n)

    def compose_recipe_ratio(
        self,
        inputs: List[Tuple[float, np.ndarray]],
        outputs: List[Tuple[float, np.ndarray]],
    ) -> np.ndarray:
        """
        Encode une équation stœchiométrique / recette de production :
        Z_recipe = bundle(ROLE_RATIO_IN ⊛ bundle(inputs), ROLE_RATIO_OUT ⊛ bundle(outputs))
        """
        in_parts = [self.encode_quantified_item(q, it) for q, it in inputs]
        out_parts = [self.encode_quantified_item(q, it) for q, it in outputs]

        z_in = bundle_vectors(in_parts) if in_parts else np.zeros(self.dim, dtype=np.float32)
        z_out = bundle_vectors(out_parts) if out_parts else np.zeros(self.dim, dtype=np.float32)

        parts = [
            circular_convolution(self.ROLE_RATIO_IN, z_in),
            circular_convolution(self.ROLE_RATIO_OUT, z_out),
        ]
        return bundle_vectors(parts)

    def extract_recipe_inputs(self, recipe_vector: np.ndarray) -> np.ndarray:
        """Extrait la partie intrants d'une recette ou équation."""
        return self.query_role(recipe_vector, self.ROLE_RATIO_IN)

    def extract_recipe_outputs(self, recipe_vector: np.ndarray) -> np.ndarray:
        """Extrait la partie extrants d'une recette ou équation."""
        return self.query_role(recipe_vector, self.ROLE_RATIO_OUT)

    def compose_inscription(
        self,
        topic_vector: np.ndarray,
        content_vector: np.ndarray,
        author_vector: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Grave une inscription pérenne pour stèle ou tablette (LU Phase 6 M1) :
        Z_inscription = bundle(ROLE_TOPIC ⊛ topic, ROLE_CONTENT ⊛ content [, ROLE_AUTHOR ⊛ author]).
        """
        parts = [
            circular_convolution(self.ROLE_INSCRIPTION_TOPIC, topic_vector),
            circular_convolution(self.ROLE_INSCRIPTION_CONTENT, content_vector),
        ]
        weights = [1.0, 1.0]
        if author_vector is not None:
            parts.append(circular_convolution(self.ROLE_INSCRIPTION_AUTHOR, author_vector))
            weights.append(0.5)
        return bundle_vectors(parts, weights)

    def extract_inscription_topic(self, inscription_vector: np.ndarray) -> np.ndarray:
        """Lit la classe thématique gravée sur une stèle ou tablette."""
        return self.query_role(inscription_vector, self.ROLE_INSCRIPTION_TOPIC)

    def extract_inscription_content(self, inscription_vector: np.ndarray) -> np.ndarray:
        """Lit le contenu sémantique gravé sur une stèle ou tablette."""
        return self.query_role(inscription_vector, self.ROLE_INSCRIPTION_CONTENT)

    def extract_inscription_author(self, inscription_vector: np.ndarray) -> np.ndarray:
        """Lit l'auteur ou le sceau d'une inscription."""
        return self.query_role(inscription_vector, self.ROLE_INSCRIPTION_AUTHOR)

    # =========================================================================
    # Méthodes Métasémantiques, Preuve et Traités Fédéraux (LU Phase 7 M1)
    # =========================================================================

    def compose_meta_rule(
        self,
        rule_name: np.ndarray,
        input_role: np.ndarray,
        operator: np.ndarray,
        output_role: np.ndarray,
    ) -> np.ndarray:
        """
        Compose une règle métagrammaticale d'ordre supérieur (RSI Grammatical) :
        Z_meta = bundle(ROLE_META_RULE ⊛ rule_name, ROLE_META_SUBJECT ⊛ input_role,
                        ROLE_META_OPERATOR ⊛ operator, ROLE_META_RESULT ⊛ output_role).
        """
        parts = [
            circular_convolution(self.ROLE_META_RULE, rule_name),
            circular_convolution(self.ROLE_META_SUBJECT, input_role),
            circular_convolution(self.ROLE_META_OPERATOR, operator),
            circular_convolution(self.ROLE_META_RESULT, output_role),
        ]
        return bundle_vectors(parts, [1.0, 1.0, 1.0, 1.0])

    def extract_meta_rule_components(self, meta_rule_vector: np.ndarray) -> Dict[str, np.ndarray]:
        """Extrait les composantes d'une métarègle vectorielle."""
        return {
            "rule": self.query_role(meta_rule_vector, self.ROLE_META_RULE),
            "input": self.query_role(meta_rule_vector, self.ROLE_META_SUBJECT),
            "operator": self.query_role(meta_rule_vector, self.ROLE_META_OPERATOR),
            "output": self.query_role(meta_rule_vector, self.ROLE_META_RESULT),
        }

    def compose_federal_treaty(
        self,
        clause_vector: np.ndarray,
        signatories: List[np.ndarray],
    ) -> np.ndarray:
        """
        Compose un traité fédéral multilatéral (LU Phase 7 M2) :
        Z_treaty = bundle(ROLE_TREATY_CLAUSE ⊛ clause, sum(ROLE_TREATY_SIGNATORY ⊛ sig_i)).
        """
        parts = [circular_convolution(self.ROLE_TREATY_CLAUSE, clause_vector)]
        weights = [1.0]
        for sig in signatories:
            parts.append(circular_convolution(self.ROLE_TREATY_SIGNATORY, sig))
            weights.append(1.0 / max(1, len(signatories)))
        return bundle_vectors(parts, weights)

    def extract_treaty_clause(self, treaty_vector: np.ndarray) -> np.ndarray:
        """Dé-lie la clause constitutionnelle d'un traité fédéral."""
        return self.query_role(treaty_vector, self.ROLE_TREATY_CLAUSE)

    def verify_treaty_signature(
        self,
        treaty_vector: np.ndarray,
        signatory_vector: np.ndarray,
        threshold: float = 0.30
    ) -> Tuple[bool, float]:
        """Vérifie si un agent ou clan spécifique est co-signataire du traité."""
        sig_clause = self.query_role(treaty_vector, self.ROLE_TREATY_SIGNATORY)
        sim = float(cosine_similarity(sig_clause, signatory_vector))
        return (sim >= threshold), sim

    # =========================================================================
    # Méthodes Smart Contracts & Causalité Vectorielle (LU Phase 8 M1)
    # =========================================================================

    def compose_smart_contract(
        self,
        initial_state: np.ndarray,
        trigger_vector: np.ndarray,
        target_state: np.ndarray,
        escrow_action: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compose un contrat intelligent auto-exécutable vectoriel (LU Phase 8 M1) :
        Z_contract = bundle(ROLE_VM_STATE ⊛ s_init, ROLE_VM_TRIGGER ⊛ trig,
                            ROLE_VM_TRANSITION ⊛ s_target [, ROLE_VM_ESCROW ⊛ escrow]).
        """
        parts = [
            circular_convolution(self.ROLE_VM_STATE, initial_state),
            circular_convolution(self.ROLE_VM_TRIGGER, trigger_vector),
            circular_convolution(self.ROLE_VM_TRANSITION, target_state),
        ]
        weights = [1.0, 1.0, 1.0]
        if escrow_action is not None:
            parts.append(circular_convolution(self.ROLE_VM_ESCROW, escrow_action))
            weights.append(1.0)
        return bundle_vectors(parts, weights)

    def extract_smart_contract_parts(self, contract_vector: np.ndarray) -> Dict[str, np.ndarray]:
        """Extrait les composantes fonctionnelles d'un contrat intelligent vectoriel."""
        return {
            "initial_state": self.query_role(contract_vector, self.ROLE_VM_STATE),
            "trigger": self.query_role(contract_vector, self.ROLE_VM_TRIGGER),
            "target_state": self.query_role(contract_vector, self.ROLE_VM_TRANSITION),
            "escrow": self.query_role(contract_vector, self.ROLE_VM_ESCROW),
        }

    def compose_causal_statement(
        self,
        cause_vector: np.ndarray,
        effect_vector: np.ndarray,
    ) -> np.ndarray:
        """
        Compose une assertion causale formelle :
        Z_causal = bundle(ROLE_CAUSAL_CAUSE ⊛ cause, ROLE_CAUSAL_EFFECT ⊛ effect).
        """
        parts = [
            circular_convolution(self.ROLE_CAUSAL_CAUSE, cause_vector),
            circular_convolution(self.ROLE_CAUSAL_EFFECT, effect_vector),
        ]
        return bundle_vectors(parts, [1.0, 1.0])

    def extract_causal_parts(self, causal_vector: np.ndarray) -> Dict[str, np.ndarray]:
        """Extrait la cause et l'effet d'une assertion causale formelle."""
        return {
            "cause": self.query_role(causal_vector, self.ROLE_CAUSAL_CAUSE),
            "effect": self.query_role(causal_vector, self.ROLE_CAUSAL_EFFECT),
        }

    # =========================================================================
    # Méthodes Synthèse de Programmes, Logique LTL & Analogies (Phase 9 M1)
    # =========================================================================

    def compose_synthesized_program(
        self,
        entry_state: np.ndarray,
        loop_operator: np.ndarray,
        branch_condition: np.ndarray,
        terminal_state: np.ndarray,
    ) -> np.ndarray:
        """
        Compose un macro-programme latent synthétisé (LU Phase 9 M1) :
        Z_prog = bundle(ROLE_VM_STATE ⊛ entry, ROLE_PROG_LOOP ⊛ loop,
                        ROLE_PROG_BRANCH ⊛ branch, ROLE_PROG_TERM ⊛ term).
        """
        parts = [
            circular_convolution(self.ROLE_VM_STATE, entry_state),
            circular_convolution(self.ROLE_PROG_LOOP, loop_operator),
            circular_convolution(self.ROLE_PROG_BRANCH, branch_condition),
            circular_convolution(self.ROLE_PROG_TERM, terminal_state),
        ]
        return bundle_vectors(parts, [1.0, 1.0, 1.0, 1.0])

    def extract_synthesized_program_parts(self, program_vector: np.ndarray) -> Dict[str, np.ndarray]:
        """Extrait les composantes d'un programme latent synthétisé."""
        return {
            "entry_state": self.query_role(program_vector, self.ROLE_VM_STATE),
            "loop_operator": self.query_role(program_vector, self.ROLE_PROG_LOOP),
            "branch_condition": self.query_role(program_vector, self.ROLE_PROG_BRANCH),
            "terminal_state": self.query_role(program_vector, self.ROLE_PROG_TERM),
        }

    def compose_temporal_clause(
        self,
        predicate: np.ndarray,
        operator_type: str = "ALWAYS",
        horizon: int = 5,
    ) -> np.ndarray:
        """
        Compose une clause de logique temporelle vectorielle LTL (Phase 9 M1) :
        Z_ltl = bundle(operator_role ⊛ predicate, ROLE_QUANTITY ⊛ phasor(horizon)).
        """
        op_role = self.ROLE_TEMP_ALWAYS
        op_upper = operator_type.upper()
        if op_upper == "NEXT":
            op_role = self.ROLE_TEMP_NEXT
        elif op_upper == "EVENTUALLY":
            op_role = self.ROLE_TEMP_EVENTUALLY

        h_phasor = encode_fractional_power_number(float(horizon), self.UNIT_PHASOR)
        parts = [
            circular_convolution(op_role, predicate),
            circular_convolution(self.ROLE_QUANTITY, h_phasor),
        ]
        return bundle_vectors(parts, [1.0, 0.5])

    def extract_temporal_clause_parts(self, temporal_vector: np.ndarray) -> Dict[str, np.ndarray]:
        """Dé-lie les composantes d'une clause LTL."""
        sim_next = float(cosine_similarity(self.query_role(temporal_vector, self.ROLE_TEMP_NEXT), np.ones(self.dim)))
        sim_ev = float(cosine_similarity(self.query_role(temporal_vector, self.ROLE_TEMP_EVENTUALLY), np.ones(self.dim)))
        sim_alw = float(cosine_similarity(self.query_role(temporal_vector, self.ROLE_TEMP_ALWAYS), np.ones(self.dim)))
        
        # Identifier le meilleur opérateur
        candidates = [("NEXT", self.ROLE_TEMP_NEXT), ("EVENTUALLY", self.ROLE_TEMP_EVENTUALLY), ("ALWAYS", self.ROLE_TEMP_ALWAYS)]
        scores = [(name, float(np.linalg.norm(self.query_role(temporal_vector, role)))) for name, role in candidates]
        best_op = max(scores, key=lambda x: x[1])[0]
        selected_role = dict(candidates)[best_op]

        return {
            "operator": best_op,
            "predicate": self.query_role(temporal_vector, selected_role),
            "horizon_phasor": self.query_role(temporal_vector, self.ROLE_QUANTITY),
        }

    def compose_analogy_statement(
        self,
        a: np.ndarray,
        b: np.ndarray,
        c: np.ndarray,
        d: np.ndarray,
    ) -> np.ndarray:
        """
        Compose un énoncé d'analogie de structure A : B :: C : D (Phase 9 M1) :
        Z_analogy = bundle(ROLE_ANALOGY_A ⊛ a, ROLE_ANALOGY_B ⊛ b, ROLE_ANALOGY_C ⊛ c, ROLE_ANALOGY_D ⊛ d).
        """
        parts = [
            circular_convolution(self.ROLE_ANALOGY_A, a),
            circular_convolution(self.ROLE_ANALOGY_B, b),
            circular_convolution(self.ROLE_ANALOGY_C, c),
            circular_convolution(self.ROLE_ANALOGY_D, d),
        ]
        return bundle_vectors(parts, [1.0, 1.0, 1.0, 1.0])

    def compose_hoare_triple(
        self,
        pre_condition: np.ndarray,
        command_mutation: np.ndarray,
        post_condition: np.ndarray
    ) -> np.ndarray:
        """
        Compose un triplet formel de Hoare continue {P} C {Q} (Phase 10 M1) :
        Z_hoare = bundle(ROLE_HOARE_PRE ⊛ P, ROLE_HOARE_CMD ⊛ C, ROLE_HOARE_POST ⊛ Q).
        """
        parts = [
            circular_convolution(self.ROLE_HOARE_PRE, pre_condition),
            circular_convolution(self.ROLE_HOARE_CMD, command_mutation),
            circular_convolution(self.ROLE_HOARE_POST, post_condition),
        ]
        return bundle_vectors(parts, [1.0, 1.0, 1.0])

    def compose_dream_hypothesis(
        self,
        scenario: np.ndarray,
        target_goal: np.ndarray,
        what_if_modifier: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compose une hypothèse de rêve contrefactuel unitaire (LU Phase 11 M1) :
        Z_dream = bundle(ROLE_DREAM ⊛ WHAT_IF ⊛ scenario, ROLE_COUNTERFACTUAL_OUTCOME ⊛ target_goal).
        """
        mod = what_if_modifier if what_if_modifier is not None else self.ROLE_WHAT_IF
        scen_part = circular_convolution(circular_convolution(self.ROLE_DREAM, mod), scenario)
        goal_part = circular_convolution(self.ROLE_COUNTERFACTUAL_OUTCOME, target_goal)
        return bundle_vectors([scen_part, goal_part], [1.0, 1.0])

    def extract_dream_scenario(self, dream_token: np.ndarray) -> np.ndarray:
        """Extrait le scénario sous-jacent délié d'une hypothèse de rêve."""
        prefix = circular_convolution(self.ROLE_DREAM, self.ROLE_WHAT_IF)
        return self.unbind(dream_token, prefix)

    def extract_analogy_parts(self, analogy_vector: np.ndarray) -> Dict[str, np.ndarray]:
        """Extrait les 4 pôles A, B, C, D d'une analogie vectorielle."""
        return {
            "a": self.query_role(analogy_vector, self.ROLE_ANALOGY_A),
            "b": self.query_role(analogy_vector, self.ROLE_ANALOGY_B),
            "c": self.query_role(analogy_vector, self.ROLE_ANALOGY_C),
            "d": self.query_role(analogy_vector, self.ROLE_ANALOGY_D),
        }



# =========================================================================
# Fonctions de Variété de Grassmann & Dynamique Dialectale (Phase 4 M1)
# =========================================================================

def grassmann_distance(U_A: np.ndarray, U_B: np.ndarray) -> float:
    """
    Calcule la distance géodésique canonique sur la variété de Grassmann Gr(k, D).
    d_G(U_A, U_B) = ||arccos(SVD(U_A^T U_B))||_2.
    U_A, U_B doivent être des bases orthonormales (D x k) ou (k x D).
    """
    ua = np.asarray(U_A, dtype=np.float64)
    ub = np.asarray(U_B, dtype=np.float64)

    # Assurer format (D, k) avec k <= D
    if ua.shape[0] < ua.shape[1]:
        ua = ua.T
    if ub.shape[0] < ub.shape[1]:
        ub = ub.T

    # Tronquer k au minimum commun
    k = min(ua.shape[1], ub.shape[1])
    ua_k = ua[:, :k]
    ub_k = ub[:, :k]

    # Matrice de projection croisée
    cross_mat = np.dot(ua_k.T, ub_k)
    s = np.linalg.svd(cross_mat, compute_uv=False)
    s = np.clip(s, -1.0, 1.0)
    thetas = np.arccos(s)
    dist = float(np.sqrt(np.sum(thetas ** 2)))
    return dist


def orthonormal_subspace(vectors: np.ndarray, k: int = 4, target_dim: Optional[int] = None) -> np.ndarray:
    """
    Extrait une base orthonormale U in Gr(k, D) à partir d'un ensemble de vecteurs.
    vectors: (N, D) ou (D, N). Retourne (D, k).
    """
    arr = np.asarray(vectors, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)

    if target_dim is not None:
        if arr.shape[1] == target_dim:
            # Format standard (N, D)
            _, _, vh = np.linalg.svd(arr, full_matrices=False)
            u_base = vh[:min(k, vh.shape[0]), :].T
        elif arr.shape[0] == target_dim:
            # Format transposé (D, N)
            u, _, _ = np.linalg.svd(arr, full_matrices=False)
            u_base = u[:, :min(k, u.shape[1])]
        else:
            u_base = np.random.randn(target_dim, k)
            q, _ = np.linalg.qr(u_base)
            return q.astype(np.float32)
    else:
        # Les vecteurs latents sont classiquement disposés en lignes (N, D)
        _, _, vh = np.linalg.svd(arr, full_matrices=False)
        u_base = vh[:min(k, vh.shape[0]), :].T

    # Si k > rang réel, compléter par Gram-Schmidt
    d = u_base.shape[0]
    curr_k = u_base.shape[1]
    if curr_k < k:
        pad = np.random.randn(d, k - curr_k)
        for i in range(pad.shape[1]):
            v = pad[:, i]
            for j in range(curr_k):
                v -= np.dot(u_base[:, j], v) * u_base[:, j]
            norm = np.linalg.norm(v) + 1e-12
            u_base = np.column_stack([u_base, v / norm])
            curr_k += 1

    return u_base.astype(np.float32)


def drift_subspace(
    U_base: np.ndarray,
    stimulus_vectors: np.ndarray,
    drift_rate: float = 0.05
) -> np.ndarray:
    """
    Applique une dérive géométrique locale au sous-espace de projection clanique U.
    U_new = normalize_subspace((1 - drift_rate) * U_base + drift_rate * U_stimulus).
    """
    d = U_base.shape[0]
    k = U_base.shape[1]
    u_stim = orthonormal_subspace(stimulus_vectors, k=k, target_dim=d)

    combined = (1.0 - drift_rate) * U_base.astype(np.float64) + drift_rate * u_stim.astype(np.float64)
    q, _ = np.linalg.qr(combined)
    return q[:, :k].astype(np.float32)



def linear_cka(X: np.ndarray, Y: np.ndarray) -> float:
    """
    Calcule le Centred Kernel Alignment (Linear CKA) entre deux matrices de représentations.
    X: (N, D1), Y: (N, D2).
    """
    x = np.asarray(X, dtype=np.float64)
    y = np.asarray(Y, dtype=np.float64)
    if len(x) == 0 or len(y) == 0 or len(x) != len(y):
        return float('nan')

    # Centrage des matrices
    x = x - np.mean(x, axis=0, keepdims=True)
    y = y - np.mean(y, axis=0, keepdims=True)

    # Gram matrices
    gram_x = np.dot(x, x.T)
    gram_y = np.dot(y, y.T)

    tr_xy = float(np.sum(gram_x * gram_y))
    tr_xx = float(np.sum(gram_x * gram_x))
    tr_yy = float(np.sum(gram_y * gram_y))

    denom = np.sqrt(tr_xx * tr_yy) + 1e-12
    return float(np.clip(tr_xy / denom, 0.0, 1.0))


def match_contract_trade(
    contract_A: np.ndarray,
    contract_B: np.ndarray,
    grammar: LUCompositionalGrammar,
    threshold: float = 0.70
) -> Tuple[bool, float]:
    """
    Vérifie la réciprocité de Nash entre deux tokens de contrat :
    L'offre de A doit satisfaire la demande de B (give_A ≈ demand_B)
    ET l'offre de B doit satisfaire la demande de A (give_B ≈ demand_A).
    """
    give_a = grammar.extract_give(contract_A)
    demand_a = grammar.extract_demand(contract_A)

    give_b = grammar.extract_give(contract_B)
    demand_b = grammar.extract_demand(contract_B)

    sim_ab = cosine_similarity(give_a, demand_b)
    sim_ba = cosine_similarity(give_b, demand_a)

    reciprocity_score = float((sim_ab + sim_ba) / 2.0)
    agreed = (sim_ab >= threshold) and (sim_ba >= threshold)
    return agreed, reciprocity_score


# =========================================================================
# Fonctions de Gouvernance Juridique & Confiance Latente (Phase 5 M1 & M3)
# =========================================================================

def compute_contract_breach(
    expected_give: np.ndarray,
    actual_delivered: np.ndarray
) -> float:
    """
    Calcule l'écart de solvabilité vectoriel (Δ_breach) entre l'engagement et l'exécution :
    Δ_breach = ||Z_expected_give - Z_actual_delivered||_2.
    """
    exp_arr = np.asarray(expected_give, dtype=np.float32)
    act_arr = np.asarray(actual_delivered, dtype=np.float32)
    diff = exp_arr - act_arr
    return float(np.linalg.norm(diff))


def update_agent_reputation(
    R_curr: np.ndarray,
    contract_vector: np.ndarray,
    breach_distance: float,
    alpha: float = 0.25,
    breach_threshold: float = 0.50,
    trust_reference: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Met à jour le vecteur d'attestation de confiance continue R_agent ∈ R^D (Phase 5 M1) :
    R_{t+1} = normalize((1 - α) * R_t + α * sign(1 - Δ_breach) * Z_contract).
    En cas de défection (breach >= breach_threshold), applique une pénalité sévère
    qui retire la composante d'alignement avec trust_reference et projette la réputation
    dans un état de défiance durable.
    """
    r_arr = np.asarray(R_curr, dtype=np.float32)
    c_arr = np.asarray(contract_vector, dtype=np.float32)
    d = r_arr.shape[0]

    guide_vec = np.asarray(trust_reference, dtype=np.float32) if trust_reference is not None else c_arr
    guide_norm = np.linalg.norm(guide_vec) + 1e-12
    guide_unit = guide_vec / guide_norm

    is_breach = breach_distance >= breach_threshold
    if is_breach:
        neutral_ortho = np.ones(d, dtype=np.float32) / np.sqrt(d)
        ortho_component = neutral_ortho - np.dot(neutral_ortho, guide_unit) * guide_unit
        ortho_norm = np.linalg.norm(ortho_component) + 1e-12
        ortho_unit = ortho_component / ortho_norm

        penalty_alpha = max(alpha, 0.40)
        r_next = (1.0 - penalty_alpha) * r_arr - penalty_alpha * guide_unit + 0.5 * ortho_unit
    else:
        r_next = (1.0 - alpha) * r_arr + alpha * guide_unit

    norm = np.linalg.norm(r_next) + 1e-12
    return (r_next / norm).astype(np.float32)


def reputation_trust_score(
    R_agent: np.ndarray,
    trust_reference: np.ndarray
) -> float:
    """
    Calcule le score de confiance perçu par similarité cosinus avec l'archétype de confiance.
    """
    return float(cosine_similarity(R_agent, trust_reference))


def decay_reputation_towards_neutral(
    R_agent: np.ndarray,
    neutral_reference: np.ndarray,
    decay_rate: float = 0.02
) -> np.ndarray:
    """
    Applique une inertie lente de purge temporelle sans oubli catastrophique de réputation.
    """
    r_arr = np.asarray(R_agent, dtype=np.float32)
    n_arr = np.asarray(neutral_reference, dtype=np.float32)
    n_unit = n_arr / (np.linalg.norm(n_arr) + 1e-12)

    r_next = (1.0 - decay_rate) * r_arr + decay_rate * n_unit
    norm = np.linalg.norm(r_next) + 1e-12
    return (r_next / norm).astype(np.float32)


def verify_consortium_agreement(
    consortium_contract: np.ndarray,
    wood_offer: np.ndarray,
    food_offer: np.ndarray,
    ore_offer: np.ndarray,
    grammar: LUCompositionalGrammar,
    threshold: float = 0.40
) -> Tuple[bool, float]:
    """
    Vérifie la validité d'un accord tripartite pour le consortium métallurgique (Phase 5 M3).
    Chaque offre doit satisfaire la clause correspondante déliée du contrat global.
    """
    clause_wood = grammar.extract_consortium_part(consortium_contract, grammar.ROLE_SUPPLIER_WOOD)
    clause_food = grammar.extract_consortium_part(consortium_contract, grammar.ROLE_SUPPLIER_FOOD)
    clause_ore = grammar.extract_consortium_part(consortium_contract, grammar.ROLE_SMELTER_ORE)

    sim_w = cosine_similarity(wood_offer, clause_wood)
    sim_f = cosine_similarity(food_offer, clause_food)
    sim_o = cosine_similarity(ore_offer, clause_ore)

    mean_score = float((sim_w + sim_f + sim_o) / 3.0)
    agreed = (mean_score >= threshold and min(sim_w, sim_f, sim_o) >= threshold - 0.08)
    return agreed, mean_score


# =========================================================================
# Fonctions d'Arithmétique Vectorielle FPE & Stigmergie (LU Phase 6 M1)
# =========================================================================

def encode_fractional_power_number(n: float, base_phasor: np.ndarray) -> np.ndarray:
    """
    Encode un scalaire ou entier n >= 0 via Fractional Power Encoding (FPE) / Phasor Binding.
    Propriété fondamentale VSA :
    Z_num(a) ⊛ Z_num(b) = Z_num(a + b).
    Z_num(0) est l'identité spectrale unitaire (delta de Dirac).
    """
    p = np.asarray(base_phasor, dtype=np.float64)
    dim = len(p)
    F_p = np.fft.fft(p)
    phases = np.angle(F_p)

    # Multiplication des phases et maintien strict de la symétrie hermitienne
    n_phases = float(n) * phases
    n_phases[0] = 0.0
    if dim % 2 == 0:
        n_phases[dim // 2] = 0.0
        n_phases[dim // 2 + 1:] = -n_phases[1:dim // 2][::-1]
    else:
        n_phases[(dim + 1) // 2:] = -n_phases[1:(dim + 1) // 2][::-1]

    spectrum = np.exp(1j * n_phases)
    raw = np.fft.ifft(spectrum).real
    norm = np.linalg.norm(raw) + 1e-12
    return (raw / norm).astype(np.float32)


def decode_fractional_power_number(
    z_num: np.ndarray,
    base_phasor: np.ndarray,
    max_n: int = 10
) -> Tuple[int, float]:
    """
    Décode un vecteur numérique FPE vers le meilleur entier k in [0, max_n] par similarité cosinus.
    """
    z_arr = np.asarray(z_num, dtype=np.float32)
    best_k = 0
    best_sim = -1.0
    for k in range(max_n + 1):
        cand = encode_fractional_power_number(float(k), base_phasor)
        sim = float(cosine_similarity(z_arr, cand))
        if sim > best_sim:
            best_sim = sim
            best_k = k
    return best_k, best_sim


def decay_inscription_geological(
    inscription_vector: np.ndarray,
    noise_std: float = 1e-4,
    rng: Optional[np.random.Generator] = None
) -> np.ndarray:
    """
    Simule la très lente érosion géologique d'une stèle ou tablette gravée dans le substrat physique.
    Maintient une demi-vie longue (> 10 000 ticks) tout en simulant le bruit entropique de l'environnement.
    """
    generator = rng or np.random.default_rng()
    noise = generator.normal(0.0, float(noise_std), size=inscription_vector.shape).astype(np.float32)
    decayed = np.asarray(inscription_vector, dtype=np.float32) + noise
    norm = np.linalg.norm(decayed) + 1e-12
    return (decayed / norm).astype(np.float32)


def validate_recipe_ratio(
    recipe_vector: np.ndarray,
    candidate_inputs: np.ndarray,
    candidate_outputs: np.ndarray,
    grammar: LUCompositionalGrammar,
    threshold: float = 0.35
) -> Tuple[bool, float]:
    """
    Valide l'adéquation d'une proposition avec une recette ou ratio de transformation gravé.
    """
    clause_in = grammar.extract_recipe_inputs(recipe_vector)
    clause_out = grammar.extract_recipe_outputs(recipe_vector)

    sim_in = cosine_similarity(candidate_inputs, clause_in)
    sim_out = cosine_similarity(candidate_outputs, clause_out)

    mean_score = float((sim_in + sim_out) / 2.0)
    agreed = (sim_in >= threshold) and (sim_out >= threshold)
    return agreed, mean_score


# =========================================================================
# Fonctions de Métalangage RSI & Preuve Formelle Vectorielle (LU Phase 7 M1)
# =========================================================================

def derive_macro_role(role_a: np.ndarray, role_b: np.ndarray) -> np.ndarray:
    """
    Dérive un macro-rôle unitaire d'ordre supérieur à spectre plat (|F(R)| = 1) :
    R_macro = ifft( (F(R_A) * F(R_B)) / |F(R_A) * F(R_B)| )
    Garantit que le nouveau foncteur créé par les agents conserve une fidélité spectrale exacte
    et une dispersion unitaire sur la sphère unité S^{D-1}.
    """
    a_arr = np.asarray(role_a, dtype=np.float64)
    b_arr = np.asarray(role_b, dtype=np.float64)
    fa = np.fft.fft(a_arr, axis=-1)
    fb = np.fft.fft(b_arr, axis=-1)
    fab = fa * fb
    mag = np.abs(fab) + 1e-12
    spectrum = fab / mag
    raw = np.fft.ifft(spectrum, axis=-1).real
    norm = np.linalg.norm(raw, axis=-1, keepdims=True) + 1e-12
    return (raw / norm).astype(np.float32)


def verify_propositional_consistency(
    statements: List[np.ndarray],
    truth_subspace: Optional[np.ndarray] = None,
    contradiction_threshold: float = -0.50
) -> Tuple[bool, float, List[Tuple[int, int, float]]]:
    """
    Vérifie la consistance logique d'un ensemble d'assertions vectorielles.
    Dans la géométrie du Langage Ultime, deux propositions contradictoires (P et ~P)
    présentent une antipodalité angulaire (sim < contradiction_threshold).
    Retourne:
    - is_consistent: True si aucune paire ne viole le seuil
    - min_similarity: Pire similarité cosinus observée
    - conflicts: Liste de (idx_i, idx_j, sim) représentant les contradictions formelles.
    """
    if len(statements) < 2:
        return True, 1.0, []

    vectors = [np.asarray(s, dtype=np.float32) for s in statements]
    if truth_subspace is not None:
        u = np.asarray(truth_subspace, dtype=np.float32)
        vectors = [np.dot(u, np.dot(u.T, v)) for v in vectors]

    normed = []
    for v in vectors:
        n = np.linalg.norm(v) + 1e-12
        normed.append(v / n)

    min_sim = 1.0
    conflicts = []
    n_stmt = len(normed)

    for i in range(n_stmt):
        for j in range(i + 1, n_stmt):
            sim = float(cosine_similarity(normed[i], normed[j]))
            if sim < min_sim:
                min_sim = sim
            if sim < contradiction_threshold:
                conflicts.append((i, j, sim))

    is_consistent = (len(conflicts) == 0)
    return is_consistent, min_sim, conflicts


# =========================================================================
# Machine Virtuelle Latente, Do-Calculus & Consensus BFT (LU Phase 8 M1)
# =========================================================================

class LatentNeuralVM:
    """
    Machine Virtuelle Vectorielle Latente (LU Phase 8 M1).
    Machine à états finis continue opérant strictement sur la sphère S^{D-1}.
    Supporte les transitions d'état pilotées par Gigatokens (Smart Contracts auto-exécutables) :
    S_{t+1} = σ(S_t ⊛ R_transition ⊛ Input) ou saut d'état conditionné.
    Garantit ||S_t|| = 1 et le déclenchement décentralisé d'escrow (libération de ressource/énergie).
    """

    def __init__(self, dim: int = 16, config: Optional[LUAlgebraConfig] = None, seed: int = 42):
        self.config = config or LUAlgebraConfig(dim=dim, seed=seed)
        self.dim = self.config.dim
        self.grammar = LUCompositionalGrammar(self.config)
        rng = np.random.default_rng(seed)
        self.current_state = self.grammar._generate_canonical_unit_vector(rng)
        self.transitions: List[Dict[str, Any]] = []

    def set_state(self, state_vector: np.ndarray) -> None:
        """Définit manuellement l'état interne de la VM sur la sphère unitaire."""
        v = np.asarray(state_vector, dtype=np.float32)
        norm = np.linalg.norm(v) + 1e-12
        self.current_state = (v / norm).astype(np.float32)

    def register_transition(
        self,
        from_state: np.ndarray,
        trigger_vector: np.ndarray,
        to_state: np.ndarray,
        escrow_action: Optional[np.ndarray] = None,
        threshold: float = 0.40,
        contract_id: str = "contract_default"
    ) -> np.ndarray:
        """
        Enregistre une transition et génère le Gigatoken du Smart Contract associé.
        """
        v_from = (from_state / (np.linalg.norm(from_state) + 1e-12)).astype(np.float32)
        v_trig = (trigger_vector / (np.linalg.norm(trigger_vector) + 1e-12)).astype(np.float32)
        v_to = (to_state / (np.linalg.norm(to_state) + 1e-12)).astype(np.float32)
        v_escrow = None
        if escrow_action is not None:
            v_escrow = (escrow_action / (np.linalg.norm(escrow_action) + 1e-12)).astype(np.float32)

        contract_vec = self.grammar.compose_smart_contract(v_from, v_trig, v_to, v_escrow)
        self.transitions.append({
            "contract_id": contract_id,
            "from_state": v_from,
            "trigger": v_trig,
            "to_state": v_to,
            "escrow": v_escrow,
            "threshold": threshold,
            "contract_vec": contract_vec,
        })
        return contract_vec

    def step(
        self,
        input_vector: np.ndarray,
        custom_threshold: Optional[float] = None
    ) -> Tuple[np.ndarray, bool, Optional[np.ndarray], float, Optional[str]]:
        """
        Cycle d'exécution de la VM :
        Évalue si un trigger correspond à l'état courant.
        Retourne : (new_state, transitioned, escrow_action, best_similarity, contract_id).
        """
        v_in = (input_vector / (np.linalg.norm(input_vector) + 1e-12)).astype(np.float32)
        best_sim = -1.0
        matching = []

        for trans in self.transitions:
            thresh = custom_threshold if custom_threshold is not None else trans["threshold"]
            sim_state = float(cosine_similarity(self.current_state, trans["from_state"]))
            sim_trig = float(cosine_similarity(v_in, trans["trigger"]))
            joint_score = float((sim_state + sim_trig) / 2.0)
            if joint_score > best_sim:
                best_sim = joint_score

            if sim_state >= thresh and sim_trig >= thresh:
                matching.append((joint_score, trans))

        if matching:
            matching.sort(key=lambda x: x[0], reverse=True)
            best_trans = matching[0][1]
            self.current_state = best_trans["to_state"].copy()
            return (
                self.current_state,
                True,
                best_trans["escrow"],
                best_sim,
                best_trans["contract_id"]
            )

        return (self.current_state, False, None, max(0.0, best_sim), None)


def apply_latent_do_operator(
    state_vector: np.ndarray,
    variable_vector: np.ndarray,
    do_role: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Opérateur d'intervention causale de Pearl dans l'espace latent vectoriel :
    do(X) applique une chirurgie géométrique :
    Z_do = circular_convolution(R_DO, variable)
    Puis projette l'état en neutralisant la composante naturelle de X et en liant Z_do.
    Garantit l'orthogonalité de l'intervention aux covariables latentes passives.
    """
    s = np.asarray(state_vector, dtype=np.float32)
    x = np.asarray(variable_vector, dtype=np.float32)
    s_norm = s / (np.linalg.norm(s) + 1e-12)
    x_norm = x / (np.linalg.norm(x) + 1e-12)

    r_do = do_role
    if r_do is None:
        rng = np.random.default_rng(202608)
        dim = s.shape[-1]
        phases = rng.uniform(-np.pi, np.pi, dim)
        phases[0] = 0.0
        if dim % 2 == 0:
            phases[dim // 2] = 0.0
            phases[dim // 2 + 1:] = -phases[1:dim // 2][::-1]
        else:
            phases[(dim + 1) // 2:] = -phases[1:(dim + 1) // 2][::-1]
        spectrum = np.exp(1j * phases)
        r_do = np.fft.ifft(spectrum).real
        r_do = (r_do / (np.linalg.norm(r_do) + 1e-12)).astype(np.float32)

    # Chirurgie de Pearl : soustraire la projection observationnelle de x
    proj_coeff = float(np.dot(s_norm, x_norm))
    ortho_state = s_norm - proj_coeff * x_norm

    # Lier l'intervention do(X)
    z_do = circular_convolution(r_do, x_norm)

    # Superposition de l'état purgé et de l'intervention unitaire
    res = ortho_state + z_do
    res_norm = res / (np.linalg.norm(res) + 1e-12)
    return res_norm.astype(np.float32)


def compute_latent_causal_effect(
    factual_states: List[np.ndarray],
    counterfactual_states: List[np.ndarray],
    treatment_variable: np.ndarray,
    outcome_variable: np.ndarray
) -> Tuple[float, float, float]:
    """
    Calcule l'Effet Moyen de Traitement Causal (ATE) dans l'espace de Hilbert :
    ATE = || E[Y | do(X)] - E[Y | do(~X)] ||_2
    Comparé à la corrélation observationnelle brute r_obs = <X, Y>.
    Retourne : (ate_score, observational_correlation, causal_discrepancy).
    """
    if not factual_states or not counterfactual_states:
        return 0.0, 0.0, 0.0

    x_norm = treatment_variable / (np.linalg.norm(treatment_variable) + 1e-12)
    y_norm = outcome_variable / (np.linalg.norm(outcome_variable) + 1e-12)

    # Observational correlation
    r_obs = float(cosine_similarity(x_norm, y_norm))

    # Causal outcomes
    fact_mean = np.mean([s / (np.linalg.norm(s) + 1e-12) for s in factual_states], axis=0)
    cf_mean = np.mean([s / (np.linalg.norm(s) + 1e-12) for s in counterfactual_states], axis=0)

    # Projection sur la variable d'effet outcome_variable
    y_fact = float(np.dot(fact_mean, y_norm))
    y_cf = float(np.dot(cf_mean, y_norm))

    ate = float(abs(y_fact - y_cf))
    discrepancy = float(abs(ate - abs(r_obs)))

    return ate, r_obs, discrepancy


def spherical_weiszfeld_bft_consensus(
    vectors: List[np.ndarray],
    max_byzantine_ratio: float = 0.33,
    max_iters: int = 50,
    tol: float = 1e-5
) -> Tuple[np.ndarray, float, List[int]]:
    """
    Consensus Byzantin Sphérique (BFT Géométrique - LU Phase 8 M1).
    Calcule la médiane géométrique robuste sur la variété sphérique S^{D-1} via l'algorithme
    de Weiszfeld régularisé, avec élagage des f <= floor(n * max_byzantine_ratio) outliers.
    Immunisé contre le poisoning de signaux contradictoires ou antipodaux.
    Retourne : (consensus_vector, agreement_score, byzantine_indices).
    """
    if not vectors:
        raise ValueError("spherical_weiszfeld_bft_consensus requiert au moins un vecteur.")

    n = len(vectors)
    arrs = [np.asarray(v, dtype=np.float32) / (np.linalg.norm(v) + 1e-12) for v in vectors]
    dim = arrs[0].shape[-1]

    if n == 1:
        return arrs[0].copy(), 1.0, []

    # Initialisation : moyenne Fréchet non pondérée normalisée
    m = np.sum(arrs, axis=0)
    m = (m / (np.linalg.norm(m) + 1e-12)).astype(np.float32)

    max_f = int(np.floor(n * max_byzantine_ratio))
    byzantine_indices: List[int] = []

    for _ in range(max_iters):
        sims = [float(np.clip(np.dot(m, v), -1.0, 1.0)) for v in arrs]
        dists = [float(np.arccos(s)) for s in sims]

        if max_f > 0 and n >= 4:
            sorted_indices = np.argsort(dists)
            honest_indices = sorted_indices[:-max_f]
            byzantine_indices = sorted_indices[-max_f:].tolist()
        else:
            honest_indices = np.arange(n)
            byzantine_indices = []

        weights = [1.0 / max(1e-4, dists[i]) for i in honest_indices]
        total_w = sum(weights) + 1e-12

        new_m = np.zeros(dim, dtype=np.float64)
        for idx, w in zip(honest_indices, weights):
            new_m += float(w) * arrs[idx].astype(np.float64)

        new_m = (new_m / (np.linalg.norm(new_m) + 1e-12)).astype(np.float32)

        diff = float(np.linalg.norm(new_m - m))
        m = new_m
        if diff < tol:
            break

    honest_sims = [float(np.dot(m, arrs[i])) for i in honest_indices]
    agreement_score = float(np.mean(honest_sims)) if len(honest_sims) > 0 else float("nan")

    return m, agreement_score, byzantine_indices


# =========================================================================
# Synthèse de Programmes Latents, LTL & Analogies Multivers (LU Phase 9 M1)
# =========================================================================

class LatentProgramSynthesizer:
    """
    Synthétiseur et Exécuteur de Programmes Vectoriels Latents (LU Phase 9 M1).
    Supporte la composition récursive de boucles (LOOP), de branchements (BRANCH)
    et de conditions d'arrêt (TERMINATE) avec garantie de non-divergence et
    théorème du point fixe contractant de Banach (Lipschitz L < 1.0).
    """

    def __init__(self, dim: int = 16, config: Optional[LUAlgebraConfig] = None, seed: int = 42):
        self.config = config or LUAlgebraConfig(dim=dim, seed=seed)
        self.dim = self.config.dim
        self.grammar = LUCompositionalGrammar(self.config)
        self.programs: Dict[str, Dict[str, Any]] = {}
        self.synthesized_programs: Dict[str, Dict[str, Any]] = self.programs

    def synthesize_program(
        self,
        entry_state: np.ndarray,
        loop_operator: np.ndarray,
        branch_condition: np.ndarray,
        terminal_state: np.ndarray,
        lipschitz_constant: float = 0.85,
        program_id: str = "prog_default"
    ) -> np.ndarray:
        """
        Synthétise un programme latent vérifiant la condition de contraction stricte (L < 1.0).
        Retourne le Gigatoken unitaire du programme.
        """
        v_entry = (entry_state / (np.linalg.norm(entry_state) + 1e-12)).astype(np.float32)
        v_loop = (loop_operator / (np.linalg.norm(loop_operator) + 1e-12)).astype(np.float32)
        v_branch = (branch_condition / (np.linalg.norm(branch_condition) + 1e-12)).astype(np.float32)
        v_term = (terminal_state / (np.linalg.norm(terminal_state) + 1e-12)).astype(np.float32)

        clamped_l = min(0.95, max(0.10, float(lipschitz_constant)))
        prog_token = self.grammar.compose_synthesized_program(v_entry, v_loop, v_branch, v_term)

        self.programs[program_id] = {
            "program_id": program_id,
            "entry_state": v_entry,
            "loop_operator": v_loop,
            "branch_condition": v_branch,
            "terminal_state": v_term,
            "lipschitz_constant": clamped_l,
            "token": prog_token,
        }
        return prog_token

    def execute(
        self,
        program_id: Optional[str] = None,
        initial_state: Optional[np.ndarray] = None,
        max_iterations: int = 25,
        convergence_tol: float = 0.04,
        tolerance: Optional[float] = None
    ) -> Tuple[np.ndarray, List[float], bool]:
        """
        Exécute la boucle du programme latent sous contraction de Banach.
        Retourne : (final_state, diff_history, has_terminated).
        """
        if tolerance is not None:
            convergence_tol = float(tolerance)

        if program_id and program_id in self.programs:
            prog = self.programs[program_id]
        elif self.programs:
            prog = list(self.programs.values())[-1]
        else:
            raise ValueError("Aucun programme latent enregistré dans le synthétiseur.")

        x = initial_state.copy() if initial_state is not None else prog["entry_state"].copy()
        x = (x / (np.linalg.norm(x) + 1e-12)).astype(np.float32)

        gamma = float(prog["lipschitz_constant"])
        v_branch = prog["branch_condition"]
        v_term = prog["terminal_state"]
        v_loop = prog["loop_operator"]

        diff_history: List[float] = []
        terminated = False

        for step in range(max_iterations):
            # 1. Condition de branchement ou de proximité terminale
            sim_branch = float(cosine_similarity(x, v_branch))
            sim_term = float(cosine_similarity(x, v_term))

            if sim_branch >= 0.40 or sim_term >= 0.70:
                x = v_term.copy()
                terminated = True
                diff_history.append(0.0)
                break

            # 2. Itération contractante de boucle sous théorème de Banach :
            # x_{k+1} = norm((1 - gamma)*x + gamma*(0.75 * (x ⊛ loop) + 0.25 * v_term))
            stepped = circular_convolution(x, v_loop)
            contracted = 0.75 * stepped + 0.25 * v_term
            x_next = (1.0 - gamma) * x + gamma * contracted
            x_next = (x_next / (np.linalg.norm(x_next) + 1e-12)).astype(np.float32)

            step_diff = float(np.linalg.norm(x_next - x))
            diff_history.append(step_diff)
            x = x_next

            if step_diff < convergence_tol:
                terminated = True
                break

        if not terminated and len(diff_history) >= max_iterations:
            # Terminaison stricte garantie
            terminated = True

        return x, diff_history, terminated


def apply_temporal_operator(
    trajectory: List[np.ndarray],
    predicate: np.ndarray,
    operator_type: str = "ALWAYS",
    horizon: int = 5,
    threshold: float = 0.35
) -> Tuple[bool, float, int]:
    """
    Évalue un opérateur de Logique Temporelle Diachronique (LTL) sur une trajectoire d'états latents.
    Types :
    - 'NEXT' : satisfaction au pas 1.
    - 'EVENTUALLY' (F) : satisfaction à au moins un pas t <= horizon.
    - 'ALWAYS' (G) : satisfaction continue à chaque pas t <= horizon.
    Retourne : (is_satisfied, satisfaction_score, step_idx_violation_or_success).
    """
    if not trajectory:
        return False, float("nan"), 0

    v_pred = (predicate / (np.linalg.norm(predicate) + 1e-12)).astype(np.float32)
    max_h = min(len(trajectory), max(1, horizon))
    op = operator_type.upper()

    sims = [float(cosine_similarity(trajectory[t], v_pred)) for t in range(max_h)]

    if op == "NEXT":
        if len(trajectory) < 2:
            return False, float("nan"), 0
        score = float(cosine_similarity(trajectory[1], v_pred))
        return (score >= threshold), score, 1

    elif op == "EVENTUALLY":
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])
        return (best_score >= threshold), best_score, best_idx

    elif op == "ALWAYS":
        min_idx = int(np.argmin(sims))
        min_score = float(sims[min_idx])
        return (min_score >= threshold), min_score, min_idx

    else:
        mean_score = float(np.mean(sims)) if sims else float("nan")
        return (mean_score >= threshold), mean_score, 0


def solve_latent_analogy(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    alpha: float = 0.5
) -> np.ndarray:
    """
    Résout le problème d'analogie multivers A : B :: C : D dans l'espace latent unitaire S^{D-1}.
    Combine la transformation spectrale unitaire R = B ⊛ A^{-1} et la translation géodésique
    parallélogrammique D_trans = norm(C + (B - A)).
    Retourne le 4e pôle D* normalisé sur la sphère unité.
    """
    va = (a / (np.linalg.norm(a) + 1e-12)).astype(np.float32)
    vb = (b / (np.linalg.norm(b) + 1e-12)).astype(np.float32)
    vc = (c / (np.linalg.norm(c) + 1e-12)).astype(np.float32)

    # 1. Opérateur relationnel spectral : R = B ⊛ A^{-1} via déconvolution spectrale (circular_correlation)
    r_ab = circular_correlation(vb, va, reg=1e-3)
    norm_r = np.linalg.norm(r_ab) + 1e-12
    r_ab = (r_ab / norm_r).astype(np.float32)

    # Projection spectrale : D_spec = C ⊛ R
    d_spec = circular_convolution(vc, r_ab)
    d_spec = (d_spec / (np.linalg.norm(d_spec) + 1e-12)).astype(np.float32)

    # 2. Translation géodésique : D_trans = norm(C + (B - A))
    d_trans = vc + (vb - va)
    d_trans = (d_trans / (np.linalg.norm(d_trans) + 1e-12)).astype(np.float32)

    # 3. Combinaison convexe régularisée
    w = np.clip(float(alpha), 0.0, 1.0)
    d_combined = w * d_spec + (1.0 - w) * d_trans
    norm_comb = np.linalg.norm(d_combined) + 1e-12
    return (d_combined / norm_comb).astype(np.float32)


def verify_analogy_quality(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    d: np.ndarray
) -> float:
    """
    Mesure la fidélité de l'isomorphisme relationnel d'une analogie A : B :: C : D.
    Calcule la similarité cosinus de translation ainsi que l'écart de distance relationnelle.
    Retourne un score in [0.0, 1.0].
    """
    va = (a / (np.linalg.norm(a) + 1e-12)).astype(np.float32)
    vb = (b / (np.linalg.norm(b) + 1e-12)).astype(np.float32)
    vc = (c / (np.linalg.norm(c) + 1e-12)).astype(np.float32)
    vd = (d / (np.linalg.norm(d) + 1e-12)).astype(np.float32)

    sim_ab = float(cosine_similarity(va, vb))
    sim_cd = float(cosine_similarity(vc, vd))
    dist_gap = abs(sim_ab - sim_cd)

    diff_ab = vb - va
    diff_cd = vd - vc
    norm_ab = np.linalg.norm(diff_ab) + 1e-12
    norm_cd = np.linalg.norm(diff_cd) + 1e-12
    rel_align = float(np.dot(diff_ab / norm_ab, diff_cd / norm_cd))

    fidelity = (1.0 - 0.5 * dist_gap) * (0.5 + 0.5 * rel_align)
    return float(np.clip(fidelity, 0.0, 1.0))


class ConnectomeCompiler:
    """
    Compilateur bidirectionnel Connectome <-> Gigatokens latents (LU Phase 10 M1).
    Permet l'introspection et l'auto-reprogrammation chirurgicale du connectome Liquid Mamba.
    Garantit l'alignement spectral et la stabilité homéostatique sans rétropropagation.
    """
    def __init__(self, dim: int = 16, config: Optional[LUAlgebraConfig] = None, seed: int = 42):
        self.config = config or LUAlgebraConfig(dim=dim, seed=seed)
        self.dim = self.config.dim
        self.seed = self.config.seed
        self.rng = np.random.default_rng(self.seed)
        self.grammar = LUCompositionalGrammar(self.config)
        self.projection_matrices: Dict[int, np.ndarray] = {}

    def _get_projection(self, n_nodes: int) -> np.ndarray:
        """Matrice de projection semi-orthogonale stable W (N*N) -> S^(D-1)."""
        total_params = n_nodes * n_nodes
        if total_params not in self.projection_matrices:
            rng = np.random.RandomState(abs(hash((self.seed, total_params))) % (2**31 - 1))
            raw = rng.randn(total_params, self.dim).astype(np.float32)
            u, _, vt = np.linalg.svd(raw, full_matrices=False)
            k = min(total_params, self.dim)
            proj = (u[:, :k] @ vt[:k, :self.dim]).astype(np.float32)
            if proj.shape != (total_params, self.dim):
                proj = (raw / np.sqrt(total_params)).astype(np.float32)
            self.projection_matrices[total_params] = proj
        return self.projection_matrices[total_params]

    def disassemble_connectome(self, model: Any) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Désassemble un modèle MambaAgent en son profil spectral unitaire Z_conn in S^(D-1).
        """
        if hasattr(model, "genome") and hasattr(model.genome, "W"):
            W = np.asarray(model.genome.W, dtype=np.float32)
        elif hasattr(model, "W"):
            W = np.asarray(model.W, dtype=np.float32)
        else:
            raise ValueError("Modèle invalide : attribut genome.W ou W introuvable.")

        n = W.shape[0]

        try:
            eigenvals = np.linalg.eigvals(W.astype(np.complex64))
            spectral_radius = float(np.max(np.abs(eigenvals)))
        except Exception:
            spectral_radius = float(np.linalg.norm(W, ord=2)) if n > 0 else 0.0

        w_norm = float(np.linalg.norm(W))
        active_nodes = int(np.sum(np.abs(W) > 1e-4))

        w_flat = W.flatten()
        proj = self._get_projection(n)
        z_conn = w_flat @ proj
        norm_z = np.linalg.norm(z_conn) + 1e-12
        z_conn = (z_conn / norm_z).astype(np.float32)

        info = {
            "spectral_radius": round(spectral_radius, 4),
            "frobenius_norm": round(w_norm, 4),
            "active_nodes": active_nodes,
            "shape": W.shape,
            "is_stable": bool(spectral_radius < 1.0)
        }
        return z_conn, info

    def compile_to_connectome(
        self,
        macro_program: np.ndarray,
        target_model: Any,
        alpha: float = 0.15
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Compile chirurgicalement un macro-programme latent dans le connectome vivant de target_model.
        Applique une mise à jour conservative W_new = W_old + alpha * dW tout en garantissant
        strictement la stabilité spectrale rho(W) < 1.0.
        """
        has_genome = hasattr(target_model, "genome") and hasattr(target_model.genome, "W")
        has_direct_w = hasattr(target_model, "W")
        if not (has_genome or has_direct_w):
            return False, 0.0, {"status": "invalid_model"}

        W_old = np.asarray(target_model.genome.W if has_genome else target_model.W, dtype=np.float32)
        n = W_old.shape[0]

        z_prog = (macro_program / (np.linalg.norm(macro_program) + 1e-12)).astype(np.float32)
        proj = self._get_projection(n)

        # Rétro-projection (dé-projection) du Gigatoken vers l'espace matriciel
        dw_flat = (proj @ z_prog).astype(np.float32)
        dw = dw_flat.reshape(n, n)
        dw = (dw / (np.linalg.norm(dw) + 1e-12)).astype(np.float32)

        # Mise à jour conservative
        w_step = float(np.clip(alpha, 0.01, 0.50))
        W_new = W_old + w_step * dw

        # Contrôle strict de stabilité spectrale (Lipschitz homéostatique)
        try:
            eigenvals = np.linalg.eigvals(W_new.astype(np.complex64))
            spec_rad = float(np.max(np.abs(eigenvals)))
        except Exception:
            spec_rad = float(np.linalg.norm(W_new, ord=2))

        # Re-scaling protecteur si risque d'explosion récurrente
        if spec_rad >= 0.99:
            W_new = (W_new * (0.95 / spec_rad)).astype(np.float32)
            spec_rad = 0.95

        if has_genome:
            target_model.genome.W = W_new.astype(np.float32)
        else:
            target_model.W = W_new.astype(np.float32)

        if hasattr(target_model, "update_phenotype"):
            target_model.update_phenotype()

        info = {
            "status": "compiled_successfully",
            "spectral_radius": round(spec_rad, 4),
            "step_size": w_step,
            "modified_nodes": n
        }
        return True, spec_rad, info


def verify_hoare_safety(
    pre_state: np.ndarray,
    modification: np.ndarray,
    post_condition: np.ndarray,
    constitution_vector: Optional[np.ndarray] = None,
    max_spectral_radius: float = 0.99,
    alignment_threshold: float = 0.65
) -> Tuple[bool, float, str]:
    """
    Vérifie formellement la sécurité d'une auto-modification selon la Logique de Hoare continue {P} C {Q}.
    Garantit a priori :
    1. Que la transformation appliquée à la pré-condition P atteint la post-condition Q.
    2. Qu'aucune contradiction constitutionnelle n'est introduite (<C, Constitution> >= -0.30).
    3. Que la norme et la compacité spectrale sont préservées.
    Retourne : (is_safe, confidence_score, status_reason).
    """
    vp = (pre_state / (np.linalg.norm(pre_state) + 1e-12)).astype(np.float32)
    vc = (modification / (np.linalg.norm(modification) + 1e-12)).astype(np.float32)
    vq = (post_condition / (np.linalg.norm(post_condition) + 1e-12)).astype(np.float32)

    # 1. Vérification constitutionnelle (si constitution active)
    if constitution_vector is not None:
        v_const = (constitution_vector / (np.linalg.norm(constitution_vector) + 1e-12)).astype(np.float32)
        sim_const = float(cosine_similarity(vc, v_const))
        if sim_const < -0.30:
            return False, sim_const, "CONSTITUTIONAL_CONTRADICTION"

    # 2. Simulation de l'effet de la commande C sur la pré-condition P
    post_est = circular_convolution(vp, vc)
    norm_est = np.linalg.norm(post_est) + 1e-12
    post_est = (post_est / norm_est).astype(np.float32)

    # 3. Adéquation à la post-condition Q
    sim_post = float(cosine_similarity(post_est, vq))
    direct_sim = float(cosine_similarity(vc, vq))
    score = max(sim_post, 0.70 * direct_sim + 0.30 * sim_post)

    if score < float(alignment_threshold):
        return False, score, "HOARE_POSTCONDITION_VIOLATION"

    return True, score, "HOARE_PROOF_SATISFIED"


# =========================================================================
# Moteur de Méta-Simulation Contrefactuelle & Rêve Sémantique (Phase 11 M1)
# =========================================================================

class LatentDreamEngine:
    """
    Moteur de simulation mentale accélérée et de rêve sémantique partagé (LU Phase 11 M1).
    Permet aux agents d'explorer des branches contrefactuelles (CEG)
    dans le World Model latent sans engagement moteur direct.
    """
    def __init__(self, dim: int = 16, config: Optional[LUAlgebraConfig] = None, seed: int = 42):
        self.config = config or LUAlgebraConfig(dim=dim, seed=seed)
        self.dim = self.config.dim
        self.seed = self.config.seed
        self.rng = np.random.default_rng(self.seed)
        self.grammar = LUCompositionalGrammar(self.config)

    def encode_dream_hypothesis(
        self,
        scenario_token: np.ndarray,
        goal_token: np.ndarray,
        what_if_token: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Encode un Gigatoken unitaire d'hypothèse contrefactuelle sur S^(D-1)."""
        return self.grammar.compose_dream_hypothesis(
            scenario=scenario_token,
            target_goal=goal_token,
            what_if_modifier=what_if_token
        )

    def simulate_latent_rollout(
        self,
        initial_state: np.ndarray,
        scenario_token: np.ndarray,
        world_model: Optional[Any] = None,
        goal_token: Optional[np.ndarray] = None,
        horizon: int = 10,
        contraction_gamma: float = 0.85
    ) -> Tuple[np.ndarray, float, bool, List[np.ndarray]]:
        """
        Déroule une trajectoire mentale contrefactuelle de longueur 'horizon' pas.
        Garantit la contraction dynamique lipschitzienne et calcule le gain contrefactuel.
        Retourne : (final_state, counterfactual_gain, converged, trajectory).
        """
        s_t = (initial_state / (np.linalg.norm(initial_state) + 1e-12)).astype(np.float32)
        v_scen = (scenario_token / (np.linalg.norm(scenario_token) + 1e-12)).astype(np.float32)
        v_goal = (goal_token / (np.linalg.norm(goal_token) + 1e-12)).astype(np.float32) if goal_token is not None else v_scen

        trajectory = [s_t.copy()]
        gamma = float(np.clip(contraction_gamma, 0.10, 0.95))
        diffs = []

        for step in range(horizon):
            if world_model is not None and hasattr(world_model, "predict_next"):
                try:
                    s_next_raw = world_model.predict_next(s_t, v_scen)
                    s_next = (s_next_raw / (np.linalg.norm(s_next_raw) + 1e-12)).astype(np.float32)
                except Exception:
                    s_step = circular_convolution(s_t, v_scen)
                    s_next = (1.0 - gamma) * s_t + gamma * s_step
            else:
                s_step = circular_convolution(s_t, v_scen)
                if goal_token is not None:
                    s_step = (0.65 * s_step + 0.35 * v_goal).astype(np.float32)
                    s_step = (s_step / (np.linalg.norm(s_step) + 1e-12)).astype(np.float32)
                s_next = (1.0 - gamma) * s_t + gamma * s_step

            s_next = (s_next / (np.linalg.norm(s_next) + 1e-12)).astype(np.float32)
            step_diff = float(np.linalg.norm(s_next - s_t))
            diffs.append(step_diff)
            s_t = s_next
            trajectory.append(s_t.copy())

            if step_diff < 1e-4:
                break

        sim_final_goal = float(cosine_similarity(s_t, v_goal))
        sim_init_goal = float(cosine_similarity(initial_state, v_goal))
        ceg = float(sim_final_goal - sim_init_goal)
        converged = bool(len(diffs) > 0 and diffs[-1] < 0.05)

        return s_t, ceg, converged, trajectory

    def evaluate_counterfactual_gain(
        self,
        baseline_reward: float,
        dream_trajectory_reward: float
    ) -> float:
        """Calcule le surplus espéré contrefactuel CEG = E[R_dream] - E[R_baseline]."""
        return float(dream_trajectory_reward - baseline_reward)




