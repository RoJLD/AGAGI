# -*- coding: utf-8 -*-
"""
src/seed_ai/harness_pieces.py — Registre de pièces du harnais (ADR-004 §2.2, ADR-005 §Conséquences).

Données PURES : aucun `import torch`, aucun `import tools.*` au niveau module (ce fichier doit rester
importable sans backend, sans monde, depuis un test qui vérifie juste le registre). `PIECES` recopie la
table du spec `docs/superpowers/specs/2026-09-16-harness-contracts-design.md` §2.2, colonne par colonne,
mise à jour par les mesures faites depuis (sham bilinéaire P4.12, deux lignes ADR-005 P4.11/P4.13) —
voir `docs/REF/REF-HARNESS-PIECES.md` pour la table publiée (générée depuis CE fichier, jamais recopiée).

Statut (`PIECE_STATUS`) : **R1** = première cellule de contrôle positif (§2.4 du spec) ; **R2** =
semaines 6-8 ; **attend** = n'entre en cellule de nécessité qu'avec son billet d'entrée payé (règle E2) ;
**hors_v1** = mécanisme in-world existant, hors périmètre CPU-pur du harnais ; **hors_registre** = cas
gelé (chemin de crédit mesuré INERTE, ne peut pas encore porter de verdict de nécessité).

`check_pieces_registry` est le test du registre annoncé au spec §2.2 : toute pièce citée par un Learner
accepté doit exister ici, et une pièce dont `in_repo_today` commence par "absent" (aucune forme dans le
dépôt : le billet d'entrée E2 n'est pas payé) ne peut être citée par aucun Learner.
"""
from src.seed_ai.harness_learner import Piece

PIECES: dict = {
    "bilinear": Piece(
        name="bilinear",
        artificial_form="((H·U)⊙(H·V))·W_bl rang 16 dans _step (src/agents/backend_torch.py:111-131), "
                         "flag de classe BILINEAR",
        biological_analogue="intégration dendritique multiplicative / coïncidence NMDA ; le rang et U/V "
                             "n'ont pas de correspondant biologique. Lésion prédite : blocage des spikes "
                             "NMDA abolit les conjonctions, pas la détection de traits",
        analogue_solidity="moyenne",
        bio_lesion_prediction="blocage des spikes NMDA abolit les conjonctions, pas la détection de traits",
        capacity_served="composition (q+key)%K",
        without={"bilinear": False},
        dose_matched=True,
        matched_sham={"bilinear_sham": True},
        in_repo_today=(
            "plain 0,271 vs bilinéaire 0,932, 0/144, n=12, 300 ép. (results/bilinear_composition.json) ; "
            "mais forme close plain 34/36 = 0,944 > 0,932 (tools/plain_substrate_ceiling.py:155) : "
            "nécessité d'ACQUISITION à dose, pas de représentation ; sham linéaire apparié (P4.12, "
            "results/bilinear_sham_r1.json) : plain 0,270 / sham 0,315 / bilinéaire 0,934 à lr 0,02 ; "
            "0,180 / 0,189 / 0,413 à 0,002 ; lecture scellée SHAM_PARTIEL (8/12) — le sham est AFFINE "
            "(H·(U+V)·W_bl) ; la nécessité de la MULTIPLICATION n'est PAS ÉTABLIE par la lecture scellée"
        ),
    ),
    "recurrent_state": Piece(
        name="recurrent_state",
        artificial_form="H porté : H' = (1−δ)H + δ·tanh(H·W_off), δ = σ(diag W) "
                         "(src/agents/backend_torch.py:119-132)",
        biological_analogue="activité persistante préfrontale, mémoire de travail — solide "
                             "fonctionnellement, aucune correspondance au mécanisme",
        analogue_solidity="solide",
        bio_lesion_prediction="dlPFC abolit le rappel différé, pas l'immédiat",
        capacity_served="rétention D ≥ 1",
        without={"feedforward": True},
        dose_matched=True,
        matched_sham=None,
        in_repo_today=(
            "LOCK-002 : 0,814/0,168 = 4,85x, n=12, SURGICAL fuite 0,028 (REINFORCE D=2, 14 400 ép.) ; "
            "2-pas supervisé : 0,923 à lr 0,002/600 ép. (results/retain_compose_lr_replication.json)"
        ),
    ),
    "bptt_credit": Piece(
        name="bptt_credit",
        artificial_form="graphe retenu à travers les pas (imitate_episode_bptt :263, "
                         "learn_episode_bptt truncate=False :230)",
        biological_analogue="traces d'éligibilité / synaptic tagging (moyenne) ; BPTT lui-même : aucune "
                             "correspondance biologique",
        analogue_solidity="moyenne",
        bio_lesion_prediction=None,
        capacity_served="écriture apprise dans la mémoire (verrou LOCK-001)",
        without={"truncate": True},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="RETAIN-COMPOSE-LR : 0,173 → 0,923 au seul lr (E19) ; nécessité NON établie",
    ),
    "td_critic": Piece(
        name="td_critic",
        artificial_form="value head nœud 28, δ = r + γV(s') − V(s) (src/agents/backend_torch.py:174-229)",
        biological_analogue="erreur de prédiction de récompense dopaminergique (Schultz)",
        analogue_solidity="solide",
        bio_lesion_prediction="VTA/SNc abolit l'apprentissage instrumental, pas l'exécution",
        capacity_served="crédit temporel dense",
        without={"td_enabled": False},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="CALIB-LEARNER : td_off -0,046 (2/12) ; P4.9 en cours — attend une Task à récompense scalaire",
    ),
    "condition_gate": Piece(
        name="condition_gate",
        artificial_form="readout de H biaisant le logit cible (src/agents/backend_torch.py:48-53, 134-149)",
        biological_analogue="gating go/no-go ganglions de la base",
        analogue_solidity="moyenne",
        bio_lesion_prediction=None,
        capacity_served="binding means→ends",
        without={"CONDITION_GATE": False},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="EDR-129/136/148 : suffisant en proxy ; nécessité à dose appariée jamais mesurée",
    ),
    "warm_start_prior": Piece(
        name="warm_start_prior",
        artificial_form="init depuis bassin DAgger / HoF vs 0.1·randn (src/agents/backend_torch.py:113-115)",
        biological_analogue="pré-câblage génomique, périodes critiques (Zador 2019)",
        analogue_solidity="solide",
        bio_lesion_prediction=None,
        capacity_served="bootstrap ; rétention du bassin",
        without={"init": "random"},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="loi warm-start (6 fils) ; S2-CREDIT-RETENTION : le crédit érode 36 → 8, 12/12",
    ),
    "neuromod_plasticity": Piece(
        name="neuromod_plasticity",
        artificial_form="règle à 3 facteurs ΔW = η·m(t)·pre⊗post, m(t) readout appris de H "
                         "(Miconi 2018) — à écrire (hypothèse de robla)",
        biological_analogue="plasticité hebbienne gatée par DA/ACh — solide comme phénomène, moyenne "
                             "comme règle",
        analogue_solidity="moyenne",
        bio_lesion_prediction="nucleus basalis → déficit sous NOUVEAUTÉ, ancien préservé",
        capacity_served='rétention sous changement de distribution (split "shift")',
        without={"modulator": "constant"},
        dose_matched=True,
        matched_sham=None,
        in_repo_today=(
            "absent : hebbien legacy numpy = no-op sous torch (ADR-003) ; entre avec son billet : une "
            "Task à shift que Hebb pur échoue et que 3-facteurs réussit"
        ),
    ),
    "frozen_llm_backbone": Piece(
        name="frozen_llm_backbone",
        artificial_form="LLM gelé + adaptateur apprenant (tête / LoRA)",
        biological_analogue="cortex mature + plasticité locale, CLS",
        analogue_solidity="faible",
        bio_lesion_prediction=None,
        capacity_served="a priori symbolique",
        without={"adapter": False, "backbone": "random_features"},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="absent : rien n'existe encore ; seul llm_fn(str)->str existe",
    ),
    "state_noise_regulator": Piece(
        name="state_noise_regulator",
        artificial_form="bruit sur l'état récurrent porté (organe dreaming)",
        biological_analogue="homéostasie du sommeil (DREAM-007 : pas du rejeu)",
        analogue_solidity="faible",
        bio_lesion_prediction=None,
        capacity_served="régulation de bruit d'état (+77% survie)",
        without={"organ": "off"},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="arc DREAM-001→007, in-world seulement",
    ),
    "curiosity_intrinsic": Piece(
        name="curiosity_intrinsic",
        artificial_form="surprise du modèle du monde → bonus",
        biological_analogue="dopamine de nouveauté",
        analogue_solidity="moyenne",
        bio_lesion_prediction=None,
        capacity_served="exploration",
        without={"intrinsic_scale": 0},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="MORTE sous torch (surprise jamais écrite, P4.8) — cas gelé de (L3) DEAD_LEARNER",
    ),
    "targeted_variation": Piece(
        name="targeted_variation",
        artificial_form="add_connection biaisé entrée→sortie",
        biological_analogue="biais développementaux de connectivité",
        analogue_solidity="faible",
        bio_lesion_prediction=None,
        capacity_served="découverte d'arête",
        without={"variation": "uniform"},
        dose_matched=True,
        matched_sham=None,
        in_repo_today="EVO-009 : 1/12 → 12/12, p = 9,6e-6 ; dose en generations",
    ),
    "eligibility_trace_credit": Piece(
        name="eligibility_trace_credit",
        artificial_form="trace d'éligibilité sur W dans TorchPopulationModel._td_update (drapeau de "
                         "classe CREDIT_TRACE_LAMBDA, défaut 0.0 = chemin d'origine bit-identique ; P4.11)",
        biological_analogue="traces d'éligibilité synaptiques / synaptic tagging (Gerstner 2018)",
        analogue_solidity="moyenne",
        bio_lesion_prediction="blocage du tagging synaptique abolit l'association à délai, pas "
                               "l'immédiate (maillon inferred)",
        capacity_served="crédit temporel par pas à délai D≥1",
        without={"trace_lambda": 0.0},
        dose_matched=True,
        matched_sham=None,
        in_repo_today=(
            "attend : réponse connue NÉGATIVE ÉTABLIE — TD(0) par pas n'apprend pas la composition "
            "différée (td0 0,190, 1/12 au-dessus de réf+0,05 ; réf lr=0 0,163), inerte aux trois pas "
            "(2,0 / 4,0 / 8,0), avec ses deux contrôles (chemin td0_d0 0,503, substrat bptt 0,807) ; "
            "réponse POSITIVE observée à UN SEUL point de fonctionnement (lr 4,0, lambda 0,9 : 0,253 > "
            "td0 sur 12/12, R0) et NON INVARIANTE (R1 : lr 2,0 → 0/12 ; lambda 0,5 → 0/12) — classe "
            "E19 ; billet PAYABLE par un balayage lr x lambda SCELLÉ (EDR-TD-STEP-PILOT-R0 avec "
            "bandeau, R1). Réserves : effet faible, un substrat, un délai, traces remises à zéro par "
            "épisode, aucune extrapolation in-world. DEUX CONTROLES DU BILLET MANQUENT, mesures a "
            "l'appui : (a) le sham exige par ADR-005 (« meme trace, delta PERMUTE dans le temps ») "
            "n'a JAMAIS ete mesure (0 occurrence dans tools/td_step_pilot.py, motif valide sur cas "
            "positif) — c'est le SEUL bras qui separe « la trace transporte du credit » de « la trace "
            "fait un pas effectif plus gros » (gamma*lambda = 0,81 ajoute 0,81*g0 au pas 1) ; (b) la "
            "dose appariee en Sigma|dW| qu'exige le billet n'est publiee par AUCUN des trois JSON du "
            "pilote : le critere d'entree n'est pas seulement non atteint, il n'est pas MESURABLE sur "
            "les artefacts existants."
        ),
    ),
    "time_constant_modulation": Piece(
        name="time_constant_modulation",
        artificial_form="facteur par nœud sur delta_j = sigmoid(W_jj) dans _step — à écrire",
        biological_analogue="neuromodulation de la constante de temps (ACh/NE)",
        analogue_solidity="faible",
        bio_lesion_prediction=None,
        capacity_served="rétention sous changement de distribution",
        without={"tau_modulation": False},
        dose_matched=True,
        matched_sham=None,
        in_repo_today=(
            "absent : P4.13 (a), results/delta_distribution_hof.json : la diagonale de W est "
            "EXACTEMENT nulle sur 161/172 nœuds des 30 génomes HoF (delta = 0,5 GELÉ) ; agent frais "
            "172/172 non nulles ; l'évolution n'a AUCUN écrivain sur tau (sparsification + "
            "mutate_weights ne réveille pas un zéro, EVO-009). La pièce n'a de sens que sur un substrat "
            "où delta est ÉCRIT (connectome torch frais) ; sur un champion évolué un facteur sur delta "
            "est un bouton GLOBAL. Billet à payer : Task à split shift"
        ),
    ),
}

PIECE_STATUS: dict = {
    "bilinear": "R1",
    "recurrent_state": "R1",
    "bptt_credit": "R2",
    "td_critic": "attend",
    "condition_gate": "attend",
    "warm_start_prior": "attend",
    "neuromod_plasticity": "attend",
    "frozen_llm_backbone": "attend",
    "state_noise_regulator": "hors_v1",
    "curiosity_intrinsic": "hors_registre",
    "targeted_variation": "attend",
    "eligibility_trace_credit": "attend",
    "time_constant_modulation": "attend",
}


def check_pieces_registry(learners) -> None:
    """Toute pièce citée par un Learner existe au registre ; une pièce dont `in_repo_today` commence par
    "absent" (billet d'entrée E2 non payé : aucune forme dans le dépôt) n'est citée par aucun Learner."""
    for lrn in learners:
        for p in lrn.pieces:
            if p.name not in PIECES:
                raise KeyError(f"{lrn.name} cite la pièce {p.name!r}, absente du registre")
            if PIECES[p.name].in_repo_today.startswith("absent"):
                raise ValueError(
                    f"{lrn.name} cite {p.name!r}, marquée absent au registre : elle n'a pas de forme "
                    "dans le dépôt (billet d'entrée E2 non payé)"
                )
