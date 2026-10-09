"""
Module: lu_measurement_bench.py
Projet: AGIseed / AGAGI (Territoire de recherche LU)
Description: Suite d'instruments de mesure scientifique et métrologie pour le Langage Ultime (LU).
Permet d'analyser et quantifier rigoureusement la communication continue en espace latent :
1. CKA (Centered Kernel Alignment) & Similarité Topologique de Mantel.
2. Erreur de Reconstruction de Cycle (Cycle-Consistency Gap).
3. Information Mutuelle Latente & Alignement Cosinus Directionnel.
4. Banc Comparatif A/B : Tokens Discrets vs Gigatokens Continus LU.

Conforme aux 12 Commandements AGIseed :
- Commandement 3 (Haute Performance): Calculs matriciels 100% NumPy vectorisés.
- Commandement 9 (Stabilité Numérique): Guards contre les matrices singulières, NaN/Inf et division par zéro.
- Commandement 14 & 15 (Validation par Simulation & PIU): Métriques quantifiables et comparatives A/B.
"""

from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional, Any
import numpy as np

from src.metaprog.lu_state_bridge import LUStateBridge, StateBridgeConfig
from src.metaprog.lu_auto_translator import MutualLatentTranslator, AutoTranslatorConfig


@dataclass
class LUMetricsReport:
    """Rapport métrologique complet pour une expérience de communication latente."""
    cka_score: float                   # Centered Kernel Alignment [0.0, 1.0]
    mantel_topological_corr: float     # Corrélation des distances de concepts [-1.0, 1.0]
    cycle_reconstruction_error: float  # Erreur L2 moyenne boucle fermée (A -> B -> A)
    directional_cosine_fidelity: float # Fidélité cosinus moyenne de traduction
    sample_size: int
    is_statistically_sound: bool


class LUMeasurementBench:
    """
    Instruments de mesure scientifique pour les espaces latents et le Langage Ultime.
    """

    @staticmethod
    def compute_linear_cka(X: np.ndarray, Y: np.ndarray, eps: float = 1e-9) -> float:
        """
        Calcule le CKA Linéaire (Centered Kernel Alignment) entre deux représentations latentes.
        CKA = HSIC(K, L) / sqrt(HSIC(K, K) * HSIC(L, L))
        Mesure si deux espaces de formes/dimensions différentes ont encodé la même structure relationnelle.
        """
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)

        if X.shape[0] != Y.shape[0]:
            raise ValueError(f"Incohérence du nombre d'échantillons: {X.shape[0]} vs {Y.shape[0]}")

        # Centrage des matrices d'activation
        X_c = X - np.mean(X, axis=0, keepdims=True)
        Y_c = Y - np.mean(Y, axis=0, keepdims=True)

        # Calcul HSIC linéaire efficace : tr(X_c X_c^T Y_c Y_c^T) = ||Y_c^T X_c||_F^2
        cross = np.dot(Y_c.T, X_c)
        hsic_xy = np.sum(cross ** 2)

        cross_xx = np.dot(X_c.T, X_c)
        hsic_xx = np.sum(cross_xx ** 2)

        cross_yy = np.dot(Y_c.T, Y_c)
        hsic_yy = np.sum(cross_yy ** 2)

        denom = np.sqrt(hsic_xx * hsic_yy)
        if denom < eps:
            return 0.0

        cka = float(hsic_xy / denom)
        return float(np.clip(cka, 0.0, 1.0))

    @staticmethod
    def compute_mantel_topological_similarity(
        X: np.ndarray,
        Y: np.ndarray,
        subsample: int = 150,
        eps: float = 1e-9
    ) -> float:
        """
        Calcule la similarité topologique de Mantel (corrélation de Pearson entre les matrices
        de distance euclidienne de deux espaces).
        Évalue si la géométrie relative des concepts est préservée entre les deux modèles.
        """
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)

        n = min(X.shape[0], subsample)
        if n < 4:
            return 0.0

        sub_X = X[:n]
        sub_Y = Y[:n]

        # Calcul vectorisé des matrices de distance (D_ij = ||x_i - x_j||)
        diff_X = sub_X[:, np.newaxis, :] - sub_X[np.newaxis, :, :]
        dist_X = np.linalg.norm(diff_X, axis=-1)

        diff_Y = sub_Y[:, np.newaxis, :] - sub_Y[np.newaxis, :, :]
        dist_Y = np.linalg.norm(diff_Y, axis=-1)

        # Extraction du triangle supérieur strict (paires distinctes)
        tri_idx = np.triu_indices(n, k=1)
        flat_dx = dist_X[tri_idx]
        flat_dy = dist_Y[tri_idx]

        # Corrélation de Pearson
        vx = flat_dx - np.mean(flat_dx)
        vy = flat_dy - np.mean(flat_dy)

        norm_x = np.linalg.norm(vx)
        norm_y = np.linalg.norm(vy)

        if norm_x < eps or norm_y < eps:
            return 0.0

        corr = float(np.dot(vx, vy) / (norm_x * norm_y))
        return float(np.clip(corr, -1.0, 1.0))

    @staticmethod
    def evaluate_translator_cycle_error(
        translator: MutualLatentTranslator,
        test_z_a: np.ndarray
    ) -> float:
        """
        Mesure l'erreur quadratique moyenne de cycle-consistance sur un jeu de test non vu.
        Erreur = mean(||T_ba(T_ab(z_a)) - z_a||_2)
        """
        za = np.asarray(test_z_a, dtype=np.float64)
        if za.ndim == 1:
            za = za.reshape(1, -1)

        pred_b = translator.translate_a_to_b(za)
        reconstructed_a = translator.translate_b_to_a(pred_b)

        errs = np.linalg.norm(reconstructed_a - za, axis=1)
        return float(np.mean(errs))

    @staticmethod
    def full_diagnostic_report(
        z_source: np.ndarray,
        z_target: np.ndarray,
        translator: Optional[MutualLatentTranslator] = None
    ) -> LUMetricsReport:
        """
        Génère un diagnostic métrologique complet pour deux espaces d'agents.
        """
        cka = LUMeasurementBench.compute_linear_cka(z_source, z_target)
        mantel = LUMeasurementBench.compute_mantel_topological_similarity(z_source, z_target)

        cycle_err = 0.0
        fidelity = 0.0

        if translator is not None:
            cycle_err = LUMeasurementBench.evaluate_translator_cycle_error(translator, z_source)
            fidelity = translator.compute_mutual_fidelity(z_source, z_target)
        else:
            # Calcul cosinus direct si dimensions identiques
            if z_source.shape[1] == z_target.shape[1]:
                ns = np.linalg.norm(z_source, axis=1, keepdims=True) + 1e-9
                nt = np.linalg.norm(z_target, axis=1, keepdims=True) + 1e-9
                fidelity = float(np.mean(np.sum((z_source / ns) * (z_target / nt), axis=1)))

        n_samples = z_source.shape[0]
        is_sound = (n_samples >= 12) and (not np.isnan(cka)) and (not np.isnan(mantel))

        return LUMetricsReport(
            cka_score=cka,
            mantel_topological_corr=mantel,
            cycle_reconstruction_error=cycle_err,
            directional_cosine_fidelity=fidelity,
            sample_size=n_samples,
            is_statistically_sound=is_sound,
        )

    @staticmethod
    def compare_discrete_vs_latent_transmission(
        concepts_matrix: np.ndarray,
        vocab_size: int = 16,
        noise_level: float = 0.05,
        seed: int = 42
    ) -> Dict[str, Any]:
        """
        Banc comparatif A/B :
        - Canal A (Discret) : Quantification en tokens 1D discrets (Argmax / Cluster downsampling)
        - Canal B (Latent LU) : Transmission continue d'un Gigatoken vectoriel unitaire bruité
        Mesure le taux de distorsion d'information (MSE de reconstruction et préservation de rang).
        """
        rng = np.random.default_rng(seed)
        n, dim = concepts_matrix.shape

        # 1. Canal Latent LU (Continu)
        latent_sent = concepts_matrix.copy()
        # Normalisation unitaire
        norms = np.linalg.norm(latent_sent, axis=1, keepdims=True) + 1e-9
        latent_sent = latent_sent / norms
        # Bruit de transmission
        latent_received = latent_sent + rng.normal(0, noise_level, size=latent_sent.shape)
        latent_received_normed = latent_received / (np.linalg.norm(latent_received, axis=1, keepdims=True) + 1e-9)
        latent_cosine_fidelity = float(np.mean(np.sum(latent_sent * latent_received_normed, axis=1)))
        latent_mse = float(np.mean((latent_sent - latent_received_normed) ** 2))

        # 2. Canal Discret (Downsampling 1D)
        # Projection vers le token le plus proche parmi un dictionnaire discret de taille vocab_size
        codebook = rng.normal(0, 1.0, size=(vocab_size, dim))
        codebook = codebook / (np.linalg.norm(codebook, axis=1, keepdims=True) + 1e-9)

        # Encodage en token discret (1D integer index)
        discrete_tokens = np.argmax(np.dot(latent_sent, codebook.T), axis=1)

        # Simulation d'erreur de transmission discrète (bit flip)
        error_mask = rng.uniform(0, 1, size=n) < noise_level
        received_tokens = discrete_tokens.copy()
        received_tokens[error_mask] = rng.integers(0, vocab_size, size=np.sum(error_mask))

        # Décodage discret -> vecteur reconstruit
        discrete_reconstructed = codebook[received_tokens]
        discrete_cosine_fidelity = float(np.mean(np.sum(latent_sent * discrete_reconstructed, axis=1)))
        discrete_mse = float(np.mean((latent_sent - discrete_reconstructed) ** 2))

        return {
            "latent_fidelity": latent_cosine_fidelity,
            "latent_mse": latent_mse,
            "discrete_fidelity": discrete_cosine_fidelity,
            "discrete_mse": discrete_mse,
            "fidelity_ratio_gain": float(latent_cosine_fidelity / (discrete_cosine_fidelity + 1e-9)),
            "entropy_loss_percentage": float(max(0.0, (1.0 - discrete_cosine_fidelity) * 100.0)),
        }
