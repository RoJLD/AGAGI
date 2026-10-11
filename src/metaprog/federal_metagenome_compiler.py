"""
src/metaprog/federal_metagenome_compiler.py — Méta-Génome Fédéral & Compilateur Évolutif (Arc 14 : Jalon M32).

Assure la synthèse continue du macro-génome civilisationnel unifié par distillation
des consensus d'essaim et des trajectoires des 3 mondes physiques, et compile de manière
sécurisée les directives latentes en micro-programmes NTM (Neural Turing Machine)
modulant chirurgicalement le connectome des agents.

Conforme aux 12 Commandements AGIseed :
- 1. Flexible (Dataclass FederalMetaGenomeConfig).
- 2. Modulaire (Découplage synthèse, compilation NTM et agent).
- 3. Haute Performance (NumPy vectorisé).
- 6. Sécurité & Isolation (Contrôle spectral strict, sandboxing).
- 7. Validation Rigoureuse (Test-Driven).
- 9. Stabilité Numérique (Garantie de non-divergence rho < 0.95).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

from src.metaprog.ntm_compiler import NTMProgramCompiler


@dataclass
class FederalMetaGenomeConfig:
    """Hyperparamètres pour le méta-génome fédéral et la compilation évolutive."""
    latent_dim: int = 64
    num_nodes: int = 172
    distillation_rate: float = 0.15
    max_spectral_radius: float = 0.95
    num_ntm_slots: int = 10
    mutation_scale: float = 0.20
    seed: int = 42
    eps: float = 1e-12


class FederalMetaGenomeSynthesizer:
    """
    Distillateur & Synthétiseur du macro-génome fédéral unifié.
    Condense l'expérience collective des 3 mondes dans un Gigatoken z_meta in S^(D-1)
    et une matrice connectomique canonique W_federal.
    """

    def __init__(self, config: Optional[FederalMetaGenomeConfig] = None):
        self.config = config or FederalMetaGenomeConfig()
        self.rng = np.random.RandomState(self.config.seed)

        # 1. Gigatoken méta-génome canonique unitaire
        v = self.rng.randn(self.config.latent_dim).astype(np.float32)
        norm_v = float(np.linalg.norm(v)) + self.config.eps
        self.z_meta = (v / norm_v).astype(np.float32)

        # 2. Matrice synaptique canonique W_federal à rayon spectral sous-unitaire
        raw_w = (self.rng.randn(self.config.num_nodes, self.config.num_nodes) * 0.05).astype(np.float32)
        self.W_federal = self._constrain_spectral_radius(raw_w, self.config.max_spectral_radius)

        self.version = 1
        self.distillations_count = 0

    def _constrain_spectral_radius(self, matrix: np.ndarray, max_radius: float) -> np.ndarray:
        """Contraint le rayon spectral absolu en deçà du seuil lipschitzien maximal."""
        m = np.nan_to_num(matrix, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)
        try:
            # Calcul des valeurs propres sur sous-échantillon ou matrice complète
            eigvals = np.linalg.eigvals(m)
            radius = float(np.max(np.abs(eigvals)))
            if radius > max_radius and radius > self.config.eps:
                m = m * (max_radius / radius)
        except Exception:
            m = np.clip(m, -1.0, 1.0) * (max_radius / 2.0)
        return m.astype(np.float32)

    @property
    def spectral_radius(self) -> float:
        """Retourne le rayon spectral courant de W_federal."""
        try:
            eigvals = np.linalg.eigvals(self.W_federal)
            return float(np.max(np.abs(eigvals)))
        except Exception:
            return 0.0

    def distill_civilization_trajectories(
        self,
        consensus_latents: List[np.ndarray],
        survivor_genomes: Optional[List[np.ndarray]] = None,
    ) -> Dict[str, Any]:
        """
        Condense les consensus récents des 3 mondes et les connectomes de survivants
        dans le méta-génome directeur.
        """
        lr = float(np.clip(self.config.distillation_rate, 0.01, 0.50))

        # 1. Mise à jour sphérique géodésique de z_meta
        if consensus_latents:
            normed_latents = []
            for c in consensus_latents:
                arr = np.asarray(c, dtype=np.float32)
                arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
                n = float(np.linalg.norm(arr)) + self.config.eps
                normed_latents.append(arr / n)

            barycenter = np.mean(normed_latents, axis=0)
            new_z = (1.0 - lr) * self.z_meta + lr * barycenter
            new_norm = float(np.linalg.norm(new_z)) + self.config.eps
            self.z_meta = (new_z / new_norm).astype(np.float32)

        # 2. Mise à jour de la matrice connectomique W_federal
        if survivor_genomes:
            mean_survivor_w = np.mean(survivor_genomes, axis=0)
            new_w = (1.0 - lr) * self.W_federal + lr * mean_survivor_w
            self.W_federal = self._constrain_spectral_radius(new_w, self.config.max_spectral_radius)

        self.version += 1
        self.distillations_count += 1

        return {
            "version": self.version,
            "distillations_count": self.distillations_count,
            "spectral_radius": float(self.spectral_radius),
            "z_meta_norm": float(np.linalg.norm(self.z_meta)),
        }


class EvolutiveCompiler:
    """
    Compilateur évolutif traduisant les Gigatokens du méta-génome en micro-programmes
    NTM appliqués en sandbox sur les agents.
    """

    def __init__(self, config: Optional[FederalMetaGenomeConfig] = None):
        self.config = config or FederalMetaGenomeConfig()
        self.rng = np.random.RandomState(self.config.seed)

        # Projecteur de z_meta vers les créneaux NTM (K * 5 dimensions)
        total_ntm_dim = self.config.num_ntm_slots * 5
        raw_proj = self.rng.randn(self.config.latent_dim, total_ntm_dim).astype(np.float32) * 0.1
        u, _, vt = np.linalg.svd(raw_proj, full_matrices=False)
        self.ntm_proj = np.dot(u, vt).astype(np.float32)

    def compile_metagenome_to_ntm(self, z_meta: np.ndarray) -> np.ndarray:
        """
        Projette z_meta in S^(D-1) vers K créneaux NTM de format [src, dst, weight, unused, enable].
        """
        arr = np.asarray(z_meta, dtype=np.float32)
        arr = np.nan_to_num(arr, nan=0.0, posinf=1.0, neginf=-1.0)
        norm = float(np.linalg.norm(arr)) + self.config.eps
        z_norm = (arr / norm).astype(np.float32)

        if z_norm.shape[0] != self.config.latent_dim:
            if z_norm.shape[0] > self.config.latent_dim:
                z_norm = z_norm[:self.config.latent_dim]
            else:
                z_norm = np.pad(z_norm, (0, self.config.latent_dim - z_norm.shape[0]))

        flat_ntm = np.dot(z_norm, self.ntm_proj)
        ntm_slots = flat_ntm.reshape(self.config.num_ntm_slots, 5).copy()

        # Sanitarisation des bornes physiques
        ntm_slots[:, 0] = np.abs(ntm_slots[:, 0])  # src >= 0
        ntm_slots[:, 1] = np.abs(ntm_slots[:, 1])  # dst >= 0
        ntm_slots[:, 2] = np.clip(ntm_slots[:, 2] * 2.0, -10.0, 10.0)  # Poids synaptique
        ntm_slots[:, 3] = 0.0  # Inutilisé
        # Activer les slots significatifs
        ntm_slots[:, 4] = np.where(np.abs(ntm_slots[:, 2]) > 0.05, 1.0, 0.0)

        return ntm_slots.astype(np.float32)

    def compile_and_apply_to_agent(self, agent: Any, z_meta: np.ndarray) -> Tuple[bool, Dict[str, Any]]:
        """
        Exécute la compilation NTM et applique les modifications de poids
        sur le génome de l'agent en validant la stabilité spectrale.
        """
        ntm_slots = self.compile_metagenome_to_ntm(z_meta)

        # Vérifier que l'agent possède un génome avec matrice W
        model = getattr(agent, "base_agent", agent)
        genome = getattr(model, "genome", None)
        if genome is None or not hasattr(genome, "W"):
            return False, {"error": "L'agent ne possède pas de génome W valide."}

        # Format batch pour NTMProgramCompiler : shape (1, K, 5) et (1, N, N)
        ntm_batch = ntm_slots[np.newaxis, :, :]
        w_batch = genome.W[np.newaxis, :, :].copy()

        try:
            # Application de la mutation en sandbox
            updated_w_batch = NTMProgramCompiler.compile_and_apply(
                ntm_memory=ntm_batch,
                W_batch=w_batch,
                agents=[model],
            )
            candidate_w = updated_w_batch[0]

            # Validation de stabilité spectrale (Commandement 9)
            eigvals = np.linalg.eigvals(candidate_w)
            spec_radius = float(np.max(np.abs(eigvals)))

            if np.isnan(spec_radius) or np.isinf(spec_radius):
                return False, {"error": "Rayon spectral indéfini (NaN/Inf)."}

            # Contrôle lipschitzien : contraindre le rayon spectral si excédent
            if spec_radius > self.config.max_spectral_radius and spec_radius > self.config.eps:
                candidate_w = candidate_w * (self.config.max_spectral_radius / spec_radius)
                spec_radius = self.config.max_spectral_radius

            # Application effective sur le génome
            genome.W = candidate_w.astype(np.float32)
            if hasattr(model, "update_phenotype"):
                model.update_phenotype()

            mutations_count = int(np.sum(ntm_slots[:, 4] > 0))

            report = {
                "mutations_applied": mutations_count,
                "spectral_radius": float(spec_radius),
                "spectral_stable": bool(spec_radius <= self.config.max_spectral_radius),
            }
            return True, report

        except Exception as e:
            return False, {"error": str(e)}
