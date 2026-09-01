"""Pré-vol expérimental : les vérifications à passer AVANT de lancer un run coûteux.

Motivation empirique — session WARM-005→009 (2026-07-20) : sur 7 revues adversariales, 7 ont trouvé une
erreur réelle. Les 11 symptômes se ramènent à 4 générateurs, dont DEUX sont automatisables. Ce module
automatise ceux-là ; les deux autres exigent une DÉCLARATION écrite avant le run (`declare_design`).

    A. L'instrument peut-il produire LES DEUX issues ?   -> assert_ablation_changes_something,
                                                            assert_positive_control, assert_not_degenerate,
                                                            assert_selection_nonempty,
                                                            assert_verdict_invariant_to_optimizer
    C. La grandeur mesurée est-elle celle qui AGIT ?     -> assert_no_aliasing, assert_no_functional_aliasing,
                                                            assert_predictor_measured_in_situ
    B. Quelle est l'unité de réplication ?               -> declare_design (non automatisable)
    D. Est-ce que je raisonne au lieu de mesurer ?       -> declare_design (non automatisable)

Chaque fonction cite l'erreur CONCRÈTE qu'elle aurait attrapée : c'est ce qui la rend enseignable, et
c'est le seul format qui a survécu à la relecture (une checklist en prose ne résiste pas à la conviction
d'avoir déjà vérifié — j'avais « vérifié » une ablation en contrôlant l'argmax et l'ε-greedy, sans voir
l'aliasing mémoire).

REF : docs/REF/REF-EXPERIMENT-PREFLIGHT.md
"""
from __future__ import annotations

import numpy as np


class PreflightError(AssertionError):
    """Échec de pré-vol : le banc ne peut pas répondre à la question posée. NE PAS lancer le run."""


class ReferenceCollapsedError(PreflightError):
    """Sous-verdict distinct de `assert_verdict_invariant_to_optimizer` (P2.21) : le bras de RÉFÉRENCE
    s'est effondré vers le bras testé, plutôt que le bras testé qui aurait rejoint sa référence. Sous-
    classe de PreflightError (un `except PreflightError` générique l'attrape toujours) mais un test peut
    filtrer sur CE type précis : « artefact avéré » et « mesure inconclusive » sont deux conclusions
    opposées, et les confondre est exactement le motif E3 que cette classe existe pour fermer."""


# --------------------------------------------------------------------------- A. les deux issues

def assert_ablation_changes_something(intact, ablated, label="ablation"):
    """Le bras ablaté doit DIFFÉRER du bras intact. Sinon le « contrôle négatif » est TAUTOLOGIQUE :
    ablater une action que le sujet n'exécute jamais est un no-op analytique, qui ne peut pas échouer.

    Aurait attrapé (EDR-WARM-007) : 8 agents `gi<0.01` dont **6/8 rendaient des tableaux intact/ablé
    BIT-IDENTIQUES**, présentés comme un contrôle négatif à `wins 2/48`. Aucune valeur probante.
    Le contrôle informatif est la manipulation INVERSE (forcer l'action chez ceux qui ne la font pas)."""
    a, b = list(intact), list(ablated)
    if a == b:
        raise PreflightError(
            f"{label} : bras intact et ablaté IDENTIQUES ({a}) -> l'ablation ne fait rien sur ce sujet. "
            "Contrôle tautologique : il ne peut pas échouer. Utiliser la manipulation INVERSE.")
    return True


def assert_positive_control(fn, expect_better_than, label="contrôle positif"):
    """Un bras dont on SAIT qu'il doit réussir doit effectivement réussir. S'il échoue, le banc est
    incapable de détecter l'effet cherché — indépendamment de toute hypothèse.

    Aurait attrapé (WARM-009, run NUL) : bras « production » censé montrer que grabber PAIE, dans un
    monde qui n'engendre AUCUN item de type `Fruit` alors que le revenu +20 exige `item_type=="Fruit"`.
    Bras structurellement INCAPABLE de réussir — miroir du contrôle tautologique. Un contrôle positif
    (« un agent qui grabbe un fruit gagne-t-il de l'énergie ici ? ») l'aurait montré en une minute."""
    got = float(fn())
    if not got > float(expect_better_than):
        raise PreflightError(
            f"{label} ÉCHOUE : {got:.4g} <= {float(expect_better_than):.4g}. Le banc ne peut pas "
            "produire l'issue cherchée -> aucun résultat négatif ne serait interprétable.")
    return True


def assert_not_degenerate(values, min_spread=1e-9, label="mesure"):
    """La métrique doit VARIER sur la population. Si tout s'effondre sur une valeur, on mesure un
    plancher/plafond, pas l'effet — et un « pas de différence » serait ininterprétable.

    Aurait attrapé (WARM-009) : les 24 génomes survivaient **6.0-7.2 ticks SANS EXCEPTION** (contre
    6-124 dans l'autre régime) = plancher de famine. Aurait aussi signalé l'effet de PLAFOND de
    WARM-008, où 32/48 contrôles étaient déjà à `move_acc = 1.000` et ne POUVAIENT pas bouger,
    rendant « sans coût sur la compétence » un artefact de saturation."""
    v = np.asarray(list(values), dtype=float)
    if v.size == 0:
        raise PreflightError(f"{label} : aucune valeur.")
    spread = float(np.nanmax(v) - np.nanmin(v))
    if spread <= min_spread:
        raise PreflightError(
            f"{label} DÉGÉNÉRÉE : étendue {spread:.4g} sur n={v.size} (toutes ≈ {float(v[0]):.4g}). "
            "Plancher ou plafond -> l'effet n'est pas mesurable dans ce régime.")
    return True


def assert_selection_nonempty(n_selected, label="sélection"):
    """Un filtre qui ne sélectionne rien produit « 0 échec », indiscernable d'un succès.

    Aurait attrapé (cette session, sur MA propre vérification) : `pytest -k "torch or backend"` a
    désélectionné les 1034 tests et j'ai lu le résultat comme une non-régression validée.
    Règle : lire le nombre de tests EXÉCUTÉS, pas seulement l'absence d'échec."""
    n = int(n_selected)
    if n <= 0:
        raise PreflightError(
            f"{label} VIDE (n={n}) : « 0 échec » ne prouve rien. Vérifier le filtre avant de conclure.")
    return True


# --------------------------------------------------------------------------- C. mesurer ce qui agit

def assert_no_aliasing(produced, source, label="sortie"):
    """La sortie rendue à l'appelant ne doit pas PARTAGER LA MÉMOIRE de l'état interne, sinon toute
    écriture de l'appelant mute l'état — et une « ablation » devient deux interventions.

    Aurait attrapé (EDR-WARM-007, bug réel) : `TorchPopulationModel.forward` renvoie une VUE de `self.H`
    (`logits = H_new[:, N-O:N]` puis `.cpu().numpy()`), donc `logits[:,24] = -1.0` épinglait le neurone
    88 dans l'état récurrent — perturbation dont l'amplitude était COLINÉAIRE au prédicteur de la
    conclusion. Trois vérifications ciblées (argmax, ε-greedy, seuil du monde) l'avaient manqué ;
    un `np.shares_memory` l'aurait montré immédiatement."""
    try:
        shared = bool(np.shares_memory(produced, source))
    except (TypeError, ValueError):
        return True                                   # types non-array : rien à vérifier
    if shared:
        raise PreflightError(
            f"{label} ALIASÉE sur l'état interne : écrire dedans mutera l'état. "
            "Copier avant de modifier, et appliquer la copie aux DEUX bras (sinon on compare deux "
            "dynamiques en plus de l'intervention).")
    return True


def assert_no_functional_aliasing(control_intact, control_ablated, tol=1e-9, label="capacité de contrôle"):
    """Complément COMPORTEMENTAL de `assert_no_aliasing` (qui, lui, est STRUCTUREL via np.shares_memory).

    Une capacité de CONTRÔLE, connue INDÉPENDANTE du canal ablaté, ne doit pas bouger sous l'ablation.
    Si elle bouge, l'ablation agit par un canal partagé du substrat (aliasing FONCTIONNEL) — et tout
    verdict de demande tiré de cette ablation est contaminé.

    Aurait attrapé (le faux positif que SP-2 hériterait) : ablater X pour mesurer « Y demande-t-elle X ? »
    sur un substrat où X et Y partagent des neurones effondre Y par la représentation partagée, pas parce
    que Y demande X. `np.shares_memory` est AVEUGLE à ça (buffers séparés) ; ce garde le mesure."""
    d = abs(float(control_intact) - float(control_ablated))
    if d > float(tol):
        raise PreflightError(
            f"{label} a BOUGÉ de {d:.4g} (> tol {float(tol):.1g}) sous l'ablation d'un canal censé lui être "
            "ÉTRANGER : aliasing FONCTIONNEL de substrat. L'ablation n'est pas chirurgicale -> tout verdict "
            "de demande qui en découle est contaminé (mesurer sur une capacité de contrôle indépendante).")
    return True


def assert_predictor_measured_in_situ(predictor_ctx, experiment_ctx, label="prédicteur"):
    """Le prédicteur doit être mesuré DANS le contexte où l'intervention opère. Un proxy mesuré ailleurs
    peut classer les sujets à côté.

    Aurait attrapé (EDR-WARM-007) : le taux de grab mesuré sur la trajectoire ORACLE donnait une
    corrélation de +0.33 avec l'effet, contre **+0.53 mesuré in-world** — et surtout il RATAIT des
    grabbers (agent à `oracle_on_frac=0.15` qui grabbe **0.996** in-world). ⚠️ Nuance établie ensuite :
    l'échec est UNILATÉRAL (0 faux-positif, 3 faux-négatifs, ρ=+0.819), pas une inversion — ne pas
    sur-généraliser dans l'autre sens non plus."""
    if predictor_ctx != experiment_ctx:
        raise PreflightError(
            f"{label} mesuré dans « {predictor_ctx} » mais l'intervention opère dans « {experiment_ctx} ». "
            "Mesurer le prédicteur in situ, ou justifier explicitement l'écart.")
    return True


# ------------------------------------------------- A (bis). le verdict survit-il au RÉGLAGE ? (E19)

def assert_verdict_invariant_to_optimizer(measure, lrs=(0.02, 0.002), max_gap_closure=2.0 / 3.0,
                                          reference_floor=None, label="verdict comparatif"):
    """Un NUL DE CAPACITÉ doit survivre au balayage du pas d'apprentissage — sinon il mesure le RÉGLAGE.

    `measure(lr)` rend le couple `(bras_testé, bras_de_référence)` : deux scalaires (médianes) mesurés AU
    MÊME `lr`, dans le MÊME run. La garde raisonne sur l'ÉCART AU BRAS DE RÉFÉRENCE d'un pas à l'autre —
    motif MESURÉ : un nul ARTEFACTUEL REFERME son écart quand on change le pas, un nul STRUCTUREL le
    CONSERVE.

        gap(lr) = référence(lr) − testé(lr)        closure = 1 − min(gap) / max(gap)

    ⚠️ JAMAIS une barre absolue — c'est LE point de conception, et il est mesuré, pas raisonné : la barre
    du dépôt `1/K + 0.15 = 0.3167` se situe **0.072 SOUS** le plafond structurel du substrat plain
    (**0.3889**, forme close des 36 paires, 8 restarts ; contrôle positif du même optimiseur sur une table
    libre non séparable : 1.000). Un substrat PROUVABLEMENT incapable de composer franchit donc cette barre
    au bon pas (0.3719 à `lr=0.1`) et même au pas d'origine avec plus de budget (0.3703 à
    `episodes=2400`). Réévaluer un SEUIL sous balayage flaguerait ce VRAI négatif ; réévaluer l'ÉCART
    ENTRE BRAS le laisse passer. Corollaire : un verdict à UN SEUL bras et seuil absolu n'est pas
    protégeable par ce mécanisme — il faut un bras de référence DANS le même run.

    Aurait attrapé (EDR-RETAIN-COMPOSE, 2026-09-01, le verdict d'un record ENTIER, n=12) : à `lr=0.02`,
    `learned` 0.173 contre `oracle` 0.971 -> verdict `RETENTION` ; à `lr=0.002`, 0.923 contre 0.945.
    L'écart passe de **0.798 à 0.022** (closure 0.97) — le bras testé REJOINT sa référence, le « mur de
    rétention » était le pas. Séparation par-seed TOTALE (min à lr=0.002 = 0.897 > max à lr=0.02 = 0.192,
    0/144). Cause racine : `n_agents=16` n'est PAS un minibatch (chaque agent porte ses PROPRES
    `W/U/V/W_bl`, `src/agents/backend_torch.py:85-86`) -> batch effectif **1** sous Adam `lr=0.02` ; les
    conditions à UN `_step` le tolèrent, celle à DEUX `_step` diverge. Aggravant : les DEUX contrôles
    calibrés de la sonde vivaient dans le régime à un seul `_step`, donc aucun ne POUVAIT voir la
    pathologie du régime qui portait le verdict. Classe **E19** du registre.

    Ne tire PAS (SPÉCIFICITÉ, mesurée sur un nul structurel connu) : sous-projet BILINEAR, plain contre
    bilinéaire (0.966) à opérandes co-présents — écart 0.652 à `lr=0.02`, 0.594 à `lr=0.1` -> closure
    **0.089**. Baisser le pas y DÉGRADE le bras testé vers le hasard (0.160) au lieu de le sauver.
    ⚠️ Provenance : ce volet de spécificité (balayage plain 4 seeds + plafond en forme close) vient d'UNE
    seule passe, NON RÉPLIQUÉE — contrairement au cas artefact, établi à n=12. Il calibre la DIRECTION de
    la garde (un nul structurel ne referme pas son écart), pas une valeur de seuil à 3 décimales.

    Règle d'usage : quand deux bras d'un verdict n'ont pas la même difficulté d'OPTIMISATION (1 pas vs 2
    pas, opérandes co-présents vs portés à travers un tick), le réglage n'est pas une nuisance mais un
    FACTEUR — le balayer fait partie du contrôle positif.

    --- P2.21 : `reference_floor` (motif E3 DANS la garde elle-même) -----------------------------------
    Une fermeture d'écart a DEUX causes indiscernables du seul nombre `closure` : (1) le bras TESTÉ monte
    vers sa référence (l'artefact visé) ; (2) le bras de RÉFÉRENCE s'EFFONDRE vers le testé — closure
    identique, aucun artefact à dénoncer, les deux bras sont juste morts. `reference_floor=None` (défaut,
    même convention que `floor=`/`ceiling=` de `ablation_verdict` — PAS de constante magique implicite)
    désactive le distingo, comportement inchangé. Fourni, la garde exige que le bras de RÉFÉRENCE reste
    STRICTEMENT AU-DESSUS de `reference_floor` aux DEUX pas qui portent la closure (`lr_max` = écart le
    plus profond, `lr_min` = écart le plus refermé — les deux seuls points qu'utilise la formule) AVANT
    de lire quoi que ce soit dans `closure`, fermeture flaguée OU PAS : lire un « pass » avec une
    référence effondrée serait tout aussi fabriqué qu'un « artefact » avec une référence effondrée. Si
    elle ne l'est pas, verdict DISTINCT — `ReferenceCollapsedError` (sous-classe de `PreflightError`,
    tag `INCONCLUSIVE_REFERENCE_COLLAPSED` dans le message) — jamais un refus muet dans la branche
    d'origine, jamais un `pass` silencieux à la place.

    Aurait attrapé EN ACTE (EDR-DELAYED-COORD, 2026-09-01, la garde elle-même prise en défaut sur son
    propre record) : bras testé = appris, bras de référence = canal ORACLE (`argmax` du référent perçu au
    lieu de l'émission apprise), même sonde, même seed — `lr=0.02` : testé 0.141, référence 0.436 (écart
    0.295) ; `lr=0.08` : testé 0.203, référence 0.194 (écart −0.009). closure = 1 − (−0.009/0.295) =
    **103.1 %** > 2/3 : AVANT ce correctif, la garde levait « artefact d'hyperparamètre ». Faux : le bras
    testé n'a JAMAIS bougé (0.141 → 0.203, tous deux dans la bande **0.164–0.206** que le crible publié de
    ce record mesure pour RETAIN/PRESENT au plancher documenté `1/K = 0.167`, K=6) — c'est la RÉFÉRENCE
    qui s'est effondrée (0.436 → 0.194, canal oracle noyé à `lr=0.08`). Avec `reference_floor = 1/6+0.15`
    (même barre que le contrôle BILINEAR ci-dessus, K=6 identique), `0.194 <= reference_floor` à
    `lr=0.08` -> `ReferenceCollapsedError`, pas « artefact ». Chiffres du couple appris/oracle et
    provenance : section « Ce que ça débloque » de
    `docs/EDR/EDR-DELAYED-COORD_Deferred_Referential_Coordination_Demands_Retention.md` (mêmes seed et
    `_params` que le crible publié dans ce même record, dont la table RETAIN/PRESENT corrobore que le
    bras appris n'a jamais quitté le plancher).

    Ne tire PAS le NOUVEAU distingo (spécificité, positif apparié) : re-testé sur RETAIN-COMPOSE ci-dessus
    avec `reference_floor = 1/6+0.15` — `oracle` vaut 0.971 puis 0.945 aux deux pas, tous deux largement
    au-dessus -> `reference_floor` ne change RIEN, la garde lève toujours « artefact d'hyperparamètre ».
    Sans ce contrôle on remplacerait une garde trop laxiste par une garde trop stricte (même défaut, signe
    inversé) : `reference_floor` doit épargner une référence VIVANTE, pas juste faire taire la garde."""
    xs = [float(x) for x in lrs]
    if len(set(xs)) < 2:
        raise PreflightError(
            f"{label} : il faut AU MOINS DEUX pas DISTINCTS pour tester l'invariance (reçu {xs}). "
            "Un seul point d'hyperparamètre ne peut pas distinguer un nul de capacité d'un nul de réglage.")
    gaps = {}
    refs = {}
    for lr in sorted(set(xs)):
        pair = measure(lr)
        try:
            tested, reference = pair
        except (TypeError, ValueError):
            raise PreflightError(
                f"{label} : `measure({lr:g})` doit rendre le couple (bras_testé, bras_de_référence) "
                f"mesuré au MÊME pas ; reçu {pair!r}.")
        tested, reference = float(tested), float(reference)
        gaps[lr] = reference - tested
        refs[lr] = reference

    lr_max = max(gaps, key=lambda k: gaps[k])          # pas où le nul est le plus PROFOND
    lr_min = min(gaps, key=lambda k: gaps[k])          # pas où il est le plus REFERMÉ
    g_max, g_min = gaps[lr_max], gaps[lr_min]
    if g_max <= 0.0:
        return True            # le bras testé n'est SOUS sa référence à aucun pas : aucun nul à défendre

    if reference_floor is not None:
        floor = float(reference_floor)
        # Les DEUX points qui portent la closure, PAS l'ensemble du balayage : ce sont les seuls que la
        # formule utilise, et suffisants pour rendre `closure` illisible si l'un d'eux est mort.
        effondres = {lr: refs[lr] for lr in {lr_max, lr_min} if refs[lr] <= floor}
        if effondres:
            detail = ", ".join(f"lr={lr:g} : référence {refs[lr]:.4g}" for lr in sorted(effondres))
            raise ReferenceCollapsedError(
                f"{label} : INCONCLUSIVE_REFERENCE_COLLAPSED -- bras de RÉFÉRENCE au PLANCHER déclaré "
                f"({floor:.4g}) à au moins un des deux pas qui portent la closure ({detail}). Une "
                "fermeture d'écart a deux causes indiscernables du seul ratio : le bras testé qui monte "
                "(artefact), OU la référence qui s'effondre (aucun artefact, les deux bras sont morts) — "
                "ici c'est la référence. Ni un refus d'artefact, ni un `pass` : rejouer à un régime où la "
                "référence reste vivante aux deux pas avant de conclure quoi que ce soit sur ce nul.")

    closure = 1.0 - (g_min / g_max)
    if closure > float(max_gap_closure):
        raise PreflightError(
            f"{label} : nul NON robuste au pas -> artefact d'hyperparamètre, PAS un verdict de capacité. "
            f"L'écart au bras de référence se REFERME de {closure:.1%} sur le balayage "
            f"(lr={lr_max:g} : écart {g_max:.4g} -> lr={lr_min:g} : écart {g_min:.4g} ; "
            f"seuil {float(max_gap_closure):.1%}). Le bras testé REJOINT sa référence quand on change "
            "SEULEMENT le réglage : le réglage est un FACTEUR du verdict. Rejouer, ou refuser le verdict.")
    return True


# --------------------------------------------------------------------------- B + D. déclaration

_MEASURED = "measured"
_INFERRED = "inferred"


def declare_design(question, replication_unit, n_independent, links, cost_estimate=None):
    """Force la DÉCLARATION ÉCRITE de ce qu'aucun code ne peut décider : l'unité de réplication, et
    quels maillons sont MESURÉS vs INFÉRÉS. Renvoie un dict à joindre au record.

    `links` : dict {nom_du_maillon: "measured" | "inferred"}.

    Générateur B — Aurait attrapé : `sign_p=1.5e-05` calculé sur **16 AGENTS** partageant trajectoire
    oracle, augmentation DAgger, optimiseur ET mondes (corr inter-agents +0.345) -> n indépendant = 2
    seeds. Écrire « unité = agent » à côté de « les agents partagent l'entraînement » rend le conflit
    visible. (⚠️ L'idiome du projet, lui, réplique correctement sur l'ÈRE/le SEED — j'avais généralisé
    ce défaut local à tout le dépôt avant de devoir me rétracter : déclarer n'exempte pas de vérifier.)

    Générateur D — Aurait attrapé : dans WARM-008 j'ai INFÉRÉ le maillon final (gain de survie) au lieu
    de le mesurer, pour économiser ~7 h. La revue l'a mesuré NUL en 28 min. Une chaîne causale
    transporte son SIGNE, pas son AMPLITUDE : l'effet valait 55 % de la marge sur la population d'origine
    et 2-10 % sur celle du banc. **Règle : réduire le n, jamais supprimer le maillon.**"""
    bad = {k: v for k, v in links.items() if v not in (_MEASURED, _INFERRED)}
    if bad:
        raise PreflightError(f"links : valeurs invalides {bad} (attendu 'measured' ou 'inferred')")
    if int(n_independent) < 1:
        raise PreflightError("n_independent doit être >= 1")
    inferred = [k for k, v in links.items() if v == _INFERRED]
    return {"question": question, "replication_unit": replication_unit,
            "n_independent": int(n_independent), "links": dict(links),
            "inferred_links": inferred, "cost_estimate": cost_estimate,
            "warning": (f"{len(inferred)} maillon(s) INFÉRÉ(S) : {inferred}. Une chaîne causale "
                        "transporte son signe, pas son amplitude — vérifier que le régime place "
                        "l'effet au-dessus du bruit, ou mesurer à n réduit.") if inferred else None}


def assert_n_per_arm(arm_a, arm_b, max_ratio=1.5, label="bras"):
    """Les deux bras doivent porter des POPULATIONS comparables avant qu'on compare leurs médianes.

    Classe E15 du registre, promue `exécutable` le 2026-09-02. Occurrence fondatrice (EDR-095) : le
    rêve forcé multipliait `n_lived` par **13-16** entre bras ; la survie médiane « chutait de 55 % »
    (sign_p 0.0005, reproduit) alors que sur la cohorte fondatrice APPARIÉE l'effet était ABSENT.
    L'indice — le n ×16 — était publié DANS le record, en « effet secondaire ».

    ⚠️ Aucune garde de borne ne voit ça : aucun bras n'est au plancher ni au plafond. Une médiane est
    robuste aux valeurs extrêmes, PAS à un changement de population — si un bras fait naître 15× plus
    d'agents, sa médiane décrit une AUTRE population, pas le même monde mesuré deux fois."""
    na, nb = len(list(arm_a)), len(list(arm_b))
    if na == 0 or nb == 0:
        raise PreflightError(f"{label} : un bras est VIDE (n_a={na}, n_b={nb}) — rien à comparer.")
    ratio = max(na, nb) / min(na, nb)
    if ratio > max_ratio:
        raise PreflightError(
            f"{label} : populations INCOMPARABLES (n_a={na}, n_b={nb}, ratio {ratio:.1f}x > "
            f"{max_ratio}x). Comparer leurs médianes décrirait deux populations différentes, pas un "
            f"effet — apparier les cohortes (même naissance), ou expliquer le n AVANT le verdict "
            f"(cf. EDR-095, classe E15).")
    return True
