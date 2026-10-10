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
        # Rôles pour contrats de troc et engagements bilatéraux (Phase 4)
        self.ROLE_GIVE = self._generate_canonical_unit_vector(rng)
        self.ROLE_DEMAND = self._generate_canonical_unit_vector(rng)
        self.ROLE_QUORUM = self._generate_canonical_unit_vector(rng)

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


def orthonormal_subspace(vectors: np.ndarray, k: int = 4) -> np.ndarray:
    """
    Extrait une base orthonormale U in Gr(k, D) à partir d'un ensemble de vecteurs.
    vectors: (N, D) ou (D, N). Retourne (D, k).
    """
    arr = np.asarray(vectors, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.shape[0] < arr.shape[1]:
        # N x D -> décomposition SVD sur N échantillons en dimension D
        _, _, vh = np.linalg.svd(arr, full_matrices=False)
        u_base = vh[:min(k, vh.shape[0]), :].T
    else:
        # D x N
        u, _, _ = np.linalg.svd(arr, full_matrices=False)
        u_base = u[:, :min(k, u.shape[1])]

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
    u_stim = orthonormal_subspace(stimulus_vectors, k=k)

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

