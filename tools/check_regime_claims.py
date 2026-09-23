"""Porte 19 -- REGIME CITE <-> REGIME MESURE (classe E8 occ. 4, spec PM S3.5).

  python tools/check_regime_claims.py                    # cliquet : exit 1 sur tout NOUVEAU record discordant
  python tools/check_regime_claims.py --report           # etat complet, exit 0
  python tools/check_regime_claims.py --update-baseline  # gele l'etat courant (dette legataire)
  python tools/check_regime_claims.py --only docs/EDR/X.md

Un record qui cite `forage_payoff = 3.0` doit citer un `results/*.json` SUIVI par git dont le bloc `regime`
porte cette valeur. Mesure le 2026-09-23 (`--report`) : 74 records citent un parametre, 5 concordent avec le
regime publie (CONCORDE) -- les 69 autres (SANS_RESULTS + SANS_REGIME + DISCORDE) sont la dette gelee ici.
Un record illisible est RAPPORTE, jamais compte CONCORDE.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASELINE = os.path.join(_ROOT, "tools", "regime_claims_baseline.json")
PARAMS = ("forage_payoff", "flip_p", "reward_scale", "lr", "n_agents", "num_agents", "max_ticks", "ticks",
          "cog_gain", "base_metabolism", "torch_episode_k")
ALIAS = {"n_agents": "num_agents", "ticks": "max_ticks"}
_NUM = r"([0-9]+(?:[.,][0-9]+)?)"
_CLAIM = re.compile(r"(?<![\w.])(" + "|".join(PARAMS) + r")\s*=\s*" + _NUM + r"(?!\w)(?!\.[0-9])")
_RESULTS = re.compile(r"`[^`]*?(results/[A-Za-z0-9_./*{},\-]+\.json)`")
_CELL_LR = re.compile(r"(?:^|\|)lr=" + _NUM + r"(?:\||$)")
OK = ("SANS_PARAMETRE", "CONCORDE")


def _f(s):
    return float(str(s).replace(",", "."))


def _canon(p):
    return ALIAS.get(p, p)


def claims(texte):
    out = {}
    for p, v in _CLAIM.findall(texte.replace("`", "")):
        out.setdefault(_canon(p), set()).add(_f(v))
    return out


def cited_results(texte):
    return sorted(set(_RESULTS.findall(texte)))


def _developper(root, motif):
    """`{2,3,4}` et `*` -> fichiers existants ; un motif sans joker rend lui-meme (existant ou non)."""
    if not any(c in motif for c in "*{"):
        return [motif]
    m = re.search(r"\{([^{}]*)\}", motif)
    variantes = [motif.replace(m.group(0), x, 1) for x in m.group(1).split(",")] if m else [motif]
    out = []
    for v in variantes:
        if "{" in v:
            out += _developper(root, v)
        elif "*" in v:
            out += sorted(os.path.relpath(p, root).replace("\\", "/") for p in glob.glob(os.path.join(root, v)))
        else:
            out.append(v)
    return out


def _absorber(dst, regime):
    for k, v in (regime or {}).items():
        if isinstance(v, (int, float)) and not isinstance(v, bool) and k in PARAMS:
            dst.setdefault(_canon(k), set()).add(float(v))


def regime_values(data):
    out = {}
    if not isinstance(data, dict):
        return out
    _absorber(out, data.get("regime") if isinstance(data.get("regime"), dict) else None)
    for k, v in data.items():
        if k.startswith("_") or not isinstance(v, dict):
            continue
        _absorber(out, v.get("regime") if isinstance(v.get("regime"), dict) else None)
        m = _CELL_LR.search(k)
        if m:
            out.setdefault("lr", set()).add(_f(m.group(1)))
    return out


def evaluer(texte, lecteur, root=_ROOT):
    cl = claims(texte)
    cites = [c for motif in cited_results(texte) for c in _developper(root, motif)]
    if not cl:
        return {"params": {}, "cites": cites, "statut": "SANS_PARAMETRE", "detail": []}
    mesures = {}
    lus = 0
    for c in cites:
        data = lecteur(c)
        if data is None:
            continue
        lus += 1
        for p, vals in regime_values(data).items():
            mesures.setdefault(p, set()).update(vals)
    params = {p: sorted(v) for p, v in cl.items()}
    if lus == 0:
        return {"params": params, "cites": cites, "statut": "SANS_RESULTS", "detail": ["aucun results/ cite n'est lisible"]}
    if not mesures:
        return {"params": params, "cites": cites, "statut": "SANS_REGIME", "detail": ["aucun bloc regime dans les results cites"]}
    detail = []
    for p, vals in cl.items():
        if p not in mesures:
            detail.append(f"{p} cite {sorted(vals)} : absent du regime publie")
        elif not (vals & mesures[p]):
            detail.append(f"{p} cite {sorted(vals)} : regime publie {sorted(mesures[p])}")
    statut = "DISCORDE" if detail else "CONCORDE"
    return {"params": params, "cites": cites, "statut": statut, "detail": detail}


def _lecteur(root):
    def lire(rel):
        try:
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None
    return lire


def _tracked(root, rel):
    p = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=root, capture_output=True)
    return p.returncode == 0


def analyze(root=_ROOT, suivi=None):
    """`suivi(root, rel) -> bool` injectable (les tests tournent hors depot git) ; defaut : `_tracked`, resolu a l'appel."""
    suivi = _tracked if suivi is None else suivi
    out, illisibles = {}, []
    d = os.path.join(root, "docs", "EDR")
    lecteur = _lecteur(root)

    def lecteur_suivi(rel):
        return lecteur(rel) if suivi(root, rel) else None
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".md"):
            continue
        rel = f"docs/EDR/{name}"
        try:
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                texte = fh.read()
        except (OSError, UnicodeDecodeError):
            illisibles.append(rel)
            continue
        out[rel] = evaluer(texte, lecteur_suivi, root)
    return {"records": out, "illisibles": illisibles}


def _load_baseline():
    if not os.path.exists(_BASELINE):
        return []
    with open(_BASELINE, encoding="utf-8") as fh:
        return json.load(fh).get("legataires", [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--root", default=_ROOT)
    args = ap.parse_args(argv)
    a = analyze(args.root)
    fautifs = sorted(f for f, v in a["records"].items() if v["statut"] not in OK)
    for f in a["illisibles"]:
        print(f"  [ILLISIBLE, non compte] {f}")
    if args.update_baseline:
        with open(_BASELINE, "w", encoding="utf-8") as fh:
            json.dump({"_comment": "Records citant un parametre SANS bloc regime concordant, geles comme dette legataire "
                                   "(E8 occ. 4). Aucun NOUVEAU (tools/check_regime_claims.py).",
                       "legataires": fautifs}, fh, ensure_ascii=False, indent=2)
        print(f"baseline gelee : {len(fautifs)} record(s) sur {len(a['records'])}")
        return 0
    n = {s: sum(1 for v in a["records"].values() if v["statut"] == s) for s in ("SANS_PARAMETRE", "CONCORDE", "SANS_RESULTS", "SANS_REGIME", "DISCORDE")}
    print(f"records : {len(a['records'])} | {n}")
    if args.report:
        for f in fautifs:
            print(f"  [{a['records'][f]['statut']}] {f} : {'; '.join(a['records'][f]['detail'])}")
        return 0
    base = set(_load_baseline())
    only = None if args.only is None else {o.replace("\\", "/") for o in args.only}
    nouveaux = [f for f in fautifs if f not in base and (only is None or f in only)]
    nouveaux += [i for i in a["illisibles"] if only is None or i in only]     # illisible BLOQUE : jamais compte OK
    if nouveaux:
        print("ECHEC : un record cite un parametre que son runner n'a pas PUBLIE (bloc regime) -- E8 occ. 4 :")
        for f in nouveaux:
            v = a["records"].get(f, {"statut": "ILLISIBLE", "detail": []})
            print(f"  [NOUVEAU {v['statut']}] {f} : {'; '.join(v['detail'])}")
        print("-> citer le results/*.json SUIVI dont le bloc regime porte la valeur, ou corriger la valeur.")
        return 1
    print(f"OK : {len(fautifs)} record(s) sans regime concordant, tous legataires (baseline). Aucun nouveau.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
