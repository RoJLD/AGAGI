"""Puissance d'EDR 083 : R co-evolutions independantes -> ecart FIABLE-BRUITE moyen +/- SE."""
import time
import numpy as np
from src.environments.config import WorldConfig
from src.seed_ai.mutation import MutationConfig
from src.seed_ai.referential_head import new_head, train_population
from src.graph_rag.async_logger import logger as al
from tools.coevolve_language import coevolve, _measure
from tools.progress import Progress

def main(R=4, gens=12, num_agents=24, K=4, n_eval=6):
    al.start()
    for _ in range(50):
        if al.get_db(): break
        time.sleep(0.1)
    cfg = WorldConfig(); mc = MutationConfig(weight_init_std=2.0)
    diffs = []
    prog = Progress(R, label="co-evolutions")
    for r in range(R):
        rng = np.random.RandomState(r)
        heads = [new_head(M=3, V=4, H=12, rng=rng) for _ in range(num_agents)]
        train_population(heads, steps=5000, seed=r)
        cf = coevolve(cfg, mc, True, heads, gens, num_agents, K, Progress(gens, label=f"FIABLE r{r+1}/{R}"))
        cb = coevolve(cfg, mc, False, None, gens, num_agents, K, Progress(gens, label=f"BRUITE r{r+1}/{R}"))
        mf = np.mean(_measure(cfg, cf, mc, True, heads, num_agents, n_eval))
        mb = np.mean(_measure(cfg, cb, mc, False, None, num_agents, n_eval))
        diffs.append(mf - mb)
        prog.update()
    d = np.array(diffs, dtype=float)
    se = d.std(ddof=1)/np.sqrt(len(d)) if len(d) > 1 else float('inf')
    print(f"\n=== CO-EVOLUTION POWERED : ecart FIABLE-BRUITE Mammouths, R={R} ===")
    print(f"  par run : {[round(x,1) for x in diffs]}")
    print(f"  moyenne = {d.mean():+.2f} +/- {se:.2f} (SE) ; FIABLE>BRUITE dans {np.mean(d>0)*100:.0f}% des runs")
    print("=== VERDICT ===")
    if d.mean() > 2*se and d.mean() > 0:
        print(f"  -> langage FONCTIONNEL EMERGE sous selection : +{d.mean():.1f} Mammouths (>2 SE). Reponse a 053/082.")
    elif d.mean() > 0:
        print(f"  -> tendance ({d.mean():+.1f}) encore sous 2 SE ; R plus grand ou survie plus longue.")
    else:
        print(f"  -> pas d'avantage ({d.mean():+.1f}) : co-evoluer ne suffit pas ici.")
    al.stop()

if __name__ == "__main__":
    main()
