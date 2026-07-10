"""tools/qd_tier_rescue.py — QD sauve-t-il le tier CRAFT mort ? (P3 audit memoire).

Rebranche l'instrument per-type d'EDR 125 (_measure_profile + _tier_fractions) sur les DEUX bras
evolutifs de map_elites_compare : HoF (mono-objectif life_score) vs QD (archive MAP-Elites, niches
diverses). La selection top-5 par life_score DROPPE un genome craft-pur (spears x300 < forager+apex) ;
l'archive QD garde une elite dans la cellule tier=2. Question gelee : QD leve-t-il frac_craft de >=0.10
(=> selection sauve le craft) ou non (=> mur = substrat/atteignabilite, EDR 111) ?

Tooling pur (pas de src/ modifie ; competence_profile/map_elites_compare/map_elites importes).
Usage : python -m tools.qd_tier_rescue
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import numpy as np

from src.environments.config import WorldConfig
from src.seed_ai.harness import Harness, SeedManager
from src.agents.mamba_agent import MambaAgent
from src.seed_ai.map_elites import MapElitesArchive
from src.graph_rag.async_logger import logger as async_logger
from tools.map_elites_compare import _make_cfg, _seed_genome, _reproduce, run_era_pool
from tools.competence_profile import _evolve_champions, _measure_profile, _tier_fractions


def _tier_coverage(archive):
    """Nb de cellules occupees par tier (readout : le craft/apex existe-t-il dans l'archive ?)."""
    tiers = [cell[1] for cell in archive.cells.keys()]
    return {f"cells_tier{t}": sum(1 for x in tiers if x == t) for t in range(4)}


def _verdict_qd_rescue(fracs_hof, fracs_qd):
    """Primaire = frac_craft. CONFIRME si QD leve le craft de >=0.10 ET le sort du plancher (>=0.10) ;
    QD_NUIT si degrade de >=0.10 ; sinon QD_NEUTRE (mur = substrat/atteignabilite, pas selection)."""
    d = fracs_qd["frac_craft"] - fracs_hof["frac_craft"]
    if d >= 0.10 and fracs_qd["frac_craft"] >= 0.10:
        return "QD_RESCUE_CRAFT CONFIRME"
    if d <= -0.10:
        return "QD_NUIT"
    return "QD_NEUTRE"


def _evolve_qd_champions(seed, eras=12, num_agents=30, max_ticks=400, run_era_fn=None):
    """Bras QD : archive MAP-Elites, reproduit depuis niches diverses (sample). Renvoie (champions, archive).
    Mirror de run_lineage_qd (map_elites_compare) mais renvoie les genomes champions + l'archive.
    run_era_fn injectable (defaut run_era_pool) pour les tests."""
    if run_era_fn is None:
        run_era_fn = run_era_pool
    SeedManager(seed).seed_boundary(0)
    cfg = _make_cfg()
    archive = MapElitesArchive()
    genomes = [_seed_genome(i) for i in range(num_agents)]
    for _ in range(eras):
        pool, _m = run_era_fn(cfg, genomes, max_ticks)
        for s, g, st in pool:
            archive.upsert(s, g, st)
        champ = archive.sample(5)
        genomes = _reproduce(champ, num_agents) if champ else [MambaAgent().genome for _ in range(num_agents)]
    return archive.sample(5), archive


def _measure_arm(champs, num_agents, max_ticks):
    """Replique les champions a num_agents et mesure le profil per-tier sur cohorte fixe (benchmark_mode).
    Bras vide -> fractions nulles (_frac_reaching([]) == 0.0)."""
    if not champs:
        return _tier_fractions([])
    reps = (champs * (num_agents // len(champs) + 1))[:num_agents]
    stats = _measure_profile(_make_cfg(), reps, max_ticks=max_ticks, disable_repro=True)
    return _tier_fractions(stats)


def _report_qd_rescue(h, per_seed, R, _return):
    """Table ASCII (HOF forg/craf/apex | QD forg/craf/apex | QD craft/apex cells) + moyenne + Delta + verdict."""
    def _mean(arm, k):
        return float(np.mean([p[arm][k] for p in per_seed]))
    keys = ("frac_forage", "frac_craft", "frac_apex")
    hof = {k: _mean("hof", k) for k in keys}
    qd = {k: _mean("qd", k) for k in keys}
    verdict = _verdict_qd_rescue(hof, qd)
    dcraft = qd["frac_craft"] - hof["frac_craft"]
    # Robustesse (revue finale I1) : nb de seeds ou le CONFIRME tiendrait PER-SEED. Le verdict gele reste
    # sur la MOYENNE ; ce readout evite un faux CONFIRME pilote par une seule graine au plancher (n=3).
    n_confirme_seeds = sum(1 for p in per_seed
                           if (p["qd"]["frac_craft"] - p["hof"]["frac_craft"]) >= 0.10
                           and p["qd"]["frac_craft"] >= 0.10)
    # Borne haute de frac_craft_QD que sample(5) UNIFORME peut delivrer (revue finale C1) : part des
    # cellules tier2 dans l'archive QD. Un NEUTRE avec tier2>0 peut venir de la dilution d'echantillonnage
    # (craft present mais noye), pas seulement de la non-retention.
    cells_tier2 = float(np.mean([p["coverage"]["cells_tier2"] for p in per_seed]))
    coverage_tot = float(np.mean([sum(p["coverage"].values()) for p in per_seed]))
    craft_cell_share = cells_tier2 / coverage_tot if coverage_tot > 0 else 0.0
    print("\n=== QD sauve-t-il le tier CRAFT ? (cohorte fixe, 2 bras apparies) ===")
    print("  seed | HOF  forg  craf  apex | QD   forg  craf  apex | QDcells t2/t3")
    for p in per_seed:
        hf, qf, cv = p["hof"], p["qd"], p["coverage"]
        print(f"  {p['seed']:4d} |      {hf['frac_forage']:5.3f} {hf['frac_craft']:5.3f} {hf['frac_apex']:5.3f} "
              f"|      {qf['frac_forage']:5.3f} {qf['frac_craft']:5.3f} {qf['frac_apex']:5.3f} "
              f"|   {cv['cells_tier2']:2d}/{cv['cells_tier3']:2d}")
    print(f"  MOYEN|      {hof['frac_forage']:5.3f} {hof['frac_craft']:5.3f} {hof['frac_apex']:5.3f} "
          f"|      {qd['frac_forage']:5.3f} {qd['frac_craft']:5.3f} {qd['frac_apex']:5.3f}")
    print(f"  d(craft) = {dcraft:+.3f}")
    print(f"  seeds CONFIRME per-seed = {n_confirme_seeds}/{len(per_seed)}")
    print(f"  QD craft-cell share (borne haute sample) = {craft_cell_share:.3f} "
          f"(cells_tier2 {cells_tier2:.2f} / coverage {coverage_tot:.2f})")
    print("=== VERDICT (QD sauve le craft ?) ===")
    print(f"  -> {verdict}")
    h.save({"R": R, "verdict": verdict, "d_craft": dcraft, "n_confirme_seeds": n_confirme_seeds,
            "craft_cell_share": craft_cell_share, "mean_hof": hof, "mean_qd": qd, "per_seed": per_seed})
    if _return:
        return {"verdict": verdict, "d_craft": dcraft, "n_confirme_seeds": n_confirme_seeds,
                "craft_cell_share": craft_cell_share, "mean_hof": hof, "mean_qd": qd,
                "per_seed": per_seed, "R": R}


def main_qd_tier_rescue(R=3, eras=12, num_agents=30, max_ticks=400, seed=1260, _return=False):
    """Pour chaque seed base+r : evolue 2 bras (HoF life_score / QD niches), mesure le profil per-tier de
    chacun sur cohorte fixe, agrege R seeds, verdict QD-sauve-craft."""
    base = seed
    async_logger.start()
    try:
        per_seed = []
        for r in range(R):
            s = base + r
            hof_champs = _evolve_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            qd_champs, archive = _evolve_qd_champions(s, eras=eras, num_agents=num_agents, max_ticks=max_ticks)
            per_seed.append({
                "seed": int(s),
                "hof": _measure_arm(hof_champs, num_agents, max_ticks),
                "qd": _measure_arm(qd_champs, num_agents, max_ticks),
                "coverage": _tier_coverage(archive),
            })
    finally:
        async_logger.stop()
    h = Harness(seed=base, name="qd_tier_rescue", with_db=False, config=WorldConfig())
    return _report_qd_rescue(h, per_seed, R, _return)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main_qd_tier_rescue()
