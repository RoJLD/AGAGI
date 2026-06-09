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
