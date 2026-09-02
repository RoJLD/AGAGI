"""DV mécaniste |logit| aux sorties notées — réparation du nan d'EVO-027.

Le helper in-run d'EVO-027 (`_logit_median`) passait `H_prev=None` à `recurrent_forward`, qui exige un
vrai tableau (`None.copy()` lève) ; l'échec était AVALÉ par `except Exception: continue` et la DV
rendait `nan` en silence — la forme (b) exacte du biais négatif systématique (le nan DÉTECTÉ puis
avalé : l'instrument SAIT et ne le dit pas). Cf. CLAUDE.md « Calibration des instruments ».

Réparation : (1) `H_prev` construit ICI en zéros (n_obs, N) — `H_history`/`H_potentials` sont
pass-through dans `recurrent_forward`, `None` y est licite ; (2) l'échec d'un forward n'est plus
avalé : il est COMPTÉ et RENDU (`n_failed`, `failures`), la médiane reste `nan` si rien n'est
mesurable mais l'instrument LE DIT. Un bug d'instrument trouvé devient un cas de calibration :
`tests/sandbox/test_instrument_calibration.py` (no-op exact / réponse connue en forme close / échec
bruyant).
"""
import os
import sys

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.seed_ai.rl_evolution import recurrent_forward


def logit_median_at_outputs(genomes, paires_rel, n_obs=8, seed=12345):
    """|logit| médian aux sorties notées, forward pur sur obs aléatoires, H frais (zéros).

    `paires_rel` : itérable de (canal, sortie_RELATIVE au bloc de sorties) — la grandeur d'EVO-012
    qui, chez les élites, écrase un poids ~N(0,1).

    Renvoie un dict — jamais un scalaire nu, pour que l'absence de mesure soit VISIBLE :
      median   : float (nan si AUCUN forward n'a abouti — et alors n_failed le dit)
      n_ok     : génomes mesurés
      n_failed : génomes dont le forward a levé
      failures : messages d'erreur (uniques, tronqués) — le nan n'est plus muet
    """
    vals, n_ok, failures = [], 0, []
    rng = np.random.default_rng(seed)
    for g in genomes:
        obs = rng.standard_normal((n_obs, g.num_inputs)).astype(np.float32)
        h0 = np.zeros((n_obs, g.num_nodes), dtype=np.float32)   # LE fix : H réel, plus jamais None
        try:
            out = recurrent_forward(g, obs, h0, None, None)[0]
        except Exception as e:                                   # noqa: BLE001 — compté et RENDU
            msg = f"{type(e).__name__}: {e}"
            if msg not in failures:
                failures.append(msg[:200])
            continue
        n_ok += 1
        for _, rel in paires_rel:
            if rel < out.shape[1]:
                vals.extend(abs(float(x)) for x in out[:, rel])
    return {"median": float(np.median(vals)) if vals else float("nan"),
            "n_ok": n_ok, "n_failed": len(genomes) - n_ok, "failures": failures}
