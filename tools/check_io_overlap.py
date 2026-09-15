"""Cliquet (porte 17) : aucun NOUVEAU génome PERSISTÉ dont les blocs d'ENTRÉE et de SORTIE se chevauchent.

Classe **E24** (2026-09-08) : `MambaBatchModel` dispose les nœuds en [entrées | cachés | sorties] et
calcule `max_H = max_N - max_I - max_O` sans jamais vérifier `max_H >= 0`. Le champion du Hall of Fame
déclare **64 entrées + 126 sorties dans 172 nœuds** : ses 18 premiers logits d'action SONT l'observation,
sans traverser un poids — annuler `W[:num_inputs, :]` ne l'aveugle pas, et une sonde de saillance y lit
1,000 sans que rien ne crie. `assert_no_io_overlap` (E24, `tools/experiment_preflight.py`) protège les
SONDES qui reçoivent un génome ; ce cliquet protège le DÉPÔT DE GÉNOMES lui-même : un lot persisté avec
chevauchement (évolution topologique sous `preserve_io_blocks=False`, le défaut jusqu'à P2.63) entrerait sinon en silence,
et tout record qui le mesurerait plus tard porterait E24 sans le savoir.

Ce qu'il balaie, à COÛT NUL (trois entiers par fichier, jamais les poids) :
  * `data/genomes/**/*.npz` (via `src.paths.genomes`) — 348 génomes au 2026-09-15, **0** chevauchant ;
  * les entrées des Hall of Fame (`data/hall_of_fame*.pkl`, via `src.paths.hall_of_fame`) — 10 entrées à
    **18** chacune (une seule lignée), gelées.

Verdict en CLIQUET : les sujets chevauchants CONNUS sont gelés dans `tools/io_overlap_baseline.json`
(sujet -> chevauchement) ; bloque tout sujet chevauchant NOUVEAU, et tout sujet connu dont le
chevauchement a GRANDI. Un fichier illisible ou sans les trois entiers est RAPPORTÉ (`illisibles`),
jamais compté comme « 0 » — l'absence de mesure n'est pas une mesure nulle.

Usage :
    python tools/check_io_overlap.py                  # arbre entier
    python tools/check_io_overlap.py --update-baseline
"""
import argparse
import glob
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_BASELINE = os.path.join(_ROOT, "tools", "io_overlap_baseline.json")
_HOF_VARIANTES = (None, "famine", "famine_s43")


def overlap_of(num_inputs, num_outputs, num_nodes):
    """Chevauchement des blocs d'entrée et de sortie : `max(0, I + O - N)`. 64 + 126 - 172 = 18."""
    return max(0, int(num_inputs) + int(num_outputs) - int(num_nodes))


def scan_npz(root=None):
    """{chemin relatif: {num_inputs, num_outputs, num_nodes, overlap}} pour chaque `.npz` sous `root`
    (défaut : `src.paths.genomes()`). Les fichiers sans les trois entiers vont dans `illisibles`."""
    import numpy as np
    if root is None:
        from src.paths import genomes
        root = str(genomes())
    sujets, illisibles = {}, []
    for p in sorted(glob.glob(os.path.join(root, "**", "*.npz"), recursive=True)):
        rel = os.path.relpath(p, root).replace("\\", "/")
        try:
            with np.load(p, allow_pickle=False) as z:
                if not all(k in z for k in ("num_inputs", "num_outputs", "num_nodes")):
                    illisibles.append(rel)
                    continue
                ni, no, nn = int(z["num_inputs"]), int(z["num_outputs"]), int(z["num_nodes"])
        except Exception as exc:                        # noqa: BLE001 — rapporté, jamais compté comme 0
            illisibles.append(f"{rel} ({type(exc).__name__})")
            continue
        sujets[rel] = {"num_inputs": ni, "num_outputs": no, "num_nodes": nn, "overlap": overlap_of(ni, no, nn)}
    return sujets, illisibles


def scan_hof(variantes=_HOF_VARIANTES):
    """Une entrée par génome de chaque Hall of Fame PRÉSENT : `hall_of_fame.pkl#<rang>`."""
    from src.paths import hall_of_fame
    from src.seed_ai.persistence import load_hall_of_fame
    import src.seed_ai.persistence as P
    sujets, illisibles = {}, []
    for v in variantes:
        p = str(hall_of_fame(v))
        if not os.path.exists(p):
            continue
        nom = os.path.basename(p)
        ancien = P.HALL_OF_FAME_PATH
        try:
            P.HALL_OF_FAME_PATH = p          # module-level, lu par load_hall_of_fame
            _version, entries = load_hall_of_fame()
        except Exception as exc:                        # noqa: BLE001
            illisibles.append(f"{nom} ({type(exc).__name__})")
            continue
        finally:
            P.HALL_OF_FAME_PATH = ancien
        for i, e in enumerate(entries):
            g = e.genome
            sujets[f"{nom}#{i}"] = {"num_inputs": int(g.num_inputs), "num_outputs": int(g.num_outputs),
                                    "num_nodes": int(g.num_nodes),
                                    "overlap": overlap_of(g.num_inputs, g.num_outputs, g.num_nodes)}
    return sujets, illisibles


def scan():
    s1, i1 = scan_npz()
    s2, i2 = scan_hof()
    return {**s1, **s2}, i1 + i2


def etat(sujets, baseline):
    """VERDICT du cliquet, jamais un booléen : `nouveaux` (chevauchants hors baseline), `aggraves`
    (connus dont le chevauchement a grandi), `connus`, et le nombre de sujets balayés."""
    chev = {k: v["overlap"] for k, v in sujets.items() if v["overlap"] > 0}
    nouveaux = sorted(k for k in chev if k not in baseline)
    aggraves = sorted(k for k in chev if k in baseline and chev[k] > int(baseline[k]))
    return {"sujets": len(sujets), "chevauchants": len(chev), "nouveaux": nouveaux, "aggraves": aggraves,
            "connus": sorted(k for k in chev if k in baseline and chev[k] <= int(baseline[k]))}


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return {}
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true")
    args = ap.parse_args(argv)
    sujets, illisibles = scan()
    if args.update_baseline:
        gele = {k: v["overlap"] for k, v in sorted(sujets.items()) if v["overlap"] > 0}
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump(gele, fh, indent=2, ensure_ascii=False)
        print(f"baseline gelée : {len(gele)} sujet(s) chevauchant(s) sur {len(sujets)} -> {_BASELINE}")
        return 0
    e = etat(sujets, _load_baseline())
    print(f"génomes persistés : {e['sujets']} | chevauchants : {e['chevauchants']} "
          f"(connus {len(e['connus'])}, nouveaux {len(e['nouveaux'])}, aggravés {len(e['aggraves'])})")
    for k in illisibles:
        print(f"  [ILLISIBLE, non compté] {k}")
    for k in e["nouveaux"]:
        print(f"  [NOUVEAU CHEVAUCHEMENT] {k} : {sujets[k]['overlap']} "
              f"({sujets[k]['num_inputs']} + {sujets[k]['num_outputs']} dans {sujets[k]['num_nodes']})")
    for k in e["aggraves"]:
        print(f"  [CHEVAUCHEMENT AGGRAVÉ] {k} : {sujets[k]['overlap']}")
    if e["nouveaux"] or e["aggraves"]:
        print("Un génome dont les blocs se chevauchent a des logits d'action qui SONT l'observation (E24) : "
              "toute sonde de perception le lira faussement. Régénérer avec `preserve_io_blocks=True`, ou "
              "geler EN CONNAISSANCE : python tools/check_io_overlap.py --update-baseline")
        return 1
    print("OK : aucun nouveau génome persisté à chevauchement entrée/sortie.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
