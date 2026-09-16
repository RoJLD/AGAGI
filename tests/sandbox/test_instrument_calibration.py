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
    # 10e ELARGISSEMENT (2026-09-09) : le VERBE NU. Deux faux positifs, avec leur motif.
    "tools/jobs/run.py::run": "primitive d'ORDONNANCEMENT : lance une commande externe en tenant un bail sur des ressources nommees, avec timeout et kill de l'arbre de processus. Elle rapporte un code de sortie et des chronos, jamais une grandeur du monde ni un verdict sur un agent. Meme justification que `is_machine_idle.py::verdict` : infrastructure.",
    "tools/parity_check.py::classify": "classe un COMMIT (liste de fichiers + message) en EXPERIENCE / DOC / DEV a partir de chemins et d'expressions regulieres. L'affirmation porte sur l'etat du DEPOT, pas sur la nature : aucune simulation, aucun agent, aucune grandeur mesuree. Outillage de discipline de commit.",
    # 9e ELARGISSEMENT DU PERIMETRE (2026-09-09) : `src` entier + les .py de la RACINE.
    "src/metaprog/secure_sandbox.py::run_sandboxed": "infrastructure d'execution : valide du code par une passe AST puis l'execute dans un dossier temporaire hors-repo (subprocess `python -I -S`, env scrube, timeout) et rend (ok, raison) sur la VALIDITE DU CODE. Aucune construction de monde, aucun agent, aucune grandeur mesuree ; l'affirmation porte sur du texte source, pas sur la nature. Meme justification que `is_machine_idle.py::verdict`.",
    "test_fixes.py::run_all_tests": "script de verification ad hoc a la racine : imprime PASS/FAIL sur cinq correctifs de code et rend un booleen d'agregation. C'est un harnais de test, du meme genre que ce que contient `tests/` (deja hors perimetre) ; il n'affirme rien sur le monde ni sur un agent.",
    "test_fixes_simple.py::run_all_tests": "variante allegee de `test_fixes.py`, meme nature : harnais de test a la racine, aucune affirmation scientifique.",
    # P2.43 (2026-09-06) : 4 helpers de la famille run_* -- aucune affirmation scientifique.
    "tools/edr_lenses.py::run_lenses": "outillage d'analyse : boucle des appels au `llm_fn` injecte et rend des textes d'interpretation etiquetes SPECULATIFS (bandeau edr_lenses.py:54-55, « ce sont des PISTES, pas des findings ») ; ne construit aucun monde, ne mesure rien, ne prononce aucun verdict ; aucun record ni backlog ne cite sa sor",
    "tools/grad_mem.py::run_bptt": "primitive numerique (forward deroule + BPTT manuel, grad_mem.py:19-65) sur W et batch fournis par l'appelant ; renvoie (loss, dW, acc) d'un batch, sans seuil, sans verdict, sans agregation, sans choix de protocole ; l'affirmation publiee (accuracy finale sur 512 tirages frais, EDR 067 tableau / EDR ",
    "tools/linguist.py::run_linguistic_analysis": "analyse DESCRIPTIVE legataire : lecture de la KuzuDB de prod (data/kuzu_graph.db, meme chemin que AsyncLogger) + K-Means ; sortie = effectifs et centres de clusters imprimes (linguist.py:57-60) ; aucune quantite de decision (ni seuil, ni ratio, ni verdict calcule) ; la « conclusion » :62-65 est un t",
    "tools/skinner_box.py::run_skinner_test": "audit d'interpretabilite QUALITATIF : une passe forward sur un genome donne, affiche le top-5 des activations cachees et le decodage des sorties, etiquette des neurones dans KuzuDB (NeuronConcept, lu par tools/sociologist.py:113 pour impression) et rend l'etat recurrent brut (H_new[0]). Aucun verdic",
    "tools/is_machine_idle.py::verdict": "decide si la MACHINE est inoccupee (processus biosphere "
               "actifs, age du WAL) pour ordonnancer des jobs. Infrastructure, aucune affirmation "
               "sur le monde ni sur un agent.",
    # 11e ELARGISSEMENT (P2.62, 2026-09-15) : motifs `learn*` tolerants a l'INDENTATION. Trois faux positifs
    # de PROFONDEUR : des wrappers de CAPTURE imbriques dans des fonctions de pre-vol (P4.8 / P4.9), qui
    # interceptent ce qui atteint le learner d'origine et le lui repassent tel quel -- ils n'apprennent
    # rien et n'affirment rien ; l'instrument est le pre-vol qui les lit (preflight_reward_seam,
    # preflight_credit_seams), calibre a reponse connue.
    "tools/evo_runs/s2_reward_ablation.py::learn": "wrapper de CAPTURE imbrique (first_tick_reward, "
               "_ticks_reward_trace) : copie les recompenses recues puis appelle l'original ; aucune mise a "
               "jour propre, aucune affirmation.",
    "tools/evo_runs/s2_credit_ablation.py::learn": "wrapper de CAPTURE imbrique (_learning_trace) : lit le "
               "pas sur l'optimiseur et copie les recompenses recues, puis appelle l'original.",
    "tools/evo_runs/s2_credit_ablation.py::learn_episode": "wrapper de CAPTURE imbrique (_learning_trace) : "
               "copie les recompenses episodiques recues puis appelle l'original.",
    # P4.16 (2026-09-22) : memes wrappers de capture (_learning_trace_2) + les deux seams de credit_variant
    # (coupe l'episodique / substitue une constante) -- aucune mise a jour propre, aucune affirmation ;
    # l'instrument est preflight_credit_seams_2, calibre a reponse connue.
    "tools/evo_runs/s2_credit_ablation_2.py::learn": "wrapper de CAPTURE imbrique (_learning_trace_2) et seam "
               "reward_const de credit_variant : copie ou substitue les recompenses puis appelle l'original.",
    "tools/evo_runs/s2_credit_ablation_2.py::learn_episode": "wrapper de CAPTURE imbrique (_learning_trace_2) et "
               "seams episode_enabled / reward_const de credit_variant : rend None ou substitue puis appelle l'original.",
    # Harnais ADR-004, tache 2 (2026-09-16).
    "src/seed_ai/harness_learner.py::learn": "stub de PROTOCOL (LearnerInstance.learn, corps `...`) : declare la signature du contrat, n'apprend rien, ne rend rien ; les implementations (tools/harness/learners/*.py::learn) sont declarees CALIBRATED.",
}

CALIBRATED = {
    # 10e ELARGISSEMENT DU PERIMETRE (2026-09-09) : le VERBE NU. Les motifs exigeaient tous un
    # SOUFFIXE, donc le verbe seul passait : +7 noms / +22 definitions. `compare` NU vit dans 10
    # fichiers et rend `compute_ab_verdict` -- deux de ses docstrings disent litteralement
    # « verdict de learnabilite » et « verdict de survie ». Dans substrate_ab_compositional.py il
    # coexistait avec `compare_gate_modes` CAPTURE, dans le meme fichier, depuis le 6e elargissement.
    # 20 gardes d'en-tete posees, 40 cas dans _MESURES_GARDEES_8 (fires + emplacement).
    # ⚠️ HONNETETE REQUISE, et elle est chiffree en P2.49 : ces 20 declarations sont de la famille
    # GARDE-SEULE -- aucun de leurs cas n'atteint le corps. Elles GROSSISSENT donc la dette que la
    # meme passe vient de mesurer, au lieu de la reduire. Les compter comme « calibrees » sans le
    # dire serait exactement le faux vert qu'on denonce. Un cas CORPS-ATTEINT y coute un monde ;
    # l'ordre de resorption est ecrit en P2.49.
    # P2.56 (2026-09-14) : re-declare d'apres tests/sandbox/test_anticipation_bench.py (corps atteint).
    "tools/anticipation_bench.py::compare": ["cohorte-vide:raises", "guard-before-world",
                                             "corps-atteint:verdict-dans-ensemble:smoke"],
    "tools/life_score_contamination_probe.py::compare": ["cohorte-vide:raises", "guard-before-world"],
    # P2.56 : INJECTION d'orchestrateur (`run_era_fn=_fake_pool_runner`) -- la couche d'agregation
    # est testee sans monde ; plus un smoke reel (test_compare_smoke_real).
    "tools/map_elites_compare.py::compare": ["cohorte-vide:raises", "guard-before-world",
                                             "injection:structure-et-verdict", "reel:smoke-coverage>=1"],
    "tools/substrate_ab.py::compare": [
        "cohorte-vide:raises", "guard-before-world",
        "CORPS-ATTEINT:appariement-des-DEUX-backends-par-seed",
        "CORPS-ATTEINT:defaut-3-seeds-ne-peut-RIEN-conclure"],
    "tools/substrate_ab_compositional.py::compare": [
        "cohorte-vide:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue", "CORPS-ATTEINT:per_seed-conserve"],
    "tools/substrate_ab_compositional.py::sweep": [
        "cohorte-vide:raises", "guard-before-world",
        "CORPS-ATTEINT:dedup-quand-facteurs-IDENTIQUES",
        "CORPS-ATTEINT:AUCUNE-dedup-quand-facteurs-DIFFERENTS"],
    "tools/torch_binary_gate_heldout_probe.py::compare": ["cohorte-vide:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue-mediane-0.5", "CORPS-ATTEINT:plancher-de-puissance-au-defaut",
        "CORPS-ATTEINT:bras-egaux-neutre"],
    # P2.56 (b) 2026-09-16/22 : injection a dose connue de run_arm (tests/sandbox/test_torch_gate_orchestrators_injection.py) --
    # ON 0,40 / OFF 0,10 / SHUFFLE 0,10 -> GRADIENT_GAGNE ET verdict_vs_shuffle GRADIENT_GAGNE ; label MEMORISE (ON == SHUFFLE) ->
    # verdict positif mais verdict_vs_shuffle NEUTRE (confond C1/I1 vu) ; gap INDEFINI (None) compte 0,0 ET compte (n_gap_indefini).
    "tools/torch_binary_gate_probe.py::compare": ["cohorte-vide:raises", "guard-before-world",
                                                  "dose:GRADIENT_GAGNE+vs_shuffle", "label-memorise:vs_shuffle-NEUTRE",
                                                  "gap-indefini:0-et-compte"],
    "tools/torch_gate_persist_ab.py::compare": ["cohorte-vide:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue-mediane-0.5", "CORPS-ATTEINT:plancher-de-puissance-au-defaut",
        "CORPS-ATTEINT:bras-egaux-neutre"],
    "tools/torch_inworld_ab.py::compare": ["cohorte-vide:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue-mediane-0.5", "CORPS-ATTEINT:plancher-de-puissance-au-defaut",
        "CORPS-ATTEINT:bras-egaux-neutre"],
    # P2.56 (b) : injection de run_arm -- ON +0,30 vs SHUFFLE +0,05 sur 5 seeds -> GRADIENT_GAGNE (diff 0,25, rows apparies par
    # seed, ON puis SHUFFLE) ; no-op EXACT (SHUFFLE == ON) -> NEUTRE ; n = 3 -> NEUTRE + underpowered (la garde de puissance dit).
    "tools/torch_throw_gate_inworld_ab.py::compare": ["cohorte-vide:raises", "guard-before-world",
                                                      "dose:GRADIENT_GAGNE", "noop-exact:NEUTRE", "n=3:NEUTRE+underpowered",
                                                      "apparie-par-seed:ON-puis-SHUFFLE"],
    # P2.56 (b) : _world/_adjacent_ref injectes -- paires (token, referent) collectees pour les SEULS agents adjacents a un
    # referent, le silence est le token 4, un agent sans referent n'est pas collecte : [(0, M), (4, M)] x 2 eres.
    # temoin : tests/sandbox/test_mute_simulators_fake_world.py
    "tools/lexicon.py::measure": ["argument-degenere:raises", "guard-before-world",
                                  "paires:token-referent-adjacent-seulement", "silence:token-4",
                                  "sans-referent:non-collecte"],
    # P2.56 (b) : _world/_apex_ctx injectes -- la mesure lit les politiques EVOLUEES (prime OFF a chaque ere) ; 1 silencieux sur 3
    # -> part de silence 1/3, MI > permutee ; aucun contexte -> (0.0, 0.0, 1.0) publie tel quel (porte 14 legataire).
    # temoin : tests/sandbox/test_mute_simulators_fake_world.py
    "tools/speaker_incentive.py::measure": ["argument-degenere:raises", "guard-before-world",
                                            "mesure-pure:prime-OFF-chaque-ere", "dose:silence-1/3-MI>permutee",
                                            "absence:(0,0,1.0)-publiee-telle-quelle"],
    # P2.56 (b) : injection de _eras_to_master (tests/sandbox/test_mute_orchestrators_injection_3.py) -- curriculum 5 eres /
    # controle 10 -> ratio 2,0 ; egaux -> 1,0 ; un run invalide est IGNORE (moyenne sur les valides) ; aucun valide -> None.
    "tools/transfer_ratio.py::measure": ["argument-degenere:raises", "guard-before-world", "dose:ratio-2.0",
                                         "egaux:ratio-1.0", "run-invalide:ignore", "aucun-valide:None-pas-un-nombre"],
    "tools/anticipation_demand_world_probe.py::probe": ["argument-degenere:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue-ratio-2.0", "CORPS-ATTEINT:plancher-de-puissance-n<12",
        "CORPS-ATTEINT:decoy-medianes-egales", "CORPS-ATTEINT:ratio-inverse",
        "CORPS-ATTEINT:bras-identiques-degenere"],
    "tools/composition_demand_world_probe.py::probe": ["argument-degenere:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue-ratio-2.0", "CORPS-ATTEINT:plancher-de-puissance-n<12",
        "CORPS-ATTEINT:decoy-medianes-egales", "CORPS-ATTEINT:ratio-inverse",
        "CORPS-ATTEINT:bras-identiques-degenere"],
    "tools/memory_demand_world_probe.py::probe": ["argument-degenere:raises", "guard-before-world",
        "CORPS-ATTEINT:dose-connue-ratio-2.0", "CORPS-ATTEINT:plancher-de-puissance-n<12",
        "CORPS-ATTEINT:decoy-medianes-egales", "CORPS-ATTEINT:ratio-inverse",
        "CORPS-ATTEINT:bras-identiques-degenere"],
    "tools/generalization_transfer_probe.py::run": ["argument-degenere:raises", "guard-before-world"],
    "tools/memory_payoff_probe.py::run": ["argument-degenere:raises", "guard-before-world"],
    # P2.56 (b) : injection de survive / life_seeds -- vie = seed + 5 : mediane ET les vies publiees predites exactement ;
    # la politique corps-seul est celle de K (body_only_policy(K)).
    "tools/s2_fallback_rate_probe.py::measured_floor": ["argument-degenere:raises", "guard-before-world",
                                                        "vies-connues:mediane-exacte", "vies-publiees:toutes", "corps-seul:K"],
    # 9e ELARGISSEMENT DU PERIMETRE (2026-09-09) : `_SCAN_DIRS` passe de ("tools", "src/seed_ai") a
    # ("tools", "src") + un balayage PLAT de la racine. Dette REELLE revelee, comme aux huit
    # elargissements precedents -- et cette fois elle vise le CLIQUET LUI-MEME :
    # `tools/hcm_analyzer.py::run_hcm_analysis` etait DECLARE CALIBRE et ne pouvait pas s'executer
    # (TypeError ligne 29 sur le contrat de `load_hall_of_fame`). Ses deux cas -- `empty-cohort:raises`
    # et `guard-before-world` -- n'exercent que la garde d'arguments, qui leve AVANT le corps.
    # Mesure de l'exposition : 92 des 248 declarations (37 %) sont dans ce cas. Les cas ci-dessous
    # ATTEIGNENT le corps ; c'est la difference qui compte, pas leur nombre.
    # 12 cas dans tests/sandbox/test_perimeter_widening.py, aucun monde construit.
    "src/paths.py::assert_roots_exist": [
        "racine-absente:leve-en-NOMMANT-la-variable", "verification-CIBLEE:ne-crie-pas",
        "aucune-racine-demandee:rend-True"],
    "src/graph_rag/hcm_analyzer.py::run_hcm_analysis": [
        "hof-vide:raises-pas-None", "garde-inerte-CORRIGEE:2-uplet-toujours-vrai",
        "n_clusters-degenere:raises", "guard-before-world"],
    "tools/hcm_analyzer.py::run_hcm_analysis": [
        "empty-cohort:raises", "guard-before-world",
        "CORPS-ATTEINT:contrat-du-HoF", "aucun-genome-compatible:raises-en-chiffrant"],
    "main_curriculum.py::run_curriculum": [
        "regime-degenere:raises", "echelle-vide:raises", "guard-before-world"],
    "multiverse_runner.py::run_world_era": [
        "regime-degenere:raises", "cohorte-vide:raises", "guard-before-world"],
    # P2.56 (b) : CLASSE de monde factice injectee -- proies moyennes 4.0 et 5 ticks (cohorte morte au tick 5) ; l'horizon
    # max_ticks 2 borne la boucle AVANT la mort ; target_prey pose sur la config (E8).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_3.py
    "tools/curriculum_world.py::run_world_era": ["empty-cohort:raises", "guard-before-world", "dose:proies-4.0-ticks-5",
                                                 "horizon:borne-la-boucle-avant-la-mort", "regime-E8:target_prey-pose"],
    # `tools/substrate_ab_compositional.py::run_curriculum` etait declare ICI ET plus bas (clé en
    # DOUBLE dans un dict litteral : la seconde ecrase la premiere sans un mot). Retire le 2026-09-14 ;
    # la declaration qui fait foi est celle du bloc G2, plus bas, qui nomme les cas reels.
    # P4.1-MECANISME (2026-09-09) : par quel CANAL le grab coute-t-il 39 % de survie ?
    # 14 cas dans tests/sandbox/test_grab_mechanism.py, dont 12 SANS aucune simulation (gardes en
    # tete, compteur calibre par injection a dose connue, mecanisme verifie sur le CODE).
    # Les deux cas qui comptent : (1) l'ANCRAGE -- la boucle refaite doit rendre la survie EXACTEMENT
    # egale a `run_condition`, l'instrument audite qui a produit le record, sans quoi le bilan
    # energetique decrirait un autre monde (E19 occ. 6) ; (2) le BOUCLAGE -- le poste `carry` du
    # moteur doit valoir 0.5 x le poids recense au MEME instant. La premiere version recensait
    # l'inventaire en tete de tick, donc AVANT le grab : bilan coherent avec lui-meme, facteur 3,7
    # d'ecart avec le moteur. Un recensement qui ne boucle pas produit une attribution de canal.
    "tools/grab_mechanism_probe.py::run_census_arm": [
        "regime-degenere:raises", "guard-before-world", "ancrage-egal-run_condition",
        "observateur-bit-identique", "bouclage-carry-vs-moteur", "dose-connue:3-doses",
        "census-vide:None-pas-zero", "compteur-remis-a-zero", "regime-mesure!=regime-annonce",
        "revenu-fruit-etrangle:code", "recensement-avant-masquage"],
    # P2.46 (2026-09-08) : garde E24 -- les blocs ENTREE et SORTIE du genome se CHEVAUCHENT, et 18
    # logits d'action du champion SONT l'observation. 4 cas dans tests/sandbox/test_control_family.py,
    # dont le contre-exemple gele (le champion, refuse avec son chiffre) apparie a son no-op (un
    # genome frais passe) ET au cas LIMITE (zero noeud cache mais aucun slot partage : la garde porte
    # sur le chevauchement, pas sur la platitude du connectome).
    "tools/experiment_preflight.py::assert_no_io_overlap": [
        "champion:refuse-et-chiffre", "frais:passe", "limite-exact:passe", "pas-un-genome:refuse"],
    # P2.42 (2026-09-08) : S2-BLIND-CHAMPION -- un champion RENDU AVEUGLE survit-il MIEUX ?
    # 14 cas dans tests/sandbox/test_s2_blind_champion.py, aucun monde construit (map_fn injectee).
    # La branche qui compte est PAS_DE_COUT : l'observation d'origine (+39 %) est POSITIVE et a n=1,
    # donc un dispositif qui ne saurait pas la RETRACTER ne prouverait rien (classe E1).
    "tools/evo_runs/s2_blind_champion.py::blind_champion_verdict": [
        "aveugle-survit-mieux", "pas-de-cout:retracte", "indetermine:bande",
        "indetermine:signe-incoherent", "aveugle-encore-sensible:harnais",
        "intervention-non-minimale:harnais", "bras-manquant!=bras-nul",
        "sous-plancher:ecarte-et-nomme", "moins-de-2-seeds", "entree-vide:pas-de-fond"],
    "tools/evo_runs/s2_blind_champion.py::run_blind_champion": [
        "plan-vide:raises", "regime-degenere:raises", "guard-before-world",
        "appariement-meme-seed", "aveuglement-pose-et-verifie"],
    # P2.42 -bis/-ter (2026-09-16) : l'aveuglement passe a l'ENTREE (obs nulle, corps et W intacts, chemin
    # d'identite E24 coupe), apprenant legacy gele dans les deux bras, bande appariee. 8 cas dans
    # tests/sandbox/test_s2_blind_champion_bis.py, 0 monde : l'aveugle IGNORE l'obs la ou la base la lit
    # (controle positif), le credit gele ne bouge pas W la ou le credit de base le bouge (controle positif),
    # garde en tete, injection de map_fn (classes, bande appariee, no-op demandes ; verdict calibre applique ;
    # controle (ii) prime). Le verdict -ter corrige la clause (iii) : ecarte seulement si les DEUX bras sont au
    # plancher -- le -bis a rendu INDETERMINE-DEGENERE (7/7 ecartes) parce que l'intact SOUS le plancher
    # etait le PHENOMENE ; 5 seeds unanimes = p 0,0625 -> INDETERMINE (puissance dite, pas avalee).
    "tools/evo_runs/s2_blind_champion_bis.py::run_blind_champion_bis": [
        "plan-vide:raises", "regime-degenere:raises", "guard-before-world",
        "classes-bande-appariee-noop:demandes", "meme-genome-deux-bras", "controle-ii:harnais"],
    "tools/evo_runs/s2_blind_champion_bis.py::blind_champion_verdict_ter": [
        "intact-sous-plancher:garde-et-nomme", "deux-bras-au-plancher:ecarte", "tous-ecartes:degenere-pas-sans-mesure",
        "5-seeds-unanimes:indetermine-p0.0625", "6-seeds:lisible", "pas-de-cout", "controle-ii-prime", "entree-vide:pas-de-fond"],
    # `compute_policy_gradient` de FrozenCreditMamba (tools/evo_runs/s2_blind_champion_bis.py) : no-op EXACT
    # (W bit-identique), confronte au credit de base qui bouge W -- test_frozen_credit_leaves_W_untouched_...
    "tools/evo_runs/s2_blind_champion_bis.py::compute_policy_gradient": ["noop:W-bit-identical", "base:moves-W"],
    # S2-002-PAIRED-R1 (2026-09-22, P2.41 b -> decision robla) : carte d'ablation-perception a bande APPARIEE. Runner
    # tools/evo_runs/s2_002_paired.py ; 8 cas dans tests/sandbox/test_s2_002_paired.py, 0 monde : injection de map_fn
    # (paired_band ET noop_control DEMANDES par cellule, cles (monde, seed), reprise respectee, garde en tete) ; la lecture
    # s2_paired_lecture atteint chaque branche dans l'ordre impose (INCOMPLET, HARNAIS par monde, CARTE_INCHANGEE,
    # CARTE_MODIFIEE, MIXTE) et publie le signe post-hoc hors verdict.
    "tools/evo_runs/s2_002_paired.py::run_s2_paired": ["plan-vide:raises", "guard-before-world",
                                                        "bande-appariee-et-noop:demandes", "reprise:respectee",
                                                        "lecture:branches-ordre-impose", "signe-post-hoc:hors-verdict"],
    # DECOMP-R1 (2026-09-16) : decomposer le +61 % -- entree du reseau coupee (identites gardees) vs 18 identites
    # coupees. 6 cas dans tests/sandbox/test_s2_blind_champion_bis.py, 0 monde : masques EXACTS (tranche annoncee a
    # zero, le reste intact, entree non mutee), complementaires ; branches dans l'ordre impose ; no-op EXACTEMENT 1
    # sinon HARNAIS ; convention 6/7 ; runner : references importees par seed, deux bras demandes, garde en tete.
    "tools/evo_runs/s2_blind_champion_bis.py::decomp_verdict": [
        "excitation", "identite", "les-deux", "ni-l-un-ni-l-autre", "mixte:entre-les-barres", "6/7:convention",
        "noop-non-exact:harnais", "w_ok-faux:harnais", "entree-vide:pas-de-fond"],
    "tools/evo_runs/s2_blind_champion_bis.py::run_decomp": [
        "plan-vide:raises", "references-importees-par-seed", "deux-bras-bande-appariee-noop"],
    # P2.41 (2026-09-08) : S2-SUBJECT-VARIANCE -- le verdict du marqueur varie-t-il avec le SUJET ?
    # 14 cas dans tests/sandbox/test_s2_subject_variance.py, aucun monde construit (map_fn injectee).
    # La branche qui COMPTE est INDETERMINE-BRUIT : sans le bras de replication du MEME sujet, le
    # critere << >= 2 sujets divergent >> pouvait etre franchi par le seul bruit sur 21 paires
    # (classe E23, trouvee AVANT le run en appliquant `assert_control_family`).
    "tools/evo_runs/s2_subject_variance.py::subject_variance_verdict": [
        "controle-absent!=passe", "positif-echoue:instrument", "negatif-mord:instrument",
        "subject-bound", "indetermine-bruit", "world-bound:exige-stabilite",
        "sans-replicat:refuse", "degenere:ecarte-et-nomme", "moins-de-2-sujets",
        "corps-confondu:rapporte", "entree-vide:pas-de-fond"],
    "tools/evo_runs/s2_subject_variance.py::run_subject_variance": [
        "plan-vide:raises", "regime-degenere:raises", "guard-before-world",
        "meme-regime-partout", "graine-de-monde-par-cellule", "sujet-de-la-cellule"],
    # P2.40 (2026-09-07) : garde E23 -- « une FAMILLE de controles n'est pas traitee comme une
    # famille ». 20 cas dans tests/sandbox/test_control_family.py, dont le CONTRE-EXEMPLE GELE (la
    # bande fixe d'EVO-011 rejouee en forme close : 0.216 de fausse alarme sur un harnais PARFAIT)
    # apparie a son no-op EXACT (le seuil du sceau -bis, 0.05/24, doit passer sans bruit).
    "tools/experiment_preflight.py::assert_control_family": [
        "bonferroni:seuil-exact", "cells=1:no-op", "seuil-trop-large:refuse",
        "plus-strict:accepte", "none:exige-raison", "entrees-degenerees:refuse",
        "contre-exemple-evo011:refuse", "reglage-bis:accepte"],
    # P2.50 (2026-09-07) : pre-vol EVO-011 (`tools/evo_runs/evo011_preflight.py`). 22 cas dans
    # tests/sandbox/test_evo011_preflight.py. `verdict_evo011_prevol` est l'instrument PUR (aucun
    # monde) ; `run_arm` / `run_seed` construisent le monde -- leurs CABLAGES sont calibres sans
    # simulation (arete exacte du sceau, saillance, specificite de canal, logit NUL du temoin,
    # ballast bit-identique, gel de la plasticite), le reste est couvert par les controles du sceau.
    # ⚠️ `run_seed` (9 fichiers) et `run_arm` (7 fichiers) sont en COLLISION -> declarations QUALIFIEES.
    # Ces trois entrees sont apparues quand le perimetre du cliquet est devenu RECURSIF (8e angle
    # mort : `tools/evo_runs/` etait invisible) -- l'elargissement a revele de la dette REELLE, comme
    # les sept precedents.
    "tools/evo_runs/evo011_preflight.py::verdict_evo011_prevol": [
        "ne-paie-pas", "paie:3-sous-lectures", "indetermine:deux-trous", "harnais-prime-sur-dv",
        "degenere:pas-de-negatif", "controles-absents!=passes", "sous-puissance:refuse"],
    "tools/evo_runs/evo011_preflight.py::run_arm": [
        "arete-exacte-du-sceau", "temoin:logit-nul-exact", "lecteur-suit-le-signe",
        "ballast:bit-identique", "gel-plasticite", "saturation:plafond", "saturation:maillon-inerte"],
    "tools/evo_runs/evo011_preflight.py::run_seed": [
        "carry-matched:causalite-inversee", "phenotype-formule-du-monde", "sans-ballast:phenotype-bouge"],
    # P2.50 (2026-09-07) : `tools/jobs/doctor.py` -- meme elargissement recursif. Deux branches
    # ajoutees dans tests/sandbox/test_jobs.py (un seul cas existait, celui de la branche `dead` :
    # une classification degeneree « tout est mort » le passait, et `--kill` en depend).
    # 2026-09-22 (E4 occ. doctor, 8a64b0d7) : « dead » recouvrait DEUX états que le rapport ne distinguait
    # pas -- un détenteur VIVANT à TTL expiré (machine en veille, run long) était titré « mort ». Trois états
    # désormais, chacun confronté à un VRAI processus dans tests/sandbox/test_doctor_visibility.py :
    # expired-alive (ne se réape pas), orphan (détenteur parti, contrôle apparié), et le TEXTE du rapport.
    "tools/jobs/doctor.py::classify_leases": ["live", "dead", "repertoire-vide",
                                              "expired-alive:detenteur-vivant", "orphan:detenteur-parti",
                                              "rapport-sans-mot-mort"],
    # P2.47 (2026-09-07) : runner S6 (taux de faux positifs du marqueur sous init non nulle).
    # 29 cas de calibration dans tests/sandbox/test_s6_fallback_rate.py -- dont le contre-exemple
    # construit (corps suffisant + politique lectrice -> l'ablation MORD), la specificite (politique
    # constante -> bras identiques), l'ancre bit-identique a fit_policy y compris quand le hill-climb
    # ACCEPTE, et le gate qui REFUSE de conclure si le controle positif ne mord pas.
    # ⚠️ `run_seed` est en COLLISION (8 fichiers) -> declaration QUALIFIEE.
    "tools/s2_fallback_rate_probe.py::run_seed": ["cell-sigma-seed", "resumable", "params-in-key"],
    "tools/s2_fallback_rate_probe.py::run_arms": ["four-rungs", "crn-per-life"],
    "tools/s2_fallback_rate_probe.py::original_ladder_verdict": ["reproduces-origin", "majority-tie"],
    "tools/s2_fallback_rate_probe.py::assert_no_world": ["static-imports:raises", "clean:passes"],
    "tools/s2_fallback_rate_probe.py::assert_intervention_perturbs_input": ["rungs-perturb", "true-is-noop"],
    "tools/s2_fallback_rate_probe.py::assert_crn_exactness": ["zero-exact", "permuted-shifted"],
    # P2.46 (2026-09-06) : 11 orchestrateurs run_* -- garde d'entree.
    # P2.44 (2026-09-08) : les SIX derniers passent a leur tour de « garde d'entree SEULEMENT » a
    # « garde + BRANCHES DE VERDICT », par injection a dose connue (tests/sandbox/test_inj_run_*.py,
    # 83 cas, controle E1 PAR MUTATION sur chacun). Les 11 orchestrateurs sont desormais calibres
    # sur leurs branches, pas seulement sur leur entree. 25 xfail STRICTS y tiennent la dette des
    # defauts REELS trouves au passage et non corriges -- dont trois affirmations de FOND publiees
    # depuis une entree vide (`empty-baseline:NEUTRE`, `total-extinction:NUIT`, troncature
    # silencieuse d'un baseline de longueur differente).
    # P2.48 (2026-09-07) : les CINQ prioritaires ont en plus leurs BRANCHES DE VERDICT calibrees par
    # injection a dose connue (tests/sandbox/test_orchestrator_injection.py, 43 cas, controle E1 par
    # mutation 6/6). Les 6 restants n'ont toujours QUE leur garde d'entree -- dette au backlog.
    "tools/cross_world_transfer.py::run_direction": ["empty-cohort:raises", "guard-before-world",
        "guard-position:before-hof", "reads-transfer-dose", "neutral-band-load-bearing",
        "sign-p-gates-power", "majority-not-only-median", "pairs-seed-by-seed-not-aggregate",
        "regime-wired-to-both-arms", "baseline-reused-once"],
    "tools/curriculum_transfer.py::run_transfer_experiment": ["empty-cohort:raises",
        "guard-before-world", "verdict-transfere-reads-dose", "verdict-nuit-reads-dose",
        "neutral-band-blocks-small-effect", "power-guard-E14-is-read", "seeds-disagree-neutral",
        "median-ratio-follows-dose", "both-arms-same-seed", "equal-era-budget",
        "tabula-arm-runs-target-only", "replication-unit-is-seed", "ratio-pairs-within-seed",
        "regime-wired-to-engine", "metric-world-not-survival", "injected-era-fn-builds-no-world",
        "logger-released-on-raise"],
    "tools/dreaming_probe.py::run_q1": ["empty-cohort:raises", "guard-before-world",
        "pressure-reads-dose", "feeds-dreaming-verdict", "median-not-mean",
        "pairs-regimes-within-seed"],
    "tools/dreaming_probe.py::run_q2": ["empty-cohort:raises", "guard-before-world",
        "ratio-reads-dose:pos-neg-null", "feeds-dreaming-verdict:pay_eps-bracketed",
        "ratio-cap:asymmetric", "pairing:within-seed", "regime:sweet-spot-both-arms",
        "dreams-counted:ON-arm-only", "split:both-directions", "split:strict-threshold",
        "median-not-mean", "replication-unit:seed", "founder-control:no-explosion",
        "intra-pop-delta:contrast-when-reference-exists"],
    "tools/dream_causal_probe.py::run_causal": ["empty-cohort:raises", "guard-before-world",
        "dose-response-read", "poses-intervention-anchors-deepest", "restores-global-on-raise",
        "default-seeds-cannot-conclude"],
    "tools/dream_causal_probe.py::run_founder_matched": ["empty-cohort:raises",
        "guard-before-world", "dose-fondateurs:forme-close", "confond-E15:med_all-vs-med_founder",
        "issue-negative:no-op-exact", "issue-negative:dose-inverse",
        "appariement:signature-par-seed", "unite-de-replication:seeds-pas-agents",
        "journal-appels:ordre-off-on", "cablage-regime:k-int-aux-deux-bras",
        "cablage-regime:parametres-identiques",
        "etat-global:FORCE_DREAM-restaure-meme-sur-exception", "persistance:json==objet",
        "seam:attribut-de-module"],
    "tools/dream_distress_probe.py::run_distress": ["empty-cohort:raises", "guard-before-world",
        "reads-dream-rate-dose", "five-seed-boundary", "seeds-not-agents-as-replicates",
        "pairs-split-with-seed", "sweet-spot-regime-wired", "no-world-built"],
    "tools/evo_memory_enrichment.py::run_experiment": ["empty-cohort:raises", "guard-before-world",
        "reads-recall-dose", "reversed-contrast", "one-value-per-seed-paired",
        "three-seeds-cannot-conclude", "wires-task-and-oos-seed", "sep-does-not-move-verdict"],
    "tools/evo_memory_inworld.py::run_contrast": ["empty-cohort:raises", "guard-before-world",
        "per-seed-dose", "reversed-contrast", "synthesis-both-directions",
        "zero-encounters-not-null", "n-equals-one", "consumed-iterator:raises"],
    "tools/s2_demand.py::run_s2": ["empty-cohort:raises", "guard-before-world",
        "reads-survival-dose", "lifescore-gate-no-void", "reflex-high-bound",
        "within-only-if-not-void", "holm-over-whole-family", "holm-survives-iterator",
        "pilot-K-wired", "empty-world-list:raises"],
    "tools/s2_openloop_probe.py::run_openloop_ladder": ["empty-cohort:raises",
        "guard-before-world", "three-rung-ladder", "intact-on-floor:refused",
        "rung-identical:refused", "per-world-independent", "same-champion-four-arms",
        "empty-world-family:raises"],
    # P2.45 (2026-09-06) : 6 homonymes reveles par le correctif du faux vert par nom nu -- QUALIFIES.
    # P2.56 (b) : _world/_apex_ctx injectes -- 2 parleurs parfaits pres d'un apex + 1 agent loin (IGNORE) : n = 2 eres x 2 ticks
    # x 2 = 8, MI > permutee ; aucun contexte -> (0.0, 0.0, 0) publie tel quel (defaut legataire de porte 14).
    # temoin : tests/sandbox/test_mute_simulators_fake_world.py
    "tools/lewis_world.py::measure_mi": ["empty-cohort:raises", "guard-before-world",
                                         "monde-factice:n-8-agent-loin-ignore", "dose:code-parfait-MI>permutee",
                                         "absence:(0,0,0)-publiee-telle-quelle"],
    "tools/target_competence_probe.py::run_probe": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : injection de measure_arm (tests/sandbox/test_mute_orchestrators_injection_2.py) -- survies 100 / 120 ->
    # survival_ratio 1,2 ; z_range 2,0 + updown 0,5 -> Z_UTILISE ; z 0,1 -> Z_INERTE ; updown 0,2 (sous 0,25 x 1,2) -> Z_INERTE.
    "tools/vertical_world_probe.py::run_probe": ["empty-cohort:raises", "guard-before-world", "dose:Z_UTILISE",
                                                 "z-inerte:Z_INERTE", "updown-sous-seuil:Z_INERTE", "survival_ratio:predit"],
    "tools/lethality_curriculum.py::_verdict": ["negatif-profond", "casse-bootstrap", "pas-le-goulot"],
    "tools/lewis_survival_sweep.py::_verdict_capacity": ["leve", "inerte", "ambigue", "single-arm:raises"],
    # P2.49 (2026-09-10) : les DEUX FRERES de `_verdict_capacity`, traites dans la meme passe.
    # ⚠️ Leur declaration disait `["empty:raises"]` -- donc GARDE-SEULE, donc comptee dans la dette --
    # alors que leurs QUATRE et TROIS branches etaient DEJA confrontees a des reponses connues dans
    # `tests/sandbox/test_edr105_forage_funnel.py` et `tests/sandbox/test_edr113_landing.py`. La
    # dette etait DECLARATIVE, pas testimoniale : elle coutait une ligne, pas un monde. Mesure de la
    # meme forme sur tout le lot : 64 des 103 declarations garde-seule ont un test qui IMPORTE le
    # symbole DEPUIS SON MODULE (analyse AST : apparier par nom NU rendait un chiffre FAUX, trois
    # `compare` differents pointant les deux memes fichiers -- l'angle mort des collisions, reproduit
    # par l'instrument qui mesurait la dette).
    # ⚠️ Et la passe qui re-declare a trouve DEUX defauts reels dans les corps enfin regardes :
    # `_verdict_landing` rendait AFFORDANCE INERTE sur UN SEUL bras (negatif fabrique, classe E14 --
    # la garde du jumeau jamais retro-appliquee) et `_verdict_forage` rendait FORAGE SUFFISANT sur
    # une agregation TOUT NAN (positif fabrique, plus rare donc plus dangereux). Les deux gardes sont
    # posees EN TETE, les deux incidents sont geles comme contre-exemples, chacun apparie a son no-op.
    "tools/lewis_survival_sweep.py::_verdict_landing":
        ["leve", "inerte", "ambigue", "single-arm:raises", "empty:raises", "deux-bras:limite-acceptee"],
    # P2.52 (2026-09-14) : `_gaps_pour_verdict`, trois exemplaires IDENTIQUES -- la regle « gap
    # indefini = ne compose pas » rendue explicite ET comptee. Six sites de binding-gap fabriquaient
    # un « jamais Y sachant X » sans un seul X observe ; et le metronome NUL de craft_or_starve etait
    # MORT au dernier quart (0 vivant sur 64 a T = 200), son « gap ~ 0 » etait 0 - 0.
    # Cas dans tests/sandbox/test_gaps_pour_verdict.py, un jeu par exemplaire + identite des trois.
    "tools/craft_or_starve_edr.py::_gaps_pour_verdict":
        ["dose-connue:2-indefinis-sur-4", "noop:aucun-indefini", "tous-indefinis:comptes",
         "zero-mesure:pas-un-indefini"],
    "tools/kchain_edr.py::_gaps_pour_verdict":
        ["dose-connue:2-indefinis-sur-4", "noop:aucun-indefini", "tous-indefinis:comptes",
         "zero-mesure:pas-un-indefini"],
    "tools/torch_binary_gate_probe.py::_gaps_pour_verdict":
        ["dose-connue:2-indefinis-sur-4", "noop:aucun-indefini", "tous-indefinis:comptes",
         "zero-mesure:pas-un-indefini"],
    "tools/lewis_survival_sweep.py::_verdict_forage":
        ["approche", "capture", "revenu", "suffisant", "nan:raises", "cle-absente:raises",
         "bornes-finies:acceptees"],
    "tools/arc5_alignment.py::_verdict": ["aligned:1bit", "independent:baseline"],
    # P2.43 (2026-09-06) : famille run_* -- declarations QUALIFIEES par chemin (5 noms en collision).
    # P2.49 (2026-09-09) : l'instrument GARDE-SEULE le plus PORTEUR du depot -- son module est
    # cite par 61 records, trois fois plus que le suivant. Le corps porte la question dont tout
    # depend : `apply_fn` est-il applique a CHAQUE ere ? Sinon chaque record d'ablation
    # comparerait un bras intact a un bras intact. 4 cas dans test_orchestrator_injection.py,
    # aucun monde construit -- dont un DEFAUT REEL gele (pool vide -> 0.0 proie, indiscernable
    # d'une vraie mesure a zero).
    "tools/ablation.py::run_condition": [
        "empty-cohort:raises", "guard-before-world",
        "CORPS-ATTEINT:ablation-appliquee-a-CHAQUE-ere", "CORPS-ATTEINT:moyenne-dose-connue",
        "CORPS-ATTEINT:pool-vivants-ET-morts", "DEFAUT-GELE:pool-vide-rend-0.0"],
    # P2.56 (b) : CLASSE de monde factice injectee -- le mecanisme (apply_fn) est applique a CHAQUE ere, sur le monde de l'ere ;
    # regime E8 (crit_base transmis, target_prey 12, eps 0.2, craft 0, era 1) ; proies 3.0 / mammouths 2.0.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_5.py
    "tools/ablation_multi.py::run_condition": ["empty-cohort:raises", "guard-before-world",
                                               "mecanisme:applique-a-CHAQUE-ere-sur-le-monde-de-l-ere",
                                               "dose:proies-3.0-mammouths-2.0",
                                               "regime-E8:crit_base-target_prey-12-eps-0.2-craft-0-era-1"],
    "tools/adaptive_planning_probe.py::run_adaptive": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : AgriculturalWorld injecte -- trajectoire PAR TICK (t, n_agents, saison, items) ; seuls les items DECLARES sont
    # comptes (un type inconnu n'apparait pas).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_3.py
    "tools/agricultural_demand_probe.py::run_agricultural": ["empty-cohort:raises", "guard-before-world",
                                                             "trajectoire-par-tick:n_agents-saison-items",
                                                             "items:declares-seuls-comptes"],
    "tools/altar_tool_funnel_probe.py::run_era_funnel": ["empty-cohort:raises", "guard-before-world"],
    "tools/anticipation_bench.py::run_bench": ["empty-cohort:raises", "guard-before-world",
                                               "corps-atteint:avoidance-dans-[0,1]:smoke"],
    # P2.49 (2026-09-09) : le HARNAIS PARTAGE du fil S2 (10 records) -- il porte la couche
    # d'APPARIEMENT que traversent s2_demand_ablation, s2_openloop_probe, cognitive_demand_inworld
    # et warmstart. Meilleure couture du depot : `world_cls` est un PARAMETRE, donc aucun
    # monkeypatch. 4 cas dans test_orchestrator_injection.py, aucun monde reel construit.
    "tools/s2_demand.py::run_condition": [
        "empty-cohort:raises", "guard-before-world",
        "CORPS-ATTEINT:seed_at(seed,i)-une-fois-PAR-ERE", "CORPS-ATTEINT:regime-impose",
        "CORPS-ATTEINT:mediane-par-ere-morts-compris", "CORPS-ATTEINT:censure-rapportee"],
    "tools/anticipation_planning_probe.py::run_planning": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : PUR (numpy) -- W nul : accuracy 0.0 (signe de 0 != +-1) et dW[0, N-O] = -0.25 (descendre le gradient CREE le fil
    # entree->sortie) ; fil direct de poids 10 : accuracy 1.0 (identite ET tanh, D 0 et 1) et dW[0, N-O] = +0.0625.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_6.py
    "tools/arm_act_grad.py::run_bptt_act": ["empty-cohort:raises", "guard-before-world", "W-nul:acc-0.0-gradient--0.25",
                                            "fil-direct:acc-1.0-identite-et-tanh", "fil-trop-fort:gradient-+0.0625"],
    "tools/cognitive_demand_inworld.py::run_credit_linear": ["empty-cohort:raises", "guard-before-world",
                                                           "learning-dose:published"],   # P1.6
    # P2.56 (b) : CLASSE de monde factice injectee -- le levier est POSE sur le monde (hear_radius 7), regime E8 (target_prey 9,
    # LANGUAGE, nuit off) ; agregats crafts 6 / kills 5 / proies 2.0 ; 5 meilleurs promus par life_score.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_3.py
    "tools/comm_lever.py::run_era": ["empty-cohort:raises", "guard-before-world",
                                     "regime-E8:hear_radius-7-target_prey-9-LANGUAGE-nuit-off",
                                     "dose:crafts-6-kills-5-proies-2.0", "promotion:5-meilleurs-par-life_score"],
    "tools/compositional_language_probe.py::run_compositional": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : CLASSE de monde factice injectee -- scramble_signal True et hear_radius 6 POSES sur le monde, target_prey 12,
    # LANGUAGE (E8) ; kills 4 / proies 2.0 ; 5 promus.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_4.py
    "tools/confirm_scramble.py::run_era": ["empty-cohort:raises", "guard-before-world",
                                           "regime-E8:scramble-True-hear_radius-6-target_prey-12-LANGUAGE",
                                           "dose:kills-4-proies-2.0", "promotion:5"],
    "tools/craft_specialization_probe.py::run_spec": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : CLASSE de monde factice injectee -- les DEUX axes poses (target_prey 7, craft_level 2) plus eps, crit_base,
    # nuit off (E8) ; sortie (crafts 8, kills 1, proies 5.0, ticks 4).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_4.py
    "tools/curriculum_2d.py::run_2d_era": ["empty-cohort:raises", "guard-before-world",
                                           "regime-E8:deux-axes-target_prey-7-craft_level-2-eps-crit_base-nuit-off",
                                           "dose:crafts-8-kills-1-proies-5.0-ticks-4"],
    # P2.56 (b) : CLASSE de monde factice injectee -- les TROIS sevrages lisent l'ere GLOBALE (crit_eras, group_reward_eras,
    # current_era poses sur le monde : E8) ; sortie (3, 1, 2.0, 4) ; 5 meilleurs promus, tries par life_score.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_5.py
    "tools/curriculum_developmental.py::run_era": ["empty-cohort:raises", "guard-before-world",
                                                   "regime-E8:trois-sevrages-sur-l-ere-GLOBALE", "dose:(3,1,2.0,4)",
                                                   "promotion:5-meilleurs-tries"],
    # P2.56 (b) : CLASSE de monde factice injectee -- le monde n'est prepare (_setup_grab_training : eps, n_items, keep_prey
    # transmis) QUE sous training ; craft_level pose (E8) ; sortie (10, 6, 5) : l'horizon borne une cohorte immortelle.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_5.py
    "tools/curriculum_grab.py::run_one_era": ["empty-cohort:raises", "guard-before-world",
                                              "monde-prepare:SEULEMENT-en-training", "dose:(10,6,5)-horizon-borne",
                                              "regime-E8:craft_level-pose"],
    "tools/dreaming_probe.py::run_era_organ": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 : corps atteint par test_behavioral_diversity (2 eres, 5 cles de diversite dans [0,1],
    # median_competence dans [0,1]) et test_credit_assignment_gamma (gamma se propage au TD).
    "tools/evolve_ceiling_probe.py::run_evolution": ["empty-cohort:raises", "guard-before-world",
                                                     "2-eres:diversite-decomposee-dans-[0,1]",
                                                     "gamma:propage-au-TD"],
    # P2.56 (b) : CLASSE de monde factice injectee (life_score = id) -- classement rendu par scores DECROISSANTS 6..2 (5 promus
    # sur 7), genomes rendus identiques par CONTENU (from_genome copie), info (ticks 5, eaten 14, mam 3, score 6.0).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_4.py
    "tools/evolve_competence.py::run_era": ["empty-cohort:raises", "guard-before-world",
                                            "classement:scores-decroissants-6..2-genomes-par-CONTENU",
                                            "dose:ticks-5-eaten-14-mam-3-score-6.0", "genomes-vides:raises"],
    # P2.56 (b) : CLASSE de monde factice injectee -- appariement seed_at(base, seed) ; les tues de mammouth des seuls
    # SURVIVANTS comptent ; une tete par genome, entrainees ensemble, portee par CHAQUE agent ; use_ref_head/decode_act poses.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_5.py
    "tools/func_benefit.py::run_seed": ["empty-cohort:raises", "guard-before-world", "appariement:seed_at(base,seed)",
                                        "compte:mammouths-des-seuls-SURVIVANTS",
                                        "tetes:une-par-genome-portee-par-chaque-agent",
                                        "regime-E8:use_ref_head-decode_act"],
    # `tools/hcm_analyzer.py::run_hcm_analysis` etait declare ICI, en version PAUVRE, ET plus haut en
    # version riche (CORPS-ATTEINT, 4 cas). Dans un dict litteral la DERNIERE cle gagne : c'est donc
    # la version pauvre qui faisait foi, et l'instrument comptait comme GARDE-SEULE dans la dette
    # P2.49 alors qu'il etait calibre. Retire le 2026-09-14 ; garde gelee :
    # `test_CALIBRATED_n_a_AUCUNE_cle_en_double`.
    "tools/hunif_retention_probe.py::run_retention": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : _world/_gain injectes -- mode token pose (SPECIATE True, SPECIATE_MODE token) pendant chaque ere puis size
    # RESTAURE (E5) ; le gain mesure 0.42 est rendu tel quel.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_2.py
    "tools/lang_speciation.py::run_seed": ["empty-cohort:raises", "guard-before-world",
                                           "etat-global-E5:mode-token-pose-puis-size-restaure",
                                           "dose:gain-0.42-transmis"],
    "tools/life_score_contamination_probe.py::run_arm": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : CLASSE de monde factice injectee -- pool COMPLET rendu avec ses stats (num_nodes, proies, crafts, mammouths),
    # meilleur 3.0 / ticks 3.0 ; un agent sans genome est IGNORE du pool et du meilleur score.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_5.py
    "tools/map_elites_compare.py::run_era_pool": ["empty-cohort:raises", "guard-before-world",
                                                  "pool:complet-avec-stats", "dose:meilleur-3.0-ticks-3.0",
                                                  "sans-genome:IGNORE-du-pool-et-du-meilleur"],
    "tools/map_elites_compare.py::run_lineage_hof": ["empty-cohort:raises", "guard-before-world",
                                                     "injection:apparie-reproductible(a==b)"],
    "tools/map_elites_compare.py::run_lineage_qd": ["empty-cohort:raises", "guard-before-world",
                                                    "injection:archive-peuplee(cov>=1)"],
    "tools/metabolic_cost_sweep.py::run_lineage": ["empty-cohort:raises", "guard-before-world"],
    "tools/metabolic_cost_sweep.py::run_era_metab": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : _world injecte (7 agents, big_kills 2) -- les 5 MEILLEURS par ere promus, tries par life_score ; mammouths
    # moyens 2.0 ; hof_stats publies (12.5, 20) ; _restore appele une fois.
    # temoin : tests/sandbox/test_mute_simulators_fake_world.py
    "tools/nas_memory.py::run_seed": ["empty-cohort:raises", "guard-before-world",
                                      "promotion:5-par-ere-tries-life_score", "dose:big_kills-2-moyenne-2.0",
                                      "hof_stats:publies-restore-appele"],
    # P2.56 (b) : _world injecte (proies = numero d'ere) -- proies moyennees sur la SECONDE moitie des eres seulement (3.5 sur
    # 1,2,3,4) ; SPECIATE restaure ; 5 promus par ere.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_2.py
    "tools/nas_rich.py::run_seed": ["empty-cohort:raises", "guard-before-world",
                                    "dose:proies-moyenne-SECONDE-moitie-3.5", "etat-global-E5:SPECIATE-restaure",
                                    "promotion:5-par-ere"],
    "tools/online_world_model_probe.py::run_online": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : CLASSE de monde factice injectee -- le crit est rythme sur l'ere GLOBALE (current_era 17 pose sur le monde),
    # crit_base 0.7 / crit_eras 9 / target_prey 5 (E8) ; sortie (0, 2, 1.0, 2).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_4.py
    "tools/persistence_test.py::run_era": ["empty-cohort:raises", "guard-before-world",
                                           "regime-E8:current_era-GLOBAL-17-crit_base-0.7-crit_eras-9",
                                           "dose:(0,2,1.0,2)"],
    "tools/planning_depth_probe.py::run_depth": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : CLASSE de monde factice injectee -- parleurs comptes 3 sur un pool de 6 (1 sur 2 parle), LANGUAGE pose (E8).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_4.py
    "tools/probe_impasse.py::run_era": ["empty-cohort:raises", "guard-before-world", "dose:parleurs-3-sur-pool-6",
                                        "regime-E8:LANGUAGE-pose"],
    # P2.56 (b) : _world/_apex_ctx injectes -- `eras` eres d'entrainement PUIS 4 eres de mesure, toutes sous la meme DEMAND ;
    # MI reelle > permutee sur un code parfait ; aucun contexte -> (0.0, 0.0) publie tel quel (porte 14 legataire).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_2.py
    "tools/reconfirm_047.py::run_seed": ["empty-cohort:raises", "guard-before-world",
                                         "eres:entrainement-puis-4-de-mesure-meme-demande", "dose:MI-reelle>permutee",
                                         "absence:(0,0)-publiee-telle-quelle"],
    "tools/referential_community_probe.py::run_community": ["empty-cohort:raises", "guard-before-world"],
    "tools/referential_game_probe.py::run_lewis": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : PUR (numpy) -- deterministe par seed ; 1 epoch : code EFFONDRE (1/3, 1/3) ; acc <= injectivite sur 4 seeds
    # (un code non injectif ne se decode pas).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_6.py
    "tools/refgame.py::run_refgame": ["empty-cohort:raises", "guard-before-world", "determinisme:par-seed",
                                      "1-epoch:code-effondre-1/3", "acc<=injectivite:4-seeds"],
    # P2.56 (b) : _world injecte -- persistence.SPECIATE pose a True pendant CHAQUE ere puis RESTAURE, meme quand le monde leve
    # (E5 etat global) ; kills 3.0 et hof (11.0, 19) transmis ; 5 promus par ere.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_2.py
    "tools/speciation.py::run_seed": ["empty-cohort:raises", "guard-before-world",
                                      "etat-global-E5:SPECIATE-pose-puis-restaure-meme-sur-exception",
                                      "dose:kills-3.0-hof-(11.0,19)", "promotion:5-par-ere"],
    "tools/substrate_ab.py::run_substrate_ab": ["empty-cohort:raises", "guard-before-world",
                                                "legacy:hit-dans-[0,1]:smoke", "torch:hit-dans-[0,1]:smoke"],
    # P2.49 / P2.56 (2026-09-14) : le banc G2 (31 records, 2e module le plus cite du lot). Les quatre
    # etaient declares GARDE-SEULE alors que `tests/sandbox/test_substrate_ab_compositional.py`
    # atteint chaque corps -- dette DECLARATIVE, une ligne chacune. Ce que les cas VALENT est ecrit
    # tel quel, sans surdeclarer :
    #   * `run_curriculum_fade_gated` porte un vrai CONTROLE POSITIF a dose connue
    #     (`gate_mode="oracle", oracle_bias=8.0` -> `binding_gap_end > 0.5`,
    #     `test_gated_oracle_opens_binding_gap`) et un refus de mode inconnu ;
    #   * `run_curriculum` : `warmup_trials=0` -> `warmup_didx_* is None` (reponse STRUCTURELLE
    #     connue, contrat P2.52) + orchestration par `compare_curriculum` ;
    #   * `run_curriculum_fade` : cles et bornes (`fade_w0=0`, penalite -> `binding_gap_end`) --
    #     du SMOKE, pas une reponse connue ;
    #   * `run_compositional` : atteint INDIRECTEMENT par `compare(seeds=(0,), trials=30)`, verdict
    #     dans un ensemble -- le plus faible des quatre. Une reponse connue lui couterait un monde.
    "tools/substrate_ab_compositional.py::run_compositional":
        ["empty-cohort:raises", "guard-before-world", "corps-atteint-via-compare:smoke"],
    "tools/substrate_ab_compositional.py::run_curriculum":
        ["empty-cohort:raises", "guard-before-world", "warmup0:phase-absente=None",
         "corps-atteint-via-compare_curriculum:smoke"],
    "tools/substrate_ab_compositional.py::run_curriculum_fade":
        ["empty-cohort:raises", "guard-before-world", "fade_w0=0:cles-et-bornes",
         "penalite:binding_gap_end-present"],
    "tools/substrate_ab_compositional.py::run_curriculum_fade_gated":
        ["empty-cohort:raises", "guard-before-world", "oracle-bias-8:gap>0.5:controle-positif",
         "gate_mode-inconnu:raises", "learned:gap-borne"],
    "tools/torch_binary_gate_heldout_probe.py::run_arm": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_binary_gate_probe.py::run_arm": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_bptt_meansends.py::run_meansends": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_gate_bptt_meansends.py::run_cell": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_gate_persist_ab.py::run_arm": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_inworld_ab.py::run_arm": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_prod_gate_meansends.py::run_prod": ["empty-cohort:raises", "guard-before-world"],
    "tools/torch_throw_gate_inworld_ab.py::run_arm": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 : tests/sandbox/test_warmstart_evolution_inworld.py -- la perte DECROIT (direction connue),
    # DAgger rend 2 tendances + un genome + un verdict bien forme.
    "tools/warmstart_evolution_inworld.py::run_bptt_imitation_warmstart":
        ["empty-cohort:raises", "guard-before-world", "loss_trend[-1]<=loss_trend[0]:direction"],
    "tools/warmstart_evolution_inworld.py::run_dagger_warmstart":
        ["empty-cohort:raises", "guard-before-world", "2-rounds:tendances-et-verdict-formes:smoke"],
    # P2.56 (b) : CLASSE de monde factice injectee -- 2 parleurs parfaits x 20 ticks : n 40, MI - base permutee > 0.7 ; l'agent
    # sans apex percu est hors des tokens ; sous 5 tokens (0.0, n) publie tel quel (porte 14) ; tetes entrainees si use_head.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_5.py
    "tools/wire_ref_head.py::run_seed": ["empty-cohort:raises", "guard-before-world",
                                         "dose:2-parleurs-parfaits-n-40-gain>0.7", "sans-apex-percu:hors-tokens",
                                         "absence:<5-tokens-(0.0,n)-publiee-telle-quelle",
                                         "tetes:entrainees-si-use_head"],
    # P2.42 (2026-09-06) : verdict statistique du harnais puissant (EDR 052), en COLLISION de nom
    # avec is_machine_idle::verdict (non-instrument) -> declaration QUALIFIEE. Forme close : t = d*sqrt(n/2).
    "src/seed_ai/eval_harness.py::verdict": ["significant", "not-significant", "and-rule:powerless-d",
                                            "zero-variance:no-verdict"],
    # P2.41 (2026-09-02) : niveau 2 de SDR-G2 -- sonde monde compositionnelle. Le verdict, jusque-la
    # INLINE dans `main`, est extrait en fonction PURE et calibre (dont le refus sur UN seul point
    # de demande : l'ancien code fabriquait un « ne paie pas » la ou aucune pente n'existe).
    "capability_payoff_verdict": ["pays", "no-payoff", "refuses-single-point"],
    # ⚠️ `run_world` est en COLLISION (3 fichiers) -> declarations QUALIFIEES obligatoires. Les DEUX
    # autres etaient invisibles jusqu'a cet elargissement : dette REELLE revelee, traitee ici.
    "tools/compositional_world_probe.py::run_world": ["empty-cohort:raises", "guard-before-world"],
    "tools/language_payoff_probe.py::run_world": ["empty-cohort:raises", "guard-before-world"],
    "tools/world_demand_marker_probe.py::run_world": ["empty-cohort:raises", "guard-before-world"],
    "run_inworld_evolution": ["empty-cohort:raises", "guard-before-world", "2-generations:trend-et-best:smoke"],
    # P2.40 (2026-09-02) : 3e vague de gardes -- les 12 sondes rendues visibles par le 6e
    # elargissement (verbes compare_/sweep_/probe_ en tete). Garde d'arguments EN TETE, testee
    # QUE (leve) et OU (refus < 0.5 s, donc avant la construction du monde).
    # P2.56 (2026-09-14) : INJECTION a dose connue dans tests/sandbox/test_orchestrator_injection.py --
    # les seuls temoins etaient des tests de SIGNATURE (le smoke reel etait « differe », c.-a-d.
    # jamais). `measure_survival`, lui, reste MUET : c'est le maillon qui simule.
    "compare_backends": ["empty-cohort:raises", "guard-before-world",
                         "injection:diff=+20:GRADIENT_GAGNE:apparie-meme-seed"],
    "compare_arms": ["empty-cohort:raises", "guard-before-world",
                     "injection:3-verdicts-en-forme-close", "noop:3-bras-identiques:NEUTRE"],
    "sweep_lr_torch": ["empty-cohort:raises", "guard-before-world",
                       "injection:une-sous-classe-par-lr:dose-lue", "reperes:meme-seed"],
    # P2.56 (b) : injection de run_arm -- bras separes par penalty : biaise (-0,5) -> NEUTRE, non biaise (0,0) -> GRADIENT_GAGNE ;
    # info publie kills et gaps ; 20 appels (4 par seed).
    "compare_debias": ["empty-cohort:raises", "guard-before-world", "biaise:NEUTRE", "non-biaise:GRADIENT_GAGNE", "info:kills+gaps"],
    # P2.56 (b) : injection de run_arm -- bras separes par shaping : sparse -> NEUTRE, dense -> GRADIENT_GAGNE ; info publie.
    "compare_density": ["empty-cohort:raises", "guard-before-world", "sparse:NEUTRE", "dense:GRADIENT_GAGNE", "info:gaps"],
    # P2.56 (b) : injection de run_arm + _collect_warm_direction -- warm_w present : cold NEUTRE, warm GRADIENT_GAGNE,
    # warm_vs_cold GRADIENT_GAGNE ; direction WARM introuvable (None) : warm devient froid ET warm_ok le DIT.
    "compare_warmstart": ["empty-cohort:raises", "guard-before-world", "cold:NEUTRE", "warm:GRADIENT_GAGNE",
                          "warm_vs_cold:GRADIENT_GAGNE", "direction-absente:warm_ok-False"],
    # P2.56 (b) : injection de run_arm -- dose-reponse par prey_count : 15 -> NEUTRE, 60 et 150 -> GRADIENT_GAGNE ; medianes
    # (diff, gap_on, kills) publiees par niveau ; 30 appels.
    "compare_rp_sweep": ["empty-cohort:raises", "guard-before-world", "niveau-bas:NEUTRE", "niveaux-hauts:GRADIENT_GAGNE",
                         "medianes-par-niveau:publiees"],
    # P2.56 (b) : evo_memory_inworld : MemoryDemandBiosphere/_cfg injectes -- rencontre CONTROLEE : l'agent qui s'approche du
    # Mammouth et reste devant le Leurre -> disc 1.0 ; mort en attaquant = engage -> disc 0.0 ; mode -> hide/ablate (E8).
    # temoin : tests/sandbox/test_mute_simulators_fake_world_6.py
    "probe_memory_discrimination": ["empty-cohort:raises", "guard-before-world",
                                    "dose:approche-Mammouth-reste-Leurre-disc-1.0", "mort-en-attaquant:engage-disc-0.0",
                                    "regime-E8:mode-vers-hide_on_approach-ablate_memory-mobilite-0"],
    # P2.56 (b) : evo_memory_inworld : MemoryDemandBiosphere/_setup_lewis injectes -- intent lu contre la position de l'apex en
    # DEBUT de tick : approche du Mammouth 1.0, fuite du Leurre 0.0, moved_frac 1.0 ; mort = engage ; era 10000, vitesse apex.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_6.py
    "probe_navigation_incontext": ["empty-cohort:raises", "guard-before-world", "dose:disc-1.0-n-1-1-moved_frac-1.0",
                                   "mort-en-attaquant:engage", "regime-E8:era-10000-benchmark-vitesse-apex"],
    # P2.56 (b) : evo_memory_inworld : monde injecte + MambaBatchModel.forward remplace (logits CONNUS) -- logit vers le Mammouth
    # 2.0, vers le Leurre 0.5 -> disc 1.5, std 0.75, n 3/3 ; forward RESTAURE apres ; sans forward : nan publie, std 0.0.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_6.py
    "probe_attack_logit": ["empty-cohort:raises", "guard-before-world", "dose:logits-connus-disc-1.5-std-0.75",
                           "forward:restaure-apres", "absence:nan-publie-std-0.0"],
    # P2.56 (b) : injection de _collect_oracle_trajectory / _probe_free_channels -- la population torch porte num_agents
    # clones du genome (W egal) a lr = 0 (jamais entrainee par la sonde), trajectoire transmise ; trajectoire vide -> None.
    "probe_genome_free_channels": ["empty-cohort:raises", "guard-before-world", "clones:lr0-W-egal",
                                   "trajectoire:transmise", "trajectoire-vide:None"],
    # P2.56 (b) : injection de _drive avec measure_convergence REEL -- constantes (off/action) convergent et sont bit-identiques,
    # marche aleatoire (H) ne converge pas : P1 {off n, action n, H 0}, P2 = n, div_action 0, P3 {1, 1, T/2}.
    "probe_substrate_attractor": ["empty-cohort:raises", "guard-before-world", "P1:converge-off-action-pas-H",
                                  "P2:bit-identique-n", "P3:diversite-1-1-T/2"],
    # P2.39 (2026-09-02) : BANC COMPOSITIONNEL -- les 9 producteurs des verdicts de SDR-G2,
    # invisibles au cliquet jusqu'au 6e elargissement (verbes compare_/sweep_/probe_ en TETE).
    # Calibres par INJECTION A DOSE CONNUE : aucun ne simule, on impose les cellules et on verifie
    # le verdict -- branches NEGATIVES incluses (une dose-reponse qui ne peut pas rendre
    # SIGNAL_INSUFFICIENT ne prouverait rien). Deblocage : la porte G2 declarait un KPI dont aucun
    # producteur n'etait calibre.
    "sweep_binding_penalty": ["forced", "suppression", "signal-insufficient"],
    "compare_gate_modes": ["binds", "collapses", "intermittent"],
    "sweep_gate_reliability": ["improved", "no-improvement"],
    "sweep_gate_warmstart": ["rescue", "no-rescue"],
    "sweep_gate_readout": ["helps", "neutral"],
    "sweep_y_saturation": ["rescues", "neutral-vs-ineffective"],
    "sweep_overtraining_stability": ["robust", "erosion"],
    "probe_collapse_predictors": ["group-separation-closed-form"],
    "compare_curriculum": ["warmup-guard", "discovery", "credit"],
    "compare_curriculum_fade": ["fade-guard", "ceiling-retention", "ceiling-binding"],
    # P2.38 (2026-09-02) : DV mecaniste |logit| d'EVO-027, extraite et REPAREE (H_prev reel,
    # echec bruyant). Le bug d'origine (nan avale) est devenu le cas de calibration.
    "tools/evo_mech_dv.py::logit_median_at_outputs": ["noop-exact", "closed-form-prediction", "loud-failure"],
    # P2.37b (2026-09-02) : `_verdict_from`, duplique VOLONTAIREMENT dans les 4 sondes mini-monde
    # (consommation de la garde de degenerescence). Nom en COLLISION -> declarations QUALIFIEES.
    # Comportement calibre sur la copie de reference (anticipation) + test ANTI-DERIVE qui gele
    # l'identite des 4 sources : la couverture s'etend aux copies tant qu'elles restent identiques.
    "tools/anticipation_demand_world_probe.py::_verdict_from": ["degenerate-priority", "demanded", "decoy"],
    "tools/cognitive_demand_world_probe.py::_verdict_from": ["identical-to-reference"],
    "tools/composition_demand_world_probe.py::_verdict_from": ["identical-to-reference"],
    "tools/memory_demand_world_probe.py::_verdict_from": ["identical-to-reference"],
    # P2.36 (2026-09-01) : les QUATRE derniers. `regime_diagnostic_verdict` prescrivait un changement
    # de protocole a partir d'un regime JAMAIS MESURE (ma calibration du matin avait gele les 4
    # branches en fournissant toujours les deux regimes -- le cas manquant n'etait couvert par
    # personne). `run_coverage_precision_diagnostic` rendait « NI_COUVERTURE_NI_PRECISION » quand
    # aucun des deux ecarts n'etait mesurable, alors que le code TESTE deja le nan.
    "run_coverage_precision_diagnostic": ["unmeasurable-is-not-neither", "empty-cohort:raises"],
    "run_grab_drift_diagnostic": ["empty-cohort:raises", "guard-before-training"],
    "run_grab_incidence_and_ablation": ["empty-cohort:raises", "guard-before-training"],
    "run_diagnostic_main": ["missing-regime:no-prescription"],
    # P2.35 (2026-09-01) : les derniers instruments de monde. Deux defauts graves --
    # `ladder_verdict(seeds=())` rendait « [1] SUBSTRAT-LIMITE », la these que EDR-200/202 ont
    # REFUTEE, sur zero donnee ; et `run_aux_off_validation` comptait un REFUS (`nan`) comme un NON,
    # donc comme une preuve du resultat cherche -- le chiffre du titre de WARM-008.
    "ladder_verdict": ["zero-seed:refused"],
    "run_aux_off_validation": ["missing-is-not-negative"],
    "run_warmstart_credit_probe": ["empty-cohort:raises", "guard-before-world",
                                  "learning-dose:published"],   # P1.6
    "measure_action_pipeline": ["empty-cohort:raises", "guard-before-world", "taux-dans-[0,1]:n>0:smoke"],
    # no-op EXACT : un genome qui ne grabbe JAMAIS rend 0.0 (reponse connue).
    "measure_inworld_grab_rate": ["empty-cohort:raises", "guard-before-world", "genome-sans-grab:0.0:noop-exact"],
    # P2.56 (b) : _world/_near_mammoth injectes -- mesure PURE (pression 0.0 a chaque ere) ; chaque agent compte avec son
    # contexte mammouth ; MI > base sur un code parfait.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_2.py
    "tools/arm_language.py::measure_mi": ["empty-cohort:raises", "guard-before-world", "mesure-pure:pression-OFF",
                                          "dose:MI>base-contexte-mammouth-par-agent"],
    # P2.56 (b) : retention_map : ORCHESTRATEUR injecte (_acquire_shared_db, run_curriculum, make_run_era_fn, summarize_retention)
    # -- transcript -> echelle REELLE + champions transmis ; etiquettes oubli/retention/retrograde a +-0.02 ; carte ecrite
    # sous cwd (chdir temporaire) ; db absente ou transcript vide -> None sans fichier ; logger arrete dans tous les cas.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_6.py
    "run_retention_map": ["empty-cohort:raises", "guard-before-world",
                          "orchestration:echelle-reelle-et-champions-transmis",
                          "etiquettes:oubli-retention-retrograde-a-0.02", "absence:None-sans-fichier",
                          "logger:arrete-meme-sans-db"],
    # P2.56 : INJECTION a DOSE CONNUE (tests/test_s2_ablation_wiring.py) -- within 100/20 = 5.0,
    # between 100/10 = 10.0, verdict PERCEPTION_DEMANDED, n = 12 : la couche d'appariement est
    # calibree en forme close. L'instrument porte 15 records ; sa declaration disait « garde seule ».
    # P2.59 (2026-09-15) : le CHEMIN REEL, via le seam de politique `batch_model_cls`
    # (tests/sandbox/test_s2_ablation_real_path.py). DECOY connu par CONSTRUCTION (politique aveugle,
    # within 1,000 exact, no-op 1,000) ; INVERSE connu par MESURE (lecteur-chasseur sous corps
    # insuffisant : 0,66 hors de la bande no-op 0,88 -- lire coute, EVO-011) ; garde E26
    # (`reference_body`) qui LEVE avant tout monde. ⚠️ DEMANDED n'a PAS de reponse connue sur le chemin
    # reel de stoneage (aucune lecture cablee net-positive : c'est le fil S2) : il reste calibre par
    # INJECTION seulement, et c'est ecrit.
    "run_ablation_map": ["empty-cohort:raises", "guard-before-world",
                         "injection:within=5.0:between=10.0:PERCEPTION_DEMANDED:n=12", "reel:smoke",
                         "reel:aveugle-sur-corps-champion:DECOY:within=1.000:noop=1.000",
                         "reel:chasseur-corps-insuffisant:INVERSE-hors-bande-noop",
                         "reference_body:PhenotypeMismatch-avant-monde", "E26:meme-corps:passe"],
    # P2.34 (2026-09-01) : gardes d'arguments EN TETE des mesures de monde -- le geste qui rend le
    # lot gratuit. Une cohorte vide ou un horizon nul produisait une MESURE (0.0 rendu comme survie
    # observee), lue en aval comme « reste au plancher » / « n'emerge pas » / « les deux se valent ».
    # Le zero d'une cohorte inexistante et celui d'une cohorte qui meurt sont le meme nombre.
    # Un test verifie non seulement QUE la garde leve, mais OU elle est posee (refus < 0.5 s).
    # P2.56 (b) : famine_harshness_probe : FamineWorld injecte -- mediane 6.0 sur 2 eres ; regime pose (cache, cycles 8/12,
    # benchmark, sweet spot metab/payoff : E8) ; la reserve injectee 5.0 est posee sur CHAQUE agent.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_3.py
    "measure_regime": ["empty-cohort:raises", "guard-before-world", "dose:mediane-6.0-sur-2-eres",
                       "regime-E8:cache-cycles-8/12-benchmark-sweet-spot", "reserve-injectee:5.0-sur-CHAQUE-agent"],
    "measure_genome": ["empty-cohort:raises", "guard-before-world"],
    "measure_in_world": ["empty-cohort:raises", "guard-before-world"],
    # P2.56 (b) : substrate_world_ab : WORLDS[cle] injecte -- UNE mediane PAR ere d'eval ([7, 7, 7] pour k_eval 3 ; l'appelant
    # agrege), substrat injecte (batch_model_cls, benchmark_mode, nuit off, era 10000) ; cohorte introuvable -> leve.
    # temoin : tests/sandbox/test_mute_simulators_fake_world_3.py
    "measure_survival": ["empty-cohort:raises", "guard-before-world", "une-mediane-PAR-ere-eval:[7,7,7]",
                         "substrat-injecte:batch_model_cls-benchmark-nuit-off-era-10000", "cohorte-introuvable:raises"],
    "measure_arm": ["empty-cohort:raises", "guard-before-world"],
    "run_credit_probe": ["empty-cohort:raises", "guard-before-world", "learning-dose:published"],   # P1.6
    # P2.56 (b) : injection de run_condition (sentinelle qui journalise) -- grille COMPLETE 2 regimes x 3 agents ; config de
    # CHAQUE regime = celle de la grille (E8) ; champion porte le genome, bras cables partent frais ; seed/K/agents/ticks transmis.
    "run_diagnostic": ["empty-cohort:raises", "guard-before-world", "grille:complete", "config-par-regime:E8",
                       "genome:champion-vs-frais", "arguments:transmis"],
    # P2.33 (2026-09-01) : QUATRIEME angle mort du cliquet -- aucun motif ne couvrait `classify_*`,
    # alors que ce sont ELLES qui PRONONCENT le verdict (l'instrument detecte qui les appelle ne
    # fait que relayer). Trois etaient ni calibrees ni comptees comme dette.
    "classify_vertical_signal": ["both-conditions", "measured-zero:concludes"],
    "classify_storage_regime": ["threshold:inclusive", "zero-buffer:epsilon"],
    "classify_record": ["world-scoped-ranks-above-learner-scoped"],
    # P2.32 (2026-09-01) : les 3 sondes g_fidelity poolaient UN RATIO PAR TICK sur tous les seeds
    # (n=900 pour 3 seeds). 300 ticks consecutifs du meme agent ne sont pas 300 replicats :
    # poole -> sign_p 7.5e-04 (G_FIDELE), par seed -> 0.250 (NEUTRE), meme effet, verdict OPPOSE.
    # La garde `sign_p < 0.05` cablee le matin meme etait donc ENTIEREMENT NEUTRALISEE ici.
    "tools/g_fidelity_probe.py::run_probe": ["unit:seed-not-tick", "diagnostic:tick-preserved",
                                             "positive:real-across-seeds"],
    "run_probe_env": ["unit:seed-not-tick"],
    "run_probe_stoneage": ["unit:seed-not-tick"],
    # P2.31 (2026-09-01) : deux orchestrateurs FAMINE, par injection. Sur les 24 instruments
    # « simulant un monde » restants, TREIZE ne simulent pas eux-memes -- ils DELEGUENT par nom de
    # module, donc sont injectables a cout nul. Cas discriminant du sweep : la MEME table donnee en
    # ordre DECROISSANT doit rendre le MINIMUM (contrat `min(required)`), pas le premier rencontre.
    "run_harshness_sweep": ["smallest-cycle", "min-not-first", "none-when-never"],
    "run_storage_probe": ["imposed-emergence", "no-op-exact", "pairing:cancels-noise"],
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
    # QUALIFIE le 2026-09-15 (P2.60) : `run_sweep` est en COLLISION depuis le portage de
    # tools/factorial_regime_sweep.py (EDR-178) -- une declaration NUE est REFUSEE par le cliquet.
    "tools/metabolic_cost_sweep.py::run_sweep": ["no-op-exact", "prediction:dose-recovered", "pairing:cancels-noise",
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
    "_verdict_evolve_nav": ["empty:refused", "single-generation:refused", "progress",
                            "stagnation:legitimate", "deux-generations:limite-acceptee"],
    # `_verdict_landing` / `_verdict_forage` : declarations NUES retirees le 2026-09-10, remplacees
    # plus haut par des declarations QUALIFIEES par chemin qui nomment les cas REELS (P2.49). En
    # garder deux ferait diverger la source de verite -- et c'est la version nue, plus pauvre, qui
    # aurait continue d'alimenter le compte de dette.
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
    "regime_diagnostic_verdict": ["floor-confound", "underpower", "real-null", "ambiguous",
                                  "missing-regime:refused"],
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
    # PRODUIRE un résultat comme n'importe quel instrument. Trois cas, réponses CONNUES de signes ou de
    # nature opposés, toutes MESURÉES dans ce dépôt : `artifact:fires` (RETAIN-COMPOSE, écart au bras
    # de référence 0.798 -> 0.022, closure 0.972 -> LÈVE) et `structural:spares` (BILINEAR/plain, 0.652 ->
    # 0.594, closure 0.089 -> ne lève PAS, alors qu'un critère de SEUIL absolu aurait flagué ce vrai
    # négatif). Correctif P2.21 (`8d0b959`) : `reference:collapses` — motif E3 DANS la garde elle-même,
    # constaté EN ACTE sur EDR-DELAYED-COORD (2026-09-01, cf. section « Ce que ça débloque » du record) :
    # AVANT le correctif, la garde tirait « artefact » alors que c'était le bras de RÉFÉRENCE (canal
    # oracle) qui s'effondrait (0.436 -> 0.194 à `lr=0.08`), pas le bras testé qui montait (0.141 -> 0.203,
    # resté dans la bande plancher 0.164-0.206). Avec `reference_floor` armé, verdict DISTINCT
    # `ReferenceCollapsedError` au lieu du refus muet dans l'ancienne branche. ⚠️ Les trois cas vivent dans
    # `tests/sandbox/test_experiment_preflight.py` (`test_optimizer_sweep_REFUSES_the_retain_compose_null`
    # / `..._SPARES_the_bilinear_structural_null` /
    # `test_optimizer_sweep_returns_INCONCLUSIVE_when_the_REFERENCE_collapses`), là où sont testées toutes
    # les assertions de pré-vol — pas dans ce fichier. Purement numériques.
    "assert_verdict_invariant_to_optimizer": ["artifact:fires", "structural:spares",
                                              "reference:collapses"],
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
    # P2.15/E2-au-SEUIL (2026-09-02) : `vitality_bar=` arme `assert_bar_is_reachable` AVANT tout
    # entrainement. Deux branches, opposees et toutes deux MESURABLES sans entrainer :
    #  * `bar-unreachable:guard-before-training` — barre inatteignable (bras facile 0.239 injecte contre
    #    0.3167) : la sonde REFUSE, et le refus est INSTANTANE. Ce n'est pas seulement QUE la garde leve,
    #    c'est OU elle est posee : refuser apres avoir paye 12 seeds x 800 episodes ne protege de rien.
    #  * `no-bar:no-op-exact` — sans barre declaree, comportement BIT-IDENTIQUE (aucune verification,
    #    aucun cout) ; et avec barre MESUREE, les 4 tableaux des bras restent bit-identiques -> mesurer
    #    le bras facile en tete ne perturbe pas la mesure (chaque `_train_and_eval_arm` re-seede).
    #    VERIFIE, pas suppose : c'est la classe E5 (etat global) qui rendrait le contraire possible.
    "run_delayed_coordination_demand_probe": ["mute-channel:chance", "mute-channel:arm-symmetry-exact",
                                              "untrained:floor", "bar-unreachable:guard-before-training",
                                              "no-bar:no-op-exact"],
    # E2 APPLIQUEE AU SEUIL (et non au bras), garde de pre-vol NEE le 2026-09-02 et calibree dans la
    # MEME passe (rituel du registre). Quatre branches, dont un COUPLE APPARIE mesure le meme jour sur
    # le MEME dispositif, le MEME bras et la MEME barre — seul le REGIME change (`flip_p`) :
    # `unreachable:fires` (flip_p=0.3, bras le plus facile 0.239 < barre 0.3167 -> LEVE) et
    # `reachable:spares` (flip_p=0, le MEME bras rend 0.3375 -> PASSE). Sans le second, une garde qui
    # refuse tout passerait le premier. `illusory-margin:fires` gele le role de la marge (0.320 contre
    # 0.3167 = 2.1 pas de quantification mais 0.18 erreur-type -> signe non etabli). `too-low-bar:
    # out-of-scope` gele la PORTEE : le defaut symetrique P2.15 (barre 0.072 SOUS le plafond structurel
    # 0.3889 du substrat plain) n'est PAS couvert, et c'est une propriete DISTINCTE — bras qui doit
    # ECHOUER vs bras qui doit REUSSIR, etabli hors dispositif vs mesure au regime configure, corrige en
    # changeant la BARRE vs en changeant le REGIME.
    # ⚠️ Les quatre cas vivent dans `tests/sandbox/test_experiment_preflight.py`
    # (`test_bar_reachability_REFUSES_the_noisy_default_regime` / `..._SPARES_the_noiseless_regime` /
    # `..._margin_refuses_an_ILLUSORY_clearance` / `..._does_NOT_cover_a_bar_that_is_TOO_LOW`), la ou
    # sont testees toutes les assertions de pre-vol. Purement numeriques.
    # ⚠️ CINQUIEME ANGLE MORT DU CLIQUET, constate en ecrivant cette ligne le 2026-09-02, CORRIGE le
    # meme jour : l'heuristique de nommage de `check_instrument_calibration.py` ne connaissait AUCUN
    # motif `assert_*`. `assert_verdict_invariant_to_optimizer` n'etait detecte que parce que son nom
    # contient « verdict », par accident ; ni `assert_n_per_arm` ni `assert_bar_is_reachable` ne
    # l'etaient. `scan_calibrated()` IGNORAIT donc la declaration ci-dessous (branche « declaration
    # perimee : ignoree ») et le compteur ne bougeait pas -- un depot pouvait livrer une garde SANS le
    # moindre cas de calibration et lire « OK, aucun nouvel instrument non calibre ». Le motif
    # `assert_\\w+` rend la famille comptable ; le contre-exemple gele est
    # `test_the_ratchet_SEES_the_assert_guard_family` (fin de fichier).
    "assert_bar_is_reachable": ["unreachable:fires", "reachable:spares", "illusory-margin:fires",
                                "too-low-bar:out-of-scope"],
    # P2.15 (2026-09-02) : l'AUTRE cote de la barre. `assert_bar_is_reachable` la borne par le HAUT
    # (franchissable par le capable) ; celle-ci la borne par le BAS (INfranchissable par l'incapable).
    # Les deux gardes partagent les MEMES chiffres geles -- barre 0.3167, plafond `plain` 0.3889 (HISTORIQUE,
    # retracte le 2026-09-08 : 34/36 MINORANT ; garde comme fixture, la garde exige la provenance) en
    # forme close -- et rendent des verdicts OPPOSES dessus : la premiere PASSE (la barre est bien
    # franchissable), la seconde REFUSE (elle ne separe rien). C'est ce couple qui rend impossible de
    # lire le `True` de l'une comme « la barre est valide ».
    # ⚠️ `chance-as-ceiling:out-of-scope` gele ce que la garde NE peut PAS faire : passer `1/K` comme
    # plafond de l'incapable la fait PASSER, et c'est precisement l'erreur P2.15 (l'incapable montait
    # a 0.3889, pas 0.1667). D'ou `provenance` OBLIGATOIRE : la garde ne verifie pas le plafond, elle
    # force a ecrire d'ou il vient pour qu'une revue puisse le verifier. Cas dans
    # `tests/sandbox/test_experiment_preflight.py`, comme toute la famille de pre-vol.
    "assert_bar_separates_the_incapable": ["p2.15:fires", "above-ceiling:spares",
                                           "undeclared-provenance:fires",
                                           "chance-as-ceiling:out-of-scope"],
    # ---- P2.15, le PLAFOND lui-meme (2026-09-07) -----------------------------------------------------
    # `assert_bar_separates_the_incapable` force a DECLARER un plafond ; encore faut-il que quelqu'un le
    # MESURE, sinon la garde deplace la devinette au lieu de la supprimer. C'est ce que fait
    # `tools/plain_substrate_ceiling.py`, et il porte lui-meme DEUX controles apparies parce qu'un
    # plafond bas a deux causes indiscernables sans eux : un optimiseur trop faible (innocente par
    # `free-table:positive`, forme LIBRE, meme cible -> 1.000) ou une forme mal paramétrée (innocentee
    # par `separable-target:specificity`, MEME forme, cible separable -> 1.000). Cas dans
    # `tests/sandbox/test_plain_substrate_ceiling.py`.
    # ⚠️ QUATRE controles, et il en a fallu quatre : les trois premiers laissaient encore passer une
    # recherche BLOQUEE. Le 4e ancre sur la seule borne PROUVEE du dossier (MILP de la sous-forme
    # additive, 27/36) : la forme complete la CONTIENT, donc doit la DOMINER. L'EGALITE dit que la
    # recherche n'a rien trouve au-dela — c'est le regime qui a produit le 0.3889 du 2026-09-02.
    # P4.1 (2026-09-08) : les trois classes d'ablation du GRAB. `NullGrabOffMamba` est le controle
    # NEGATIF apparie et son plancher est mesure BIT-IDENTIQUE (30 eres) ; `GrabForcedMamba` est la
    # manipulation INVERSE, qui REFUTE « toute perturbation de la colonne 24 aide ». Cas dans
    # tests/sandbox/test_grab_cost.py.
    "tools/s2_demand_ablation.py::GrabOffMamba": ["ablation:fires", "aliasing:garde"],
    "tools/s2_demand_ablation.py::NullGrabOffMamba": ["noop:bit-identique", "aliasing:garde"],
    "tools/s2_demand_ablation.py::GrabForcedMamba": ["inverse:refute-perturbation", "aliasing:garde"],
    "measure_plain_composition_ceiling": ["free-table:positive", "separable-target:specificity",
                                          "budget-saturation:fires", "dominates-proven-bound:fires",
                                          "modular-target:below-one", "above-chance:fires"],
    "plain_readout_ceiling": ["free-table:positive", "separable-target:specificity",
                              "unknown-target:refuses"],
    # La BORNE PROUVEE (MILP, gap 0) — d'une autre nature que le minorant de recherche : elle se calibre
    # sur des valeurs EXACTES (K=4 -> 12/16, K=6 -> 27/36) et sur un controle positif de la FORMULATION
    # elle-meme (cible separable -> 36/36), qui attrape un « grand M » trop petit — une formulation qui
    # fabriquerait le negatif avec le meme air d'exactitude.
    "additive_argmax_exact_ceiling": ["exact-K4-K6:frozen", "separable-target:positive",
                                      "infeasible-perfection:fires", "unknown-target:refuses"],
    # Le TEMOIN GELE : la valeur centrale du dossier P2.15 ne repose plus sur « une recherche l'a trouvee
    # une fois » (19 restarts sur 24 avaient ete necessaires). `in_situ=True` boucle la derivation sur le
    # VRAI substrat — si forme close et forward divergeaient, ce serait l'aliasing d'EDR-WARM-007.
    "verify_plain_ceiling_witness": ["closed-form:frozen", "in-situ:agrees"],
    # ---- LA FAMILLE DES GARDES, rendue comptable par le motif `assert_*` (2026-09-02) ----------------
    # Ces neuf declarations ne CREENT aucune couverture : elles DECLARENT une couverture qui existait
    # deja et que le cliquet ne savait pas nommer. Verifie fonction par fonction avant de les ecrire --
    # chacune a au moins un cas `fires` (reponse connue OUI, rejouant une erreur REELLE du depot) ET au
    # moins un cas `spares` (reponse connue NON), c'est-a-dire les DEUX issues : une garde qui refuse
    # tout passerait le premier seule. Aucune n'est en collision de nom -> declarations NUES licites.
    # ⚠️ Comme pour `assert_verdict_invariant_to_optimizer` et `assert_bar_is_reachable`, les cas vivent
    # dans `tests/sandbox/test_experiment_preflight.py` (« chaque test rejoue une erreur REELLE »), la ou
    # sont testees toutes les assertions de pre-vol -- pas dans ce fichier. Purement numeriques.
    # WARM-007 : 6/8 agents rendaient des tableaux intact/able BIT-IDENTIQUES, comptes comme controle.
    "assert_ablation_changes_something": ["identical-tables:fires", "changed-tables:spares"],
    # WARM-009 : bras cense montrer que grabber PAIE, dans un monde sans aucun item `Fruit`.
    "assert_positive_control": ["incapable-arm:fires", "capable-arm:spares"],
    # WARM-009 (24 genomes tous a 6.0-7.2 ticks = plancher) et WARM-008 (32/48 deja a move_acc=1.000) :
    # les DEUX bords degeneres sont couverts, pas seulement le plancher.
    "assert_not_degenerate": ["floor:fires", "ceiling:fires", "spread:spares"],
    # `pytest -k` avait deselectionne 1034 tests -> « 0 echec » lu comme un succes (E4 a l'etat pur).
    "assert_selection_nonempty": ["zero-selected:fires", "nonzero:spares"],
    # WARM-007, le bug d'aliasing FONDATEUR : `forward` renvoyait une VUE de H (motif exact du backend,
    # `H[:, 64:172]`), donc ecrire dans les logits mutait l'etat recurrent. `non-array:spares` gele la
    # PORTEE : les types non-array sont toleres par design, ce qui doit rester un choix visible.
    "assert_no_aliasing": ["real-view:fires", "copy:spares", "non-array:spares"],
    # Variante FONCTIONNELLE (l'aliasing qui ne partage pas la memoire mais deplace quand meme le
    # controle) : cas dans `tests/test_functional_aliasing.py`, sur la fuite mesuree 0.4658 -> 0.7190 a
    # alpha=1. `under-tolerance:spares` gele le fait qu'une derive de 1e-12 n'est PAS une fuite.
    "assert_no_functional_aliasing": ["control-moves:fires", "control-unchanged:spares",
                                      "under-tolerance:spares"],
    # WARM-007 : predicteur mesure sur la trajectoire ORACLE, intervention operant IN-WORLD.
    "assert_predictor_measured_in_situ": ["context-mismatch:fires", "context-match:spares"],
    # EDR-095 aux chiffres REELS : le reve force multipliait `n_lived` par 13-16 entre bras, et la
    # « chute de 55 % » comparait deux populations differentes. `paired-cohorts:spares` est le controle
    # de specificite qui compte (n egaux, et desequilibre modere 12 vs 16 sous le seuil 1.5x) -- sans
    # lui, une garde interdisant TOUTE comparaison passerait le premier cas.
    "assert_n_per_arm": ["edr095-population-shift:fires", "paired-cohorts:spares", "empty-arm:fires"],
    # ⚠️ SEULE garde de la famille vivant HORS `experiment_preflight.py`, et la raison pour laquelle la
    # portee du motif est tout `_SCAN_DIRS` et non ce seul module (EDR-WARM-008 : `aux_off_weight > 0`
    # ferme un gate DUR du craft et du feu, et sous `explore_eps > 0` le monde force grab/rub hors
    # logit). Trois voies de refus INDEPENDANTES couvertes, plus la config sure. Cas dans
    # `tests/sandbox/test_warmstart_evolution_inworld.py::test_assert_aux_off_safe_blocks_craft_and_
    # throw_and_explore`.
    "assert_aux_off_safe": ["craft-level:fires", "torch-throw-gate:fires", "explore-eps:fires",
                            "safe-config:spares"],
    # P1.6 (2026-09-14) -- l'APPRENANT in-world est un instrument : contrôle positif à DOSE PUBLIÉE.
    # Cas `test_run_learner_probe_*` et `test_learner_verdict_*` (fin de ce fichier) : oracle câblé à
    # 1.0 exact, dose comptée = mécanique du monde, bras lr=0 sans aucun poids déplacé (le plafond de
    # l'incapable mesuré DANS le dispositif), reproductibilité, variante publiée ; verdict qui LÈVE sur
    # entrée absente et refuse de conclure quand l'oracle ou la référence sont hors bornes.
    "tools/cognitive_demand_inworld.py::run_learner_probe": [
        "guard-before-world", "oracle:hit=1.0", "dose-counted", "lr0-reference:dW=0",
        "reproducible", "variant-published"],
    "learner_verdict": ["missing:raises", "harness:indeterminate", "inert", "learns:during_run", "learns:early"],
    # Harnais ADR-004 (2026-09-16). Cas dans tests/sandbox/test_harness_task.py.
    # Revue fix-round-1 (2026-09-16) : la sonde de lot vide (f) et _episodes_bit_identical (a)/(d)
    # ignoraient mask_seq -- probe malformee (mask non tronque) et deux episodes differant SEULEMENT
    # par leur mask juges bit-identiques a tort. Corrige + 2 cas T=2 ajoutes (bug trouve en revue ->
    # cas de calibration, jamais une simple note).
    "src/seed_ai/harness_task.py::assert_task_contract": [
        "toy:passes", "no-nobite:raises", "biting-control:raises", "verifier-is-oracle:raises",
        "aliased-ablation:raises", "chance-as-ceiling:raises", "short-provenance:raises",
        "non-reproducible:raises", "state-without-control:raises",
        "t2-mask-seq:content-diff-control:passes", "t2-mask-seq:mask-only-control:not-bit-identical",
        "no-change-control:raises", "target-changed:raises", "mask-seq-aliased:raises"],
    # Cas dans tests/sandbox/test_harness_learner.py.
    "src/seed_ai/harness_learner.py::assert_learner_contract": [
        "counter:passes-L0-L7", "L0:max_K", "L2:REFERENCE_LEARNS", "L3:DEAD_LEARNER", "L4:VACUOUS_PIECE",
        "L4:pieces-scoped", "L5:aliasing", "L7:single-sweep"],
    # `run_episode` (motif `run\w*`) : instrument PARTAGE par la garde et le futur runner -- il tourne
    # une politique sur un episode et rend (actions, hits) via task.score (le VERIFIEUR, jamais l'oracle,
    # E1). Revue fix-round-1 (2026-09-16) : la declaration initiale listait DEUX libelles portes par
    # une SEULE fonction de test (sur-affirmation de couverture), et la branche `ablate` (site="state",
    # appliquee au DERNIER pas seulement) n'avait AUCUN cas -- un libelle par fonction de test reelle,
    # desormais.
    "src/seed_ai/harness_learner.py::run_episode": [
        "counter:hits-via-task-score",           # test_run_episode_scores_with_the_task_verifier
        "ablate:applied-at-last-step"],           # test_run_episode_applies_ablate_only_before_the_last_step
    # Tache 4 (2026-09-16) -- `_TabularInstance.learn` (verite-terrain, table de comptes indexee par
    # la cle de l'observation cumulee). `learn` est en COLLISION (`src/agents/backend.py::learn` entre
    # autres) : declaration QUALIFIEE obligatoire. Un libelle par fonction de test REELLE de
    # `tests/sandbox/test_harness_tabular.py` (meme discipline que `run_episode` ci-dessus, apres la
    # revue fix-round-1 qui a corrige la sur-affirmation de couverture) : les 5 fonctions du fichier
    # appellent toutes `learn`, directement (`_train`) ou via `assert_learner_contract` (L2/L3/L4).
    # ⚠️ Fix round 1 (revue, 2026-09-16) : `_keys` hachait TOUTE la ligne d'observation -- sous
    # `inject_distractor_slot` (must_bite=False), le bit distracteur (jamais actif a l'entrainement)
    # faisait chuter le learner de verite-terrain a la chance, un artefact de HACHAGE lu a tort comme
    # X_DECOY/INCONCLUSIVE_SPECIFICITY. Fixe par `seen_cols` (colonnes vues a l'entrainement, cf. module) ;
    # cas ajoute : `specificity-control:decoy`.
    "tools/harness/learners/tabular.py::learn": [
        "contract:passes-both-regimes",          # test_honest_tabular_passes_the_contract_on_both_regimes
        "decoy:refused-after-learn",              # test_decoy_piece_is_refused_by_L4_not_judged_dispensable
        "table:learns-reference-chance",          # test_table_learns_composition_and_reference_stays_at_chance
        "without-table:chance-state-reset:chance",  # test_without_table_falls_to_chance_and_state_reset_kills_two_step
        "specificity-control:decoy"],             # test_specificity_control_spares_the_reader_but_permute_key_bites
    # Tache 9 (2026-09-16) -- ConnectomeLearner.learn (adaptateur UNIQUE vers make_population(backend=
    # "torch"), torch.optim.Adam sur [W]+[U,V,W_bl si presents], imitate_episode_bptt). `learn` est en
    # COLLISION (src/agents/backend.py::learn, tools/harness/learners/tabular.py::learn entre autres) :
    # declaration QUALIFIEE obligatoire. Un libelle par assertion REELLE de tests/sandbox/
    # test_harness_connectome.py qui EXERCE `learn` -- test_two_open_instances_with_different_flags_
    # are_refused n'appelle jamais learn (seul build/les drapeaux de classe sont exerces) et ne porte
    # donc aucun libelle ici, meme discipline que tabular.py::learn ci-dessus. Le test de bit-identite
    # porte DEUX libelles (deux groupes d'assertions distincts dans le meme corps -- le contraste
    # bilineaire/plain PUIS la reference lr=0 a dose appariee), meme motif que harness_verdict_lecture
    # ci-dessous.
    "tools/harness/learners/connectome.py::learn": [
        "contract:L0-L7",                  # test_connectome_passes_the_learner_contract
        "cellA:bit-identical",             # test_cell_A_seed0_is_bit_identical_to_the_published_json
        "reference:dparam=0",              # test_cell_A_seed0_is_bit_identical_to_the_published_json
        "cellB:regime-n_classes=6"],       # test_cell_B_regime_reproduces_retain_compose_at_seed0
    # Tache 5 (2026-09-16) -- harness_verdict_lecture : lecture PURE (ADR-004 §2.3-6) qui COMPOSE trois
    # instruments deja calibres (ablation_verdict pour demande/necessite, alias_guard_verdict pour l'etat,
    # learner_verdict pour l'acquisition, import paresseux) et publie l'E19 (assert_verdict_invariant_to_
    # optimizer) sur les DEUX conditions -- acquisition (le nul tient-il au pas ?) ET necessite (l'ecart
    # tient-il aux deux pas ?). Un libelle par fonction de test REELLE de tests/sandbox/test_harness_
    # verdict.py (meme discipline que run_episode / tabular.py::learn ci-dessus).
    # test_missing_arm_is_INCOMPLET_and_n11_is_INCONCLUSIVE_N porte DEUX libelles (deux assertions
    # distinctes dans le meme corps) ; test_nan_and_empty_raise_instead_of_fabricating est PARTAGEE avec
    # measure_noise_floor ci-dessous (elle leve sur les deux instruments dans le meme corps de test).
    # Fix round 1/5 (revue contrôleur, 2026-09-16) -- trois defauts REELS trouves par des sondes mesurees
    # (jamais une relecture) : CRITICAL 1 (les trois INCONCLUSIVE* de ablation_verdict devenaient une
    # affirmation NEGATIVE -> nouvelle branche DEMAND_INCONCLUSIVE, 3 cas), CRITICAL 2 (l'E19 de necessite
    # lisait du bruit sous-resolution comme un artefact de pas -> plancher de resolution, 1 cas dedie +
    # jitter independant restaure sur le cas both-at-ceiling), IMPORTANT 1 (intervention_verified cablee
    # -> lue depuis db.regime, 1 cas), IMPORTANT 2 (deux defauts de REGLE relus comme verdict scientifique
    # -> ValueError en tete, 2 cas), IMPORTANT 3 (demande publiee mais IGNOREE sur un sujet qui n'a rien
    # acquis -- pas de nouveau cas, verifie par l'existant), IMPORTANT 4 (controle positif de la garde de
    # barre + incapable_ceiling=None, 2 cas).
    # Fix round 2/5 (re-revue contrôleur, 2026-09-16) -- deux regressions du fix round 1, dont une causee
    # par le ruling du controleur lui-meme (corrigee ici) : CRITICAL re-ruling (l'E19 defend le nul du
    # CONTRASTE quel que soit le cote -- sauter NECESSARY laissait passer un artefact de pas cote
    # NECESSARY, fabriquant DEMANDED_ACQUIRED_NECESSARY depuis un ecart qui se referme, 2 cas) ; IMPORTANT
    # re-ruling (necessite+E19 doivent tourner AVANT la demande sur le chemin ACQUIS -- LR_ARTIFACT/
    # INDETERMINE_HARNAIS sont plus severes que toute branche de demande dans l'ORDRE 2.3-b, 1 cas) ;
    # MINOR (sweep a 3 pas -> ValueError au lieu d'un KeyError illisible, 1 cas).
    "src/seed_ai/harness_verdict.py::harness_verdict_lecture": [
        "branch-order",                             # test_branch_order_is_the_sealed_one
        "cellA:PIECE_PARTIAL",                       # test_cell_A_known_answer_is_PARTIAL_with_ceiling_above_bar
        "cellB:NECESSARY",                           # test_cell_B_known_answer_is_NECESSARY
        "NOT_DEMANDED",                              # test_ablated_equal_to_intact_is_NOT_DEMANDED
        "DEMAND_WITHIN_NOISE",                       # test_ratio_inside_the_measured_noise_band_is_DEMAND_WITHIN_NOISE_never_decoy
        "DEMAND_INCONCLUSIVE:grey-zone",             # test_grey_zone_ratio_is_DEMAND_INCONCLUSIVE_not_a_claim
        "DEMAND_INCONCLUSIVE:inverted",              # test_ablation_that_improves_the_arm_is_DEMAND_INCONCLUSIVE_not_a_claim
        "DEMAND_INCONCLUSIVE:degenerate-floor",      # test_intact_at_the_bayes_floor_is_DEMAND_INCONCLUSIVE_never_a_negative_claim
        "INCONCLUSIVE_SPECIFICITY",                  # test_a_biting_control_is_INCONCLUSIVE_SPECIFICITY
        "NOT_ACQUIRED:dose+saturation",              # test_learner_at_reference_is_NOT_ACQUIRED_with_dose_and_saturation
        "INDETERMINE_HARNAIS:prior-solves",          # test_reference_above_prior_max_is_INDETERMINE_HARNAIS_PRIOR_SOLVES
        "INDETERMINE_HARNAIS:oracle",                # test_oracle_below_min_is_INDETERMINE_HARNAIS
        "LR_ARTIFACT:necessity",                     # test_piece_gap_that_closes_at_the_second_lr_is_LR_ARTIFACT
        "INDETERMINE_HARNAIS:reference-collapsed",   # test_intact_collapsed_at_the_second_lr_is_INDETERMINE_HARNAIS
        "LR_ARTIFACT:acquisition",                   # test_acquisition_null_that_vanishes_at_the_second_lr_is_LR_ARTIFACT
        "LR_ARTIFACT:necessary-side",                # test_necessary_side_gap_that_closes_at_the_second_lr_is_LR_ARTIFACT
        "INDETERMINE_HARNAIS:necessary-side-reference-collapsed",  # test_necessary_side_reference_collapsed_at_the_second_lr_is_INDETERMINE_HARNAIS
        "order:necessity-e19-before-demand",         # test_necessity_and_e19_run_before_demand_on_the_acquired_path
        "rule:three-step-sweep:raises",              # test_three_step_sweep_raises_ValueError_not_KeyError
        "necessity:gap-below-resolution",            # test_gap_below_resolution_floor_is_PIECE_NOT_NECESSARY_not_LR_ARTIFACT
        "PIECE_NOT_NECESSARY:both-at-ceiling",       # test_D_equal_to_A_is_PIECE_NOT_NECESSARY_and_both_at_ceiling_is_not_degenerate
        "necessity:unverified-intervention:degenerate",  # test_missing_intervention_flag_with_D_equal_to_A_is_PIECE_INCONCLUSIVE_not_NOT_NECESSARY
        "INCOMPLET",                                 # test_missing_arm_is_INCOMPLET_and_n11_is_INCONCLUSIVE_N
        "INCONCLUSIVE_N",                            # test_missing_arm_is_INCOMPLET_and_n11_is_INCONCLUSIVE_N
        "nan:raises",                                # test_nan_and_empty_raise_instead_of_fabricating
        "boundary:<=-is-necessary",                  # test_mutating_necessity_threshold_to_strict_flips_the_boundary_case
        "rule:duplicate-lrs:raises",                 # test_duplicate_lrs_in_sweep_raises_ValueError_not_LR_ARTIFACT
        "rule:short-provenance:raises",              # test_short_provenance_raises_ValueError_not_CEILING_ABOVE_BAR
        "acquisition:bar-separates",                 # test_incapable_ceiling_below_the_bar_is_SEPARATES
        "acquisition:ceiling-unvalidated"],          # test_incapable_ceiling_none_is_CEILING_UNVALIDATED
    "src/seed_ai/harness_verdict.py::measure_noise_floor": [
        "band:min-max",                              # test_noise_floor_band_is_min_max_of_paired_ratios
        "empty:raises",                              # test_nan_and_empty_raise_instead_of_fabricating
        "per-arm:weak-arm-band"],                    # test_necessity_uses_the_band_of_the_WEAK_arm_not_only_A
    "src/seed_ai/harness_verdict.py::measure_ablated_bayes_ceiling": [
        "composition:certified-1/K",                 # test_measure_ablated_bayes_ceiling_certifies_the_declared_floor
        "wrong-declared-floor:uncertified",          # test_measure_ablated_bayes_ceiling_flags_a_wrong_declared_floor
        "not-enumerable:uncertified"],                # test_measure_ablated_bayes_ceiling_uncertified_when_state_space_not_enumerable
    # Tache 6 (2026-09-16) -- run_harness_cell : runner de CELLULE (ADR-004 S2.3). Compose les cinq
    # instruments deja calibres des taches 1-5 (assert_task_contract, assert_learner_contract, run_episode,
    # harness_verdict_lecture, measure_ablated_bayes_ceiling) + preregister/verify/provenance,
    # declare_design/assert_control_family/assert_selection_nonempty, project_cost/CostGuard. Un libelle par
    # fonction de test REELLE de tests/sandbox/test_harness_cell.py (meme discipline que harness_verdict_
    # lecture ci-dessus) ; `_run_arm`, `_accuracy`, `_accuracy_ablated`, `_tick` (prefixe `_`) ne sont pas
    # detectees par le motif `run\w*` du cliquet.
    # Revue controleur, fix round 1 (2026-09-16) : 3 nouveaux cas pour des refus DECIDABLES qui ne
    # tombaient qu'au verdict, apres jusqu'a 65 builds (ablation de regle absente de la tache, sweep a lrs
    # dupliques, n_floor > len(seeds)), 2 pour les minors (seeds dupliques, episodes < 2) -- 6 -> 11.
    # Tache 8 (consolidation semaine 1, 2026-09-16) : 3 gardes sans AUCUN contre-exemple -- bayes_floors
    # nommant une ablation absente de la tache, sweep du learner divergent de celui de la regle, unit_s
    # DONNE (E8 : unit_s_measured doit rester None) -- 11 -> 14.
    "tools/harness/cell.py::run_harness_cell": [
        "guard-before-world:task-contract",       # test_task_contract_refuses_before_any_build
        "guard-before-world:tampered",            # test_tampered_rule_refuses_before_any_build
        "guard-before-world:cost",                # test_cost_projection_refuses_before_any_build
        "guard-before-world:rule_path",           # test_rule_path_selects_a_sub_rule_and_missing_key_raises_before_any_build
        "guard-before-world:unknown-ablation",    # test_rule_naming_an_unknown_ablation_refuses_before_any_build
        "guard-before-world:unknown-bayes-floor-ablation",  # test_rule_naming_an_unknown_bayes_floor_ablation_refuses_before_any_build
        "guard-before-world:duplicate-lrs",       # test_rule_with_duplicate_lrs_refuses_before_any_build
        "guard-before-world:n_floor-above-seeds", # test_rule_with_n_floor_above_seeds_refuses_before_any_build
        "guard-before-world:sweep-mismatch",      # test_learner_sweep_mismatching_rule_refuses_before_any_build
        "guard-before-world:duplicate-seeds",     # test_duplicate_seeds_refuse_before_any_build
        "guard-before-world:episodes-min",        # test_episodes_below_two_refuses_before_any_build
        "injection:unite=seed+reference-dose-matched",  # test_unit_is_the_seed_and_reference_is_dose_matched
        "unit_s:given-not-measured",              # test_unit_s_given_is_published_and_never_measured
        "abandon:INCONCLUSIVE_N"],                # test_abandoned_seed_is_counted_and_yields_INCONCLUSIVE_N
    # P2.60 (2026-09-15) -- banc factoriel 2^4 d'EDR-177 et driver d'EDR-178, portes dans HEAD par FUSION
    # 3-voies du tag keep/edr-177-178-factorial-regime-sweep (merge-tree sans conflit, gardes de HEAD
    # conservees). Deux ORCHESTRATEURS calibres PAR INJECTION a dose connue, AUCUN monde construit
    # (tests/sandbox/test_edr177_178_calibration.py, 28 cas) : `run_arm` remplace par une sentinelle qui LEVE
    # s'il est atteint (la garde est EN TETE), puis par un `run_arm` factice dont les gaps suivent un modele
    # additif connu -- 16 cellules DISTINCTES avec la cellule tout-propre, densite mappee sur `prey_count`,
    # les 3 flags de chaque cellule transmis 2 x K fois (ON puis SHUFFLE, meme seed, penalty=0, night
    # transmis), no-op EXACT sous un bruit par seed (l'appariement l'annule : diffs == 0.0, NEUTRE, effets
    # 0.0), dose additive RETROUVEE exactement par cellule et en effets principaux, cellule-0 GRADIENT_GAGNE
    # atteignable a K=5 (E1). Defaut de seeds releve de 4 a 5 (plancher de `compute_ab_verdict`, P2.49).
    "compare_factorial": ["empty-cohort:raises", "guard-before-world", "injection:16-cellules-distinctes",
                          "injection:prey_count-mappe", "injection:flags->run_arm:apparie-meme-seed",
                          "no-op-exact:bruit-annule", "prediction:dose-recovered", "positive:reachable",
                          "seeds-default:5"],
    # Nom QUALIFIE : `run_sweep` est en COLLISION avec tools/metabolic_cost_sweep.py::run_sweep (declare
    # plus haut, qualifie dans la meme passe). Knobs de CHAQUE regime transmis intacts au banc, no-op EXACT
    # (dose 0 -> effets 0.0), dose RETROUVEE en forme close du plan 2^4 (effet principal = dose, interaction
    # = gamma/2), regimes non melanges, chemin par DEFAUT verifie : c'est `compare_factorial` du banc qui est
    # appele (sinon l'injection serait un controle qui ne peut pas echouer, E1).
    "tools/factorial_regime_sweep.py::run_sweep": [
        "guard-before-world", "passthrough:regime-knobs", "no-op-exact", "prediction:dose-recovered",
        "pairing:regimes-isolated", "default:bench-called"],
    # Verdict de la cellule tout-propre sorti du bloc __main__ vers une fonction PURE : garde de puissance
    # STRICTE a n=12 (11 -> NON-CONCLUANT), les trois etiquettes, un NUL sous le plancher dit NON-CONCLUANT
    # (pas un nul mesure), etiquette hors vocabulaire / verdict absent / n degenere -> leve.
    "_cell0_verdict": ["positive:powered", "positive:underpowered", "neutral", "hebbian",
                       "underpowered-null:non-conclusive", "unknown:raises"],
    # P2.62 (2026-09-15) -- les APPRENANTS entrent au perimetre du cliquet (11e elargissement : motif
    # `learn*` + le gradient de politique legacy, tolerants a l'INDENTATION puisque ce sont des METHODES).
    # ⚠️ Le nom du gradient legacy n'est PAS ecrit ici : la clause de fermeture de P3.4 est un
    # `grep_present` de ce nom dans CE fichier, et une simple mention la satisferait a tort.
    # Les deux apprenants du backend torch etaient DEJA calibres par P1.6, sans etre comptes. `learn` et
    # `learn_episode` sont des noms en COLLISION (4 et 2 fichiers) : declarations QUALIFIEES.
    # `src/agents/backend_torch.py::learn` (TD par tick) -- cas dans tests/sandbox/test_learning_events.py :
    #   test_counter_counts_td_and_episode_calls_and_restores_the_class (1er learn d'une vie DIFFERE, puis
    #   un update par tick), test_default_flags_are_bit_identical_to_the_bare_backend (no-op EXACT sur W),
    #   test_td_disabled_skips_every_update_and_says_why (TD coupe : aucun poids ne bouge, skips nommes),
    #   test_reward_scale_changes_the_update_and_is_published (dose-reponse : ×0,05 change l'update),
    #   test_lr_override_reaches_the_optimizer_and_is_restored, test_dW_accumulates_only_when_an_update_happens ;
    #   et in-world, tests/sandbox/test_instrument_calibration.py::test_run_learner_probe_lr0_reference_moves_no_weight
    #   (lr=0 -> dW_abs_sum == 0.0, le plafond de l'incapable mesure DANS le dispositif).
    "src/agents/backend_torch.py::learn": ["first-learn:deferred", "td:one-update-per-tick",
                                           "default:bit-identical", "td-off:dW=0", "reward-scale:dose-response",
                                           "lr-override:reaches-optimizer", "lr0:dW=0"],
    # P4.11 (2026-09-16, ADR-005 item 1) -- la trace d'eligibilite TD(lambda) de `_td_update` (chemin
    # `_td_update_trace`, drapeau CREDIT_TRACE_LAMBDA, 0.0 = chemin d'origine). Cas dans
    # tests/sandbox/test_credit_trace_lambda.py, le CONTROLE POSITIF en premier (cond. iv de la revue c9) :
    #   test_CONTROLE_POSITIF_delta_W_is_EXACTLY_the_sealed_formula_at_lambda_0_9_over_two_updates (la formule
    #   rejouee HORS du modele predit W a 1e-6 sur deux mises a jour, et predit AUTRE chose a lambda=0,5),
    #   test_lambda_zero_is_BIT_IDENTICAL_to_the_original_TD0_path (no-op EXACT, aucune trace allouee),
    #   test_trace_path_forced_at_vanishing_lambda_matches_TD0_closely_but_is_declared_NOT_bit_identical,
    #   test_trace_decays_as_gamma_lambda_to_the_k_when_gradients_vanish, test_lr_zero_leaves_W_untouched_while_
    #   the_trace_still_advances, test_refusals_are_explicit_gate_bilinear_and_non_sgd_optimizer (Adam REFUSE sauf
    #   contournement DEMANDE), test_reset_traces_is_an_option_counted_never_a_default,
    #   test_counter_adapter_sets_and_restores_the_flags_and_publishes_them.
    "src/agents/backend_torch.py::_td_update": ["positive-control:formula-predicts-W", "lambda0:bit-identical",
                                                 "lambda->0:allclose-not-bit-identical", "decay:(gamma*lambda)^k",
                                                 "lr0:dW=0-trace-advances", "refusals:explicit", "reset:option-counted",
                                                 "adapter:restored-published"],
    # `src/agents/backend_torch.py::learn_episode` (REINFORCE episodique) -- cas :
    #   tests/sandbox/test_learning_events.py::test_counter_counts_td_and_episode_calls_and_restores_the_class
    #   (un appel = un episode compte), tests/sandbox/test_instrument_calibration.py::
    #   test_run_learner_probe_counts_the_dose_the_world_delivers (un episode tous les `torch_episode_k`
    #   ticks, skips comptes) et test_run_learner_probe_lr0_reference_moves_no_weight (lr=0 -> dW == 0).
    "src/agents/backend_torch.py::learn_episode": ["episode:counted", "dose:torch_episode_k", "lr0:dW=0"],
    # Les wrappers du COMPTEUR (`tools/learning_events.py::learn` / `::learn_episode`, installes par
    # `count_learning_events`) sont ce que test_learning_events.py exerce DIRECTEMENT : bit-identiques par
    # defaut, restaures en `finally` (exception comprise), dW nul quand aucun update n'a lieu.
    "tools/learning_events.py::learn": ["default:bit-identical", "td-off:dW=0", "restored:on-exception"],
    "tools/learning_events.py::learn_episode": ["episode:counted", "restored"],
    # P3.4 (2026-09-15) : l'apprenant LEGACY, chemin actif pendant tout l'arc EVO. Cas unitaires ici
    # (signe de l'update PREDIT, lr=0 = meme code a pas nul, 1er appel differe) + cas du compteur dans
    # `test_learning_events.py` ; sa reponse connue in-world (n=12, cohorte immortelle) est dans
    # `results/legacy_learner_calibration.json` (runner `tools/legacy_learner_calibration.py`).
    # P2.72 (b), 2026-09-15 : classe de mort d'un agent ressuscite -- trois classes exhaustives + AUCUNE qui crie
    "_cause_de_mort": ["energy:<=0", "hp:<=0", "both", "alive:AUCUNE-never-fabricated"],
    "src/agents/mamba_agent.py::compute_policy_gradient": [
        "first-call:deferred", "update:sign-predicted-on-chosen-move", "lr0:same-code-null-step",
        "knobs:default-0.04-0.05", "inworld:legacy-policy-counted"],
    # RESTE GELE dans tools/instrument_calibration_baseline.json (dette legataire, PAS masquee) :
    #   `learn` (src/agents/backend.py : abstrait + LegacyPopulationModel qui delegue au legacy ;
    #   tools/evo_runs/s2_reward_ablation.py : deux seams de CAPTURE), `learn_episode_bptt`
    #   (src/agents/backend_torch.py, hors chemin in-world). Le gradient de politique legacy en est
    #   SORTI le 2026-09-15 (P3.4) : ses CINQ definitions sont declarees ci-dessous, qualifiees.
    # P3.4 : les quatre homonymes du legacy. torch_batch_model : cas de `test_torch_batch_model.py`
    # (V monte et W bouge sous recompense positive ; apprend et porte H a travers le rebuild par tick).
    # baseline_models : no-op PROUVE (W bit-identique apres appel). ablation_models : delegation
    # PROUVEE (l'interne recoit l'appel). Le wrapper du compteur : cas de `test_learning_events.py`.
    "src/agents/torch_batch_model.py::compute_policy_gradient": ["actor-critic:learns", "rebuild:carries-H"],
    "src/agents/baseline_models.py::compute_policy_gradient": ["noop:W-bit-identical"],
    "src/agents/ablation_models.py::compute_policy_gradient": ["delegates:inner-called"],
    "tools/learning_events.py::compute_policy_gradient": [
        "first:deferred-counted", "default:bit-identical", "td-off:skips", "lr0:same-code",
        "lr:critic-ratio-kept", "restored"],
    # P1.7 (2026-09-14) -- le CORPS est derive de W[0:10] (classe E26). Cas dans
    # tests/sandbox/test_phenotype_guard.py : formule du monde exacte, make_blind REFUSE, tolerance
    # explicite sur le DRAIN et inv_capacity exige EGAL, lest exact et bit-identique sur la politique.
    "assert_phenotype_matched": ["matched:passes", "make_blind:refuses", "tol-on-drain:explicit",
                                 "inv-capacity:exact"],
    # P4.4 (2026-09-14) -- lecture de la regle scellee S2-CREDIT-RETENTION, branches dans l'ORDRE impose.
    # Cas dans tests/sandbox/test_s2_credit_retention.py (reponses connues sur lignes synthetiques).
    "credit_retention_verdict": ["missing:raises", "incomplet", "harnais", "dose", "retenu_etendu", "erode",
                                 "retenu_neutre", "appris_froid", "pas_appris_froid"],
    # `run_arm` est un nom en COLLISION (3 autres fichiers) : la declaration DOIT etre qualifiee. Cas :
    # tests/sandbox/test_s2_credit_retention.py::test_run_arm_refuses_degenerate_args_before_any_world.
    "tools/evo_runs/s2_credit_retention.py::run_arm": ["guard-before-world"],
    # P4.8 (2026-09-14) -- lecture de la regle scellee S2-REWARD-ABLATION(-bis), branches dans l'ORDRE impose
    # (INCOMPLET -> HARNAIS -> DOSE -> REPLICATION -> lecture). Cas dans tests/sandbox/test_s2_reward_ablation.py
    # (reponses connues sur lignes synthetiques). Le SEAM de recompense y est calibre a reponse connue
    # (decomposition exacte Δenergie / 2·surprise / 3/√count au tick 1) et la CURIOSITE MORTE sous torch
    # (surprise jamais ecrite par backend_torch) y est gelee avec son contre-exemple (pre-vol qui LEVE).
    "reward_ablation_verdict": ["missing:raises", "incomplet", "harnais", "dose", "replication",
                                "mal_alignee:nouveaute", "mal_alignee:energy_etendu",
                                "credit_erode_seul:plein", "credit_erode_seul:attenue", "sign-and-delta",
                                "curiosity-dead:measured", "curiosity-dead:refuses-live"],
    # Cas : tests/sandbox/test_s2_reward_ablation.py::test_run_arm_refuses_degenerate_args_before_any_world.
    "tools/evo_runs/s2_reward_ablation.py::run_arm": ["guard-before-world"],
    # P4.9 (2026-09-15) -- lecture de la regle scellee S2-CREDIT-ABLATION, branches dans l'ORDRE impose
    # (INCOMPLET -> HARNAIS -> DOSE (TD et episodique) -> REPLICATION -> mecanisme PAS_OU_BRUIT /
    # SIGNAL_QUELCONQUE / SIGNE_NEGATIF + lectures secondaires voie_td / pas / ratios dW). Cas dans
    # tests/sandbox/test_s2_credit_ablation.py ; les quatre SEAMS de credit y sont calibres a reponse connue
    # (ce qui ATTEINT le learner d'origine : zeros, negation exacte, TD jamais appele, pas lu sur l'optimiseur)
    # et le pre-vol a son contre-exemple (seam qui fuit -> leve).
    "credit_ablation_verdict": ["missing:raises", "incomplet", "harnais", "dose:td", "dose:episodic", "replication",
                                "pas_ou_bruit", "signal_quelconque", "signe_negatif", "neg_etend", "voie_td",
                                "pas", "dW-ratio", "sign-and-delta", "seams:known-answer", "seams:refuses-leak"],
    # Cas : tests/sandbox/test_s2_credit_ablation.py::test_run_arm_refuses_degenerate_args_before_any_world.
    "tools/evo_runs/s2_credit_ablation.py::run_arm": ["guard-before-world"],
    # P4.16 (2026-09-22) -- lecture de la regle scellee S2-CREDIT-ABLATION-2, branches dans l'ORDRE impose
    # (INCOMPLET -> HARNAIS -> DOSE (TD et episodique par voie) -> REPLICATION -> contenu / voie / pas episodique
    # + ratios dW). Cas dans tests/sandbox/test_s2_credit_ablation_2.py ; les seams episode_enabled / reward_const
    # (credit_variant, empiles SOUS count_learning_events) y sont calibres a reponse connue avec un no-op EXACT
    # contre la trace de P4.9 et un contre-exemple (seam qui fuit -> le pre-vol LEVE).
    "credit_ablation_2_verdict": ["missing:raises", "incomplet", "harnais", "dose:td", "dose:episodic", "replication",
                                  "contenu_indifferent", "contenu_compte", "td_suffit_aussi", "episodique_seul",
                                  "pas_episodique", "sign-and-delta", "dW-ratio", "seams:noop-exact",
                                  "seams:known-answer", "seams:refuses-leak"],
    # Cas : tests/sandbox/test_s2_credit_ablation_2.py::test_run_arm_refuses_degenerate_args_before_any_world.
    "tools/evo_runs/s2_credit_ablation_2.py::run_arm": ["guard-before-world"],
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
    # ⚠️ P2.15, RECTIFIÉ le 2026-09-07 — ce test assertait `r["unlocked"]` contre `bar = 1/6 + 0.15`.
    # Il ne le peut plus, et c'est un DURCISSEMENT : le plafond du substrat plain sur cette tâche vaut
    # AU MOINS 34/36 = 0.9444 (mesuré, re-vérifié sans autograd ET in situ dans le vrai
    # `TorchPopulationModel` ; deux chercheurs indépendants trouvent 0.944 et 1.000). Il DÉPASSE donc le
    # 0.932 du bilinéaire : la séparation de CAPACITÉ n'est pas établie, et la sonde REFUSE désormais de
    # certifier `unlocked` tant qu'aucune borne SUPÉRIEURE PROUVÉE n'est déclarée.
    # Ce qui est gelé ici reste ENTIER et c'était déjà tout le contenu empirique : la séparation
    # d'APPRENABILITÉ à budget fixe, médianes ET séparation par-seed totale (0/144).
    bar = 1 / 6 + 0.15
    assert r["plain_median"] <= bar, r                                        # plain reste au plancher
    assert r["bilinear_median"] > bar, r                                      # bilinéaire décolle nettement
    assert min(r["per_seed"]["bilinear"]) > max(r["per_seed"]["plain"]), r    # séparation TOTALE par-seed
    assert r["unlocked"] is None and r["bar_status"] == "UNVALIDATED", (
        "⛔ 2026-09-08 : `bar_status` valait `CEILING_IS_MINORANT` tant que `\"auto\"` résolvait un "
        "« plafond de l'incapable » pour le plain. Il n'en résout plus AUCUN, et c'est la conséquence "
        "logique de la RÉFUTATION : le plain n'est pas incapable, sa forme close compose PARFAITEMENT "
        "(9/9 à K=3, 16/16 à K=4, vérifiés in situ). Un plafond d'incapable n'existe pas pour un bras "
        f"qui atteint le maximum. Obtenu : {r['unlocked']} / {r['bar_status']}")


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
    plafond structurel mesuré du substrat plain (0.3889 — chiffre de l'époque, rétracté le 2026-09-08 :
    le plain atteint 0.944 sans apprendre). Ce qui est gelé, c'est la BASCULE, pas un
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
    # ...et il BASCULE en ne changeant QUE le pas.
    assert hi["bilinear_median"] > bar, hi
    # Séparation TOTALE par-seed sur le bras testé : la bascule n'est pas un effet de médiane.
    assert min(hi["per_seed"]["bilinear"]) > max(lo["per_seed"]["bilinear"]), (lo, hi)
    # ⚠️ P2.15 (2026-09-07) — ce test assertait AUSSI `not lo["unlocked"]` et `hi["unlocked"]`. Il ne
    # le peut plus, et c'est un DURCISSEMENT, pas une perte : à 2 pas AUCUN plafond d'incapable n'est
    # établi (la forme close ne vaut que pour un `_step` depuis H_in=0), donc la sonde REFUSE désormais
    # de rendre `unlocked` plutôt que de le rendre contre une barre qui ne sépare rien. Le franchissement
    # de 0.3167 par `hi` (0.3797) était d'ailleurs SOUS le plafond mesuré du substrat plain : il ne
    # pouvait pas établir de capacité, ce que la docstring signalait déjà en prose. Ce qui est gelé —
    # la BASCULE, sur les médianes et le per-seed — est intact, et c'était déjà tout le contenu du test.
    assert lo["unlocked"] is None and hi["unlocked"] is None, (lo["unlocked"], hi["unlocked"])
    assert lo["bar_status"] == "UNVALIDATED" and hi["bar_status"] == "UNVALIDATED", (lo, hi)


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


def test_delayed_coordination_probe_REFUSES_an_UNREACHABLE_bar_before_training_anything():
    """⚠️ CONTRE-EXEMPLE GELE aux chiffres REELS du 2026-09-02 (defaut d'instrument n°2 du record).

    Au bruit PAR DEFAUT du module (`flip_p=0.3`), le bras le plus FACILE de la sonde — PRESENT sans
    leurre, qui ne demande AUCUNE retention — plafonne a **0.239**, sous la barre de vitalite du depot
    `1/K + 0.15 = 0.3167`. Toute cellule mesuree a ce reglage et comparee a cette barre est un
    instrument a ISSUE UNIQUE : il ne peut rendre qu'« echec ». Declarer la barre (`vitality_bar=`)
    doit donc REFUSER ce regime.

    Et ce n'est pas seulement QUE la garde leve, c'est OU elle est posee : la configuration demandee ici
    est celle du verdict complet (12 seeds x 800 episodes, plusieurs heures). Le refus doit etre
    INSTANTANE — une garde qui refuse APRES avoir paye le run ne protege de rien. Verifie par le TEMPS.

    Second volet : fournir `easiest_arm_accuracy` SANS `vitality_bar` doit lever, jamais devenir un
    no-op silencieux — l'appelant qui fournit la mesure croit avoir arme la garde."""
    import time

    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe as run
    from tools.experiment_preflight import PreflightError
    t0 = time.time()
    with pytest.raises(PreflightError, match="INATTEIGNABLE"):
        run(seeds=list(range(12)), D=2, episodes=800, n_agents=16, K=6, flip_p=0.3,
            vitality_bar=1 / 6 + 0.15, easiest_arm_accuracy=0.239)
    assert time.time() - t0 < 0.5, (
        "la garde d'atteignabilite refuse trop lentement : elle est posee APRES l'entrainement")

    # SPECIFICITE : le regime `flip_p=0` (le SEUL que le record mesure comme fonctionnel, 0.3375 et
    # reproduisant le Lewis publie a 0.0005) doit PASSER la garde -- sinon elle refuserait tout.
    with pytest.raises(PreflightError, match="SANS `vitality_bar`"):
        run(seeds=[0], easiest_arm_accuracy=0.3375)


def test_delayed_coordination_probe_is_BIT_IDENTICAL_when_the_bar_check_runs():
    """⚠️ NO-OP EXACT (la forme de test la plus forte). Deux choses a la fois :

    (1) sans `vitality_bar` (defaut), rien n'a change — c'est la condition pour que l'ajout d'une garde
        ne soit pas lui-meme une intervention sur la mesure ;
    (2) avec `vitality_bar` MESUREE (le bras facile est reellement entraine EN TETE), les quatre
        tableaux des bras restent BIT-IDENTIQUES a ceux du meme appel sans barre.

    (2) est la propriete non triviale, et elle est VERIFIEE au lieu d'etre raisonnee : `_train_and_eval_
    arm` re-seede `np.random` et `torch` a chaque entree, donc une mesure supplementaire en tete ne
    decale AUCUN tirage en aval. C'est precisement la classe E5 (etat global / RNG partage) qui rendrait
    le contraire possible -- et dans ce depot elle a deja transforme une sonde en artefact (EVO-008).
    Barre a 0.0 : la garde s'execute et passe quel que soit le resultat de l'entrainement minuscule,
    donc le test mesure l'INTERFERENCE, pas l'apprentissage."""
    from tools.delayed_coordination_demand_probe import run_delayed_coordination_demand_probe as run
    kw = dict(seeds=[0], D=1, episodes=4, n_agents=4, K=6, V=8, lr=0.05, flip_p=0.3, eval_batches=2)
    sans = run(**kw)
    avec = run(vitality_bar=0.0, **kw)
    assert sans["_bar_reachability"] is None, "sans barre declaree : aucun verdict, aucune verification"
    assert avec["_bar_reachability"]["easiest_arm_source"] == "PRESENT sans leurre, mesuré"
    for cle in ("RETAIN_intact", "RETAIN_ablated", "PRESENT_intact", "PRESENT_ablated"):
        assert sans[cle] == avec[cle], (
            f"{cle} a BOUGE : mesurer le bras facile en tete decale les tirages en aval (classe E5)")


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


# ======================================================================================================
# P2.31 (2026-09-01) — deux orchestrateurs FAMINE calibres PAR INJECTION. Aucune simulation.
#
# Sur les 24 instruments « simulant un monde » restants, TREIZE ne simulent pas eux-memes : ils
# DELEGUENT par nom de module, donc ils sont injectables a cout nul. C'est plus de la moitie.
# ======================================================================================================

def _harshness(monkeypatch, table):
    """Injecte `measure_regime` -> survie flottante. table[(cache, reserve_active)](cyc_fam) -> float."""
    import tools.famine_harshness_probe as H

    def faux(genome, cache, cyc_ab, cyc_fam, inject_reserve, **kw):
        return table[(cache, inject_reserve > 0.0)](cyc_fam)

    monkeypatch.setattr(H, "measure_regime", faux)
    return H


_EXIGE_AU_DELA_DE_40 = {(False, False): lambda c: 10.0, (True, False): lambda c: 10.0,
                        (True, True): lambda c: 20.0 if c >= 40 else 12.0}


def test_harshness_sweep_finds_the_SMALLEST_requiring_cycle(monkeypatch):
    """Le stockage devient necessaire a partir de 40 : c'est 40 qu'il faut rapporter, pas 60."""
    H = _harshness(monkeypatch, _EXIGE_AU_DELA_DE_40)
    r = H.run_harshness_sweep(None, [20, 40, 60])
    assert r["smallest_required_cycle_famine"] == 40


def test_harshness_sweep_returns_the_MINIMUM_not_the_first_encountered(monkeypatch):
    """⚠️ Le cas discriminant : la MEME table, mais la liste donnee en ordre DECROISSANT. Un code qui
    rendrait « le premier rencontre » repondrait 60. Le contrat est `min(required)`, et rien ne le
    testait -- or l'appelant choisit l'ordre de sa liste."""
    H = _harshness(monkeypatch, _EXIGE_AU_DELA_DE_40)
    assert H.run_harshness_sweep(None, [60, 40, 20])["smallest_required_cycle_famine"] == 40


def test_harshness_sweep_reports_NONE_when_no_regime_requires_storage(monkeypatch):
    """⚠️ SPECIFICITE : « aucun » doit etre None, jamais 0 ni le premier cycle. Un 0 se lirait comme
    « le stockage est requis des le cycle 0 », l'exact contraire du resultat."""
    H = _harshness(monkeypatch, {(False, False): lambda c: 10.0, (True, False): lambda c: 10.0,
                                 (True, True): lambda c: 11.0})
    assert H.run_harshness_sweep(None, [20, 40, 60])["smallest_required_cycle_famine"] is None


def test_classify_storage_regime_pivots_exactly_on_its_declared_ratio():
    """Fonction PURE que l'heuristique de nommage ne detecte MEME PAS (ni verdict/measure/run dans son
    nom) alors qu'elle produit « STORAGE_REQUIRED ». Frontiere gelee : le seuil est INCLUSIF."""
    from tools.famine_harshness_probe import classify_storage_regime
    assert classify_storage_regime(10.0, 15.0, 1.5)["verdict"] == "STORAGE_REQUIRED"
    assert classify_storage_regime(10.0, 14.9, 1.5)["verdict"] == "STORAGE_REDUNDANT"
    assert classify_storage_regime(0.0, 50.0, 1.5)["verdict"] == "STORAGE_REQUIRED", (
        "rien ne survit SANS reserve, 50 ticks AVEC : le stockage est bien requis (et pas de "
        "division par zero -- epsilon)")
    # ⚠️ CAS QUE MA PREMIERE PASSE AVAIT MANQUE (ajoute le 2026-09-01). J'avais gele la FRONTIERE et la
    # division par zero, pas la COMPARABILITE des deux bras : avec buffer = oracle = 0.0, l'instrument
    # rendait « STORAGE_REDUNDANT » -- « le buffer naturel suffit » -- alors que RIEN ne survit, ni avec
    # reserve ni sans. Les deux tests du depot ne couvraient que buffer=0 avec un oracle VIVANT.
    assert classify_storage_regime(0.0, 0.0, 1.5)["verdict"] == "INDETERMINE_AUCUN_SURVIVANT", (
        "deux bras morts ne prouvent pas que le buffer suffit")


def _storage(monkeypatch, table, bruit=None):
    """Injecte `measure_genome`, `evolve_in_famine` et le champion. table[(evolue, cache)] -> survie."""
    import tools.famine_storage_probe as S
    monkeypatch.setattr(S, "load_champion_genome", lambda: "CHAMP")
    monkeypatch.setattr(S, "evolve_in_famine", lambda seed, *a, **k: f"EVOLVED_{seed}")

    def faux(genome, seed, cache=True, *a, **k):
        evolue = str(genome).startswith("EVOLVED")
        return {"median_survival": table[(evolue, cache)] + (bruit or {}).get(seed, 0.0),
                "fruits_at_transition": 3}

    monkeypatch.setattr(S, "measure_genome", faux)
    return S


_EMERGE = {(True, True): 40.0, (True, False): 10.0, (False, True): 20.0, (False, False): 19.0}


def test_storage_probe_detects_an_imposed_emergence(monkeypatch):
    """Dose imposee : +30 de survie chez l'evolue quand le cache est actif, +1 chez le stoneage."""
    S = _storage(monkeypatch, _EMERGE)
    r = S.run_storage_probe(list(range(12)))
    assert r["median_delta_famine"] == 30.0 and r["median_delta_stoneage"] == 1.0
    assert r["verdict"] == "EMERGE"


def test_storage_probe_invents_NOTHING_when_ablation_changes_nothing(monkeypatch):
    """⚠️ NO-OP EXACT : ablater le cache ne change rien nulle part -> deltas nuls, aucune emergence.
    C'est le negatif LEGITIME (donnees reelles sans effet), distinct du refus sur donnees absentes."""
    S = _storage(monkeypatch, {(True, True): 20.0, (True, False): 20.0,
                               (False, True): 20.0, (False, False): 20.0})
    r = S.run_storage_probe(list(range(12)))
    assert r["median_delta_famine"] == 0.0 and r["verdict"] == "N_EMERGE_PAS"


def test_storage_probe_PAIRING_cancels_between_seed_variance(monkeypatch):
    """⚠️ Le delta est APPARIE (on/off sur le MEME seed). Un bruit de 500 par seed doit s'annuler
    exactement. S'il ne s'annulait pas, l'effet impose de +30 serait noye."""
    S = _storage(monkeypatch, _EMERGE, bruit={s: 500.0 * (s % 4) for s in range(12)})
    r = S.run_storage_probe(list(range(12)))
    assert r["median_delta_famine"] == 30.0 and r["verdict"] == "EMERGE"


# ======================================================================================================
# P2.32 (2026-09-01) — PSEUDO-REPLICATION dans les 3 sondes `g_fidelity`, et la garde qu'elle annulait.
#
# `run_probe` / `run_probe_env` / `run_probe_stoneage` poolaient UN RATIO PAR TICK sur tous les seeds
# (`all_ratios.extend`) puis passaient le pool a `fidelity_verdict`. Avec measure=300 et 3 seeds :
# n = 900. Or 300 ticks consecutifs du MEME agent, sur la MEME trajectoire, avec le MEME g, ne sont pas
# 300 replicats independants -- l'unite de replication de ce depot est le SEED (CLAUDE.md, question 3).
#
# MESURE, sur des donnees ou g gagne 55 % des ticks :
#     poole    n=900  mediane 0.900  sign_p 7.5e-04  -> G_FIDELE
#     par seed n=3    mediane 0.900  sign_p 0.250    -> NEUTRE
# Meme effet, meme mediane, VERDICT OPPOSE.
#
# ⚠️ CONSEQUENCE SUR MA PROPRE CORRECTION DU MATIN. J'avais cable `sign_p < 0.05` dans `fidelity_verdict`
# (P2.20) pour empecher un positif sous-puissant. Sur un pool de 900 ticks correles, ce test passe
# TOUJOURS : la garde avait l'air d'une garde et ne pouvait jamais mordre. Un correctif juste, pose sur
# une unite d'analyse fausse, ne corrige rien.
#
# ⚠️ Et il y a une borne dure a connaitre : a 3 seeds, le test des signes ne peut pas descendre sous
# 0.25. Un dispositif a 3 seeds ne PEUT PAS etre significatif par ce test -- ce qui est une information
# de design, pas un defaut de l'instrument.
# ======================================================================================================

def test_g_fidelity_takes_its_verdict_on_SEEDS_not_on_ticks(monkeypatch):
    """⚠️ LE contre-exemple. 3 seeds x 300 ticks, g meilleur sur 55 % des ticks. Le verdict doit se
    prendre sur n=3, donc NEUTRE -- pas sur n=900, qui rendrait G_FIDELE."""
    import random
    import tools.g_fidelity_probe as G
    random.seed(0)

    def faux(seed, warmup, measure):
        return ([0.9 if random.random() < 0.55 else 1.1 for _ in range(300)],
                {a: [] for a in range(G.MambaBatchModel.PLAN_A)})

    monkeypatch.setattr(G, "collect_ratios", faux)
    r = G.run_probe([0, 1, 2])
    assert r["n"] == 3, f"l'unite de replication doit etre le SEED, or n={r['n']}"
    assert r["verdict"] == "NEUTRE", f"3 seeds ne peuvent pas etre significatifs, or : {r['verdict']}"
    assert r["sign_p"] >= 0.25


def test_g_fidelity_still_reports_the_TICK_diagnostic(monkeypatch):
    """⚠️ SPECIFICITE : corriger l'unite d'analyse ne doit pas SUPPRIMER l'information par tick, qui
    reste un diagnostic utile. La perdre rendrait les anciens rapports incomparables."""
    import random
    import tools.g_fidelity_probe as G
    random.seed(0)
    monkeypatch.setattr(G, "collect_ratios", lambda s, w, m: (
        [0.9 if random.random() < 0.55 else 1.1 for _ in range(300)],
        {a: [] for a in range(G.MambaBatchModel.PLAN_A)}))
    r = G.run_probe([0, 1, 2])
    assert r["n_ticks_pooles"] == 900 and abs(r["median_ratio_ticks"] - 0.9) < 1e-9
    assert len(r["ratios_par_seed"]) == 3


def test_g_fidelity_still_finds_a_REAL_effect_across_seeds(monkeypatch):
    """⚠️ L'autre bord : un effet PRESENT DANS CHAQUE SEED doit rester detectable. Sans ce cas, on aurait
    remplace un instrument trop permissif par un instrument aveugle."""
    import tools.g_fidelity_probe as G
    monkeypatch.setattr(G, "collect_ratios", lambda s, w, m: (
        [0.3] * 300, {a: [] for a in range(G.MambaBatchModel.PLAN_A)}))
    r = G.run_probe(list(range(12)))
    assert r["n"] == 12 and r["verdict"] == "G_FIDELE" and r["sign_p"] < 0.05


def test_the_sign_test_has_a_HARD_FLOOR_at_three_seeds():
    """Information de DESIGN, pas defaut : a n=3 le test des signes ne peut pas descendre sous 0.25.
    Le geler evite qu'on relance un jour un dispositif a 3 seeds en esperant un p significatif."""
    from tools.g_fidelity_probe import _sign_p
    assert _sign_p(3, 3) >= 0.25
    assert _sign_p(5, 5) < 0.25, "a 5 seeds unanimes, le test peut enfin conclure"


# ======================================================================================================
# P2.33 (2026-09-01) — le QUATRIEME angle mort du cliquet : les fonctions `classify_*`.
#
# Aucun motif de `_INSTRUMENT_PATTERNS` ne couvrait `classify_*`. Or ce sont ELLES qui PRONONCENT le
# verdict : `classify_storage_regime` rend « STORAGE_REQUIRED », et l'instrument detecte qui l'appelle
# ne fait que le relayer. Trois fonctions etaient donc ni calibrees, ni meme COMPTEES comme dette.
#
# L'heuristique est desormais connue faillible sur QUATRE axes : ce qu'elle cherche (motif, 2026-07-21),
# OU elle cherche (perimetre, 2026-07-21), comment elle IDENTIFIE ce qu'elle trouve (collisions,
# 2026-09-01), et sous quels VERBES (classify_, 2026-09-01). Chaque elargissement a revele de la dette
# REELLE -- c'est la raison de continuer a l'elargir.
# ======================================================================================================

def test_classify_vertical_signal_needs_BOTH_conditions():
    """Z_UTILISE exige une amplitude verticale ET un usage des actions Up/Down au-dessus du hasard.
    Une seule des deux ne suffit pas : monter sans jamais choisir Up, c'est etre pousse, pas voler."""
    from tools.vertical_world_probe import classify_vertical_signal
    assert classify_vertical_signal(2.0, 0.40)["verdict"] == "Z_UTILISE"
    assert classify_vertical_signal(2.0, 0.10)["verdict"] == "Z_INERTE", "amplitude seule ne suffit pas"
    assert classify_vertical_signal(0.1, 0.40)["verdict"] == "Z_INERTE", "actions seules ne suffisent pas"


def test_classify_vertical_signal_treats_a_MEASURED_zero_as_a_result():
    """⚠️ Meme distinction que pour `agri_verdict` : ses entrees sont des scalaires MESURES. Un
    `z_range` de 0.0 signifie « l'agent n'a jamais change de couche » -- une observation, pas une
    absence. Z_INERTE est donc CORRECT ici, et lui ajouter une garde « donnees vides » serait une
    erreur. Le defaut de vide est chez son APPELANT (`measure_arm`, cohorte vide), pas chez lui."""
    from tools.vertical_world_probe import classify_vertical_signal
    assert classify_vertical_signal(0.0, 0.0)["verdict"] == "Z_INERTE"


def test_classify_storage_regime_is_reachable_by_the_ratchet_now():
    """Cette fonction etait DEJA calibree (P2.31) mais INVISIBLE au cliquet faute de motif : elle
    n'apparaissait ni comme calibree ni comme dette. Le motif `classify_*` la rend comptable."""
    import tools.check_instrument_calibration as C
    assert "classify_storage_regime" in C.scan_instruments()


def test_classify_record_ranks_a_world_scoped_null_above_a_learner_scoped_one():
    """L'instrument de RETRO-AUDIT : il classe les records graves par risque de conclusion fabriquee.
    Propriete qui porte tout son tri -- un nul qui conclut sur LE MONDE est plus risque qu'un nul
    portant sur un apprenant, parce qu'il generalise plus loin que sa mesure."""
    import os
    import tempfile

    from tools.retro_audit_records import classify_record

    def _classe(corps):
        """`classify_record` prend un CHEMIN, pas du texte : on écrit un record jetable."""
        chemin = os.path.join(tempfile.mkdtemp(), "r.md")
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write("---\nid: EDR-999\ntype: EDR\nverdict: NEUTRE\n---\n\n" + corps)
        return classify_record(chemin)

    monde = _classe("Le MONDE n'exige pas cette capacite : aucun effet mesure.")
    appr = _classe("Ce learner n'apprend pas la tache : aucun effet mesure.")
    assert monde is not None and appr is not None
    assert monde["risque"] >= appr["risque"], (
        f"un nul portant sur LE MONDE generalise plus loin que sa mesure qu'un nul portant sur un "
        f"apprenant : {monde['risque']} vs {appr['risque']}")


# ======================================================================================================
# P2.34 (2026-09-01) — GARDES D'ARGUMENTS en tete des mesures de monde. Sept instruments, zero seconde.
#
# LE GESTE QUI REND LE LOT GRATUIT : poser la garde EN TETE de fonction, AVANT la construction du monde.
# Une vingtaine de cas « donnees absentes » passent ainsi de « quelques secondes chacun » a ZERO
# simulation -- la fonction repond avant que le monde n'existe.
#
# CE QUE LA GARDE EMPECHE. Sans elle, une cohorte vide ou un horizon nul produisait une MESURE : 0.0
# rendu comme survie observee, puis lu en aval par un verdict comme « reste au plancher », « le
# stockage n'emerge pas », « les deux substrats se valent ». Le zero d'une cohorte inexistante et le
# zero d'une cohorte qui meurt sont le meme nombre -- et seule la garde les separe.
#
# ⚠️ ELLES LEVENT, elles ne rendent pas de sentinelle. Un `num_agents=0` n'est pas un resultat
# scientifique, c'est une erreur d'appel : rendre 0.0 la ferait entrer dans une moyenne comme une
# mesure. C'est l'idiome `assert_selection_nonempty` du depot.
# ======================================================================================================

_MESURES_GARDEES = [
    ("tools.famine_harshness_probe", "measure_regime",
     dict(genome=None, cache=True, cyc_ab=30, cyc_fam=20, n_agents=0)),
    ("tools.famine_storage_probe", "measure_genome", dict(genome=None, seed=0, num_agents=0)),
    ("tools.cross_world_transfer", "measure_in_world",
     dict(world_key="x", genome=None, seed=0, num_agents=0)),
    ("tools.substrate_world_ab", "measure_survival",
     dict(world_key="x", seed=0, backend_cls=None, num_agents=0)),
    ("tools.vertical_world_probe", "measure_arm", dict(genome=None, use_3d=False, seed=0, n_agents=0)),
    ("tools.cognitive_demand_inworld", "run_credit_probe", dict(num_agents=0)),
    ("tools.s2_regime_diagnostic", "run_diagnostic", dict(num_agents=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES)
def test_world_measures_REFUSE_an_empty_cohort_before_building_anything(mod, nom, kw):
    """⚠️ LE contre-exemple, x7. Zero agent ne peut pas produire une survie mesuree."""
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES)
def test_the_guard_is_placed_BEFORE_any_world_is_built(mod, nom, kw):
    """⚠️ Ce n'est pas seulement QUE la garde leve, c'est OU elle est posee. Placee apres la
    construction du monde, elle couterait une simulation par cas et ce lot serait impayable. On le
    verifie par le TEMPS : un refus doit etre instantane (< 0.5 s), pas « quelques secondes »."""
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, (
        f"{nom} met trop de temps a refuser : la garde est posee APRES la construction du monde")


# ======================================================================================================
# P2.35 (2026-09-01) — les derniers instruments de monde. Deux defauts graves, six gardes d'arguments.
#
# DEFAUT 1 -- `ladder_verdict(seeds=())`. `binds`/`survs` restent vides, `np.median([])` rend nan,
# `_rung_composes(nan, nan)` est False, `not l2` est vrai -> l'instrument rendait « [1] SUBSTRAT-LIMITE ».
# C'est la these « le verrou est le substrat », PRECISEMENT celle que EDR-200/202 ont REFUTEE : une
# these refutee ressuscitee sur ZERO donnee, avec pour seul signe un RuntimeWarning. Son DERIVE
# `_decomp_verdict` avait recu la meme garde le meme jour (P2.21) ; le parent ne l'avait pas.
#
# DEFAUT 2 -- `run_aux_off_validation` : UN REFUS N'EST PAS UN NON. `measure_inworld_grab_rate` rend
# `nan` quand il n'y a eu AUCUNE occasion de grab -- il refuse correctement d'inventer un taux. Mais
# `nan > 0.5` vaut False, donc le refus etait compte comme « gi pas au-dessus du seuil », c'est-a-dire
# comme une PREUVE que le grab est annule -- le resultat meme que ce banc cherche, et le chiffre du
# titre de WARM-008. L'instrument disait « je ne sais pas », son appelant entendait « non ».
# ======================================================================================================

def test_ladder_verdict_REFUSES_to_resurrect_a_refuted_thesis_on_zero_data():
    """⚠️ Zero seed ne peut pas prouver que le verrou est le substrat."""
    import warnings
    from tools.craft_or_starve_edr import ladder_verdict
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert ladder_verdict(seeds=())["verdict"] == "INDETERMINE_AUCUNE_MESURE"


def test_a_missing_measurement_is_not_counted_as_a_negative():
    """⚠️ La propriete qui compte, isolee : `nan > 0.5` vaut False en Python. Compter les refus avec les
    negatifs transforme « je ne sais pas » en « non » -- et ici le « non » EST la conclusion cherchee.
    Ce test gele l'arithmetique, independamment du banc qui la porte."""
    import numpy as np
    gis = [0.9, float("nan"), 0.2, float("nan")]
    naif = sum(1 for g in gis if g > 0.5)
    finis = [g for g in gis if np.isfinite(g)]
    assert naif == 1 and len(gis) == 4, "le comptage naif dit 1/4"
    assert sum(1 for g in finis if g > 0.5) == 1 and len(finis) == 2, "le comptage honnete dit 1/2"
    assert len(gis) - len(finis) == 2, "et il DECLARE les 2 mesures manquantes"


_MESURES_GARDEES_2 = [
    ("tools.cognitive_demand_inworld", "run_warmstart_credit_probe", dict(num_agents=0)),
    ("tools.warmstart_evolution_inworld", "measure_action_pipeline", dict(genome=None, num_agents=0)),
    ("tools.warmstart_evolution_inworld", "measure_inworld_grab_rate", dict(genome=None, num_agents=0)),
    ("tools.arm_language", "measure_mi", dict(config=None, db=None, eras=0)),
    ("tools.retention_map", "run_retention_map", dict(ladder=None, num_agents=0)),
    ("tools.s2_demand_ablation", "run_ablation_map", dict(num_agents=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_2)
def test_remaining_world_measures_REFUSE_degenerate_arguments(mod, nom, kw):
    """Seconde vague de gardes, meme principe et meme justification que P2.34."""
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_2)
def test_remaining_guards_are_also_placed_BEFORE_the_world(mod, nom, kw):
    """⚠️ Meme verification de PLACEMENT : un refus instantane prouve que la garde precede la
    construction du monde. `run_retention_map` acquiert une base KuzuDB -- une garde posee apres
    couterait une ressource exclusive pour rien."""
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


# ======================================================================================================
# P2.36 (2026-09-01) — les QUATRE derniers. Deux defauts de la meme famille, vus une troisieme fois.
#
# `regime_diagnostic_verdict` : un regime ABSENT rendait 0.0 via `md.get("champ_median", 0.0)`,
# exactement comme un regime ou tout meurt -> CONFOND_PLANCHER + `regime_recommande="sweet"`,
# c'est-a-dire une PRESCRIPTION DE PROTOCOLE derivee d'une mesure inexistante.
# ⚠️ Ma calibration du matin (P2.22) avait gele les QUATRE branches -- en fournissant toujours les deux
# regimes. Le cas « entree manquante » n'etait couvert par personne, y compris par moi.
#
# `run_coverage_precision_diagnostic` : si les bins tardifs sont tous a n=0, les deux ecarts sont nan et
# la branche `else` rendait « NI_COUVERTURE_NI_PRECISION » -- une affirmation de fond sans qu'aucun des
# deux effets ait pu etre observe. Le code teste pourtant deja `cov_gap == cov_gap` : il CONNAIT le nan,
# et l'avale quand meme. Troisieme occurrence du meme motif aujourd'hui (apres `degenerate` non lu par
# `ablation_verdict`, et `nan > 0.5` compte comme un NON).
# ======================================================================================================

def _rd_regime(mediane):
    return {"champion": {"survival": [mediane] * 40, "era_survival": [mediane] * 12,
                         "censored_frac": 0.0},
            "reflexe": {"survival": [10] * 40, "era_survival": [10] * 12, "censored_frac": 0.0}}


def test_regime_diagnostic_REFUSES_to_prescribe_from_a_regime_never_measured():
    """⚠️ Le regime « defaut » absent ne peut pas fonder « passe au sweet »."""
    from tools.s2_regime_diagnostic import regime_diagnostic_verdict
    r = regime_diagnostic_verdict({"sweet": _rd_regime(300)}, max_ticks=400)
    assert r["verdict"] == "INDETERMINE_REGIME_MANQUANT"
    assert r["regime_recommande"] is None, "aucune prescription sans les deux regimes"
    assert r["regimes_manquants"] == ["defaut"]


def test_regime_diagnostic_still_finds_a_REAL_floor_confound():
    """⚠️ SPECIFICITE : avec les DEUX regimes mesures, le confond de plancher doit toujours sortir --
    c'est le verdict que cet instrument existe pour produire."""
    from tools.s2_regime_diagnostic import regime_diagnostic_verdict
    cells = {"defaut": {"champion": {"survival": [5] * 40, "era_survival": [5] * 12,
                                     "censored_frac": 0.0},
                        "reflexe": {"survival": [5] * 40, "era_survival": [5] * 12,
                                    "censored_frac": 0.0}},
             "sweet": _rd_regime(300)}
    assert regime_diagnostic_verdict(cells, max_ticks=400)["verdict"] == "CONFOND_PLANCHER"


def test_UNMEASURABLE_is_not_the_same_as_NEITHER():
    """⚠️ La propriete isolee, independamment du banc : deux ecarts non mesurables ne prouvent pas que
    ni l'un ni l'autre n'agit. Le code connaissait le nan (il le teste) et l'avalait dans le negatif."""
    nan = float("nan")
    cov_gap, prec_gap = nan, nan
    has_cov = cov_gap == cov_gap and cov_gap >= 0.10
    has_prec = prec_gap == prec_gap and prec_gap >= 0.10
    assert not has_cov and not has_prec, "les deux drapeaux sont False..."
    assert cov_gap != cov_gap and prec_gap != prec_gap, (
        "...mais pour cause de NON-MESURE, pas d'absence d'effet : c'est cette distinction que la "
        "branche `else` effacait")


_WARM_DERNIERS = [
    ("run_coverage_precision_diagnostic", dict(num_agents=0)),
    ("run_grab_drift_diagnostic", dict(num_agents=0)),
    ("run_grab_incidence_and_ablation", dict(num_agents=0)),
]


@pytest.mark.parametrize("nom,kw", _WARM_DERNIERS)
def test_last_warm_diagnostics_REFUSE_degenerate_arguments(nom, kw):
    """Ces trois lancent un entrainement torch de plusieurs milliers d'epoques : une garde posee trop
    bas couterait une passe complete avant de refuser."""
    import time
    import tools.warmstart_evolution_inworld as W
    f = getattr(W, nom)
    t0 = time.time()
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement"


# ======================================================================================================
# P2.37 (2026-09-02) — PLANCHERS des 4 sondes mini-monde : mesures calibrees sur FORME CLOSE.
#
# Les 6 appels a `ablation_verdict` de ces sondes ne declaraient AUCUNE borne (dette E14 gelee la
# veille). Les planchers sont desormais MESURES (pas inventes) : regime partage A (anticipation /
# cognitive / memory : E0=15, metab=1.0, INSUFF=0.5) -> PLANCHER_AVEUGLE = 30.0 ; composition (regime
# propre, chaine 2 etapes) -> PLANCHER_SANS_PLAN = 54.0, par enumeration EXACTE des 25 politiques
# stage-conditionnees. Une politique ALEATOIRE aurait rendu ~30 et SOUS-GARDE le nul de 24 ticks.
#
# ⚠️ LA CALIBRATION DU MESUREUR EST UNE FORME CLOSE : la politique corps (a=0) en INSUFF draine
# exactement metab - body_gain = 0.5/tick depuis E0=15 -> mort au tick 30, DETERMINISTE. Si le mesureur
# ne rend pas 30.0 exactement, c'est LUI qui est faux — l'etalon s'est deja trompe avant l'instrument
# dans ce depot (CLAUDE.md), d'ou la preference pour la prediction sur la valeur absolue.
#
# ⚠️ ET LE CABLAGE EST LA MOITIE DU CORRECTIF : la garde ne modifie que v["verdict"]/v["degenerate"] —
# les sondes lisaient les booleens bruts collapse/decoy, donc floor= aurait ete INERTE. Chaque sonde
# passe par `_verdict_from`, teste ici.
# ======================================================================================================

def test_the_body_policy_floor_is_a_CLOSED_FORM():
    """La forme close qui calibre le mesureur : corps a=0, INSUFF -> mort au tick 30 EXACTEMENT."""
    import numpy as np
    from tools.anticipation_demand_world_probe import survive as s_ant
    from tools.cognitive_demand_world_probe import survive as s_cog
    from tools.memory_demand_world_probe import survive as s_mem
    K = 5
    b0 = np.zeros(K); b0[0] = 1.0
    rng = np.random.RandomState(0)
    assert s_ant(np.zeros((K, K)), b0, "ablated", 0.5, 2.0, "energy", 1, K, rng, 300) == 30
    assert s_cog(np.zeros((K, K)), b0, "true", 0.5, 2.0, "energy", K, rng, 300) == 30
    assert s_mem(np.zeros((K, 2 * K)), b0, "ablated", 0.5, 2.0, "energy", "delayed", K, rng, 300) == 30


def test_the_composition_floor_beats_the_blind_floor():
    """⚠️ Le choix de la POLITIQUE de reference n'est pas un detail : l'oracle prive du plan (mais
    gardant l'obs de stage) atteint ~54 par guess-and-craft, la ou l'aveugle plafonne a 30. Prendre
    l'aveugle aurait SOUS-GARDE le nul de 24 ticks. Gele : la politique (a0=4, a1=1) doit battre 30."""
    import numpy as np
    from tools.composition_demand_world_probe import survive as s_cmp
    K = 5
    W = np.zeros((K, 2 * K)); W[4, 0] = 1.0; W[1, 1] = 1.0
    vies = [s_cmp(W, np.zeros(K), "ablated", 0.5, 3.0, "energy", 2, K,
                  np.random.RandomState(100 + i), 300) for i in range(24)]
    import statistics
    assert statistics.median(vies) > 40, (
        f"guess-and-craft doit battre nettement le corps (30), or mediane = {statistics.median(vies)}")


def test_verdict_from_READS_the_guard_instead_of_raw_booleans():
    """⚠️ La moitie du correctif. Un dict avec degenerate=True ET collapse=True doit rendre
    INDETERMINE — l'ancien code lisait collapse et aurait rendu SENSITIVE sur un regime illisible."""
    from tools.anticipation_demand_world_probe import _verdict_from
    degenere = {"degenerate": True, "verdict": "INCONCLUSIVE_DEGENERATE",
                "collapse": True, "decoy": False, "n": 24, "ratio": 2.3}
    assert _verdict_from(degenere, "SURVIVAL_ANTICIPATION_SENSITIVE") == "INDETERMINE_DEGENERATE"
    positif = {"degenerate": False, "verdict": "X_DEMANDED", "n": 24, "ratio": 5.0}
    assert _verdict_from(positif, "SURVIVAL_ANTICIPATION_SENSITIVE") == "SURVIVAL_ANTICIPATION_SENSITIVE"
    leurre = {"degenerate": False, "verdict": "X_DECOY", "n": 24, "ratio": 1.0}
    assert _verdict_from(leurre, "SURVIVAL_ANTICIPATION_SENSITIVE") == "SURVIVAL_NEUTRAL"


def test_the_declared_floors_match_their_measurement():
    """Les constantes declarees doivent rester celles qui ont ete MESUREES — pas de derive silencieuse."""
    from tools.anticipation_demand_world_probe import PLANCHER_AVEUGLE as pa
    from tools.cognitive_demand_world_probe import PLANCHER_AVEUGLE as pc
    from tools.memory_demand_world_probe import PLANCHER_AVEUGLE as pm
    from tools.composition_demand_world_probe import PLANCHER_AVEUGLE as pv, PLANCHER_SANS_PLAN as pp
    assert pa == pc == pm == pv == 30.0, "le regime partage A a UN plancher : 30.0"
    assert pp == 54.0, "composition a le sien : 54.0 (enumere)"


def test_the_four_verdict_from_copies_are_IDENTICAL():
    """⚠️ ANTI-DERIVE. `_verdict_from` est duplique VOLONTAIREMENT dans les 4 sondes (calque de la
    recommandation « duplication commentee, pas de nouveau module »). Le prix de la duplication est la
    derive silencieuse : si une copie change seule, les quatre sondes ne consomment plus la meme garde.
    Ce test gele l'identite -- toute divergence doit etre soit propagee aux quatre, soit ce test mis a
    jour EXPLICITEMENT avec la raison."""
    import inspect
    from tools import (anticipation_demand_world_probe as A, cognitive_demand_world_probe as C,
                       composition_demand_world_probe as P, memory_demand_world_probe as M)
    srcs = {m.__name__: inspect.getsource(m._verdict_from) for m in (A, P, M)}
    ref = srcs.pop('tools.anticipation_demand_world_probe')
    for nom, src in srcs.items():
        assert src == ref, f"la copie de _verdict_from dans {nom} a derive de la reference"
    assert not hasattr(C, '_verdict_from') or inspect.getsource(C._verdict_from) == ref


def test_verdict_from_is_calibrated_via_the_anticipation_copy():
    """Le comportement des 4 copies est calibre par test_verdict_from_READS_... (degenerate prioritaire,
    X_DEMANDED -> sensitive, X_DECOY -> NEUTRAL) + l'anti-derive ci-dessus qui etend la couverture aux
    trois autres copies. Ce test verifie seulement que la chaine tient : la copie de reference est bien
    celle que le test de comportement importe."""
    from tools.anticipation_demand_world_probe import _verdict_from
    assert _verdict_from({"degenerate": True, "verdict": "X", "n": 24}, "S") == "INDETERMINE_DEGENERATE"


def test_floor_for_is_REGIME_GATED():
    """⚠️ Garde E8 : un plancher mesure a 12 agents/200 ticks ne vaut RIEN a 20/400. Hors regime,
    _floor_for doit rendre None -- importer un plancher d'ailleurs fabriquerait la degenerescence
    qu'il est cense detecter (l'erreur du seuil ~99 % importe de WARM-001 dans WARM-002)."""
    from tools.s2_demand_ablation import _floor_for
    assert _floor_for("stoneage", 12, 200) == 24.0
    assert _floor_for("stoneage", 20, 400) is None, "hors regime -> None, jamais une valeur importee"
    assert _floor_for("monde_inconnu", 12, 200) is None


def test_noperc_floors_match_their_measurement():
    """Les constantes declarees = les valeurs MESUREES (campagne du 2026-09-02, seed 3026)."""
    from tools.s2_demand_ablation import PLANCHER_NOPERC
    assert PLANCHER_NOPERC == {"soup": 32.0, "stoneage": 24.0, "agricultural": 25.25,
                               "industrial": 24.0, "famine": 21.75}


# ---------------------------------------------------------------------------------------------------
# P2.38 (2026-09-02) : logit_median_at_outputs -- la DV mecaniste d'EVO-027, REPAREE puis calibree.
# L'ancien helper in-run passait H_prev=None a recurrent_forward (None.copy() leve) et AVALAIT
# l'echec (except: continue) -> nan muet sur tout le run. Forme (b) canonique du biais negatif
# (le nan DETECTE puis avale). Regle d'auto-amelioration : le bug devient le cas de calibration.
# ---------------------------------------------------------------------------------------------------

def _genome_stub(W, num_inputs, num_outputs):
    from types import SimpleNamespace
    import numpy as np
    return SimpleNamespace(W=np.asarray(W, dtype=np.float64), num_inputs=num_inputs,
                           num_outputs=num_outputs, num_nodes=len(W))


def test_logit_median_noop_EXACT_zero():
    """No-op EXACT : W nulle -> H reste a zero hors bloc d'entree -> mediane 0.0 EXACTEMENT."""
    import numpy as np
    from tools.evo_mech_dv import logit_median_at_outputs
    g = _genome_stub(np.zeros((5, 5)), 2, 2)
    r = logit_median_at_outputs([g], paires_rel=((0, 1),))
    assert r["median"] == 0.0 and r["n_ok"] == 1 and r["n_failed"] == 0


def test_logit_median_predicts_closed_form():
    """Reponse connue en FORME CLOSE : une seule arete canal0 -> sortie relative 1 (noeud N-O+1),
    H0=0, pas d'organe MCTS (T=1), diagonale nulle (delta=sigmoid(0)=0.5) :
        |logit| = 0.5 * |tanh(w * obs[:, 0])|
    C'est exactement le cas que l'ancien helper d'EVO-027 rendait nan EN SILENCE."""
    import numpy as np
    from tools.evo_mech_dv import logit_median_at_outputs
    w = 1.7
    W = np.zeros((5, 5)); W[0, 4] = w              # noeud 4 = sortie relative 1 (N=5, O=2)
    g = _genome_stub(W, 2, 2)
    r = logit_median_at_outputs([g], paires_rel=((0, 1),), n_obs=8, seed=12345)
    obs = np.random.default_rng(12345).standard_normal((8, 2)).astype(np.float32)
    attendu = float(np.median(0.5 * np.abs(np.tanh(w * obs[:, 0]))))
    assert r["n_ok"] == 1 and r["n_failed"] == 0
    assert np.isclose(r["median"], attendu, rtol=1e-5), (r["median"], attendu)


def test_logit_median_failure_is_LOUD():
    """L'echec d'un forward n'est PLUS avale : n_failed et failures le disent, la mediane reste nan
    mais l'instrument SAIT et LE DIT (l'ancien comportement -- nan muet -- est la classe a bannir)."""
    import math
    from types import SimpleNamespace
    from tools.evo_mech_dv import logit_median_at_outputs
    casse = SimpleNamespace(num_inputs=2, num_nodes=5)          # pas de num_outputs ni W -> le forward leve
    r = logit_median_at_outputs([casse], paires_rel=((0, 1),))
    assert r["n_failed"] == 1 and r["n_ok"] == 0
    assert math.isnan(r["median"]) and r["failures"], "le nan doit etre ACCOMPAGNE de sa cause"


# ------------------------------------------------------------------------------------------------
# CINQUIEME ANGLE MORT D'E4 (2026-09-02) : le cliquet ne voyait pas la famille des GARDES.
# ------------------------------------------------------------------------------------------------

def test_the_ratchet_SEES_the_assert_guard_family():
    """CONTRE-EXEMPLE GELE, tire sur la CONFIGURATION EXACTE qui a produit l'erreur reelle.

    Fait mesure avant correctif : `assert_bar_is_reachable`, livree en `f7bd77e` AVEC ses 5 cas de
    calibration ET sa declaration dans `CALIBRATED`, etait ABSENTE du rapport du cliquet -- aucun motif
    de l'heuristique ne connaissait `assert_*`. Sa declaration tombait dans la branche « declaration
    perimee : ignoree » de `scan_calibrated()`, donc en SILENCE. Corollaire plus grave :
    `assert_verdict_invariant_to_optimizer` n'etait detecte que PAR ACCIDENT, son nom contenant la
    sous-chaine « verdict ». La famille de fonctions qui SONT les gardes du depot echappait au cliquet
    cense garantir qu'elles sont calibrees : une future garde pouvait etre livree sans le moindre cas et
    le compteur afficher « OK, aucun nouvel instrument non calibre ». C'est E4 (« verification vide :
    0 echec indiscernable d'un succes ») dans l'outil ecrit pour l'empecher.

    Ce test ECHOUE si l'heuristique redevient aveugle a cette famille -- il ne se contente pas de passer
    aujourd'hui. Il gele TROIS proprietes distinctes, chacune une facon differente de rouvrir le trou."""
    import tools.check_instrument_calibration as C
    instruments = C.scan_instruments()

    # (1) DETECTION -- le cas exact de l'erreur reelle. Casse si le motif `assert_*` disparait.
    assert "assert_bar_is_reachable" in instruments, (
        "l'heuristique est redevenue aveugle a `assert_*` : une garde livree sans cas de calibration "
        "passerait desormais pour « OK »")
    assert instruments["assert_bar_is_reachable"] == "tools/experiment_preflight.py"

    # (2) PORTEE -- la famille ne vit PAS que dans `experiment_preflight.py`. `assert_aux_off_safe`
    # (garde EDR-WARM-008) est le contre-exemple MESURE qui interdit de restreindre le motif a ce seul
    # module : une portee « module de pre-vol uniquement » rouvrirait le trou pour cette garde-la.
    assert instruments.get("assert_aux_off_safe") == "tools/warmstart_evolution_inworld.py", (
        "portee retrecie au seul module de pre-vol -> les gardes vivant ailleurs redeviennent invisibles")

    # (3) LA DECLARATION EST HONOREE -- detecter ne suffit pas. Le defaut reel etait un rejet SILENCIEUX
    # de la declaration ; si `scan_calibrated()` cessait de la reconnaitre, (1) passerait toujours et la
    # garde compterait comme DETTE au lieu de calibree. On verifie donc l'aller-retour complet.
    calibrated = C.scan_calibrated()
    assert "assert_bar_is_reachable" in calibrated, (
        "la declaration `CALIBRATED` de la garde est de nouveau ignoree en silence")
    assert "assert_verdict_invariant_to_optimizer" in calibrated

    # (4) AUCUNE de la famille ne doit etre une dette silencieuse : au moment du correctif, les 11
    # `assert_*` du perimetre etaient TOUTES deja couvertes (fires + spares) -> zero dette legataire
    # gelee, rien n'a ete fait disparaitre par `--update-baseline`. Ce controle fige ce fait : une
    # NOUVELLE garde `assert_*` non calibree fera echouer ce test en plus de bloquer le cliquet.
    famille = {n for n in instruments if n.startswith("assert_")}
    assert len(famille) >= 11, f"la famille a retreci : {sorted(famille)}"
    # `NOT_AN_INSTRUMENT` peut etre QUALIFIE (« fichier.py::fonction ») : denuder avant de soustraire,
    # sinon une exemption legitime ne serait pas reconnue et ce test crierait a tort.
    faux_positifs = {n.split("::")[-1] for n in C.scan_not_instruments()}
    non_calibrees = sorted(famille - calibrated - faux_positifs)
    assert not non_calibrees, (
        f"garde(s) `assert_*` sans cas de calibration declare : {non_calibrees} -- ajouter les cas "
        f"(les DEUX issues) puis declarer dans CALIBRATED, ou justifier dans NOT_AN_INSTRUMENT")


# ---------------------------------------------------------------------------------------------------
# P2.39 (2026-09-02) : le BANC COMPOSITIONNEL -- 9 orchestrateurs qui PRONONCENT les verdicts de la
# porte SDR-G2 (BINDING_FORCED, GATE_BINDS, ANTISAT_RESCUES...) et qui etaient INVISIBLES au cliquet.
# 6e angle mort de nommage : aucun motif ne couvrait `compare_*`, `sweep_*`, `probe_*` en TETE de nom
# (seul `run_*sweep*` etc. l'etait). Mesure AVANT elargissement : +22 fonctions, dont ces 9.
# Consequence directe : la porte G2 declarait un KPI (`binding_gap`) dont AUCUN producteur n'etait
# calibre -- c'est la raison pour laquelle SDR-G2 bloque tout nouveau run proxy.
#
# TECHNIQUE : injection a DOSE CONNUE (celle des 13 orchestrateurs de monde du 2026-09-01). Aucun de
# ces 9 ne simule : ils appellent `run_curriculum_fade[_gated]` et AGREGENT. On leur impose des
# cellules factices a valeurs choisies et on verifie que le verdict tombe JUSTE -- y compris ses
# branches NEGATIVES, sans lesquelles le test ne prouverait rien (E1).
# ---------------------------------------------------------------------------------------------------

_CELL_DEFAUT = {"binding_gap_end": 0.05, "p_y_given_x_end": 0.50, "p_y_given_not_x_end": 0.45,
                "y_rate_end": 0.50, "hit_end": 0.20, "compo_didx_end": 0.70,
                "y_rate_start": 0.60, "binding_gap_start": 0.02, "did_x_auc_early": 0.60,
                "delta": 0.0, "warmup_didx_end": 0.80,
                # cle lue par le SEUL sweep_gate_readout (marge de suppression du gate) -- trouvee
                # PAR l'injection : sans elle, KeyError. C'est ce que ce type de test sert a voir.
                "gate_bias_margin_end": 0.0}


def _cellule(**over):
    """Cellule factice complete : toutes les cles que les orchestrateurs lisent, surchargeables."""
    c = dict(_CELL_DEFAUT)
    c.update(over)
    return c


def _injecte(monkeypatch, nom, fabrique):
    """Remplace `nom` DANS le module du banc par `fabrique(backend, **kw) -> cellule`."""
    import tools.substrate_ab_compositional as B
    monkeypatch.setattr(B, nom, fabrique)
    return B


def test_sweep_binding_penalty_READS_the_dose_response_it_claims(monkeypatch):
    """Reponse connue x3 : la dose-reponse est IMPOSEE, le verdict doit suivre.
    BINDING_FORCED (le gap s'ouvre sans suppression) / SUPPRESSION (P(Y|X) s'effondre : l'echec
    trivial que le gap seul masquerait) / SIGNAL_INSUFFICIENT (gap plat)."""
    import tools.substrate_ab_compositional as B

    def _forced(backend, seed=0, y_without_x_penalty=0.0, **kw):
        return _cellule(binding_gap_end=(0.60 if y_without_x_penalty > 0 else 0.05),
                        p_y_given_x_end=0.80)

    def _suppression(backend, seed=0, y_without_x_penalty=0.0, **kw):
        return _cellule(binding_gap_end=(0.60 if y_without_x_penalty > 0 else 0.05),
                        p_y_given_x_end=(0.10 if y_without_x_penalty > 0 else 0.80))

    def _plat(backend, seed=0, y_without_x_penalty=0.0, **kw):
        return _cellule(binding_gap_end=0.05, p_y_given_x_end=0.80)

    for fab, attendu in ((_forced, "BINDING_FORCED"), (_suppression, "SUPPRESSION"),
                         (_plat, "SIGNAL_INSUFFICIENT")):
        monkeypatch.setattr(B, "run_curriculum_fade", fab)
        r = B.sweep_binding_penalty(seeds=(0, 1, 2), penalties=(0.0, 2.0), backends=("torch",))
        assert r["verdict"] == attendu, (attendu, r["verdict"])


def test_compare_gate_modes_READS_the_per_seed_bimodality(monkeypatch):
    """Reponse connue x3. ⚠️ Ce que ce test protege : le gate appris est BIMODAL (binde OU collapse) --
    l'instrument compte `n_bind` PAR SEED, pas la mediane. Une regression vers la mediane rendrait
    GATE_COLLAPSES sur une distribution 2/5 qui binde reellement."""
    import tools.substrate_ab_compositional as B

    def _fab(learned_gaps):
        etat = {"i": 0}

        def _f(backend, seed=0, gate_mode="learned", **kw):
            if gate_mode == "oracle":
                return _cellule(binding_gap_end=0.90)
            if gate_mode == "none":
                return _cellule(binding_gap_end=0.05)
            g = learned_gaps[etat["i"] % len(learned_gaps)]
            etat["i"] += 1
            return _cellule(binding_gap_end=g)
        return _f

    cas = (([0.9, 0.9, 0.9, 0.05, 0.05], "GATE_BINDS"),      # majorite binde
           ([0.0, 0.0, 0.0, 0.0, 0.0], "GATE_COLLAPSES"),     # aucun
           ([0.9, 0.05, 0.05, 0.05, 0.05], "GATE_INTERMITTENT"))
    for gaps, attendu in cas:
        monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(gaps))
        r = B.compare_gate_modes(seeds=(0, 1, 2, 3, 4))
        assert r["verdict"] == attendu, (attendu, r["verdict"], r["per_mode"]["learned"])


def test_the_four_gate_sweeps_READ_their_own_improvement_threshold(monkeypatch):
    """Les 4 balayages `sweep_gate_*` / `sweep_y_saturation` partagent la meme forme : n_bind d'une
    baseline vs n_bind du meilleur bras, seuil +2. Reponse connue : baseline 5/10 et meilleur 8/10
    doit tirer le verdict POSITIF de chacun ; baseline 5/10 et meilleur 5/10 le NEGATIF."""
    import tools.substrate_ab_compositional as B

    def _fab(n_bind_base, n_bind_traite, est_traite):
        etat = {"i": 0}

        def _f(backend, seed=0, **kw):
            n = n_bind_traite if est_traite(kw) else n_bind_base
            i = etat["i"] % 10
            etat["i"] += 1
            return _cellule(binding_gap_end=(0.90 if i < n else 0.05))
        return _f

    seeds = tuple(range(10))
    # (fonction, est_traite, kwargs, verdict positif, verdict negatif)
    cas = (
        (B.sweep_gate_reliability, lambda kw: kw.get("entropy_coef", 0.0) > 0
         or kw.get("elig_lambda", 0.0) > 0, {}, "RELIABILITY_IMPROVED", "NO_IMPROVEMENT"),
        (B.sweep_gate_warmstart, lambda kw: kw.get("gate_warmstart_trials", 0) > 0, {},
         "RESCUE", "NO_RESCUE"),
        (B.sweep_gate_readout, lambda kw: kw.get("gate_hidden", 0) > 0, {},
         "READOUT_HELPS", "READOUT_NEUTRAL"),
    )
    for fn, est_traite, kwargs, pos, neg in cas:
        monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(5, 8, est_traite))
        assert fn(seeds=seeds, **kwargs)["verdict"] == pos, (fn.__name__, pos)
        monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(5, 5, est_traite))
        assert fn(seeds=seeds, **kwargs)["verdict"] == neg, (fn.__name__, neg)


def test_sweep_y_saturation_SEPARATES_neutral_from_ineffective(monkeypatch):
    """⚠️ LE cas qui compte pour cet instrument : ses deux verdicts nuls ne disent PAS la meme chose.
    ANTISAT_NEUTRAL = la penalite MORD (y_rate_start chute) et ne rescape pas -> refute l'hypothese
    saturation. ANTISAT_INEFFECTIVE = la penalite ne mord meme pas -> manip ratee, RIEN n'est refute.
    Les confondre publierait une refutation la ou il n'y a qu'une manipulation manquee (le motif
    « donnees absentes -> affirmation NEGATIVE de fond » du depot)."""
    import tools.substrate_ab_compositional as B

    def _fab(n_bind_traite, y_start_traite):
        etat = {"i": 0}

        def _f(backend, seed=0, y_saturation_penalty=0.0, **kw):
            traite = y_saturation_penalty > 0
            n = n_bind_traite if traite else 5
            i = etat["i"] % 10
            etat["i"] += 1
            return _cellule(binding_gap_end=(0.90 if i < n else 0.05),
                            y_rate_start=(y_start_traite if traite else 0.60))
        return _f

    seeds = tuple(range(10))
    monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(8, 0.30))
    assert B.sweep_y_saturation(seeds=seeds, penalties=(0.0, 1.0))["verdict"] == "ANTISAT_RESCUES"
    monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(5, 0.30))      # mord, ne rescape pas
    r = B.sweep_y_saturation(seeds=seeds, penalties=(0.0, 1.0))
    assert r["verdict"] == "ANTISAT_NEUTRAL" and r["manip_lowered_saturation"] is True
    monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(5, 0.60))      # ne mord PAS
    r = B.sweep_y_saturation(seeds=seeds, penalties=(0.0, 1.0))
    assert r["verdict"] == "ANTISAT_INEFFECTIVE" and r["manip_lowered_saturation"] is False


def test_sweep_overtraining_stability_READS_erosion_across_horizons(monkeypatch):
    """Reponse connue : n_bind qui CHUTE de 8 a 5 entre le horizon court et le long -> BINDING_EROSION ;
    n_bind stable -> RECIPE_ROBUST. (Le verdict porte sur la plus forte penalite = la recette 136.)"""
    import tools.substrate_ab_compositional as B

    def _fab(n_court, n_long):
        etat = {"i": 0}

        def _f(backend, seed=0, compo_trials=250, **kw):
            n = n_long if compo_trials >= 1000 else n_court
            i = etat["i"] % 10
            etat["i"] += 1
            return _cellule(binding_gap_end=(0.90 if i < n else 0.05))
        return _f

    seeds = tuple(range(10))
    monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(8, 5))
    assert B.sweep_overtraining_stability(seeds=seeds, penalties=(6.0,),
                                          compo_trials_list=(250, 1000))["verdict"] == "BINDING_EROSION"
    monkeypatch.setattr(B, "run_curriculum_fade_gated", _fab(8, 8))
    assert B.sweep_overtraining_stability(seeds=seeds, penalties=(6.0,),
                                          compo_trials_list=(250, 1000))["verdict"] == "RECIPE_ROBUST"


def test_probe_collapse_predictors_SEPARATES_the_two_groups_it_compares(monkeypatch):
    """DIAGNOSTIC (pas de verdict) : il compare la moyenne d'un predicteur chez les BINDEURS vs les
    COLLAPSES. Reponse connue en forme close : auc 0.90 chez les bindeurs, 0.50 chez les collapses
    -> separation EXACTEMENT 0.40. Un appariement casse (groupes intervertis) le montrerait."""
    import tools.substrate_ab_compositional as B
    etat = {"i": 0}

    def _f(backend, seed=0, **kw):
        bindeur = etat["i"] < 5
        etat["i"] += 1
        return _cellule(binding_gap_end=(0.90 if bindeur else 0.05),
                        did_x_auc_early=(0.90 if bindeur else 0.50))

    monkeypatch.setattr(B, "run_curriculum_fade_gated", _f)
    r = B.probe_collapse_predictors(seeds=tuple(range(10)))
    pred = r["predictors"]["did_x_auc_early"]
    assert r["n_bind"] == 5 and pred["bind_mean"] == 0.90 and pred["collapse_mean"] == 0.50
    assert abs(pred["separation"] - 0.40) < 1e-9


def test_the_two_curriculum_comparators_READ_their_guard_before_their_claim(monkeypatch):
    """`compare_curriculum` et `compare_curriculum_fade` portent chacun un GARDE-FOU en tete de leur
    regle de lecture : si le warmup n'a pas pris (didx <= 0.30) / si le fade n'a pas maintenu X
    (compo_didx <= 0.40), AUCUNE conclusion de plafond n'est permise. Reponse connue : le garde-fou
    doit primer meme quand les chiffres AVAL sont ceux d'un beau positif."""
    import tools.substrate_ab_compositional as B

    monkeypatch.setattr(B, "run_curriculum",
                        lambda backend, seed=0, **kw: _cellule(warmup_didx_end=0.10, hit_end=0.90))
    assert B.compare_curriculum(seeds=(0, 1, 2))["verdict_curriculum"] == "WARMUP_FAILED"
    monkeypatch.setattr(B, "run_curriculum",
                        lambda backend, seed=0, **kw: _cellule(warmup_didx_end=0.80, hit_end=0.90))
    assert B.compare_curriculum(seeds=(0, 1, 2))["verdict_curriculum"] == "DISCOVERY"
    monkeypatch.setattr(B, "run_curriculum",
                        lambda backend, seed=0, **kw: _cellule(warmup_didx_end=0.80, hit_end=0.10))
    assert B.compare_curriculum(seeds=(0, 1, 2))["verdict_curriculum"] == "CREDIT"

    monkeypatch.setattr(B, "run_curriculum_fade",
                        lambda backend, seed=0, **kw: _cellule(compo_didx_end=0.20, hit_end=0.90,
                                                               p_y_given_x_end=0.90))
    assert B.compare_curriculum_fade(seeds=(0, 1, 2))["verdict_fade"] == "FADE_INEFFECTIVE"
    monkeypatch.setattr(B, "run_curriculum_fade",
                        lambda backend, seed=0, **kw: _cellule(compo_didx_end=0.80, hit_end=0.50,
                                                               p_y_given_x_end=0.90))
    assert B.compare_curriculum_fade(seeds=(0, 1, 2))["verdict_fade"] == "CEILING_WAS_RETENTION"
    monkeypatch.setattr(B, "run_curriculum_fade",
                        lambda backend, seed=0, **kw: _cellule(compo_didx_end=0.80, hit_end=0.10,
                                                               p_y_given_x_end=0.50))
    assert B.compare_curriculum_fade(seeds=(0, 1, 2))["verdict_fade"] == "CEILING_WAS_BINDING"


# ======================================================================================================
# P2.40 (2026-09-02) : TROISIEME VAGUE DE GARDES -- les 12 sondes rendues visibles par le 6e
# elargissement du detecteur (verbes `compare_`/`sweep_`/`probe_` en TETE de nom). Meme principe et
# meme justification que P2.34/P2.37 : un argument degenere est une erreur d'APPEL, pas un fait sur le
# monde. La garde est posee AVANT la construction du monde -> calibration a cout ZERO, et on teste non
# seulement QU'elle leve mais OU elle est posee (refus < 0.5 s).
# ======================================================================================================

_MESURES_GARDEES_3 = [
    ("tools.substrate_world_ab", "compare_backends", dict(k_eval=0)),
    ("tools.substrate_world_ab", "compare_arms", dict(num_agents=0)),
    ("tools.substrate_world_ab", "sweep_lr_torch", dict(world_key="stoneage", seed=0, genome=None, lrs=())),
    ("tools.torch_throw_gate_inworld_ab", "compare_debias", dict(seeds=())),
    ("tools.torch_throw_gate_inworld_ab", "compare_density", dict(ticks=0)),
    ("tools.torch_throw_gate_inworld_ab", "compare_warmstart", dict(n_agents=0)),
    ("tools.torch_throw_gate_inworld_ab", "compare_rp_sweep", dict(prey_levels=())),
    # P2.60 (2026-09-15) : banc factoriel EDR-177 + driver EDR-178, portes par fusion 3-voies -- meme
    # garde, meme forme, meme test de placement.
    ("tools.torch_throw_gate_inworld_ab", "compare_factorial", dict(seeds=())),
    ("tools.factorial_regime_sweep", "run_sweep", dict(regimes={})),
    ("tools.evo_memory_inworld", "probe_memory_discrimination",
     dict(genome=None, mode="visible", seed=0, n_trials=0)),
    ("tools.evo_memory_inworld", "probe_navigation_incontext",
     dict(genome=None, mode="visible", seed=0, num_agents=0)),
    ("tools.evo_memory_inworld", "probe_attack_logit",
     dict(genome=None, mode="visible", seed=0, ticks=0)),
    ("tools.warmstart_evolution_inworld", "probe_genome_free_channels", dict(genome=None, max_ticks=0)),
    ("tools.substrate_attractor_probe", "probe_substrate_attractor", dict(n=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_3)
def test_third_wave_measures_REFUSE_degenerate_arguments(mod, nom, kw):
    """⚠️ Ces 12 etaient INVISIBLES au cliquet jusqu'au 2026-09-02 : aucun motif ne couvrait leurs
    verbes en tete de nom. Elles produisent pourtant des verdicts de monde (GRADIENT_GAGNE,
    discrimination, logit d'attaque). Sans garde, `seeds=()` / `ticks=0` rendait une agregation VIDE
    lue en aval comme une mesure -- la forme (a) du biais negatif systematique du depot."""
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_3)
def test_third_wave_guards_are_placed_BEFORE_the_world(mod, nom, kw):
    """⚠️ PLACEMENT : plusieurs de ces sondes construisent un monde reel (voire prennent le bail kuzu).
    Un refus instantane prouve que la garde precede la construction -- une garde posee plus bas
    couterait une ressource exclusive pour rien."""
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


# ======================================================================================================
# P2.41 (2026-09-02) : NIVEAU 2 de SDR-G2 -- la sonde monde compositionnelle.
# `run_world` produit `comp_rate`, le KPI du niveau 2 de la porte, et etait invisible au cliquet
# (motif CIBLE `world` ajoute : +3 fonctions, la ou `run_\w+` generique en ajouterait +56).
# Son VERDICT etait calcule INLINE dans `main` -> ni testable ni calibrable : il est EXTRAIT en
# fonction pure `capability_payoff_verdict`, calibree ici sur reponse connue.
# ======================================================================================================

def test_capability_payoff_verdict_READS_the_slope_it_claims():
    """Reponse connue x2 : l'avantage CROIT avec la demande (0.01 -> 0.21, les chiffres d'EDR-161)
    -> CAPABILITY_PAYS ; l'avantage est PLAT -> CAPABILITY_NO_PAYOFF. Les deux issues sont
    atteignables sur le meme instrument (E1)."""
    from tools.compositional_world_probe import capability_payoff_verdict
    assert capability_payoff_verdict({0.0: 0.009, 1.0: 0.212})["verdict"] ==         "CAPABILITY_PAYS_UNDER_COMPOSITION_DEMAND"
    assert capability_payoff_verdict({0.0: 0.20, 1.0: 0.21})["verdict"] == "CAPABILITY_NO_PAYOFF"
    # gain reel mais SANS pente : la clause exige les DEUX (pente ET gain absolu)
    assert capability_payoff_verdict({0.0: 0.30, 1.0: 0.30})["verdict"] == "CAPABILITY_NO_PAYOFF"


def test_capability_payoff_verdict_REFUSES_to_read_a_slope_from_ONE_point():
    """⚠️ CONTRE-EXEMPLE GELE -- le motif dominant du depot (donnees absentes -> affirmation NEGATIVE
    de fond). L'ancien code INLINE de `main` rendait CAPABILITY_NO_PAYOFF sur une seule demande,
    c.-a-d. la ou AUCUNE pente n'est definissable : un « la capacite ne paie pas » fabrique par
    l'absence de second point. La fonction extraite REFUSE au lieu d'affirmer."""
    from tools.compositional_world_probe import capability_payoff_verdict
    for entree in ({1.0: 0.50}, {}, {0.0: None, 1.0: 0.50}):
        r = capability_payoff_verdict(entree)
        assert r["verdict"] == "INDETERMINE_AUCUNE_MESURE", (entree, r)
        assert "deux niveaux" in r["why"]


_MESURES_GARDEES_4 = [
    ("tools.compositional_world_probe", "run_world", dict(capability=True, demand=1.0, episodes=0)),
    ("tools.curriculum_world", "run_world_era",
     dict(config=None, db=None, target_prey=10, num_agents=0)),
    # revelees PAR la collision de noms (3 fichiers portent `run_world`) -- elles etaient invisibles
    ("tools.language_payoff_probe", "run_world", dict(demanding=True, K=0, seed=0)),
    ("tools.world_demand_marker_probe", "run_world", dict(demanding=True, K=4, seed=0, n_eval=0)),
    ("tools.warmstart_evolution_inworld", "run_inworld_evolution", dict(generations=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_4)
def test_world_probes_REFUSE_degenerate_arguments(mod, nom, kw):
    """Meme principe que les 3 vagues precedentes : 0 episode / 0 agent est une erreur d'APPEL."""
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_4)
def test_world_probe_guards_are_placed_BEFORE_the_world(mod, nom, kw):
    """PLACEMENT : `run_world` construit une population torch de 128 agents, `run_world_era` une
    Biosphere3D -- un refus instantane prouve que la garde precede la construction."""
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


# ======================================================================================================
# P2.42 (2026-09-06) : `src/seed_ai/eval_harness.py::verdict` -- le verdict statistique du harnais
# puissant (EDR 052), en COLLISION de nom avec tools/is_machine_idle.py::verdict (non-instrument) et
# donc INVISIBLE au cliquet jusqu'ici. Utilise par aligned_selection, confirm_055, fiabiliser,
# lang_speciation : il PRONONCE « SIGNIFICATIF » / « bruit ». Reponses connues en forme close.
# ======================================================================================================

def _cond(mean, std, n):
    return {"mean": float(mean), "std": float(std), "n": int(n), "vals": []}


def test_eval_harness_verdict_READS_a_clear_separation_with_the_right_winner():
    """Reponse connue : 0 vs 1, std 0.1, n=3 -> d = 10, t = 10*sqrt(1.5) = 12.25 -> SIGNIFICATIF, et le
    gagnant est la condition a la plus haute moyenne (direction preservee dans les deux ordres)."""
    import math
    from src.seed_ai.eval_harness import verdict
    r = {"a": _cond(0.0, 0.1, 3), "b": _cond(1.0, 0.1, 3)}
    v = verdict("a", "b", r)
    assert v["significant"] and v["winner"] == "b"
    assert math.isclose(abs(v["d"]), 10.0, rel_tol=1e-9)
    assert math.isclose(abs(v["t"]), 10.0 * math.sqrt(1.5), rel_tol=1e-9)
    assert verdict("b", "a", r)["winner"] == "b"


def test_eval_harness_verdict_calls_identical_conditions_NOISE():
    """Specificite : memes moyennes -> t = d = 0 -> NON significatif, aucun gagnant."""
    from src.seed_ai.eval_harness import verdict
    v = verdict("a", "b", {"a": _cond(0.5, 0.2, 3), "b": _cond(0.5, 0.2, 3)})
    assert not v["significant"] and v["winner"] is None and v["t"] == 0.0 and v["d"] == 0.0


def test_eval_harness_verdict_AND_rule_refuses_a_large_effect_measured_without_power():
    """⚠️ LA clause qui fait l'instrument : |t|>=2.5 ET |d|>=0.8. Forme close pour na=nb=n, sa=sb=s :
    t = d*sqrt(n/2). A n=2, std 1, moyennes 0 vs 1 : d = 1.0 (grand) mais t = 1.0 (< 2.5) -> le
    verdict doit etre NON significatif. Lecon d'EDR 051 gelee : un run sous-puissant CLASSE LE BRUIT --
    un grand effet mesure sur 2 seeds n'est pas un verdict."""
    import math
    from src.seed_ai.eval_harness import verdict
    v = verdict("a", "b", {"a": _cond(0.0, 1.0, 2), "b": _cond(1.0, 1.0, 2)})
    assert math.isclose(abs(v["d"]), 1.0, rel_tol=1e-9) and math.isclose(abs(v["t"]), 1.0, rel_tol=1e-9)
    assert not v["significant"] and v["winner"] is None


def test_eval_harness_verdict_gives_NO_verdict_on_zero_variance():
    """⚠️ CHANGE EXPLICITEMENT le 2026-09-14 (P2.57), comme la version precedente l'exigeait.
    Elle gelait : « variance NULLE -> t force a 0 -> NON significatif ; l'instrument refuse de
    prononcer sans estimation du bruit ». Mais « NON significatif » N'EST PAS un refus de prononcer :
    `summary` l'ecrit « NON significatif (bruit) » et neuf outils le lisent comme un nul. C'etait un
    negatif fabrique, et la docstring le disait sans le voir.
    Le choix est desormais SEPARE en deux cas, et les deux sont geles ici :
      * n < 2 : il n'y a PAS d'estimation du bruit -> l'instrument REFUSE (leve), il ne rend rien ;
      * n >= 2 a variance nulle et moyennes DISTINCTES : c'est une mesure (dispersion zero,
        difference deterministe) -> separation PARFAITE, t = +-inf, significatif. Moyennes EGALES
        a variance nulle -> t = 0, la seule lecture nulle qui reste."""
    import pytest
    from src.seed_ai.eval_harness import verdict
    with pytest.raises(ValueError, match="INDEFINI"):
        verdict("a", "b", {"a": _cond(0.0, 0.0, 1), "b": _cond(1.0, 0.0, 1)})   # n = 1 : REFUS
    v = verdict("a", "b", {"a": _cond(0.0, 0.0, 3), "b": _cond(1.0, 0.0, 3)})
    assert v["t"] == float("-inf") and v["significant"] and v["winner"] == "b"
    v0 = verdict("a", "b", {"a": _cond(1.0, 0.0, 3), "b": _cond(1.0, 0.0, 3)})
    assert v0["t"] == 0.0 and not v0["significant"]


# ======================================================================================================
# P2.43 (2026-09-06) : FAMILLE run_* -- 7e elargissement du cliquet de calibration. Un motif run_\\w+
# generique etait connu pour ajouter ~56 fonctions non calibrees (mesure le 2026-09-02, delibere-
# ment NON avale alors). Inventaire refute : 72 fonctions -- 57 simulateurs, 14 orchestrateurs,
# 4 helpers. Ici : les simulateurs (+ 3 orchestrateurs a garde), par GARDE D'ARGUMENTS EN TETE,
# testee QUE (leve) et OU (refus < 0.5 s, donc avant la construction du monde). Les 11 autres
# orchestrateurs ont chacun un test d'INJECTION A DOSE CONNUE (section P2.44).
# ⚠️ Toutes les declarations sont QUALIFIEES par chemin : 5 noms sont en collision (run_condition,
# run_era, run_seed, run_arm, run_compositional) et le cliquet ne doit verdir un nom qu'une fois
# TOUS ses chemins couverts (defaut `out.add(bare)` corrige dans la meme passe).
# ======================================================================================================

_MESURES_GARDEES_5 = [
    ("tools.ablation", "run_condition", dict(config=None, db=None, apply_fn=None, num_agents=0)),
    ("tools.ablation_multi", "run_condition", dict(config=None, db=None, apply_fn=None, crit_base=0.0, num_agents=0)),
    ("tools.adaptive_planning_probe", "run_adaptive", dict(n_test=0)),
    ("tools.agricultural_demand_probe", "run_agricultural", dict(genome=None, seed=0, num_agents=0)),
    ("tools.altar_tool_funnel_probe", "run_era_funnel", dict(seed=0, metab=0.25, payoff=3.0, num_agents=0, max_ticks=40, shared_db=None)),
    ("tools.anticipation_bench", "run_bench", dict(plan_bias=0.0, seeds=[0], steps=0)),
    ("tools.s2_demand", "run_condition", dict(world_cls=None, batch_model_cls=None, genome=None, seed=0, num_agents=0)),
    ("tools.anticipation_planning_probe", "run_planning", dict(n_test=0)),
    ("tools.arm_act_grad", "run_bptt_act", dict(W=None, K=0, D=10, bits=None, act=None)),
    ("tools.cognitive_demand_inworld", "run_credit_linear", dict(num_agents=0)),
    ("tools.comm_lever", "run_era", dict(config=None, db=None, hear_radius=3, num_agents=0)),
    ("tools.compositional_language_probe", "run_compositional", dict(episodes=0)),
    ("tools.confirm_scramble", "run_era", dict(config=None, db=None, hear_radius=3, scramble=False, num_agents=0)),
    ("tools.craft_specialization_probe", "run_spec", dict(capability=True, episodes=0)),
    ("tools.curriculum_2d", "run_2d_era", dict(config=None, db=None, target_prey=10, num_agents=0)),
    ("tools.curriculum_developmental", "run_era", dict(config=None, db=None, global_era=0, rarity=10, crit_eras=20, group_eras=20, num_agents=0)),
    ("tools.curriculum_grab", "run_one_era", dict(config=None, db=None, training=False, num_agents=0)),
    ("tools.dreaming_probe", "run_era_organ", {"target": "stoneage", "seed": 0, "organ_fraction": 0.5, "metab": 0.25, "payoff": 3.0, "num_agents": 0, "max_ticks": 400, "shared_db": None}),
    ("tools.evolve_ceiling_probe", "run_evolution", dict(target="stoneage", k_eras=2, num_agents=0, max_ticks=60, shared_db=None, preserve_dims=True, node_cap=512)),
    ("tools.evolve_competence", "run_era", dict(cfg=None, genomes=[], max_ticks=400)),
    ("tools.func_benefit", "run_seed", dict(config=None, db=None, seed=0, use_head=True, decode_act=True, num_agents=0)),
    ("tools.hcm_analyzer", "run_hcm_analysis", dict(num_ticks=0)),
    ("tools.hunif_retention_probe", "run_retention", dict(capability=True, cost=0.3, n_agents=0)),
    ("tools.lang_speciation", "run_seed", dict(config=None, db=None, speciate=False, seed=0, eras=0)),
    ("tools.life_score_contamination_probe", "run_arm", dict(num_agents=0)),
    ("tools.map_elites_compare", "run_era_pool", dict(cfg=None, genomes=[], max_ticks=0)),
    ("tools.map_elites_compare", "run_lineage_hof", dict(seed=0, eras=0)),
    ("tools.map_elites_compare", "run_lineage_qd", dict(seed=0, eras=0)),
    ("tools.metabolic_cost_sweep", "run_lineage", dict(seed=0, coef=0.0, eras=0)),
    ("tools.metabolic_cost_sweep", "run_era_metab", dict(cfg=None, genomes=[], max_ticks=0)),
    ("tools.nas_memory", "run_seed", dict(config=None, db=None, transient=True, seed=0, eras=0)),
    ("tools.nas_rich", "run_seed", dict(config=None, db=None, transient=True, seed=0, eras=0)),
    ("tools.online_world_model_probe", "run_online", dict(n_test=0)),
    ("tools.persistence_test", "run_era", dict(config=None, db=None, global_era=0, num_agents=0)),
    ("tools.planning_depth_probe", "run_depth", dict(n_test=0)),
    ("tools.probe_impasse", "run_era", dict(config=None, db=None, num_agents=0)),
    ("tools.reconfirm_047", "run_seed", dict(config=None, db=None, seed=0, eras=0)),
    ("tools.referential_community_probe", "run_community", dict(n_agents=0)),
    ("tools.referential_game_probe", "run_lewis", dict(n_agents=0)),
    ("tools.refgame", "run_refgame", dict(epochs=0)),
    ("tools.speciation", "run_seed", dict(config=None, db=None, speciate=False, seed=0, eras=0)),
    ("tools.substrate_ab", "run_substrate_ab", dict(backend="legacy", ticks=0)),
    ("tools.substrate_ab_compositional", "run_compositional", dict(backend="legacy", trials=0)),
    ("tools.substrate_ab_compositional", "run_curriculum", dict(backend="legacy", compo_trials=0)),
    ("tools.substrate_ab_compositional", "run_curriculum_fade", dict(backend="legacy", compo_trials=0)),
    ("tools.substrate_ab_compositional", "run_curriculum_fade_gated", {"backend": "torch", "compo_trials": 0}),
    ("tools.torch_binary_gate_heldout_probe", "run_arm", {"shuffle_reward": False, "train_ep": 0}),
    ("tools.torch_binary_gate_probe", "run_arm", {"gate_on": True, "n_agents": 0}),
    ("tools.torch_bptt_meansends", "run_meansends", {"mode": "bptt", "epochs": 0}),
    ("tools.torch_gate_bptt_meansends", "run_cell", {"mode": "bptt", "use_gate": True, "epochs": 0}),
    ("tools.torch_gate_persist_ab", "run_arm", {"persist": True, "n_agents": 0}),
    ("tools.torch_inworld_ab", "run_arm", dict(use_torch=False, seed=0, ticks=4, n_agents=0)),
    ("tools.torch_prod_gate_meansends", "run_prod", dict(use_gate=True, episodes=20, n_agents=0)),
    ("tools.torch_throw_gate_inworld_ab", "run_arm", dict(shuffle=False, seed=0, ticks=40, warmup=20, n_agents=0)),
    ("tools.warmstart_evolution_inworld", "run_bptt_imitation_warmstart", dict(seed=2026, num_agents=4, n_epochs=0)),
    ("tools.warmstart_evolution_inworld", "run_dagger_warmstart", dict(seed=2026, rounds=0, num_agents=4)),
    ("tools.wire_ref_head", "run_seed", dict(config=None, db=None, seed=0, use_head=False, num_agents=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_5)
def test_fifth_wave_run_family_REFUSES_degenerate_arguments(mod, nom, kw):
    """Meme principe que P2.34/P2.37/P2.40/P2.41 : 0 agent / 0 ere / 0 tick est une erreur d'APPEL."""
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_5)
def test_fifth_wave_guards_are_placed_BEFORE_the_world(mod, nom, kw):
    """PLACEMENT : le refutateur a verifie pour chacune que, SANS garde, l'appel degenere construit
    un monde complet (Biosphere3D(None) -> WorldConfig() par defaut) avant d'echouer ailleurs ou de
    rendre 0.0/nan -- un refus instantane prouve que la garde precede la construction."""
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


# ======================================================================================================
# P2.45 (2026-09-06) : les 6 DEFINITIONS HOMONYMES revelees par le correctif du faux vert par nom nu
# (`collision_coverage`). Elles etaient comptees calibrees parce qu'UN autre fichier du meme nom
# l'etait -- exactement le faux vert E4 que le cliquet est cense empecher.
# ======================================================================================================

_MESURES_GARDEES_6 = [
    ("tools.lewis_world", "measure_mi", dict(config=None, db=None, eras=0)),
    ("tools.target_competence_probe", "run_probe",
     dict(target="stoneage", k=0, num_agents=1, max_ticks=1, shared_db=None)),
    ("tools.vertical_world_probe", "run_probe", dict(genome=None, seeds=())),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_6)
def test_homonyms_REFUSE_degenerate_arguments(mod, nom, kw):
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_6)
def test_homonym_guards_are_placed_BEFORE_the_world(mod, nom, kw):
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


def test_lethality_verdict_READS_its_three_prewritten_branches():
    """Regle pre-enregistree (§4 du record) en forme close : sous la porte -> NEGATIF PROFOND ;
    p<0.05 ET mediane>0 ET borne basse>0 -> CASSE LE BOOTSTRAP ; sinon PAS LE GOULOT."""
    from tools.lethality_curriculum import _verdict, GATE
    assert _verdict(GATE, 0.001, 5.0, 1.0) == "NEGATIF PROFOND"          # <= GATE, quoi qu'il arrive
    assert _verdict(GATE + 1, 0.01, 5.0, 1.0) == "CASSE LE BOOTSTRAP"
    assert _verdict(GATE + 1, 0.20, 5.0, 1.0) == "PAS LE GOULOT"         # p trop grand
    assert _verdict(GATE + 1, 0.01, 5.0, -1.0) == "PAS LE GOULOT"        # borne basse <= 0


def test_capacity_verdict_READS_delta_and_slope_and_REFUSES_a_single_arm():
    """EDR110 : LEVE si delta>=0.10 ET pente>0 ; INERTE si |delta|<0.10 ET |pente|<0.05 ; AMBIGUE sinon.
    ⚠️ Un seul bras rendait INERTE (delta=0, pente=0) -- une affirmation de fond sur ZERO comparaison,
    le motif « donnees absentes -> negatif » : desormais un refus."""
    from tools.lewis_survival_sweep import _verdict_capacity
    A = lambda n, p: {"n_hidden": n, "plateau": p}
    assert _verdict_capacity([A(5, 0.20), A(20, 0.30), A(80, 0.40)]) == "CAPACITE LEVE"
    assert _verdict_capacity([A(5, 0.30), A(20, 0.31), A(80, 0.30)]) == "CAPACITE INERTE"
    # ⚠️ IDENTITE TROUVEE EN CALIBRANT (2026-09-06) : avec 3 bras EQUIDISTANTS en log2 (5/20/80, la
    # config canonique d'EDR110), la pente des moindres carres vaut EXACTEMENT delta/4 -- le bras du
    # milieu n'y entre pas. Consequences : (i) delta >= 0.10 => pente >= 0.025 > 0 => LEVE est FORCE,
    # la clause « ET pente > 0 » n'ajoute rien ; (ii) une non-monotonie pure (bosse : 0.20/0.45/0.20)
    # est lue INERTE, pas AMBIGUE -- l'instrument ne VOIT pas la bosse ; (iii) AMBIGUE n'est donc
    # atteignable que par delta <= -0.10, c'est-a-dire quand la capacite NUIT.
    assert _verdict_capacity([A(5, 0.20), A(20, 0.45), A(80, 0.20)]) == "CAPACITE INERTE"
    assert _verdict_capacity([A(5, 0.40), A(20, 0.30), A(80, 0.20)]) == "CAPACITE AMBIGUE"  # nuit
    with pytest.raises(ValueError, match="degenere"):
        _verdict_capacity([A(5, 0.30)])


def test_arc5_alignment_verdict_READS_mutual_information_it_computes(monkeypatch):
    """Orchestrateur : `collect` simule, `_verdict` agrege en MI vs baseline par permutation.
    INJECTION a dose connue : tokens parfaitement alignes sur un contexte binaire equilibre ->
    MI = 1 bit (forme close H(ctx)) et baseline ~0 ; tokens independants du contexte -> MI ~ baseline."""
    import numpy as np
    import tools.arc5_alignment as A
    ctx = [0, 1] * 200
    monkeypatch.setattr(A, "collect", lambda *a, **k: ([c for c in ctx], list(ctx)))
    np.random.seed(0)
    mi, base = A._verdict(None, None, "aligne", 0.0, 0.0)
    assert abs(mi - 1.0) < 0.05 and base < 0.05, (mi, base)
    rng = np.random.RandomState(1)
    monkeypatch.setattr(A, "collect", lambda *a, **k: (rng.randint(0, 2, size=400).tolist(), list(ctx)))
    mi2, base2 = A._verdict(None, None, "independant", 0.0, 0.0)
    assert mi2 < 0.05 and abs(mi2 - base2) < 0.05, (mi2, base2)


# ======================================================================================================
# P2.46 (2026-09-06) : les 11 ORCHESTRATEURS de la famille run_* -- dernier verrou avant l'elargissement
# du detecteur au motif `run_\\w+` generique. Ils n'entrainent pas eux-memes mais AGREGENT en verdict :
# une liste de seeds vide n'est pas « zero effet mesure », c'est un appel invalide.
# ⚠️ CE QUE CES CAS NE FONT PAS : ils ne testent AUCUNE branche de verdict. Les tests d'INJECTION a
# dose connue (monkeypatch de la fonction de run, cellules imposees, branches negatives) restent a
# ecrire pour ces 11 -- dette DECLAREE au backlog, pas masquee par une garde qui ne couvre que l'entree.
# ======================================================================================================

_MESURES_GARDEES_7 = [
    ("tools.cross_world_transfer", "run_direction", dict(source_label="a", source_hof="x.pkl", target_world="stoneage", k_eval=0)),
    ("tools.curriculum_transfer", "run_transfer_experiment", dict(seeds=())),
    ("tools.dreaming_probe", "run_q1", dict(seeds=(), target="stoneage", num_agents=4, max_ticks=10, shared_db=None)),
    ("tools.dreaming_probe", "run_q2", dict(seeds=(0,), target="stoneage", num_agents=0, max_ticks=10, shared_db=None)),
    ("tools.dream_causal_probe", "run_causal", dict(seeds=(), target="stoneage", num_agents=4, max_ticks=10, shared_db=None)),
    ("tools.dream_causal_probe", "run_founder_matched", dict(seeds=())),
    ("tools.dream_distress_probe", "run_distress", dict(seeds=(), target="stoneage", num_agents=4, max_ticks=10, shared_db=None)),
    ("tools.evo_memory_enrichment", "run_experiment", dict(seeds=(), K=4, D=2, generations=1, pop=4)),
    ("tools.evo_memory_inworld", "run_contrast", dict(seeds=())),
    ("tools.s2_demand", "run_s2", dict(num_agents=0)),
    ("tools.s2_openloop_probe", "run_openloop_ladder", dict(K=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_7)
def test_run_orchestrators_REFUSE_degenerate_arguments(mod, nom, kw):
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_7)
def test_run_orchestrator_guards_are_placed_BEFORE_the_runs(mod, nom, kw):
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


# --- 10e ELARGISSEMENT DU CLIQUET (2026-09-09) : le VERBE NU ----------------------------------------
# Tous les motifs exigeaient un SOUFFIXE (`run_\w+`, `compare_\w+`...), donc le verbe seul passait.
# Cout mesure AVANT application : +7 noms / +22 definitions. Ce que ca fait entrer n'est pas
# anecdotique : `compare` NU vit dans 10 fichiers, et deux de ses docstrings disent litteralement
# « verdict de learnabilite » (tools/substrate_ab.py) et « verdict de survie » (tools/torch_inworld_ab.py) --
# ils rendent `compute_ab_verdict`. Pire : dans `tools/substrate_ab_compositional.py`, `compare` nu
# coexistait avec `compare_gate_modes` CAPTURE, dans le meme fichier, depuis le 6e elargissement.
# 20 gardes posees dans la meme passe -> le cliquet reste STRICT, baseline a zero.
_MESURES_GARDEES_8 = [
    ("tools.anticipation_bench", "compare", dict(seeds=())),
    ("tools.life_score_contamination_probe", "compare", dict(seeds=())),
    ("tools.map_elites_compare", "compare", dict(seeds=())),
    ("tools.substrate_ab", "compare", dict(seeds=())),
    ("tools.substrate_ab_compositional", "compare", dict(seeds=())),
    ("tools.substrate_ab_compositional", "sweep", dict(seeds=())),
    ("tools.torch_binary_gate_heldout_probe", "compare", dict(seeds=())),
    ("tools.torch_binary_gate_probe", "compare", dict(seeds=())),
    ("tools.torch_gate_persist_ab", "compare", dict(seeds=())),
    ("tools.torch_inworld_ab", "compare", dict(seeds=())),
    ("tools.torch_throw_gate_inworld_ab", "compare", dict(seeds=())),
    ("tools.lexicon", "measure", dict(config=None, db=None, eras=0)),
    ("tools.speaker_incentive", "measure", dict(config=None, db=None, eras=0)),
    ("tools.transfer_ratio", "measure", dict(prev=None, target=None, repeats=0)),
    ("tools.anticipation_demand_world_probe", "probe",
     dict(body_gain=0.0, cog_gain=0.0, currency="survival", shift=1, K=0, seed=0)),
    ("tools.composition_demand_world_probe", "probe",
     dict(body_gain=0.0, cog_gain=0.0, currency="survival", chain_len=2, K=0, seed=0)),
    ("tools.memory_demand_world_probe", "probe",
     dict(body_gain=0.0, cog_gain=0.0, currency="survival", recall=1, K=0, seed=0)),
    ("tools.generalization_transfer_probe", "run", dict(K=0, seed=0)),
    ("tools.memory_payoff_probe", "run", dict(K=0, delay=1, lam=0.0, seed=0)),
    ("tools.s2_fallback_rate_probe", "measured_floor", dict(cell=None, seed=0, n_eval=0)),
]


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_8)
def test_the_BARE_VERB_instruments_REFUSE_a_degenerate_argument(mod, nom, kw):
    """Ils prononcent des verdicts (learnabilite, survie, binding_gap, comp_rate, plancher) et
    n'avaient AUCUNE garde : une cohorte vide leur faisait rendre 0.0 / nan / {} que l'aval lit comme
    une mesure. C'est la direction CONSTANTE des defauts de ce depot : absence -> negatif de fond."""
    import importlib
    f = getattr(importlib.import_module(mod), nom)
    with pytest.raises(ValueError, match="degenere"):
        f(**kw)


@pytest.mark.parametrize("mod,nom,kw", _MESURES_GARDEES_8)
def test_the_BARE_VERB_guards_are_placed_BEFORE_any_world(mod, nom, kw):
    """On ne teste pas QUE la garde leve, on teste OU elle est posee : un refus doit etre instantane.
    Sans ce second cas, une garde placee apres la construction du monde passerait le premier."""
    import importlib
    import time
    f = getattr(importlib.import_module(mod), nom)
    t0 = time.time()
    with pytest.raises(ValueError):
        f(**kw)
    assert time.time() - t0 < 0.5, f"{nom} refuse trop lentement : la garde est posee trop bas"


# ======================================================================================================
# P2.52 (b) (2026-09-09) : `tools/demand_marker.py::ablation_verdict` -- L'INSTRUMENT FONDATIONNEL.
# 11 records citent ce module, pour DEUX sites de defaut fabrique seulement : le meilleur rapport
# records/site du depot, donc la premiere cible de l'item (b).
#
# MESURE : `ablation_verdict([50]*12, [0]*12)` rend **X_DEMANDED avec ratio = 5.0e10** et
# `degenerate=False`. Le SIGNE est REEL -- une cohorte ablatee qui s'eteint face a un intact qui
# survit EST le contraste le plus tranche qui soit, et le verdict, qui ne lit qu'un SEUIL, reste
# valide. Mais l'AMPLITUDE est fixee par `eps`, pas par le monde : 50 / 1e-9.
#
# Le depot avait DEJA tranche ce cas exact dans `cross_world_transfer` -- « on ne le corrige pas en
# silence, on l'ANNONCE » (`n_denominateurs_eteints`). L'instrument FONDATIONNEL ne l'avait pas.
# ======================================================================================================

def test_ablation_verdict_ANNOUNCES_that_an_extinct_denominator_makes_the_ratio_a_BOUND():
    """⚠️ LE CAS QUI COMPTE. Bras ablate ETEINT : le verdict tient (le signe est reel), mais le ratio
    doit etre annonce comme une BORNE. Un record qui cite « ratio = 5e10 » citerait sinon un artefact
    d'epsilon comme une mesure du monde."""
    from tools.demand_marker import ablation_verdict
    v = ablation_verdict([50.0] * 12, [0.0] * 12)
    assert v["verdict"] == "X_DEMANDED", "le SIGNE est reel : le verdict ne doit PAS etre annule"
    assert v["denominateur_eteint"] is True
    assert v["ratio_est_une_borne"] is True, (
        "le ratio vaut med_i/eps : il est fixe par epsilon, pas par le monde")


def test_ablation_verdict_does_NOT_cry_bound_on_an_ORDINARY_contrast():
    """NO-OP APPARIE, indispensable : un drapeau leve en permanence ne distingue rien, et serait
    ignore des la premiere lecture. Sur un contraste ordinaire (50 vs 25), le ratio EST une mesure."""
    from tools.demand_marker import ablation_verdict
    v = ablation_verdict([50.0] * 12, [25.0] * 12)
    assert v["verdict"] == "X_DEMANDED" and v["ratio"] == pytest.approx(2.0)
    assert v["denominateur_eteint"] is False and v["ratio_est_une_borne"] is False


def test_ablation_verdict_makes_an_EMPTY_arm_VISIBLE():
    """Un bras VIDE produisait une mediane de 0.0, donc un ratio PUBLIE alors qu'aucune comparaison
    n'avait eu lieu. Le VERDICT etait deja protege -- `n = min(len, len) = 0 < n_floor` -- mais le
    ratio, non. Les comptes par bras rendent l'absence visible au lieu de la laisser deviner."""
    from tools.demand_marker import ablation_verdict
    v = ablation_verdict([50.0] * 12, [])
    assert v["verdict"] == "INCONCLUSIVE", "le plancher de puissance protege deja le verdict"
    assert v["n_intact"] == 12 and v["n_ablated"] == 0
    assert v["bras_vide"] is True and v["ratio_est_une_borne"] is True


def test_the_CENSORED_case_is_also_a_BOUND_and_was_already_known():
    """Le depot savait deja qu'un intact CENSURE au plafond rend le ratio sous-estime -- « le ratio
    est une borne INFERIEURE », dit sa docstring. Ce cas verifie que le nouveau drapeau REJOINT ce
    savoir au lieu de le dupliquer : censure => borne, sans exception."""
    from tools.demand_marker import ablation_verdict
    v = ablation_verdict([300.0] * 12, [100.0] * 12, ceiling=300.0)
    assert v["censored"] is True and v["ratio_est_une_borne"] is True


# ==================================================================================================
# P2.56 (2026-09-14) -- une cle en DOUBLE dans `CALIBRATED` est une declaration ECRASEE sans un mot
# ==================================================================================================

def _cles_litterales(nom_variable):
    """Les cles TELLES QU'ECRITES dans le source, par AST -- le dict a l'execution ne peut plus les
    voir : Python garde la DERNIERE et jette les autres en silence."""
    import ast
    import io
    src = io.open(__file__, encoding="utf-8").read()
    for n in ast.walk(ast.parse(src)):
        if (isinstance(n, ast.Assign) and any(isinstance(x, ast.Name) and x.id == nom_variable
                                              for x in n.targets)):
            conteneur = n.value
            noeuds = conteneur.keys if isinstance(conteneur, ast.Dict) else conteneur.elts
            return [k.value for k in noeuds if isinstance(k, ast.Constant)]
    raise AssertionError(f"{nom_variable} introuvable dans {__file__}")


def test_CALIBRATED_n_a_AUCUNE_cle_en_double():
    """CONTRE-EXEMPLE MESURE le 2026-09-14 : `tools/hcm_analyzer.py::run_hcm_analysis` etait declare
    DEUX fois -- une version RICHE (CORPS-ATTEINT, 4 cas) puis, 220 lignes plus bas, une version
    PAUVRE (`["empty-cohort:raises", "guard-before-world"]`). Dans un dict litteral la derniere cle
    gagne : c'est la version pauvre qui faisait foi, et l'instrument comptait comme GARDE-SEULE dans
    la dette P2.49 alors qu'il etait calibre. Un second doublon (`run_curriculum` du banc G2) avait
    des valeurs identiques, donc aucun effet -- jusqu'a ce que quelqu'un en mette une a jour et pas
    l'autre. Deux doublons sur 273 cles, trouves parce qu'on en avait cherche UN.
    ⚠️ Aucun cliquet ne pouvait le voir : `scan_calibrated` lit le dict EVALUE, ou le doublon n'existe
    plus. Seul le SOURCE le porte, d'ou l'AST."""
    from collections import Counter
    for nom in ("CALIBRATED", "NOT_AN_INSTRUMENT"):
        cles = _cles_litterales(nom)
        doubles = {k: v for k, v in Counter(cles).items() if v > 1}
        assert not doubles, (
            f"{nom} : cle(s) declaree(s) PLUSIEURS fois -- seule la DERNIERE compte, les autres "
            f"sont jetees sans un mot : {doubles}")
        assert len(cles) > 0, f"{nom} vide : le detecteur d'AST n'a rien lu"


# ======================================================================================================
# P1.6 (2026-09-14) — L'APPRENANT IN-WORLD EST UN INSTRUMENT : contrôle positif à DOSE PUBLIÉE.
#
# Les nuls « le crédit n'apprend pas à froid » (S2-009 §crédit, S2-010, S2-011) ont été publiés sans
# compter la dose reçue (≈ 48 mises à jour par agent, panel du 2026-09-14) et sans contrôle positif de
# l'apprenant lui-même. `run_learner_probe` mesure, sur une cohorte IMMORTELLE (l'énergie est remise à
# 80 sous 30 : la récompense n'est jamais écrêtée par la mort), le taux de coups d'une politique sur la
# tâche linéaire 1-bit de S2-011, par blocs de ticks, avec la dose comptée par
# `tools/learning_events.count_learning_events`. Ses réponses connues : l'ORACLE câblé touche à 1.0
# exactement ; le bras `lr=0` ne bouge AUCUN poids (c'est le plafond de l'incapable, mesuré dans le
# même dispositif — jamais importé, jamais « chance + marge ») ; la dose délivrée est exactement celle
# que la mécanique du monde prévoit (un TD par tick, un épisode tous les `torch_episode_k` ticks).
# `learner_verdict` lit ces mesures et REFUSE de conclure quand le contrôle positif ou la référence
# sont hors bornes — jamais une affirmation de fond sur une entrée absente (porte 14).
# ======================================================================================================

def _learner(**kw):
    from tools.cognitive_demand_inworld import run_learner_probe
    base = dict(seed=2026, num_agents=6, ticks=40, block=20)
    base.update(kw)
    return run_learner_probe(**base)


def test_run_learner_probe_refuses_degenerate_args_before_any_world():
    import time
    from tools.cognitive_demand_inworld import run_learner_probe
    t0 = time.time()
    with pytest.raises(ValueError):
        run_learner_probe(seed=1, num_agents=0, ticks=40, block=20)
    with pytest.raises(ValueError):
        run_learner_probe(seed=1, num_agents=6, ticks=0, block=20)
    with pytest.raises(ValueError):
        run_learner_probe(seed=1, num_agents=6, ticks=40, block=0)
    assert time.time() - t0 < 0.5, "la garde doit refuser AVANT de construire un monde"


def test_run_learner_probe_oracle_is_the_positive_control_of_the_dv():
    r = _learner(policy="oracle")
    assert [b["hit_rate"] for b in r["blocks"]] == [1.0, 1.0], "l'oracle câblé touche à 1.0 EXACTEMENT"
    assert r["hit_first"] == 1.0 and r["hit_last"] == 1.0
    assert r["learning"]["td_calls"] == 0 and r["learning"]["episode_calls"] == 0, "aucune population torch"


def test_run_learner_probe_counts_the_dose_the_world_delivers():
    r = _learner(policy="torch")
    lrn = r["learning"]
    assert lrn["td_calls"] == 40, "un TD par tick sur une cohorte immortelle (population constante)"
    assert lrn["td_updates"] == 39, "le premier learn d'une vie est différé"
    assert lrn["episode_calls"] + sum(lrn["skips"].values()) == 40 // 8, "un épisode tous les torch_episode_k ticks"
    assert r["chance"] == pytest.approx(1.0 / 8.0)
    assert all(b["n_agents"] == 6 for b in r["blocks"]), "immortelle : personne ne meurt"


def test_run_learner_probe_immortal_cohort_stays_complete_under_learning():
    """Mesuré sur le run P1.6 v1 (2026-09-14, 12 seeds) : avec une recharge d'ÉNERGIE seule, les bras
    APPRENANTS perdaient jusqu'à la moitié de leur cohorte dès le premier bloc (seed 2027 : 12 -> 9 à 400
    ticks, 3 à 800) alors que les bras lr=0 et oracle en gardaient 11 — le taux de coups des blocs tardifs
    portait donc un biais de SURVIVANTS corrélé au bras. Immortel veut dire immortel : l'énergie ET les hp
    sont rechargés, et la cohorte reste COMPLÈTE sous apprentissage. Ce cas rejoue la cellule qui a révélé
    le défaut (seed 2027, apprenant naturel, 400 ticks)."""
    r = _learner(seed=2027, num_agents=12, ticks=400, block=200, policy="torch")
    assert [b["n_agents"] for b in r["blocks"]] == [12, 12], r["blocks"]
    assert r["resurrections"] >= 1, "sur cette cellule le monde TUE (v1 : 12 -> 9) ; l'immortalité doit avoir agi"
    assert r["learning"]["td_calls"] == 400 and r["learning"]["td_updates"] <= 399


def test_run_learner_probe_lr0_reference_moves_no_weight():
    r = _learner(policy="torch", lr=0.0)
    assert r["learning"]["dW_abs_sum"] == 0.0, "lr=0 : le plafond de l'incapable, mesuré dans le dispositif"
    assert r["learning"]["td_updates"] > 0, "…mais les updates ont bien eu lieu (ce n'est pas TD coupé)"


def test_run_learner_probe_is_reproducible_at_fixed_seed():
    a = _learner(policy="torch")
    b = _learner(policy="torch")
    assert a["blocks"] == b["blocks"]
    assert a["learning"] == b["learning"]


def test_run_learner_probe_publishes_its_variant():
    r = _learner(policy="torch", reward_scale=0.05, td_enabled=False, lr=0.004)
    assert r["learning"]["reward_scale"] == 0.05
    assert r["learning"]["td_enabled"] is False
    assert r["learning"]["lr"] == 0.004
    assert r["learning"]["td_updates"] == 0 and r["learning"]["skips"].get("td_disabled") == 40
    assert r["policy"] == "torch" and r["immortal"] is True


def test_learner_verdict_refuses_missing_inputs():
    from tools.cognitive_demand_inworld import learner_verdict
    for bad in (None, float("nan")):
        with pytest.raises(ValueError):
            learner_verdict(learner_first=bad, learner_last=0.3, reference_last=0.2, oracle_last=1.0)
        with pytest.raises(ValueError):
            learner_verdict(learner_first=0.2, learner_last=0.3, reference_last=bad, oracle_last=1.0)


def test_learner_verdict_indeterminate_when_harness_controls_fail():
    from tools.cognitive_demand_inworld import learner_verdict
    v = learner_verdict(learner_first=0.2, learner_last=0.6, reference_last=0.2, oracle_last=0.7)
    assert v["verdict"] == "INDETERMINE_HARNAIS" and "oracle" in v["why"]
    v = learner_verdict(learner_first=0.2, learner_last=0.6, reference_last=0.55, oracle_last=1.0)
    assert v["verdict"] == "INDETERMINE_HARNAIS" and "reference" in v["why"]


def test_learner_verdict_inert_and_learns_are_separated_by_the_paired_reference_only():
    """Le critère est la SÉPARATION à la référence lr=0 du MÊME seed (mêmes génomes initiaux : `seed_at`
    précède la création des agents, et l'override `lr` ne consomme aucun tirage). Une cohorte FRAÎCHE ne
    peut être « déjà au-dessus au départ » que parce qu'elle a APPRIS dans le premier bloc : le gain
    intra-run ne décide donc pas du verdict, il date seulement l'apprentissage (`onset`). Règle corrigée
    le 2026-09-14 après le seed 1/12 du run P1.6 (lr=0,004 à 0,32 dès le bloc 1 contre 0,15 pour lr=0) —
    déclaré ici, pas caché : la version d'origine rendait INDETERMINATE dans ce cas."""
    from tools.cognitive_demand_inworld import learner_verdict
    inert = learner_verdict(learner_first=0.20, learner_last=0.21, reference_last=0.20, oracle_last=1.0)
    assert inert["verdict"] == "LEARNER_INERT"
    learns = learner_verdict(learner_first=0.20, learner_last=0.45, reference_last=0.20, oracle_last=1.0)
    assert learns["verdict"] == "LEARNER_LEARNS" and learns["sep"] == pytest.approx(0.25)
    assert learns["onset"] == "during_run"
    early = learner_verdict(learner_first=0.44, learner_last=0.45, reference_last=0.20, oracle_last=1.0)
    assert early["verdict"] == "LEARNER_LEARNS" and early["onset"] == "early", "appris dans le premier bloc"
    assert "LEARNER_INDETERMINATE" not in (inert["verdict"], learns["verdict"], early["verdict"])


# Les TROIS sondes crédit publiées (S2-009 §crédit, S2-010, S2-011) publient désormais leur DOSE. Le
# chemin par défaut est bit-identique (prouvé au niveau du modèle dans test_learning_events.py) : ici
# on vérifie seulement que la dose est PUBLIÉE et cohérente avec la mécanique (un TD par tick vivant,
# un update de moins par population construite — le premier learn d'une vie est différé).

def _dose_is_coherent(lrn, max_ticks_total):
    assert 1 <= lrn["td_calls"] <= max_ticks_total, lrn
    assert 0 <= lrn["td_updates"] < lrn["td_calls"], lrn
    assert lrn["episode_calls"] + sum(lrn["skips"].values()) <= lrn["td_calls"] // 8 + 1, lrn
    assert lrn["reward_scale"] == 1.0 and lrn["td_enabled"] is True and lrn["lr"] is None, "variante par défaut publiée"


def test_run_credit_linear_publishes_its_learning_dose():
    from tools.cognitive_demand_inworld import run_credit_linear
    r = run_credit_linear(seed=2026, eras=1, num_agents=3, max_ticks=20)
    assert isinstance(r["trend"], list) and len(r["trend"]) == 1
    _dose_is_coherent(r["learning"], 20)


def test_run_credit_probe_publishes_its_learning_dose_without_changing_its_return():
    from tools.cognitive_demand_inworld import run_credit_probe
    out = {}
    trend = run_credit_probe(seed=2026, eras=1, num_agents=3, max_ticks=20, learning_out=out)
    assert isinstance(trend, list) and len(trend) == 1, "le type de retour publié (liste) est INCHANGÉ"
    _dose_is_coherent(out, 20)


def test_run_warmstart_credit_probe_publishes_its_learning_dose():
    from tools.cognitive_demand_inworld import run_warmstart_credit_probe
    r = run_warmstart_credit_probe(seed=2026, num_agents=3, max_ticks=20, schedule=[(0.25, 12.0)])
    assert len(r["trend"]) == 1 and "learned" in r
    _dose_is_coherent(r["learning"], 20)


# ==================================================================================================
# P3.4 (2026-09-15) -- calibration de l'apprenant LEGACY `MambaBatchModel.compute_policy_gradient`.
# Actor-Critic TD(0) numpy : au tick t+1, delta = r + gamma*V(s') - V(s) credite l'action CHOISIE au
# tick t. Le monde recree le modele a chaque tick : W est persiste dans `agent.genome.W`.
# ==================================================================================================

def _legacy_one(seed=5, move=2):
    from src.agents.mamba_agent import MambaAgent, MambaBatchModel
    np.random.seed(seed)
    a = MambaAgent()
    m = MambaBatchModel([a])
    obs = np.random.RandomState(seed).uniform(-1.0, 1.0, (1, a.genome.num_inputs)).astype(np.float32)
    act = [{"move": move, "grab": 0, "rub": 0}]
    return a, m, obs, act


def test_compute_policy_gradient_first_call_is_deferred_and_second_call_updates():
    a, m, obs, act = _legacy_one()
    W0 = np.array(a.genome.W, copy=True)
    m.forward(obs); m.compute_policy_gradient(np.array([1.0], dtype=np.float32), act)
    assert np.array_equal(a.genome.W, W0), "tick 1 : V(s') inconnu, aucune mise a jour"
    m.forward(obs); m.compute_policy_gradient(np.array([1.0], dtype=np.float32), act)
    assert not np.array_equal(a.genome.W, W0), "tick 2 : la transition differee est creditee"


def test_compute_policy_gradient_update_sign_is_predicted_by_the_TD_error():
    """PREDICTION : la colonne du logit de l'action CHOISIE bouge dans le sens de sign(delta * h) pour
    tout noeud presynaptique h != 0 (REINFORCE : grad = (1 - pi[move]) > 0 sur l'action jouee). On
    impose delta > 0 avec une grosse recompense, puis delta < 0 avec une grosse penalite : les deux
    signes sont produits (l'instrument peut rendre les DEUX issues), et chacun est celui predit."""
    from src.agents.mamba_agent import MambaBatchModel
    for reward, sign in ((50.0, +1.0), (-50.0, -1.0)):
        a, m, obs, act = _legacy_one(move=2)
        m.forward(obs); m.compute_policy_gradient(np.array([reward], dtype=np.float32), act)
        W0 = np.array(a.genome.W, copy=True)
        h = np.asarray(a._td["h"], dtype=np.float64)
        N_i, O_i = a.genome.num_nodes, a.genome.num_outputs
        col = N_i - O_i + 2                                   # noeud de sortie du move 2
        m.forward(obs); m.compute_policy_gradient(np.array([reward], dtype=np.float32), act)
        dcol = np.asarray(a.genome.W, dtype=np.float64)[:, col] - W0[:, col]
        live = np.abs(h) > 1e-6
        assert live.sum() >= 3, "il faut des presynaptiques actifs pour lire un signe"
        # sur les noeuds actifs dont le poids n'est pas au CLIP (+-5), le signe est exactement predit
        unclipped = live & (np.abs(W0[:, col]) < 4.9)
        assert unclipped.sum() >= 3
        assert np.all(np.sign(dcol[unclipped]) == sign * np.sign(h[unclipped])), (reward, dcol[unclipped][:5])
    assert (MambaBatchModel.LR_ACTOR, MambaBatchModel.LR_CRITIC) == (0.04, 0.05)


def test_compute_policy_gradient_lr_zero_is_the_same_code_at_null_step():
    """Le plafond de l'incapable (bras `lr0_reference` de P3.4) : meme chemin, pas nul, W bit-identique
    et transition tout de meme enregistree."""
    from src.agents.mamba_agent import MambaBatchModel
    a, m, obs, act = _legacy_one()
    W0 = np.array(a.genome.W, copy=True)
    MambaBatchModel.LR_ACTOR, MambaBatchModel.LR_CRITIC = 0.0, 0.0
    try:
        for _ in range(3):
            m.forward(obs); m.compute_policy_gradient(np.array([7.0], dtype=np.float32), act)
    finally:
        MambaBatchModel.LR_ACTOR, MambaBatchModel.LR_CRITIC = 0.04, 0.05
    assert np.array_equal(a.genome.W, W0)
    assert getattr(a, "_td", None) is not None


def test_run_learner_probe_accepts_the_legacy_policy_and_counts_its_dose():
    """Le seam `policy=\"legacy\"` de `run_learner_probe` : la dose legacy est COMPTEE (un appel par tick,
    un update par tick apres le premier) et le chemin torch n'est PAS touche. Fumee courte (20 ticks)."""
    from tools.cognitive_demand_inworld import run_learner_probe
    r = run_learner_probe(seed=2026, num_agents=3, ticks=20, block=10, policy="legacy")
    assert r["policy"] == "legacy"
    L = r["learning"]
    assert L["legacy_calls"] == 20, L
    assert L["legacy_updates"] >= 18, L
    assert L["td_calls"] == 0 and L["episode_calls"] == 0, "le chemin torch ne doit pas etre appele"
    assert L["dW_abs_sum"] > 0.0
    assert len(r["blocks"]) == 2 and 0.0 <= r["hit_last"] <= 1.0


def test_baseline_compute_policy_gradient_is_a_proven_noop():
    """P3.4 : `BaselineBatchModel.compute_policy_gradient` est un no-op -- W bit-identique, pas seulement
    « ne leve pas » (le seul cas existant, test_baseline_models.py)."""
    from src.agents.baseline_models import ReflexBatchModel
    from src.agents.mamba_agent import MambaAgent
    np.random.seed(9)
    a = MambaAgent()
    bm = ReflexBatchModel([a])
    W0 = np.array(a.genome.W, copy=True)
    obs = np.zeros((1, a.genome.num_inputs), dtype=np.float32)
    bm.forward(obs)
    bm.compute_policy_gradient(np.array([50.0], dtype=np.float32), [{"move": 1, "grab": 1, "rub": 0}])
    assert np.array_equal(a.genome.W, W0)


def test_ablation_compute_policy_gradient_delegates_to_the_inner_model():
    """P3.4 : `PerceptionAblatedMamba.compute_policy_gradient` DELEGUE a l'interne, arguments intacts."""
    import src.agents.ablation_models as am
    cls = [c for c in vars(am).values() if isinstance(c, type) and c.__module__ == am.__name__
           and "compute_policy_gradient" in vars(c)]          # classes DEFINIES la, pas importees
    assert cls, "aucune classe d'ablation ne definit compute_policy_gradient"
    calls = []

    class _Inner:
        def compute_policy_gradient(self, *a, **k):
            calls.append((a, k)); return "delegue"

    obj = object.__new__(cls[0])
    obj._inner = _Inner()
    r = cls[0].compute_policy_gradient(obj, "R", "A", extra=1)
    assert r == "delegue" and calls == [(("R", "A"), {"extra": 1})]


def test_cause_de_mort_classifies_energy_hp_both_and_REFUSES_to_name_a_cause_for_a_living_agent():
    """P2.72 (b) : la cause de mort compte AVANT la recharge ; un agent vivant rend AUCUNE, jamais une cause."""
    from tools.cognitive_demand_inworld import _cause_de_mort
    assert _cause_de_mort({"energy": -3.0, "hp": 40.0}) == "energie_epuisee"
    assert _cause_de_mort({"energy": 12.0, "hp": 0.0}) == "hp_epuise"
    assert _cause_de_mort({"energy": 0.0, "hp": -5.0}) == "les_deux"
    assert _cause_de_mort({"energy": 30.0, "hp": 60.0}) == "AUCUNE"


def test_compute_policy_gradient_SKIPS_and_COUNTS_a_non_finite_update_instead_of_poisoning_W():
    """E28 (2026-09-15) : un dW non fini traversait `np.clip` (qui ne retire PAS les NaN) et W devenait NaN
    pour toujours ; le monde convertissait ensuite ce NaN en mort a chaque tick (`max(0.0, nan)` = 0.0) —
    663/669 morts d'une cohorte immortelle a lr 0,04 avaient un W non fini. Desormais : compte + saut.
    NO-OP apparie : une recompense finie met a jour W exactement comme avant."""
    from src.agents.mamba_agent import MambaBatchModel
    a, m, obs, act = _legacy_one(seed=7)
    MambaBatchModel.ABLATE_NTM = True          # W n'a plus qu'UN auteur ici : le gradient (cf. E8 occ. 5)
    try:
        # la transition memorisee au tick t est creditee au tick t+1 : une recompense NaN au tick t donne
        # un delta NaN au tick t+1
        m.forward(obs); m.compute_policy_gradient(np.array([np.nan], dtype=np.float32), act)
        W0 = np.array(a.genome.W, copy=True)
        m.forward(obs); m.compute_policy_gradient(np.array([1.0], dtype=np.float32), act)   # delta = NaN ici
        assert np.array_equal(a.genome.W, W0), "un dW non fini ne doit PAS toucher W"
        assert np.isfinite(a.genome.W).all() and getattr(a, "_td_nan_skips", 0) == 1
        m.forward(obs); m.compute_policy_gradient(np.array([1.0], dtype=np.float32), act)   # delta fini
        assert not np.array_equal(a.genome.W, W0) and np.isfinite(a.genome.W).all()
        assert a._td_nan_skips == 1
    finally:
        MambaBatchModel.ABLATE_NTM = False


def test_run_learner_probe_publishes_the_price_of_computation_next_to_the_dose():
    """P4.14 (ADR-005 item 4) : « glia » = une publication -- `compute_spent_total` (compteur) et `brain_cost_total`
    (puits `brain` d'EDR-099, lu sur le monde avec trace_energy_sinks) a cote de la dose, plus la part du cerveau
    dans l'energie perdue. Fumee : 20 ticks, 3 agents. Le monde ne change pas (bit-identite de la DV verifiee
    hors test sur 400 ticks : hit_rate 0,20635..., n_decisions 4 754, seed 2026 lr 0,001)."""
    from tools.cognitive_demand_inworld import run_learner_probe
    r = run_learner_probe(seed=2026, num_agents=3, ticks=20, block=10, policy="legacy")
    g = r["glia"]
    assert set(g) == {"compute_spent_total", "brain_cost_total", "energie_perdue_total", "brain_share"}
    assert g["brain_cost_total"] >= 0.0 and g["energie_perdue_total"] > 0.0
    assert 0.0 <= g["brain_share"] < 0.05, "le cerveau coute ~0,1 % du drain (EDR-099) ; ici un plafond large"
    assert r["learning"]["forward_calls"] == 20 and r["learning"]["compute_spent_total"] >= 0.0
