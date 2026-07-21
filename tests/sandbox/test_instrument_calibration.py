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
