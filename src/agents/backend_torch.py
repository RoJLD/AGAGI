"""Backend torch — substrat LTC différentiable (ADR-003, Axe 1, REF-LTC-2021).

Porte la dynamique Liquid Time-Constant DU CONNECTOME EXISTANT dans torch :
    δ = sigmoid(diag(W))          (constante de temps liquide, par nœud)
    H' = (1−δ)·H + δ·tanh(H·W_offdiag)
avec W = Parameter ENTRAÎNABLE par autograd. But : un substrat appris par GRADIENT
(vs hebbien/mutation numpy du legacy), pour l'A/B `transfer_ratio` à substrat constant
(1 variable = la règle d'apprentissage). Ce n'est PAS un portage bit-fidèle du
MambaBatchModel : ni NTM, ni router, ni thresholds, ni TTC — substrat minimal volontaire
(moins de confounds). On adopte l'autodiff de torch, on ne réimplémente pas la roue.

`learn` = Actor-Critic TD(0) à crédit temporel (parité sémantique avec le legacy
`compute_policy_gradient`) : value head = nœud 28 ; acteur sur move (8 logits) + grab
(nœud 24) + rub (nœud 25) ; δ = r + γ·V(s') − V(s), transition différée d'un tick. La
perte A-C est posée, AUTOGRAD calcule le gradient (vs dérivation manuelle du legacy).

Limites MVP (incréments suivants) : dimensions homogènes (I/O/N identiques sur la
population). Hétérogénéité topologique, organes (NTM/router/TTC), et cellule ncps =
variables séparées ultérieures.

Réf : docs/ADR/003_backend_abstraction.md ; REF-LTC-2021.
"""
import numpy as np

from src.agents.backend import PopulationModel

try:
    import torch
except Exception:  # pragma: no cover - environnement sans torch
    torch = None

_MOVE_LOGITS = 8   # actions de déplacement 0..7 (cf. MambaBatchModel.PLAN_A)
_GRAB_NODE = 24    # logit binaire grab (sortie 24, cf. legacy)
_RUB_NODE = 25     # logit binaire rub (sortie 25, cf. legacy)
_VALUE_NODE = 28   # value head V(s) (sortie 28, cf. legacy compute_policy_gradient)
_GAMMA = 0.9       # crédit temporel (= MambaBatchModel.TD_GAMMA par défaut)


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
        self._prev = None
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
        """Actor-Critic TD(0) à crédit temporel. La transition (s,a,r) du tick courant
        est mémorisée ; l'update est appliqué au tick SUIVANT, quand V(s') est connu
        (δ = r + γ·V(s') − V(s)). Premier appel d'une vie -> différé (retourne None)."""
        if self.B == 0 or actions_batch is None or self._last is None:
            return None
        obs_t, H_in = self._last
        # V(s') = valeur de l'état courant (calculé par le dernier forward), bootstrap détaché
        v_next = self.H[:, self.N - self.O + _VALUE_NODE].detach()
        trans = {"obs": obs_t, "H_in": H_in, "act": list(actions_batch),
                 "reward": np.asarray(rewards_batch, dtype=np.float32)}
        loss = None
        if self._prev is not None:
            loss = self._td_update(self._prev, v_next)
        self._prev = trans
        return loss

    def _td_update(self, prev, v_next):
        """Applique l'update Actor-Critic TD pour la transition précédente."""
        F = torch.nn.functional
        H_new = self._step(prev["obs"], prev["H_in"])             # re-différencie s wrt W
        out = H_new[:, self.N - self.O:self.N]                    # (B,O)
        v = out[:, _VALUE_NODE]                                   # V(s)
        rew = torch.tensor(prev["reward"], device=self.device)
        target = (rew + _GAMMA * v_next).detach()                # cible TD (bootstrap)
        delta = (target - v).detach()                            # avantage = erreur TD

        idx = torch.arange(self.B, device=self.device)
        moves = torch.tensor([int(a.get("move", 0)) for a in prev["act"]], device=self.device)
        logp = torch.log_softmax(out[:, :_MOVE_LOGITS], dim=1)[idx, moves]
        grab = torch.tensor([float(a.get("grab", 0)) for a in prev["act"]], device=self.device)
        rub = torch.tensor([float(a.get("rub", 0)) for a in prev["act"]], device=self.device)
        logp = logp - F.binary_cross_entropy_with_logits(out[:, _GRAB_NODE], grab, reduction="none")
        logp = logp - F.binary_cross_entropy_with_logits(out[:, _RUB_NODE], rub, reduction="none")

        actor_loss = -(delta * logp).mean()                      # ACTOR (avantage = δ)
        critic_loss = ((v - target) ** 2).mean()                 # CRITIC (vers r + γV')
        loss = actor_loss + 0.5 * critic_loss
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self._write_back()
        return float(loss.item())

    def learn_episode_bptt(self, obs_seq, actions_seq, rewards, truncate=False, gamma=1.0):
        """BPTT FENÊTRÉ (EDR-146) — la capacité que numpy N'A PAS. Rejoue l'épisode (obs_seq) depuis
        H=0 en RETENANT le graphe récurrent, crédite les actions PRISES par le retour (REINFORCE) et
        backprop UNE fois à travers toute la fenêtre -> le crédit de l'étape finale remonte par la
        récurrence jusqu'à W (façonne la mémoire des étapes antérieures). ADDITIF : ne touche NI
        forward NI learn (le banc compositional // reste intact).

        truncate=True détache H entre les pas (= crédit 1-pas, ce que forward/learn/legacy font) pour
        l'A/B : le crédit final ne peut alors PAS remonter la récurrence -> pas de means→ends.
        obs_seq: liste de (B,I) ; actions_seq: liste (par pas) de listes de dicts {"move":int} ;
        rewards: (B,) retour épisodique. Ne fait PAS l'échantillonnage (le banc choisit les actions)."""
        if self.B == 0 or not obs_seq:
            return None
        R = torch.tensor(np.asarray(rewards, dtype=np.float32), device=self.device)   # (B,)
        H = torch.zeros((self.B, self.N), device=self.device)
        idx = torch.arange(self.B, device=self.device)
        total_logp = torch.zeros(self.B, device=self.device)
        for t, obs in enumerate(obs_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :self.I], device=self.device)
            if truncate and t > 0:
                H = H.detach()                                        # coupe le crédit à travers le temps
            H = self._step(obs_t, H)                                  # graphe retenu (BPTT) sauf si truncate
            out = H[:, self.N - self.O:self.N]
            moves = torch.tensor([int(a.get("move", 0)) for a in actions_seq[t]], device=self.device)
            logp = torch.log_softmax(out[:, :_MOVE_LOGITS], dim=1)[idx, moves]
            total_logp = total_logp + (gamma ** t) * logp
        loss = -(R * total_logp).mean()                              # REINFORCE, retour épisodique
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
