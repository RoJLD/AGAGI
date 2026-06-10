"""
tools/curriculum_craft.py — Curriculum développemental sur l'AXE CRAFT (EDR 018/025).

Étape 4 de la Vague 0ter : ramper la *complexité de la mécanique de craft* par paliers,
chacun franchi seulement quand le précédent est MAÎTRISÉ (mastery gate) — la boucle
d'émergence prouvée à L0 (EDR 021) rejouée sur chaque palier.

  L0 (auto)     : tenir tranchant + manche -> lance (aucune action).
  L1 (action)   : idem mais exige le geste `rub`.
  L2 (position) : idem mais exige `rub` ET ingrédients en positions 0 et 1.

À chaque palier, l'ε-greedy explore les gestes requis (grab ; rub dès L1) ; le HoF
persiste -> l'évolution capitalise. On avance quand le craft/ère dépasse `mastery`
pendant `patience` ères consécutives.

Usage : HEADLESS=1 python -m tools.curriculum_craft
"""
import os
import time
import shutil

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from tools.curriculum_grab import run_one_era


def main(levels=(0, 1, 2), max_eras_per_level=14, eps=0.3, mastery=5, patience=2):
    # HoF vierge (backup) pour un curriculum propre.
    if os.path.exists("data/hall_of_fame.pkl"):
        shutil.copy("data/hall_of_fame.pkl", "data/hall_of_fame.pkl.bak_pre_craft")
        os.remove("data/hall_of_fame.pkl")
    shutil.rmtree("data/agent_states/hall_of_fame", ignore_errors=True)

    async_logger.start()
    db = None
    for _ in range(50):
        db = async_logger.get_db()
        if db:
            break
        time.sleep(0.1)
    if db is None:
        print("KuzuDB indisponible.")
        return
    config = WorldConfig()

    summary = {}
    for L in levels:
        print(f"\n=== AXE CRAFT — PALIER L{L} "
              f"({['auto', 'rub', 'position'][L] if L < 3 else '?'}) ===")
        consec = 0
        mastered = False
        for e in range(max_eras_per_level):
            c, t, s = run_one_era(config, db, training=True, eps=eps, craft_level=L)
            consec = consec + 1 if c >= mastery else 0
            tag = " <- MAITRISE" if consec >= patience else ""
            print(f"  L{L} ere {e+1:2d}: crafts={c:3d} ticks={t:3d} consec={consec}{tag}")
            if consec >= patience:
                mastered = True
                break
        summary[L] = "maitrise" if mastered else "NON maitrise (plafond)"
        print(f"  --> L{L} : {summary[L]}")

    print("\n=== BILAN AXE CRAFT ===")
    for L in levels:
        print(f"  L{L} : {summary[L]}")
    async_logger.stop()


if __name__ == "__main__":
    main()
