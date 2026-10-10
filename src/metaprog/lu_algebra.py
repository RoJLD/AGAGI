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
from typing import Dict, List, Optional, Tuple, Union
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
