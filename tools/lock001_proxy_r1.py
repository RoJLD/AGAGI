# -*- coding: utf-8 -*-
"""LOCK-001-PROXY, BARREAU 1 -- « des épisodes plus longs suffisent-ils à D = 2 ? » (P4.5, rang 17).

L'escalier prescrit par `tools/lang_memory_sweep_reference_point.py:101-103` va du moins cher au plus
cher : épisodes plus longs -> curriculum D 0->1->2 -> amorçage supervisé court puis REINFORCE (le test
que LOCK-001 nomme lui-même). Ce runner ne fait QUE le premier barreau, et sa règle scellée dit ce
qu'il ne tranche PAS.

Point-référence (results/lang_memory_sweep.json) : bilinéaire, lr = 0,002, 3600 épisodes, D = 0
apprend (médiane 0,744, 3/3 seeds) ; D = 2 au même point : 3/3 à la chance (0,211 / 0,183 / 0,170).
Ici : D = 2, MÊME point, épisodes 7200 et 14400 ; et un second `lr` (0,0005) sur le barreau du haut,
pour que tout NUL soit confronté à l'optimiseur (E19, RETAIN-COMPOSE-LR : un nul 2-pas à `lr` fixe
s'est déjà retourné une fois).

Coût mesuré (2026-09-14, machine partageant un job in-world) : ~97 s / 1000 épisodes / cellule
(majorant). 9 cellules -> ~105 min CPU, SANS bail `kuzu`, en tranches résumables.

Usage :
  python tools/lock001_proxy_r1.py            # une tranche de SWEEP_SLICE_S secondes (défaut 540)
  python tools/lock001_proxy_r1.py --lecture  # applique la règle scellée aux cellules mesurées
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.experiment_preflight import assert_control_family, declare_design  # noqa: E402
from tools.preregister import verify  # noqa: E402

NOM_REGLE = "LOCK-001-PROXY-R1"
OUT = os.path.join("results", "lock001_proxy_r1.json")
SLICE_S = float(os.environ.get("SWEEP_SLICE_S", "540"))
SEEDS = (0, 1, 2)
K, N_AGENTS, D = 6, 16, 2
CELLULES = [(0.002, 7200), (0.002, 14400), (0.0005, 14400)]   # (lr, episodes)
CHANCE = 1.0 / K


def cle(lr, ep, seed):
    return f"lr={lr:g}|ep={ep}|D={D}|seed={seed}"


def design():
    """Déclaration ÉCRITE (pré-vol) : unité = seed, n = 3 par cellule (EXPLORATOIRE, sous n_floor=12),
    famille = 9 cellules dont chacune est confrontée à la chance."""
    return declare_design(
        question="A D=2, des episodes plus longs (7200, 14400) font-ils sortir lang_i de la chance, "
                 "la ou 3600 episodes n'y suffisent pas ? (barreau 1 de LOCK-001-PROXY)",
        replication_unit="seed", n_independent=len(SEEDS),
        # vocabulaire ferme du pre-vol : 'measured' / 'inferred' (la garde le refuse sinon)
        links={"episodes -> lang_i(D=2)": "measured", "lr -> lang_i(D=2) [clause E19]": "measured",
               "lang_i(D=2) -> 'le mur LOCK-001 est perce'": "inferred"},
        allow_inferred_reason="n = 3 est EXPLORATOIRE (sous n_floor = 12) : un PERCE indicatif declenche "
                              "le barreau 1b a n = 12, jamais un record -- le maillon reste inferre "
                              "jusque-la, et la regle scellee le dit",
        cost_estimate="9 cellules x ~97 s/1000 ep -> ~105 min CPU (majorant), sans bail kuzu",
        control_family=assert_control_family(cells=len(CELLULES) * len(SEEDS)),
    )


def _lecture_r1(db, regle):
    """LECTURE de la règle scellée sur les cellules mesurées. PURE (pas de simulation), calibrée dans
    tests/sandbox/test_lock001_proxy_r1.py. Renvoie un dict avec `branche` et les médianes.

    Branches (ORDRE IMPOSÉ, la première qui mord arrête) :
      INCOMPLET       -- une cellule manque : aucune lecture ;
      PERCE_INDICATIF -- au barreau du haut (14400, lr 0,002) médiane lang_i >= seuil_perce ET 3/3 seeds
                         > seuil_seed : déclenche le barreau 1b (n = 12), JAMAIS un record ;
      PERCE_PAR_LR    -- 14400/0,002 nul mais 14400/0,0005 >= seuil_perce : E19, le pas était du
                         mauvais côté -- même suite que PERCE_INDICATIF, sur le lr qui perce ;
      TENDANCE        -- la médiane monte d'au moins `delta_tendance` de 3600 -> 14400 sans atteindre
                         seuil_perce : prolonger (barreau 1c, 28800) AVANT le curriculum ;
      NE_PERCE_PAS    -- médiane < seuil_seed aux DEUX lr à 14400 : barreau 1 réfuté, passer au
                         curriculum (barreau 2) ;
      AUTRE           -- tout le reste, rapporté tel quel, aucun re-run sans re-scellement."""
    seuils = regle["seuils"]
    manquantes = [cle(lr, ep, s) for lr, ep in CELLULES for s in SEEDS if cle(lr, ep, s) not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": manquantes}

    def med(lr, ep):
        vals = [db[cle(lr, ep, s)]["lang_i"] for s in SEEDS]
        return statistics.median(vals), vals

    m_haut, v_haut = med(0.002, 14400)
    m_lr, v_lr = med(0.0005, 14400)
    m_mi, _ = med(0.002, 7200)
    ref3600 = regle["reference_3600"]["mediane_lang_i_D2"]
    out = {"mediane_14400_lr0002": m_haut, "mediane_14400_lr00005": m_lr, "mediane_7200": m_mi,
           "reference_3600": ref3600, "seeds_14400_lr0002": v_haut, "seeds_14400_lr00005": v_lr}
    if m_haut >= seuils["seuil_perce"] and all(v > seuils["seuil_seed"] for v in v_haut):
        out["branche"] = "PERCE_INDICATIF"
    elif m_lr >= seuils["seuil_perce"] and all(v > seuils["seuil_seed"] for v in v_lr):
        out["branche"] = "PERCE_PAR_LR"
    elif max(m_haut, m_lr) >= ref3600 + seuils["delta_tendance"]:
        out["branche"] = "TENDANCE"
    elif m_haut < seuils["seuil_seed"] and m_lr < seuils["seuil_seed"]:
        out["branche"] = "NE_PERCE_PAS"
    else:
        out["branche"] = "AUTRE"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    regle = verify(NOM_REGLE)          # lève si la règle a été retouchée après scellement
    db = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture_r1(db, regle), indent=1, ensure_ascii=False))
        return 0
    from tools.language_memory_demand_probe import _train_and_eval
    d = design()
    print(f"design : {d.get('replication_unit')} x {d.get('n_independent')} ; famille "
          f"{len(CELLULES) * len(SEEDS)} cellules ; {len(db)} cellule(s) deja mesuree(s)")
    t0 = time.time()
    for lr, ep in CELLULES:
        for s in SEEDS:
            k = cle(lr, ep, s)
            if k in db:
                continue
            if time.time() - t0 > SLICE_S:
                print(f"tranche epuisee ({SLICE_S:.0f} s) -- relancer pour continuer")
                return 0
            tc = time.time()
            li, la, ci, ca = _train_and_eval(seed=s, episodes=ep, n_agents=N_AGENTS, K=K, D=D, lr=lr,
                                             memory_mode="learned", control_mode="feedforward",
                                             bilinear=True)
            db[k] = {"lang_i": li, "lang_a": la, "ctrl_i": ci, "ctrl_a": ca,
                     "secondes": round(time.time() - tc, 1)}
            json.dump(db, open(OUT, "w", encoding="utf-8"), indent=1)
            print(f"  {k}: lang_i={li:.3f} lang_a={la:.3f} ctrl_i={ci:.3f} ctrl_a={ca:.3f} "
                  f"({db[k]['secondes']} s)")
    print("toutes les cellules sont mesurees -> --lecture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
