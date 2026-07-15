"""Instrument transversal : le témoin CAUSAL de « la capacité X est-elle exigée » = ablation
WITHIN-subject de X, pas « un agent équipé de X réussit » (between-subject, faux-positif).

ablation_verdict compare la fitness (survie) d'un MÊME sujet avec X intact vs X ablaté :
- ratio = median(intact) / median(ablated) ; ratio >> 1 => X est causalement porteur (X_DEMANDED) ;
  ratio ~ 1 => X est un leurre (X_DECOY).
- garde-fou n<12 : aucun verdict POSITIF sous puissance insuffisante (les petits n s'évaporent).
- corroborant optionnel weight_on_x = |W| que la politique met sur X (2e témoin ; le proxy montre
  |W|->0 quand X ne paie pas). Non calculable sur le champion HoF in-world -> None.

REF : docs/REF/REF-DEMAND-MARKER.md. Modalités : perception (S2-001, S2-002 in-world),
communication (LANG-006), généralisation (G1-001), mémoire (MEM-001).
"""
import statistics


def ablation_verdict(intact, ablated, weight_on_x=None,
                     n_floor=12, collapse_factor=1.5, decoy_ceiling=1.3, eps=1e-9):
    """intact, ablated : itérables de fitness appariées (survies par ère/seed). Renvoie le dict verdict.

    - collapse := ratio >= collapse_factor (X porteur)  ; decoy := ratio <= decoy_ceiling (X leurre).
    - verdict : X_DEMANDED si collapse ET n>=n_floor ; X_DECOY si decoy ; sinon INCONCLUSIVE.
    """
    intact = [float(x) for x in intact]
    ablated = [float(x) for x in ablated]
    n = min(len(intact), len(ablated))
    med_i = statistics.median(intact) if intact else 0.0
    med_a = statistics.median(ablated) if ablated else 0.0
    ratio = med_i / max(med_a, eps)
    collapse = ratio >= collapse_factor
    decoy = ratio <= decoy_ceiling
    if collapse and n >= n_floor:
        verdict = "X_DEMANDED"
    elif decoy:
        verdict = "X_DECOY"
    else:
        verdict = "INCONCLUSIVE"          # effet présent mais sous-puissant, OU zone grise
    return {"ratio": float(ratio), "n": int(n), "collapse": bool(collapse),
            "decoy": bool(decoy), "corroborant": weight_on_x, "verdict": verdict}
