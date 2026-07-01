"""Décomposition du résidu torch↔legacy (EDR-141, item 2).

Question : après avoir matché l'activation (EDR-139/140), pourquoi torch-swish (52-56t) traîne-t-il
encore legacy-core (66-68t) ? Sonde PURE (pas de monde, pas de KuzuDB) : fait tourner legacy-core et
torch-swish sur le MÊME génome + la MÊME séquence d'obs, et mesure la divergence de logits par tick.

Constat (champion HoF stoneage) : t=0 diff = 0.0000 (parité PAR-PAS exacte) ; t>=1 diverge — MAIS si
l'on neutralise le masque d'attention d'entrée dynamique de legacy (recalculé chaque tick en
sigmoid(attention_logits), appliqué aux entrées ; torch ne le réplique pas), la divergence retombe à
0.0000 à CHAQUE tick. => le résidu est ENTIÈREMENT ce masque d'attention, PAS du bruit numérique.

Usage : python tools/torch_parity_probe.py   (env: TPP_HOF, TPP_TICKS)
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def per_tick_divergence(genome, ticks: int = 12, force_legacy_mask_ones: bool = False, seed: int = 0):
    """Divergence max|logit| par tick entre legacy-core et torch-swish sur le même génome+obs.
    force_legacy_mask_ones : neutralise le masque d'attention d'entrée dynamique de legacy (test causal)."""
    import numpy as np
    from src.agents.mamba_agent import MambaAgent, MambaCoreBatchModel
    from src.agents.torch_batch_model import TorchBatchModel

    Swish = type("TorchSwish", (TorchBatchModel,), {"ACTIVATION": "swish"})
    I = genome.num_inputs
    rng = np.random.RandomState(seed)
    al = MambaAgent(); al.from_genome(genome)
    at = MambaAgent(); at.from_genome(genome)
    divs = []
    for _ in range(ticks):
        if force_legacy_mask_ones:
            al.attention_mask = np.ones(I, dtype=np.float32)
        obs = (rng.randn(1, I) * 0.5).astype(np.float32)
        pl, _ = MambaCoreBatchModel([al]).forward(obs)
        pt, _ = Swish([at]).forward(obs)
        O = min(pl.shape[1], pt.shape[1])
        divs.append(float(np.max(np.abs(pl[0, :O] - pt[0, :O]))))
    return divs


def main():
    from tools.substrate_world_ab import _load_champion
    hof = os.environ.get("TPP_HOF", "data/hall_of_fame.pkl")
    ticks = int(os.environ.get("TPP_TICKS", "12"))
    g = _load_champion(hof)
    normal = per_tick_divergence(g, ticks, force_legacy_mask_ones=False)
    nomask = per_tick_divergence(g, ticks, force_legacy_mask_ones=True)
    print("PARITE torch-swish vs legacy-core (max|logit diff| par tick)")
    print("  tick   normal   legacy-masque-force-ones")
    for t in range(ticks):
        print(f"  {t:4d}   {normal[t]:.4f}   {nomask[t]:.4f}")
    print(f"resume : max normal={max(normal):.4f} | max sans-masque={max(nomask):.6f} "
          f"-> residu = masque d'attention d'entree ({'CONFIRME' if max(nomask) < 1e-4 else 'PARTIEL'})")
    return {"normal": normal, "nomask": nomask}


if __name__ == "__main__":
    main()
