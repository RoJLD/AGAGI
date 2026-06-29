"""Backend torch — substrat LTC différentiable (ADR-003, Axe 1, REF-LTC-2021).

Porte la dynamique Liquid Time-Constant DU CONNECTOME EXISTANT dans torch :
    δ = sigmoid(diag(W))          (constante de temps liquide, par nœud)
    H' = (1−δ)·H + δ·tanh(H·W_offdiag)
avec W = Parameter ENTRAÎNABLE par autograd. But : un substrat appris par GRADIENT
(vs hebbien/mutation numpy du legacy), pour l'A/B `transfer_ratio` à substrat constant
(1 variable = la règle d'apprentissage). Ce n'est PAS un portage bit-fidèle du
MambaBatchModel : ni NTM, ni router, ni thresholds, ni TTC — substrat minimal volontaire
(moins de confounds). On adopte l'autodiff de torch, on ne réimplémente pas la roue.

Limites MVP (incréments suivants) : dimensions homogènes (I/O/N identiques sur la
population) ; `learn` = REINFORCE sur l'action `move` (8 premiers logits de sortie).
Hétérogénéité topologique, organes, et cellule ncps = variables séparées ultérieures.

Réf : docs/ADR/003_backend_abstraction.md ; REF-LTC-2021.
"""
import numpy as np

from src.agents.backend import PopulationModel

try:
    import torch
except Exception:  # pragma: no cover - environnement sans torch
    torch = None

_MOVE_LOGITS = 8  # actions de déplacement 0..7 (cf. MambaBatchModel.PLAN_A)


class TorchPopulationModel(PopulationModel):
    """Population LTC différentiable. Même contrat que le backend legacy."""

    backend = "torch"

    def __init__(self, agents, world_model=None, lr=0.04, device="cpu"):
        if torch is None:
            raise NotImplementedError("backend 'torch' : PyTorch non installé (requirements-torch.txt)")
        self.agents = agents
        self.B = len(agents)
        self.world_model = world_model
        self.device = torch.device(device)
        self._last = None
        if self.B == 0:
            self.W = None
            return

        dims_I = {a.genome.num_inputs for a in agents}
        dims_O = {a.genome.num_outputs for a in agents}
        dims_N = {a.genome.num_nodes for a in agents}
        if len(dims_I) != 1 or len(dims_O) != 1 or len(dims_N) != 1:
            raise NotImplementedError(
                "TorchPopulationModel (MVP) exige des dimensions homogènes "
                f"(I={dims_I}, O={dims_O}, N={dims_N}) ; hétérogénéité topologique = incrément suivant"
            )
        self.I, self.O, self.N = dims_I.pop(), dims_O.pop(), dims_N.pop()

        W = np.stack([np.asarray(a.genome.W, dtype=np.float32) for a in agents], axis=0)
        self.W = torch.tensor(W, device=self.device, requires_grad=True)
        self.H = torch.zeros((self.B, self.N), device=self.device)
        self.opt = torch.optim.SGD([self.W], lr=lr)
        self._eye = torch.eye(self.N, device=self.device)

    def _step(self, obs_t, H_in):
        """Une étape LTC différentiable. obs_t (B,I), H_in (B,N) -> H_new (B,N).
        Le gradient ne circule que par self.W (H_in et obs_t sont des constantes)."""
        H = H_in.clone()
        H[:, :self.I] = obs_t                                       # injection des capteurs
        diag = torch.diagonal(self.W, dim1=1, dim2=2)              # (B,N)
        delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
        W_off = self.W * (1.0 - self._eye)                         # hors-diagonale
        excitation = torch.bmm(H.unsqueeze(1), W_off).squeeze(1)   # (B,N) = H · W_off
        return (1.0 - delta) * H + delta * torch.tanh(excitation)

    def forward(self, batch_obs, env_surprise_batch=None):
        if self.B == 0:
            return np.array([]), 0
        obs_t = torch.tensor(np.asarray(batch_obs, dtype=np.float32)[:, :self.I], device=self.device)
        H_in = self.H.detach()
        with torch.no_grad():
            H_new = self._step(obs_t, H_in)
        self.H = H_new.detach()
        self._last = (obs_t, H_in)
        logits = H_new[:, self.N - self.O:self.N]
        return logits.cpu().numpy(), 0

    def learn(self, rewards_batch, actions_batch=None):
        """REINFORCE par autograd sur l'action `move` : maximise reward·log π(move).
        Re-différencie la dernière étape (stockée par forward) par rapport à W."""
        if self.B == 0 or actions_batch is None or self._last is None:
            return None
        obs_t, H_in = self._last
        H_new = self._step(obs_t, H_in)                            # graphe avec grad sur W
        logits = H_new[:, self.N - self.O:self.N]
        logp = torch.log_softmax(logits[:, :_MOVE_LOGITS], dim=1)
        moves = torch.tensor([int(a.get("move", 0)) for a in actions_batch], device=self.device)
        rew = torch.tensor(np.asarray(rewards_batch, dtype=np.float32), device=self.device)
        chosen = logp[torch.arange(self.B, device=self.device), moves]
        loss = -(rew * chosen).mean()
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self._write_back()
        return float(loss.item())

    def _write_back(self):
        """Baldwin : réécrit W appris dans les génomes (in place)."""
        W = self.W.detach().cpu().numpy()
        for i, a in enumerate(self.agents):
            a.genome.W = W[i].astype(np.float32).copy()

    def extract(self):
        if self.B:
            self._write_back()
        return self.agents
