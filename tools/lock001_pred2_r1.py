# -*- coding: utf-8 -*-
"""LOCK-001, PRÉDICTION N° 2 -- « un levier qui perce UN fil sans effet sur les autres RÉFUTE l'identité ».

[[EDR-LOCK-002]] a mesuré que le PAS d'apprentissage perce le fil « mémoire » : à D = 2, sur le substrat
bilinéaire, `lr = 0,0005` fait passer la rétention à deux délais de la chance à 0,50 (3 600 épisodes)
puis 0,78 (14 400, n = 12). LOCK-001 dit que trois fils creusent le même mur ; sa clause n° 2 rend cela
falsifiable. Ce runner applique le MÊME levier au fil « coordination référentielle différée »
([[EDR-DELAYED-COORD]], bras RETAIN), au MÊME point (bilinéaire, D = 2, `lr` 0,0005) -- avec PRESENT,
qui ne demande aucune rétention, comme RÉFÉRENCE qui doit apprendre (E19 : un nul à référence effondrée
est vide).

Ce qu'on sait déjà (DELAYED-COORD, n = 12, substrat PLAIN, 1 600 épisodes) : RETAIN 0,227 (lr 0,05) →
0,284 (lr 0,002), 12/12 -- le pas compte, mais 0,284 n'est pas « appris » (chance 0,167, plafond du
séparable 0,389).

Cellules : (lr 0,002, 3 600), (lr 0,0005, 3 600), (lr 0,0005, 14 400) × {RETAIN, PRESENT} × seeds 0-2.
Coût mesuré (2026-09-14, machine libre) : RETAIN ~61 s / 1000 ép., PRESENT ~43 s / 1000 ép.

Usage :
  python tools/lock001_pred2_r1.py            # une tranche (SWEEP_SLICE_S, défaut 3000 s)
  python tools/lock001_pred2_r1.py --lecture  # applique la règle scellée
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.experiment_preflight import assert_control_family, declare_design  # noqa: E402
from tools.preregister import stamp, verify  # noqa: E402

NOM_REGLE = "LOCK-001-PRED2-R1"
OUT = os.path.join("results", "lock001_pred2_r1.json")
SLICE_S = float(os.environ.get("SWEEP_SLICE_S", "3000"))
SEEDS = (0, 1, 2)
BRAS = ("RETAIN", "PRESENT")
CELLULES = [(0.002, 3600), (0.0005, 3600), (0.0005, 14400)]     # (lr, episodes)
FIXE = dict(D=2, n_agents=16, K=6, V=8, flip_p=0.0, credit="bptt", choice_decoy=False,
            sender_lr=0.05, bilinear=True)


def cle(bras, lr, ep, seed):
    return f"{bras}|lr={lr:g}|ep={ep}|seed={seed}"


def design():
    return declare_design(
        question="Le PAS qui perce le fil memoire (LOCK-002) perce-t-il le fil coordination differee "
                 "(DELAYED-COORD, bras RETAIN) au meme point ? -- prediction n 2 de LOCK-001",
        replication_unit="seed", n_independent=len(SEEDS),
        links={"lr, episodes -> RETAIN_intact": "measured",
               "lr, episodes -> PRESENT_intact (reference E19)": "measured",
               "RETAIN_intact -> 'l identite des trois murs tient / est refutee'": "inferred"},
        allow_inferred_reason="n = 3 exploratoire : toute branche tranchante declenche n = 12 avant de graver",
        cost_estimate="18 cellules ; ~61 s/1000 ep (RETAIN), ~43 s (PRESENT) -> ~2 h CPU, sans bail kuzu",
        control_family=assert_control_family(cells=len(CELLULES) * len(SEEDS)),
    )


def _cellules_de(regle):
    """Les points (lr, episodes) de la regle si elle les porte (barreau 2+), sinon ceux du barreau 1."""
    return [(c["lr"], c["episodes"]) for c in regle["cellules"]] if "cellules" in regle else CELLULES


def _seeds_de(regle):
    """Les seeds de la regle (n = 12 au barreau N12), sinon ceux du barreau 1 (0-2)."""
    return tuple(regle["seeds"]) if "seeds" in regle else SEEDS


def _importer(db, regle):
    """Points MESURES SOUS UNE AUTRE REGLE et declares importes par celle-ci (`points_importes`) : lus
    depuis leur fichier, jamais re-mesures ni re-ecrits. La regle dit d'ou vient chaque point."""
    for imp in regle.get("points_importes", []):
        src = json.load(open(imp["fichier"], encoding="utf-8"))
        for c in imp["cellules"]:
            for b in BRAS:
                for s_ in _seeds_de(regle):
                    k = cle(b, c["lr"], c["episodes"], s_)
                    if k in src and k not in db:
                        db[k] = dict(src[k], importe_de=imp["fichier"])
    return db


def _lecture_pred2(db, regle):
    """LECTURE de la règle scellée. PURE, calibrée dans tests/sandbox/test_lock001_pred2_r1.py.

    Par point (lr, ep) : la référence PRESENT doit apprendre (médiane >= seuil_reference), sinon le
    point est ININTERPRETABLE et n'entre dans aucune branche. Sur les points interprétables :
      PERCE          -- RETAIN médiane >= seuil_perce ET 3/3 > seuil_seed sur au moins un point ;
      MONTE          -- sinon, RETAIN médiane >= seuil_monte sur au moins un point ;
      NE_PERCE_PAS   -- RETAIN médiane < seuil_seed sur TOUS les points interprétables ;
      AUTRE          -- le reste, rapporté tel quel.
    INCOMPLET prime ; SANS_REFERENCE si aucun point n'est interprétable."""
    seuils = regle["seuils"]
    cellules = _cellules_de(regle)
    seeds = _seeds_de(regle)
    # nombre MINIMUM de seeds au-dessus de seuil_seed pour PERCE : tous par defaut (3/3 au barreau 1),
    # 11/12 au barreau N12 (test des signes unilateral, p <= 0,0032 -- convention du n = 12 du depot).
    seeds_min = int(seuils.get("seeds_min", len(seeds)))
    manquantes = [cle(b, lr, ep, s) for lr, ep in cellules for b in BRAS for s in seeds
                  if cle(b, lr, ep, s) not in db]
    if manquantes:
        return {"branche": "INCOMPLET", "manquantes": manquantes}

    def med(bras, lr, ep):
        vals = [db[cle(bras, lr, ep, s)]["intact"] for s in seeds]
        return statistics.median(vals), vals

    points, interpretables = {}, []
    for lr, ep in cellules:
        mr, vr = med("RETAIN", lr, ep)
        mp, vp = med("PRESENT", lr, ep)
        ok = mp >= seuils["seuil_reference"]
        points[f"lr={lr:g}|ep={ep}"] = {"RETAIN_intact": mr, "RETAIN_seeds": vr, "PRESENT_intact": mp,
                                        "PRESENT_seeds": vp, "reference_apprend": ok}
        if ok:
            interpretables.append((mr, vr))
    out = {"points": points, "reference_retain_n12_plain": regle["reference_n12"]["RETAIN_intact_lr0002"]}
    if not interpretables:
        out["branche"] = "SANS_REFERENCE"
        return out
    if any(m >= seuils["seuil_perce"] and sum(v > seuils["seuil_seed"] for v in vals) >= seeds_min
           for m, vals in interpretables):
        out["branche"] = "PERCE"
    elif any(m >= seuils["seuil_monte"] for m, _ in interpretables):
        out["branche"] = "MONTE"
    elif all(m < seuils["seuil_seed"] for m, _ in interpretables):
        out["branche"] = "NE_PERCE_PAS"
    else:
        out["branche"] = "AUTRE"
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    nom = argv[argv.index("--regle") + 1] if "--regle" in argv else NOM_REGLE
    regle = verify(nom)
    out_path = OUT if nom == NOM_REGLE else os.path.join("results", nom.lower().replace("-", "_") + ".json")
    cellules = _cellules_de(regle)
    seeds = _seeds_de(regle)
    db = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    if "--lecture" in argv:
        print(json.dumps(_lecture_pred2(_importer(dict(db), regle), regle), indent=1, ensure_ascii=False))
        return 0
    importes = _importer({}, regle)          # a ne PAS re-mesurer
    fixe = dict(FIXE, **regle.get("fixe_override", {}))   # ex. substrat plain au barreau 3 -- LU dans la regle
    from tools.delayed_coordination_demand_probe import _train_and_eval_arm
    d = design()
    print(f"regle {nom} | design : {d.get('replication_unit')} x {len(seeds)} ; "
          f"{len(cellules) * len(BRAS) * len(seeds)} cellules dont {len(importes)} importees ; "
          f"{len(db)} deja mesuree(s) -> {out_path}")
    t0 = time.time()
    for lr, ep in cellules:
        for bras in BRAS:
            for s in seeds:
                k = cle(bras, lr, ep, s)
                if k in db or k in importes:
                    continue
                if time.time() - t0 > SLICE_S:
                    print(f"tranche epuisee ({SLICE_S:.0f} s) -- relancer pour continuer")
                    return 0
                tc = time.time()
                ai, aa, _ = _train_and_eval_arm(seed=s, arm=bras, episodes=ep, lr=lr, **fixe)
                db[k] = {"intact": float(ai), "ablated": float(aa), "secondes": round(time.time() - tc, 1)}
                json.dump(stamp(db, nom), open(out_path, "w", encoding="utf-8"), indent=1)   # P2.68
                print(f"  {k}: intact={ai:.3f} ablated={aa:.3f} ({db[k]['secondes']} s)")
    print("toutes les cellules sont mesurees -> --lecture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
