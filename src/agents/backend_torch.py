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

    # --- Gate de conditionnement optionnel (EDR-148 : port prod de la recette 129/136/147) ---
    # OFF par défaut => chemin prod inchangé (banc compositional // intact). Quand activé, un readout
    # linéaire de H (population-partagé, SÉPARÉ de W, non hérité = MVP) biaise l'action cible, appris
    # dans le VRAI chemin Actor-Critic TD(0) ; ANTISAT pénalise la saturation de la marginale de base.
    CONDITION_GATE = False   # active le gate de conditionnement dans forward + learn
    ANTISAT = 0.0            # force de l'anti-saturation de la marginale de base (EDR-136)
    GATE_TARGET = None       # index du logit move gaté (l'action "ends") ; None => gate désactivé
    GATE_TARGETS = None      # EDR-165 : liste d'indices pour un gate MULTI-CIBLE (routage conditionnel
                             # vers plusieurs "ends", ex. spécialisation multi-chaînes) ; prioritaire sur
                             # GATE_TARGET quand non-None. Additif seulement. Single-target inchangé si None.
    GATE_MULT = False        # EDR-160 : gate MULTIPLICATIF sigmoïde (biais = SCALE·σ(H·w+b) ∈ [0,SCALE])
    GATE_SCALE = 8.0         # amplitude du gate multiplicatif ; σ→0 supprime PROPREMENT hors-contexte

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
        self._eye = torch.eye(self.N, device=self.device)

        # Gate de conditionnement (EDR-148) : params population-partagés, ajoutés à l'optimiseur.
        self.w_gate = None
        self.b_gate = None
        self._gate_runtime = True     # interrupteur runtime (diagnostic EDR-148 ; voir _gate_bias)
        params = [self.W]
        # MULTIPLICATIF (EDR-160) : biais initial NÉGATIF -> σ≈0 -> gate démarre ÉTEINT (bon prior de
        # porte). ADDITIF : 0 (neutre). Sinon le gate mult démarre always-on (σ(0)=0.5) et dégrade.
        b0 = -4.0 if type(self).GATE_MULT else 0.0
        if type(self).CONDITION_GATE and type(self).GATE_TARGETS:
            k = len(type(self).GATE_TARGETS)                      # gate MULTI-CIBLE (EDR-165)
            self.w_gate = torch.zeros(self.N, k, device=self.device, requires_grad=True)
            self.b_gate = torch.full((k,), b0, device=self.device, requires_grad=True)
            params += [self.w_gate, self.b_gate]
        elif type(self).CONDITION_GATE and type(self).GATE_TARGET is not None:
            self.w_gate = torch.zeros(self.N, device=self.device, requires_grad=True)   # single (inchangé)
            self.b_gate = torch.full((1,), b0, device=self.device, requires_grad=True)
            params += [self.w_gate, self.b_gate]
        self.opt = torch.optim.SGD(params, lr=lr)

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

    def _gate_value(self, H):
        """Valeur brute du gate (B,) = readout de l'état H. ADDITIF : H·w+b (non borné). MULTIPLICATIF
        (EDR-160, GATE_MULT) : SCALE·σ(H·w+b) ∈ [0,SCALE] -> le gate sort ~0 hors-contexte (suppression
        PROPRE de la contamination S1 d'EDR-159) et ~SCALE en contexte. Pas de garde runtime (le banc
        contrôle le scoping via gate_last_only) ; utilisé par _gate_bias et learn_episode."""
        raw = H @ self.w_gate + self.b_gate                       # (B,)
        if type(self).GATE_MULT:
            return type(self).GATE_SCALE * torch.sigmoid(raw)
        return raw

    def _gate_bias(self, H):
        """Biais de gate (B,) pour forward/_td_update. None si gate inactif. Le gate CONDITIONNE sur H
        -> il apprend QUAND se déclencher (pas de béquille d'étape : substrat prod task-agnostique).
        `_gate_runtime` (défaut True) permet à un banc de le désactiver ponctuellement (diagnostic
        EDR-148 : isoler la contamination de l'étape « means » S1)."""
        if self.w_gate is None or not getattr(self, "_gate_runtime", True):
            return None
        return self._gate_value(H)

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
        gb = self._gate_bias(H_new)
        if gb is not None:                                        # le gate influence l'action ÉCHANTILLONNÉE
            logits = logits.clone()
            if type(self).GATE_TARGETS:                           # multi-cible (EDR-165)
                for k, tgt in enumerate(type(self).GATE_TARGETS):
                    logits[:, tgt] = logits[:, tgt] + gb[:, k].detach()
            else:
                tgt = type(self).GATE_TARGET
                logits[:, tgt] = logits[:, tgt] + gb.detach()
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
        base_move = out[:, :_MOVE_LOGITS]                        # politique de BASE (pré-gate)
        move_logits = base_move
        gate_pen = 0.0
        gb = self._gate_bias(H_new)
        if gb is not None and type(self).GATE_TARGETS is None:   # gate DANS le graphe (single ; multi = via learn_episode)
            tgt = type(self).GATE_TARGET
            onehot = torch.zeros(_MOVE_LOGITS, device=self.device)
            onehot[tgt] = 1.0
            move_logits = base_move + gb.unsqueeze(1) * onehot
            if type(self).ANTISAT > 0:                           # anti-saturation de la marginale de BASE (EDR-136)
                base_p_tgt = torch.softmax(base_move, dim=1)[:, tgt].mean()
                gate_pen = type(self).ANTISAT * base_p_tgt ** 2
        logp = torch.log_softmax(move_logits, dim=1)[idx, moves]
        grab = torch.tensor([float(a.get("grab", 0)) for a in prev["act"]], device=self.device)
        rub = torch.tensor([float(a.get("rub", 0)) for a in prev["act"]], device=self.device)
        logp = logp - F.binary_cross_entropy_with_logits(out[:, _GRAB_NODE], grab, reduction="none")
        logp = logp - F.binary_cross_entropy_with_logits(out[:, _RUB_NODE], rub, reduction="none")

        actor_loss = -(delta * logp).mean()                      # ACTOR (avantage = δ)
        critic_loss = ((v - target) ** 2).mean()                 # CRITIC (vers r + γV')
        loss = actor_loss + 0.5 * critic_loss + gate_pen
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

    def imitate_episode_bptt(self, obs_seq, target_moves_seq, truncate_window=None, mask_seq=None,
                             aux_off_weight=0.0):
        """IMITATION récurrente supervisée (BPTT) — distincte de learn_episode_bptt (REINFORCE). Rejoue
        obs_seq depuis H=0 en RETENANT le graphe récurrent ; perte = cross-entropy des move-logits vs
        l'action-enseignant par pas ; backprop unique -> _write_back. ADDITIF (ne touche pas forward/
        learn/learn_episode/learn_episode_bptt).

        obs_seq : liste de (B,>=I) ; target_moves_seq : liste de (B,) entiers dans [0,8).
        truncate_window=W : détache H tous les W pas (stabilité longue fenêtre).
        mask_seq (optionnel) : liste de (B,) ∈ {0,1} par pas -> perte CE PONDÉRÉE, normalisée par Σmask
        (exclut les pas post-mortem des agents). None -> moyenne uniforme (comportement INCHANGÉ).

        ⚠️ aux_off_weight (EDR-WARM-005) : ne superviser QUE les 8 logits de mouvement laisse les canaux
        d'ACTION AUXILIAIRES libres — mesuré in-world, `grab` (nœud 24) se fige à ON sur 100 % des ticks
        et draine l'énergie en continu (ablation within-subject : survie ×2.3 en le forçant OFF, alors
        que la décision de mouvement était déjà correcte à 98.7 %). aux_off_weight>0 ajoute une BCE
        poussant grab ET rub vers OFF — l'oracle, lui, sort des zéros partout sauf la direction.
        Défaut 0.0 = comportement INCHANGÉ (rétro-compatible)."""
        if self.B == 0 or not obs_seq:
            return None
        F = torch.nn.functional
        H = torch.zeros((self.B, self.N), device=self.device)
        loss = torch.zeros((), device=self.device)
        denom = 0.0
        for t, obs in enumerate(obs_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :self.I], device=self.device)
            if truncate_window and t > 0 and (t % truncate_window == 0):
                H = H.detach()
            H = self._step(obs_t, H)
            out = H[:, self.N - self.O:self.N]
            move_logits = out[:, :_MOVE_LOGITS]
            tgt = torch.tensor(np.asarray(target_moves_seq[t]), dtype=torch.long, device=self.device)
            m = None
            if mask_seq is None:
                loss = loss + F.cross_entropy(move_logits, tgt)
                denom += 1.0
            else:
                ce = F.cross_entropy(move_logits, tgt, reduction="none")      # (B,)
                m = torch.tensor(np.asarray(mask_seq[t], dtype=np.float32), device=self.device)
                loss = loss + (ce * m).sum()
                denom += float(m.sum().item())
            if aux_off_weight > 0:            # canaux d'action auxiliaires -> OFF (comme l'oracle)
                zeros = torch.zeros(self.B, device=self.device)
                aux = (F.binary_cross_entropy_with_logits(out[:, _GRAB_NODE], zeros, reduction="none")
                       + F.binary_cross_entropy_with_logits(out[:, _RUB_NODE], zeros, reduction="none"))
                loss = loss + aux_off_weight * (aux.mean() if m is None else (aux * m).sum())
        loss = loss / max(1.0, denom)
        self.opt.zero_grad()
        loss.backward()
        self.opt.step()
        self._write_back()
        return float(loss.item())

    def learn_episode(self, obs_seq, actions_seq, rewards, gamma=1.0, gate_last_only=True):
        """CRÉDIT ÉPISODIQUE prod (EDR-158) — le véhicule que le `learn()` TD différé n'était PAS
        (EDR-148 : la recette de binding 129/136/147, validée sous REINFORCE épisodique, NE tient pas
        dans le TD(0) différé 1-pas). Rejoue l'épisode en TRONQUANT la récurrence (H détaché entre pas
        = crédit 1-pas par pas) mais crédite les actions par le RETOUR ÉPISODIQUE multi-actions ;
        applique le gate de conditionnement (biais appris sur GATE_TARGET) + anti-saturation de la
        marginale de base. Reproduit la recette 147 comme MÉTHODE du substrat prod (réutilisable), pas
        une boucle de banc. ADDITIF : ne touche NI forward NI learn NI learn_episode_bptt.

        gate_last_only=True : gate appliqué au SEUL dernier pas (l'action « ends ») -> évite la
        contamination de l'étape « means » (EDR-148). rewards: (B,) retour/avantage épisodique
        (baseliné par le caller). Le caller échantillonne les actions ; ici on crédite celles prises."""
        if self.B == 0 or not obs_seq:
            return None
        R = torch.tensor(np.asarray(rewards, dtype=np.float32), device=self.device)   # (B,)
        H = torch.zeros((self.B, self.N), device=self.device)
        idx = torch.arange(self.B, device=self.device)
        total_logp = torch.zeros(self.B, device=self.device)
        gate_pen = 0.0
        T = len(obs_seq)
        for t, obs in enumerate(obs_seq):
            obs_t = torch.tensor(np.asarray(obs, dtype=np.float32)[:, :self.I], device=self.device)
            H = H.detach()                                            # tronqué (crédit 1-pas ; retour porte le multi-actions)
            H = self._step(obs_t, H)
            out = H[:, self.N - self.O:self.N]
            base_move = out[:, :_MOVE_LOGITS]
            move_logits = base_move
            use_gate = self.w_gate is not None and (not gate_last_only or t == T - 1)
            if use_gate:
                gb = self._gate_value(H)                             # (B,) single ou (B,K) multi (EDR-165)
                if type(self).GATE_TARGETS:                          # gate MULTI-CIBLE : un biais par "ends"
                    for k, tgt in enumerate(type(self).GATE_TARGETS):
                        onehot = torch.zeros(_MOVE_LOGITS, device=self.device)
                        onehot[tgt] = 1.0
                        move_logits = move_logits + gb[:, k:k + 1] * onehot
                        if type(self).ANTISAT > 0:
                            base_p_tgt = torch.softmax(base_move, dim=1)[:, tgt].mean()
                            gate_pen = gate_pen + type(self).ANTISAT * base_p_tgt ** 2
                else:
                    tgt = type(self).GATE_TARGET
                    onehot = torch.zeros(_MOVE_LOGITS, device=self.device)
                    onehot[tgt] = 1.0
                    move_logits = base_move + gb.unsqueeze(1) * onehot
                    if type(self).ANTISAT > 0:
                        base_p_tgt = torch.softmax(base_move, dim=1)[:, tgt].mean()
                        gate_pen = gate_pen + type(self).ANTISAT * base_p_tgt ** 2
            moves = torch.tensor([int(a.get("move", 0)) for a in actions_seq[t]], device=self.device)
            logp = torch.log_softmax(move_logits, dim=1)[idx, moves]
            total_logp = total_logp + (gamma ** t) * logp
        loss = -(R * total_logp).mean() + gate_pen                   # REINFORCE épisodique + anti-saturation
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
