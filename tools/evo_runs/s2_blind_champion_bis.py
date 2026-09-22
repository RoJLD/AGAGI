"""S2-BLIND-CHAMPION-bis (P2.42, 2026-09-16) — le champion HoF survit-il MIEUX quand il ne voit plus ?

Le `-bis` corrige l'E8 du sceau d'origine (`S2-BLIND-CHAMPION`) : annuler `W[:num_inputs, :]` ne coupait pas
l'observation (elle entrait encore par `H[:, :max_I] = x`, dont 18 logits d'action SONT l'observation — E24) et
changeait le CORPS (drain 2,40 → 1,30, E26). Ici l'aveuglement se fait à l'ENTRÉE : la politique reçoit une
observation NULLE (`InputBlindFrozenMamba`), le génome, le corps, les biais et la récurrence sont ceux du champion,
bit-identiques, et le chemin d'identité est coupé lui aussi. L'apprenant legacy est GELÉ dans les DEUX bras
(`compute_policy_gradient` no-op ; les écritures NTM de `forward` ne le sont pas — même chose dans les deux bras,
déclaré). La bande RNG est APPARIÉE (`run_ablation_map(paired_band=True)`) et le no-op est mesuré par bras.

Contrôles, AVANT la DV (ordre du sceau) : (i) l'intervention est réelle et minimale — la politique aveugle ignore
l'observation (prouvé à 0 monde : `forward(obs)` == `forward(obs')` bit à bit) et le génome des deux bras est le
MÊME objet ; (ii) l'aveuglement mord — l'ablation de perception ne change RIEN au bras aveugle : à bande appariée
et observation nulle les deux runs sont attendus BIT-IDENTIQUES, `within_ratio` = 1,000 exactement (tolérance
scellée 0,05, résidu publié) ; (iii) plancher 24,0 sur le bras intact ; (iv) non-dégénérescence ; (v) famille.
DV : `r_blind` = survie médiane aveugle / intacte par seed, `blind_champion_verdict` (instrument calibré,
barres 1,20 / 1,05, test des signes). Régime gravé de S2-002/003 : stoneage, 12 agents, 200 ticks, K=12, 7 seeds.
Usage : python -m tools.evo_runs.s2_blind_champion_bis   (bail `kuzu`)
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.agents.mamba_agent import MambaBatchModel
from tools.evo_runs.s2_blind_champion import (FLOOR, K, REGIME, SEEDS, WORLD, blind_champion_verdict)

PREREG = "S2-BLIND-CHAMPION-bis"


class FrozenCreditMamba(MambaBatchModel):
    """Le champion tel quel, apprenant legacy GELÉ : `compute_policy_gradient` ne fait rien. Les écritures
    NTM de `forward` restent (elles sont la politique, pas l'apprenant) — identiques dans les deux bras."""

    def compute_policy_gradient(self, rewards_batch, actions_batch=None):
        return None


class InputBlindFrozenMamba(FrozenCreditMamba):
    """Le champion AVEUGLÉ À L'ENTRÉE : l'observation est remplacée par des zéros de même forme AVANT le
    forward normal. W, corps, biais, récurrence : bit-identiques au champion. Dérangé, un zéro reste un zéro."""

    def forward(self, batch_obs, env_surprise_batch=None):
        return super().forward(np.zeros_like(np.asarray(batch_obs, dtype=np.float32)), env_surprise_batch)


class PartialInputBlindFrozenMamba(FrozenCreditMamba):
    """DÉCOMPOSITION (S2-BLIND-CHAMPION-DECOMP-R1) : le bras aveugle total met `x = 0`, ce qui coupe DEUX choses à la
    fois — l'entrée du réseau récurrent (excitation) et les 18 nœuds d'IDENTITÉ (`max_N - max_O .. max_I`, dont la
    valeur est directement un logit d'action : EDR-HOF-IO-OVERLAP). Ici on ne met à zéro qu'UNE tranche de x, calculée
    sur le modèle : `_zero_slice()` -> (lo, hi). Le gain du routeur (tanh(x·router)) voit la tranche restante."""

    def _zero_slice(self):
        raise NotImplementedError

    def forward(self, batch_obs, env_surprise_batch=None):
        x = np.array(batch_obs, dtype=np.float32, copy=True)
        lo, hi = self._zero_slice()
        x[:, lo:hi] = 0.0
        return super().forward(x, env_surprise_batch)


class BlindExceptIdentityFrozenMamba(PartialInputBlindFrozenMamba):
    """Entrée du réseau COUPÉE (x[:, :max_N-max_O] = 0), les 18 nœuds d'identité GARDÉS."""

    def _zero_slice(self):
        return 0, self.max_N - self.max_O


class IdentityZeroedFrozenMamba(PartialInputBlindFrozenMamba):
    """Les 18 nœuds d'identité seuls COUPÉS (x[:, max_N-max_O:max_I] = 0), le reste de l'entrée GARDÉ."""

    def _zero_slice(self):
        return self.max_N - self.max_O, self.max_I


def blind_champion_verdict_ter(rows, floor=FLOOR, **kw):
    """S2-BLIND-CHAMPION-ter (P2.42) : la clause (iii) du `-bis` écartait tout seed dont le bras INTACT est sous le
    plancher 24,0 -- et le `-bis` a rendu INDETERMINE-DEGENERE (7/7 écartés) parce que le champion à crédit gelé
    survit 20,5-22,5 ticks : l'intact SOUS le plancher est ici le PHÉNOMÈNE, pas un artefact. La clause (iii)-ter :
    un seed n'est écarté que si les DEUX bras sont au plancher ou dessous (le ratio n'y mesure rien) ; sinon
    `intact_median` est publié face au plancher et un intact sous le plancher est un FAIT nommé (`sous_plancher`).
    Le reste du verdict est l'instrument calibré d'origine, appelé avec `floor=0.0` sur les seeds gardés."""
    rows = list(rows or [])
    gardes, ecartes, sous = [], [], []
    for r in rows:
        i, b = r.get("intact") or {}, r.get("blind") or {}
        im, bm = float(i.get("intact_median", 0.0)), float(b.get("intact_median", 0.0))
        if im <= floor and bm <= floor:
            ecartes.append(r.get("seed"))
        else:
            gardes.append(r)
            if im < floor:
                sous.append(r.get("seed"))
    out = blind_champion_verdict(gardes, floor=0.0, **kw)
    out["ecartes"] = sorted(ecartes + [s for s in out.get("ecartes", []) if s not in ecartes])
    out["intact_sous_plancher"] = sous
    if rows and not gardes:                              # mesuré, mais rien d'exploitable : pas « sans mesure »
        out["verdict"] = "INDETERMINE-DEGENERE"
        out["echecs"] = [f"0 seed(s) exploitable(s) sur {len(rows)} : les deux bras au plancher {floor} ou dessous partout"]
    return out


def run_blind_champion_bis(seeds=SEEDS, k=K, regime=None, world=WORLD, map_fn=None, champion_fn=None, verbose=True,
                           verdict_fn=blind_champion_verdict):
    """Deux bras par seed, MÊME génome (le champion), politiques `FrozenCreditMamba` (intact) et
    `InputBlindFrozenMamba` (aveugle), bande appariée, no-op mesuré. Garde d'arguments en tête."""
    regime = dict(regime or REGIME)
    seeds = list(seeds or [])
    if not seeds or int(k) <= 0 or int(regime.get("num_agents", 0)) <= 0 or int(regime.get("max_ticks", 0)) <= 0:
        raise ValueError(f"run_blind_champion_bis : argument degenere (seeds={len(seeds)}, K={k}, regime={regime})")
    if map_fn is None:
        from tools.s2_demand_ablation import run_ablation_map as map_fn
    if champion_fn is None:
        from tools.s2_demand import load_champion_genome as champion_fn
    rows = []
    for s in seeds:
        ref = champion_fn()
        W0 = np.array(ref.W, copy=True)
        mi = map_fn(worlds=[world], seed=s, K=k, subject=ref, batch_model_cls=FrozenCreditMamba,
                    paired_band=True, noop_control=True, **regime)[world]
        mb = map_fn(worlds=[world], seed=s, K=k, subject=ref, batch_model_cls=InputBlindFrozenMamba,
                    paired_band=True, noop_control=True, **regime)[world]
        # (i) : même génome dans les deux bras, et la politique aveugle ignore l'observation (test à 0 monde)
        mb = dict(mb, w_ok=bool(np.array_equal(W0, np.asarray(ref.W)) and mb.get("policy") == "InputBlindFrozenMamba"
                                and mi.get("policy") == "FrozenCreditMamba" and mb.get("reference") == "paired_band"))
        rows.append({"seed": s, "intact": mi, "blind": mb})
        if verbose:
            print(f"  seed {s} : intact={mi['intact_median']:6.1f} (noop {mi['noop']['ratio']:.3f}) | "
                  f"aveugle={mb['intact_median']:6.1f} (noop {mb['noop']['ratio']:.3f}) | "
                  f"r={mb['intact_median'] / max(mi['intact_median'], 1e-9):.3f} | (i) {'ok' if mb['w_ok'] else 'ECHEC'} "
                  f"| (ii) within_aveugle={mb['within_ratio']:.4f}", flush=True)
    return rows, verdict_fn(rows)


SEEDS_TER = (3032, 3033, 3034, 3035, 3036, 3037, 3038)      # population de seeds NEUVE : le -bis a été vu (E11)


def decomp_verdict(rows, bar_high=1.20, bar_low=1.05, seeds_min=6, tol_noop=0.0):
    """S2-BLIND-CHAMPION-DECOMP-R1 : décomposer le +61 % de l'aveugle total en (a) entrée du réseau coupée, identités
    gardées (`r_ex`) et (b) identités seules coupées (`r_id`), chaque r = survie bras / survie intact (référence -ter,
    même seed). Contrôles avant la DV : (i) même génome (w_ok) ; no-op apparié des bras nouveaux = 1,000 exactement
    (tol 0) -- sinon INDETERMINE-HARNAIS. Branches, ordre imposé : INCOMPLET ; INDETERMINE-HARNAIS ; EXCITATION
    (r_ex >= 1,20 sur >= 6/7 ET r_id <= 1,05 sur >= 6/7) ; IDENTITE (l'inverse) ; LES_DEUX (les deux >= 1,20 sur >= 6/7) ;
    NI_L_UN_NI_L_AUTRE (les deux <= 1,05 sur >= 6/7 : l'effet exige de couper les deux, non additif) ; MIXTE (sinon)."""
    rows = list(rows or [])
    out = {"verdict": None, "n": len(rows), "r_ex": [], "r_id": [], "echecs": []}
    if not rows:
        out["verdict"] = "INDETERMINE-SANS-MESURE"
        return out
    for r in rows:
        for bras in ("except_identity", "identity_zeroed"):
            b = r.get(bras) or {}
            if not b:
                out["echecs"].append(f"seed {r.get('seed')} : bras {bras} manquant")
                continue
            if not b.get("w_ok"):
                out["echecs"].append(f"seed {r.get('seed')} : (i) génome ou politique inattendus sur {bras}")
            nr = (b.get("noop") or {}).get("ratio")
            if nr is None or abs(float(nr) - 1.0) > tol_noop:
                out["echecs"].append(f"seed {r.get('seed')} : no-op apparié != 1,000 sur {bras} ({nr})")
    if out["echecs"]:
        out["verdict"] = "INDETERMINE-HARNAIS"
        return out
    for r in rows:
        i = float(r["intact_median_ref"])
        out["r_ex"].append(float(r["except_identity"]["intact_median"]) / max(i, 1e-9))
        out["r_id"].append(float(r["identity_zeroed"]["intact_median"]) / max(i, 1e-9))
    hi_ex = sum(1 for x in out["r_ex"] if x >= bar_high)
    lo_ex = sum(1 for x in out["r_ex"] if x <= bar_low)
    hi_id = sum(1 for x in out["r_id"] if x >= bar_high)
    lo_id = sum(1 for x in out["r_id"] if x <= bar_low)
    out.update({"med_r_ex": statistics.median(out["r_ex"]), "med_r_id": statistics.median(out["r_id"]),
                "hi_ex": hi_ex, "lo_ex": lo_ex, "hi_id": hi_id, "lo_id": lo_id})
    if hi_ex >= seeds_min and lo_id >= seeds_min:
        out["verdict"] = "EXCITATION"
    elif hi_id >= seeds_min and lo_ex >= seeds_min:
        out["verdict"] = "IDENTITE"
    elif hi_ex >= seeds_min and hi_id >= seeds_min:
        out["verdict"] = "LES_DEUX"
    elif lo_ex >= seeds_min and lo_id >= seeds_min:
        out["verdict"] = "NI_L_UN_NI_L_AUTRE"
    else:
        out["verdict"] = "MIXTE"
    return out


def run_decomp(seeds=SEEDS_TER, k=K, regime=None, world=WORLD, map_fn=None, champion_fn=None, ref_rows=None, verbose=True):
    """Deux bras nouveaux par seed (mêmes seeds que le -ter, dont on importe intact_median comme référence appariée)."""
    regime = dict(regime or REGIME)
    seeds = list(seeds or [])
    if not seeds or int(k) <= 0 or int(regime.get("num_agents", 0)) <= 0 or int(regime.get("max_ticks", 0)) <= 0:
        raise ValueError(f"run_decomp : argument degenere (seeds={len(seeds)}, K={k}, regime={regime})")
    if ref_rows is None:
        from src.paths import results_file
        ref = json.load(open(str(results_file("s2_blind_champion_ter.json")), encoding="utf-8"))
        ref_rows = {r["seed"]: r for r in ref["rows"]}
    if map_fn is None:
        from tools.s2_demand_ablation import run_ablation_map as map_fn
    if champion_fn is None:
        from tools.s2_demand import load_champion_genome as champion_fn
    rows = []
    for s in seeds:
        ref_r = ref_rows[s]
        champ = champion_fn()
        W0 = np.array(champ.W, copy=True)
        row = {"seed": s, "intact_median_ref": ref_r["intact"]["intact_median"], "blind_median_ref": ref_r["blind"]["intact_median"]}
        for nom, cls in (("except_identity", BlindExceptIdentityFrozenMamba), ("identity_zeroed", IdentityZeroedFrozenMamba)):
            m = map_fn(worlds=[world], seed=s, K=k, subject=champ, batch_model_cls=cls, paired_band=True, noop_control=True, **regime)[world]
            row[nom] = dict(m, w_ok=bool(np.array_equal(W0, np.asarray(champ.W)) and m.get("policy") == cls.__name__
                                         and m.get("reference") == "paired_band"))
        rows.append(row)
        if verbose:
            i = row["intact_median_ref"]
            print(f"  seed {s} : intact(ref)={i:6.1f} aveugle(ref)={row['blind_median_ref']:6.1f} | "
                  f"sans-entree-sauf-identite={row['except_identity']['intact_median']:6.1f} (r {row['except_identity']['intact_median']/i:.3f}, "
                  f"noop {row['except_identity']['noop']['ratio']:.3f}) | identite-coupee={row['identity_zeroed']['intact_median']:6.1f} "
                  f"(r {row['identity_zeroed']['intact_median']/i:.3f}, noop {row['identity_zeroed']['noop']['ratio']:.3f})", flush=True)
    return rows, decomp_verdict(rows)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    from src.paths import results_file
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import stamp, verify
    if "--decomp" in argv:
        return main_decomp()
    ter = "--ter" in argv
    prereg = "S2-BLIND-CHAMPION-ter" if ter else PREREG
    seeds = SEEDS_TER if ter else SEEDS
    rule = verify(prereg)
    out_path = str(results_file("s2_blind_champion_ter.json" if ter else "s2_blind_champion_bis.json"))
    design = declare_design(
        question=rule["question"],
        replication_unit="seed de monde (K=12 ères appariées par seed ; les deux bras partagent seed, génome, corps)",
        n_independent=len(seeds),
        links={"survie_intact": "measured", "survie_aveugle_entree": "measured", "noop_par_bras": "measured",
               "controle_ii_within_aveugle": "measured", "genome_identique": "measured"},
        cost_estimate=rule["cout"],
        control_family=assert_control_family(cells=len(seeds), alpha_family=0.05))
    t0 = time.time()
    with hold("kuzu", owner="s2-blind-champion-" + ("ter" if ter else "bis"), ttl_s=5400):
        rows, verdict = run_blind_champion_bis(seeds=seeds, verdict_fn=blind_champion_verdict_ter if ter else blind_champion_verdict)
    out = {"_design": design, "_regime": {"world": WORLD, **REGIME, "K": K, "seeds": list(seeds), "floor": FLOOR,
                                            "clause_iii": "ter : ecarte si les DEUX bras <= plancher" if ter else "bis : ecarte si intact < plancher",
                                            "blinding": "entree (obs = 0)", "learner": "legacy credit gele, NTM non gele",
                                            "reference": "paired_band", "noop_control": True},
           "rows": rows, "verdict": verdict, "_cout_s": time.time() - t0}
    json.dump(stamp(out, prereg), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(verdict, indent=1, ensure_ascii=False))
    print("->", out_path)
    return out


def main_decomp():
    from src.paths import results_file
    from tools.experiment_preflight import assert_control_family, declare_design
    from tools.jobs.run import hold
    from tools.preregister import stamp, verify
    prereg = "S2-BLIND-CHAMPION-DECOMP-R1"
    rule = verify(prereg)
    verify("S2-BLIND-CHAMPION-ter")                       # la référence importée n'a pas été retouchée
    out_path = str(results_file("s2_blind_champion_decomp_r1.json"))
    design = declare_design(
        question=rule["question"],
        replication_unit="seed de monde (mêmes 7 seeds que le -ter ; intact et aveugle total IMPORTÉS du -ter, appariés par seed)",
        n_independent=len(SEEDS_TER),
        links={"survie_sans_entree_sauf_identite": "measured", "survie_identite_coupee": "measured",
               "survie_intact_et_aveugle_ref": "measured", "noop_par_bras": "measured"},
        cost_estimate=rule["cout"],
        control_family=assert_control_family(cells=2 * len(SEEDS_TER), alpha_family=0.05))
    t0 = time.time()
    with hold("kuzu", owner="s2-blind-champion-decomp", ttl_s=5400):
        rows, verdict = run_decomp()
    out = {"_design": design, "_regime": {"world": WORLD, **REGIME, "K": K, "seeds": list(SEEDS_TER), "floor": FLOOR,
                                            "bras": {"except_identity": "x[:, :max_N-max_O] = 0 (46 entrees coupees, 18 identites gardees)",
                                                     "identity_zeroed": "x[:, max_N-max_O:max_I] = 0 (18 identites coupees, 46 entrees gardees)"},
                                            "reference": "paired_band", "noop_control": True, "learner": "legacy credit gele, NTM non gele",
                                            "references_importees": "-ter (intact et aveugle total), lu via results_file(s2_blind_champion_ter.json)"},
           "rows": rows, "verdict": verdict, "_cout_s": time.time() - t0}
    json.dump(stamp(out, prereg), open(out_path, "w", encoding="utf-8"), indent=1)
    print(json.dumps(verdict, indent=1, ensure_ascii=False))
    print("->", out_path)
    return out


if __name__ == "__main__":
    main()
