"""TorchBatchModel — adaptateur monde (B×O) avec padding élastique hétérogène.

Task 1 : __init__ + forward.
Task 2 : forward sync état agent + compute_policy_gradient Actor-Critic TD(0).

Réutilise le mapping élastique de MambaBatchModel (mamba_agent.py:357-379)
et la dynamique LTC différentiable de backend_torch._step.
"""
import numpy as np

try:
    import torch
except Exception:
    torch = None

_MOVE_LOGITS = 8   # actions de déplacement 0..7
_GRAB_NODE = 24    # logit binaire grab (sortie 24)
_RUB_NODE = 25     # logit binaire rub (sortie 25)
_VALUE_NODE = 28   # value head V(s) (sortie 28)
_GAMMA = 0.9       # crédit temporel (parité backend_torch)


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

    def _write_back(self):
        """Demap W appris vers chaque genome (inverse du scatter __init__)."""
        W_np = self.W.detach().cpu().numpy()
        for i, a in enumerate(self.agents):
            idx = self.mappings[i]
            a.genome.W = W_np[i][idx[:, None], idx[None, :]].astype(np.float32).copy()

    def _sync_agent_state(self, H_new, env_surprise_batch):
        """Sync des attributs lus par le monde après chaque forward."""
        H_np = H_new.cpu().numpy()
        for i, a in enumerate(self.agents):
            idx = self.mappings[i]
            # W writeback (état courant du réseau différentiable → génome)
            W_np = self.W.detach().cpu().numpy()
            a.genome.W = W_np[i][idx[:, None], idx[None, :]].astype(np.float32).copy()
            # surprise_momentum : scalaire flottant
            if env_surprise_batch is not None:
                a.surprise_momentum = float(env_surprise_batch[i])
            else:
                a.surprise_momentum = getattr(a, "surprise_momentum", 0.0)
                if not isinstance(a.surprise_momentum, float):
                    a.surprise_momentum = 0.0
            # attention_mask : vecteur d'entrées (ones = pas de masque)
            a.attention_mask = np.ones(a.genome.num_inputs, dtype=np.float32)
            # ntm_memory : conserve l'existant ou initialise
            if not hasattr(a, "ntm_memory") or a.ntm_memory is None:
                a.ntm_memory = np.zeros((10, 5), dtype=np.float32)
            # explicit_memory : vecteur court
            a.explicit_memory = np.zeros(5, dtype=np.float32)

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
        # Task 2 : sync état agent (contrat aval)
        self._sync_agent_state(H_new, env_surprise_batch)
        return logits.cpu().numpy(), np.ones(self.B, dtype=np.float32)  # compute_spent neutre

    def compute_policy_gradient(self, rewards_batch, actions_batch=None):
        """Actor-Critic TD(0) différé, parité sémantique avec backend_torch._td_update.

        La transition (s,a,r) est mémorisée au tick courant ; l'update est appliqué au
        tick SUIVANT quand V(s') est connu : δ = r + γ·V(s') − V(s).
        Premier appel → différé (retourne None).
        actions_batch : liste de dict {"move":int, "grab":0/1, "rub":0/1}.
        """
        if self.B == 0:
            return None
        if self._last is None:
            return None

        obs_t, H_in = self._last
        # V(s') = valeur de l'état actuel (dernier forward), bootstrap détaché
        v_next = self.H[:, self.max_N - self.max_O + _VALUE_NODE].detach()

        trans = {
            "obs": obs_t,
            "H_in": H_in,
            "act": list(actions_batch) if actions_batch is not None else None,
            "reward": np.asarray(rewards_batch, dtype=np.float32),
        }
        loss = None
        if self._prev is not None:
            loss = self._td_update(self._prev, v_next)
        self._prev = trans
        return loss

    def _td_update(self, prev, v_next):
        """Applique l'update Actor-Critic TD pour la transition précédente."""
        F = torch.nn.functional
        H_new = self._step(prev["obs"], prev["H_in"])          # re-différencie wrt W
        out = H_new[:, self.max_N - self.max_O:self.max_N]    # (B, max_O)

        v = out[:, _VALUE_NODE]                                # V(s)
        rew = torch.tensor(prev["reward"])
        target = (rew + _GAMMA * v_next).detach()             # cible TD bootstrap
        delta = (target - v).detach()                         # avantage = erreur TD

        idx = torch.arange(self.B)
        acts = prev["act"] or [{}] * self.B
        moves = torch.tensor([int(a.get("move", 0)) for a in acts])
        grab = torch.tensor([float(a.get("grab", 0)) for a in acts])
        rub = torch.tensor([float(a.get("rub", 0)) for a in acts])

        logp = torch.log_softmax(out[:, :_MOVE_LOGITS], dim=1)[idx, moves]
        logp = logp - F.binary_cross_entropy_with_logits(out[:, _GRAB_NODE], grab, reduction="none")
        logp = logp - F.binary_cross_entropy_with_logits(out[:, _RUB_NODE], rub, reduction="none")

        actor_loss = -(delta * logp).mean()
        critic_loss = ((v - target) ** 2).mean()
        loss = actor_loss + 0.5 * critic_loss

        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self._write_back()
        return float(loss.item())
