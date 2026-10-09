"""
Module: lu_auto_translator.py
Projet: AGIseed / AGAGI (Branche de recherche LU)
Description: Auto-apprentissage et co-construction de traducteurs latents inter-modèles.
Permet à deux modèles ou agents hétérogènes d'apprendre conjointement à traduire
leurs états latents respectifs via cycle-consistency et alignement sur stimuli partagés.

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): AutoTranslatorConfig hyper-paramétrable.
- Commandement 2 (Modulaire): Découplé des architectures de réseau sous-jacentes.
- Commandement 3 (Haute Performance): Optimisation vectorisée en pur NumPy (SGD avec momentum / Adam-lite).
- Commandement 8 (Extensible): Extensible à des topologies asymétriques arbitraires.
- Commandement 9 (Stabilité Numérique): Gradient clipping, orthogonal initialization, guards NaN/Inf.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np


@dataclass
class AutoTranslatorConfig:
    """Hyperparamètres pour le co-apprentissage du traducteur latent."""
    dim_a: int = 64
    dim_b: int = 64
    learning_rate: float = 0.01
    momentum: float = 0.9
    cycle_lambda: float = 1.0       # Poids de la perte de cycle-consistance (A -> B -> A)
    align_lambda: float = 1.0       # Poids de la perte d'alignement direct
    l2_reg: float = 1e-4            # Régularisation L2 pour éviter les poids explosifs
    grad_clip: float = 5.0          # Norme max du gradient
    eps: float = 1e-8
    seed: int = 42


class MutualLatentTranslator:
    """
    Traducteur bidirectionnel auto-apprenant entre deux agents A et B.
    Apprend les matrices W_ab, b_ab et W_ba, b_ba sans exiger de ré-entraînement lourd.
    """

    def __init__(self, config: Optional[AutoTranslatorConfig] = None):
        self.config = config or AutoTranslatorConfig()
        rng = np.random.default_rng(self.config.seed)

        da, db = self.config.dim_a, self.config.dim_b

        # Initialisation quasi-orthogonale (évite le collapse trivial à 0)
        if da == db:
            h = rng.normal(0, 1.0, (da, da))
            q, _ = np.linalg.qr(h)
            self.W_ab = q.astype(np.float64)
            self.W_ba = q.T.astype(np.float64)
        else:
            scale = 1.0 / np.sqrt(max(da, db))
            self.W_ab = rng.normal(0, scale, (da, db)).astype(np.float64)
            self.W_ba = rng.normal(0, scale, (db, da)).astype(np.float64)

        self.b_ab = np.zeros((1, db), dtype=np.float64)
        self.b_ba = np.zeros((1, da), dtype=np.float64)

        # Buffers de momentum
        self.v_W_ab = np.zeros_like(self.W_ab)
        self.v_b_ab = np.zeros_like(self.b_ab)
        self.v_W_ba = np.zeros_like(self.W_ba)
        self.v_b_ba = np.zeros_like(self.b_ba)

        self.total_steps: int = 0

    def warmstart_spectral(self, anchors_a: np.ndarray, anchors_b: np.ndarray) -> "MutualLatentTranslator":
        """
        Initialisation spectrale SVD (Procruste) pour accélérer la convergence en haute dimension (D=64).
        Calibre instantanément W_ab et W_ba sur les directions principales de variance croisée.
        """
        za = np.asarray(anchors_a, dtype=np.float64)
        zb = np.asarray(anchors_b, dtype=np.float64)
        if za.shape[0] < 2 or zb.shape[0] < 2:
            return self

        za_c = za - np.mean(za, axis=0, keepdims=True)
        zb_c = zb - np.mean(zb, axis=0, keepdims=True)

        cross_cov = np.dot(za_c.T, zb_c)
        u, _, vt = np.linalg.svd(cross_cov, full_matrices=False)
        r = np.dot(u, vt)

        if self.config.dim_a == self.config.dim_b:
            self.W_ab = r
            self.W_ba = r.T
        else:
            k = min(self.config.dim_a, self.config.dim_b)
            self.W_ab = np.dot(u[:, :k], vt[:k, :])
            self.W_ba = self.W_ab.T

        self.b_ab = np.mean(zb, axis=0, keepdims=True) - np.dot(np.mean(za, axis=0, keepdims=True), self.W_ab)
        self.b_ba = np.mean(za, axis=0, keepdims=True) - np.dot(np.mean(zb, axis=0, keepdims=True), self.W_ba)

        self.v_W_ab.fill(0.0)
        self.v_b_ab.fill(0.0)
        self.v_W_ba.fill(0.0)
        self.v_b_ba.fill(0.0)
        return self

    def translate_a_to_b(self, z_a: np.ndarray) -> np.ndarray:
        """Traduit un vecteur ou un lot de vecteurs de l'Agent A vers l'Agent B."""
        arr = np.asarray(z_a, dtype=np.float64)
        is_1d = arr.ndim == 1
        if is_1d:
            arr = arr.reshape(1, -1)

        out = np.dot(arr, self.W_ab) + self.b_ab
        out = np.nan_to_num(out, nan=0.0, posinf=1.0, neginf=-1.0)
        return out[0] if is_1d else out

    def translate_b_to_a(self, z_b: np.ndarray) -> np.ndarray:
        """Traduit un vecteur ou un lot de vecteurs de l'Agent B vers l'Agent A."""
        arr = np.asarray(z_b, dtype=np.float64)
        is_1d = arr.ndim == 1
        if is_1d:
            arr = arr.reshape(1, -1)

        out = np.dot(arr, self.W_ba) + self.b_ba
        out = np.nan_to_num(out, nan=0.0, posinf=1.0, neginf=-1.0)
        return out[0] if is_1d else out

    def train_step(
        self,
        batch_z_a: np.ndarray,
        batch_z_b: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Exécute un pas de co-apprentissage vectorisé.
        - Si batch_z_b est fourni : apprentissage supervisé/aligné + cycle-consistance.
        - Si batch_z_b est None : apprentissage purement auto-supervisé via cycle-consistance A -> B -> A.
        """
        za = np.asarray(batch_z_a, dtype=np.float64)
        if za.ndim == 1:
            za = za.reshape(1, -1)
        n_samples = za.shape[0]

        has_paired_b = batch_z_b is not None
        if has_paired_b:
            zb = np.asarray(batch_z_b, dtype=np.float64)
            if zb.ndim == 1:
                zb = zb.reshape(1, -1)
        else:
            zb = None

        # --- 1. Forward Pass ---
        # A -> B
        pred_b = np.dot(za, self.W_ab) + self.b_ab
        # Cycle A -> B -> A
        cycle_a = np.dot(pred_b, self.W_ba) + self.b_ba

        loss_align_ab = 0.0
        loss_align_ba = 0.0
        grad_pred_b = np.zeros_like(pred_b)
        grad_W_ba = np.zeros_like(self.W_ba)
        grad_b_ba = np.zeros_like(self.b_ba)

        # Perte d'alignement supervisé (si disponible)
        if has_paired_b:
            diff_ab = pred_b - zb
            loss_align_ab = float(0.5 * np.mean(np.sum(diff_ab ** 2, axis=1)))
            grad_pred_b += (self.config.align_lambda / n_samples) * diff_ab

            # B -> A
            pred_a = np.dot(zb, self.W_ba) + self.b_ba
            diff_ba = pred_a - za
            loss_align_ba = float(0.5 * np.mean(np.sum(diff_ba ** 2, axis=1)))
            grad_W_ba += (self.config.align_lambda / n_samples) * np.dot(zb.T, diff_ba)
            grad_b_ba += (self.config.align_lambda / n_samples) * np.sum(diff_ba, axis=0, keepdims=True)

        # Perte de cycle-consistance : Cycle A -> B -> A == A
        diff_cycle_a = cycle_a - za
        loss_cycle_a = float(0.5 * np.mean(np.sum(diff_cycle_a ** 2, axis=1)))

        grad_cycle_a = (self.config.cycle_lambda / n_samples) * diff_cycle_a
        grad_W_ba += np.dot(pred_b.T, grad_cycle_a)
        grad_b_ba += np.sum(grad_cycle_a, axis=0, keepdims=True)

        grad_pred_b += np.dot(grad_cycle_a, self.W_ba.T)

        # Gradients pour W_ab et b_ab
        grad_W_ab = np.dot(za.T, grad_pred_b) + self.config.l2_reg * self.W_ab
        grad_b_ab = np.sum(grad_pred_b, axis=0, keepdims=True)
        grad_W_ba += self.config.l2_reg * self.W_ba

        # --- 2. Gradient Clipping (Commandement 9) ---
        for g in [grad_W_ab, grad_b_ab, grad_W_ba, grad_b_ba]:
            norm = np.linalg.norm(g)
            if norm > self.config.grad_clip:
                g *= (self.config.grad_clip / (norm + self.config.eps))

        # --- 3. SGD avec Momentum ---
        lr = self.config.learning_rate
        mom = self.config.momentum

        self.v_W_ab = mom * self.v_W_ab - lr * grad_W_ab
        self.b_ab_step = mom * self.v_b_ab - lr * grad_b_ab
        self.v_W_ba = mom * self.v_W_ba - lr * grad_W_ba
        self.v_b_ba = mom * self.v_b_ba - lr * grad_b_ba

        self.W_ab += self.v_W_ab
        self.b_ab += self.b_ab_step
        self.W_ba += self.v_W_ba
        self.b_ba += self.v_b_ba

        self.total_steps += 1

        total_loss = loss_cycle_a * self.config.cycle_lambda + (loss_align_ab + loss_align_ba) * self.config.align_lambda

        return {
            "total_loss": float(total_loss),
            "cycle_loss": float(loss_cycle_a),
            "align_loss": float(loss_align_ab + loss_align_ba),
        }

    def compute_mutual_fidelity(self, test_z_a: np.ndarray, test_z_b: np.ndarray) -> float:
        """Calcule la similarité cosinus moyenne croisée après traduction A -> B."""
        pred_b = self.translate_a_to_b(test_z_a)
        target_b = np.asarray(test_z_b, dtype=np.float64)

        norm_p = np.linalg.norm(pred_b, axis=1, keepdims=True) + self.config.eps
        norm_t = np.linalg.norm(target_b, axis=1, keepdims=True) + self.config.eps

        cosines = np.sum((pred_b / norm_p) * (target_b / norm_t), axis=1)
        return float(np.mean(cosines))
