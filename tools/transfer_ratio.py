"""
tools/transfer_ratio.py — Mesure le Ratio de Transfert (cf. docs/EDR/009).

C'est l'expérience qui VALIDE (ou réfute) l'axe ontogénétique. On compare le
nombre d'ères nécessaires pour maîtriser un monde cible, selon que le cerveau :
  - a d'abord gradué le monde précédent (bras CURRICULUM, hérite du champion),
  - ou démarre de zéro (bras CONTROL, tabula rasa).

    Ratio = eras_to_master(cible | tabula rasa)
            ─────────────────────────────────────────────
            eras_to_master(cible | a gradué le prédécesseur)

  Ratio > 1 : transfert POSITIF — le curriculum accélère (axe validé).
  Ratio < 1 : transfert NÉGATIF — l'entrenchment l'emporte (revert / C_floor plus bas).
  Ratio ≈ 1 : le curriculum n'aide pas sur cette paire de mondes.

⚠️ Stochastique : la simulation n'a pas de seed fixe. Le ratio sur 1 répétition
est bruité — augmenter --repeats pour une estimation stable (au prix du temps).

Usage :
    python -m tools.transfer_ratio --prev stoneage --target agricultural --repeats 3
"""
import argparse

import numpy as np

from src.curriculum.runner import GraduationConfig
from src.graph_rag.async_logger import logger as async_logger
from main_curriculum import run_curriculum


def _eras_to_master(ladder, keep_memory, grad_cfg, **kw):
    """Renvoie (ères_pour_le_dernier_monde, a_gradué?) ou (None, None)."""
    transcript = run_curriculum(
        ladder, keep_memory=keep_memory, grad_cfg=grad_cfg,
        manage_logger=False, **kw,
    )
    if not transcript:
        return None, None
    last = transcript[-1]
    return last["eras"], last["graduated"]


def measure(prev, target, repeats=1, keep_memory=True, **kw):
    grad_cfg = GraduationConfig()
    curric, control = [], []

    async_logger.start()  # un seul cycle DB pour tous les bras
    try:
        for r in range(repeats):
            c_eras, c_grad = _eras_to_master([prev, target], keep_memory, grad_cfg, **kw)
            t_eras, t_grad = _eras_to_master([target], False, grad_cfg, **kw)
            if c_eras is None or t_eras is None:
                print(f"[run {r}] bras invalide (KuzuDB ?) — ignoré.")
                continue
            curric.append(c_eras)
            control.append(t_eras)
            print(f"[run {r}] curriculum={c_eras} ères (grad={c_grad}) | "
                  f"control={t_eras} ères (grad={t_grad})")
    finally:
        async_logger.stop()

    if not curric:
        print("Aucun run valide — impossible de calculer le ratio.")
        return None

    mc, mt = float(np.mean(curric)), float(np.mean(control))
    ratio = (mt / mc) if mc else float("nan")
    verdict = "POSITIF" if ratio > 1 else "NEGATIF" if ratio < 1 else "NEUTRE"
    print(f"\n=== Ratio de Transfert ({prev} → {target}, n={len(curric)}) ===")
    print(f"  curriculum (hérite)   : {mc:.2f} ères")
    print(f"  control (tabula rasa) : {mt:.2f} ères")
    print(f"  RATIO = {ratio:.2f}  ->  transfert {verdict}")
    return ratio


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Mesure le Ratio de Transfert (EDR 009).")
    ap.add_argument("--prev", default="stoneage", help="monde prédécesseur (gradué d'abord)")
    ap.add_argument("--target", default="agricultural", help="monde cible mesuré")
    ap.add_argument("--repeats", type=int, default=1, help="répétitions (réduit le bruit)")
    ap.add_argument("--num-agents", type=int, default=60)
    ap.add_argument("--max-ticks", type=int, default=400)
    args = ap.parse_args()
    measure(
        args.prev, args.target, repeats=args.repeats,
        num_agents=args.num_agents, max_ticks=args.max_ticks,
    )
