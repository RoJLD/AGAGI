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
# Fonctions capturees par l'HEURISTIQUE DE NOMMAGE mais qui ne produisent AUCUNE affirmation
# scientifique. La declaration exige un MOTIF : on ne se debarrasse pas d'une ligne, on justifie
# qu'elle n'a rien a faire la. Sans ce mecanisme, le baseline confondait « dette reelle » et « faux
# positif », et le compteur de non-calibres ne disait pas ce qu'il annoncait.
NOT_AN_INSTRUMENT = {
    "tools/is_machine_idle.py::verdict": "decide si la MACHINE est inoccupee (processus biosphere "
               "actifs, age du WAL) pour ordonnancer des jobs. Infrastructure, aucune affirmation "
               "sur le monde ni sur un agent.",
}

CALIBRATED = {
    # P2.30 (2026-09-01) : calibre PAR INJECTION (monkeypatch des `*_survival_eras`), sans simuler.
    # Un DEFAUT a ete trouve en le faisant, dans `ablation_verdict` (fichier d'une session
    # PARALLELE en cours -- non modifie) : la branche `collapse` rend X_DEMANDED SANS consulter
    # `why`, donc un bras intact SOUS le plancher declare produit un FAUX POSITIF. Documente par un
    # `xfail(strict=True)` qui ECHOUERA le jour de la correction.
    "verdict_demand_marker": ["collapse:positive", "decoy:neutral", "floor:known-gap-xfail"],
    # P2.29 (2026-09-01) : premier instrument SIMULANT UN MONDE calibre -- PAR INJECTION, sans
    # simuler une seule ere. `run_sweep` accepte `run_era_fn` : on lui impose une DOSE CONNUE et on
    # verifie qu'il la RETROUVE (calibration par PREDICTION, celle que CLAUDE.md prefere). Le cas
    # decisif est l'APPARIEMENT : bruit de 161x entre seeds, dose de +50 % retrouvee a 1.5000
    # EXACTEMENT -- personne ne testait que le design apparie fait ce pour quoi il existe.
    "run_sweep": ["no-op-exact", "prediction:dose-recovered", "pairing:cancels-noise",
                  "specificity:efficiency-not-competence"],
    # P2.28 (2026-09-01) : les 8 derniers verdicts PURS. AUCUN defaut -- c'est le resultat. Trois
    # sont exemplaires et gardent chacun une chose DIFFERENTE : la TAILLE D'ECHANTILLON
    # (_verdict_coordination, n>=20), le PREREQUIS d'entonnoir (_verdict_craft_wall, sans forage le
    # craft ne veut rien dire), et le fait que LA QUESTION SOIT BIEN POSEE (readout_verdict : si le
    # plafond supervise ne depasse pas le hasard, juger le RL n'apprend rien). Trois questions
    # distinctes ; un instrument peut echouer sur l'une en reussissant les autres.
    "_verdict_coordination": ["sample-size", "coordinated", "independent"],
    "_verdict_craft_wall": ["funnel-prerequisite", "wall-confirmed", "monotone"],
    "readout_verdict": ["invalid-target", "rl-recovers", "credit-gated"],
    "credit_verdict": ["bias-not-rarity", "rarity-also-fatal"],
    "density_verdict": ["bias-is-fatal"],
    "_verdict_qd_rescue": ["absolute-floor", "rescue", "harms", "neutral"],
    "_verdict_retention": ["absolute-floor", "lever", "policy-locked"],
    "dreaming_verdict": ["four-cases", "measured-zero:concludes"],
    # P2.27 (2026-09-01) : sondage SYSTEMATIQUE des verdicts de sondes sur entree vide. 11 etaient
    # deja corrects (levee / INDETERMINE / INVALID_TARGET) et sont geles comme tels ; 3 rendaient une
    # affirmation de FOND, NEGATIVE, sur zero donnee -- dont "AUTEL_MORT" et "N_EMERGE_PAS", deux
    # conclusions que ce depot a gravees. Les deux dernieres codaient le cas vide EXPLICITEMENT.
    # ⚠️ Un ZERO MESURE n'est pas une donnee absente : `agri_verdict(0,0)` DOIT trancher.
    "funnel_verdict": ["empty:refused", "negative:legitimate"],
    "distress_verdict": ["empty:refused", "positive:distress"],
    "compute_emergence_verdict": ["empty:refused", "positive:emerge"],
    "agri_verdict": ["measured-zero:concludes"],
    "_verdict_tom_emergence": ["measured-zero:concludes"],
    "_verdict_horizon": ["empty:indeterminate"],
    "nav_verdict": ["empty:invalid-target"],
    "energy_verdict": ["empty:invalid-target"],
    "unresolved_verdicts": ["empty:empty-list"],
    # P2.26 (2026-09-01) : les 6 verdicts restants de lewis_survival_sweep. Sondage systematique sur
    # entree vide : 5 sur 6 etaient DEJA corrects (2 levent, 3 rendent INDETERMINE). Seul
    # `_verdict_evolve_nav` concluait -- et sa docstring documentait le choix (« traj vide ->
    # SUBSTRAT BLOQUE »), donc c'etait une DECISION, prise dans la seule direction ou un verdict
    # fabrique passe inapercu. `_verdict_approach` et `_verdict_reach` exigent LA CELLULE dont ils
    # dependent, pas seulement des donnees : motif de reference, gele comme tel.
    "_verdict_evolve_nav": ["empty:refused", "progress", "stagnation:legitimate"],
    "_verdict_landing": ["empty:raises"],
    "_verdict_forage": ["empty:raises"],
    "_verdict_approach": ["missing-cell:indeterminate", "thresholds:discriminated"],
    "_verdict_reach": ["missing-cell:indeterminate", "thresholds:three-zones"],
    "_verdict_deconfound": ["missing-frozen-cell:indeterminate"],
    # P2.25 (2026-09-01) : les 2 verdicts S2 restants. `verdict_within_subject` portait la MEME
    # cecite au plancher que `s2_verdict` -- et c'est le MARQUEUR DE DEMANDE transversal (4
    # modalites). `verdict_from_survival_cmps` ne PEUT PAS se garder (il ne recoit que p/cliff) :
    # l'appelant declare. Son levee sur entree vide est GELEE comme comportement CORRECT.
    "verdict_within_subject": ["floor:refused", "positive:causal-signal"],
    "verdict_from_survival_cmps": ["declared-degeneracy", "no-declaration:normal", "empty:raises"],
    # P2.24 (2026-09-01) : les 4 verdicts « a gate » de lewis_survival_sweep. Deux defauts, tous deux
    # penchant vers le NEGATIF : entree vide -> affirmation de fond ; `zip` tronque silencieusement
    # -> un "BARREAU TROUVE" devenait "PAS DE RUNG" (verdict INVERSE). La specificite gele que le
    # negatif LEGITIME (donnees completes, rien ne franchit) reste rendu.
    "tools/lewis_survival_sweep.py::_verdict": ["empty:refused", "truncated:refused", "negative:legitimate", "positive:rung-found"],
    "_verdict_apex": ["empty:refused", "truncated:refused", "negative:legitimate"],
    "_verdict_metab": ["empty:refused", "truncated:refused", "negative:legitimate"],
    "_verdict_surprise": ["empty:refused", "truncated:refused", "negative:legitimate"],
    # P2.23 (2026-09-01) : famille `disjoint_heads`, 8 verdicts a vote majoritaire calibres EN LOT.
    # Defaut commun corrige : une liste VIDE rendait un verdict DE FOND (`_verdict_disjoint([])`
    # -> "DISJOINT_NEUTRAL", une affirmation sans AUCUNE donnee -- classes E18 + E4). Les seuils
    # GELES ne sont pas touches. Cas structurels : refus sur n=0, discrimination des deux extremes,
    # existence d'une zone MEDIANE (majorite stricte), frontieres inclusives de `_verdict_lr`.
    # ⚠️ `_verdict_capacity` et `_verdict_v4` sont des noms EN COLLISION -> declarations QUALIFIEES.
    "_verdict_disjoint": ["empty:refused", "extremes:discriminated", "middle:exists"],
    "_verdict_confound": ["empty:refused", "extremes:discriminated", "middle:exists"],
    "_verdict_correlated": ["empty:refused", "extremes:discriminated", "middle:exists"],
    "_verdict_v3": ["empty:refused", "extremes:discriminated", "middle:exists"],
    "_verdict_lr": ["empty:refused", "extremes:discriminated", "middle:exists", "thresholds:inclusive"],
    "tools/disjoint_heads_capacity.py::_verdict_capacity": ["empty:refused", "extremes:discriminated", "middle:exists"],
    "tools/disjoint_heads_v4.py::_verdict_v4": ["empty:refused", "extremes:discriminated", "middle:exists"],
    "tools/disjoint_heads_synergy.py::_verdict_v4": ["empty:refused", "extremes:discriminated", "middle:exists"],
    # P2.22 (2026-09-01) : l'instrument qui tranche « ce nul est-il reel ou fabrique par un
    # plancher ? » (classe E3), et sa garde donneuse `_survivable` -- reutilisee le meme jour pour
    # armer la degenerescence de `s2_verdict`. Un instrument qui sert d'etalon a un autre se
    # calibre en premier. Les 4 branches + les 3 regimes de la garde sont geles.
    "regime_diagnostic_verdict": ["floor-confound", "underpower", "real-null", "ambiguous"],
    # P2.21 (2026-09-01) : `_decomp_verdict` avait ZERO test et un CONTROLE NEGATIF (L0, la cellule
    # sans aucun levier) entraine puis JAMAIS lu -- « BOTH-NECESSARY » ne pouvait pas etre refute
    # par le cas qui le refute le plus simplement (classe E1). Les 5 branches sont gelees.
    "_decomp_verdict": ["degenerate:L0-composes", "positive:both-necessary",
                        "separation:two-levers", "coherence:L2-fails"],
    # P2.20 (2026-09-01) : E14 -- `sign_p` etait CALCULE puis JETE dans trois verdicts, alors que
    # `compute_ab_verdict` avait recu la garde. Contre-exemple gele : la configuration PUBLIEE de
    # D2 (+47 %, 7/8 seeds, sign_p=0.070) bascule EFFICACE -> NEUTRE. Specificite : 12 seeds
    # unanimes conservent leur verdict. `fidelity_verdict` corrige en plus une ASYMETRIE (G_INUTILE
    # n'exigeait ni majorite ni sign_p, G_FIDELE exigeait la majorite).
    "compute_sweep_verdict": ["underpowered:D2-published", "positive:powered"],
    "compute_transfer_verdict": ["underpowered:both-directions", "positive:powered"],
    "fidelity_verdict": ["symmetry:both-labels", "underpowered:both-directions"],
    # P2.19 (2026-09-01) : garde de DÉGÉNÉRESCENCE de l'instrument FONDATEUR de G0. Quatre
    # branches : les deux cas CERTAINS (plancher et plafond, variance nulle des deux côtés), le
    # cas DÉCLARÉ (étendue réelle, plancher passé par l'appelant — régime exact de WARM-002), et
    # la SPÉCIFICITÉ (un vrai signal survit, dont le régime publié d'EDR-112).
    "s2_verdict": ["floor:certain", "ceiling:certain", "floor:declared", "positive:real-signal"],
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
    # 2026-09-01, revue adversariale du graphe AGI-Taxonomy : la garde `functional_aliasing` de
    # LANG-MEMORY donnait 'pass' sur le SEUL critère `leakage <= tol`, sans jamais vérifier que le bras
    # CONTROL est VIVANT — motif E3 (« métrique dégénérée lue comme pas d'effet ») que `_degeneracy`
    # bloque sur le bras PRINCIPAL et que ce chemin contournait. La fonction de décision est extraite en
    # `alias_guard_verdict` (pure, sans entraînement) et calibrée sur les DEUX dégénérescences ATTESTÉES
    # (plancher `train_control=False` ; plafond `[1.0]*3` vs `[1.0]*3` de
    # results/lang_memory_diagnostic.json:30), plus le POSITIF qui prouve que la garde n'est pas
    # devenue vacueuse, la FUITE (comportement historique préservé) et l'APPARIEMENT par seed.
    "alias_guard_verdict": ["floor:degenerate", "ceiling:degenerate", "surgical:positive",
                            "leak:negative", "seeds:pairing"],
    # Le terme BILINÉAIRE débloque-t-il la composition ? Le nul de la Tâche 2 (REINFORCE/2-pas défaut,
    # `same_tick=False, credit_mode="reinforce"`) était PROVISOIRE : la revue adversariale a identifié
    # 2 confonds — CRÉDIT (`learn_episode` détache H à CHAQUE pas, sévrant le gradient encode->usage) et
    # RÉTENTION (key au pas 0, q au pas 1 — le bilinéaire doit porter key à travers un tick). Tâche 3
    # (2026-08-03) a ajouté 2 leviers optionnels (défauts = comportement Tâche 2 INCHANGÉ) : `same_tick`
    # (key+q dans LA MÊME observation, 1 pas — lève la rétention) et `credit_mode="supervised"` (BPTT non
    # tronqué via `imitate_episode_bptt` — lève le crédit). ⚠️ MESURÉ : en levant les DEUX confonds à la
    # fois (`same_tick=True, credit_mode="supervised"`), le bilinéaire APPREND (q+key)%K quasi-parfaitement
    # (médiane 0.932, 12/12 seeds > 0.89) alors que plain reste au plancher (médiane 0.271, 12/12 seeds
    # < 0.31) -> `unlocked=True`, SÉPARATION TOTALE par-seed. Mais lever le crédit SEUL (2-pas,
    # `credit_mode="supervised", same_tick=False`) NE SUFFIT PAS : bilinéaire reste au plancher (médiane
    # 0.178, même SOUS plain 0.218) -> le confond dominant du nul de la Tâche 2 était la RÉTENTION, pas le
    # crédit seul. Le bilinéaire low-rank PEUT représenter le produit q·key (capacité représentationnelle
    # prouvée), mais ne résout PAS, par lui-même, le portage de key à travers un tick récurrent. Verdict
    # n=12 sur les 2 conditions, cf. tests ci-dessous + `docs/EDR/EDR-BILINEAR_...md`.
    # ⚠️ E19, 2026-09-01 — la phrase « lever le crédit SEUL ne suffit pas -> le confond dominant était la
    # RÉTENTION » est SUSPENDUE : elle est conditionnée à `lr=0.02` (:163). MESURÉ n=12 en ne changeant
    # QUE le pas : 2-pas supervisé -> bilinéaire 0.1789 / `unlocked=False` à lr=0.02 (reproduit 0.178) mais
    # 0.3797 / `unlocked=True` à lr=0.002, séparation par-seed TOTALE (0.2016 < 0.3500, 0/144). Le régime
    # à UN pas (`same_tick=True`, le résultat PHARE) n'est PAS touché. Branches : le régime 2-pas est
    # désormais couvert par `..._is_lr_dependent`, qui gèle la BASCULE au lieu du nul.
    "run_bilinear_composition_probe": ["same_tick:positive", "two_step:lr_artifact", "recall:noop"],
    # Diagnostic retain+compose. Positif = same_tick (le bilinéaire compose 2 entrées co-présentes -> >bar) ;
    # négatif = oracle DÉCORRÉLÉ (key aléatoire en état -> ne porte pas la bonne info -> plancher). Générateur A.
    # ⚠️ CLASSE E19, 2026-09-01 — la déclaration `["*"]` (« instrument sans branches ») était FAUSSE et a
    # coûté le verdict d'un record entier : la sonde a un paramètre de RÉGIME énuméré (`conditions=`), et
    # les DEUX branches calibrées (`same_tick` :51-52 et `oracle_decorrelated` :53-58) sont des conditions
    # à UN SEUL `_step`. La branche qui PORTE le verdict (`learned`, DEUX `_step` + BPTT, :59-61) n'était
    # PAS calibrée — et c'est exactement là que `lr=0.02` diverge (batch effectif = 1, chaque agent porte
    # ses PROPRES W/U/V/W_bl, `src/agents/backend_torch.py:85-86`). Un « OK » du cliquet ne vaut QUE dans
    # les régimes des cas gelés : un contrôle positif du régime FACILE ne calibre PAS le régime DUR.
    # La branche `learned:lr_artifact` gèle la bascule de verdict (cf. le contre-exemple en fin de fichier).
    "run_retain_compose_diagnostic_probe": ["same_tick:positive", "oracle_decorrelated:floor",
                                            "learned:lr_artifact"],
    # E19, garde de pré-vol NÉE le 2026-09-01 et calibrée dans la MÊME passe (rituel du registre).
    # Détectée par le cliquet via le motif `\\w*verdict\\w*` — et c'en EST un : elle rend un jugement
    # binaire (« ce nul est-il un artefact de réglage ? ») sur un balayage de `lr`, donc elle peut
    # PRODUIRE un résultat comme n'importe quel instrument. Ses deux cas sont des réponses CONNUES de
    # signes opposés, toutes deux MESURÉES dans ce dépôt : `artifact:fires` (RETAIN-COMPOSE, écart au bras
    # de référence 0.798 -> 0.022, closure 0.972 -> LÈVE) et `structural:spares` (BILINEAR/plain, 0.652 ->
    # 0.594, closure 0.089 -> ne lève PAS, alors qu'un critère de SEUIL absolu aurait flagué ce vrai
    # négatif). ⚠️ Les deux cas vivent dans `tests/sandbox/test_experiment_preflight.py`
    # (`test_optimizer_sweep_REFUSES_the_retain_compose_null` / `..._SPARES_the_bilinear_structural_null`),
    # là où sont testées toutes les assertions de pré-vol — pas dans ce fichier. Purement numériques.
    "assert_verdict_invariant_to_optimizer": ["artifact:fires", "structural:spares"],
    # DELAYED-COORD : sonde de Lewis DIFFÉRÉE, instrument NÉ le 2026-09-01 et calibré dans la MÊME passe
    # (rituel du cliquet). Deux réponses CONNUES ANALYTIQUEMENT, sans rien supposer de l'apprentissage :
    # (1) `mute-channel:chance` — à `flip_p=1.0` le sender ne voit qu'un tirage UNIFORME, donc le canal ne
    #     porte AUCUNE information sur la cible et le plafond de Bayes vaut EXACTEMENT 1/K. Toute valeur
    #     au-dessus signalerait une FUITE de la cible vers le readout — la classe d'erreur exacte de
    #     MEM-PERCEPTION itération 1 (l'encodage du contrôle portait la réponse). Couvre le pipeline
    #     COMPLET, entraînement inclus.
    # (2) `mute-channel:arm-symmetry-exact` — no-op EXACT, la forme de test la plus forte. La DATE de
    #     présentation de la cible est le SEUL facteur censé séparer RETAIN de PRESENT ; à `flip_p=1.0`
    #     cette date devient sans objet, donc les deux bras doivent rendre des accuracies BIT-IDENTIQUES.
    #     Casse dès qu'une édition rompt l'identité de construction (longueur de séquence, nombre de
    #     forwards, ou simplement un tirage RNG de plus dans un bras) — c'est-à-dire la contrainte non
    #     négociable du design, rendue exécutable au lieu d'être seulement écrite.
    # (3) `untrained:floor` — `episodes=0` : PINGLE LE PLANCHER de l'instrument à 1/K. Portée VOLONTAIREMENT
    #     modeste, et il faut le dire : un readout non entraîné est à la chance QUELLE QUE SOIT son entrée,
    #     donc ce cas n'attrape PAS une fuite (c'est (1) qui le fait, prouvé sensible : porteur propre ->
    #     0.490 contre une barre à 0.257). Ce qu'il attrape vraiment, c'est un chemin de SCORE cassé —
    #     accuracy comparée au leurre plutôt qu'à la cible, ou éval dégénérée. Utile parce qu'un verdict
    #     « effondrement vers ~0.17 » n'est lisible que si l'on sait mesurer ce que vaut le plancher (E14).
    # ⚠️ NON couvert : le contrôle positif « générateur A » (canal ORACLE -> RETAIN s'effondre, PRESENT
    # inerte) MESURÉ hors-test (0.436 -> 0.148 ; 0.391, Δ 0.026) mais qui exige un paramètre `sender_mode`
    # que la sonde n'expose pas encore — il revient à la tâche qui ajoutera le bras ALIAS et le verdict.
    "run_delayed_coordination_demand_probe": ["mute-channel:chance", "mute-channel:arm-symmetry-exact",
                                              "untrained:floor"],
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


# ------------------------------------------------- ablation_verdict borné des DEUX côtés (E3, 2026-09-01)
# Revue adversariale du graphe AGI-Taxonomy : `decoy := ratio <= decoy_ceiling` était UNILATÉRAL — un
# ratio 0.596 (le bras de contrôle Lewis MULTIPLIÉ par 1.68 par l'ablation, 0.592 -> 0.994) passait pour
# X_DECOY (« ablation inerte »), donc `specificity_control='pass'`. `_degeneracy` ne l'attrapait pas :
# elle ne teste que « intact au plancher » et « les deux bras au plafond », or ici l'intact est VIVANT et
# seul l'ABLÉ approche le plafond déclaré. ⚠️ `n_floor=3` (au lieu du défaut 12) : les 3 tests ci-dessous
# portent n=3 points de mesure ; sous le défaut, `n < n_floor` fait tomber les TROIS cas en `INCONCLUSIVE`
# avant même d'atteindre la branche collapse/decoy/inverted testée — ça ne change ni les données (les
# accuracies mesurées) ni le sens des cas, seulement la puissance déclarée pour que le test touche la
# décision qu'il prétend calibrer.

def test_ablation_verdict_REFUSES_an_inverted_effect_as_decoy():
    """CONTRE-EXEMPLE GELÉ (classe E3) — mesuré le 2026-09-01 sur le bras de contrôle Lewis
    sous H-reset : l'ablation MULTIPLIE le contrôle par 1.68 (0.592 -> 0.994), donc ratio 0.596.
    L'ancienne règle `decoy := ratio <= 1.3` classait ça `X_DECOY`, lu « ablation inerte », donc
    `specificity_control='pass'`. Un effet massif de SIGNE INVERSE n'est pas une inertie."""
    from tools.demand_marker import ablation_verdict
    ci = [0.510, 0.658, 0.592]
    ca = [0.988, 0.994, 0.994]
    r = ablation_verdict(ci, ca, intervention_verified=True, floor=1 / 6, ceiling=1.0, n_floor=3)
    assert r["verdict"] != "X_DECOY", r
    assert r["ratio"] < 1.0, r


def test_ablation_verdict_STILL_accepts_a_genuine_decoy():
    """CONTRÔLE POSITIF — sans lui, une garde qui refuse TOUT serait aussi inutile qu'une garde
    qui accepte tout. Un vrai decoy (ablation réellement inerte, ratio ~1.0) doit RESTER X_DECOY."""
    from tools.demand_marker import ablation_verdict
    ci = [0.592, 0.658, 0.610]
    ca = [0.590, 0.652, 0.615]
    r = ablation_verdict(ci, ca, intervention_verified=True, floor=1 / 6, ceiling=1.0, n_floor=3)
    assert r["verdict"] == "X_DECOY", r


def test_ablation_verdict_still_collapses_a_real_demand():
    """NON-RÉGRESSION du sens principal : une vraie demande reste X_DEMANDED."""
    from tools.demand_marker import ablation_verdict
    r = ablation_verdict([0.633, 0.654, 0.621], [0.194, 0.175, 0.177],
                         intervention_verified=True, floor=1 / 6, ceiling=1.0, n_floor=3)
    assert r["verdict"] == "X_DEMANDED", r


def test_ablation_verdict_inverted_still_defers_to_degeneracy():
    """FIX ROUND 1 (revue, Constat 1 Important). La branche `decoy` fait
    `"INCONCLUSIVE_DEGENERATE" if why else "X_DECOY"` — la branche `inverted` rendait
    `INCONCLUSIVE_INVERTED` INCONDITIONNELLEMENT, sans jamais relire `why`. Scénario mécanique :
    un bras intact au PLANCHER déclaré (`why` non-None) avec un ablé normal produit lui aussi un
    ratio bas -> serait étiqueté « inversé » au lieu de « dégénéré », masquant exactement ce que
    `_degeneracy` existe pour attraper. Ici l'intact (médiane 0.15) est SOUS le plancher déclaré
    (0.2) : le verdict doit rester `INCONCLUSIVE_DEGENERATE`, jamais `INCONCLUSIVE_INVERTED`."""
    from tools.demand_marker import ablation_verdict
    ci = [0.15, 0.16, 0.14]
    ca = [0.9, 0.88, 0.92]
    r = ablation_verdict(ci, ca, intervention_verified=True, floor=0.2, ceiling=1.0, n_floor=3)
    assert r["ratio"] < 1.0, r                          # bien dans la zone "inverted" en amplitude
    assert r["verdict"] == "INCONCLUSIVE_DEGENERATE", r  # PAS INCONCLUSIVE_INVERTED : `why` prime
    assert r["degenerate"] is True and r["why"], r


def test_ablation_verdict_replays_the_two_carved_edges_negative_controls():
    """FIX ROUND 1 (revue, Constat 2 Important). `check_agi_taxonomy.py` ne rappelle JAMAIS
    `ablation_verdict` : il valide des chaînes FIGÉES dans `data/agi_taxonomy/demands.json`, donc le
    Step 5 du brief (non-régression via `check_agi_taxonomy.py`) est structurellement AVEUGLE à un
    changement de la fonction de décision. Ce test rejoue les DEUX contrôles de spécificité
    (`specificity_control='pass'`) des deux arêtes déjà gravées, avec les accuracies RÉELLES à n=12
    persistées par les probes, à travers la NOUVELLE borne bilatérale.

    Sources (mêmes params que la production : `intervention_verified=True, floor=1/6, ceiling=1.0`,
    `tools/perception_coordination_demand_probe.py:130-132` et
    `tools/memory_perception_demand_probe.py:179-181`, K=6 -> floor=1/6) :
      - NO-COORD (arête `language -> perception`) : `results/sp2_edge_accuracies.json` champs
        `nocoord_intact`/`nocoord_ablated` (ratio publié 0.9885,
        `docs/EDR/EDR-LANG-PERCEPTION_Coordination_Demands_Perception.md:36`).
      - PRESENT (arête `memory -> perception`) : `results/mem_perception_edge_accuracies.json` champs
        `present_intact`/`present_ablated` (ratio publié 0.984,
        `docs/EDR/EDR-MEM-PERCEPTION_Memory_Demands_Perception.md:71`).
    Les deux ratios (~0.99, ~0.98) sont bien à l'INTÉRIEUR de la nouvelle borne bilatérale
    [1/1.3≈0.769, 1.3] : ni l'un ni l'autre n'était donc jamais dans la zone `inverted`, et les deux
    doivent RESTER `X_DECOY` -- sinon la nouvelle borne invaliderait une arête déjà gravée."""
    from tools.demand_marker import ablation_verdict
    floor = 1.0 / 6

    nocoord_intact = [0.731249988079071, 0.7328125238418579, 0.7593749761581421, 0.7171875238418579,
                      0.7281249761581421, 0.739062488079071, 0.7593749761581421, 0.7718750238418579,
                      0.7093750238418579, 0.753125011920929, 0.7437499761581421, 0.754687488079071]
    nocoord_ablated = [0.7593749761581421, 0.7281249761581421, 0.7515624761581421, 0.7406250238418579,
                       0.7515624761581421, 0.768750011920929, 0.737500011920929, 0.770312488079071,
                       0.721875011920929, 0.7562500238418579, 0.734375, 0.7484375238418579]
    r_coord = ablation_verdict(nocoord_intact, nocoord_ablated, intervention_verified=True,
                               floor=floor, ceiling=1.0)
    assert r_coord["verdict"] == "X_DECOY", (
        f"NO-COORD (arête language->perception) invalidée par la nouvelle borne : {r_coord}")
    assert r_coord["ratio"] == pytest.approx(0.9885416428248087, rel=0.02)

    present_intact = [0.47187501192092896, 0.4984374940395355, 0.39531248807907104, 0.4937500059604645,
                      0.4859375059604645, 0.4859375059604645, 0.550000011920929, 0.453125,
                      0.4671874940395355, 0.4828124940395355, 0.620312511920929, 0.4781250059604645]
    present_ablated = [0.49687498807907104, 0.48906248807907104, 0.4281249940395355, 0.53125,
                       0.46562498807907104, 0.49531251192092896, 0.5406249761581421, 0.4703125059604645,
                       0.4375, 0.512499988079071, 0.5874999761581421, 0.4453125]
    r_mem = ablation_verdict(present_intact, present_ablated, intervention_verified=True,
                             floor=floor, ceiling=1.0)
    assert r_mem["verdict"] == "X_DECOY", (
        f"PRESENT (arête memory->perception) invalidée par la nouvelle borne : {r_mem}")
    assert r_mem["ratio"] == pytest.approx(0.9841269841269841, rel=0.02)


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


# --- alias_guard_verdict : la garde de DÉGÉNÉRESCENCE du bras CONTROL (armée le 2026-09-01) --------
# Cas PUREMENT NUMÉRIQUES (aucun entraînement, aucun torch) : ils testent la LOGIQUE de la garde, pas
# le harnais. Contre-exemples GELÉS = les deux configurations RÉELLES qui ont produit un
# `functional_aliasing='pass'` vide de sens. K=6 -> floor=1/6=0.16667, ceiling=1.0, tol=0.05.

_LM_FLOOR = 1.0 / 6                       # plancher de chance à K=6, tel que passé par la sonde
_LM_XRESP = 0.40                          # réponse du bras PRINCIPAL, largement > tol (ablation qui mord)


def test_alias_guard_refuses_pass_when_control_was_never_trained():
    """DÉGÉNÉRESCENCE PLANCHER — contre-exemple GELÉ, la config `train_control=False`.

    Config réelle : `train_control=False` SAUTE le bloc d'entraînement CONTROL
    (tools/language_memory_demand_probe.py:161-162) -> les deux mesures CONTROL restent au hasard
    (1/K=0.167). Le record le dit explicitement — docs/EDR/EDR-LANG-MEMORY_Language_Demands_Memory.md
    :120-124 : « `control_intact` et `control_ablated` restent tous deux proches du hasard (poids jamais
    entraînés sur cette tête), donc `functional_aliasing="pass"` y est **vide de sens** — une différence
    quasi nulle entre deux mesures de hasard est garantie par construction, pas une preuve de chirurgie ».
    L'ancienne règle (leakage <= tol SEUL) rendait 'pass' ici."""
    from tools.language_memory_demand_probe import alias_guard_verdict
    ci = [0.171, 0.163, 0.168, 0.159, 0.174, 0.166, 0.170, 0.161, 0.167, 0.172, 0.164, 0.169]
    ca = [0.166, 0.170, 0.161, 0.168, 0.163, 0.172, 0.165, 0.167, 0.160, 0.169, 0.171, 0.164]
    r = alias_guard_verdict(ci, ca, x_response=_LM_XRESP, floor=_LM_FLOOR, ceiling=1.0)
    assert r["leakage"] <= 0.05, r["leakage"]                 # l'ANCIEN critère est bien satisfait…
    assert r["alias_verdict"] == "DEGENERATE_CONTROL", r      # …et ne suffit PLUS
    assert r["functional_aliasing"] == "fail" and r["control_degenerate"] is True, r
    assert "jamais appris" in r["control_why"], r["control_why"]


def test_alias_guard_refuses_pass_when_control_is_saturated():
    """DÉGÉNÉRESCENCE PLAFOND — contre-exemple GELÉ, valeurs RÉELLES du diagnostic.

    results/lang_memory_diagnostic.json:30 (config `train_control=True, weight_decay=0.0,
    episodes=3000, D=0, seeds=[0,1,2]`) porte littéralement :
        "control_intact": [1.0,1.0,1.0], "control_ablated": [1.0,1.0,1.0],
        "functional_aliasing_note": "CONTROL sature et reste chirurgical (leakage=0.0) ICI, ..."
    Deux bras SATURÉS à 1.0 donnent `leakage = 0` MÉCANIQUEMENT : le 'pass' ne mesure rien. C'est
    exactement le cas que `_degeneracy` bloque sur le bras principal (« les deux bras au PLAFOND
    déclaré ») et que le calcul de leakage contournait."""
    from tools.language_memory_demand_probe import alias_guard_verdict
    ci = ca = [1.0] * 12                                       # n=12 ; le diagnostic réel portait n=3
    r = alias_guard_verdict(ci, ca, x_response=_LM_XRESP, floor=_LM_FLOOR, ceiling=1.0)
    assert r["leakage"] == 0.0                                 # « leakage=0.0 » du diagnostic
    assert r["alias_verdict"] == "DEGENERATE_CONTROL", r
    assert r["functional_aliasing"] == "fail", r
    # les deux bras EXACTEMENT à 1.0 : le `_degeneracy` du bras CONTROL tire aussi, pas seulement la marge
    assert r["control_demand"]["degenerate"] is True and "PLAFOND" in r["control_demand"]["why"]


def test_alias_guard_still_passes_a_LIVING_surgical_control():
    """CONTRÔLE POSITIF DE LA GARDE (indispensable : une garde qui refuse TOUT est aussi inutile
    qu'une garde qui accepte tout). CONTROL VIVANT — médiane ~0.58, bien au-dessus du plancher 0.167
    et bien sous le plafond, dans la bande MESURÉE du récit (« CONTROL, lui, APPREND bien (médianes
    0.54-0.61) », docstring de tools/language_memory_demand_probe.py) — et CHIRURGICAL : le H-reset
    ne le fait pas bouger de plus de `tol`. -> SURGICAL, `functional_aliasing='pass'`."""
    from tools.language_memory_demand_probe import alias_guard_verdict
    ci = [0.58, 0.61, 0.55, 0.60, 0.57, 0.59, 0.54, 0.62, 0.56, 0.60, 0.58, 0.57]
    ca = [0.57, 0.60, 0.56, 0.59, 0.58, 0.58, 0.55, 0.60, 0.55, 0.61, 0.57, 0.58]
    r = alias_guard_verdict(ci, ca, x_response=_LM_XRESP, floor=_LM_FLOOR, ceiling=1.0)
    assert r["alias_verdict"] == "SURGICAL" and r["functional_aliasing"] == "pass", r
    assert r["control_degenerate"] is False and r["control_why"] is None, r
    assert r["leak_seeds"] == 0, r["leak_per_seed"]


def test_alias_guard_leak_verdict_is_unchanged_by_the_new_rule():
    """NON-RÉGRESSION DU NÉGATIF : un CONTROL VIVANT qui FUIT (il se dégrade sous le même H-reset)
    reste FUNCTIONAL_LEAK. La garde de dégénérescence n'invalide QUE le nul (note de conception de
    `ablation_verdict`) : un bras qui BOUGE est vivant par définition, l'ordre des branches
    (fuite AVANT dégénérescence) l'encode."""
    from tools.language_memory_demand_probe import alias_guard_verdict
    ci = [0.95, 0.93, 0.96, 0.94, 0.95, 0.92, 0.97, 0.94, 0.93, 0.96, 0.95, 0.94]
    ca = [0.20, 0.18, 0.22, 0.17, 0.19, 0.21, 0.16, 0.20, 0.18, 0.19, 0.22, 0.17]
    r = alias_guard_verdict(ci, ca, x_response=_LM_XRESP, floor=_LM_FLOOR, ceiling=1.0)
    assert r["alias_verdict"] == "FUNCTIONAL_LEAK" and r["functional_aliasing"] == "fail", r
    assert r["leak_seeds"] == 12, r["leak_per_seed"]


def test_alias_guard_vacuous_ablation_takes_priority_unchanged():
    """NON-RÉGRESSION : si le bras PRINCIPAL ne bouge pas (`x_response <= tol`), la question de la
    chirurgie ne se pose pas -> VACUOUS_ABLATION, avant toute autre branche (comportement historique)."""
    from tools.language_memory_demand_probe import alias_guard_verdict
    r = alias_guard_verdict([0.58] * 12, [0.57] * 12, x_response=0.01, floor=_LM_FLOOR, ceiling=1.0)
    assert r["alias_verdict"] == "VACUOUS_ABLATION" and r["functional_aliasing"] == "fail", r


def test_alias_guard_leak_seeds_separates_two_sets_with_the_SAME_aggregate_median():
    """APPARIEMENT PAR SEED — ce que la médiane AGRÉGÉE ne peut pas voir.

    `demand_marker` est l'instrument WITHIN-SUBJECT et la SÉPARATION PAR SEED porte les deux verdicts
    gravés du graphe (« 12/12 seeds à recouvrement ZÉRO »). Ici deux jeux ont EXACTEMENT la même
    médiane agrégée de fuite (0.02, donc le même `leakage`, donc le même `alias_verdict`) mais des
    profils par seed OPPOSÉS : chirurgie propre (12 seeds à 0.02) vs 4 seeds fuyant à 0.20. Seul
    `leak_seeds` les distingue — c'est pourquoi il est EXPOSÉ (hors décision, aucun seuil par seed
    n'étant étalonné)."""
    from tools.language_memory_demand_probe import alias_guard_verdict
    clean_i = [0.60] * 12
    clean_a = [0.58] * 12                                        # 12 seeds à 0.02 de fuite
    lumpy_i = [0.60] * 12
    lumpy_a = [0.40] * 4 + [0.58] * 4 + [0.60] * 4               # 4 seeds fuient à 0.20
    a = alias_guard_verdict(clean_i, clean_a, _LM_XRESP, floor=_LM_FLOOR, ceiling=1.0)
    b = alias_guard_verdict(lumpy_i, lumpy_a, _LM_XRESP, floor=_LM_FLOOR, ceiling=1.0)
    assert a["leakage"] == pytest.approx(b["leakage"], abs=1e-12), (a["leakage"], b["leakage"])
    assert a["alias_verdict"] == b["alias_verdict"] == "SURGICAL"   # INDISCERNABLES sur l'agrégat
    assert a["leak_seeds"] == 0 and b["leak_seeds"] == 4, (a["leak_per_seed"], b["leak_per_seed"])


def test_alias_guard_is_wired_into_the_probe_result():
    """La garde doit être BRANCHÉE, pas seulement écrite : les clés remontent bien dans le dict de
    `run_language_memory_demand_probe` (classe E4 — une vérification qui ne peut pas échouer).
    `episodes=0` -> aucun entraînement, rapide."""
    from tools.language_memory_demand_probe import run_language_memory_demand_probe
    r = run_language_memory_demand_probe(seeds=list(range(12)), episodes=0, n_agents=8, K=6, D=1,
                                         memory_mode="oracle")
    assert set(r) >= {"alias_verdict", "functional_aliasing", "leak_seeds", "control_degenerate",
                      "control_why", "leak_per_seed", "control_demand"}, sorted(r)
    # le CONTROL du mode oracle est un bypass CÂBLÉ (`g = c`, :218) -> saturé 1.0/1.0 -> dégénéré.
    assert r["alias_verdict"] == "DEGENERATE_CONTROL" and r["control_degenerate"] is True, r


# ------------------------------------------- run_bilinear_composition_probe (BILINEAR) ------------
# Le terme bilinéaire low-rank de `TorchPopulationModel` (Tâche 1, `7747b1e`) débloque-t-il
# (q+key)%K, que le substrat PLAIN ne peut pas apprendre (étalon LANG-MEMORY, 0.15-0.33) ? Le nul
# REINFORCE/2-pas de la Tâche 2 (`4bd8b8b`) était PROVISOIRE (revue adversariale, 2 confonds : CRÉDIT
# + RÉTENTION, cf. commentaire CALIBRATED ci-dessus). Tâche 3 (2026-08-03) lève les deux confonds
# séparément puis ensemble, n=12, budget borné (episodes=300, wall mesuré < 5 min/condition).
# `test_bilinear_unlocks_composition_same_tick_supervised` = le test DÉCISIF (renommé depuis
# `test_bilinear_composition_crux_finding_stays_null`, dont l'assertion "reste nul" ne survit PAS à la
# levée des deux confonds).
# ⚠️ E19, 2026-09-01 : la clause « la levée seule du crédit laisse le nul intact -> c'est la RÉTENTION,
# pas le crédit, qui était le confond dominant » est CONDITIONNÉE au pas d'apprentissage et n'est PAS
# établie. MESURÉ n=12 en ne changeant QUE `lr` : bilinéaire 2-pas 0.1789 (`unlocked=False`) à lr=0.02
# mais 0.3797 (`unlocked=True`) à lr=0.002, séparation par-seed totale (0.2016 < 0.3500, 0/144).
# Cf. `test_bilinear_composition_null_under_retention_is_lr_dependent` ci-dessous, qui gèle la bascule.
# Le POSITIF principal (same_tick, UN pas) n'est PAS touché : il ne vit pas dans le régime pathologique.

@pytest.mark.slow          # wall mesuré 107-292s (variance système) > 120s (pytest.ini) ; désélectionné
@pytest.mark.timeout(600)  # en CI rapide (-m "not slow") ; override explicite (marge sur la variance mesurée)
def test_bilinear_unlocks_composition_same_tick_supervised():
    """POSITIF DÉCISIF (générateur A, les DEUX confonds levés à la fois) : `same_tick=True` (key ET q
    dans LA MÊME observation, 1 seul pas -> lève la RÉTENTION) + `credit_mode="supervised"` (BPTT non
    tronqué via `imitate_episode_bptt` -> lève le CRÉDIT, contrairement à `learn_episode` qui détache H
    à chaque pas). Sur (q+key)%K : PLAIN reste au plancher, BILINÉAIRE APPREND quasi-parfaitement ->
    `unlocked=True`, SÉPARATION TOTALE par-seed (aucun recouvrement des 12+12 valeurs). Budget : n=12,
    episodes=300, n_agents=16, K=6, rank=16 (wall mesuré ≈292s < 5 min, << 9 min). Medians mesurés
    (2026-08-03) : plain=0.271 (12 seeds dans [0.233,0.303]), bilinéaire=0.932 (12 seeds dans
    [0.891,0.969]) — le bilinéaire low-rank PEUT représenter le produit q·key quand les deux sont
    présents au même pas (capacité représentationnelle prouvée). Ce test vit dans le régime à UN SEUL pas
    et n'est donc PAS touché par l'artefact E19. Cf.
    `test_bilinear_composition_null_under_retention_is_lr_dependent` (le nul du 2-pas, lui, BASCULE avec
    le seul `lr` : « la rétention était le confond dominant » n'est pas établi)."""
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    r = run_bilinear_composition_probe(seeds=list(range(12)), episodes=300, n_agents=16, K=6, rank=16,
                                        task="composition", same_tick=True, credit_mode="supervised")
    bar = 1 / 6 + 0.15
    assert r["plain_median"] <= bar, r                                        # plain reste au plancher
    assert r["bilinear_median"] > bar and r["unlocked"], r                    # bilinéaire décolle nettement
    assert min(r["per_seed"]["bilinear"]) > max(r["per_seed"]["plain"]), r    # séparation TOTALE par-seed


@pytest.mark.slow          # wall MESURÉ 199.7s (call) / 204.8s (session) > 120s (pytest.ini) ;
                           # détail : 92.5s le lot lr=0.02 + 109.9s le lot lr=0.002. Désélectionné en CI rapide.
@pytest.mark.timeout(600)  # override explicite (marge ~3× sur la variance système)
def test_bilinear_composition_null_under_retention_is_lr_dependent():
    """CONTRE-EXEMPLE GELÉ, classe **E19** — ce test s'appelait `..._null_under_retention_supervised` et
    assertait `bilinear_median <= bar` + `not unlocked` au SEUL `lr=0.02` : il GELAIT un artefact, et
    aurait fait échouer toute correction future du réglage. Il gèle désormais la BASCULE elle-même.

    Condition INCHANGÉE (isole la RÉTENTION, crédit déjà réparé) : `credit_mode="supervised"` +
    `same_tick=False` (2 pas, key au pas 0 / q au pas 1 — la rétention reste EXIGÉE), episodes=300,
    n_agents=16, K=6, rank=16. SEULE variable ajoutée : `lr`, désormais passé EXPLICITEMENT aux deux
    appels (le test ne dépend donc plus du défaut de la sonde, qui pourra bouger sans le casser).

    MESURÉ ICI, n=12, 2026-09-01 (les deux lots, wall 92.5s + 109.9s) :
      * `lr=0.02`  -> plain 0.2180, bilinéaire **0.1789** (SOUS plain), `unlocked=False`
                     — reproduit AU CHIFFRE PRÈS le nul publié le 2026-08-03 (0.218 / 0.178).
      * `lr=0.002` -> plain 0.1812, bilinéaire **0.3797** (> bar 0.3167), `unlocked=True`.
      * Séparation par-seed TOTALE sur le bras bilinéaire : max(lr=0.02)=0.2016 < min(lr=0.002)=0.3500,
        **0/144** chevauchement, 12/12 seeds au-dessus de la barre à lr=0.002 (signe p=2⁻¹²).
    Le nul du 2-pas et le verdict `unlocked` sont donc des propriétés du RÉGLAGE, pas du substrat : la
    conclusion « réparer le crédit SEUL ne débloque rien, le confond dominant était la RÉTENTION » est
    conditionnée à `lr=0.02` et n'est PAS établie. Même défaut, même sonde-sœur, même Adam à batch
    effectif 1 (`n_agents` n'est pas un minibatch — `src/agents/backend_torch.py:85-86`) que
    EDR-RETAIN-COMPOSE. Les chiffres du 2026-08-03 ne sont pas effacés : ils sont REPRODUITS ci-dessus et
    restent vrais À CE PAS.

    ⚠️ Ce que ce test n'affirme PAS : que le 2-pas soit RÉSOLU à lr=0.002. 0.3797 reste très loin du 0.932
    obtenu à opérandes co-présents ; il franchit une barre (0.3167) elle-même mal placée — 0.072 SOUS le
    plafond structurel mesuré du substrat plain (0.3889). Ce qui est gelé, c'est la BASCULE, pas un
    verdict de capacité."""
    from tools.bilinear_composition_probe import run_bilinear_composition_probe
    bar = 1 / 6 + 0.15
    seeds = list(range(12))
    lo = run_bilinear_composition_probe(seeds=seeds, episodes=300, n_agents=16, K=6, rank=16,
                                        task="composition", same_tick=False, credit_mode="supervised",
                                        lr=0.02)
    hi = run_bilinear_composition_probe(seeds=seeds, episodes=300, n_agents=16, K=6, rank=16,
                                        task="composition", same_tick=False, credit_mode="supervised",
                                        lr=0.002)
    # Le nul publié TIENT à lr=0.02 (aucune mesure n'est effacée)...
    assert lo["plain_median"] <= bar and lo["bilinear_median"] <= bar, lo
    assert not lo["unlocked"], lo
    # ...et il BASCULE en ne changeant QUE le pas.
    assert hi["bilinear_median"] > bar, hi
    assert hi["unlocked"], hi
    # Séparation TOTALE par-seed sur le bras testé : la bascule n'est pas un effet de médiane.
    assert min(hi["per_seed"]["bilinear"]) > max(lo["per_seed"]["bilinear"]), (lo, hi)


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


# ------------------------------------------------- run_retain_compose_diagnostic_probe (Task 1)
# H1 (rétention apprise) vs H2 (lecture d'état) sur le mur retain+compose. Budget mesuré (2026-08-04) :
# n=4 seeds, episodes=400, n_agents=16, K=6 -> ≈81s (same_tick) / ≈73s (oracle_decorrelated), chacun
# sous le timeout pytest.ini de 120s (pas de marqueur @pytest.mark.slow/@timeout requis).

def test_retain_compose_same_tick_composes():
    """POSITIF (générateur A) : le bilinéaire compose key+q CO-PRÉSENTS -> same_tick > bar. Prouve que
    l'instrument PEUT montrer la composition (sinon un oracle<=bar serait ininterprétable).
    Mesuré (2026-08-04) : same_tick_median=0.966, 4 seeds dans [0.955, 0.977], tous > bar=1/6+0.15≈0.317."""
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    r = run_retain_compose_diagnostic_probe(seeds=list(range(4)), episodes=400, n_agents=16, K=6,
                                            conditions=("same_tick",))
    assert r["same_tick_median"] > 1/6 + 0.15, r


def test_retain_compose_decorrelated_oracle_is_floor():
    """NÉGATIF : un key ALÉATOIRE injecté en état (décorrélé de la cible) ne permet PAS (q+key)%K -> plancher.
    Prouve que l'oracle mesure la LECTURE de l'état retenu, pas un artefact d'injection.
    Mesuré (2026-08-04) : oracle_decorrelated_median=0.162, 4 seeds dans [0.152, 0.178], tous <= bar≈0.317."""
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    r = run_retain_compose_diagnostic_probe(seeds=list(range(4)), episodes=400, n_agents=16, K=6,
                                            conditions=("oracle_decorrelated",))
    assert r["oracle_decorrelated_median"] <= 1/6 + 0.15, r


@pytest.mark.slow          # wall MESURÉ 51.3s (call) / 69.7s (session) — SOUS les 120s de pytest.ini,
                           # mais la variance système documentée dans ce fichier atteint 2.7× (:1607,
                           # 107->292s) : 51×2.7 = 138s dépasserait le cap et tuerait le test à tort.
@pytest.mark.timeout(600)  # override explicite. Marqueur `slow` à revoir si la variance se resserre.
def test_retain_compose_learned_verdict_is_an_lr_artifact():
    """CONTRE-EXEMPLE GELÉ de la classe **E19** — la branche `learned` est celle qui PORTE le verdict du
    record, et c'était la SEULE des trois qui n'avait aucun cas de calibration. Les deux contrôles
    ci-dessus (`same_tick`, `oracle_decorrelated`) sont des conditions à UN SEUL `_step` : par
    CONSTRUCTION, aucun ne POUVAIT voir une pathologie propre au régime à DEUX `_step`. Le cliquet
    déclarait l'instrument couvert (`["*"]`) pendant que le régime porteur du verdict ne l'était pas.

    Ce que ce test gèle : le verdict de la sonde BASCULE en ne changeant QUE le pas d'apprentissage.
    ÉTABLI n=12, episodes=600 (2026-09-01) — `same_tick` / `oracle` / `learned` :
      * `lr=0.02`  -> 0.969 / 0.971 / **0.173**  => verdict rendu `RETENTION`
      * `lr=0.002` -> 0.937 / 0.945 / **0.923**  => verdict rendu `INCONCLUSIVE`
    `learned` par seed, lr=0.02 : [0.145 … 0.192] ; lr=0.002 : [0.897 … 0.964]. Séparation TOTALE
    (min à lr=0.002 = 0.897 > max à lr=0.02 = 0.192, **0/144**), 12/12 seeds au-dessus de la barre à
    lr=0.002 (test de signe p=2⁻¹²). L'écart `learned`↔`oracle` passe de **0.798 à 0.022** : le bras testé
    REJOINT son bras de référence — signature d'un ARTEFACT, pas d'un nul de capacité (cf.
    `tools/experiment_preflight.py::assert_verdict_invariant_to_optimizer`).

    CAUSE RACINE : `n_agents=16` n'est PAS un minibatch — chaque agent porte ses PROPRES `W/U/V/W_bl`
    (`src/agents/backend_torch.py:85-86` et `:113-115`), donc la `cross_entropy` sur 16 lignes donne à
    chaque jeu de paramètres EXACTEMENT 1 exemple par pas (batch effectif = 1) sous Adam `lr=0.02`
    (`tools/retain_compose_diagnostic_probe.py:80`, signature `:101`). Les conditions à un `_step` sont
    bien conditionnées et tolèrent ce pas ; `learned` enchaîne DEUX `_step` avec BPTT et diverge. Le
    réglage avait été validé IMPLICITEMENT sur les conditions faciles, puis appliqué à la condition testée.

    Budget de CE test (réduit : 3 seeds, episodes=400 — le n=12/600 ci-dessus est l'ÉTABLISSEMENT, pas la
    garde) : wall MESURÉ 51.3 s (call) / 69.7 s (session), 2026-09-01, 1 thread. Le défaut `lr=0.02` de la
    sonde n'est PAS modifié (cela ré-écrirait silencieusement le passé et invaliderait les chiffres cités
    ici) : les deux pas sont passés EXPLICITEMENT."""
    from tools.retain_compose_diagnostic_probe import run_retain_compose_diagnostic_probe
    bar = 1/6 + 0.15
    seeds = list(range(3))
    lo = run_retain_compose_diagnostic_probe(seeds=seeds, episodes=400, n_agents=16, K=6,
                                             conditions=("learned",), lr=0.02)
    hi = run_retain_compose_diagnostic_probe(seeds=seeds, episodes=400, n_agents=16, K=6,
                                             conditions=("learned",), lr=0.002)
    # Le nul du record TIENT à son pas (aucune mesure n'est effacée)... et il BASCULE au pas voisin.
    assert lo["learned_median"] <= bar < hi["learned_median"], (lo["learned_median"], hi["learned_median"])
    # Séparation par-seed TOTALE : la bascule n'est pas un effet de médiane.
    assert min(hi["per_seed"]["learned"]) > max(lo["per_seed"]["learned"]), (lo["per_seed"], hi["per_seed"])


# ======================================================================================================
# P2.19 (2026-09-01) — GARDE DE DÉGÉNÉRESCENCE de `s2_verdict`, l'instrument FONDATEUR de G0.
#
# `s2_verdict` porte EDR-112 (« le monde EXIGE l'intelligence ») et tout le fil S2, marqué FOUNDATIONAL.
# Défaut MESURÉ avant correctif : il rendait EXIGE avec EXACTEMENT le même p (0.0025261742685023236) et
# le même Cliff (1.0) sur TROIS régimes incomparables — « 3 vs 2 vs 1 ticks » (tout le monde est mort),
# « 400 vs 399 vs 398 » (tout le monde est censuré) et un vrai signal « 45 vs 15 ».
#
# La cause n'est pas un bug mais une CONSÉQUENCE du design : Cliff et Wilcoxon travaillent sur les RANGS,
# donc l'amplitude n'entre jamais dans le verdict. L'insensibilité à l'échelle — voulue, la survie étant
# censurée et asymétrique — devient une cécité à la dégénérescence.
#
# Non-régression vérifiée AVANT d'armer : EDR-112 publie « 0 % censure partout » et Cliff +0.92 (donc du
# chevauchement, donc de l'étendue) — la garde ne peut pas y toucher.
# ======================================================================================================

def _s2_cond(surv, life, era_s, era_l):
    """Un dict `run_condition` : individus poolés + médianes par ère (par seed)."""
    return {"survival": surv, "life_score": life, "era_survival": era_s, "era_life": era_l}


def test_s2_verdict_REFUSES_a_floor_pinned_regime():
    """⚠️ Le cas certain, côté PLANCHER : tout le monde meurt en 1-3 ticks. Avant la garde : EXIGE."""
    from src.seed_ai.s2_stats import s2_verdict
    r = s2_verdict(_s2_cond([3] * 40, [3.0] * 40, [3] * 12, [3.0] * 12),
                   {"reflexe": _s2_cond([2] * 40, [2.0] * 40, [2] * 12, [2.0] * 12),
                    "aleatoire": _s2_cond([1] * 40, [1.0] * 40, [1] * 12, [1.0] * 12)})
    assert r["verdict"] == "INCONCLUSIVE_DEGENERATE", (
        f"un régime où tout le monde meurt à 1-3 ticks ne peut pas rendre {r['verdict']}")


def test_s2_verdict_REFUSES_a_ceiling_censored_regime():
    """Le cas certain, côté PLAFOND : tous les bras collés à max_ticks. La différence est un artefact
    de troncature, pas un effet."""
    from src.seed_ai.s2_stats import s2_verdict
    r = s2_verdict(_s2_cond([400] * 40, [400.0] * 40, [400] * 12, [400.0] * 12),
                   {"reflexe": _s2_cond([399] * 40, [399.0] * 40, [399] * 12, [399.0] * 12),
                    "aleatoire": _s2_cond([398] * 40, [398.0] * 40, [398] * 12, [398.0] * 12)})
    assert r["verdict"] == "INCONCLUSIVE_DEGENERATE"


def test_s2_verdict_REFUSES_a_declared_floor_even_with_real_spread():
    """Le cas NON certain : de l'étendue existe (4-11 ticks), donc aucun détecteur automatique ne peut
    conclure — c'est l'appelant qui DÉCLARE le plancher. Régime exact de WARM-002 : médiane 7.5 sous le
    plancher 9.0 établi par WARM-010, d'où était sortie la conclusion réfutée « le paysage est PLAT »."""
    from src.seed_ai.s2_stats import s2_verdict
    champ = _s2_cond(list(range(4, 12)), [7.0] * 8, [7] * 12, [7.0] * 12)
    bases = {"reflexe": _s2_cond(list(range(2, 10)), [5.0] * 8, [5] * 12, [5.0] * 12)}
    assert s2_verdict(champ, bases)["verdict"] != "INCONCLUSIVE_DEGENERATE", (
        "sans plancher déclaré, la garde ne DOIT PAS deviner — un plancher n'est pas déductible "
        "de deux tableaux")
    r = s2_verdict(champ, bases, floor=9.0)
    assert r["verdict"] == "INCONCLUSIVE_DEGENERATE" and "PLANCHER" in r["why"]


def test_s2_verdict_SPARES_a_real_signal():
    """⚠️ SPÉCIFICITÉ — sans ce cas, une garde qui refuse TOUT passerait les trois précédents tout en
    détruisant le verdict fondateur. Signal réel (45 vs 15, étendue des deux côtés) -> EXIGE."""
    from src.seed_ai.s2_stats import s2_verdict
    r = s2_verdict(_s2_cond(list(range(30, 70)), [50.0] * 40, [45] * 12, [50.0] * 12),
                   {"reflexe": _s2_cond(list(range(5, 45)), [20.0] * 40, [15] * 12, [20.0] * 12),
                    "aleatoire": _s2_cond(list(range(1, 41)), [10.0] * 40, [8] * 12, [10.0] * 12)})
    assert r["verdict"] == "EXIGE", f"le vrai signal doit survivre à la garde, or : {r['verdict']}"


def test_s2_verdict_SPARES_the_EDR112_regime():
    """Non-régression sur le record FONDATEUR. EDR-112 publie 0 % de censure et Cliff +0.92 avec un
    ratio ~4× ; reconstruit ici à cette échelle, il doit rester EXIGE même avec plancher ET plafond
    déclarés (max_ticks=400, plancher de famine 9.0)."""
    from src.seed_ai.s2_stats import s2_verdict
    champ = _s2_cond(list(range(60, 140)), [100.0] * 80, [95] * 12, [100.0] * 12)
    bases = {"reflexe": _s2_cond(list(range(10, 50)), [30.0] * 40, [24] * 12, [30.0] * 12)}
    r = s2_verdict(champ, bases, floor=9.0, ceiling=400.0)
    assert r["verdict"] == "EXIGE", (
        f"le régime publié d'EDR-112 doit passer la garde, or : {r['verdict']} ({r.get('why')})")


# ======================================================================================================
# P2.20 (2026-09-01) — E14 : la garde de PUISSANCE `sign_p` était CALCULÉE puis JETÉE dans trois verdicts.
#
# `compute_ab_verdict` avait reçu la garde ; ses trois homologues ne l'ont jamais reçue. C'est la
# définition littérale de la classe E14 (« garde jamais rétro-appliquée »).
#
# CONSÉQUENCE VIVANTE au moment du correctif — le cas le plus net qu'on puisse trouver : sur DEUX LIGNES
# ADJACENTES de `docs/roadmap/NAS.md`, le même critère est appliqué à la main de façon inconstante.
#   ligne 167 : D1, +13 %, « NON significatif (sign_p 0.727) » -> RÉFUTÉ
#   ligne 166 : D2, +47 %, « sign_p=0.070 »                    -> ✅ EFFICACE
# Or 0.070 > 0.05. Par le critère que le document applique lui-même juste en dessous, D2 n'est pas
# significatif non plus. L'instrument calculait sign_p, le renvoyait, et laissait le lecteur décider.
#
# Second défaut, trouvé dans la même passe : `fidelity_verdict` n'exigeait NI majorité NI sign_p pour
# `G_INUTILE`, alors que sa jumelle `G_FIDELE` exigeait la majorité -> un NÉGATIF était structurellement
# plus facile à obtenir qu'un POSITIF. L'instrument penchait vers « g est inutile ».
# ======================================================================================================

_D2_PUBLIE = [1.47, 1.50, 1.45, 1.60, 1.40, 1.55, 1.42, 0.85]   # 8 seeds, 7 favorables -> sign_p = 0.0703


def test_sweep_verdict_REFUSES_the_published_D2_configuration():
    """⚠️ CONTRE-EXEMPLE GELÉ de la conséquence réelle. La configuration publiée de D2 (+47 %, 8 seeds,
    sign_p = 0.070) doit rendre NEUTRE, pas EFFICACE : 7 favorables sur 8 ne passent pas le test des
    signes. Si ce test tombe, la garde de puissance a été redésarmée."""
    from tools.metabolic_cost_sweep import compute_sweep_verdict
    # ⚠️ Les clés sont `eff_ratios`/`surv_ratios`. Avec de mauvaises clés, n=0 -> NEUTRE : CE test
    # serait passé pour une raison entièrement fausse. C'est arrivé en l'écrivant, et seul le test de
    # spécificité ci-dessous l'a révélé. D'où l'assertion sur `sign_p` : elle prouve que les données
    # sont bien ARRIVÉES jusqu'au calcul.
    r = compute_sweep_verdict([{"coef": 0.0, "eff_ratios": _D2_PUBLIE, "surv_ratios": [1.0] * 8}])
    cell = r["per_coef"][0]
    assert cell["n"] == 8, f"les données n'ont pas atteint le calcul : n={cell['n']}"
    assert abs(cell["sign_p"] - 0.0703) < 1e-3, f"sign_p attendu ~0.0703, obtenu {cell['sign_p']}"
    assert cell["verdict"] == "NEUTRE", (
        f"+47 % sur 7/8 seeds (sign_p=0.070) ne peut pas être EFFICACE, or : {cell['verdict']}")


def test_sweep_verdict_SPARES_a_powered_effect():
    """⚠️ SPÉCIFICITÉ — sans ce cas, une garde qui refuse TOUT passerait le test précédent tout en
    rendant l'instrument incapable de jamais conclure. 12 seeds unanimes -> EFFICACE."""
    from tools.metabolic_cost_sweep import compute_sweep_verdict
    r = compute_sweep_verdict([{"coef": 0.0, "eff_ratios": [1.5] * 12, "surv_ratios": [1.0] * 12}])
    assert r["per_coef"][0]["verdict"] == "EFFICACE"


def test_transfer_verdict_requires_power_in_BOTH_directions():
    """La garde doit valoir pour TRANSFERE comme pour NUIT : une garde asymétrique fabrique des négatifs.
    7/8 dans un sens comme dans l'autre -> NEUTRE ; 12 unanimes -> le verdict correspondant."""
    from tools.curriculum_transfer import compute_transfer_verdict
    assert compute_transfer_verdict(_D2_PUBLIE)["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([1.0 / r for r in _D2_PUBLIE])["verdict"] == "NEUTRE"
    assert compute_transfer_verdict([1.8] * 12)["verdict"] == "TRANSFERE"
    assert compute_transfer_verdict([0.55] * 12)["verdict"] == "NUIT"


def test_fidelity_verdict_is_SYMMETRIC_between_its_two_labels():
    """⚠️ Le second défaut : `G_INUTILE` n'exigeait ni majorité ni sign_p, `G_FIDELE` exigeait la
    majorité. Un négatif était plus facile à obtenir qu'un positif -> l'instrument penchait. Les deux
    labels doivent maintenant demander la même chose."""
    from tools.g_fidelity_probe import fidelity_verdict
    assert fidelity_verdict([0.5] * 12)["verdict"] == "G_FIDELE"
    assert fidelity_verdict([2.0] * 12)["verdict"] == "G_INUTILE"
    # sous-puissance : 7/8 des deux côtés -> NEUTRE des deux côtés
    faible_inutile = [1.47, 1.50, 1.45, 1.60, 1.40, 1.55, 1.42, 0.85]
    assert fidelity_verdict(faible_inutile)["verdict"] == "NEUTRE"
    assert fidelity_verdict([1.0 / r for r in faible_inutile])["verdict"] == "NEUTRE"


# --- DELAYED-COORD : sonde de Lewis DIFFÉRÉE (instrument né le 2026-09-01, calibré dans la même passe) ---
# Les deux cas ci-dessous n'utilisent QUE des réponses connues analytiquement (plafond de Bayes du canal,
# indépendance d'un readout non entraîné, symétrie exacte des bras). Aucun ne suppose que la tâche est
# apprenable — ils resteraient valides si la capacité était absente, ce qui est exactement ce qu'on veut
# d'une calibration : elle interroge l'INSTRUMENT, pas le phénomène.

def test_delayed_coordination_probe_is_at_CHANCE_when_the_channel_is_MUTE():
    """Réponse CONNUE : à `flip_p=1.0`, `_noisy_onehot` ignore son référent et rend un tirage UNIFORME —
    le sender ne perçoit RIEN de la cible, donc le canal ne porte aucune information et le plafond de
    Bayes vaut EXACTEMENT `1/K`. Une accuracy au-dessus de la chance signalerait une FUITE de la cible
    vers le readout du receiver (la classe d'erreur de MEM-PERCEPTION itération 1, où l'encodage du
    contrôle portait la réponse elle-même). Couvre le pipeline COMPLET, entraînement inclus.

    Second volet — no-op EXACT (spécificité la plus forte) : la DATE de présentation de la cible est le
    SEUL facteur qui sépare RETAIN de PRESENT. Neutralisée (les deux référents sont le même tirage
    uniforme), les deux bras doivent être BIT-IDENTIQUES. Cette assertion casse dès qu'une édition rompt
    l'identité de construction exigée par le design — longueur de séquence, nombre de forwards, ou un
    simple tirage RNG supplémentaire dans un bras."""
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe as run
    K = 6
    r = run(seeds=[0, 1, 2], D=1, episodes=60, n_agents=8, K=K, V=8, lr=0.05, flip_p=1.0, eval_batches=25)
    assert r["_params"]["ceiling_bayes"] == pytest.approx(1.0 / K), r["_params"]
    vals = [v for arm in ("RETAIN", "PRESENT") for v in r[arm + "_intact"] + r[arm + "_ablated"]]
    assert all(abs(v - 1.0 / K) <= 0.09 for v in vals), r      # aucune fuite cible -> readout
    assert r["RETAIN_intact"] == r["PRESENT_intact"], r        # no-op EXACT : bras bit-identiques
    assert r["RETAIN_ablated"] == r["PRESENT_ablated"], r


def test_delayed_coordination_probe_UNTRAINED_cannot_beat_chance():
    """Réponse CONNUE : sans entraînement (`episodes=0`) la réponse du receiver est indépendante d'une
    cible tirée uniformément, donc son accuracy vaut `1/K` en espérance QUELLE QUE SOIT sa politique.
    Ce cas PINGLE LE PLANCHER de l'instrument — pas davantage, et il faut le dire : un readout non
    entraîné est à la chance quelle que soit son entrée, donc ce test n'attrape PAS une fuite de la
    cible (c'est le cas `mute-channel` qui le fait). Ce qu'il attrape, c'est un chemin de SCORE cassé
    (accuracy comparée au leurre plutôt qu'à la cible, éval dégénérée). Il vaut parce qu'un verdict
    « effondrement vers ~0.17 » n'est interprétable que si le plancher a été MESURÉ (classe E14)."""
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe as run
    K = 6
    r = run(seeds=[0, 1, 2], D=1, episodes=0, n_agents=8, K=K, V=8, flip_p=0.3, eval_batches=25)
    vals = [v for arm in ("RETAIN", "PRESENT") for v in r[arm + "_intact"] + r[arm + "_ablated"]]
    assert all(abs(v - 1.0 / K) <= 0.09 for v in vals), r


# ======================================================================================================
# P2.21 (2026-09-01) — `_decomp_verdict` : ZÉRO test, et un CONTRÔLE NÉGATIF entraîné puis jamais lu.
#
# La décomposition factorielle 2×2 (crédit × curriculum) entraîne QUATRE cellules. L'arbre de décision
# n'en lisait que TROIS : `(substep, False)` = L0 — ni crédit tick-return, ni curriculum — était
# entraînée au prix fort, affichée dans le rapport, et **jamais consultée**.
#
# Or L0 est le contrôle négatif de toute la décomposition. Si L0 compose déjà, AUCUN levier n'est
# nécessaire, et rendre `BOTH-NECESSARY` (« les deux sont requis ») est faux. Le verdict le plus fort
# du dispositif ne pouvait donc pas être réfuté par le cas qui le réfute le plus simplement — classe E1.
#
# Instrument PUR (un dict de booléens en entrée) : calibrable sans aucune simulation de monde.
# ======================================================================================================

def _decomp_cells(l0, substep_curr, tick_seul, l2):
    """Les 4 cellules du 2×2, réduites à ce que l'arbre lit : `composes`."""
    return {("substep", False): {"composes": l0},
            ("substep", True): {"composes": substep_curr},
            ("tick", False): {"composes": tick_seul},
            ("tick", True): {"composes": l2}}


def test_decomp_verdict_REFUSES_to_conclude_when_the_bare_rung_already_composes():
    """⚠️ LE contre-exemple. Si L0 compose, il n'y a aucun contraste à décomposer — conclure
    « les deux leviers sont nécessaires » serait faux. AVANT le correctif, ce cas rendait un verdict
    de levier tout à fait ordinaire."""
    from tools.craft_or_starve_edr import _decomp_verdict
    v = _decomp_verdict(_decomp_cells(l0=True, substep_curr=True, tick_seul=True, l2=True))
    assert v == "DEGENERE-SANS-LEVIER", (
        f"le barreau NU compose : aucun levier n'est nécessaire, or le verdict rendu est {v}")


def test_decomp_verdict_still_reports_BOTH_NECESSARY_on_the_real_positive():
    """⚠️ SPÉCIFICITÉ — sans ce cas, une garde qui refuse TOUT passerait le test précédent tout en
    détruisant le verdict que le dispositif existe pour produire. Seul L2 compose -> les deux requis."""
    from tools.craft_or_starve_edr import _decomp_verdict
    v = _decomp_verdict(_decomp_cells(l0=False, substep_curr=False, tick_seul=False, l2=True))
    assert v == "BOTH-NECESSARY", f"le positif réel doit survivre à la garde, or : {v}"


def test_decomp_verdict_separates_the_two_single_levers():
    """Les deux branches intermédiaires doivent rester DISCRIMINANTES : un instrument qui rendrait le
    même verdict pour « curriculum seul » et « crédit seul » n'isolerait plus le levier décisif —
    c'est pourtant sa seule raison d'être."""
    from tools.craft_or_starve_edr import _decomp_verdict
    curr = _decomp_verdict(_decomp_cells(l0=False, substep_curr=True, tick_seul=False, l2=True))
    cred = _decomp_verdict(_decomp_cells(l0=False, substep_curr=False, tick_seul=True, l2=True))
    assert curr == "CURRICULUM-SUFFISANT" and cred == "CREDIT-SUFFISANT" and curr != cred


def test_decomp_verdict_flags_INCOHERENT_when_the_known_composing_cell_fails():
    """Le gate d'origine : si L2 — la cellule CONNUE composante — ne compose pas, la mesure contredit
    le verdict déjà gravé et c'est un artefact, pas un résultat."""
    from tools.craft_or_starve_edr import _decomp_verdict
    v = _decomp_verdict(_decomp_cells(l0=False, substep_curr=False, tick_seul=False, l2=False))
    assert v == "INCOHERENT"


# ======================================================================================================
# P2.22 (2026-09-01) — `regime_diagnostic_verdict` et sa garde donneuse `_survivable`.
#
# Cet instrument tranche la question « ce nul est-il réel, ou fabriqué par un plancher ? » — c'est-à-dire
# exactement la classe E3. Et c'est LUI qui a fourni la notion de survivabilité (`SURV_FLOOR_FRAC`,
# `CENSORED_SURV`) réutilisée le même jour pour armer la garde de dégénérescence de `s2_verdict`
# (P2.19). Un instrument qui sert d'étalon à un autre doit être calibré en premier.
#
# Instrument PUR (dicts de `run_condition`) : aucune simulation de monde.
# ======================================================================================================

def _rd_cond(mediane, n=12, censures=0.0):
    return {"survival": [mediane] * 40, "era_survival": [mediane] * n, "censored_frac": censures}


def _rd_cells(defaut_champ, defaut_base, sweet_champ, sweet_base):
    return {"defaut": {"champion": _rd_cond(defaut_champ), "reflexe": _rd_cond(defaut_base)},
            "sweet": {"champion": _rd_cond(sweet_champ), "reflexe": _rd_cond(sweet_base)}}


def test_regime_diagnostic_names_the_FLOOR_CONFOUND_it_exists_to_find():
    """⚠️ LE verdict que l'outil existe pour produire : au régime par défaut tout le monde est au
    plancher (5 ticks) et le champion ne se distingue pas ; au régime « sweet » il décolle (300) ET
    bat sa baseline. Le nul du défaut était donc un ARTEFACT DE PLANCHER, pas une absence d'effet."""
    from tools.s2_regime_diagnostic import regime_diagnostic_verdict
    r = regime_diagnostic_verdict(_rd_cells(5, 5, 300, 10), max_ticks=400)
    assert r["verdict"] == "CONFOND_PLANCHER" and r["regime_recommande"] == "sweet"
    assert r["lift"] and r["lift"] >= 1.5


def test_regime_diagnostic_calls_UNDERPOWER_when_the_default_regime_already_shows_it():
    """Si le champion bat DÉJÀ au régime par défaut, un nul rapporté ailleurs vient d'un manque de
    puissance, pas d'un plancher. Cette branche passe AVANT toutes les autres : la confondre avec
    CONFOND_PLANCHER ferait recommander un changement de régime inutile."""
    from tools.s2_regime_diagnostic import regime_diagnostic_verdict
    r = regime_diagnostic_verdict(_rd_cells(250, 10, 300, 10), max_ticks=400)
    assert r["verdict"] == "SOUS_PUISSANCE" and r["regime_recommande"] == "defaut"


def test_regime_diagnostic_accepts_a_REAL_null_and_does_not_explain_it_away():
    """⚠️ SPÉCIFICITÉ, et c'est la plus importante ici : un instrument conçu pour trouver des artefacts
    de plancher doit savoir dire « ce nul est RÉEL ». Le régime sweet est survivable (300) et le
    champion n'y bat toujours pas -> il n'y a rien à sauver."""
    from tools.s2_regime_diagnostic import regime_diagnostic_verdict
    r = regime_diagnostic_verdict(_rd_cells(5, 5, 300, 300), max_ticks=400)
    assert r["verdict"] == "N_EXIGE_PAS_REEL" and r["regime_recommande"] is None


def test_regime_diagnostic_says_AMBIGU_rather_than_guessing():
    """Aucun régime survivable : l'instrument doit refuser de trancher plutôt qu'inventer un levier."""
    from tools.s2_regime_diagnostic import regime_diagnostic_verdict
    assert regime_diagnostic_verdict(_rd_cells(5, 5, 5, 5), max_ticks=400)["verdict"] == "AMBIGU"


def test_the_survivability_guard_DONATED_to_s2_verdict_discriminates():
    """La garde donneuse elle-même, dans ses TROIS régimes. Elle est réutilisée par la garde de
    dégénérescence de `s2_verdict` : si elle se dérègle, deux instruments se dérèglent ensemble."""
    from tools.s2_regime_diagnostic import _survivable
    assert _survivable(_rd_cond(300), 400) is True, "médiane >= 50 % de max_ticks = survivable"
    assert _survivable(_rd_cond(5), 400) is False, "médiane 5/400 ne peut pas être survivable"
    assert _survivable(_rd_cond(5, censures=0.30), 400) is True, (
        "30 % de censurés = des agents ATTEIGNENT max_ticks : survivable malgré une médiane basse")


# ======================================================================================================
# P2.23 (2026-09-01) — la famille `disjoint_heads` : 8 verdicts à vote majoritaire, calibrés EN LOT.
#
# DÉFAUT MESURÉ, commun aux huit : une liste VIDE produisait un verdict DE FOND.
#     `_verdict_disjoint([])` -> "DISJOINT_NEUTRAL"  = « les têtes disjointes ne changent rien »,
#     affirmé à partir d'AUCUNE donnée. C'est la classe E18 (un estimateur qui récompense l'absence
#     de preuve) doublée de E4 (une vérification vide indiscernable d'un succès).
# Les SEUILS sont marqués GELE dans chaque docstring et ne sont PAS touchés : la correction ajoute
# uniquement la branche n=0, qu'aucun run réel ne visite.
#
# Les cas sont écrits sur des propriétés STRUCTURELLES et non sur les chaînes exactes : un futur membre
# de la famille est ainsi couvert sans réécrire quoi que ce soit, et le test ne se périme pas si un
# libellé change.
# ======================================================================================================

_FAMILLE_DISJOINT = [
    ("tools.disjoint_heads_ab", "_verdict_disjoint", 1),
    ("tools.disjoint_heads_capacity", "_verdict_capacity", 2),
    ("tools.disjoint_heads_confound", "_verdict_confound", 1),
    ("tools.disjoint_heads_correlated", "_verdict_correlated", 2),
    ("tools.disjoint_heads_lr", "_verdict_lr", 1),
    ("tools.disjoint_heads_synergy", "_verdict_v4", 1),
    ("tools.disjoint_heads_v3", "_verdict_v3", 1),
    ("tools.disjoint_heads_v4", "_verdict_v4", 1),
]


def _appelle(mod, fn, arite, valeurs):
    import importlib
    f = getattr(importlib.import_module(mod), fn)
    return f(*([list(valeurs)] * arite))


@pytest.mark.parametrize("mod,fn,arite", _FAMILLE_DISJOINT)
def test_disjoint_family_REFUSES_to_judge_without_any_seed(mod, fn, arite):
    """⚠️ LE contre-exemple. Zéro seed doit donner zéro verdict — pas un verdict de fond."""
    assert _appelle(mod, fn, arite, []) == "INDETERMINE_AUCUN_SEED", (
        f"{mod}.{fn} rend encore un verdict sur une entrée VIDE")


@pytest.mark.parametrize("mod,fn,arite", _FAMILLE_DISJOINT)
def test_disjoint_family_DISCRIMINATES_its_two_extremes(mod, fn, arite):
    """⚠️ SPÉCIFICITÉ — sans ce cas, un instrument qui rendrait TOUJOURS « indéterminé » passerait le
    test précédent tout en étant inutilisable. Les deux extrêmes unanimes doivent différer, et aucun
    ne doit être le refus."""
    haut = _appelle(mod, fn, arite, [1.0] * 5)
    bas = _appelle(mod, fn, arite, [-1.0] * 5)
    assert haut != bas, f"{mod}.{fn} ne distingue pas ses deux extrêmes ({haut})"
    assert "INDETERMINE" not in haut and "INDETERMINE" not in bas, (
        f"{mod}.{fn} refuse de juger des données unanimes")


@pytest.mark.parametrize("mod,fn,arite", _FAMILLE_DISJOINT)
def test_disjoint_family_has_a_real_MIDDLE_zone(mod, fn, arite):
    """Une majorité stricte (`n//2 + 1`) doit exister : sur 4 seeds partagés 2/2, aucun camp ne
    l'atteint. Si le verdict partagé était identique à un extrême, le seuil de majorité ne servirait
    à rien et un demi-échantillon suffirait à conclure."""
    partage = _appelle(mod, fn, arite, [1.0, 1.0, -1.0, -1.0])
    haut = _appelle(mod, fn, arite, [1.0] * 5)
    bas = _appelle(mod, fn, arite, [-1.0] * 5)
    assert partage != haut and partage != bas, (
        f"{mod}.{fn} : un partage 2/2 rend le même verdict qu'un consensus ({partage})")


def test_the_frozen_thresholds_of_verdict_lr_are_INCLUSIVE():
    """Les seuils publiés sont `>= 0.90` et `<= 0.79`. Un off-by-one les rendrait exclusifs et
    déplacerait silencieusement le verdict qui porte le « 194 LR_CLOSES ». Frontières gelées."""
    from tools.disjoint_heads_lr import _verdict_lr
    assert _verdict_lr([0.90] * 5) == "LR_CLOSES", "0.90 doit être DANS le camp LR_CLOSES"
    assert _verdict_lr([0.79] * 5) == "LR_INTERCHANGEABLE", "0.79 doit être DANS le camp opposé"
    assert _verdict_lr([0.85] * 5) == "PARTIAL", "le TROU 0.80-0.89 ne conclut ni dans un sens ni l'autre"


# ======================================================================================================
# P2.24 (2026-09-01) — les 4 verdicts « à gate » de `lewis_survival_sweep`, et un biais SYSTÉMATIQUE.
#
# DEUX défauts mesurés, et tous deux penchaient dans la MÊME direction — la conclusion NÉGATIVE :
#   (1) entrée VIDE -> "PAS DE RUNG", "MUR INTRINSEQUE", "PAS LE METABOLISME SEUL", "PAS LE BRAIN_COST".
#       Quatre affirmations de fond tirées d'AUCUNE donnée (classes E18 + E4).
#   (2) `zip(levels, medians)` TRONQUE SILENCIEUSEMENT. Avec une médiane manquante, un
#       **"BARREAU TROUVE" devenait "PAS DE RUNG"** : un verdict INVERSÉ, pas une erreur.
#
# ⚠️ C'est l'asymétrie qui rend ces défauts dangereux ici. Des données absentes ou incomplètes ne
# produisaient pas « inconnu » mais « le mur est intrinsèque ». Dans un dépôt dont la plupart des
# résultats SONT négatifs, un négatif fabriqué ressemble à tous les autres.
# ======================================================================================================

_SWEEP_GATE = [
    ("_verdict", 2, "PAS DE RUNG"),
    ("_verdict_apex", 2, "MUR INTRINSEQUE"),
    ("_verdict_metab", 2, "PAS LE METABOLISME SEUL"),
    ("_verdict_surprise", 3, "PAS LE BRAIN_COST"),
]


def _sweep_call(nom, arite, niveaux, medianes):
    import tools.lewis_survival_sweep as L
    f = getattr(L, nom)
    return f(niveaux, medianes, *([[0.0] * len(medianes)] if arite == 3 else []))


@pytest.mark.parametrize("nom,arite,negatif", _SWEEP_GATE)
def test_sweep_verdicts_REFUSE_to_conclude_without_any_level(nom, arite, negatif):
    """⚠️ LE contre-exemple : zéro niveau ne peut pas prouver « il n'y a pas de barreau »."""
    v = _sweep_call(nom, arite, [], [])
    assert v == "INDETERMINE_AUCUN_NIVEAU", (
        f"{nom} rend « {v} » sans aucune donnée — une affirmation de fond tirée du vide")
    assert v != negatif


@pytest.mark.parametrize("nom,arite,negatif", _SWEEP_GATE)
def test_sweep_verdicts_REFUSE_truncated_input_instead_of_INVERTING(nom, arite, negatif):
    """⚠️ Le défaut le plus dangereux : `zip` tronquait sans un mot, et le niveau qui franchissait
    disparaissait. Le verdict ne devenait pas faux « au hasard » — il basculait vers le NÉGATIF."""
    v = _sweep_call(nom, arite, [0, 1, 2, 3], [0.0, 0.0, 0.0])
    assert v == "INDETERMINE_DONNEES_INCOMPLETES", (
        f"{nom} conclut « {v} » sur des données incomplètes au lieu de le signaler")


@pytest.mark.parametrize("nom,arite,negatif", _SWEEP_GATE)
def test_sweep_verdicts_still_deliver_their_LEGITIMATE_negative(nom, arite, negatif):
    """⚠️ SPÉCIFICITÉ, et elle est essentielle ici : le négatif est un résultat SCIENTIFIQUE valide
    quand il repose sur des données complètes. Une garde qui l'empêcherait détruirait l'instrument."""
    v = _sweep_call(nom, arite, [0, 1, 2, 3], [0.0, 0.0, 0.0, 0.0])
    assert v == negatif, f"{nom} ne sait plus rendre son négatif légitime : {v}"


def test_sweep_verdict_still_finds_a_rung_when_a_level_crosses():
    """L'autre bord de la spécificité : un franchissement réel doit toujours donner un POSITIF."""
    from tools.lewis_survival_sweep import GATE
    assert _sweep_call("_verdict", 2, [0, 1, 2, 3], [0.0, 0.0, 0.0, GATE + 1.0]) == "BARREAU TROUVE"


# ======================================================================================================
# P2.25 (2026-09-01) — les DEUX verdicts S2 restants. Un chemin non gardé, et le marqueur transversal.
#
# `verdict_within_subject` portait EXACTEMENT la même cécité que `s2_verdict` (P2.19) : « tout le monde
# à 2-3 ticks » rendait CAUSAL-PARTIEL, comme un vrai signal. Or c'est le MARQUEUR DE DEMANDE transversal
# du dépôt — validé sur perception, communication, généralisation et mémoire. Une cécité au plancher s'y
# propage donc à quatre modalités d'un coup.
#
# `verdict_from_survival_cmps` NE PEUT PAS se garder lui-même : il reçoit des comparaisons déjà calculées
# ({p, cliff}) et non les distributions. C'était le CHEMIN NON GARDÉ vers le verdict tant que `s2_verdict`
# était seul protégé. L'appelant, qui a les distributions, lui passe le résultat de `s2_degeneracy`.
# ======================================================================================================

def _ws_plat(mediane, n=12):
    return {"survival": [mediane] * 40, "life_score": [float(mediane)] * 40,
            "era_survival": [mediane] * n, "era_life": [float(mediane)] * n}


def _ws_etale(a, b):
    return {"survival": list(range(a, b)), "life_score": [float(a)] * (b - a),
            "era_survival": [(a + b) // 2] * 12, "era_life": [float(a)] * 12}


def test_within_subject_marker_REFUSES_a_floor_pinned_regime():
    """⚠️ Le marqueur transversal ne doit pas confondre « ablater effondre » avec « tout est déjà au
    sol ». Avant la garde : CAUSAL-PARTIEL, le même verdict qu'un vrai signal."""
    from src.seed_ai.s2_stats import verdict_within_subject
    r = verdict_within_subject(_ws_plat(3), _ws_plat(2), _ws_plat(1))
    assert r["verdict"] == "INCONCLUSIVE_DEGENERATE"


def test_within_subject_marker_SPARES_a_real_causal_signal():
    """⚠️ SPÉCIFICITÉ — le marqueur doit continuer à trancher quand les distributions sont réelles."""
    from src.seed_ai.s2_stats import verdict_within_subject
    r = verdict_within_subject(_ws_etale(40, 90), _ws_etale(5, 45), _ws_etale(1, 20))
    assert r["verdict"] != "INCONCLUSIVE_DEGENERATE" and "verdict" in r


def test_from_survival_cmps_HONOURS_a_degeneracy_declared_by_its_caller():
    """Le chemin non gardé : cette fonction n'a pas les distributions, donc l'appelant DÉCLARE."""
    from src.seed_ai.s2_stats import verdict_from_survival_cmps
    cmps = {"reflexe": {"p": 0.001, "cliff": 0.9}}
    assert verdict_from_survival_cmps(cmps, degenerate_why="plancher")["verdict"] == "INCONCLUSIVE_DEGENERATE"
    assert verdict_from_survival_cmps(cmps)["verdict"] == "EXIGE", (
        "sans déclaration, le verdict normal doit être rendu — sinon la garde bloque tout")


def test_from_survival_cmps_FAILS_LOUDLY_on_empty_input():
    """⚠️ Comportement CORRECT à GELER, pas à corriger : sans aucune comparaison, la fonction LÈVE au
    lieu de rendre un verdict. Si quelqu'un « répare » ça un jour en renvoyant VOID ou AMBIGU, il
    fabriquera un verdict à partir de rien — c'est ce test qui l'en empêchera."""
    from src.seed_ai.s2_stats import verdict_from_survival_cmps
    with pytest.raises(ValueError):
        verdict_from_survival_cmps({})


# ======================================================================================================
# P2.26 (2026-09-01) — les 6 verdicts restants de `lewis_survival_sweep`. UN seul etait fautif.
#
# Sondage systematique sur entree vide : `_verdict_landing` et `_verdict_forage` LEVENT (correct),
# `_verdict_approach`, `_verdict_deconfound` et `_verdict_reach` rendent INDETERMINE (correct). Seul
# `_verdict_evolve_nav` concluait — et sa docstring documentait explicitement ce choix : « traj vide ->
# SUBSTRAT BLOQUE », soit « le substrat bloque la navigation » affirme sur ZERO generation.
#
# C'est instructif justement parce que 5 sur 6 etaient bons : le defaut n'etait pas une negligence de
# module, c'etait une DECISION, prise dans la seule direction ou un verdict fabrique passe inapercu.
#
# ⚠️ `_verdict_approach` et `_verdict_reach` font mieux qu'un test de vide : ils verifient que LA
# CELLULE dont ils dependent existe (speed=0.0 / oracle=True). C'est le motif que les autres n'avaient
# pas, et il est gele ici pour servir de reference.
# ======================================================================================================

def test_evolve_nav_REFUSES_to_blame_the_substrate_on_zero_generation():
    """⚠️ LE contre-exemple : aucune generation ne peut prouver que le substrat bloque."""
    from tools.lewis_survival_sweep import _verdict_evolve_nav
    assert _verdict_evolve_nav([]) == "INDETERMINE_AUCUNE_GENERATION"


def test_evolve_nav_still_separates_progress_from_stagnation():
    """⚠️ SPECIFICITE dans les DEUX sens : la garde ne doit ni empecher le positif, ni empecher le
    negatif LEGITIME (une trajectoire plate SUR DES DONNEES REELLES est bien un substrat bloque)."""
    from tools.lewis_survival_sweep import _verdict_evolve_nav
    assert _verdict_evolve_nav([0.1] * 5 + [0.5] * 5) == "NAVIGATION EVOLUE"
    assert _verdict_evolve_nav([0.2] * 10) == "SUBSTRAT BLOQUE"


def test_landing_and_forage_FAIL_LOUDLY_rather_than_conclude():
    """Comportement CORRECT a GELER, pas a corriger. Si quelqu'un les « repare » en attrapant
    l'exception pour renvoyer un verdict par defaut, il fabriquera une conclusion a partir de rien."""
    from tools.lewis_survival_sweep import _verdict_landing, _verdict_forage
    with pytest.raises((IndexError, KeyError, ValueError)):
        _verdict_landing({})
    with pytest.raises((IndexError, KeyError, ValueError)):
        _verdict_forage({})


def test_approach_and_reach_require_THE_CELL_they_depend_on_not_merely_data():
    """⚠️ Le motif de reference. Ces deux verdicts sont portes par UNE cellule precise (vitesse figee /
    oracle). Des donnees ABONDANTES mais sans cette cellule doivent rendre INDETERMINE -- un test de
    « liste non vide » ne l'aurait pas attrape."""
    from tools.lewis_survival_sweep import _verdict_approach, _verdict_reach
    assert _verdict_approach([(1.0, {"p_reach": 0.9}), (2.0, {"p_reach": 0.9})]) == "INDETERMINE"
    assert _verdict_reach([(False, 0.0, {"p_reach": 0.99})]) == "INDETERMINE"


def test_approach_and_reach_discriminate_on_their_frozen_thresholds():
    """SPECIFICITE : avec la bonne cellule, les seuils pre-enregistres doivent trancher les 3 zones."""
    from tools.lewis_survival_sweep import _verdict_approach, _verdict_reach
    assert _verdict_approach([(0.0, {"p_reach": 0.7})]) == "KINEMATIQUE"
    assert _verdict_approach([(0.0, {"p_reach": 0.3})]) == "POLITIQUE"
    assert _verdict_reach([(True, 0.0, {"p_reach": 0.95})]) == "PRIMITIVE FERME"
    assert _verdict_reach([(True, 0.0, {"p_reach": 0.30})]) == "PRIMITIVE NE FERME PAS"
    assert _verdict_reach([(True, 0.0, {"p_reach": 0.70})]) == "PRIMITIVE PARTIELLE"


def test_deconfound_says_INDETERMINE_when_a_frozen_cell_is_missing():
    """Sa docstring le promet (« INDETERMINE si une des deux cellules figees manque ») : le geler
    empeche qu'une refonte le remplace par un ratio calcule sur une seule cellule."""
    from tools.lewis_survival_sweep import _verdict_deconfound
    assert _verdict_deconfound([]) == "INDETERMINE"


# ======================================================================================================
# P2.27 (2026-09-01) — sondage SYSTEMATIQUE des verdicts de sondes sur entree vide.
#
# 17 verdicts purs sondes. ONZE etaient DEJA corrects : `credit_verdict`, `density_verdict`,
# `_verdict_qd_rescue`, `_verdict_coordination`, `_verdict_craft_wall`, `_verdict_retention` LEVENT ;
# `_verdict_horizon` rend INDETERMINE ; `energy_verdict`, `nav_verdict`, `readout_verdict` rendent
# INVALID_TARGET ; `unresolved_verdicts` rend une liste vide (une liste, pas un verdict).
#
# TROIS etaient fautifs, et tous trois rendaient une affirmation de FOND, NEGATIVE, sur zero donnee :
#   funnel_verdict({})            -> "AUTEL_MORT"      (« l'autel est mort »)
#   distress_verdict([])          -> "NEUTRE"
#   compute_emergence_verdict([],[]) -> "N_EMERGE_PAS" (« le stockage n'emerge pas »)
# Les deux derniers codaient le cas vide EXPLICITEMENT : c'etait une decision, pas un oubli.
#
# ⚠️ DISTINCTION QUI M'A FAIT SUR-SIGNALER, gelee ici pour qu'on ne « corrige » pas ce qui va bien :
# passer 0.0 a une fonction qui attend un scalaire MESURE n'est pas « aucune donnee », c'est UNE MESURE
# VALANT ZERO. `agri_verdict(0, 0)` = « rien n'a ete plante », une observation legitime. La sonde avait
# annonce SIX defauts ; il y en avait TROIS.
# ======================================================================================================

def test_probe_verdicts_REFUSE_to_conclude_on_zero_data():
    """⚠️ Les trois contre-exemples. Aucun agent, aucun seed -> aucune affirmation de fond."""
    from tools.altar_tool_funnel_probe import funnel_verdict
    from tools.dream_distress_probe import distress_verdict
    from tools.famine_storage_probe import compute_emergence_verdict
    assert funnel_verdict({})["verdict_autel"] == "INDETERMINE_AUCUN_AGENT"
    assert distress_verdict([])["verdict"] == "INDETERMINE_AUCUN_SEED"
    assert compute_emergence_verdict([], [])["verdict"] == "INDETERMINE_AUCUN_SEED"


def test_probe_verdicts_still_deliver_their_LEGITIMATE_negative_and_positive():
    """⚠️ SPECIFICITE des deux cotes. « AUTEL_MORT » reste rendu quand un agent REEL n'a rien resolu :
    c'est un resultat, pas un artefact. Et les positifs doivent survivre a la garde."""
    from tools.altar_tool_funnel_probe import funnel_verdict
    from tools.dream_distress_probe import distress_verdict
    from tools.famine_storage_probe import compute_emergence_verdict
    inactif = {"s0": [{"preys_eaten": 0, "spears_crafted": 0, "mammoth_kills": 0, "altars_solved": 0}]}
    assert funnel_verdict(inactif)["verdict_autel"] == "AUTEL_MORT"
    assert distress_verdict([0.5] * 12)["verdict"] == "DETRESSE"
    assert compute_emergence_verdict([20.0] * 12, [0.0] * 12)["verdict"] == "EMERGE"


def test_a_measured_ZERO_is_not_missing_data():
    """⚠️ Le piege qui m'a fait sur-signaler, gele. Ces fonctions prennent des scalaires MESURES : zero
    y est une observation (« rien n'a ete plante », « le delta vaut 0 »), pas une absence. Leur ajouter
    une garde « entree vide » serait une ERREUR — elles doivent conclure sur un zero mesure."""
    from tools.agricultural_demand_probe import agri_verdict
    from tools.tom_probe import _verdict_tom_emergence
    assert agri_verdict(0, 0) == "AGRICULTURE_COSMETIC", (
        "aucune plantation OBSERVEE est un resultat : la fonction doit trancher, pas s'abstenir")
    assert _verdict_tom_emergence(0.5, 0.5, 0.5) == "TOM_INERT", (
        "trois accuracies egales = aucune elevation : c'est une mesure, pas une absence de mesure")


def test_the_eleven_already_correct_verdicts_stay_correct():
    """Ces onze n'avaient pas besoin d'etre corriges — donc rien ne signalait leur bon comportement.
    Le geler empeche qu'une refonte les aligne un jour sur les trois fautifs « par coherence »."""
    from tools.memory_credit_horizon import _verdict_horizon
    from tools.nav_localization_probe import nav_verdict
    from tools.energy_readout_probe import energy_verdict
    from tools.cartography import unresolved_verdicts
    assert _verdict_horizon([], []) == "INDETERMINE"
    assert nav_verdict(0.0, 0.0, 0.0, 0.0) == "INVALID_TARGET"
    assert energy_verdict(0.0, 0.0, 0.0) == "INVALID_TARGET"
    assert unresolved_verdicts([]) == []


# ======================================================================================================
# P2.28 (2026-09-01) — les 8 derniers verdicts PURS. Tous etaient DEJA corrects ; on gele leurs branches.
#
# Aucun defaut ici, et c'est le resultat. Trois sont meme exemplaires, chacun gardant une chose
# DIFFERENTE — et c'est ce trio qui montre ce qu'une garde doit verifier :
#   `_verdict_coordination` verifie la TAILLE D'ECHANTILLON (n >= 20 des deux cotes) ;
#   `_verdict_craft_wall`   verifie le PREMIER ETAGE de l'entonnoir (sans forage, le craft ne veut rien
#                           dire -> INDETERMINE) ;
#   `readout_verdict`       verifie que LA CIBLE EST APPRENABLE (si le plafond supervise ne depasse pas
#                           le hasard, juger le RL n'a aucun sens -> INVALID_TARGET).
# Trois questions distinctes : « ai-je assez de donnees ? », « le prerequis est-il rempli ? », « la
# question est-elle bien posee ? ». Un instrument peut echouer sur l'une en reussissant les autres.
# ======================================================================================================

def test_coordination_verdict_guards_its_SAMPLE_SIZE():
    """n < 20 d'un cote suffit a refuser : un delta calcule sur 3 chasses n'est pas un delta."""
    from tools.tom_coordination import _verdict_coordination
    assert _verdict_coordination({"n_with": 5, "n_alone": 100, "delta": 0.9}) == "INDETERMINE"
    assert _verdict_coordination({"n_with": 50, "n_alone": 50, "delta": 0.5}) == "COORDINATED"
    assert _verdict_coordination({"n_with": 50, "n_alone": 50, "delta": 0.01}) == "INDEPENDENT"


def test_craft_wall_verdict_guards_its_FUNNEL_PREREQUISITE():
    """Sans forage (< 0.10), le taux de craft ne mesure rien : l'etage amont est vide."""
    from tools.competence_profile import _verdict_craft_wall
    assert _verdict_craft_wall({"frac_forage": 0.05, "frac_craft": 0.0, "frac_apex": 0.0}) == "INDETERMINE"
    assert _verdict_craft_wall({"frac_forage": 0.80, "frac_craft": 0.02,
                                "frac_apex": 0.30}) == "CRAFT_WALL CONFIRME"
    assert _verdict_craft_wall({"frac_forage": 0.80, "frac_craft": 0.60,
                                "frac_apex": 0.40}) == "ECHELLE MONOTONE"


def test_readout_verdict_guards_that_the_QUESTION_IS_WELL_POSED():
    """⚠️ La garde la plus subtile des trois : si le plafond SUPERVISE ne depasse pas le hasard, la
    cible est mal posee et juger le RL dessus produirait un « CREDIT_GATED » qui n'apprend rien sur le
    credit. L'instrument refuse de repondre a une mauvaise question."""
    from tools.nav_readout_trainability import readout_verdict
    assert readout_verdict(0.52, 0.51, 0.50) == "INVALID_TARGET"
    assert readout_verdict(0.90, 0.85, 0.50) == "RL_RECOVERS"
    assert readout_verdict(0.90, 0.52, 0.50) == "CREDIT_GATED"


def test_the_nav_pair_separates_BIAS_from_RARITY_and_SPARSITY():
    """Deux instruments jumeaux qui attribuent un effondrement a la bonne cause. Les confondre
    inverserait le correctif recommande (retirer un biais contre densifier un signal)."""
    from tools.nav_credit_structure import credit_verdict
    from tools.nav_signal_density import density_verdict
    assert credit_verdict([0.9], [0.1]) == "BIAS_NOT_RARITY"
    assert credit_verdict([0.1], [0.1]) == "RARITY_ALSO_FATAL"
    assert density_verdict([0.9, 0.8], [0.1, 0.2]) == "BIAS_IS_FATAL"


def test_qd_rescue_and_retention_need_an_ABSOLUTE_floor_not_only_a_delta():
    """⚠️ Propriete partagee et facile a perdre : un gain de +0.10 sur un craft quasi nul (0.001 ->
    0.101) ne « sauve » rien. Les deux exigent le delta ET un plancher absolu. Sans le plancher, un
    bruit sur un plancher deviendrait un levier."""
    from tools.qd_tier_rescue import _verdict_qd_rescue
    from tools.craft_retention_probe import _verdict_retention
    assert _verdict_qd_rescue({"frac_craft": 0.00}, {"frac_craft": 0.15}) == "QD_RESCUE_CRAFT CONFIRME"
    assert _verdict_qd_rescue({"frac_craft": 0.15}, {"frac_craft": 0.00}) == "QD_NUIT"
    assert _verdict_qd_rescue({"frac_craft": 0.10}, {"frac_craft": 0.12}) == "QD_NEUTRE"
    assert _verdict_retention({"frac_craft": 0.00}, "cond", {"frac_craft": 0.20}).startswith("RETENTION_LEVER")
    assert _verdict_retention({"frac_craft": 0.10}, "cond", {"frac_craft": 0.11}) == "POLICY_LOCKED"


def test_dreaming_verdict_covers_its_four_cases_on_MEASURED_values():
    """Gate 4-cas (survit x paye). Ses entrees sont des scalaires MESURES : des zeros y sont une
    observation (« aucun ecart »), pas une absence — « MORT » sur des zeros est donc CORRECT, et ce
    test empeche qu'on y ajoute une garde « entree vide » qui serait une erreur."""
    from tools.dreaming_probe import dreaming_verdict
    assert dreaming_verdict(0.0, 0.0, 0.0, 1.0) == "MORT"
    assert dreaming_verdict(0.1, -0.5, 0.1, 1.0) == "SURVIT_ET_PAYE"
    assert dreaming_verdict(0.1, -0.5, 0.0, 1.0) == "SURVIT_PAS_PAYE"
    assert dreaming_verdict(-0.9, 0.5, 0.1, 1.0) == "PAYE_PAS_SURVIT"


def test_a_declared_NON_INSTRUMENT_must_be_QUALIFIED_when_its_name_collides():
    """⚠️ Garde du mecanisme ajoute le meme jour. `verdict` existe dans DEUX fichiers : declarer le nom
    NU exempterait aussi `src/seed_ai/eval_harness.py::verdict`, qui est peut-etre un vrai instrument.
    Le defaut avait ete corrige pour `CALIBRATED` le matin, et REINTRODUIT ici l'apres-midi."""
    import tools.check_instrument_calibration as C
    declares = C.scan_not_instruments()
    collisions = C.scan_collisions()
    for nom in declares:
        nu = nom.split("::")[-1]
        if nu in collisions:
            assert "::" in nom, (
                f"« {nu} » est defini dans {len(collisions[nu])} fichiers : une declaration NUE "
                f"exempterait des homonymes jamais examines")


# ======================================================================================================
# P2.29 (2026-09-01) — `run_sweep` calibré PAR INJECTION, sans simuler une seule ère.
#
# METHODE, reutilisable pour tout ORCHESTRATEUR. `run_sweep` accepte `run_era_fn` : on lui impose une
# DOSE CONNUE a la place de la simulation et on verifie qu'il la RETROUVE. C'est la calibration PAR
# PREDICTION que CLAUDE.md prefere a la valeur absolue — et elle coute zero seconde de monde.
#
# Ce qu'on teste ainsi n'est pas le monde (ce n'est pas le role de cet instrument) mais la couche qui
# transforme des mesures en AFFIRMATION : agregation, appariement, choix du ratio. C'est precisement la
# couche que personne ne testait.
#
# Contrat du faux : run_era_fn(cfg, genomes, max_ticks) -> (scored, m),
#   m = {"score", "ticks", "mean_active"} ; efficiency = competence / mean_active.
# ======================================================================================================

_SWEEP_PARAM = "metabolic_cost_coef"
_SWEEP_ERAS = 3


def _sweep_injecte(effet_comp, seeds, coefs, bruit=None, effet_actif=lambda c: 1.0):
    """Lance `run_sweep` avec une ere FACTICE dont la competence suit une dose imposee."""
    from tools.metabolic_cost_sweep import run_sweep
    ordre, appels = list(seeds), {"n": 0}
    par_seed = len(coefs) * _SWEEP_ERAS

    def faux(cfg, genomes, max_ticks):
        seed = ordre[(appels["n"] // par_seed) % len(ordre)]
        appels["n"] += 1
        coef = float(getattr(cfg, _SWEEP_PARAM, 0.0))
        score = 100.0 * (bruit or {}).get(seed, 1.0) * effet_comp(coef)
        return ([(score, g) for g in genomes[:5]],
                {"score": score, "ticks": 200.0, "mean_active": 50.0 * effet_actif(coef)})

    return run_sweep(seeds, coefs, eras=_SWEEP_ERAS, num_agents=6, max_ticks=10,
                     run_era_fn=faux, param=_SWEEP_PARAM)


def test_sweep_invents_NO_effect_when_the_dose_does_nothing():
    """⚠️ NO-OP EXACT. La dose ne change rien -> ratio 1.0000 et verdict NEUTRE. Un sweep qui
    fabriquerait un effet ici invaliderait tout ce qu'il a jamais rapporte."""
    r = _sweep_injecte(lambda c: 1.0, seeds=list(range(12)), coefs=[0.0, 0.5])
    cell = r["per_coef"][0]
    assert abs(cell["median_eff"] - 1.0) < 1e-9, f"effet invente : {cell['median_eff']}"
    assert cell["verdict"] == "NEUTRE"


def test_sweep_RECOVERS_an_imposed_dose_exactly():
    """⚠️ PREDICTION. On impose +50 % de competence ; le sweep doit rendre 1.5000, pas « un effet »."""
    r = _sweep_injecte(lambda c: 1.0 + c, seeds=list(range(12)), coefs=[0.0, 0.5])
    cell = r["per_coef"][0]
    assert abs(cell["median_eff"] - 1.5) < 1e-9, f"dose non retrouvee : {cell['median_eff']}"
    assert cell["verdict"] == "EFFICACE" and cell["sign_p"] < 0.05


def test_sweep_PAIRING_cancels_between_seed_variance():
    """⚠️ LE test qui manquait. Un sweep APPARIE existe pour que la variance entre seeds s'annule dans
    le ratio. On impose un bruit de 161x entre seeds ET la meme dose de +50 % : si l'appariement est
    reellement fait, la dose ressort EXACTE. Si quelqu'un remplacait un jour l'appariement par une
    comparaison de moyennes, ce bruit noierait l'effet et ce test tomberait."""
    bruit = {s: 1.0 + 40.0 * (s % 5) for s in range(12)}
    r = _sweep_injecte(lambda c: 1.0 + c, seeds=list(range(12)), coefs=[0.0, 0.5], bruit=bruit)
    cell = r["per_coef"][0]
    assert abs(cell["median_eff"] - 1.5) < 1e-9, (
        f"le bruit entre seeds n'est pas annule -> l'appariement est casse : {cell['median_eff']}")
    assert cell["verdict"] == "EFFICACE"


def test_sweep_measures_EFFICIENCY_not_competence():
    """⚠️ SPECIFICITE sur la GRANDEUR MESUREE (la question 2 du pre-vol : est-ce bien la grandeur qui
    agit ?). Competence ET `mean_active` montent de 50 % ensemble -> l'EFFICIENCE ne bouge pas. Un
    compteur de score aurait crie a l'effet ; cet instrument doit rendre NEUTRE."""
    r = _sweep_injecte(lambda c: 1.0 + c, seeds=list(range(12)), coefs=[0.0, 0.5],
                       effet_actif=lambda c: 1.0 + c)
    cell = r["per_coef"][0]
    assert abs(cell["median_eff"] - 1.0) < 1e-9, (
        f"l'instrument suit la competence, pas l'efficience : {cell['median_eff']}")
    assert cell["verdict"] == "NEUTRE"


# ======================================================================================================
# P2.30 (2026-09-01) — `verdict_demand_marker` calibre PAR INJECTION, et un DEFAUT trouve en le faisant.
#
# Il appelle `_mamba_survival_eras` / `_torch_survival_eras` par nom de module : on injecte des survies
# CONNUES et on verifie la traduction en verdict. Aucune simulation.
#
# ⚠️ DEFAUT TROUVE, dans `tools/demand_marker.ablation_verdict` (fichier d'une SESSION PARALLELE, en
# cours de travail -- non modifie ici). La branche `collapse` rend X_DEMANDED SANS consulter `why` :
#     ablation_verdict([7.0]*12, [3.0]*12, floor=9.0)
#       -> verdict = "X_DEMANDED", degenerate = True,
#          why = "bras intact au PLANCHER declare (mediane 7 <= floor 9)"
# La degenerescence est DETECTEE, RAPPORTEE dans le dict, et NON LUE par le verdict -- exactement la
# forme de `sign_p` calcule puis jete (P2.20).
#
# La garde de plancher est ASYMETRIQUE : son commentaire dit qu'elle existe parce qu'« un bras intact au
# sol rendrait NEUTRAL » (le faux NEGATIF de WARM-002). Elle ne protege pas du faux POSITIF : deux bras
# mourant a 7 et 3 ticks, tous deux SOUS le plancher de survivabilite, donnent ratio 2.33 donc
# « la perception est exigee ». L'exemption « un positif censure reste un positif, le ratio est une
# borne INF » est juste pour le PLAFOND ; elle a ete appliquee a TOUTES les raisons, plancher compris.
#
# Les commits de la session parallele montrent qu'elle traite ces branches une par une (`decoy`, puis
# `inverted` -- « round 1 »). Le test ci-dessous est donc `xfail(strict=True)` : il documente le defaut
# de facon EXECUTABLE et ECHOUERA le jour ou il sera corrige, forcant a retirer le marqueur.
# ======================================================================================================

def _wdm_injecte(monkeypatch, intact_med, ablated_med, n=12):
    import tools.warmstart_evolution_inworld as W

    def faux(genome, ablate, seed, K, num_agents, max_ticks, metab, cog):
        return [ablated_med if ablate else intact_med] * n

    monkeypatch.setattr(W, "_mamba_survival_eras", faux)
    return W.verdict_demand_marker(None, "mamba")


def test_demand_marker_reports_PERCEPTION_DEMANDED_on_a_real_collapse(monkeypatch):
    """SPECIFICITE : un vrai effondrement, bien AU-DESSUS du plancher, doit rester un positif."""
    assert _wdm_injecte(monkeypatch, 40.0, 5.0)["verdict"] == "PERCEPTION_DEMANDED"


def test_demand_marker_reports_NEUTRAL_on_a_real_decoy(monkeypatch):
    """SPECIFICITE inverse : ablater ne change presque rien, au-dessus du plancher -> leurre REEL."""
    assert _wdm_injecte(monkeypatch, 40.0, 39.0)["verdict"] == "NEUTRAL"


@pytest.mark.xfail(strict=True, reason=(
    "DEFAUT CONNU (2026-09-01) : la branche `collapse` d'`ablation_verdict` rend X_DEMANDED sans "
    "consulter `why`. Un bras intact SOUS le plancher declare (7 <= 9) produit donc un FAUX POSITIF. "
    "Fichier d'une session parallele en cours de travail (elle traite ces branches une par une) -- "
    "non modifie ici. Quand ce sera corrige, ce test PASSERA et l'xfail strict echouera : retirer "
    "alors le marqueur."))
def test_demand_marker_should_REFUSE_a_positive_below_the_declared_floor(monkeypatch):
    """⚠️ Deux bras mourant a 7 et 3 ticks, tous deux SOUS le plancher de survivabilite, ne peuvent pas
    prouver que la perception est exigee. `ablation_verdict` le SAIT (degenerate=True, why renseigne)
    et l'ignore dans cette branche."""
    assert _wdm_injecte(monkeypatch, 7.0, 3.0)["verdict"] == "INCONCLUSIVE_DEGENERATE"


def test_the_degeneracy_IS_detected_even_though_the_verdict_ignores_it():
    """Ce que le defaut n'est PAS : le detecteur ne se trompe pas, il est simplement pas lu. Geler ce
    fait empeche qu'on « corrige » `_degeneracy` alors que le probleme est dans le branchement."""
    from tools.demand_marker import ablation_verdict
    r = ablation_verdict([7.0] * 12, [3.0] * 12, floor=9.0)
    assert r["degenerate"] is True and "PLANCHER" in (r["why"] or "").upper(), (
        "le detecteur de degenerescence doit continuer a VOIR le plancher")
