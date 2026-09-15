"""
World Model — tête prédictive façon RND (cf. docs/EDR/010, levier 1 ; roadmap Vague 0).

Modèle de transition linéaire partagé par la population : il prédit une projection
aléatoire FIXE de l'observation suivante à partir de l'observation courante.
L'erreur de prédiction sert de **vraie surprise** (elle remplace le signal mort du
forward batch, qui valait toujours 0) et de socle à la récompense de curiosité
intrinsèque (axe 4.1).

    pred(t)   = obs(t)   @ Wp        # prédiction de proj(obs(t+1)) ; Wp APPRIS en ligne
    target(t) = obs(t+1) @ P         # P : projection aléatoire FIXE (non apprise)
    erreur    = mean((pred − target)²)   # par agent (B,)

P est figé : c'est ce qui empêche l'effondrement trivial. Un agent ne peut pas
rendre sa cible facile — il ne peut que mieux *modéliser* la dynamique du monde.
La surprise chute donc sur le familier (le modèle l'a appris) et reste haute sur
le nouveau : exactement le signal de curiosité recherché.
"""
import numpy as np


class WorldModel:
    # E28 : compteur de remises a zero pour non-fini (publie par les sondes ; jamais remis a zero ici)
    nonfinite_resets = 0

    def __init__(self, input_dim: int, out_dim: int = 8, lr: float = 0.01, seed: int = 1234):
        self.input_dim = int(input_dim)
        self.out_dim = int(out_dim)
        self.lr = float(lr)
        rng = np.random.default_rng(seed)
        # Projection cible FIXE (jamais apprise).
        self.P = (rng.standard_normal((self.input_dim, self.out_dim)).astype(np.float32)
                  / np.sqrt(self.input_dim))
        # Modèle de transition APPRIS (init à zéro -> prédiction nulle au départ).
        self.Wp = np.zeros((self.input_dim, self.out_dim), dtype=np.float32)

    def _fit_width(self, obs: np.ndarray) -> np.ndarray:
        """Coerce l'observation à la largeur input_dim (pad de zéros / troncature)."""
        obs = np.atleast_2d(np.asarray(obs, dtype=np.float32))
        w = obs.shape[1]
        if w == self.input_dim:
            return obs
        out = np.zeros((obs.shape[0], self.input_dim), dtype=np.float32)
        m = min(w, self.input_dim)
        out[:, :m] = obs[:, :m]
        return out

    def predict(self, obs: np.ndarray) -> np.ndarray:
        return self._fit_width(obs) @ self.Wp

    def target(self, next_obs: np.ndarray) -> np.ndarray:
        return self._fit_width(next_obs) @ self.P

    def observe_batch(self, Wp_batch: np.ndarray, prev_obs: np.ndarray,
                      next_obs: np.ndarray, train: bool = True):
        """World Model PAR AGENT (EDR 015) : un Wp distinct par agent (B, input_dim, out),
        cible P PARTAGÉE. Chaque agent apprend son prédicteur depuis sa propre trajectoire
        -> surprise par-agent qui ne sature pas comme le modèle partagé.

        Renvoie (erreurs (B,), Wp_batch mis à jour).
        """
        prev = self._fit_width(prev_obs)                 # (B, input_dim)
        nxt = self._fit_width(next_obs)
        pred = np.einsum('bi,bio->bo', prev, Wp_batch)   # (B, out)
        tgt = nxt @ self.P                               # (B, out)
        diff = pred - tgt
        err = np.mean(diff ** 2, axis=1)                 # (B,)
        if train and prev.shape[0] > 0:
            grad = np.einsum('bi,bo->bio', prev, diff)   # (B, input_dim, out)
            Wp_batch = Wp_batch - self.lr * grad
        # E28 (2026-09-15) : ce SGD brut sur l'observation (energie jusqu'a 100, lr 0,01) DIVERGE -- mesure :
        # 669/669 morts d'une cohorte immortelle avaient un Wp non fini, des le tick 51. Le NaN qui en sort
        # devient `surprise` NaN, puis `brain_cost` NaN, puis `energy = max(0.0, nan)` = 0.0 : une MORT par
        # tick, sans exception. Ici on ne laisse pas sortir un non-fini : Wp de l'agent remis a zero (il
        # repart de son etat initial), err = 1.0 (surprise MAXIMALE, bornee comme le clip aval), et
        # l'evenement est COMPTE. Bit-identique tant que tout est fini.
        mauvais = ~(np.isfinite(err) & np.isfinite(Wp_batch).all(axis=(1, 2)))
        if np.any(mauvais):
            WorldModel.nonfinite_resets += int(mauvais.sum())
            Wp_batch = np.where(mauvais[:, None, None], 0.0, Wp_batch).astype(Wp_batch.dtype, copy=False)
            err = np.where(mauvais, 1.0, err).astype(err.dtype, copy=False)
        return err, Wp_batch

    def observe(self, prev_obs: np.ndarray, next_obs: np.ndarray, train: bool = True) -> np.ndarray:
        """Erreur de prédiction (B,) entre pred(prev_obs) et target(next_obs).

        Si train=True, met à jour Wp d'un pas de descente de gradient sur l'EQM.
        """
        prev = self._fit_width(prev_obs)
        nxt = self._fit_width(next_obs)
        pred = prev @ self.Wp
        tgt = nxt @ self.P
        diff = pred - tgt                              # (B, out)
        err = np.mean(diff ** 2, axis=1)               # (B,)
        if train and prev.shape[0] > 0:
            grad = prev.T @ diff / prev.shape[0]        # (input, out) = ∂EQM/∂Wp
            self.Wp -= self.lr * grad
        return err
