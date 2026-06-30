"""TorchBatchModel — adaptateur monde (B×O) avec padding élastique hétérogène.

Task 1 : __init__ + forward uniquement (YAGNI).
Réutilise le mapping élastique de MambaBatchModel (mamba_agent.py:357-379)
et la dynamique LTC différentiable de backend_torch._step.

compute_policy_gradient / state-sync = Task 2.
"""
import numpy as np

try:
    import torch
except Exception:
    torch = None


class TorchBatchModel:
    KWTA_KEEP_FRAC = 1.0           # tolère les attrs posés par le monde (no-op torch)

    def __init__(self, models, world_model=None):
        if torch is None:
            raise NotImplementedError("torch absent (requirements-torch.txt)")
        self.agents = models           # NB: le monde passe les .model (MambaAgent)
        self.B = len(models)
        self.world_model = world_model
        if self.B == 0:
            return
        self.max_I = max(m.genome.num_inputs for m in models)
        self.max_O = max(m.genome.num_outputs for m in models)
        self.max_H = max(m.genome.num_nodes - m.genome.num_inputs - m.genome.num_outputs for m in models)
        self.max_N = min(self.max_I + self.max_H + self.max_O, 256)
        W = np.zeros((self.B, self.max_N, self.max_N), dtype=np.float32)
        self.mappings = []
        for i, m in enumerate(models):
            I_i, O_i, N_i = m.genome.num_inputs, m.genome.num_outputs, m.genome.num_nodes
            idx = np.zeros(N_i, dtype=int)
            for s in range(I_i): idx[s] = s
            for s in range(I_i, N_i - O_i): idx[s] = self.max_I + (s - I_i)
            for s in range(N_i - O_i, N_i): idx[s] = (self.max_I + self.max_H) + (s - (N_i - O_i))
            idx = np.clip(idx, 0, self.max_N - 1)
            self.mappings.append(idx)
            W[i][idx[:, None], idx[None, :]] = m.genome.W
        self.W = torch.tensor(W, requires_grad=True)
        self.H = torch.zeros((self.B, self.max_N))
        self.opt = torch.optim.SGD([self.W], lr=0.04)
        self._eye = torch.eye(self.max_N)
        self._last = None
        self._prev = None

    def _step(self, obs_t, H_in):
        H = H_in.clone()
        H[:, :obs_t.shape[1]] = obs_t
        diag = torch.diagonal(self.W, dim1=1, dim2=2)
        delta = torch.sigmoid(torch.clamp(diag, -10.0, 10.0))
        excit = torch.bmm(H.unsqueeze(1), self.W * (1.0 - self._eye)).squeeze(1)
        return (1.0 - delta) * H + delta * torch.tanh(excit)

    def forward(self, batch_obs, env_surprise_batch=None):
        if self.B == 0:
            return np.array([]), np.array([])
        x = np.zeros((self.B, self.max_I), dtype=np.float32)
        x[:, :batch_obs.shape[1]] = batch_obs
        obs_t = torch.tensor(x)
        H_in = self.H.detach()
        with torch.no_grad():
            H_new = self._step(obs_t, H_in)
        self.H = H_new.detach()
        self._last = (obs_t, H_in)
        logits = H_new[:, self.max_N - self.max_O:self.max_N]
        return logits.cpu().numpy(), np.ones(self.B, dtype=np.float32)  # compute_spent neutre (pas de TTC)
