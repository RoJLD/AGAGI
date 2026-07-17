"""Le langage PAIE-t-il ? (fil langage / porte G3, LANG-006 — clôt la question du bénéfice, en proxy)

Mon axe langage (LANG-001→005) a établi la CAPACITÉ (signalisation émerge, compositionnelle, partagée). Il
reste le PAYOFF : communiquer confère-t-il un avantage de survie, et QUAND ? On réutilise la méthodo causale
de S2-001 : ablater le CANAL de communication within-subject (décorréler les messages) ; si la survie
s'effondre, le langage est causalement porteur.

Mondes à VÉRITÉ-TERRAIN :
- COORDINATION-DEMANDING : l'action requise a*(t) dépend d'une cible t PRIVÉE au locuteur (l'auditeur ne voit
  pas t) -> résoudre l'asymétrie d'info EXIGE le canal. Vérité-terrain : le langage doit payer.
- NO-COORDINATION (trivial) : a* est FIXE quel que soit t -> l'auditeur agit sans info. Le langage NE doit PAS
  payer (le canal est superflu).

Locuteur : t -> message ; Auditeur : message -> action. Ajustés CONJOINTEMENT pour maximiser la survie (canal
intact) -> le protocole n'émerge QUE s'il paie. Marqueurs : survie(canal intact) vs survie(canal RANDOMISÉ,
ablation) vs survie(SANS canal) ; corroborant = MI(message ; action) (le canal est-il utilisé ?).

Usage : python tools/language_payoff_probe.py   (env: LPP_SEEDS, LPP_K, LPP_TICKS)
"""
import os
import sys
import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _oh(i, n):
    v = np.zeros(n)
    v[i] = 1.0
    return v


def survive(demanding, Ws, Wr, channel, K, M, rng, ticks=200, E0=10.0, gain=1.0, metab=0.5):
    """Une vie coopérative. Chaque tick : cible t (privée au locuteur), action requise a*=t (demanding) ou 0
    (trivial). Locuteur émet m ; l'auditeur agit sur le canal. Récompense si action==a*. Survie = ticks avant
    énergie<=0. channel : 'true' (intact) / 'random' (ablation : message décorrélé) / 'none' (aucun canal)."""
    E = E0
    for _ in range(ticks):
        t = rng.randint(K)
        astar = t if demanding else 0
        m = int(np.argmax(Ws @ _oh(t, K)))
        if channel == "true":
            a = int(np.argmax(Wr @ _oh(m, M)))
        elif channel == "random":
            a = int(np.argmax(Wr @ _oh(rng.randint(M), M)))     # ablation : message bidon
        else:
            a = int(np.argmax(Wr @ np.zeros(M)))                # sans canal : biais seul
        E += (gain if a == astar else 0.0) - metab
        if E <= 0:
            return _
    return ticks


def _score(demanding, Ws, Wr, K, M, seed, episodes, ticks):
    return np.mean([survive(demanding, Ws, Wr, "true", K, M, np.random.RandomState(seed + 200 + e), ticks)
                    for e in range(episodes)])


def fit_protocol(demanding, K, M, seed, iters=500, episodes=6, ticks=200):
    """Ajuste locuteur (Ws : M×K) + auditeur (Wr : K×M) CONJOINTEMENT par hill-climb pour maximiser la survie
    avec canal intact. Un protocole n'émerge que s'il PAIE (sinon le bruit ne se stabilise pas)."""
    rng = np.random.RandomState(seed)
    Ws = np.zeros((M, K))
    Wr = np.zeros((K, M))
    best = _score(demanding, Ws, Wr, K, M, seed, episodes, ticks)
    step = 0.7
    for i in range(iters):
        Wsc = Ws + step * rng.randn(M, K)
        Wrc = Wr + step * rng.randn(K, M)
        sc = _score(demanding, Wsc, Wrc, K, M, seed, episodes, ticks)
        if sc > best:
            Ws, Wr, best = Wsc, Wrc, sc
        elif i % 70 == 69:
            step *= 0.85
    return Ws, Wr


def mi_message_action(demanding, Ws, Wr, K, M, seed, n=3000):
    """MI(message ; action) sur des ticks à canal intact : le canal est-il UTILISÉ ? (0 = auditeur ignore m)."""
    rng = np.random.RandomState(seed + 900)
    c = np.zeros((M, K))
    for _ in range(n):
        t = rng.randint(K)
        m = int(np.argmax(Ws @ _oh(t, K)))
        a = int(np.argmax(Wr @ _oh(m, M)))
        c[m, a] += 1
    p = c / c.sum()
    pm = p.sum(1, keepdims=True)
    pa = p.sum(0, keepdims=True)
    nz = p > 0
    return float(np.sum(p[nz] * np.log(p[nz] / (pm @ pa)[nz] + 1e-12)))


def run_world(demanding, K, seed, n_eval=40, ticks=200):
    M = K
    Ws, Wr = fit_protocol(demanding, K, M, seed, ticks=ticks)
    ev = np.random.RandomState(seed + 500)

    def med(channel):
        return float(np.median([survive(demanding, Ws, Wr, channel, K, M,
                                         np.random.RandomState(ev.randint(1 << 30)), ticks)
                                for _ in range(n_eval)]))
    return {
        "surv_true": med("true"),
        "surv_ablated": med("random"),
        "surv_nocomm": med("none"),
        "mi": mi_message_action(demanding, Ws, Wr, K, M, seed),
    }


def main():
    import statistics
    seeds = list(range(int(os.environ.get("LPP_SEEDS", "8"))))
    K = int(os.environ.get("LPP_K", "4"))
    ticks = int(os.environ.get("LPP_TICKS", "200"))

    print(f"K={K} ticks={ticks} seeds={len(seeds)} (survie médiane ; cap={ticks})")
    print(f"{'monde':22s} {'canal':>7s} {'ablé':>6s} {'sans':>6s} | {'MI(m;a)':>8s} | {'PAIE(×)':>8s}")
    summary = {}
    for demanding, name in ((True, "COORDINATION-DEMAND"), (False, "NO-COORDINATION")):
        rows = [run_world(demanding, K, s, ticks=ticks) for s in seeds]
        st = statistics.median(r["surv_true"] for r in rows)
        sa = statistics.median(r["surv_ablated"] for r in rows)
        sn = statistics.median(r["surv_nocomm"] for r in rows)
        mi = statistics.median(r["mi"] for r in rows)
        pays = st / max(sa, 1e-9)
        summary[name] = (pays, mi)
        print(f"{name:22s} {st:7.1f} {sa:6.1f} {sn:6.1f} | {mi:8.3f} | {pays:7.1f}x")

    pays_dem, mi_dem = summary["COORDINATION-DEMAND"]
    pays_triv, mi_triv = summary["NO-COORDINATION"]
    # langage PAIE = l'ablation du canal effondre la survie SEULEMENT quand la coordination est exigée
    correct = pays_dem > 1.5 and pays_triv < 1.3 and mi_dem > 0.3 and mi_triv < 0.15
    verdict = ("LANGUAGE_PAYS_IFF_TASK_DEMANDS_COORDINATION" if correct else "LANGUAGE_PAYOFF_UNCLEAR")
    print(f"VERDICT={verdict} : ablation du canal -> demand {pays_dem:.1f}x (PAIE) / trivial {pays_triv:.1f}x "
          f"(ne paie pas) ; MI(m;a) demand {mi_dem:.2f} vs trivial {mi_triv:.2f} (canal utilisé SSI il paie) "
          f"-> le langage paie causalement quand la tâche exige de résoudre une asymétrie d'info")


if __name__ == "__main__":
    main()
