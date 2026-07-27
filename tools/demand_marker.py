"""Instrument transversal : le témoin CAUSAL de « la capacité X est-elle exigée » = ablation
WITHIN-subject de X, pas « un agent équipé de X réussit » (between-subject, faux-positif).

ablation_verdict compare la fitness (survie) d'un MÊME sujet avec X intact vs X ablaté :
- ratio = median(intact) / median(ablated) ; ratio >> 1 => X est causalement porteur (X_DEMANDED) ;
  ratio ~ 1 => X est un leurre (X_DECOY).
- garde-fou n<12 : aucun verdict SOUS n<12, qu'il soit POSITIF (demandé) OU NUL (leurre) — les
  petits n s'évaporent dans les deux sens.
- corroborant optionnel weight_on_x = |W| que la politique met sur X (2e témoin ; le proxy montre
  |W|->0 quand X ne paie pas). Non calculable sur le champion HoF in-world -> None.

REF : docs/REF/REF-DEMAND-MARKER.md. Modalités : perception (S2-001, S2-002 in-world),
communication (LANG-006), généralisation (G1-001), mémoire (MEM-001).
"""
import statistics


def _degeneracy(intact, ablated, med_i, med_a, floor, ceiling, eps, intervention_verified=False):
    """Le bras de référence a-t-il de quoi BOUGER ? Renvoie la raison, ou None.

    POURQUOI CETTE GARDE EXISTE (classe E3+E14 du registre, armée le 2026-07-21). `ablation_verdict`
    était un pur ratio de médianes : **tout bras collé à une borne produit MÉCANIQUEMENT ratio ≈ 1.0,
    donc X_DECOY, donc « X est un leurre »** — un verdict NUL fabriqué par la borne, pas par l'absence
    d'effet. Trois conclusions gravées en sont sorties :
      * EDR-WARM-002 : bras intact à 5.0-7.2 ticks alors que le plancher no-perception vaut 9.0 →
        « le paysage de fitness est PLAT » ; réfuté par EDR-WARM-010 (la fitness récompense en fait
        densément, 9.0 → 200.0 strictement monotone).
      * EDR-S2-004 : 3 cellules sur 4 où `fit_policy` part de `W = zeros` et n'accepte qu'en
        `sc > best` STRICT ; quand `score(W=0)` atteint déjà le cap, W **ne quitte jamais son
        initialisation** → la politique est constante, ablater l'obs est un no-op LITTÉRAL, et le
        corroborant « |W| = 0.000 EXACT » est le zéro de départ, pas un poids appris.
      * EDR-S2-007 : cellule `shift0` où `_model_matrix` est la matrice IDENTITÉ → les deux bras sont
        le même calcul, bit à bit.

    ⚠️ CE QUE LE CODE PEUT ET NE PEUT PAS DÉTECTER. Un plancher n'est PAS déductible de deux tableaux :
    rien ne distingue « 7 ticks, c'est le sol » de « 7 ticks, c'est un niveau signifiant ». Sont donc
    détectés d'office les seuls cas CERTAINS (arms identiques, variance nulle) ; le reste exige que
    l'appelant DÉCLARE `floor=` / `ceiling=` — ce que l'étalon de WARM-010 fournit désormais
    (`tools/ground_truth_worlds.partial_oracle`, plancher 9.0 au régime S2-009)."""
    if intact and ablated and len(intact) == len(ablated) and intact == ablated:
        # ⚠️ NUANCE TROUVÉE PAR CALIBRATION (P2.4, le jour même où cette garde a été armée). Des bras
        # identiques ont DEUX causes opposées, et deux tableaux de sorties ne permettent PAS de les
        # distinguer :
        #   (a) l'intervention ne s'est PAS APPLIQUÉE — S2-007 (matrice identité), S2-004 (politique
        #       constante car W gelé) : le verdict est fabriqué, il faut bloquer ;
        #   (b) l'intervention s'est appliquée et N'A RIEN FAIT — étalon TRIVIAL de S2-001 : l'obs EST
        #       bien randomisée, mais la politique optimale ne la lit pas, parce qu'elle ne porte aucune
        #       information. C'est un X_DECOY LÉGITIME, et c'est la vérité-terrain qui valide le marqueur.
        # Bloquer (b) reviendrait à refuser le nul sur le cas même où le nul est la bonne réponse.
        # D'où `intervention_verified` : l'appelant DÉCLARE avoir vérifié que l'ablation perturbe bien
        # l'ENTRÉE (pas la sortie). Défaut False = conservateur.
        if not intervention_verified:
            return ("les deux bras sont IDENTIQUES point par point : soit l'ablation ne s'est pas "
                    "appliquée, soit elle n'a eu aucun effet — indécidable sans vérifier l'ENTRÉE. "
                    "Passer `intervention_verified=True` si la perturbation du canal est établie.")
    # ⚠️ RÈGLE RETIRÉE, et la raison mérite d'être gardée : « variance nulle du bras intact » semble un
    # bon signal de dégénérescence, mais **un positif entièrement CENSURÉ est légitimement constant**
    # (12 ères touchant toutes le cap de 200 ticks). La règle confondait « la métrique ne pouvait pas
    # bouger » avec « elle a saturé vers le haut », et sur-bloquait — mesuré : elle cassait un test
    # préexistant de nul sain. Le cas S2-004 qu'elle visait est déjà couvert par la détection
    # d'identité ci-dessus (W gelé -> survie déterministe -> les deux bras EXACTEMENT égaux).
    if floor is not None and med_i <= floor:
        return f"bras intact au PLANCHER déclaré (médiane {med_i:g} <= floor {floor:g})"
    if ceiling is not None and med_i >= ceiling and med_a >= ceiling:
        return f"les deux bras au PLAFOND déclaré (médianes {med_i:g}/{med_a:g} >= ceiling {ceiling:g})"
    return None


def ablation_verdict(intact, ablated, weight_on_x=None,
                     n_floor=12, collapse_factor=1.5, decoy_ceiling=1.3, eps=1e-9,
                     floor=None, ceiling=None, intervention_verified=False):
    """intact, ablated : itérables de fitness appariées (survies par ère/seed). Renvoie le dict verdict.

    - collapse := ratio >= collapse_factor (X porteur)  ; decoy := ratio <= decoy_ceiling (X leurre).
    - verdict : X_DEMANDED si collapse ET n>=n_floor ; X_DECOY si decoy ET n>=n_floor ; sinon
      INCONCLUSIVE (le garde-fou n<12 bloque les deux verdicts, pas seulement le positif).
    - **GARDE DE DÉGÉNÉRESCENCE, ARMÉE PAR DÉFAUT** : un bras de référence sans amplitude ne peut PAS
      produire de verdict NUL — `X_DECOY` devient `INCONCLUSIVE_DEGENERATE`, avec la raison dans
      `why`. Cf. `_degeneracy` pour les trois conclusions que l'absence de cette garde a produites.
      `floor=` / `ceiling=` déclarent les bornes connues du régime (fortement recommandé).
    - `intervention_verified=True` : l'appelant atteste avoir vérifié que l'ablation perturbe
      bien l'ENTRÉE. Sans ça, des bras identiques sont bloqués — car « l'intervention ne s'est
      pas appliquée » et « elle n'a eu aucun effet » sont indiscernables depuis les SORTIES.

    Note de conception : la dégénérescence n'invalide **que le NUL**. Un bras intact au plafond avec un
    bras ablaté bas reste un effet RÉEL — simplement CENSURÉ, donc sous-estimé : le ratio est une borne
    INFÉRIEURE. On le signale (`censored`) sans le bloquer, sinon on jetterait de vrais positifs."""
    intact = [float(x) for x in intact]
    ablated = [float(x) for x in ablated]
    n = min(len(intact), len(ablated))
    med_i = statistics.median(intact) if intact else 0.0
    med_a = statistics.median(ablated) if ablated else 0.0
    ratio = med_i / max(med_a, eps)
    collapse = ratio >= collapse_factor
    decoy = ratio <= decoy_ceiling
    why = _degeneracy(intact, ablated, med_i, med_a, floor, ceiling, eps, intervention_verified)
    censored = bool(ceiling is not None and med_i >= ceiling and med_a < ceiling)
    if collapse and n >= n_floor:
        verdict = "X_DEMANDED"            # un positif censuré reste un positif : ratio = borne INF
    elif decoy and n >= n_floor:
        verdict = "INCONCLUSIVE_DEGENERATE" if why else "X_DECOY"
    else:
        verdict = "INCONCLUSIVE"          # effet OU nul sous-puissant (n<n_floor), ou zone grise
    return {"ratio": float(ratio), "n": int(n), "collapse": bool(collapse),
            "decoy": bool(decoy), "corroborant": weight_on_x, "verdict": verdict,
            "degenerate": bool(why), "why": why, "censored": censored}
