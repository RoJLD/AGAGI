"""Règle TD-STEP-PILOT-R3 (P4.19), BROUILLON v2 -- NON scellée. Source unique de la règle jusqu'au sceau : la revue
adversariale lit le JSON que `brouillon()` écrit (hors du dépôt), robla tranche les questions ouvertes, puis la règle
est scellée par `tools/preregister.preregister(..., reviewed_by=...)` -- jamais avant.

v2 (2026-10-14) remplace le brouillon v1 du 2026-09-28 sur cinq points, tous nés d'une MESURE faite AVANT le sceau et
sans regarder une cellule des seeds du verdict :
  1. marge 20 pas PROPOSÉE (v1 : 29) -- τ mesuré sur les seeds tenues à l'écart (results/td_step_pilot_r3_tau.json) ;
  2. modèle de bruit de la calibration DÉCLARÉ (v1 double-comptait un bruit d'éval tirée absent de l'éval exhaustive) ;
  3. image de calcul EXIGÉE par son digest, vérifiée par l'agrégat (cellule d'une autre image EXCLUE, jamais lue) ;
  4. exécution CELLULE PAR CELLULE sur nexus (le run monolithique du v1 ne tenait pas dans un Job du déport) ;
  5. trois QUESTIONS OUVERTES, à trancher par la revue puis robla, dont la marge liée à trois usages.
Usage : python -m tools.td_step_pilot_r3_regle <sortie.json>
"""
import json
import math
import sys

DIGEST_IMAGE = "sha256:d5341acf6f9206968c5d9ac4793618a54b1a6734a1c090cfc305cfb62a1e1141"

REGLE = {
    "question": (
        "P4.19 (ADR-005, ligne eligibility_trace_credit ; critère amendé le 2026-09-24, décisions de robla datées du "
        "2026-09-28) : sur le pilote TD PAR PAS (D=1, substrat bilinéaire rang 16, 3000 épisodes, SGD, traces remises "
        "à zéro à chaque épisode), l'aide de la trace λ 0,9 sur TD(0) vient-elle du TRANSPORT du crédit (l'alignement "
        "de δ avec la trace) ou d'un PAS plus gros ? Sham : même trace, δ DÉCALÉ d'un épisode dans le seul terme porté "
        "(CREDIT_TRACE_DELTA_SHAM = decale). Deux pas : 4,0 PRIMAIRE, 4√2 SECONDAIRE."),
    "cellule": {
        "K": 6, "n_agents": 16, "episodes_td": 3000, "lambda": 0.9, "trace_reset_per_episode": True,
        "seeds": list(range(1, 13)),
        "pas": {"p1": 4.0, "p2": 4.0 * math.sqrt(2.0)}, "pas_primaire": "p1", "pas_secondaire": "p2",
        "lr_par_agent": {"p1": 0.25, "p2": 4.0 * math.sqrt(2.0) / 16},
        "bras_par_pas": ["lam0", "lam09", "sham09", "td0_d0", "td0_app"], "bras_apparie": True,
        "references": ["lr0_reference", "lr0_reference_d0"],
        "bloc_episodes": 500, "lieu": "nexus", "threads": 1,
        "image_digest": DIGEST_IMAGE,
        "image_regle": (
            "le run scellé tourne sur CETTE image, citée par son digest : celle sur laquelle τ a été mesuré (24 MANIFEST "
            "de results/td_step_pilot_r3_tau.json). Décision de Master 2 (2026-10-13) : l'image de production RESTE "
            "d5341acf jusqu'au run scellé de R3 et au retest de P4.18, une reconstruction à contexte IDENTIQUE ayant "
            "rendu un AUTRE digest (dépendances Python transitives non épinglées ; numpy, torch et kuzu identiques). "
            "Vérifiée par l'agrégat (`agreger_r3`) : une cellule d'un autre digest est EXCLUE et nommée, jamais lue. "
            "Soumission avec Python 3.13 en chemin complet (le « python » 3.14 des sessions refuse, fuseau illisible)."),
        "substrat": "bilinear rang 16, W/U/V/W_bl traces (tools/td_step_pilot._train_eval_td_step)",
        "evaluation": ("DEUX évaluations par cellule : les 40 lots TIRÉS de R0-R2 (grille 640, inchangés, pour le lien "
                       "au bit avec R0 -- publié, jamais exigé), PUIS l'éval EXHAUSTIVE des K² = 36 couples (key, q) "
                       "par agent, argmax déterministe, AUCUN tirage (grille B·K² = 576) : le verdict se lit sur elle"),
        "instrument_dose": ("_InstrumentDose (enveloppe d'instance de _td_update : learn ET flush) : chemin Σ‖Δθ‖₁ et "
                            "net ‖θ_T − θ_0‖₁ par paramètre et par agent (float64), net par bloc de 500 épisodes ; "
                            "sous sham : sham_omis, chemins porté appliqué / contrefactuel / TD(0), terme porté au "
                            "rang 0, E[δ1|clé] et E[δ̃|clé]"),
        "bras_apparie_def": ("td0_app : λ 0, pas multiplié PAR BLOC de 500 épisodes par ρ_b = net(lam09, b) / "
                             "net(lam0, b) du MÊME seed et du MÊME pas (boucle OUVERTE : ρ vient de bras déjà mesurés, "
                             "jamais du bras apparié) ; le net ATTEINT est publié et contrôlé"),
        "execution": (
            "CELLULE PAR CELLULE sur nexus, une commande par Job (`python -m tools.td_step_pilot_r3 cellule --bras B "
            "--pas P --seed S [--rho …]`, `reference --ref R --seed S`), 1 CPU et 1 thread posés par le déport depuis le "
            "cgroup ; les ρ du bras apparié sont calculés sur la batcave depuis lam0 et lam09 RAPATRIÉS (`rho`, repr "
            "exacte) et passés en argument, le pod ne voyant que les fichiers suivis ; pré-vol FIGÉ dans "
            "results/td_step_pilot_r3_prevol.json, jamais réécrit (unité = temps CPU de la cellule : le mur d'une même "
            "cellule a varié de 29 à 107 s avec la contention entre pods) ; agrégat sur la batcave, sans simulation : "
            "chaque fichier relié au MANIFEST de son Job par sha256, cellule EXCLUE et nommée si hors lieu, hors image, "
            "code non nul, arbre sale ou sans MANIFEST ; ρ revérifiés au bit ; refus de mêler deux sha de code ; ordre "
            "« étape 2 après étape 1 » publié depuis les horodatages des MANIFEST. Ordre des étapes : pré-vol (seed 1 au "
            "pas primaire, 5 cellules), étape 1 (pas primaire, références comprises), étape 2 (pas secondaire)."),
    },
    "seuils": {
        "marge_pas": 20,
        "seeds_effet": 11, "seeds_chemin": 10, "seeds_appariement": 10,
        "appariement_bornes": [0.8, 1.25], "garde_dose_sham": [0.9, 1.1],
        "f_transporte_max": 0.25, "f_pas_plus_gros_min": 0.75,
        "bootstrap_B": 10000, "bootstrap_graine": 4190,
        "calibration": {
            "modele_de_bruit": (
                "DÉCLARÉ v2 : pas de bruit d'éval (éval exhaustive, entraînement déterministe par seed) ; d_s ~ N(μ, τ), "
                "μ = 34,5 et τ = 6,68 pas MESURÉS sur les seeds 13-24 tenues à l'écart (nexus, sha 67888a3a, lam0 et "
                "lam09 seulement, jamais le sham) ; lam0 fixe ; lam09 = lam0 + d_s ; sham09 = lam0 + f·d_s + σ_e·z, σ_e = "
                "τ (écart d'une différence entre deux bras d'un même seed, mesuré) et 9,3 en sensibilité ; bras apparié "
                "= lam0. Implémenté par base_injection_v2 / calibrer_lecture_v2 (tools/td_step_pilot_r3.py). Remplace le "
                "modèle v1, qui injectait 9,3 pas de bruit binomial d'éval TIRÉE sur chaque bras -- double compte."),
            "mu_pas": 34.5, "tau_pas": 6.68, "sigmas_e_pas": [6.68, 9.3], "f": [0.0, 0.3, 0.5, 0.6, 0.8, 1.0],
            "n_rep": 1000, "graine": 41903,
            "exigence": "P(TRANSPORTE | f=0) ≥ 0,8 et P(PAS_PLUS_GROS | f=1) ≥ 0,8 à σ_e = τ ; fausses lectures publiées",
            "mesure_preliminaire": (
                "hors règle, 400 rép. (results/td_step_pilot_r3_puissance_apres_tau.json) : marge 29 / 11 → "
                "P(TRANSPORTE | f=0) 0,17-0,19 ; marge 20 / 11 → 0,86-0,90 et P(PAS_PLUS_GROS | f=1) 0,93-0,97 ; "
                "15, 10, 0 n'ajoutent presque rien ; fausses lectures ≤ 2,8 %")},
        "budget_etape_s": 14400, "safety": 1.5, "unite_reference_s": 5.0, "fraction_cout_apparie_max": 1.0 / 3.0,
        "justification": (
            "MARGE 20 PROPOSÉE, NON ADOPTÉE (question ouverte 1) : la marge de 29 pas (0,05 × 576, prise de R0-R2) "
            "couvrait un bruit d'éval TIRÉE qui n'existe pas sur la grille exhaustive ; sur les seeds tenues à l'écart, "
            "3/12 effets réels sont à 26 pas, sous elle, et la lecture v1 aurait rendu PAS_D_EFFET (9/12) ; 20 pas = "
            "coude de la puissance mesurée. 11/12 = critère de l'ADR ; 10/12 = convention de R0-R2 pour le chemin ; f̂ "
            "≤ 0,25 (borne haute IC90) = TRANSPORTE, f̂ ≥ 0,75 (borne basse) = PAS_PLUS_GROS : le sham garde au plus un "
            "quart / au moins trois quarts du gain ; garde de dose exogène [0,9 ; 1,1] (fantôme : 1,002) ; appariement "
            "du bras td0_app accepté si net atteint / net visé ∈ [0,8 ; 1,25] sur ≥ 10/12 seeds ; bras apparié retenu "
            "au pré-vol ssi son unité CPU MESURÉE est STRICTEMENT sous 1/3 de la somme des quatre autres (décision 3 : "
            "sur le COÛT seul, avant toute autre cellule, jamais après un verdict) ; budget 4 h par étape, marge 1,5, "
            "sur les unités CPU par bras du pré-vol -- la marge de queue est 1,5 et non 3 parce que les unités viennent "
            "de VRAIES cellules du run (leçon de P4.18 : unité d'un seed complet à 96 % du seuil sous la marge ×3).")},
    "dv_primaire": (
        "par pas et par seed, succès sur la grille exhaustive de 576 ; d = lam09 − lam0 et e = sham09 − lam0 (pas "
        "entiers) ; f̂ = Σe/Σd, IC90 par bootstrap APPARIÉ sur les seeds (B 10 000, graine 4190) ; f̂ None si Σd ≤ "
        "12 × marge (240 pas à la marge proposée ; porte 14) ; un rééchantillon à Σd* ≤ 0 est compté et écarté, IC "
        "None au-delà de 5 %."),
    "regle_de_lecture_continue": (
        "PAR PAS, ORDRE IMPOSÉ : INCOMPLET (une cellule manque ou a été EXCLUE par l'agrégat, ou pré-vol absent alors "
        "que la règle prévoit le bras apparié) ; INSTRUMENT_ROMPU (sham_omis ≠ 16, terme porté non nul au rang 0, ou "
        "appliqué/contrefactuel hors [0,9 ; 1,1] dans une cellule sham) ; CONTROLE_CHEMIN_ECHOUE (td0_d0 > "
        "lr0_reference_d0 + marge sur < 10/12) ; PAS_D_EFFET (lam09 > lam0 + marge sur < 11/12) ; F_INDEFINI (f̂ ou "
        "son IC None) ; SHAM_NUIT (borne haute < 0 : confondant du critique, jamais TRANSPORTE) ; TRANSPORTE (borne "
        "haute ≤ 0,25) ; PAS_PLUS_GROS (borne basse ≥ 0,75) ; SHAM_PARTIEL (sinon, f̂ et IC publiés). SYNTHÈSE vers "
        "l'ADR : REFUSÉE ssi PAS_PLUS_GROS au pas PRIMAIRE ; ENTRE ssi aux DEUX pas TRANSPORTE ET lam09 > barre "
        "(lr0_reference + marge) sur ≥ 11/12 ET sham09 > barre sur < 11/12 ET (bras apparié retenu -> lisible ET "
        "lam09 > td0_app + marge sur ≥ 11/12), puis garde E19 (assert_verdict_invariant_to_optimizer, measure = "
        "(médiane sham09, médiane lam09), reference_floor = max des médianes lam0 + marge) PASSE ; ATTEND sinon, "
        "manques NOMMÉS. Le pas secondaire ne produit JAMAIS à lui seul un verdict négatif (décision 2)."),
    "discrimination": {
        "TRANSPORTE aux deux pas + ADR + dose + E19": "la pièce ENTRE au registre (ligne eligibility_trace_credit).",
        "PAS_PLUS_GROS au pas primaire": "la pièce est REFUSÉE et ça se grave : l'aide de la trace est le PAS.",
        "tout autre cas": "la ligne reste « attend » avec ses manques nommés, sans réordonner la file.",
        "SHAM_NUIT": "le sham détruit plus que le transport (critique bruité, nœud V lu au pas 1) : ni transport ni pas "
                     "plus gros établis -- nommé, jamais lu TRANSPORTE."},
    "publies_hors_branche": [
        "comptes littéraux de l'ADR par pas (lam09, sham09, lam0 > barre ; sham09 > lam0 + marge ; lam09 > sham09 à "
        "marge 0)", "médianes de tous les bras et références",
        "dose : ρ_td (chemin et net), sham/trace en CHEMIN (prédit ≈ 0,82 sous transport, ≈ 1 sinon) et en NET, rapport "
        "de COHÉRENCE (net_S/net_T)/(chemin_S/chemin_T) (< 1 prédit sous transport, ≈ 1 sinon ; direction seulement)",
        "E[δ1|clé] et E[δ̃|clé] par cellule sham (la dispersion de δ̃ par clé doit rester au niveau du bruit)",
        "lien au bit avec R0 au pas primaire (IDENTIQUE / DIFFERENT / NON_MESURE) -- jamais exigé (lieu nexus)",
        "par cellule : MANIFEST (job, lieu, sha, image, threads posés, horodatages, durée), environnement (torch, numpy, "
        "python, threads), temps mur et CPU", "cellules EXCLUES par l'agrégat, avec leur raison",
        "moyenne et écart-type des d de l'étape 1 (seeds du verdict), à côté de μ et τ des seeds tenues à l'écart -- "
        "descriptif, ne change aucun seuil"],
    "controles": {
        "positif_effet": "branche PAS_D_EFFET (rejoué, donc falsifiable)",
        "positif_chemin": "td0_d0 contre lr0_reference_d0 (rejoué)",
        "positif_instrument": ("mode identite = trace à 1e-5 ; formule du porté à réponse connue ; instrument nul au bit "
                               "à lr 0 ; instrument no-op (bras instrumenté = bras nu) -- tests/sandbox/"
                               "test_credit_trace_delta_sham.py et test_td_step_pilot_r3.py"),
        "specificite": "le sham diffère de la trace à lr > 0 (test) ; garde de dose exogène",
        "lecture": ("calibrée par INJECTION (0 simulation) sous le modèle v2 déclaré (seuils.calibration) : f ∈ {0 ; "
                    "0,3 ; 0,5 ; 0,6 ; 0,8 ; 1} ; σ_e ∈ {τ ; 9,3} ; 1000 rép. ; publiée dans results/"
                    "td_step_pilot_r3_calibration_lecture.json AVANT le sceau ; exigence de seuils.calibration"),
        "agregat": ("tests/sandbox/test_td_step_pilot_r3.py : exclusions nommées (lieu, image, code, arbre sale, sans "
                    "MANIFEST), ρ revérifiés au bit, refus de deux sha, pré-vol figé ; mutations à la main tuées"),
        "famille": "144 cellules (12 seeds × 5 bras × 2 pas + 24 références) via assert_control_family",
        "e19": "garde appelée seulement si TRANSPORTE aux deux pas ; PreflightError -> VERDICT_DEPEND_DU_PAS (attend)"},
    "questions_ouvertes": [
        ("(1) MARGE UNIQUE LIÉE À TROIS USAGES -- à trancher par la revue, puis robla, SANS regarder une cellule des "
         "seeds 1-12. `marge_pas` sert à la fois : (a) à PAS_D_EFFET (lam09 > lam0 + marge, ≥ 11/12) -- c'est là que τ "
         "montre que 29 est trop haut ; (b) au contrôle du CHEMIN (td0_d0 > lr0_reference_d0 + marge, ≥ 10/12) -- "
         "grandeur différente (sans délai), jamais mesurée en éval exhaustive ; (c) à la BARRE littérale de l'ADR (lam09 "
         "et sham09 contre lr0_reference + marge) et au bras apparié (lam09 > td0_app + marge). Abaisser une marge "
         "partagée à 20 rend aussi le chemin, la barre et l'appariement plus permissifs. Options : une marge par usage, "
         "chacune justifiée ; ou 20 partout, en le disant ; ou 29 pour (b) et (c), 20 pour (a)."),
        ("(2) LE COMPTE de PAS_D_EFFET reste 11/12 (critère de l'ADR) : à 20 pas il suffit (0,86-0,90) ; 10/12 "
         "n'ajoute presque rien (0,88-0,92)."),
        ("(3) SHAM_NUIT sort 5 à 8 % du temps quand le vrai f vaut 0 (borne haute de l'IC < 0 par bruit) : c'est la "
         "principale perte de puissance restante ; la garder (un critique bruité qui détruit est un confondant réel) ou "
         "exiger aussi f̂ < −marge relative ?")],
    "cout": (
        "Sur nexus, une cellule par Job (1 CPU, 4 Gi, délai 1200 s, au plus 10 Jobs simultanés) : pré-vol 5 cellules ; "
        "étape 1 = 55 cellules neuves + 24 références (sans entraînement) ; étape 2 = 60 cellules, jouée après l'étape 1. "
        "Coût MESURÉ sur le même dispositif (pilote τ, 10 Jobs simultanés) : lam0 107 s, lam09 158 s de mur par cellule "
        "(médianes), 29 s pour une cellule seule ; sham09 ≈ lam09, td0_d0 ≈ lam0 / 2 attendus -- ≈ 6 vagues de 10 par "
        "étape, ≈ 40 min de bout en bout, plus une vague td0_app après le calcul des ρ. Aucune charge sur la batcave hors "
        "agrégat (sans simulation) ; SANS bail kuzu (aucun monde, aucune base). Fenêtre de nexus : arrêt à minuit."),
    "provenance": (
        "Écrite en connaissant R0 (lr 4,0 : trace 12/12, dont seeds 8 et 11 à +1 pas), R1 (lr 2,0 : 0/12) et R2 "
        "(AIDE_A_UN_POINT ; lr 8,0 hors régime, td0_d0 7/12). Le pas 4√2 est choisi APRÈS ces résultats : chemin "
        "bifurquant, dit tel quel -- d'où son statut SECONDAIRE. Décisions de robla (ADR-005, datées du 2026-09-28) : "
        "sham décalé d'un épisode ; 4,0 primaire / 4√2 secondaire ; dose appariée en NET entre bras apprenants, le sham "
        "SEUL apparié en CHEMIN (exception 3 bis) ; barre = référence lr 0 ; lieu = nexus. v2 : τ et μ MESURÉS sur les "
        "seeds 13-24 tenues à l'écart (jamais le sham, jamais les seeds du verdict), démarche validée par robla le "
        "2026-10-13 ; calibration v1 (results/td_step_pilot_r3_calibration_lecture_brouillon_v1.json) remplacée, pas "
        "effacée. Aucune cellule des seeds 1-12 mesurée à l'écriture. Le seed 0 (fumée de R0) reste exclu."),
}


def brouillon(chemin):
    """Écrit le brouillon (JSON) que la revue adversariale lit. N'écrit RIEN dans docs/preregistrations : sceller
    passe par preregister(..., reviewed_by=...) après la revue et les décisions de robla."""
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(REGLE, f, indent=1, ensure_ascii=False)
    return chemin


if __name__ == "__main__":
    print("brouillon ->", brouillon(sys.argv[1]))
