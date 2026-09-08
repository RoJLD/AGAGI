"""Mesure d'ARETE language->memory (3e arete du graphe AGI-Taxonomy) -- P2.14b.

Verifie la regle scellee LANG-MEMORY-EDGE AVANT toute lecture, puis mesure les DEUX bras par seed
(learned = bras principal ; present = SPECIFICITY_CONTROL, cle re-montree -> ablation attendue
inerte) au point-reference etabli par le balayage S1. RESUMABLE : chaque (bras, seed) persiste dans
results/lang_memory_edge.json ; relancer jusqu'a RESTE=0 -- la LECTURE (verdicts, garde d'alias,
bloc d'arete) ne s'execute que grille complete.

L'agregation replique VERBATIM run_language_memory_demand_probe (floor=1/K, ceiling=1.0, tol=0.05,
alias_guard_verdict sur CONTROL) : meme instrument calibre, seulement decoupe pour la resumabilite.

    PYTHONPATH=. python -u tools/lang_memory_edge_run.py     # relancer jusqu'a RESTE=0
"""
import json
import os
import sys
import time

sys.path.insert(0, '.')
import numpy as np
import torch

torch.set_num_threads(1)
from tools.preregister import verify
from tools.demand_marker import ablation_verdict
from tools.language_memory_demand_probe import _train_and_eval, alias_guard_verdict

SLICE_S = float(os.environ.get("EDGE_SLICE_S", "500"))
# -bis (2026-09-02) : la regle est parametrable (EDGE_RULE) et chaque regle ecrit dans SON fichier --
# la premiere mesure (EDR-LANG-MEMORY-EDGE, controle sature) reste intacte, jamais ecrasee.
RULE_NAME = os.environ.get("EDGE_RULE", "LANG-MEMORY-EDGE")
_suffix = RULE_NAME.replace("LANG-MEMORY-EDGE", "").replace("-", "_").lower()
OUT = os.path.join("results", f"lang_memory_edge{_suffix}.json")

rule = verify(RULE_NAME)
pt = rule["point_de_fonctionnement"]
LR, EP, D, K, N_AGENTS = pt["lr"], pt["episodes"], pt["D"], pt["K"], pt["n_agents"]
CTE = int(pt.get("control_train_every", 1))     # de-saturation -bis (1 = comportement d'origine)
CIN = float(pt.get("control_input_noise", 0.0))  # bruit CONTROL a dose connue (-bis)
SEEDS = list(range(int(rule["n_seeds"])))
print(f"regle SCELLEE verifiee ({RULE_NAME}) | lr={LR} ep={EP} D={D} K={K} "
      f"cte={CTE} n={len(SEEDS)} seeds -> {OUT}")

# ---- GARDE E23 (porte 11) : la FAMILLE de controles est DECLAREE, avant toute mesure -------------
# COMBIEN de cellules ? TROIS, chacune evaluee UNE SEULE FOIS, sur des medianes deja AGREGEES sur les
# {n_seeds} seeds -- jamais une bande par seed. Elles sont toutes les trois dans le bloc LECTURE plus
# bas, et ce sont exactement les trois conjonctions NON-DV de la ligne `ok = (...)` :
#   (1) garde CALIB-ALIAS sur le bras CONTROL feedforward   -> `guard = alias_guard_verdict(...)`
#   (2) bras PRESENT = SPECIFICITY_CONTROL (cle re-montree) -> `present = ablation_verdict(pi, pa)`
#   (3) barre d'EMERGENCE du point-reference                -> `coord_intact >= bar`
# Le bras PRINCIPAL (`lang`) est la DV primaire scellee, pas un controle : il n'entre pas dans la famille.
from tools.experiment_preflight import assert_control_family, declare_design   # noqa: E402

FAMILLE_CELLULES = 3
_famille = assert_control_family(
    cells=FAMILLE_CELLULES, alpha_family=0.05, method="none",
    reason="Multiplicite SANS OBJET ici, et la raison est structurelle : les 3 cellules sont des "
           "DECISIONS DETERMINISTES prises sur des medianes deja agregees sur les seeds (bandes de "
           "`ablation_verdict` / `alias_guard_verdict`, comparaison `coord_intact >= emergence_bar`). "
           "AUCUN seuil de test statistique n'est applique, donc il n'y a pas d'alpha a corriger et "
           "une Bonferroni serait DECORATIVE. Surtout, AUCUNE bande n'est appliquee PAR SEED -- c'est "
           "exactement la forme qui donnait 0.216 de fausse alarme sur EVO-011 (24 cellules). "
           "`leak_seeds` EST per-seed mais N'ENTRE PAS dans la decision (choix documente dans la "
           "docstring de `alias_guard_verdict`, faute de seuil par seed etalonne) : il est RAPPORTE.")
design = declare_design(
    question=rule["question"],
    replication_unit=f"seed ({len(SEEDS)} seeds scelles ; les {N_AGENTS} agents d'un seed partagent "
                     f"entrainement, optimiseur et tirages -- ils ne sont PAS des replicats)",
    n_independent=len(SEEDS),
    links={"H-reset entre encode et use -> chute du bras PRINCIPAL (learned)": "measured",
           "MEME H-reset -> bras CONTROL feedforward inerte (chirurgie)": "measured",
           "cle RE-MONTREE au tick d'usage (present) -> ablation inerte (specificite)": "measured"},
    control_family=_famille,
    cost_estimate=rule.get("cout"))
print(f"[design] unite = {design['replication_unit']} | famille = {_famille['cells']} cellules, "
      f"method={_famille['method']} (raison publiee dans le design)")
print()
os.makedirs("results", exist_ok=True)
db = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}

t0, reste = time.time(), []
for mode in ("learned", "present"):
    for s in SEEDS:
        k = f"{mode}|seed={s}"
        if k in db:
            continue
        if time.time() - t0 > SLICE_S:
            reste.append(k)
            continue
        li, la, ci, ca = _train_and_eval(seed=s, episodes=EP, n_agents=N_AGENTS, K=K, D=D, lr=LR,
                                         memory_mode=mode, control_mode="feedforward", bilinear=True, control_train_every=CTE, control_input_noise=CIN)
        db[k] = {"lang_i": li, "lang_a": la, "ctrl_i": ci, "ctrl_a": ca}
        json.dump(db, open(OUT, "w", encoding="utf-8"), indent=1)
        print(f"  {k}: lang_i={li:.3f} lang_a={la:.3f} ctrl_i={ci:.3f} ctrl_a={ca:.3f} "
              f"[{time.time()-t0:.0f}s]")

if reste:
    print(f"\nRESTE={len(reste)} {reste[:4]}... -> RELANCER (aucune lecture sur grille partielle)")
    raise SystemExit(0)

# ---------- LECTURE (grille complete ; ordre scelle) ----------
def bras(mode, champ_i, champ_a):
    return ([db[f"{mode}|seed={s}"][champ_i] for s in SEEDS],
            [db[f"{mode}|seed={s}"][champ_a] for s in SEEDS])

li, la = bras("learned", "lang_i", "lang_a")
ci, ca = bras("learned", "ctrl_i", "ctrl_a")
pi, pa = bras("present", "lang_i", "lang_a")
floor = 1.0 / K

lang = ablation_verdict(li, la, intervention_verified=True, floor=floor, ceiling=1.0)
x_response = abs(float(np.median(li)) - float(np.median(la)))
guard = alias_guard_verdict(ci, ca, x_response, floor=floor, ceiling=1.0, tol=0.05)
present = ablation_verdict(pi, pa, intervention_verified=True, floor=floor, ceiling=1.0)

coord_intact = float(np.median(li))
bar = float(rule["emergence_bar"])
print("\n=== LANG-MEMORY-EDGE ===")
print(f"bras PRINCIPAL  : {lang['verdict']} ratio={lang['ratio']:.2f} "
      f"(intact med={coord_intact:.3f}, able med={float(np.median(la)):.3f}, n={lang['n']})")
print(f"bras PRESENT    : {present['verdict']} ratio={present['ratio']:.2f} "
      f"(intact med={float(np.median(pi)):.3f}, able med={float(np.median(pa)):.3f})")
print(f"garde ALIAS     : {guard['alias_verdict']} (functional_aliasing={guard['functional_aliasing']}, "
      f"leakage={guard['leakage']:.3f}, leak_seeds={guard['leak_seeds']})")
print(f"barre EMERGENCE : coord_intact={coord_intact:.3f} vs emergence_bar={bar} "
      f"-> {'AU-DESSUS' if coord_intact >= bar else 'SOUS LA BARRE'}")

ok = (lang["verdict"] == "X_DEMANDED" and present["verdict"] == "X_DECOY"
      and guard["functional_aliasing"] == "pass" and coord_intact >= bar)
if ok:
    edge = {"capability": "language", "prerequisite": "memory", "strength": "hard",
            "evidence": {"ablation_verdict": "X_DEMANDED", "ratio": round(lang["ratio"], 3),
                          "n": len(SEEDS), "specificity_control": "pass",
                          "functional_aliasing": "pass", "ablation_target": "substrate",
                          "coord_intact": round(coord_intact, 3), "emergence_bar": bar,
                          "record": "docs/EDR/LANG-MEMORY-EDGE_A_COMPLETER.md"}}
    print("\n-> TOUTES les branches scellees positives. Bloc d'arete candidat (record a graver "
          "AVANT insertion dans demands.json ; la porte check_agi_taxonomy verifiera tout) :")
    print(json.dumps(edge, ensure_ascii=False, indent=1))
else:
    print("\n-> au moins une branche scellee NEGATIVE : lire la regle, graver le resultat TEL QUEL "
      "(un negatif se grave au meme titre), AUCUNE arete n'entre dans le graphe.")
