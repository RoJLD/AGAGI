"""
Vrai Policy Gradient (REINFORCE) avec CRÉDIT D'ACTION — cf. docs/EDR/020.

Le levier n°1 de la session (EDR 019) : le Hebbien rustre (`dW ∝ advantage·h·hᵀ`)
renforçait tout le connectome sans savoir QUELLE action avait été bonne → aucun
geste ne pouvait être encodé. Ici, on crédite l'action *choisie* :

    pour l'action a, ∂log π(a)/∂W[:,node_a] = (1{k=a} − π(k)) · h

→ augmente le logit de l'action récompensée, baisse les autres. C'est ce qui permet
d'ACQUÉRIR un comportement (grab, rub…) — pas seulement de moduler l'amplitude.

Convention : les sorties sont les O derniers nœuds de l'agent (N nœuds). L'action
de sortie k est portée par le nœud `N − O + k`, et son logit = H[N−O+k].
"""
import numpy as np


def _softmax(x):
    e = np.exp(x - np.max(x))
    return e / (e.sum() + 1e-8)


def td_error(reward, value, next_value, gamma=0.9):
    """Erreur TD(0) : δ = r + γ·V(s') − V(s) (EDR 023).

    Sert à la fois d'**avantage** pour l'actor ET d'erreur de correction du **critic**.
    Capture le crédit TEMPOREL : une action à récompense immédiate nulle/négative mais qui
    mène à un état de forte valeur (ex. *crafter* — coûte 2.0 maintenant — pour pouvoir
    *chasser l'apex* plus tard) reçoit un avantage **positif** via γ·V(s'). C'est ce que le
    critic Monte-Carlo (vers le reward immédiat) ne pouvait pas faire — sans quoi aucune
    chaîne moyens→fins n'est apprenable. γ règle l'horizon (myope ↔ prévoyant)."""
    return reward + gamma * next_value - value


def reinforce_action_update(h, out_logits, chosen_move, binary_actions,
                            advantage, lr, n_move=8):
    """dW (N, N) créditant les actions CHOISIES (vrai policy gradient).

    h            : (N,) activation présynaptique de l'agent.
    out_logits   : (O,) logits de sortie (les O derniers nœuds).
    chosen_move  : int, direction de mouvement choisie (0..n_move-1) ou -1 si aucune.
    binary_actions : dict {index_de_sortie: pris(bool)} pour les actions binaires (grab, rub…).
    advantage    : float (reward − value). lr : pas d'apprentissage.

    Renvoie dW (N, N) à ajouter au connectome de l'agent.
    """
    h = np.asarray(h, dtype=np.float32)
    out_logits = np.asarray(out_logits, dtype=np.float32)
    N = h.shape[0]
    O = len(out_logits)
    base = N - O
    dW = np.zeros((N, N), dtype=np.float32)
    if base < 0:
        return dW

    # Mouvement : politique catégorielle softmax sur les n_move premières sorties.
    if 0 <= chosen_move < n_move and n_move <= O:
        pi = _softmax(out_logits[:n_move])
        for m in range(n_move):
            grad = (1.0 if m == chosen_move else 0.0) - pi[m]
            dW[:, base + m] += lr * advantage * grad * h

    # Actions binaires (grab, rub…) : politique de Bernoulli (sigmoïde).
    for idx, taken in binary_actions.items():
        if 0 <= idx < O:
            p = 1.0 / (1.0 + np.exp(-out_logits[idx]))
            grad = (1.0 if taken else 0.0) - p
            dW[:, base + idx] += lr * advantage * grad * h

    return dW
