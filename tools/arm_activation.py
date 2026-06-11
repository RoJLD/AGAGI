"""
tools/arm_activation.py — Armer le #8 sur le kind ACTIVATION (EDR 066).

Le #8 améliore l'AGENT (pas que le monde) : le LLM local propose des fonctions d'ACTIVATION, la
**sandbox EDR 035** les valide (gate AST {numpy,math} + subprocess isolé), et on mesure si elles
BATTENT tanh sur le banc mémoire (rappel de K bits — mem_nas, auto-contenu). Le #8 lit les scores
passés et itère. Cage = la sandbox EDR 035 (conçue pour du code-maths ; conteneur OS = défense en
profondeur pour un LLM non-fiable).

Usage : python -m tools.arm_activation   (LLM local requis ; pas de DB)
"""
import json
import re

import numpy as np

from src.metaprog.secure_sandbox import validate_code, run_sandboxed, first_def_name
from src.metaprog.llm_proposer_fn import local_llm_fn
from src.seed_ai.mutation import MutationConfig, apply_mutations
from tools.mem_nas import fresh_genome, _select, I_DIM, O_DIM

ACT_TEST = ("import numpy as np\n_r = {fn}(np.array([-2.0, -0.5, 0.0, 0.5, 2.0]))\n"
            "assert _r.shape == (5,)\n"
            "assert not np.isnan(_r).any() and not np.isinf(_r).any()\nprint('ok')\n")


def build_activation_prompt(context: dict) -> str:
    past = (context or {}).get("recent", [])
    lines = [
        "Tu ameliores un reseau de neurones RECURRENT (Liquid Mamba). Propose UNE fonction",
        "d'ACTIVATION f(x) (numpy, vectorisee) pour remplacer tanh dans : H = (1-dt)*H + dt*f(excitation).",
        "Objectif : MEILLEURE MEMOIRE recurrente (retenir des bits sur un delai). Bornee de preference.",
        "Activations deja essayees et leur score (accuracy memoire ; tanh = baseline) :",
    ]
    for p in past:
        lines.append(f"  - {p['name']}: {p['score']}")
    lines += [
        "Contraintes STRICTES : numpy/math uniquement, aucun autre import, fonction PURE f(x)->x.",
        'Reponds UNIQUEMENT en JSON : {"name": "...", "code": "import numpy as np\\ndef f(x):\\n    return ..."}',
    ]
    return "\n".join(lines)


def compile_activation(code: str):
    """Valide (gate AST EDR 035) + teste (subprocess isolé) + compile en-process. -> (fn|None, raison)."""
    ok, reason = validate_code(code)
    if not ok:
        return None, f"AST gate: {reason}"
    name = first_def_name(code)
    if name is None:
        return None, "aucune fonction"
    ok2, reason2 = run_sandboxed(code, ACT_TEST.format(fn=name))
    if not ok2:
        return None, f"sandbox: {reason2}"
    ns = {}
    exec(code, ns)                                   # AST-validé (numpy/math seulement) -> sûr
    return ns.get(name), "ok"


def _forward_act(genome, obs, H, act):
    """Un pas récurrent (= recurrent_forward) mais avec une activation PLUGGABLE au lieu de tanh."""
    I, N = genome.num_inputs, genome.num_nodes
    W = genome.W
    dt = (1.0 / (1.0 + np.exp(-np.clip(np.diagonal(W), -10, 10)))).reshape(1, N)
    Wnd = W.copy()
    np.fill_diagonal(Wnd, 0.0)
    H = H.copy()
    H[:, :I] = obs
    return (1.0 - dt) * H + dt * act(np.dot(H, Wnd))


def eval_genome_act(genome, act, K=6, D=3, trials=24):
    N, O = genome.num_nodes, genome.num_outputs
    accs = []
    for _ in range(trials):
        bits = np.random.choice([-1.0, 1.0], size=K).astype(np.float32)
        H = np.zeros((1, N), dtype=np.float32)
        obs = np.zeros((1, I_DIM), dtype=np.float32)
        obs[0, :K] = bits
        H = _forward_act(genome, obs, H, act)
        for _ in range(D):
            H = _forward_act(genome, np.zeros((1, I_DIM), dtype=np.float32), H, act)
        go = np.zeros((1, I_DIM), dtype=np.float32)
        go[0, K] = 1.0
        H = _forward_act(genome, go, H, act)
        recalled = np.sign(H[0, -O:][:K])
        accs.append(float(np.mean(recalled == bits)))
    return float(np.mean(accs))


def evolve_act(act, seed, generations=25, pop=24, hidden0=6, K=6, D=3, add_node_rate=0.3):
    np.random.seed(seed)
    mc = MutationConfig()
    mc.add_node_rate = add_node_rate
    genomes = [fresh_genome(I_DIM + O_DIM + hidden0) for _ in range(pop)]
    n_elite = max(2, pop // 4)
    best = 0.0
    for _ in range(generations):
        scores = [eval_genome_act(g, act, K, D) for g in genomes]
        best = max(best, max(scores))
        elite = _select(genomes, scores, n_elite, True)
        children = []
        while len(children) < pop - len(elite):
            children.append(apply_mutations(elite[np.random.randint(len(elite))], mc))
        genomes = elite + children
    return best


def main(n_iters=5, seeds=(0, 1), llm=None):
    llm = llm or local_llm_fn()
    base = float(np.mean([evolve_act(np.tanh, s) for s in seeds]))
    print(f"ARM-ACTIVATION (#8 sur l'agent) : baseline tanh acc={base:.3f}")
    context = {"recent": [{"name": "tanh", "score": round(base, 3)}]}
    results = [("tanh", base)]
    for i in range(n_iters):
        try:
            resp = llm(build_activation_prompt(context))
            d = json.loads(re.search(r"\{.*\}", resp, re.DOTALL).group(0))
            name, code = str(d.get("name", f"act{i}")), str(d.get("code", ""))
        except Exception as e:
            print(f"  iter {i}: reponse illisible ({type(e).__name__})")
            continue
        fn, reason = compile_activation(code)
        if fn is None:
            print(f"  '{name}': REJETE par la cage ({reason})")
            context["recent"].append({"name": name, "score": f"rejete: {reason[:40]}"})
            continue
        try:
            acc = float(np.mean([evolve_act(fn, s) for s in seeds]))
        except Exception as e:
            print(f"  '{name}': crash eval ({type(e).__name__})")
            context["recent"].append({"name": name, "score": "crash"})
            continue
        flag = "  <-- BAT tanh" if acc > base + 0.02 else ""
        print(f"  '{name}': acc={acc:.3f}{flag}")
        context["recent"].append({"name": name, "score": round(acc, 3)})
        results.append((name, acc))

    results.sort(key=lambda r: r[1], reverse=True)
    print("\n=== CLASSEMENT (accuracy memoire) ===")
    for n, a in results:
        print(f"  {n:28s}: {a:.3f}")
    bn, ba = results[0]
    if bn != "tanh" and ba > base + 0.02:
        print(f"  -> le #8 a TROUVE une activation qui BAT tanh : '{bn}' (+{ba - base:.3f}) ! Il ameliore l'AGENT.")
    else:
        print("  -> aucune activation ne bat tanh nettement (tanh reste fort sur ce banc).")


if __name__ == "__main__":
    main()
