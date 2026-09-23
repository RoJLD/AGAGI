"""
tools/harness/seal_r1.py — Scelle HARNESS-R1-bis à partir du SMOKE (jamais de chiffre importé d'un autre régime,
E8). HARNESS-R1 (sans -bis) reste sur disque, INTACT : une pré-inscription ne se corrige pas, cf.
`tools/preregister.py`. Usage : PYTHONIOENCODING=utf-8 python -m tools.harness.seal_r1 [chemin du smoke]

Fix round 1/5 (revue contrôleur, tâche 10) — la règle R1 n'avait encore LU aucune cellule (aucun run n'avait
consommé la règle scellée) : la voie légitime pour corriger huit défauts Important, dont quatre touchant le
CONTENU scellé, est un `-bis` scellé AVANT toute cellule, citant R1 et la raison (`remplace`/`raison_bis`),
précédents `S6-FALLBACK-RATE-bis`, `S2-REWARD-ABLATION-bis`.

Défauts corrigés ici (numérotés comme dans la revue) :
(1) `budget_s` PAR CELLULE (`3.0 * unit_s[cellule] * 12 * 5`, l'unité MESURÉE désormais comparable —
    cf. fix (2) de `smoke_r1.py`), plus `budget_family_s` = somme. `project_cost(..., safety=3.0)`
    appliquerait ENCORE cette marge : ce nombre est déjà la projection avec marge, jamais à la
    remultiplier.
(4) chaque cellule porte `issues = {"attendue": ..., "sinon": ...}` (E2 : lire l'issue NÉGATIVE, pas
    seulement la positive espérée) ; `discrimination` porte une phrase DISTINCTE par branche (ce qu'elle
    signifie pour CETTE famille), la boilerplate d'ordre restant unique dans `regle_de_lecture_continue`.
(5) `control_family` PAR CELLULE (`n_ablations * len(sweep)`, la même formule que
    `run_harness_cell` calculera lui-même) : A=6, A'=6, B=8 — total **20** au niveau famille (R1
    déclarait `cells=6` pour la famille ENTIÈRE, une sous-déclaration E23).
(6) `n_agents=16`, `eval_batches=40` scellés dans chaque cellule, à côté d'`episodes`.
(8)/(9) le sweep de chaque cellule est vérifié égal à `ConnectomeLearner(lrs=..., n_classes=...).sweep()`
    (test) ; le plafond de l'incapable importe `PLAIN_COMPOSITION_CEILING`/`_PROVENANCE` de
    `tools.plain_substrate_ceiling` (comme `CompositionTask`), jamais retapé en dur.
(10) le second lr de B se choisit par médiane décroissante puis, à égalité, par proximité à
    `sweep0_lr` (lu d'une seule source, `B_SWEEP0_LR`, jamais un `0.002` répété en littéral).
(12) `cout` dit explicitement que le temps mur est un MAJORANT mesuré sous charge (E12).
(13) la provenance ne peut pas vivre DANS le sceau qu'elle décrit (circularité) : `main()` l'attache
    plutôt au JSON du SMOKE via `stamp(` (la ressource que ce scellement vient de consommer), APRÈS
    `preregister(`. ⚠️ PAS un fichier `docs/preregistrations/HARNESS-R1-bis.provenance.json` : ce
    répertoire est scanné ENTIER par `check_preregistration_applied.py` (`_familles()` lit CHAQUE
    `.json` comme un payload `{"name","rule","seal"}`) — un fichier de provenance y a un champ `rule`
    qui est une CHAÎNE, pas un dict, et fait planter le cliquet (`AttributeError` mesuré en écrivant
    cette tâche). `stamp()` suit la discipline lecture-var-puis-écriture de CLAUDE.md (jamais un `"w"`
    avant d'avoir fini de lire) avec une assertion de taille avant d'écrire (E22 : une réécriture ne
    doit jamais RÉDUIRE l'artefact qu'elle tamponne).
(14) le champ `warning` de `declare_design` (texte d'aide au lecteur humain, pas une donnée scellable)
    est retiré du dict `design` avant scellement ; le reste (links, control_family, n_independent,
    question, cost_estimate) est conservé.

Fix round 2/5 (re-revue contrôleur, tâche 10) — SANS re-sceller (le `-bis` sur disque est propre ;
`preregister` reste IDEMPOTENT à contenu identique -- un re-run de ce module rend le MÊME chemin, sans
`PreregistrationConflict`, tant que le smoke lu ne change pas) :
(1) fallback non adossé : la prédiction ACQUIRED de A' avait un `else` qui scellait la CLAIM SANS
    référence mesurée si `Aprime_ref` manquait -- motif (a) du dépôt (entrée absente -> affirmation de
    fond). `build_rule_r1` REFUSE désormais (`ValueError`) un smoke sans `Aprime_ref`, sans `noise` pour
    les trois cellules (A/Aprime/B), ou sans `unit_s` (bras full_eval) pour les trois cellules -- AUCUNE
    prédiction ne se scelle plus sans sa mesure. Les branches `if ... is not None else ...` sont
    retirées : la valeur est désormais TOUJOURS présente (garde en tête de fonction) ou la fonction a
    déjà levé.
(2) entrée périmée par défaut : `main()` sans argument lisait `harness_r1_smoke_0.json`, le smoke DE R1
    (sans `Aprime_ref`) -- un re-run sans argument aurait construit une règle DÉGRADÉE avant d'échouer
    sur le conflit de contenu. Le défaut est désormais `<SMOKE_NAME>_<SMOKE_SEED>_rerun.json` (le
    fichier réellement rendu par le re-smoke de la tâche 10) ; de toute façon, le refus du point (1)
    bloquerait un smoke incomplet avant tout scellement.
(3) `B_SWEEP0_LR` vit désormais dans `tools/harness/r1_constants.py`, SOURCE UNIQUE partagée avec
    `smoke_r1.py` (jamais un `0.002` redéclaré indépendamment dans les deux fichiers).
"""
import json
import os
import statistics
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.paths import results_file  # noqa: E402
from src.seed_ai.harness_pieces import PIECES  # noqa: E402
from src.seed_ai.harness_verdict import BRANCHES  # noqa: E402
from tools.experiment_preflight import assert_control_family, declare_design  # noqa: E402
from tools.harness.r1_constants import B_SWEEP0_LR, SMOKE_NAME, SMOKE_SEED  # noqa: E402
from tools.plain_substrate_ceiling import PLAIN_COMPOSITION_CEILING, PLAIN_COMPOSITION_PROVENANCE  # noqa: E402
from tools.preregister import preregister, stamp, verify  # noqa: E402

N_SEEDS, N_ARMS = 12, 5

# Ce que chaque branche de lecture SIGNIFIE pour la famille HARNESS-R1 -- une phrase DISTINCTE par
# branche (fix (4)) : un dict dont les 15 valeurs sont identiques ne discrimine rien, c'est le défaut
# que cette phrase corrige. La boilerplate d'ORDRE (unique) reste seule dans `regle_de_lecture_continue`.
_DISCRIMINATION_TEXT = {
    "INCOMPLET": "un bras ou une eval manque dans la db : le runner n'a pas fini, aucune lecture n'est tentee.",
    "INCONCLUSIVE_N": "moins de n_floor=12 seeds completes (abandons de cout) : la cellule ne peut conclure, quel que soit le resultat mesure.",
    "INDETERMINE_HARNAIS": "le controle positif de la DV (oracle) echoue, ou la reference lr=0 depasse prior_max : le harnais lui-meme est suspect, aucune lecture de la piece n'est tentee.",
    "LR_ARTIFACT": "le nul (d'acquisition ou de necessite) disparait au second pas du sweep : artefact du pas de lr, pas une propriete de la piece.",
    "NOT_ACQUIRED": "le sujet n'acquiert rien au-dessus de sa reference appariee : la question de necessite de la piece ne se pose pas encore.",
    "NOT_DEMANDED": "l'ablation ne mord pas hors bande de bruit : la tache ne DEMANDE pas cette information au sujet (DECOY informatif).",
    "DEMAND_WITHIN_NOISE": "l'ablation mord mais dans la bande de bruit mesuree : aucune demande detectable au-dessus du plancher.",
    "DEMAND_INCONCLUSIVE": "l'instrument de demande refuse de conclure (puissance, signe inverse, degenerescence) : ni demande ni absence de demande n'est affirmee.",
    "INCONCLUSIVE_SPECIFICITY": "le controle de specificite (distracteur) mord : la chute de l'ablation ciblee pourrait venir d'ailleurs que de l'information retiree.",
    "INCONCLUSIVE_ALIAS": "la garde d'aliasing sur l'ablation d'etat echoue : impossible de distinguer une vraie lesion d'un artefact de vue partagee.",
    "PIECE_NOT_NECESSARY": "le contraste intact/sans-piece tombe dans la bande de bruit ou ne mord pas : la piece n'est PAS necessaire a cette tache, a cette dose.",
    "PIECE_INCONCLUSIVE": "le contraste de necessite est lui-meme inconclusif (puissance, degenerescence) : ni necessaire ni non-necessaire n'est affirme.",
    "PIECE_PARTIAL": "sans la piece, le sujet chute mais reste au-dessus de la barre d'acquisition : la piece AIDE sans etre seule a porter la capacite.",
    "DEMANDED_ACQUIRED_NECESSARY": "la tache demande l'information, le sujet l'acquiert, et la piece est necessaire a la porter : la lecture la plus forte du harnais.",
    "AUTRE": "issue non prevue par les 14 branches precedentes : a documenter EXPLICITEMENT avant toute republication de la regle, jamais une cle attrape-tout silencieuse.",
}

# (4) issue NEGATIVE nommee par cellule -- E2 : un instrument qui ne peut pas rater ne prouve rien, donc
# la lecture du RATAGE doit etre ecrite AVANT le run, pas improvisee apres coup.
_ISSUES = {
    "A": {"attendue": "PIECE_PARTIAL",
          "sinon": "soit la bit-identite est perdue (harnais), soit le regime differe (E19/E8) : INDETERMINE, pas un resultat"},
    "Aprime": {"attendue": "PIECE_NOT_NECESSARY",
               "sinon": "le bilineaire modifie le rappel same_tick : resultat a graver"},
    "B": {"attendue": "DEMANDED_ACQUIRED_NECESSARY",
          "sinon": "la retention ne passe pas par l'etat porte a ce pas : resultat a graver, LOCK-001 rouvert"},
}


def _hyper(lr, n_classes):
    return {"lr": lr, "rank": 16, "n_classes": n_classes, "credit": "supervised"}


def build_rule_r1(smoke: dict) -> dict:
    """Pure : construit les trois sous-règles de cellule (A, A', B) et la règle de famille HARNESS-R1-bis.
    Choisit le second lr de B = le meilleur des lr != `B_SWEEP0_LR` dont la médiane dépasse la barre
    (référence + 0,05) ; à égalité, celui le plus proche de `B_SWEEP0_LR` (fix (10)) ; lève s'il n'y en a
    aucun.

    Fix round 2 (1) -- EN TÊTE, avant tout calcul : un smoke incomplet ne doit produire NI règle
    dégradée NI prédiction non adossée. `Aprime_ref`, `noise` (A/Aprime/B) et `unit_s` (A/Aprime/B, bras
    full_eval) sont exigés ; leur absence LÈVE `ValueError`, jamais une prédiction bâtie sur un `else`
    silencieux (motif (a) du dépôt -- entrée absente -> affirmation de fond)."""
    if "Aprime_ref" not in smoke:
        raise ValueError("smoke sans 'Aprime_ref' : aucune prediction ACQUIRED de A' ne peut se sceller "
                         "sans sa reference mesuree (motif (a) : entree absente -> affirmation de fond)")
    _noise = smoke.get("noise", {})
    _missing_noise = [c for c in ("A", "Aprime", "B") if c not in _noise]
    if _missing_noise:
        raise ValueError(f"smoke sans 'noise' pour {_missing_noise} : plancher de bruit manquant, "
                         "aucune prediction ne peut citer une bande mesuree sans elle")
    _missing_unit = [c for c in ("A", "Aprime", "B") if c not in smoke.get("unit_s", {})]
    if _missing_unit:
        raise ValueError(f"smoke sans 'unit_s' (bras full_eval) pour {_missing_unit} : cout non mesure, "
                         "donc non comparable entre cellules (fix round 1, point 2)")

    sweep0_lr = B_SWEEP0_LR
    ref_b = statistics.median(float(v) for v in smoke["B_ref"].values())
    bar_b = ref_b + 0.05
    cands = {float(lr): statistics.median(float(v) for v in col.values()) for lr, col in smoke["B"].items() if float(lr) != sweep0_lr}
    ok = {lr: m for lr, m in cands.items() if m > bar_b}
    if not ok:
        raise ValueError(f"aucun second pas de B ne franchit la barre {bar_b:.3f} : {cands}")
    best = max(ok.values())
    tied = [lr for lr, v in ok.items() if v == best]
    lr2 = min(tied, key=lambda lr: abs(lr - sweep0_lr))          # bris d'egalite (10) : le plus proche de sweep0_lr

    # (2) unit_s est desormais le bras full_eval (comparable entre cellules) ; unit_s_nude reste informatif.
    unit = smoke["unit_s"]
    unit_nude = smoke.get("unit_s_nude", {})
    budget_family = 0.0

    # (1) LU du registre, jamais tape en dur (decision controleur tache 10, deja appliquee en R1).
    sham_bilinear = PIECES["bilinear"].matched_sham
    sham_recurrent = PIECES["recurrent_state"].matched_sham

    common = {"n_floor": N_SEEDS, "min_sep": 0.05, "prior_max": 0.5, "oracle_min": 0.9, "collapse_factor": 1.5,
              "alive_margin": 0.05, "n_agents": 16, "eval_batches": 40}          # (6)

    # (9) plafond de l'incapable IMPORTE, jamais retape.
    ceiling = {"value": float(PLAIN_COMPOSITION_CEILING),
               "provenance": PLAIN_COMPOSITION_PROVENANCE + " MINORANT, jamais PROUVE.", "proven": False}

    abl_A = [{"name": "permute_key", "site": "input", "must_bite": True},
             {"name": "permute_query", "site": "input", "must_bite": True},
             {"name": "inject_distractor_slot", "site": "input", "must_bite": False}]
    abl_Aprime = [dict(abl_A[0]), {"name": "permute_query", "site": "input", "must_bite": False}, dict(abl_A[2])]
    abl_B = [dict(a) for a in abl_A] + [{"name": "state_reset", "site": "state", "must_bite": True}]

    floors_A = {"permute_key": 1 / 6, "permute_query": 1 / 6}
    floors_Aprime = {"permute_key": 1 / 6}
    floors_B = {"permute_key": 1 / 6, "permute_query": 1 / 6, "state_reset": 1 / 6}

    sweep_A = [_hyper(0.02, None), _hyper(0.002, None)]
    sweep_Aprime = [_hyper(0.02, None), _hyper(0.002, None)]
    sweep_B = [_hyper(sweep0_lr, 6), _hyper(lr2, 6)]

    # (5) control_family PAR CELLULE, meme formule que run_harness_cell (n_ablations * len(sweep)) :
    # A=3*2=6, A'=3*2=6, B=4*2=8 -- total 20 (R1 declarait 6 pour la famille ENTIERE, sous-declaration E23).
    cf_A = assert_control_family(cells=len(abl_A) * len(sweep_A))
    cf_Aprime = assert_control_family(cells=len(abl_Aprime) * len(sweep_Aprime))
    cf_B = assert_control_family(cells=len(abl_B) * len(sweep_B))
    cf_total_n = len(abl_A) * len(sweep_A) + len(abl_Aprime) * len(sweep_Aprime) + len(abl_B) * len(sweep_B)
    cf_total = assert_control_family(cells=cf_total_n)

    def _cell(task, episodes, piece, sweep, ablations, bayes_floors, incapable_ceiling, matched_sham,
              control_family, cell_key):
        nonlocal budget_family
        b = 3.0 * float(unit[cell_key]) * N_SEEDS * N_ARMS
        budget_family += b
        return dict(common, task=task, learner="connectome_torch", piece=piece, episodes=episodes,
                    sweep=sweep, ablations=ablations, bayes_floors=bayes_floors,
                    incapable_ceiling=incapable_ceiling, matched_sham=matched_sham,
                    control_family=control_family, budget_s=b, issues=_ISSUES[cell_key])

    cells = {
        "A": _cell("composition_same_tick_K6", 300, "bilinear", sweep_A, abl_A, floors_A, ceiling,
                   sham_bilinear, cf_A, "A"),
        "Aprime": _cell("recall_same_tick_K6", 150, "bilinear", sweep_Aprime, abl_Aprime, floors_Aprime,
                        None, sham_bilinear, cf_Aprime, "Aprime"),
        "B": _cell("composition_two_step_K6", 600, "recurrent_state", sweep_B, abl_B, floors_B, None,
                  sham_recurrent, cf_B, "B"),
    }

    # (7) plancher de bruit MESURE par cellule et par seed -- publie tel quel dans la regle (les
    # predictions ci-dessous en citent le resume, pas des chiffres importes d'ailleurs, E8). Presence
    # deja garantie par la garde en tete de fonction (fix round 2, point 1) : TOUJOURS calculable ici.
    noise = _noise
    band_A = (min(noise["A"].values()), max(noise["A"].values()))
    med_B_intact = statistics.median(float(v) for v in smoke["B"][str(sweep0_lr)].values())
    med_Aprime_ref = statistics.median(float(v) for v in smoke["Aprime_ref"].values())

    design = declare_design(
        question="Le harnais à trois conditions rend-il, sur les trois cellules PORTÉES à réponse "
                 "connue, PARTIAL (A), NOT_NECESSARY (A') et NECESSARY (B) ?",
        replication_unit="seed", n_independent=N_SEEDS,
        links={"ablation->chute": "measured", "dose->acquisition": "measured", "sans_piece->chute": "measured",
               "analogue_bio": "inferred"},
        allow_inferred_reason="l'analogue biologique d'une pièce est une hypothèse portée par le registre "
                              "(spec §2.6), jamais mesurée ici",
        control_family=cf_total)
    design.pop("warning", None)          # (14) : conseil au lecteur humain, pas une donnee a sceller

    a_pred = ("PIECE_PARTIAL : chute >= 3x hors bande, plain ~0,27 > barre ~0,22 (billet publié, "
              "results/bilinear_composition.json) ; bit-identite seed 0 (0,9328125 / 0,2703125, connu "
              "publié) ; bar_status CEILING_ABOVE_BAR (0,944 = 34/36 forme close, publiée > barre "
              "ref+0,05) ; sham DECLARED ({\"bilinear_sham\": True}, registre PIECES) ; "
              f"bande de bruit MESUREE au smoke [{band_A[0]:.3f}, {band_A[1]:.3f}] ; e19 ROBUST attendu")

    aprime_pred = ("PIECE_NOT_NECESSARY : plain = bilineaire = 1,0 (same_tick supervise 150 ep., MESURE "
                   "seeds 0-2 au present smoke) ; acquisition ACQUIRED : reference lr=0 MESUREE mediane "
                   f"{med_Aprime_ref:.3f} << 1,0 appris")

    b_pred = (f"DEMANDED_ACQUIRED_NECESSARY : intact MESURE au present smoke, mediane {med_B_intact:.3f} a lr "
              f"{sweep0_lr} ; state_reset -> ~1/6 (plancher de Bayes K=6, connu) ; sans recurrent_state "
              "(feedforward, entraine sans etat porte) -> ~1/6 (meme plancher) ; second pas de lr "
              f"{lr2} (mediane MESUREE au present smoke {ok[lr2]:.3f}) ; e19 ROBUST attendu")

    return {
        "question": design["question"],
        "design": design,
        "design_note": "unite = seed, n = 12 (seeds 0-11), 5 bras apparies par seed (A, A0, A2, D, D2), "
                       "eval du meme sujet, plancher de bruit par second rng",
        "remplace": "HARNESS-R1",
        "raison_bis": "revue de la tâche 10 : unités non comparables, référence A' non mesurée, plancher "
                      "de bruit absent, issue négative non nommée, famille de contrôles sous-déclarée "
                      "(E2/E8/E23)",
        "cellules": cells,
        "dv_primaire": "`hits` par seed et par bras ; `ratio_within` par ablation ; `sep_ref` (mediane A - mediane A0) ; `dose.updates` par bras ; `noise_band` ; `closure` (E19)",
        "discrimination": dict(_DISCRIMINATION_TEXT),
        "regle_de_lecture_continue": "ORDRE IMPOSE : " + " -> ".join(BRANCHES),
        "predictions_chiffrees_AVANT_le_run": {"A": a_pred, "Aprime": aprime_pred, "B": b_pred},
        "clause_E19": "toute cellule non NECESSARY passe assert_verdict_invariant_to_optimizer sur les deux pas du sweep ; closure > 2/3 = LR_ARTIFACT, pas un verdict",
        "smoke": {"B_medians_by_lr": {str(k): v for k, v in cands.items()}, "B_ref_median": ref_b,
                  "unit_s": unit, "unit_s_nude": unit_nude, "noise": noise, "sweep0_lr": sweep0_lr},
        "budget_family_s": budget_family,
        "cout": (f"temps mur = MAJORANT mesure SOUS CHARGE (E12, d'autres sessions actives pendant le "
                f"smoke) ; unites (s/bras, bras full_eval -- ce que run_harness_cell chronometre) : "
                f"{unit} ; bras nu (informatif) : {unit_nude} ; budget PAR CELLULE = 3 x unite x 12 "
                f"seeds x 5 bras (deja la marge de project_cost, ne PAS remultiplier par safety=3) ; "
                f"budget_family_s = {budget_family/60:.0f} min ; sans bail kuzu"),
    }


# Ruling contrôleur E12 (2026-09-22, après le premier run de -bis) : sous 9 processus python
# concurrents, la CostGuard PAR SEED (`budget_s / 12` = 15 x unité scellée) a abandonné les seeds 2-3
# de la cellule A (bras A0/A2/D/D2) -> INCONCLUSIVE_N. La marge x3 de `project_cost` supposait la
# charge du SMOKE (mesurée à peu près au repos) ; elle ne borne pas la charge d'un run réel partagé
# avec d'autres sessions. Texte SCELLÉ verbatim (ruling contrôleur) -- ne pas reformuler.
RAISON_TER = ("E12 : sous 9 processus python concurrents, la CostGuard par seed (15 x unite) a "
             "abandonne les seeds 2-3 de la cellule A (A0/A2/D/D2) -> INCONCLUSIVE_N ; la marge x3 de "
             "project_cost supposait la charge du smoke. Le budget est une garde de cout, pas une "
             "grandeur lue : la lecture est inchangee.")


def build_rule_r1_ter(rule_bis: dict) -> dict:
    """Pure : construit HARNESS-R1-ter à partir de la règle -bis DÉJÀ SCELLÉE -- LUE depuis le JSON
    scellé (`verify("HARNESS-R1-bis")`), JAMAIS recalculée depuis le smoke (décision contrôleur E12,
    2026-09-22) : recalculer depuis le smoke risquerait de faire bouger le choix du second lr de B
    (`build_rule_r1` re-sélectionne `lr2` par médiane) ou toute autre valeur dérivée, alors que seul le
    BUDGET doit changer. `rule_bis` est copié en PROFONDEUR (`json.loads(json.dumps(...))`) -- jamais
    muté en mémoire, la règle -bis reste intacte sur disque ET en mémoire pour l'appelant.

    Seuls trois changements par rapport à -bis :
      * `cellules[clé].budget_s` x3 (marge de charge EXPLICITE : la CostGuard par seed devient
        `budget_s_ter / 12` = 45 x unité scellée par seed, pour ~5 x unité de travail par seed -- le
        budget est une GARDE DE COÛT, jamais une grandeur LUE par `harness_verdict_lecture`, donc la
        relever ne change AUCUNE lecture) ;
      * `budget_family_s` = somme des budgets de cellule (déjà x3 chacun) ;
      * `remplace` (-bis, pas R1) et `raison_ter` (texte scellé, `RAISON_TER`), à côté de `remplace`/
        `raison_bis` d'origine -- CONSERVÉS : -ter remplace -bis, qui remplaçait déjà R1, la chaîne
        entière reste lisible depuis n'importe quel maillon.

    `predictions_chiffrees_AVANT_le_run` n'est PAS touché : la même prédiction, scellée dans -bis AVANT
    le premier run, reste la prédiction de -ter -- seul le budget de coût a changé, pas la lecture
    attendue. Un champ séparé le déclare explicitement (jamais une mutation silencieuse d'un dict déjà
    scellé ailleurs)."""
    rule = json.loads(json.dumps(rule_bis))
    budget_family = 0.0
    for c in rule["cellules"].values():
        c["budget_s"] = 3.0 * float(c["budget_s"])
        budget_family += c["budget_s"]
    rule["budget_family_s"] = budget_family
    rule["remplace"] = "HARNESS-R1-bis"
    rule["raison_ter"] = RAISON_TER
    rule["predictions_chiffrees_AVANT_le_run_note"] = "scellées dans -bis avant tout run, re-portées telles quelles"
    return rule


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--ter" in argv:
        # -ter se construit depuis le SCEAU -bis, jamais depuis un chemin de smoke -- aucun autre
        # argument n'a de sens ici.
        bis = verify("HARNESS-R1-bis")
        rule = build_rule_r1_ter(bis)
        p = preregister("HARNESS-R1-ter", rule)
        print("->", p)
        return
    # Fix round 2, point (2) : le nominal (`<SMOKE_NAME>_<SMOKE_SEED>.json`) est le smoke DE R1 (sans
    # Aprime_ref) -- desormais suivi par git, ce qui a detourne le re-smoke de la tache 10 vers
    # `_rerun.json` (P2.61). Le defaut suit ce meme fichier, tire de la source UNIQUE `SMOKE_NAME` --
    # et de toute facon, la garde en tete de `build_rule_r1` (fix round 2, point 1) refuse tout smoke
    # incomplet avant qu'aucune regle degradee ne puisse se sceller.
    path = results_file(f"{SMOKE_NAME}_{SMOKE_SEED}_rerun.json")
    if argv:
        path = argv[0]
    # LIRE dans une variable AVANT toute écriture (CLAUDE.md -- jamais un "w" avant d'avoir fini de lire).
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    payload = json.loads(raw)
    rule = build_rule_r1(payload["data"])
    p = preregister("HARNESS-R1-bis", rule)
    # (13) la provenance ne peut pas vivre DANS le sceau qu'elle decrit (circularite) : `stamp()`
    # l'attache au JSON du SMOKE (la ressource que ce scellement vient de consommer), jamais à un
    # fichier sous docs/preregistrations/ (voir docstring du module -- `check_preregistration_applied.py`
    # scanne ENTIER ce repertoire et plante sur un payload dont "rule" n'est pas un dict).
    stamp(payload, "HARNESS-R1-bis")
    new_content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    assert len(new_content) >= len(raw), "stamp() a REDUIT le smoke -- refus d'ecrire (E22)"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("->", p)
    print("-> smoke tamponne (provenance) :", path, payload["_provenance"][-1])


if __name__ == "__main__":
    main()
