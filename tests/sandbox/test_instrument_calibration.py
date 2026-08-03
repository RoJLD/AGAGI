"""CALIBRATION D'INSTRUMENTS sur vérité-terrain.

Principe (REF-EXPERIMENT-PREFLIGHT) : un instrument de mesure doit retrouver une réponse CONNUE
ANALYTIQUEMENT avant d'être appliqué à l'inconnu. Sans ça, un bug de l'instrument PRODUIT un résultat —
c'est exactement ce qui est arrivé à l'ablation `grab_off` (aliasing `logits`↔`H`, EDR-WARM-007), dont la
perturbation d'état était colinéaire au prédicteur de la conclusion.

BOUCLE D'AUTO-AMÉLIORATION : chaque bug d'instrument trouvé en revue doit devenir un cas ici. La suite
croît de façon MONOTONE avec les erreurs découvertes -> un bug corrigé ne peut plus jamais repasser
silencieusement. C'est un cliquet, pas une checklist.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytest.importorskip("torch")

from src.seed_ai.mutation import Genome  # noqa: E402
from tools.ground_truth_worlds import GroundTruthCarryWorld, make_carry_world  # noqa: E402
from tools.warmstart_evolution_inworld import _torch_survival_eras  # noqa: E402

# Déclaration EXPLICITE de ce qui est calibré, lue par tools/check_instrument_calibration.py.
# Clé = (fonction, branches couvertes). ⚠️ NE PAS déduire du nom : jusqu'au 2026-07-21 le cliquet
# comptait un instrument calibré dès que son nom apparaissait dans ce fichier, ce qui masquait une
# couverture PARTIELLE (classe E4 — une vérification qui ne peut pas échouer).
# `["*"]` = instrument sans branches. Ajouter une branche ici EXIGE d'ajouter le cas de test.
CALIBRATED = {
    # P2.1 : branche "perception" enfin couverte — inertie à dose 0 (métrique VIVANTE),
    # effondrement à dose 6, monotonie dans la plage NON CENSURÉE (le ratio se compresse
    # dès que le bras intact frôle max_ticks : les chiffres publiés sont des bornes INF).
    "_torch_survival_eras": ["grab_off", "perception"],
    "_verdict_decomposition": ["*"],        # P2.3 : bilinéaire / linéaire / monotonie (2026-07-21)
    # P2.0 : contrôle positif oracle (22.2×) + dose-réponse de fidélité, régime S2-009.
    # ⚠️ Couvre le BANC (monde, boucle d'ères, agrégation, ablation par dérangement) avec une politique
    # INJECTÉE. Le chemin génome→comportement (`PerceptionAblatedMamba` sur un génome évolué) reste
    # NON couvert : l'oracle entre avec `genome=None`.
    "_mamba_survival_eras": ["perception:oracle"],
    # P2.8 : contrôle positif de la variante `cog_linear` (oracle 200 vs plancher 13.5,
    # ratio 14.81 mesuré à K=12). Instrument NÉ le 2026-07-21 — calibré dans la même passe.
    "run_linear_sanity": ["*"],
    # P2.10 : ON = contrôle positif RÉEL (22.22, amplitude) ; OFF = nul DÉGÉNÉRÉ (bras
    # bit-identiques sur 12 ères) — la seconde branche corrige le contrôle négatif de S2-009.
    "run_cog_demand_map": ["on:positive", "off:degenerate"],
    # P2.11 : contrôle positif du verdict FONDATEUR (champion_body). Premier instrument de
    # `src/` calibré — le scan y a été étendu le même jour. Rend bien COGNITION quand la
    # cognition paie (200 vs 7), et ne crédite pas un corps inexistant.
    "verdict_cognition_body": ["positive:cognition"],
    # P2.2 : bug RÉEL corrigé (paire doublement éteinte comptée contre le rêve). Les deux
    # sens du défaut sont figés, + non-régression sur les valeurs publiées par EDR-095.
    "dose_response_verdict": ["*"],
    # P2.4 : l'instrument le plus cité du graphe (REF-DEMAND-MARKER, ~20 records).
    # DEMANDING -> X_DEMANDED, TRIVIAL -> X_DECOY, les deux sur métrique VIVANTE (hors
    # plafond), + la nuisance `intervention_verified` trouvée en calibrant.
    "ablation_verdict": ["*"],
    # P2.6 : bundle Lewis. Toutes les branches atteignables, frontière `> 0.5` STRICTE
    # vérifiée, et la bascule METABOLISME->CARRY assertée là où la docstring de
    # GroundTruthCarryWorld l'annonçait sans jamais la tester.
    "_verdict_drain": ["*"],
    "_verdict_bio": ["*"],
    # P2.5 : garde de PUISSANCE armée (le `sign_p` calculé ne conditionnait rien).
    # Débloqué par la fin des sessions parallèles. Ne peut que transformer un POSITIF
    # en NEUTRE -> les conclusions nulles du graphe sont intactes par construction.
    "compute_ab_verdict": ["*"],
    # DREAM-005 : sonde d'attracteur promue du scratchpad. `measure_convergence` est le CŒUR
    # scientifique (il tranche « cette trajectoire d'état converge-t-elle ? »). Calibré sur deux
    # systèmes CONNUS — contractif (converge) et marche aléatoire (ne converge pas) — + monotonie
    # (le pas de queue décroît quand la contraction est plus forte). Ferme la dette « instrument
    # de scratchpad hors cliquet » signalée par le record.
    "measure_convergence": ["*"],
    # EVO-002 : instrument de RÉTENTION calibré PAR PRÉDICTION (sep(D)=(1−δ)^D sur un génome diagonal, δ
    # depuis le forget-gate clippé), + les deux pôles (δ=0 -> 1 ; δ=1&W_off=0 -> 0) + monotonie. Surtout :
    # démontre qu'il DISSOCIE ce que measure_convergence CONFOND — un substrat δ=0 est « gelé » pour
    # measure_convergence (pas médian 0) mais sep=1 (il RETIENT). C'est la calibration-contre-tâche qui a
    # fait rétrograder cet instrument de primaire à corroborant dans EDR-EVO-002.
    "measure_retention_separation": ["*"],
    # EVO-002 : verdict de CAPACITÉ (3 branches OBJECTIVE_IS_LEVER / SUBSTRATE_OR_SEARCH_LIMITED /
    # INCONCLUSIVE) + garde de PUISSANCE (test de signe : n=3 unanime -> p=0.25 -> INCONCLUSIVE malgré
    # une accuracy haute).
    "compute_enrichment_verdict": ["*"],
    # SP-3 : récupération d'un DAG de prérequis IMPOSÉ (os-taxonomy = clé de réponse). Contrôle positif
    # (prérequis DUR récupéré), SPÉCIFICITÉ sous confond corrélé (no-op sur non-arête même corrélée),
    # monotonie (dur > mou > non-arête), + contraste : une ablation par l'ANCÊTRE faux-positive.
    "run_prerequisite_recovery_probe": ["*"],
    "prerequisite_recovery_verdict": ["*"],
    # SP-2 : « coordination demande perception » sur le jeu de Lewis. Contrôle positif = sender ORACLE
    # (signal = perception -> ablater effondre) ; contrôle négatif = sender ALÉATOIRE (inerte). Générateur A.
    "run_perception_coordination_demand_probe": ["*"],
    # « memory demands perception » (delayed-match torch). Contrôle positif = memory ORACLE (rétention
    # parfaite -> déranger l'encodage effondre) ; contrôle négatif = memory ALÉATOIRE (inerte). Générateur A.
    "run_memory_perception_demand_probe": ["*"],
    # EVO-003 : instrument LOAD-BEARING du verdict in-world (l'évolution n'encode PAS la cognition d'apex :
    # la politique ignore le canal type obs[4]). Calibré PAR CONSTRUCTION : un génome qui CÂBLE obs[4] vers
    # les move-outputs -> Δ grand (sonde sensible) ; un génome dont le FANOUT de obs[4] est nul -> Δ EXACT 0
    # avec sorties non dégénérées (logit_std>0) -> ce qui rend le Δ≈0 des champions INTERPRÉTABLE (ils
    # ignorent obs[4]) et non un artefact. C'est le contrôle positif qui a débloqué le verdict après 4 sondes.
    "measure_type_sensitivity": ["*"],
    # CALIB-ALIAS : aliasing FONCTIONNEL de substrat (câblage imposé dans le vrai recurrent_forward).
    # no-op EXACT sur disjoint, FUITE sur partagé, monotone en la dose, + contraste : np.shares_memory
    # (le garde STRUCTUREL) est aveugle à la fuite que le garde COMPORTEMENTAL attrape.
    "run_functional_aliasing_probe": ["*"],
    "functional_aliasing_verdict": ["*"],
    # EVO-004 : généralise measure_type_sensitivity à TOUS les canaux (quels canaux d'obs la politique LIT).
    # Calibré PAR CONSTRUCTION : un lecteur du canal k -> saillance ISOLÉE sur k (haute), 0 ailleurs ; un
    # non-lecteur (fanout de k = 0) -> saillance nulle sur k. C'est le contrôle positif qui rend le « ~200×
    # sous un lecteur » des champions INTERPRÉTABLE (ils ne lisent presque rien) et non un artefact.
    "measure_channel_saliency": ["*"],
    # EVO-004 / classe E17 : saillance de l'indice sur le banc proxy. Calibré sur un génome qui RÉSOUT la
    # tâche (acc 1.000, câblé à la main) — et qui sert de CONTRE-EXEMPLE gelé : sa saillance en AMPLITUDE
    # vaut 2e-6, indiscernable de celle d'un NON-lecteur (0.0), tandis que `sign_flip` sépare 1.00 vs 0.00.
    # C'est la garde exécutable de la classe E17 du registre (amplitude mesurée là où la décision lit le signe).
    "measure_cue_saliency": ["*"],
    # EVO-005 : objectif cognitif in-world. `measure_cognitive_rate` est l'ESTIMATEUR qui décide quels agents
    # la sélection retient -> calibré sur vérité-terrain ANALYTIQUE (la chance à faible compte est écrasée,
    # monotonie, un tick réussi de plus aide toujours) + un CONTRE-EXEMPLE gelé : la variante « lissage vers
    # la chance » — la lecture évidente de la leçon d'EDR-056 — crée une incitation à MOURIR TÔT et aurait
    # fabriqué un faux négatif. `benchmark_cognitive` a ses deux bornes (lecteur câblé > plafond d'une
    # politique fixe ; MÊME génome privé de l'information -> effondrement ; non-lecteur -> plancher).
    # (`synthetic_reader` n'est PAS déclaré : c'est un TÉMOIN câblé, pas une fonction qui produit une
    # affirmation — mais la dérive d'état qu'il révèle est gelée par un test.)
    "measure_cognitive_rate": ["*"],
    "benchmark_cognitive": ["reader:positive", "blind:specificity", "nonreader:floor"],
    # EVO-003, rendu VISIBLE au cliquet le 2026-07-27 (motif `benchmark_\w+`, classe E4). Couverture
    # PARTIELLE assumée : seule la branche du DÉFAUT est calibrée — `disc` SATURE à 1.00 sur 1-2 rencontres
    # et zéro contact Leurre, donc rend son maximum sur une preuve qui ne peut pas le soutenir (E18 hors
    # d'une fitness + plafond E3). C'est ce qui rend le « contrôle positif partiel » d'EVO-003
    # ininterprétable. La branche « disc mesure vraiment un choix » reste NON calibrée.
    "benchmark_discrimination": ["saturation:degenerate"],
    # EVO-006 : crédit PARTIEL (K sous-tâches). `benchmark_cognitive` gagne la branche `partial:ladder`
    # (monotonie 0/3 < 1/3 < 3/3 ET isolation : câbler la sous-tâche k ne fait monter QUE k).
    # `measure_decision_saliency` est NÉ avec ce record : il lit la bascule de `sign(logits[out])`,
    # l'opérateur EXACT du monde (`do_throw = logits[8] > 0`), là où `measure_channel_saliency` lit
    # `argmax(logits[:8])` et est donc AVEUGLE aux sous-tâches hors-argmax — contre-exemple gelé : sur un
    # lecteur `throw` PARFAIT (bascule 1.000), la saillance d'argmax rend 0.000.
    "measure_decision_saliency": ["reader:positive", "channel:specificity", "nonreader:floor"],
    # « language demands memory » (delayed-code-application). Contrôle positif DEMANDE = memory ORACLE
    # (rétention parfaite -> ablater collapse LANG) ; négatif = ALÉATOIRE (inerte) ; le garde
    # functional_aliasing est prouvé SENSIBLE par control LEAKY (contrôle forcé de dépendre du key ->
    # FUITE détectée). Générateur A dans les DEUX dimensions (demande + aliasing) — 1ère ablation
    # SUBSTRAT du graphe AGI-Taxonomy (les 2 arêtes précédentes ablataient l'ENTRÉE, 'n/a').
    "run_language_memory_demand_probe": ["*"],
    # Le terme BILINÉAIRE débloque-t-il la composition ? Positif ATTENDU (hypothèse du sous-projet) =
    # (q+key)%K passe de NUL (plain) à APPRIS (bilinéaire) ; no-op = pur-rappel non régressé en
    # bilinéaire. ⚠️ MESURÉ (Tâche 2, 2026-08-03) : le positif NE SE PRODUIT PAS dans l'enveloppe
    # testée (episodes 150-3000, lr 0.02-0.1, rank 16-64, 5 seeds) — bilinéaire reste AU PLANCHER
    # (~0.15-0.20) et est même SYSTÉMATIQUEMENT SOUS plain (qui frôle le seuil, cohérent avec
    # l'étalon LANG-MEMORY). Calibré sur le NUL REPRODUCTIBLE (le bras « positif » ne peut PAS
    # réussir à ce budget — c'est une MESURE, pas un artefact d'instrument, car le même instrument
    # démontre bilinéaire > seuil sur task='recall', donc n'est pas structurellement bloqué à False)
    # + le no-op RÉEL (bilinéaire apprend bien le pur-rappel). Verdict scientifique n=12 : Tâche 3.
    "run_bilinear_composition_probe": ["*"],
}

_GENOMES = os.path.join("results", "warm007_genomes")
_GRABBER = os.path.join(_GENOMES, "seed2026_agent00.npz")      # gi = 1.000 mesuré in-world
_NON_GRABBER = os.path.join(_GENOMES, "seed2026_agent06.npz")  # gi = 0.000 mesuré in-world


def _load(path):
    if not os.path.exists(path):
        pytest.skip(f"génome de calibration absent : {path}")
    d = np.load(path, allow_pickle=False)
    return Genome(d["W"], int(d["num_inputs"]), int(d["num_outputs"]))


def _eras(genome, ablate, K=3, max_ticks=300, world=None):
    return _torch_survival_eras(genome, ablate, 2026, K, 12, max_ticks, 0.75, 12.0,
                                ablate_kind="grab_off", world_cls=world or GroundTruthCarryWorld)


def test_instrument_is_exact_noop_on_non_grabber():
    """LE CONTRÔLE QUI COMPTE. Sur un agent qui ne grabbe pas, l'ablation doit être un no-op EXACT,
    ère par ère. Toute dérive signale que l'instrument agit par un canal AUTRE que le geste — signature
    qu'avait le bug d'aliasing, et qui était passée pour un résultat (ratios 0.95-2.68 sur des gi=0)."""
    g = _load(_NON_GRABBER)
    intact, ablate = _eras(g, False), _eras(g, True)
    assert intact == ablate, f"ablation NON inerte sur un non-grabber : {intact} vs {ablate}"


def test_survival_follows_the_imposed_carry_cost_by_prediction():
    """CALIBRATION PRINCIPALE, par PRÉDICTION (pas par valeur absolue — les coûts d'action, hors de
    `_resolve_biology`, dominent et ne sont pas contrôlables sans réécrire `step()`).

    On identifie le drain non contrôlé D en UN point (gt_carry=0), puis on PRÉDIT la survie à
    gt_carry=c sans aucun paramètre libre restant. Si la mesure suit la prédiction, la survie répond
    bien LINÉAIREMENT au coût imposé -> l'instrument de survie est calibré sur ce régime."""
    g = _load(_GRABBER)
    s0 = float(np.median(_eras(g, False, world=make_carry_world(0.0))))
    assert s0 > 0, "bras de référence dégénéré"
    D = GroundTruthCarryWorld.identify_other_drain(s0)
    for c in (1.0, 3.0):
        predit = GroundTruthCarryWorld.predict_survival(D, c)
        mesure = float(np.median(_eras(g, False, world=make_carry_world(c))))
        assert mesure == pytest.approx(predit, rel=0.25), (
            f"NON CALIBRÉ à gt_carry={c} : mesuré {mesure:.1f} vs prédit {predit:.1f} "
            f"(D={D:.2f} identifié à carry=0, survie {s0:.1f})")


def test_ablation_effect_grows_with_the_imposed_carry_cost():
    """MONOTONIE : plus le portage coûte cher, plus retirer le grab doit rapporter. Un instrument dont
    l'effet ne suit pas la dose IMPOSÉE mesure autre chose que ce qu'il prétend."""
    g = _load(_GRABBER)
    ratios = []
    for c in (0.0, 3.0):
        w = make_carry_world(c)
        mi = float(np.median(_eras(g, False, world=w)))
        mo = float(np.median(_eras(g, True, world=w)))
        ratios.append(mo / max(mi, 1e-9))
    assert ratios[1] > ratios[0], f"effet NON monotone en la dose imposée : {ratios}"


def test_instrument_does_not_alias_recurrent_state():
    """Régression du bug RÉEL (EDR-WARM-007). Encodé ici parce que c'est un défaut d'INSTRUMENT :
    `forward` renvoie une vue de `H`, donc clamper les logits mutait l'état récurrent."""
    from src.agents.mamba_agent import MambaAgent
    from src.agents.backend_torch import TorchPopulationModel
    from tools.warmstart_evolution_inworld import _GRAB_NODE_T
    from tools.experiment_preflight import assert_no_aliasing, PreflightError
    pop = TorchPopulationModel([MambaAgent() for _ in range(4)], lr=0.0)
    logits, _ = pop.forward(np.zeros((4, pop.I), dtype=np.float32))
    with pytest.raises(PreflightError):                        # la VUE brute est bien aliasée
        assert_no_aliasing(logits, pop.H.numpy())
    assert assert_no_aliasing(logits.copy(), pop.H.numpy()) is True
    assert 0 <= _GRAB_NODE_T < pop.O


# ---------------------------------------------------------------- _verdict_decomposition (P2.3)

_NM, _N, _NIN, _NOUT = 4, 40, 8, 8


def _gt_triples(kind, n=400, noise=0.0, seed=0):
    """Triplets à VÉRITÉ-TERRAIN pour `tools/g_bilinear_probe`.

    `lineaire`   : H' = H + c_a          (delta CONSTANT par action, aucune dépendance en H)
    `bilineaire` : H' = H + H @ A_a      (dépendance LINÉAIRE EN H, par action)

    `g_learned` simule ce qu'un g LINÉAIRE peut capturer : le vrai c_a en régime linéaire (donc
    prédicteur exact), zéro en régime bilinéaire (donc incapable). C'est exactement le rôle que joue
    `tr["g_learned"]` dans `main_bilinear_check`."""
    rng = np.random.default_rng(seed)
    C = {a: rng.normal(0, 0.30, _N) for a in range(_NM)}
    A = {a: rng.normal(0, 0.05, (_N, _N)) for a in range(_NM)}
    tri = []
    for i in range(n):
        a = i % _NM
        H = rng.normal(0, 1.0, _N)
        d = C[a] if kind == "lineaire" else H @ A[a]
        Hn = H + d + (rng.normal(0, noise, _N) if noise else 0.0)
        tri.append({"H_prev": H, "H_next": Hn, "move": a,
                    "g_learned": C[a] if kind == "lineaire" else np.zeros(_N)})
    return tri


def _decompose(tri):
    """Rejoue EXACTEMENT le pipeline de `main_bilinear_check` sur des triplets fournis."""
    from tools.g_bilinear_probe import (_split_temporal, _fit_bilinear, _ratios_for_predictor,
                                        _verdict_decomposition, _hidden_idx, _median)
    tr, te = _split_temporal(tri, _NM, 0.7)
    W = _fit_bilinear(tr, _NM, _N, 1.0)
    hid = _hidden_idx(_N, _NIN, _NOUT)
    L = lambda t: t["g_learned"]                                   # noqa: E731
    B = lambda t: t["H_prev"] @ W[t["move"]]                       # noqa: E731
    lh = _ratios_for_predictor(te, L, idx=hid)
    bh = _ratios_for_predictor(te, B, idx=hid)
    return (_verdict_decomposition(_ratios_for_predictor(te, L), _ratios_for_predictor(te, B), lh, bh),
            _median(lh), _median(bh))


def test_decomposition_recovers_a_bilinear_ground_truth():
    """CONTRÔLE POSITIF : sur un système bilinéaire PAR CONSTRUCTION, l'instrument doit le dire."""
    v, mlh, mbh = _decompose(_gt_triples("bilineaire"))
    assert v == "LATENT_BILINEAR", f"verdict {v} (learned={mlh:.3f}, bilin={mbh:.3f})"
    assert mbh < 0.1 and mlh > 0.9


def test_decomposition_is_not_a_tautology_on_a_linear_ground_truth():
    """LE CONTRÔLE QUI DÉCIDE (manquait — classe E1). Le fit bilinéaire a N² paramètres par action
    contre N pour le linéaire : s'il gagnait mécaniquement par surajustement, la fonction ne pourrait
    JAMAIS rendre autre chose que LATENT_BILINEAR, et la prémisse de la tétralogie G4
    (PLAN-001/002/003/004) serait une tautologie.

    Mesuré : sur un système authentiquement linéaire, le bilinéaire est PIRE que la ligne de base
    (~1.59 > 1.0) — ridge + découpage temporel tiennent. L'instrument discrimine."""
    v, mlh, mbh = _decompose(_gt_triples("lineaire"))
    assert v == "LATENT_LINEAR", f"verdict {v} (learned={mlh:.3f}, bilin={mbh:.3f})"
    assert mlh < 0.1, "le prédicteur linéaire exact devrait être quasi parfait"
    assert mbh > mlh, "le bilinéaire NE DOIT PAS battre le linéaire sur un système linéaire"


def test_decomposition_degrades_monotonically_with_noise():
    """MONOTONIE : quand le bruit noie la structure, la fidélité doit se dégrader vers 1.0 (ligne de
    base). Un instrument dont le verdict ne bouge pas avec la dose mesure autre chose."""
    ratios = [_decompose(_gt_triples("bilineaire", noise=s))[2] for s in (0.0, 0.05, 0.3)]
    assert ratios[0] < ratios[1] < ratios[2], f"non monotone en le bruit : {ratios}"
    assert ratios[2] > 0.5, "à fort bruit, la fidélité devrait s'effondrer vers la ligne de base"


# ---------------------------------------------------------------------------------------------------
# P2.0 — `_mamba_survival_eras` : contrôle POSITIF + dose-réponse (régime S2-009, réponse connue).
#
# Motivation : WARM-002 a conclu « paysage de fitness PLAT » d'un ratio intact/ablé ≈ 1.00 alors que son
# bras intact survivait 5.0-7.2 ticks — SOUS le plancher no-perception (9.0). Un ratio lu sur un bras au
# plancher vaut 1.0 par CONSTRUCTION. Ces deux tests rendent cette confusion impossible à répéter : le
# premier prouve que le banc SAIT produire un positif, le second que la fitness récompense la compétence
# PARTIELLE — donc qu'un ratio plat ne peut plus être imputé au monde sans vérifier le plancher.
# ---------------------------------------------------------------------------------------------------

_S2_009_RATIO = 21.05        # ratio publié par EDR-S2-009 au régime metab=0.75 / cog=12.0, seed 2026
_FLOOR = 9.0                 # survie de l'oracle privé de perception, à ce régime


def _oracle_eras(intact_cls, ablated_cls=None, K=3):
    from tools.cognitive_demand_inworld import CognitiveOracleAblated
    from tools.warmstart_evolution_inworld import _mamba_survival_eras
    kw = dict(seed=2026, K=K, num_agents=12, max_ticks=200, metab=0.75, cog=12.0,
              intact_cls=intact_cls, ablated_cls=ablated_cls or CognitiveOracleAblated)
    return _mamba_survival_eras(None, False, **kw), _mamba_survival_eras(None, True, **kw)


def test_mamba_bench_reproduces_the_known_oracle_ratio():
    """CONTRÔLE POSITIF (générateur A du pré-vol : l'instrument peut-il produire LES DEUX issues ?).

    L'oracle lecteur-de-signal de S2-009 a une réponse CONNUE : ratio 21.05. Si ce banc rend ~1.0 avec
    une politique parfaite, aucun NEUTRAL qu'il produit n'est interprétable. Mesuré : 22.2×."""
    from tools.cognitive_demand_inworld import CognitiveOracleBatchModel
    from tools.demand_marker import ablation_verdict
    intact, ablated = _oracle_eras(CognitiveOracleBatchModel)
    ratio = ablation_verdict(intact, ablated)["ratio"]
    assert ratio > 10.0, f"le banc ne reproduit PAS le positif connu (ratio={ratio:.2f}, attendu ~{_S2_009_RATIO})"
    assert abs(np.median(ablated) - _FLOOR) <= 2.0, f"plancher dérivé : {np.median(ablated)} (attendu ~{_FLOOR})"


def test_fitness_rewards_partial_competence_so_the_landscape_is_not_flat():
    """RÉFUTE le MÉCANISME de WARM-002 : « un suiveur-de-signal PARTIEL survit AUSSI PEU qu'un
    non-suiveur ; la survie ne récompense qu'au-delà de ~99 % d'accuracy ».

    Mesuré (K=12) : 9.0 → 12.0 → 17.5 → 37.0 → 94.2 → 200.0 pour p = 0 → 1, strictement monotone, sans
    chevauchement d'ères à AUCUNE marche. La récompense existe dès le premier incrément de fidélité.
    ⚠️ PORTÉE : gradient dans l'espace des COMPORTEMENTS (oracle paramétré). Ne dit RIEN de
    l'atteignabilité par mutation de `genome.W` — c'est la question ouverte que ce résultat ouvre."""
    from tools.warmstart_evolution_inworld import _mamba_survival_eras
    from tools.ground_truth_worlds import partial_oracle
    med = [float(np.median(_mamba_survival_eras(
        None, False, seed=2026, K=3, num_agents=12, max_ticks=200, metab=0.75, cog=12.0,
        intact_cls=partial_oracle(p)))) for p in (0.0, 0.5, 1.0)]
    assert med[0] < med[1] < med[2], f"non monotone en la fidélité : {med}"
    assert med[1] > med[0] * 1.5, (
        f"compétence PARTIELLE non récompensée ({med[0]:.1f} -> {med[1]:.1f}) : WARM-002 aurait raison")


def test_mamba_seam_defaults_preserve_historical_behaviour():
    """Le seam `intact_cls`/`ablated_cls` a été ajouté à un instrument PARTAGÉ. Ses défauts encodent
    tout l'arc WARM : les changer réécrirait silencieusement des mesures publiées."""
    import inspect
    from tools.s2_demand_ablation import PerceptionAblatedMamba
    from tools.warmstart_evolution_inworld import _mamba_survival_eras
    p = inspect.signature(_mamba_survival_eras).parameters
    assert p["intact_cls"].default is None
    assert p["ablated_cls"].default is PerceptionAblatedMamba


def test_linear_sanity_reproduces_its_known_positive_control():
    """CALIBRATION de `run_linear_sanity` (dette P2.8). L'oracle linéaire décode le signal PAR
    CONSTRUCTION : sa réponse est connue, il DOIT écraser sa propre ablation. Si ce banc rendait un
    ratio ~1, aucun chiffre de la variante `cog_linear` ne serait interprétable.

    Cet instrument est né aujourd'hui — et il est entré dans le dépôt SANS que le cliquet bronche,
    parce que l'heuristique de détection ne couvrait pas le suffixe `_sanity`. Le motif est élargi, et
    ce cas existe pour que la fonction ne reste pas la dette qu'elle vient de révéler.
    Mesuré au n complet (K=12) : oracle 200.0 / plancher 13.5 / ratio 14.81 / X_DEMANDED."""
    from tools.cognitive_demand_inworld import run_linear_sanity
    r = run_linear_sanity(seed=2026, K=2, num_agents=6, max_ticks=60)
    assert r["oracle_median"] >= 3.0 * r["floor_median"], (
        f"contrôle positif NON reproduit : oracle {r['oracle_median']} vs plancher {r['floor_median']}")
    assert r["floor_median"] > 0.0, "plancher dégénéré : l'ablation tue instantanément"


def _cog_mode(cd, K=2, agents=6, ticks=60):
    """Rejoue les deux bras d'un mode de `run_cog_demand_map` au régime PUBLIÉ par EDR-S2-009
    (metab=0.75, cog=12.0) — et NON aux défauts de signature (4.0/6.0), qui ne correspondent à aucun
    chiffre gravé."""
    from src.worlds.world_1_stoneage import Biosphere3D
    from tools.s2_demand import run_condition
    from tools.demand_marker import ablation_verdict
    from tools.cognitive_demand_inworld import CognitiveOracleBatchModel, CognitiveOracleAblated

    def world():
        e = Biosphere3D()
        e.config.cognitive_demand = cd
        e.config.cog_gain, e.config.base_metabolism, e.config.forage_payoff = 12.0, 0.75, 0.0
        return e
    i = run_condition(world, CognitiveOracleBatchModel, None, 2026, num_agents=agents,
                      max_ticks=ticks, n_eras=K)
    a = run_condition(world, CognitiveOracleAblated, None, 2026, num_agents=agents,
                      max_ticks=ticks, n_eras=K)
    return i["era_survival"], a["era_survival"], ablation_verdict(i["era_survival"],
                                                                 a["era_survival"], ceiling=float(ticks))


def test_cog_demand_map_on_mode_reproduces_the_published_positive_control():
    """CALIBRATION de `run_cog_demand_map` (P2.10) — l'instrument qui a produit le **ratio 21.05 de
    EDR-S2-009**, pierre angulaire du « le monde EXIGE la perception », cité par tout l'arc WARM et par
    S2-010/011. Il est resté INVISIBLE au cliquet jusqu'au 2026-07-21 (suffixe `_map` hors motif).

    Le bras ON est un vrai contrôle positif : l'oracle décode le signal par construction, son ablation
    doit effondrer la survie. Mesuré au n complet : 200.0 vs 9.0, ratio 22.22, `X_DEMANDED`, amplitude
    réelle (bras NON identiques, non dégénéré)."""
    intact, ablated, v = _cog_mode(True)
    assert v["ratio"] >= 3.0, f"contrôle positif NON reproduit : ratio {v['ratio']:.2f}"
    assert not v["degenerate"], f"bras ON dégénéré : {v['why']}"
    assert intact != ablated, "le bras ON doit avoir de l'amplitude"


def test_cog_demand_map_off_mode_null_is_degenerate_not_measured():
    """LE CAS QUI CORRIGE S2-009. Son contrôle NÉGATIF (« OFF → ratio 1.00 NEUTRAL ») est un **no-op
    LITTÉRAL** : en mode OFF, `forage_payoff = 0` et aucune nourriture cognitive → tout le monde meurt à
    ~7 ticks quoi qu'il fasse. Mesuré à K=12 : intact et ablé **bit à bit identiques sur les 12 ères**.

    Le ratio 1.00 ne montre donc PAS « le marqueur reste inerte quand la perception ne paie pas », mais
    « le marqueur rend 1.00 quand la métrique est morte ». Un vrai contrôle négatif exige un monde où les
    agents SURVIVENT et où la perception ne paie pas — ce que fournissent S2-001, LANG-006 et MEM-001.

    Ce test PINNE la dégénérescence pour qu'elle ne repasse plus pour un résultat, et vérifie du même
    coup que la garde armée (EDR-AUDIT-001) l'attrape sur des données de PRODUCTION, pas une fixture."""
    intact, ablated, v = _cog_mode(False)
    assert intact == ablated, f"les bras OFF devraient être identiques : {intact} vs {ablated}"
    assert v["degenerate"], f"la garde ne détecte plus la dégénérescence de OFF : {intact} vs {ablated}"


def test_underpowered_masks_degenerate_in_the_verdict_but_not_in_the_field():
    """SUBTILITÉ D'ORDRE, trouvée en écrivant le test précédent. `ablation_verdict` teste `n >= n_floor`
    AVANT la garde de dégénérescence : à petit n, des bras bit-identiques sortent en `INCONCLUSIVE`
    (sous-puissant) et non `INCONCLUSIVE_DEGENERATE`. **Sous-puissance et dégénérescence sont deux
    défauts distincts, et le premier MASQUE le second dans le verdict** — le champ `degenerate` reste
    vrai, c'est lui qu'il faut lire.

    Valeurs de la mesure RÉELLE à K=12 (mode OFF, régime publié S2-009) utilisées comme fixture."""
    from tools.demand_marker import ablation_verdict
    off = [7.0] * 8 + [6.5] + [7.0] * 3                   # mesuré : intact et ablé identiques
    petit = ablation_verdict(off[:2], off[:2])
    assert petit["verdict"] == "INCONCLUSIVE" and petit["degenerate"] is True
    complet = ablation_verdict(off, list(off))
    assert complet["verdict"] == "INCONCLUSIVE_DEGENERATE", (
        "au n complet, un nul sur bras identiques DOIT être marqué dégénéré")


# ---------------------------------------------------------------- branche `perception` (P2.1)
# Le trou le PLUS ANCIEN du cliquet : cette branche porte les ratios publiés de WARM-001 (1.6→2.1) et
# WARM-003 (5.04) et n'avait aucun cas. Étalon = `GroundTruthPerceptionWorld`, dose = `cog_gain`.

_PERC_INCOME = 10.0        # point de fonctionnement MESURÉ : dose 0 -> survie ~19 (au-dessus du plancher
                           # 9), dose 12 -> ~179 (sous le plafond 200). Voir la note de fenêtre ci-dessous.


def _perc(dose, ablate, K=2, income=_PERC_INCOME):
    from tools.ground_truth_worlds import make_perception_world
    g = _load(os.path.join("results", "warm003_dagger_genome.npz"))
    return _torch_survival_eras(g, ablate, 2026, K, 12, 200, 0.75, dose,
                                ablate_kind="perception",
                                world_cls=make_perception_world(dose, income=income))


def _perc_ratio(dose, K=2):
    from tools.demand_marker import ablation_verdict
    i, a = _perc(dose, False, K), _perc(dose, True, K)
    return ablation_verdict(i, a, ceiling=200.0), float(np.median(i))


def test_perception_ablation_is_inert_when_perception_pays_nothing():
    """SPÉCIFICITÉ, et le piège qu'il fallait éviter. À `cog_gain = 0` la perception ne rapporte rien :
    l'ablation doit être INERTE. Mais un ratio ~1 ne vaut que si la métrique est VIVANTE — sinon c'est
    la dégénérescence de WARM-002, pas une inertie.

    D'où `gt_income` : un revenu corporel plat, obs-INDÉPENDANT. Mesuré à ce point de fonctionnement :
    survie 19.5 (plancher de référence 9.0, plafond 200) et ratio 0.96."""
    v, med = _perc_ratio(0.0)
    assert 12.0 < med < 195.0, f"métrique NON vivante à dose 0 (médiane {med:.1f}) : test sans valeur"
    assert 0.7 <= v["ratio"] <= 1.4, f"ablation NON inerte alors que la perception ne paie rien : {v['ratio']:.2f}"


def test_perception_ablation_collapses_when_perception_pays():
    """CONTRÔLE POSITIF. À dose 6, l'ablation doit effondrer la survie. Mesuré : 126.5 → 29.8 (4.25×)."""
    v, med = _perc_ratio(6.0)
    assert v["ratio"] >= 2.0, f"pas d'effondrement alors que la perception paie : {v['ratio']:.2f}"
    assert med > 12.0, "bras intact au plancher : l'effondrement ne serait pas interprétable"


def test_perception_ratio_is_monotone_only_while_uncensored():
    """DIRECTION — et sa LIMITE, mesurée plutôt que supposée.

    Le ratio croît avec la dose TANT QUE le bras intact reste sous `max_ticks` : 0.96 → 2.64 → 4.25 pour
    dose 0 → 3 → 6. Au-delà il **redescend** (3.14 à dose 12) parce que l'intact plafonne à ~179/200 et
    ne peut plus monter, alors que l'ablé continue de croître (un agent dérangé touche parfois juste).

    ⚠️ CONSÉQUENCE POUR LES CHIFFRES PUBLIÉS : tout ratio de cette branche dont le bras intact frôle
    `max_ticks` est une **borne INFÉRIEURE compressée**, pas une amplitude. C'est ce que signale le champ
    `censored` de `ablation_verdict`. Même phénomène que la cellule positive de S2-007 (EDR-AUDIT-001)."""
    r = [_perc_ratio(d)[0]["ratio"] for d in (0.0, 3.0, 6.0)]
    assert r[0] < r[1] < r[2], f"non monotone dans la plage NON censurée : {r}"
    assert r[0] < 1.5 and r[2] > 2.0, f"amplitude insuffisante pour conclure : {r}"


# ------------------------------------------------------- verdict_cognition_body (contrôle positif)
# LE CONTRÔLE QUI MANQUAIT AU VERDICT FONDATEUR. `champion_body` (EDR-S2-012) conclut « la survie vient
# du CORPS, RIEN de la cognition » — la moitié NULLE de ce verdict n'avait aucun contrôle positif
# in-world, exactement le défaut reproché à WARM-002 et à S2-006 par EDR-AUDIT-001.
# Premier instrument de `src/` calibré (le scan y a été étendu le 2026-07-21).

def test_cognition_body_verdict_can_return_cognition_when_cognition_pays():
    """Régime `cognitive_demand` CALIBRÉ (P2.10 : oracle 200 vs plancher 9). On remplace la cellule
    `champion` par une politique DONT ON SAIT qu'elle utilise sa cognition — l'oracle lecteur-de-signal.
    Génomes tous FRAIS, donc aucun avantage corporel : la bonne réponse est COGNITION, pas BODY.

    Mesuré au n complet (K=12, 12 agents, 200 ticks) : oracle 200.0 / actions random 7.0 ;
    verdict COGNITION, policy p=0.0025 cliff=1.000, body p=1 cliff=0.000.

    ⚠️ Ce que ce cas établit et ce qu'il n'établit PAS : il prouve que l'instrument DISCRIMINE (le
    verdict BODY de champion_body n'est pas une incapacité). Il ne corrige pas les quatre
    affaiblissements de EDR-S2-012 (« 5/5 » qui vaut 4, life_score à 2/5 sous Holm, p au plancher du
    test, bras `body` between-subject)."""
    from src.agents.baseline_models import RandomActionBatchModel
    from src.seed_ai.s2_stats import verdict_cognition_body
    from tools.s2_demand import run_condition
    from tools.cognitive_demand_inworld import CognitiveOracleBatchModel
    from tools.warmstart_evolution_inworld import make_cog_world

    w, K, ag, t = make_cog_world(0.75, 12.0), 12, 6, 60
    kw = dict(num_agents=ag, max_ticks=t, n_eras=K)
    cog = run_condition(w, CognitiveOracleBatchModel, None, 2026, **kw)
    body = run_condition(w, RandomActionBatchModel, None, 2026, **kw)
    rgen = run_condition(w, None, None, 2026, **kw)
    ract = run_condition(w, RandomActionBatchModel, None, 2026, **kw)

    assert np.median(cog["survival"]) > 3.0 * np.median(body["survival"]), (
        "le régime ne fait pas payer la cognition : le contrôle positif n'a pas d'objet")
    v = verdict_cognition_body(cog, body, rgen, ract, metric="survival")
    assert v["verdict"] == "COGNITION", (
        f"l'instrument ne SAIT PAS rendre COGNITION quand la cognition paie (rendu : {v['verdict']}) — "
        f"tout verdict BODY qu'il produit serait alors ininterprétable")
    assert v["policy_sig"] is True and v["body_sig"] is False, (
        "avec des génomes tous FRAIS, aucun avantage corporel ne doit être crédité")


# ---------------------------------------------------------------- dose_response_verdict (P2.2)
# L'instrument qui a produit EDR-095 (« le rêve forcé RÉDUIT causalement la survie »), porté par SDR-G4.
# Défaut RÉEL trouvé et corrigé : une paire doublement ÉTEINTE rendait `0 / 1e-6 = 0.0`, survivait au
# filtre `r != 1.0` et comptait comme DÉFAVORABLE au rêve.

def _dose(off, deep):
    from tools.dream_causal_probe import dose_response_verdict
    return dose_response_verdict({"off": off, 8: deep})


def test_dose_response_identical_arms_are_neutral():
    """SPÉCIFICITÉ (cas sain) : deux bras identiques NON nuls ne peuvent pas produire d'effet."""
    assert _dose([5.0] * 10, [5.0] * 10)["verdict"] == "NEUTRE"


def test_dose_response_doubly_extinct_pairs_cannot_manufacture_a_verdict():
    """LE BUG RÉEL (classe E1). Mesuré AVANT correctif : deux bras **strictement identiques et
    éteints** rendaient `CAUSE_NUISIBLE, ratio 0.0, sign_p 0.00195` — l'instrument déclarait le rêve
    nuisible avec forte confiance sur deux tableaux littéralement égaux.

    Une paire dont les DEUX bras sont à zéro ne porte aucune information : c'est une égalité, pas un
    argument contre le rêve."""
    v = _dose([0.0] * 10, [0.0] * 10)
    assert v["verdict"] == "INCONCLUSIVE_DEGENERATE", (
        f"un verdict est FABRIQUÉ à partir de bras identiques : {v['verdict']} (ratio {v['ratio']})")
    assert v["n_ecartees"] == 10


def test_dose_response_extinct_pairs_no_longer_poison_a_real_benefit():
    """LE BUG DANS L'AUTRE SENS, et c'est celui qu'on aurait pu ne jamais voir. Sur un jeu où le rêve
    aide dans 4 paires informatives sur 4, six paires éteintes empoisonnaient la MÉDIANE (ratio 0.0 au
    lieu de 1.40) et gonflaient le dénominateur du test de signe. Le défaut pouvait donc aussi MASQUER
    un bénéfice réel."""
    v = _dose([0.0] * 6 + [5.0] * 4, [0.0] * 6 + [7.0] * 4)
    assert v["ratio"] == pytest.approx(1.40, rel=0.02), f"médiane encore empoisonnée : {v['ratio']}"
    assert v["n"] == 4 and v["n_ecartees"] == 6


def test_dose_response_can_produce_both_issues():
    """GÉNÉRATEUR A DU PRÉ-VOL : l'instrument peut-il rendre LES DEUX issues ? Ce n'était pas établi.
    Vérifié : bénéfique quand le rêve aide, nuisible quand il nuit."""
    assert _dose([5.0] * 10, [7.0] * 10)["verdict"] == "CAUSE_BENEFIQUE"
    assert _dose([5.0] * 10, [3.0] * 10)["verdict"] == "CAUSE_NUISIBLE"


def test_dose_response_reproduces_edr095_on_its_published_values():
    """NON-RÉGRESSION SUR LA CONCLUSION PUBLIÉE. EDR-095 rapporte `ratio(Kmax/off) = 0.543`,
    `sign_p = 0.00195`, avec `off ∈ [0.113, 0.165]` et bras forcés `∈ [0.055, 0.090]` — **séparation
    parfaite, AUCUN zéro**, donc aucune paire éteinte : le correctif ne peut pas la changer.

    On ne peut l'affirmer que parce que ce record a publié ses VALEURS ABSOLUES — ce que S2-009
    n'avait pas fait (cf. EDR-AUDIT-001)."""
    v = _dose([0.128] * 10, [0.070] * 10)
    assert v["verdict"] == "CAUSE_NUISIBLE"
    assert v["ratio"] == pytest.approx(0.547, rel=0.02)      # publié : 0.543
    assert v["sign_p"] == pytest.approx(0.00195, rel=0.02)   # publié : 0.00195
    assert v["n_ecartees"] == 0, "les données d'EDR-095 ne contiennent aucune paire éteinte"


# ---------------------------------------------------------------- ablation_verdict (P2.4)
# L'instrument le plus central du graphe : REF-DEMAND-MARKER l'adopte et ~20 records en dépendent.
# Étalon DÉJÀ ÉCRIT (`tools/world_demand_marker_probe.py`) : DEMANDING (l'obs porte l'info) vs
# TRIVIAL (l'obs est un leurre). Pur numpy, aucun monde, aucun bail.

def _wdm(demanding, K=4, seed=0, gain=0.4, metab=0.5, iters=400, episodes=6, ticks=200, n_eval=40):
    """Rejoue l'étalon à un régime SORTI DU PLAFOND (`gain < metab` : même un lecteur parfait décline).

    ⚠️ POURQUOI PAS LES DÉFAUTS : à `gain=1.0 / metab=0.5`, les deux bras de TRIVIAL sont à **200/200**,
    le cap de `ticks`. Le ratio 1.00 y serait lu sur une métrique SATURÉE — si l'ablation nuisait un
    peu, le plafond le masquerait. Ici TRIVIAL vit à ~101 et DEMANDING à ~46 : la spécificité est
    démontrée sur une métrique VIVANTE."""
    from tools.world_demand_marker_probe import survive
    rng = np.random.RandomState(seed)
    W, b = np.zeros((K, K)), np.zeros(K)

    def sc(W, b):
        return np.mean([survive(demanding, W, b, "true", K, np.random.RandomState(seed + 100 + e),
                                ticks, 10.0, gain, metab) for e in range(episodes)])

    best, step = sc(W, b), 0.6
    for i in range(iters):
        Wc, bc = W + step * rng.randn(K, K), b + step * rng.randn(K)
        s = sc(Wc, bc)
        if s > best:
            W, b, best = Wc, bc, s
        elif i % 60 == 59:
            step *= 0.85
    ev = np.random.RandomState(seed + 500)

    def med(mode):
        return [survive(demanding, W, b, mode, K, np.random.RandomState(ev.randint(1 << 30)),
                        ticks, 10.0, gain, metab) for _ in range(n_eval)]
    return med("true"), med("random"), float(np.abs(W).sum())


def test_ablation_verdict_detects_demand_on_the_demanding_ground_truth():
    """CONTRÔLE POSITIF sur vérité-terrain : dans DEMANDING l'obs révèle l'action nourricière, donc la
    randomiser DOIT effondrer la survie. Mesuré hors plafond : 46.0 → 25.0 (ratio 1.84), |W| ≈ 35.9
    (politique réellement ENTRAÎNÉE, pas un W gelé)."""
    from tools.demand_marker import ablation_verdict
    intact, ablated, wnorm = _wdm(True)
    assert wnorm > 1.0, f"la politique n'a pas appris à peser l'obs (|W|={wnorm:.3f})"
    v = ablation_verdict(intact, ablated, ceiling=200.0, intervention_verified=True)
    assert v["verdict"] == "X_DEMANDED", f"demande NON détectée sur le monde qui l'impose : {v}"
    assert not v["degenerate"], v["why"]


def test_ablation_verdict_stays_null_on_the_trivial_ground_truth():
    """SPÉCIFICITÉ sur vérité-terrain : dans TRIVIAL l'obs est un LEURRE, donc la randomiser ne doit
    RIEN changer. Mesuré hors plafond : 101.0 vs 101.0, ratio 1.00, métrique VIVANTE (pas au cap 200).

    `|W| = 0.000` est ici la bonne réponse et NON un artefact d'optimiseur (contraste avec S2-004) :
    une politique optimale doit ignorer une obs non informative."""
    from tools.demand_marker import ablation_verdict
    intact, ablated, wnorm = _wdm(False)
    assert 20.0 < float(np.median(intact)) < 195.0, "métrique au plancher ou au plafond : test sans valeur"
    v = ablation_verdict(intact, ablated, ceiling=200.0, intervention_verified=True)
    assert v["verdict"] == "X_DECOY", f"leurre pris pour une demande : {v}"
    assert wnorm == pytest.approx(0.0, abs=1e-9)


def test_identical_arms_need_the_intervention_to_be_verified():
    """NUANCE TROUVÉE PAR CETTE CALIBRATION, le jour même où la garde a été armée. Des bras identiques
    ont DEUX causes opposées, indiscernables depuis les SORTIES :
      (a) l'intervention ne s'est PAS appliquée (S2-007 matrice identité, S2-004 W gelé) -> à bloquer ;
      (b) elle s'est appliquée et n'a rien fait (TRIVIAL : l'obs EST randomisée, la politique l'ignore)
          -> X_DECOY LÉGITIME, et c'est la vérité-terrain qui VALIDE le marqueur.
    Bloquer (b) reviendrait à refuser le nul là où le nul est la bonne réponse. La garde exige donc que
    l'appelant atteste avoir vérifié la perturbation de l'ENTRÉE."""
    from tools.demand_marker import ablation_verdict
    ident = [101.0] * 12
    assert ablation_verdict(ident, list(ident))["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert ablation_verdict(ident, list(ident), intervention_verified=True)["verdict"] == "X_DECOY"


# ---------------------------------------------------------------- bundle Lewis (P2.6)
# `_verdict_drain` / `_verdict_bio` : mappings PURS (décomposition énergétique -> nom du coupable).
# Aucun monde, aucun bail. Le test qui compte : peuvent-ils rendre CHAQUE branche, et la bascule
# METABOLISME -> CARRY tombe-t-elle exactement là où l'arithmétique le dit ?

def _phases(brain=0.0, action=0.0, biologie=0.0, mouvement=0.0):
    net = brain + action + biologie + mouvement
    return {"brain": brain, "action": action, "biologie": biologie,
            "mouvement": mouvement, "net": net}


def _bio(metab=0.0, terrain=0.0, carry=0.0, autres=0.0):
    return {"bio_metab": metab, "bio_terrain": terrain, "bio_carry": carry, "bio_autres": autres}


def test_drain_verdict_can_name_every_culprit():
    """GÉNÉRATEUR A : l'instrument peut-il rendre TOUTES ses issues ? Un mapping qui ne sait désigner
    qu'un seul coupable ne diagnostique rien. Les 4 phases + la branche diffuse doivent être
    atteignables."""
    from tools.lewis_survival_sweep import _verdict_drain
    assert _verdict_drain(_phases(action=8.0, biologie=1.0)) == "TARIF=THROW"
    assert _verdict_drain(_phases(biologie=8.0, action=1.0)) == "TARIF=BIOLOGIE"
    assert _verdict_drain(_phases(brain=8.0, action=1.0)) == "TARIF=BRAIN"
    assert _verdict_drain(_phases(mouvement=8.0, action=1.0)) == "TARIF=MOUVEMENT"
    assert _verdict_drain(_phases(action=2.0, biologie=2.0, brain=2.0)) == "DRAIN DIFFUS"
    assert _verdict_drain(_phases()) == "DRAIN DIFFUS"                       # net <= 0


def test_drain_verdict_threshold_is_strictly_above_half():
    """LA FRONTIÈRE, vérifiée au lieu d'être supposée. Le seuil est `> 0.5` STRICT : une phase qui porte
    exactement la moitié du drain ne nomme PAS de coupable. Un partage 50/50 est diffus par définition —
    c'est ce qui rend le verdict interprétable."""
    from tools.lewis_survival_sweep import _verdict_drain
    assert _verdict_drain(_phases(action=5.0, biologie=5.0)) == "DRAIN DIFFUS"
    assert _verdict_drain(_phases(action=5.01, biologie=4.99)) == "TARIF=THROW"


def test_bio_verdict_switches_at_the_analytic_carry_metab_crossover():
    """LA BASCULE CALCULABLE EXACTEMENT (celle que la docstring de `GroundTruthCarryWorld` annonçait
    sans jamais l'asserter). L'étalon impose `metab` et `carry` par tick : à `gt_carry == gt_metab`, le
    drain biologie est partagé 50/50, donc **aucun** coupable (> 0.5 strict) ; dès que `carry` dépasse
    `metab`, le verdict bascule sur CARRY, et inversement."""
    from tools.lewis_survival_sweep import _verdict_bio
    m = 1.0
    assert _verdict_bio(_bio(metab=m, carry=m)) == "DRAIN BIO DIFFUS"          # exactement à la bascule
    assert _verdict_bio(_bio(metab=m, carry=m * 1.05)) == "TARIF=CARRY"        # carry passe devant
    assert _verdict_bio(_bio(metab=m * 1.05, carry=m)) == "TARIF=METABOLISME"  # metab passe devant


def test_bio_verdict_gains_do_not_create_a_culprit():
    """`bio_autres` porte les GAINS et n'est pas une cible de tarif — mais il entre au dénominateur.
    Conséquence à connaître : un gain important DILUE les parts et pousse vers DIFFUS. Le vérifier
    évite de lire « drain diffus » comme « rien ne domine » alors que c'est « un revenu masque »."""
    from tools.lewis_survival_sweep import _verdict_bio
    assert _verdict_bio(_bio(metab=8.0, carry=1.0)) == "TARIF=METABOLISME"
    assert _verdict_bio(_bio(metab=8.0, carry=1.0, autres=10.0)) == "DRAIN BIO DIFFUS"
    assert _verdict_bio(_bio(metab=1.0, autres=-2.0)) == "DRAIN BIO DIFFUS"    # bio_net <= 0


# ---------------------------------------------------------------- compute_ab_verdict (P2.5)
# Débloqué le 2026-07-21 (fin des sessions parallèles). Fonction PURE : diffs appariés -> verdict.
# `sign_p` était calculé, renvoyé, affiché — et ne conditionnait RIEN.

def _ab(diffs, **kw):
    from tools.substrate_ab import compute_ab_verdict
    return compute_ab_verdict([{"diff": d} for d in diffs], **kw)


def test_ab_verdict_requires_the_sign_test_not_just_the_band():
    """LES TROIS CAS MESURÉS AVANT CORRECTIF — tous rendaient `GRADIENT_GAGNE` :
      (a) 6 favorables sur 11 avec **`sign_p = 1.000`** : le test de signe dit « aucune preuve,
          absolument », et le verdict disait « le gradient gagne » ;
      (b) **n = 2** suffisait, pourvu que la médiane dépasse la bande ;
      (c) médiane 0.021 (à peine au-dessus de `band=0.02`) contre deux contre-exemples de −0.5.
    Générateur de FAUX POSITIFS pur — dont le garde-fou était déjà dans la fonction, débranché."""
    assert _ab([0.03, -0.02, 0.04, -0.03, 0.05, -0.01, 0.03, -0.02, 0.04, -0.02, 0.03])["verdict"] == "NEUTRE"
    assert _ab([0.5, 0.5])["verdict"] == "NEUTRE"
    assert _ab([0.021] * 3 + [-0.5] * 2)["verdict"] == "NEUTRE"


def test_ab_verdict_still_fires_on_a_genuinely_powered_effect():
    """SPÉCIFICITÉ — sans ce bras, la garde pourrait tout rendre NEUTRE et paraître « sûre » en ne
    mesurant plus rien. Les DEUX directions doivent rester atteignables (générateur A)."""
    assert _ab([0.30, 0.25, 0.40, 0.32, 0.28, 0.35])["verdict"] == "GRADIENT_GAGNE"
    assert _ab([-0.30, -0.25, -0.40, -0.32, -0.28, -0.35])["verdict"] == "HEBBIEN_GAGNE"


def test_ab_verdict_needs_five_replicates_in_perfect_separation():
    """LA FRONTIÈRE, arithmétique et non négociable : `sign_p` vaut 0.25 à n=3 et 0.0625 à n=5. **Trois
    réplicats ne peuvent porter AUCUN verdict**, quelle que soit l'amplitude de l'effet.

    ⚠️ Ce point vaut d'être retenu : les **7** tests de câblage du dépôt qui touchaient cet instrument
    utilisaient tous `n=3` — la convention enseignait donc le défaut, en testant la plomberie à une
    taille qui ne peut rien porter, ce qui rendait invisible l'absence de garde de puissance."""
    assert _ab([0.5] * 3)["verdict"] == "NEUTRE"
    assert _ab([0.5] * 5)["verdict"] == "GRADIENT_GAGNE"


def test_ab_verdict_flags_underpowered_rather_than_hiding_it():
    """Un effet réel mais sous-puissant ne doit pas être confondu avec une absence d'effet : le champ
    `underpowered` distingue « la médiane dépasse la bande mais le signe ne suit pas » de « rien »."""
    faible = _ab([0.5] * 3)
    assert faible["verdict"] == "NEUTRE" and faible["underpowered"] is True
    vrai_nul = _ab([0.001, -0.001, 0.002, -0.002, 0.0, 0.001])
    assert vrai_nul["verdict"] == "NEUTRE" and vrai_nul["underpowered"] is False


# --- DREAM-005 : `measure_convergence` (sonde d'attracteur, tools/substrate_attractor_probe.py) -----
from tools.substrate_attractor_probe import measure_convergence  # noqa: E402


def _contractive_traj(rate, n=40, start=(1.0, 1.0)):
    """Système CONTRACTIF connu : H <- rate*H (rate<1) -> point fixe 0. Réponse connue : CONVERGE."""
    h = np.array(start, dtype=float)
    traj = [h.copy()]
    for _ in range(n):
        h = rate * h
        traj.append(h.copy())
    return traj


def _random_walk_traj(sigma, n=40, seed=0, start=(1.0, 1.0)):
    """Marche aléatoire CONNUE : H <- H + bruit -> jamais de point fixe. Réponse connue : NE CONVERGE PAS."""
    rng = np.random.RandomState(seed)
    h = np.array(start, dtype=float)
    traj = [h.copy()]
    for _ in range(n):
        h = h + rng.randn(2) * sigma
        traj.append(h.copy())
    return traj


def test_measure_convergence_contractive_converges():
    """Spécificité (+) : un système contractif connu est classé CONVERGE, pas de faux négatif."""
    assert measure_convergence(_contractive_traj(0.5))["converges"] is True


def test_measure_convergence_random_walk_does_not():
    """Spécificité (−) : une marche aléatoire connue N'EST PAS classée convergente. Sans ce contrôle,
    un détecteur toujours-vrai passerait le test contractif et fabriquerait le verdict « contractif »."""
    assert measure_convergence(_random_walk_traj(0.3))["converges"] is False


def test_measure_convergence_tail_step_monotone_in_contraction():
    """Monotonie (direction) : plus la contraction est forte (rate petit), plus le pas de queue est
    petit. La grandeur mesurée suit la dose imposée, pas seulement le verdict binaire."""
    tails = [measure_convergence(_contractive_traj(r))["tail_step"] for r in (0.9, 0.7, 0.5, 0.3)]
    assert tails == sorted(tails, reverse=True), f"non monotone : {tails}"


def test_measure_convergence_too_short_is_not_convergent():
    """Borne : une trajectoire plus courte que la fenêtre de queue ne peut RIEN affirmer -> non
    convergente par défaut (ne pas fabriquer un verdict sur trop peu de pas)."""
    assert measure_convergence([np.zeros(2), np.zeros(2)], tail=8)["converges"] is False


# --- EVO-002 : `measure_retention_separation` + `compute_enrichment_verdict` ------------------------
# (tools/evo_memory_enrichment.py). L'instrument de rétention est calibré PAR PRÉDICTION : sur un génome
# à W purement DIAGONAL (W_off=0), la dynamique sous entrée nulle est H_new=(1−δ)·H avec δ=sigmoid(diag
# clippé à [−10,10]) -> sep(D)=(1−δ)^D, sans paramètre libre. On vérifie aussi qu'il DISSOCIE ce que
# measure_convergence confond (δ→0 : « gelé » mais retient).
from tools.evo_memory_enrichment import (  # noqa: E402
    measure_retention_separation, compute_enrichment_verdict, I_DIM, O_DIM)
from src.seed_ai.rl_evolution import recurrent_forward  # noqa: E402

_N_RET = I_DIM + O_DIM + 3


def _diag_genome(c):
    """Génome à W DIAGONAL pur (W_off=0) : forget-gate uniforme δ=sigmoid(clip(c,−10,10)), aucune
    interaction récurrente -> sep(D) = (1−δ)^D exactement (réponse CONNUE)."""
    W = np.zeros((_N_RET, _N_RET), dtype=np.float32)
    np.fill_diagonal(W, c)
    return Genome(W, I_DIM, O_DIM)


def _delta(c):
    return 1.0 / (1.0 + np.exp(-max(-10.0, min(10.0, c))))   # forget-gate, AVEC le clip de recurrent_forward


def test_retention_separation_matches_prediction():
    """CALIBRATION PRINCIPALE, par PRÉDICTION : sep(D) mesuré = (1−δ)^D prédit depuis le forget-gate, sur
    plusieurs doses δ et délais D, sans paramètre libre. Un instrument qui suit sa prédiction analytique
    ne fabrique pas son résultat."""
    for c in (-2.0, 0.0, 2.0):
        for D in (2, 3, 5):
            pred = (1.0 - _delta(c)) ** D
            got = measure_retention_separation(_diag_genome(c), D, n_pairs=48, seed=0)
            assert got == pytest.approx(pred, rel=0.05, abs=1e-3), \
                f"NON CALIBRÉ à c={c} D={D} : mesuré {got:.5f} vs prédit {pred:.5f}"


def test_retention_separation_poles():
    """Deux pôles CONNUS : δ→0 (c très négatif) -> RETIENT (sep≈1) ; δ→1 & W_off=0 (c très positif) ->
    OUBLIE (sep≈0). Bornes de l'échelle."""
    assert measure_retention_separation(_diag_genome(-10.0), 3, n_pairs=48, seed=0) > 0.99
    assert measure_retention_separation(_diag_genome(+10.0), 3, n_pairs=48, seed=0) < 0.01


def test_retention_separation_monotone_in_forget_gate():
    """Monotonie (direction) : sep décroît quand δ croît (le substrat oublie plus vite). La grandeur suit
    la dose imposée, pas seulement les bornes."""
    seps = [measure_retention_separation(_diag_genome(c), 3, n_pairs=48, seed=0)
            for c in (-6.0, -2.0, 0.0, 2.0, 6.0)]
    assert seps == sorted(seps, reverse=True), f"non monotone en δ : {seps}"


def test_retention_dissociates_from_convergence_confound():
    """LE CONTRÔLE QUI JUSTIFIE L'INSTRUMENT : un substrat δ≈0 NE BOUGE PAS -> measure_convergence le dit
    « convergent/gelé » (ce que EVO-001 lirait comme « contractif, pas de mémoire »), ALORS QU'il RETIENT
    parfaitement (sep≈1). Les deux instruments mesurent des choses DIFFÉRENTES ; sep est immunisé contre
    le confond qui aurait fait passer une mémoire pour un oubli. C'est la raison d'être de EDR-EVO-002."""
    g = _diag_genome(-10.0)
    # trajectoire d'un seul état sous entrée nulle -> quasi constante
    N = g.num_nodes
    Hh = np.zeros((1, 5, N), np.float32)
    Hp = np.zeros((1, N), np.float32)
    H = np.zeros((1, N), np.float32)
    H[0, I_DIM:] = np.linspace(-1, 1, N - I_DIM).astype(np.float32)
    traj = [H[0].copy()]
    for _ in range(40):
        _, H, _, _, _ = recurrent_forward(g, np.zeros((1, I_DIM), np.float32), H, Hh, Hp)
        traj.append(H[0].copy())
    assert measure_convergence(traj)["converges"] is True, "un substrat δ≈0 devrait sembler GELÉ"
    assert measure_retention_separation(g, 3, n_pairs=48, seed=0) > 0.99, "…mais il RETIENT (sep≈1)"


def test_enrichment_verdict_objective_is_lever():
    """Branche POSITIVE : DEMAND maîtrise (≈1), FRESH à chance, MLESS-xeval à chance (avec UNE fuite
    incidente tolérée par la médiane) -> OBJECTIVE_IS_LEVER, sign_p<0.05 sur DEMAND>FRESH."""
    dem = [1.0, 1.0, 0.98, 1.0, 0.99, 1.0]
    fresh = [0.55, 0.48, 0.60, 0.52, 0.50, 0.44]
    mless = [0.50, 1.0, 0.45, 0.52, 0.48, 0.51]          # 1 fuite -> médiane reste ~chance
    v = compute_enrichment_verdict(dem, mless, fresh)
    assert v["verdict"] == "OBJECTIVE_IS_LEVER"
    assert v["n_favorable"] == 6 and v["sign_p"] < 0.05 and v["specific_to_demand"]


def test_enrichment_verdict_substrate_or_search_limited():
    """Branche NÉGATIVE (réfuterait EVO-001) : DEMAND reste au plancher malgré la demande."""
    dem = [0.52, 0.48, 0.55, 0.50, 0.47, 0.53]
    fresh = [0.50, 0.49, 0.51, 0.50, 0.48, 0.52]
    mless = [0.50, 0.50, 0.49, 0.51, 0.50, 0.50]
    v = compute_enrichment_verdict(dem, mless, fresh)
    assert v["verdict"] == "SUBSTRATE_OR_SEARCH_LIMITED"


def test_enrichment_verdict_power_guard_blocks_small_n():
    """Garde de PUISSANCE : n=3 unanime -> sign_p=0.25 (>0.05) -> PAS de positif, malgré une accuracy
    parfaite. Reproduit le garde-fou du dépôt (pas de verdict positif sous puissance)."""
    v = compute_enrichment_verdict([1.0, 1.0, 1.0], [0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    assert v["sign_p"] == pytest.approx(0.25, abs=1e-9)
    assert v["verdict"] != "OBJECTIVE_IS_LEVER"


# --- SP-3 : run_prerequisite_recovery_probe / prerequisite_recovery_verdict --------------------------
# Étalon = un DAG de prérequis IMPOSÉ au format os-taxonomy (fixture SOURCE UNIQUE dans tools/). La
# réponse est connue PAR CONSTRUCTION : Ah est prérequis DUR de B, As MOU, Aprime NON-prérequis mais
# corrélé à Ah via l'ancêtre Z. On importe la fixture depuis tools/ (jamais de redéclaration locale).


def test_sp3_positive_control_recovers_a_hard_prerequisite():
    """CONTRÔLE POSITIF (générateur A) : sur un prérequis DUR imposé, l'ablation within-subject DOIT
    effondrer l'acquisition. Mesuré par construction : p 0.7 -> 0.3 (ratio ~2.33)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    out = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))
    by = {e["prereq"]: e for e in out["edges"]}
    assert by["Ah_food_chains"]["verdict"] == "X_DEMANDED", by


def test_sp3_specificity_holds_under_correlation():
    """LE TEST QUI DÉCIDE LE GO/NO-GO. Aprime est un NON-prérequis de B, mais corrélé à Ah (ancêtre Z
    partagé). L'ablation CHIRURGICALE d'Aprime ne touche pas ce que B lit -> no-op, X_DECOY. La
    corrélation seule ne fait PAS faux-positiver un marqueur qui ablate le bon canal."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    out = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), seeds=list(range(12)))
    by = {e["prereq"]: e for e in out["edges"]}
    assert by["Aprime_rainforest_web"]["verdict"] == "X_DECOY", by
    assert abs(by["Aprime_rainforest_web"]["ratio"] - 1.0) < 1e-9


def test_sp3_metric_is_alive_not_floored_or_ceilinged():
    """La spécificité ne vaut que sur une métrique VIVANTE (piège WARM-002). Le bras intact médian doit
    être strictement entre le plancher et le plafond déclarés."""
    import numpy as np
    from tools.ground_truth_worlds import acquisition_scores, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    med = float(np.median(acquisition_scores(fixture_subgraph(), fixture_world(), list(range(12)))))
    assert 15.0 < med < 200.0, f"métrique NON vivante (médiane {med})"


def test_sp3_ratio_is_monotone_hard_soft_nonedge():
    """MONOTONIE (direction) : dur > mou > non-arête (~1). Le mou n'est PAS tenu d'être X_DEMANDED —
    il est évalué par le RATIO, pas la catégorie (spec §7)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    by = {e["prereq"]: e for e in
          run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), list(range(12)))["edges"]}
    assert (by["Ah_food_chains"]["ratio"] > by["As_biodiversity"]["ratio"]
            > by["Aprime_rainforest_web"]["ratio"]), by


def test_sp3_confounded_ablation_would_false_positive():
    """LE CONTRASTE QUI REND LE RÉSULTAT NON-VACUEUX. Si on ablate Aprime par son ANCÊTRE Z (au lieu du
    canal chirurgical), Z alimente aussi Ah -> B s'effondre -> on attribuerait à tort une arête Aprime->B.
    C'est le mode d'échec que SP-2 doit éviter : la spécificité n'est PAS automatique, elle exige d'ablater
    le bon canal."""
    from tools.ground_truth_worlds import acquisition_scores, fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    from tools.demand_marker import ablation_verdict
    sg, w = fixture_subgraph(), fixture_world()
    intact = acquisition_scores(sg, w, list(range(12)))
    confounded = acquisition_scores(sg, w, list(range(12)), zeroed={"Z_producers"})  # ablation par l'ancêtre
    v = ablation_verdict(intact, confounded, intervention_verified=True, floor=15.0, ceiling=200.0)
    assert v["verdict"] == "X_DEMANDED", (
        "l'ablation par l'ancêtre DOIT effondrer B (faux positif si attribué à Aprime) : "
        f"{v['ratio']:.2f}")


def test_sp3_graph_recovery_precision_recall():
    """Recouvrement de graphe : sur la fixture, précision=rappel=1.0 (seul Ah récupéré, imposé dur)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    rec = run_prerequisite_recovery_probe(fixture_subgraph(), fixture_world(), list(range(12)))["recovery"]
    assert rec["precision"] == 1.0 and rec["recall"] == 1.0 and rec["recovered"] == ["Ah_food_chains"]


def test_sp3_recovered_ratio_tracks_the_imposed_gate_dose_by_prediction():
    """PRÉDICTION / LINÉARITÉ (3e forme canonique, spec §7.2) — distincte de la monotonie §7.3.

    Le ratio RÉCUPÉRÉ par la sonde (sortie de l'instrument) suit la DOSE imposée `hard_w`, avec une
    valeur PRÉDITE sans paramètre libre (générateur entièrement connu) :
        p_intact  = income + hard_w·eff(Ah=1) + soft_w·eff(As=1) = income + hard_w + soft_w
        p_ablated = income + soft_w              (ablation du dur -> terme dur = 0)
        ratio prédit = p_intact / p_ablated
    On vérifie que le ratio récupéré colle à la prédiction à chaque dose, ET qu'il croît avec la dose.
    C'est la calibration PAR PRÉDICTION (le cliquet ne vérifie que l'enregistrement, pas cette forme)."""
    from tools.prerequisite_recovery_probe import run_prerequisite_recovery_probe
    from tools.ground_truth_worlds import fixture_world
    from tools.os_taxonomy_adapter import fixture_subgraph
    sg = fixture_subgraph()
    hard = sg["hard"][0]
    seeds = list(range(12))
    ratios = []
    for hw in (0.2, 0.4, 0.6):
        w = fixture_world()
        w["hard_w"] = hw
        predicted = (w["income"] + hw + w["soft_w"]) / (w["income"] + w["soft_w"])
        by = {e["prereq"]: e for e in run_prerequisite_recovery_probe(sg, w, seeds)["edges"]}
        got = by[hard]["ratio"]
        assert got == pytest.approx(predicted, rel=0.15), (
            f"hard_w={hw}: ratio récupéré {got:.3f} vs prédit {predicted:.3f}")
        ratios.append(got)
    assert ratios == sorted(ratios), f"le ratio récupéré doit croître avec la dose hard_w : {ratios}"


# --- EVO-003 : `measure_type_sensitivity` (tools/evo_memory_inworld.py) ----------------------------
# L'instrument LOAD-BEARING du verdict EVO-003 : la décision d'approche du champion dépend-elle du canal
# type d'apex (obs[4]) ? Calibré PAR CONSTRUCTION avec deux génomes de réponse CONNUE — un LECTEUR (câble
# obs[4] vers les move-outputs) et un NON-LECTEUR (fanout de obs[4] mis à zéro, sorties variables sinon).
from tools.evo_memory_inworld import measure_type_sensitivity  # noqa: E402
from src.agents.mamba_agent import MambaAgent as _MambaAgentTS  # noqa: E402


def _reader_genome():
    """Réponse CONNUE = LIT obs[4] : W nul sauf canal type (obs[4]) -> les 4 move-outputs (δ≈1)."""
    g = _MambaAgentTS().genome
    N, O = g.num_nodes, g.num_outputs
    g.W[:] = 0.0
    for j in range(4):
        g.W[4, N - O + j] = 5.0
        g.W[N - O + j, N - O + j] = 5.0
    return g


def _nonreader_genome():
    """Réponse CONNUE = IGNORE obs[4] : W dense aléatoire (sorties non dégénérées) mais fanout de obs[4] nul."""
    g = _MambaAgentTS().genome
    g.W[4, :] = 0.0
    return g


def test_type_sensitivity_detects_a_reader():
    """CONTRÔLE POSITIF de la sonde : un génome qui câble obs[4] vers les move-outputs rend un Δ nettement
    non nul -> la sonde SAIT détecter la dépendance de la décision au canal type."""
    r = measure_type_sensitivity(_reader_genome(), seed=1, num_agents=12, ticks=40)
    assert r["n"] > 0, "aucun agent près d'un apex -> régime à ajuster"
    assert r["delta_abs_mean"] > 0.3, f"lecteur NON détecté : Δ={r['delta_abs_mean']:.3f}"


def test_type_sensitivity_zero_on_a_nonreader():
    """SPÉCIFICITÉ : un génome dont le FANOUT de obs[4] est nul (sorties variables via d'autres entrées)
    rend Δ≈0 SANS être dégénéré (logit_std>0). C'est ce qui rend le Δ≈0 des champions évolués
    INTERPRÉTABLE (ils ignorent obs[4]) plutôt qu'un artefact d'instrument insensible."""
    r = measure_type_sensitivity(_nonreader_genome(), seed=1, num_agents=12, ticks=40)
    assert r["n"] > 0
    assert r["delta_abs_mean"] < 0.02, f"Δ non nul alors que obs[4] n'a AUCUN fanout : {r['delta_abs_mean']:.4f}"
    assert r["logit_std"] > 0.1, "sorties dégénérées -> un Δ≈0 y serait ININTERPRÉTABLE"


def test_type_sensitivity_reader_dominates_nonreader():
    """PRÉDICTION (le contraste qui porte le verdict EVO-003 : champions ≈ non-lecteurs) : lecteur ≫ non-lecteur."""
    rr = measure_type_sensitivity(_reader_genome(), seed=2, num_agents=12, ticks=40)
    rn = measure_type_sensitivity(_nonreader_genome(), seed=2, num_agents=12, ticks=40)
    assert rr["delta_abs_mean"] > 10.0 * max(rn["delta_abs_mean"], 1e-6)


# --- SP-2 : run_perception_coordination_demand_probe --------------------------------------------------
# Jeu référentiel de Lewis (pur torch CPU) : ablation d'ENTRÉE within-subject sur la perception du sender
# (derange_rows, in-distribution). `episodes=200` (PAS 0) pour les DEUX cas ci-dessous : à episodes=0 le
# RECEIVER n'est jamais entraîné (la boucle `for _ in range(episodes)` ne tourne pas), donc même un signal
# ORACLE PARFAIT reste indécodé -> l'accuracy intacte stagne à la chance -> ablater ne peut rien effondrer
# (mesuré : ratio 1.09, X_DECOY, PAS X_DEMANDED). Le sender reste bypassé (oracle/aléatoire n'apprend
# jamais) -> le banc reste rapide (~50s/cas) même en entraînant le receiver.


def test_sp2_oracle_sender_makes_perception_demanded():
    """CONTRÔLE POSITIF (générateur A) : avec un sender ORACLE (signal = index perçu), la coordination est
    parfaite et DÉRANGER la perception l'effondre -> COORD X_DEMANDED. Le banc SAIT produire l'effondrement.
    Sender bypassé (oracle) -> seul le receiver entraîne, ~50s pour 12 seeds."""
    from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe
    r = run_perception_coordination_demand_probe(seeds=list(range(12)), episodes=200, n_agents=16, K=6,
                                                 sender_mode="oracle")
    assert r["coord"]["verdict"] == "X_DEMANDED", r["coord"]
    assert r["coord"]["ratio"] > 1.5


def test_sp2_random_sender_is_inert_no_false_demand():
    """CONTRÔLE NÉGATIF : avec un sender ALÉATOIRE (signal décorrélé), pas de coordination -> DÉRANGER la
    perception est inerte -> COORD PAS X_DEMANDED. Le banc ne FABRIQUE pas un effondrement inexistant."""
    from tools.perception_coordination_demand_probe import run_perception_coordination_demand_probe
    r = run_perception_coordination_demand_probe(seeds=list(range(12)), episodes=200, n_agents=16, K=6,
                                                 sender_mode="random")
    assert r["coord"]["verdict"] != "X_DEMANDED", r["coord"]


# --- CALIB-ALIAS : run_functional_aliasing_probe / functional_aliasing_verdict ----------------------
# Étalon = un génome câblé à la main dans le VRAI recurrent_forward. Réponse connue PAR CONSTRUCTION :
# α=0 disjoint (ablater X = no-op exact sur out_Y), α>0 partagé (fuite), monotone en α. Déterministe.


def test_alias_noop_exact_on_disjoint_substrate():
    """no-op EXACT (spécificité) : sur un câblage DISJOINT, ablater X ne touche PAS out_Y (bit-identique),
    mais tue bien out_X (ablation NON vacuse -> générateur A). Mesuré : leakage 0.0, x_response ~0.466."""
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(0.0))
    assert r["leakage"] == 0.0 and r["verdict"] == "SURGICAL"
    assert r["x_response"] > 0.1, "l'ablation doit changer la capacité PROPRE de X (sinon no-op vacux)"


def test_alias_positive_control_leak_on_shared_substrate():
    """contrôle positif : sur un câblage PARTAGÉ (α=1), ablater X fait FUIR out_Y. Mesuré : leakage ~0.253."""
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    r = run_functional_aliasing_probe(make_aliasing_genome(1.0))
    assert r["verdict"] == "FUNCTIONAL_LEAK" and r["leakage"] > 0.1


def test_alias_leakage_is_monotone_in_the_sharing_dose():
    """monotonie (direction) : la fuite croît avec la dose de partage α. Mesuré : ~0/0.099/0.177/0.253."""
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    leaks = [run_functional_aliasing_probe(make_aliasing_genome(a))["leakage"] for a in (0.0, 0.3, 0.6, 1.0)]
    assert leaks[0] == 0.0, f"α=0 doit être un no-op exact : {leaks}"
    assert all(a < b for a, b in zip(leaks, leaks[1:])), f"fuite non STRICTEMENT croissante : {leaks}"


def test_alias_structural_guard_is_blind_to_functional_leak():
    """LE CONTRASTE QUI JUSTIFIE LE NOUVEAU GARDE. Sur le substrat partagé, la sortie de contrôle FUIT,
    mais les deux mesures sont des arrays INDÉPENDANTS -> np.shares_memory est False -> l'ancien garde
    STRUCTUREL `assert_no_aliasing` PASSE (aveugle), tandis que le garde COMPORTEMENTAL tire."""
    import numpy as np
    import pytest
    from tools.functional_aliasing_probe import run_functional_aliasing_probe
    from tools.ground_truth_worlds import make_aliasing_genome
    from tools.experiment_preflight import assert_no_aliasing, assert_no_functional_aliasing, PreflightError
    r = run_functional_aliasing_probe(make_aliasing_genome(1.0))
    ci = np.array([r["control_intact"]], dtype=np.float32)
    ca = np.array([r["control_ablated"]], dtype=np.float32)
    assert not np.shares_memory(ci, ca), "deux mesures indépendantes ne partagent pas la mémoire"
    assert assert_no_aliasing(ci, ca) is True, "le garde STRUCTUREL est aveugle à la fuite fonctionnelle"
    with pytest.raises(PreflightError):
        assert_no_functional_aliasing(r["control_intact"], r["control_ablated"])


# --- EVO-004 : `measure_channel_saliency` (généralise measure_type_sensitivity à tous les canaux) --------
# Calibré PAR CONSTRUCTION avec les mêmes génomes de réponse CONNUE : un LECTEUR du canal 4 doit avoir une
# saillance ISOLÉE sur le canal 4 (haute) et 0 sur les autres ; un NON-LECTEUR (fanout de 4 nul) -> 0 sur 4.
from tools.evo_memory_inworld import measure_channel_saliency  # noqa: E402


def test_channel_saliency_isolates_the_read_channel():
    """CONTRÔLE POSITIF + spécificité : le lecteur du canal 4 doit s'allumer FORT sur le canal 4 et rester
    à ~0 sur des canaux qu'il ne câble pas -> la sonde attribue la saillance au BON canal."""
    sal = measure_channel_saliency(_reader_genome(), seed=1, channels=[0, 1, 4, 11, 36], num_agents=12, ticks=40)
    assert sal[4] > 0.3, f"canal lu non détecté : {sal[4]:.3f}"
    for k in (0, 1, 11, 36):
        assert sal[k] < 0.02, f"saillance parasite sur un canal NON câblé {k} : {sal[k]:.3f}"


def test_channel_saliency_zero_on_a_nonread_channel():
    """SPÉCIFICITÉ : un génome dont le fanout du canal 4 est nul rend une saillance ≈0 sur le canal 4 ->
    ce qui rend le « ~200× sous un lecteur » des champions INTERPRÉTABLE (ils ne lisent presque rien)."""
    sal = measure_channel_saliency(_nonreader_genome(), seed=1, channels=[4], num_agents=12, ticks=40)
    assert sal[4] < 0.02, f"saillance non nulle alors que le canal 4 n'a pas de fanout : {sal[4]:.4f}"


def test_channel_saliency_decision_branch_detects_the_reader():
    """Branche `decision=True` (FONCTIONNELLE, classe E17) : le taux de bascule d'`argmax` — la grandeur qui
    AGIT in-world (`action = argmax(logits[:8])`, world_1_stoneage.py:1291). Le lecteur du canal 4 doit
    changer d'action quasi systématiquement quand on inverse ce canal ; le non-lecteur, jamais."""
    rd = measure_channel_saliency(_reader_genome(), seed=1, channels=[4], num_agents=12, ticks=40, decision=True)
    rn = measure_channel_saliency(_nonreader_genome(), seed=1, channels=[4], num_agents=12, ticks=40, decision=True)
    assert rd[4] > 0.5, f"le lecteur ne change pas d'action : flip={rd[4]:.3f}"
    assert rn[4] < 0.02, f"le non-lecteur change d'action : flip={rn[4]:.3f}"


# --- E17 : AMPLITUDE vs SIGNE — la garde exécutable de la classe (registre des erreurs) -----------------
# Contre-exemple GELÉ : un génome qui RÉSOUT le rappel différé (acc 1.000) a une saillance en AMPLITUDE de
# ~2e-6, indiscernable de celle d'un NON-lecteur (0.0) ; seul `sign_flip` les sépare (1.00 vs 0.00). Deux
# occurrences dans l'arc EVO (sep(D) puis measure_cue_saliency) -> classe promue `exécutable` d'emblée.
from tools.evo_memory_enrichment import (  # noqa: E402
    measure_cue_saliency, eval_genome as _eval_cue, I_DIM as _I, O_DIM as _O)

_N_CUE = _I + _O + 3


def _cue_reader(w=0.05, K=2):
    """Réponse CONNUE : indice j -> nœud de sortie j (poids MINUSCULE), diagonale très négative (δ≈0) donc
    la valeur est PORTÉE à travers les D pas nuls. Résout la tâche (acc 1.000) avec une amplitude ~0."""
    W = np.zeros((_N_CUE, _N_CUE), np.float32)
    for j in range(K):
        W[j, _N_CUE - _O + j] = w
        W[_N_CUE - _O + j, _N_CUE - _O + j] = -10.0
    return Genome(W, _I, _O)


def _cue_nonreader(seed=0):
    """Réponse CONNUE : W dense aléatoire mais fanout de l'indice NUL -> ne peut pas le lire."""
    rng = np.random.RandomState(seed)
    W = (rng.randn(_N_CUE, _N_CUE) * 0.4).astype(np.float32)
    W[0, :] = 0.0
    return Genome(W, _I, _O)


def test_cue_saliency_sign_flip_separates_reader_from_nonreader():
    """CONTRÔLE POSITIF + SPÉCIFICITÉ sur la grandeur FONCTIONNELLE : le lecteur suit toujours l'indice
    (sign_flip=1), le non-lecteur jamais (0). C'est cette mesure — pas l'amplitude — qui porte le verdict."""
    assert measure_cue_saliency(_cue_reader(), K=2, D=3, trials=48, seed=0)["sign_flip"] > 0.95
    assert measure_cue_saliency(_cue_nonreader(), K=2, D=3, trials=48, seed=0)["sign_flip"] < 0.05


def test_cue_saliency_amplitude_is_blind_to_a_perfect_reader():
    """⚠️ LE CONTRE-EXEMPLE GELÉ (classe E17). Le génome ci-dessous RÉSOUT la tâche — `acc = 1.000`, il lit
    donc l'indice par construction — et pourtant sa saillance en AMPLITUDE est ~1e-6, du même ordre que
    celle d'un non-lecteur (0.0). Sur un substrat CONTRACTIF dont la décision se lit par `np.sign`,
    l'amplitude ne mesure PAS la dépendance fonctionnelle. Si quelqu'un ré-adopte l'amplitude comme mesure
    de saillance, ce test tombe."""
    g = _cue_reader()
    assert _eval_cue(g, 2, 3, True, 200, seed=99) == pytest.approx(1.0), "le témoin doit RÉSOUDRE la tâche"
    ampl_reader = measure_cue_saliency(g, K=2, D=3, trials=48, seed=0)["delayed"]
    ampl_none = measure_cue_saliency(_cue_nonreader(), K=2, D=3, trials=48, seed=0)["delayed"]
    assert ampl_reader < 1e-4, f"amplitude du lecteur PARFAIT attendue ≈0, mesurée {ampl_reader:.2e}"
    assert abs(ampl_reader - ampl_none) < 1e-4, (
        "l'amplitude doit être INDISCERNABLE entre lecteur parfait et non-lecteur — c'est la classe E17")


# --- EVO-005 : objectif cognitif in-world — estimateur de fitness + banc ------------------------------
# Instruments NÉS le 2026-07-27, calibrés dans la même passe (cliquet : aucun nouvel instrument non
# calibré). Vérité-terrain ANALYTIQUE pour l'estimateur, contrôle positif CÂBLÉ pour le banc in-world.
from tools.evo_cognitive_objective import (  # noqa: E402
    measure_cognitive_rate, benchmark_cognitive, synthetic_reader,
    CHANCE as _CHANCE, PSEUDO as _PSEUDO)


def _ag(ticks, hits):
    return {"_cog_ticks": ticks, "_cog_hits": hits}


def _naive_rate_toward_chance(ticks, hits, pseudo=_PSEUDO):
    """Variante NAÏVE, figée ici comme CONTRE-EXEMPLE : lissage vers la CHANCE (prior Beta(10,10)).
    C'est la formulation « évidente » de la leçon d'EDR-056 — et elle est fausse (cf. test ci-dessous)."""
    return (hits + 0.5 * pseudo) / (ticks + pseudo)


def test_cognitive_rate_crushes_low_count_luck():
    """CONTRÔLE de SPÉCIFICITÉ (leçon d'EDR-056) : un agent qui a « réussi » 3 fois sur 3 par hasard ne
    doit PAS être crédité comme un lecteur. C'est exactement le mode d'échec qui a fait backfirer la
    fitness alignée de 056 (distinction fortuite à compte 1, amplifiée ×400)."""
    lucky = measure_cognitive_rate(_ag(3, 3))
    real = measure_cognitive_rate(_ag(120, 120))
    assert lucky < 0.2, f"la chance à faible compte est créditée : {lucky:.3f}"
    assert real > 0.8, f"un lecteur RÉEL doit être crédité : {real:.3f}"
    assert lucky < real


def test_cognitive_rate_has_no_incentive_to_die_early():
    """⚠️ CONTRE-EXEMPLE GELÉ (classe E18) — le défaut de design attrapé au pré-vol d'EVO-005.

    Un lissage vers la CHANCE récompense l'ABSENCE DE PREUVE : comme les agents réels plafonnent vers
    0.10, un agent mort à 3 ticks est tiré vers 0.435 tandis qu'un agent vivant 120 ticks et lisant mal
    tombe à 0.157. À poids fort la sélection optimiserait alors la MORT PRÉCOCE, et le banc rendrait un
    faux négatif (« l'objectif cognitif ne produit pas de lecture ») qui ne mesurerait que l'estimateur.
    Le lissage vers ZÉRO n'a pas ce défaut. Si quelqu'un ré-adopte le lissage vers la chance, ce test tombe."""
    dead_early, long_poor = _ag(3, 0), _ag(120, 12)
    assert _naive_rate_toward_chance(3, 0) > _naive_rate_toward_chance(120, 12), (
        "le contre-exemple doit RESTER un contre-exemple : la variante naïve favorise la mort précoce")
    assert measure_cognitive_rate(dead_early) < measure_cognitive_rate(long_poor), (
        "l'estimateur retenu ne doit JAMAIS préférer un agent mort tôt à un agent qui a vécu et fait mieux")


def test_cognitive_rate_is_monotone_and_never_penalises_a_good_tick():
    """MONOTONIE (direction) : à ticks fixés le taux croît avec les succès, et un tick RÉUSSI de plus
    améliore TOUJOURS le score — la propriété algébrique (`t + PSEUDO > h`) qui garantit l'absence
    d'incitation perverse quel que soit le régime de survie."""
    assert (measure_cognitive_rate(_ag(100, 10)) < measure_cognitive_rate(_ag(100, 50))
            < measure_cognitive_rate(_ag(100, 90)))
    for t, h in ((0, 0), (5, 2), (50, 25), (200, 199)):
        assert measure_cognitive_rate(_ag(t + 1, h + 1)) > measure_cognitive_rate(_ag(t, h)), (
            f"un tick réussi de plus doit toujours aider (t={t}, h={h})")


def test_benchmark_cognitive_positive_control_and_specificity():
    """CONTRÔLE POSITIF (générateur A du pré-vol) + SPÉCIFICITÉ, in-world.

    Le lecteur RÉFLEXE câblé doit dépasser le plafond analytique d'une politique FIXE (0.5) ; le MÊME
    génome privé de l'INFORMATION (`inject=False` : le signal est tiré et noté mais jamais montré) doit
    s'effondrer. Sans ces deux bornes, un nul du banc serait ininterprétable — l'instrument doit pouvoir
    produire LES DEUX issues."""
    g = synthetic_reader(59, 108, 172, w=2.0, reflex=True)
    seen = benchmark_cognitive(g, seed=1, num_agents=8, ticks=100, inject=True)
    blind = benchmark_cognitive(g, seed=1, num_agents=8, ticks=100, inject=False)
    assert seen["raw"] > _CHANCE, (
        f"le lecteur câblé doit dépasser le plafond d'une politique FIXE : {seen['raw']:.3f} <= {_CHANCE}")
    assert blind["raw"] < seen["raw"] / 2.0, (
        f"retirer l'INFORMATION doit effondrer le taux : vu={seen['raw']:.3f} aveugle={blind['raw']:.3f}")


def test_benchmark_cognitive_nonreader_stays_at_floor():
    """CONTRÔLE NÉGATIF : même substrat réflexe, canal du signal NON câblé (w=0) -> le banc ne doit rien
    créditer. Distingue « lit le signal » de « bouge beaucoup »."""
    nr = benchmark_cognitive(synthetic_reader(59, 108, 172, w=0.0, reflex=True),
                             seed=1, num_agents=8, ticks=100, inject=True)
    assert nr["raw"] < 0.25, f"un non-lecteur est crédité : {nr['raw']:.3f}"


def test_synthetic_reader_needs_the_reflex_diagonal_state_drift_counterexample():
    """⚠️ CONTRE-EXEMPLE GELÉ (classe E6) — la DÉRIVE D'ÉTAT du substrat in-world, mesurée au pré-vol.

    Le MÊME câblage lecteur, à diagonale nulle (δ = sigmoid(0) = 0.5), tombe à la CHANCE in-world alors
    qu'il est parfait sur un état frais : H accumule et, l'activation ayant f(0) ≠ 0, même les sorties
    JAMAIS câblées dérivent (+7.45 ± 9.8 après 25 ticks), ce qui noie une marge de signal de ±2.5.

    C'est le mécanisme du confond laissé OUVERT par EDR-S2-011 (« le bassin BC atteint acc 1.00 sur
    `_step(obs, H=0)` mais ne transfère pas au forward RÉCURRENT du monde »). Conséquence de design : un
    lecteur RÉACTIF exige une CONJONCTION de deux mutations — câbler le canal ET dé-mémoriser la sortie."""
    drift = benchmark_cognitive(synthetic_reader(59, 108, 172, w=8.0, reflex=False),
                                seed=1, num_agents=8, ticks=100, inject=True)
    reflex = benchmark_cognitive(synthetic_reader(59, 108, 172, w=2.0, reflex=True),
                                 seed=1, num_agents=8, ticks=100, inject=True)
    assert drift["raw"] < _CHANCE + 0.1, (
        f"le contre-exemple doit RESTER un contre-exemple : lecteur à état dérivant = {drift['raw']:.3f}")
    assert reflex["raw"] > drift["raw"] + 0.15, (
        f"le lecteur RÉFLEXE doit nettement dominer : réflexe={reflex['raw']:.3f} dérivant={drift['raw']:.3f}")


# --- EVO-003 : `benchmark_discrimination` — la SATURATION à compte 1, gelée ---------------------------
from tools import evo_memory_inworld as _emi  # noqa: E402


def test_benchmark_discrimination_resolution_is_coarser_than_its_published_claims():
    """⚠️ CONTRE-EXEMPLE GELÉ — `disc` est calculé sur 1-2 ÉVÉNEMENTS, donc sa RÉSOLUTION (1/n ≥ 0.2) est
    plus grossière que les écarts qu'on lui fait dire.

    `disc = big/(big+leurre)` sur une cohorte entière de 24 agents × 150 ticks ne rassemble qu'une poignée
    de rencontres. Il ne peut alors prendre que {0, 0.5, 1.0} : le « contrôle positif partiel, disc
    0.80-1.00 » d'[[EDR-EVO-003]] n'est pas seulement fragile, il est **littéralement non représentable**
    à ces comptes — et un `disc = 1.00` y est produit par l'ABSENCE d'un contact Leurre, pas par un choix
    (classe E18 hors d'une fitness : elle ne fausse pas la sélection, elle fabrique un VERDICT).

    ⚠️ DEUX corrections successives par la mesure, gardées ici en mémoire :
    (1) l'hypothèse initiale (« biais du survivant par la létalité du Leurre ») était plus faible que le
        défaut réel ;
    (2) la 1ʳᵉ version de CE test assertait `disc == 1.00`, généralisé depuis 3 génomes qui rendaient tous
        1.00 — un 4ᵉ rend 0.500 (2 rencontres, 1 Leurre). C'était une **classe E9** (généralisation depuis
        un échantillon saillant) dans le test écrit pour épingler un défaut d'échantillonnage. Ce qui est
        gelé désormais est STRUCTUREL — la taille du dénominateur — pas la valeur observée."""
    np.random.seed(0)
    seen = [_emi.benchmark_discrimination(g, memory_regime=False, seed=7, num_agents=24, ticks=150)
            for g in _emi._fresh_soup(3, _emi._cfg(), 0.4)]
    live = [r for r in seen if r["encounters"] > 0]
    assert live, ("le banc ne produit AUCUN événement sur 3 génomes : le cas ne peut plus rien épingler "
                  "(vérification vide, classe E4) — réviser num_agents/ticks avant de lire ce test vert")
    for r in live:
        assert r["encounters"] <= 5, (
            f"le régime a CHANGÉ : {r['encounters']} rencontres. À comptes élevés `disc` redeviendrait "
            f"interprétable, et les verdicts d'EDR-EVO-003 devraient être relus")
        assert r["disc"] * r["encounters"] == pytest.approx(round(r["disc"] * r["encounters"])), (
            f"disc={r['disc']:.3f} devrait être quantifié au 1/{r['encounters']}")
        assert 1.0 / r["encounters"] >= 0.2, (
            f"résolution de disc = 1/{r['encounters']} — un écart de 0.20 est le PLUS PETIT que cet "
            f"instrument puisse représenter ici, or EVO-003 en publiait de plus fins")


# --- EVO-006 : crédit PARTIEL (K sous-tâches) — monotonie ET spécificité ------------------------------
# Le banc K>1 ne teste quelque chose QUE si câbler une sous-tâche sur K rend un score strictement entre le
# plancher et le lecteur complet. C'est `assert_ablation_changes_something` appliqué à la GRANULARITÉ du
# crédit : sans ce gradient, un nul du banc serait ininterprétable (rien n'aurait été offert à trouver).


def test_partial_credit_ladder_is_monotone():
    """MONOTONIE (direction) — l'échelle du crédit partiel. Chaque sous-tâche câblée en plus doit AUGMENTER
    le score, et 1 sur 3 doit déjà FRANCHIR le plafond analytique d'une politique fixe (0.5). C'est
    exactement ce qui était impossible à K=1, où il fallait un lecteur complet d'un seul coup."""
    raws = [benchmark_cognitive(synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=n),
                                seed=1, num_agents=8, ticks=100, inject=True, K=3)["raw"]
            for n in (0, 1, 3)]
    assert raws[0] < raws[1] < raws[2], f"échelle non monotone : {[round(r, 3) for r in raws]}"
    assert raws[1] > _CHANCE, (
        f"câbler 1 sous-tâche sur 3 doit franchir le plafond d'une politique FIXE : {raws[1]:.3f}")


def test_partial_credit_is_isolated_to_the_wired_subtask():
    """SPÉCIFICITÉ (no-op sur les autres) — câbler la sous-tâche 0 ne doit faire monter QUE la sous-tâche 0 ;
    les autres restent à la chance. Sans ça, le score global monterait pour une raison sans rapport avec la
    lecture (p.ex. un changement de comportement moteur), et la lecture « par sous-tâche » ne voudrait
    rien dire."""
    b = benchmark_cognitive(synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=1),
                            seed=1, num_agents=8, ticks=100, inject=True, K=3)
    assert b["sub"][0] > 0.6, f"la sous-tâche CÂBLÉE doit monter : {b['sub'][0]:.3f}"
    for k in (1, 2):
        assert abs(b["sub"][k] - _CHANCE) < 0.15, (
            f"la sous-tâche NON câblée {k} doit rester à la chance : {b['sub'][k]:.3f}")


def test_signal_channels_carry_zero_information_in_the_base_world():
    """CONTRÔLE de base, bon marché et load-bearing : les 3 canaux porteurs sont des `np.zeros` CÂBLÉS EN
    DUR du monde (world_1_stoneage.py:610-623). S'ils cessaient d'être exactement nuls, le banc ne
    mesurerait plus une lecture du SIGNAL mais une corrélation avec un contenu de monde, et toute la
    série EVO-005/006 deviendrait ininterprétable."""
    from tools.evo_cognitive_objective import _run_era as _cog_run_era, SIG_COLS
    np.random.seed(0)
    env, _ = _cog_run_era(_emi._fresh_soup(10, _emi._cfg(), 0.4), _emi._cfg(), 40, era=1,
                          inject=False, K=3)
    if not env.agents:
        pytest.skip("aucun survivant à 40 ticks : rien à inspecter")
    obs = np.asarray(env.get_batch_observations(), dtype=np.float32)
    for c in SIG_COLS:
        assert np.abs(obs[:, c]).max() == 0.0, (
            f"le canal {c} n'est PLUS à information nulle (max|v|={np.abs(obs[:, c]).max():.6f}) — "
            f"le monde a changé, les verdicts EVO-005/006 doivent être relus")


def test_decision_saliency_separates_reader_from_nonreader_and_is_channel_specific():
    """CONTRÔLE POSITIF + SPÉCIFICITÉ de `measure_decision_saliency` (instrument NÉ avec EVO-006).

    Il mesure la bascule de `sign(logits[out_idx])` — l'opérateur EXACT par lequel le monde décide
    (`do_throw = logits[8] > 0`). Nécessaire parce que `measure_channel_saliency(decision=True)` lit la
    bascule d'`argmax(logits[:8])` et est donc AVEUGLE PAR CONSTRUCTION aux sous-tâches qui ne passent pas
    par l'argmax : sur un lecteur `throw` PARFAIT elle rend 0.000. C'est la classe E17 déplacée du choix
    de la GRANDEUR (amplitude vs signe) au choix de la SORTIE mesurée."""
    from tools.evo_cognitive_objective import measure_decision_saliency, SIG_COLS, THROW_IDX
    reader = synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=2)
    nonreader = synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=0)
    on = measure_decision_saliency(reader, seed=2000, channel=SIG_COLS[1], out_idx=THROW_IDX,
                                   num_agents=8, ticks=40)
    off = measure_decision_saliency(reader, seed=2000, channel=SIG_COLS[0], out_idx=THROW_IDX,
                                    num_agents=8, ticks=40)
    floor = measure_decision_saliency(nonreader, seed=2000, channel=SIG_COLS[1], out_idx=THROW_IDX,
                                      num_agents=8, ticks=40)
    assert on > 0.9, f"le lecteur câblé doit basculer quasi toujours : {on:.3f}"
    assert off < 0.05, f"SPÉCIFICITÉ : un canal sans rapport ne doit rien basculer : {off:.3f}"
    assert floor < 0.05, f"le non-lecteur ne doit rien basculer : {floor:.3f}"


def test_argmax_saliency_is_blind_to_a_perfect_throw_reader():
    """⚠️ CONTRE-EXEMPLE GELÉ — pourquoi l'instrument précédent ne suffisait pas.

    Un génome qui lit PARFAITEMENT le signal `throw` (bascule de sign(logits[8]) = 1.000, cf. test
    ci-dessus) rend une saillance d'`argmax` NULLE : sa lecture ne passe pas par les logits de
    déplacement. Sonder la mauvaise SORTIE produit donc un faux négatif sur un lecteur avéré — et c'est
    ce qui a rendu la règle pré-enregistrée d'EVO-006 inapplicable telle qu'écrite."""
    from tools.evo_cognitive_objective import measure_decision_saliency, SIG_COLS, THROW_IDX
    from tools.evo_memory_inworld import measure_channel_saliency as _mcs
    reader = synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=2)
    real = measure_decision_saliency(reader, seed=2000, channel=SIG_COLS[1], out_idx=THROW_IDX,
                                   num_agents=8, ticks=40)
    blind = _mcs(reader, seed=2000, channels=[SIG_COLS[1]], num_agents=8, ticks=40, decision=True)
    assert real > 0.9, f"le témoin doit être un lecteur AVÉRÉ : {real:.3f}"
    assert blind[SIG_COLS[1]] < 0.05, (
        f"la saillance d'argmax doit être AVEUGLE à ce lecteur : {blind[SIG_COLS[1]]:.3f} — "
        f"si ça devient faux, les deux instruments se recouvrent et ce garde-fou est caduc")


# ------------------------------------------- run_memory_perception_demand_probe (MEM-PERCEPTION)
# « memory demande perception » sur un delayed-match-to-sample torch (Tâche 1, deuxième arête du
# graphe AGI-Taxonomy). Mémoire = état récurrent H PORTÉ encode -> délai -> test. oracle/random
# BYPASSENT l'agent (guess lu directement sur l'indice encodé, ou tiré au hasard) -> aucun
# entraînement -> episodes=0 valide et rapide, symétrique à SP-2 (run_perception_coordination_demand_probe).

def test_mp_oracle_memory_makes_perception_demanded():
    """CONTRÔLE POSITIF (générateur A) : avec une mémoire ORACLE (rétention parfaite de l'indice encodé),
    DÉRANGER la perception à l'encodage l'effondre -> DELAYED X_DEMANDED. Le banc SAIT produire l'effondrement.
    Oracle BYPASSE l'agent (guess = indice encodé) -> aucun entraînement -> episodes=0 valide, quelques secondes."""
    from tools.memory_perception_demand_probe import run_memory_perception_demand_probe
    r = run_memory_perception_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                           memory_mode="oracle")
    assert r["delayed"]["verdict"] == "X_DEMANDED", r["delayed"]
    assert r["delayed"]["ratio"] > 1.5


def test_mp_random_memory_is_inert_no_false_demand():
    """CONTRÔLE NÉGATIF : avec une mémoire ALÉATOIRE (guess décorrélé de l'indice), DÉRANGER la perception
    est inerte -> DELAYED PAS X_DEMANDED. Le banc ne FABRIQUE pas un effondrement inexistant."""
    from tools.memory_perception_demand_probe import run_memory_perception_demand_probe
    r = run_memory_perception_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                           memory_mode="random")
    assert r["delayed"]["verdict"] != "X_DEMANDED", r["delayed"]


# --- EVO-008 : un instrument ne doit laisser AUCUNE trace sur le RNG global ---------------------------
# Classe E5 (aliasing) transposee a l'ETAT GLOBAL : `np.random.seed(...)` dans une sonde detourne
# l'evolution qu'elle est censee OBSERVER quand on l'appelle ENTRE deux eres. Le defaut a ete revele par
# un cas a REPONSE CONNUE (le seed 0, lecteur avere 4 fois, rendait une courbe de saillance PLATE) — sans
# ce temoin, l'artefact se lisait comme un resultat : « le lecteur apparait de nulle part ».


def test_decision_saliency_leaves_the_global_rng_untouched():
    """⚠️ CONTRE-EXEMPLE GELE. Mesurer ne doit pas MUTER le systeme mesure. Si quelqu'un retire la
    restauration d'etat, toute sonde intercalee dans une boucle d'evolution la detournera silencieusement."""
    from tools.evo_cognitive_objective import measure_decision_saliency, SIG_COLS, THROW_IDX
    np.random.seed(1234)
    before = np.random.rand(4)
    np.random.seed(1234)
    measure_decision_saliency(synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=2),
                              seed=77, channel=SIG_COLS[1], out_idx=THROW_IDX, num_agents=4, ticks=10)
    after = np.random.rand(4)
    assert np.allclose(before, after), (
        f"la sonde a DETOURNE le RNG global : {before} -> {after}. Une mesure intercalee dans une "
        f"evolution la rendrait non reproductible, et sa courbe ININTERPRETABLE")


def test_decision_saliency_value_is_unchanged_by_the_restoration():
    """La restauration ne doit pas alterer ce que l'instrument MESURE : meme graine -> meme valeur."""
    from tools.evo_cognitive_objective import measure_decision_saliency, SIG_COLS, THROW_IDX
    g = synthetic_reader(59, 108, 172, w=2.0, reflex=True, wire=2)
    a = measure_decision_saliency(g, seed=5, channel=SIG_COLS[1], out_idx=THROW_IDX, num_agents=4, ticks=10)
    np.random.seed(999)                     # etat d'appelant DIFFERENT
    b = measure_decision_saliency(g, seed=5, channel=SIG_COLS[1], out_idx=THROW_IDX, num_agents=4, ticks=10)
    assert a == b, f"l'instrument doit dependre de SA graine, pas de l'etat de l'appelant : {a} vs {b}"


# ------------------------------------------- run_language_memory_demand_probe (LANG-MEMORY) ------------
# « language demands memory » (delayed-code-application, torch). Tâche 1, 3e arête du graphe
# AGI-Taxonomy — 1re ablation SUBSTRAT (reset de H PORTÉ, pas une ablation d'ENTRÉE) : `functional_aliasing`
# doit être MESURÉ ('pass'/'fail'), jamais 'n/a'. oracle/random BYPASSENT LANG (guess lu directement sur
# (q+key)%K, ou tiré au hasard) ; leaky BYPASSE CONTROL (forcé de dépendre du key retenu) -> aucun
# entraînement -> episodes=0 valide et rapide, symétrique à SP-2/MEM-PERCEPTION.

def test_lm_oracle_memory_makes_language_demanded():
    """CONTRÔLE POSITIF (demande) : mémoire ORACLE (rétention parfaite du key) -> ablater l'état
    (H-reset) effondre LANG -> X_DEMANDED. Le banc SAIT produire l'effondrement."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                         memory_mode="oracle")
    assert r["lang_demand"]["verdict"] == "X_DEMANDED", r["lang_demand"]


def test_lm_random_memory_is_inert():
    """CONTRÔLE NÉGATIF (demande) : mémoire ALÉATOIRE (guess décorrélé) -> ablation inerte -> PAS
    X_DEMANDED. Le banc ne fabrique pas un effondrement inexistant."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                         memory_mode="random")
    assert r["lang_demand"]["verdict"] != "X_DEMANDED", r["lang_demand"]


def test_lm_leaky_control_fires_the_aliasing_guard():
    """VÉRITÉ-TERRAIN DU GARDE : un control LEAKY (forcé de dépendre du key retenu, pas de `c`) ->
    ablater l'état fait FUIR le contrôle -> `functional_aliasing='fail'` (FUNCTIONAL_LEAK). Prouve que
    le garde SAIT détecter une fuite (sinon un 'pass' serait vacux). oracle+leaky : LANG effondre
    (X_DEMANDED) ET le garde tire — les deux dimensions (demande + aliasing) sont sensibles."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=16, K=6, D=2,
                                         memory_mode="oracle", control_mode="leaky")
    assert r["functional_aliasing"] == "fail" and r["alias_verdict"] == "FUNCTIONAL_LEAK", r


# ------------------------------------------- run_bilinear_composition_probe (BILINEAR) ------------
# Le terme bilinéaire low-rank de `TorchPopulationModel` (Tâche 1, `7747b1e`) débloque-t-il
# (q+key)%K, que le substrat PLAIN ne peut pas apprendre (étalon LANG-MEMORY, 0.15-0.33) ? Ces cas
# ENTRAÎNENT réellement (pas de bypass agent, contrairement à MEM-PERCEPTION/LANG-MEMORY) -> budget
# BORNÉ au strict nécessaire pour trancher (seeds=[0,1,2], voir docstrings pour le budget exact et
# le wall-clock mesuré). ⚠️ Le test « positif » ci-dessous a été RENOMMÉ pour refléter le résultat
# RÉELLEMENT MESURÉ : après recherche d'hyperparamètres bornée (episodes 150-3000, lr 0.02-0.1,
# rank 16-64, 5 seeds), le bilinéaire ne franchit JAMAIS le seuil sur la composition — il reste
# systématiquement SOUS plain. Forcer un budget non borné pour fabriquer un "unlocked=True" aurait
# violé le protocole de pré-vol (ne pas raisonner/forcer au lieu de mesurer) ; le nul reproductible
# EST la calibration (cf. commentaire CALIBRATED ci-dessus).

def test_bilinear_composition_crux_finding_stays_null():
    """CRUX (générateur A, résultat MESURÉ, pas l'hypothèse aspirationnelle du brief) : sur
    (q+key)%K, PLAIN reste nul (reproduit l'étalon LANG-MEMORY) ET BILINÉAIRE reste nul AUSSI ->
    `unlocked=False`. Budget borné : seeds=[0,1,2], episodes=600, n_agents=16, K=6 (wall mesuré
    ≈60s, << 3 min). Medians mesurés (2026-08-03) : plain≈0.22, bilinéaire≈0.18 (per-seed
    bilinéaire = [0.195, 0.178, 0.180], TOUJOURS sous plain [0.209, 0.259, 0.219] et sous le seuil
    1/6+0.15≈0.317). Ce nul est REPRODUCTIBLE, pas un budget insuffisant : 3000 épisodes (seed 0)
    et rank=64/lr=0.1 (seeds 0,1) donnent le MÊME plancher (~0.15-0.19). Verdict scientifique n=12,
    Tâche 3 : ce nul pourrait être le finding final du sous-projet, ou un axe différent (méthode de
    crédit, tâche de combinaison plus simple) pourrait renverser — pas cette recherche bornée-ci."""
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0, 1, 2], episodes=600, n_agents=16, K=6, task="composition")
    bar = 1 / 6 + 0.15
    assert r["plain_median"] <= bar, r              # plain reste nul (reproduit l'étalon LANG-MEMORY)
    assert r["bilinear_median"] <= bar, r            # FINDING : bilinéaire ne décolle PAS non plus
    assert not r["unlocked"], r


def test_bilinear_noop_on_recall():
    """NO-OP : le pur-rappel (que le plain apprend déjà vite) reste appris en bilinéaire (pas de
    régression) — ET prouve que l'instrument N'EST PAS structurellement bloqué à `bilinear_median`
    bas (cf. commentaire CALIBRATED) : le même code produit un score ÉLEVÉ ici, bas sur la
    composition. Budget borné : seeds=[0,1,2], episodes=150, n_agents=16, K=6 (wall mesuré ≈23s).
    Per-seed bilinéaire mesuré (2026-08-03) : [0.608, 0.688, 0.712], tous >> seuil 1/6+0.15≈0.317
    (plus lent que plain [0.975, 0.958, 1.0] à ce budget, mais clairement au-dessus du seuil)."""
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=[0, 1, 2], episodes=150, n_agents=16, K=6, task="recall")
    assert r["bilinear_median"] > 1 / 6 + 0.15, r    # bilinéaire n'abîme pas le rappel
