"""
tools/confirm_b.py — A/B PROPRE de la portée du signal (EDR 040, confirme EDR 038).

Caveat de l'EDR 038 : la portée semblait briser l'impasse, mais comparée à un *autre run*
(EDR 037), pas en A/B simultané. Ici : même HoF de DÉPART, deux lignées **indépendantes** qui
évoluent en parallèle, seule différence = `hear_radius` (0 vs 3). On sauvegarde/restaure le HoF
pour garantir le même point de départ. Verdict : radius 3 bat-il radius 0, toutes choses égales ?

Usage : HEADLESS=1 python -m tools.confirm_b
"""
import os
import shutil
import time

import numpy as np

from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger as async_logger
from tools.comm_lever import run_era

HOF_PKL = "data/hall_of_fame.pkl"
HOF_DIR = "data/agent_states/hall_of_fame"
BAK_PKL = "data/hall_of_fame.pkl.bak_confirmb"
BAK_DIR = "data/agent_states/hall_of_fame.bak_confirmb"


def _backup():
    if os.path.exists(HOF_PKL):
        shutil.copy(HOF_PKL, BAK_PKL)
    if os.path.exists(HOF_DIR):
        shutil.rmtree(BAK_DIR, ignore_errors=True)
        shutil.copytree(HOF_DIR, BAK_DIR)


def _restore():
    if os.path.exists(BAK_PKL):
        shutil.copy(BAK_PKL, HOF_PKL)
    if os.path.exists(BAK_DIR):
        shutil.rmtree(HOF_DIR, ignore_errors=True)
        shutil.copytree(BAK_DIR, HOF_DIR)


def _lineage(config, db, radius, eras):
    mammo, proies = [], []
    for e in range(eras):
        _, b, mp = run_era(config, db, radius)
        mammo.append(b)
        proies.append(mp)
    return mammo, proies


def main(eras=16):
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

    _backup()                                   # snapshot du point de départ COMMUN
    print(f"A/B PROPRE (meme HoF de depart, {eras} eres/lignee) :")
    a_m, a_p = _lineage(config, db, 0, eras)    # lignée A : pas de portée
    _restore()                                  # remettre EXACTEMENT le même départ
    b_m, b_p = _lineage(config, db, 3, eras)    # lignée B : portée 3

    half = eras // 2
    am, ap = np.mean(a_m[half:]), np.mean(a_p[half:])
    bm, bp = np.mean(b_m[half:]), np.mean(b_p[half:])
    print(f"\n  radius 0 (pas de portee) : mammouth_moy={am:.2f}  proies_moy={ap:.2f}")
    print(f"  radius 3 (avec portee)   : mammouth_moy={bm:.2f}  proies_moy={bp:.2f}")
    print(f"  -> delta mammouth = {bm-am:+.2f} ; delta proies = {bp-ap:+.2f}")
    verdict = "CONFIRME (portee aide)" if (bm - am) > 0.2 else "NON confirme (effet faible/nul)"
    print(f"  VERDICT : {verdict}")

    # nettoyage des backups
    for p in (BAK_PKL,):
        if os.path.exists(p):
            os.remove(p)
    shutil.rmtree(BAK_DIR, ignore_errors=True)
    async_logger.stop()


if __name__ == "__main__":
    main()
