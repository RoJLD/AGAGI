"""Calibration du cliquet de calibration LUI-MÊME sur les trois motifs RÉSORBANTS (P2.83 passe (i), 2026-09-26).

Le défaut (P2.83, moitié SILENCE fermée le 2026-09-24) : 9 déclarations `CALIBRATED` tombaient dans la branche
« déclaration périmée » sans un mot — dont 4 fonctions bien PRÉSENTES qu'aucun des 16 motifs ne voyait :
`plain_readout_ceiling`, `additive_argmax_exact_ceiling`, `verify_plain_ceiling_witness` (le plafond du plain,
valeur centrale du dossier P2.15) et `_td_update` (l'update TD(0) du chemin publié, calibré par P4.11). Leurs cas
existaient, leur déclaration existait : seule la DÉTECTION manquait, et le compteur les comptait pour rien.

DOUZIÈME élargissement : `*ceiling*` et `verify_*` (fonctions de module, ancrées `^def`) et `_td_update*`
(MÉTHODE, tolérant l'indentation comme les apprenants du 11e). Ces tests portent sur la couche qui IDENTIFIE, par
injection d'un arbre factice (coût nul), un no-op apparié de SPÉCIFICITÉ (le motif `*median*`, +9, a été REJETÉ :
des formateurs), et un ancrage sur l'arbre RÉEL : les quatre déclarations résorbées ne sont plus « ignorées », et la
collision `_td_update` est VUE sur ses deux chemins.

⚠️ `verify_*` seul n'ajoute RIEN sur l'arbre courant (son unique hit, `verify_plain_ceiling_witness`, est aussi un
`*ceiling*`) : le motif est PROSPECTIF, et c'est `verify_witness_in_situ` de l'arbre FACTICE qui tue sa mutation —
dit ici pour que personne ne lise « tué » comme « mesuré sur le réel ».
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools import check_instrument_calibration as M  # noqa: E402

# Arbre factice : la forme RÉELLE des symboles résorbés, plus les voisins qui ne doivent PAS entrer.
_FAUX_ARBRE = [
    ("tools/plain_substrate_ceiling.py",
     "def plain_readout_ceiling(K):\n    return 0\n"
     "def additive_argmax_exact_ceiling(K):\n    return 1\n"
     "def verify_plain_ceiling_witness(K):\n    return 2\n"
     "def _fmt_mediane(x):\n    return 3\n"),
    ("tools/witness.py",
     "def verify_witness_in_situ(K):\n    return 8\n"
     "def verify(K):\n    return 9\n"),
    ("src/agents/backend_torch.py",
     "class TorchPopulationModel:\n"
     "    def _td_update(self, prev, v_next):\n        return 4\n"
     "    def _td_update_trace(self, lam, logp, v, target, delta):\n        return 5\n"
     "    def _trace_step(self, e, g, gl):\n        return 6\n"),
    ("tools/x.py", "def _median_norm(v):\n    return 7\n"),
]


def test_scan_SEES_the_ceiling_functions(monkeypatch):
    """CONTRE-EXEMPLE GELÉ : les trois fonctions de plain_substrate_ceiling.py, exactement la forme réelle."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    found = M.scan_instruments()
    for nom in ("plain_readout_ceiling", "additive_argmax_exact_ceiling", "verify_plain_ceiling_witness"):
        assert found.get(nom) == "tools/plain_substrate_ceiling.py", (nom, found)


def test_scan_SEES_a_verify_witness_that_is_NOT_a_ceiling(monkeypatch):
    """Le seul témoin qui distingue `verify_*` de `*ceiling*` : un `verify_…` sans « ceiling » dans son nom.
    `verify` NU (sans suffixe) reste dehors : le motif exige `verify_`."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    found = M.scan_instruments()
    assert found.get("verify_witness_in_situ") == "tools/witness.py", found
    assert "verify" not in found, found


def test_scan_SEES_the_td_update_METHODS_trace_included(monkeypatch):
    """Les deux updates TD sont des MÉTHODES (indentées) : sans tolérance à l'indentation, invisibles."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    found = M.scan_instruments()
    assert found.get("_td_update") == "src/agents/backend_torch.py", found
    assert found.get("_td_update_trace") == "src/agents/backend_torch.py", found


def test_the_widening_is_SPECIFIC_formatters_and_trace_helpers_stay_out(monkeypatch):
    """SPÉCIFICITÉ (no-op apparié) : `_fmt_mediane`, `_median_norm` (le motif `*median*` rejeté) et la méthode
    voisine `_trace_step` ne doivent PAS entrer."""
    monkeypatch.setattr(M, "_iter_sources", lambda: iter(_FAUX_ARBRE))
    found = M.scan_instruments()
    assert "_fmt_mediane" not in found and "_median_norm" not in found and "_trace_step" not in found, found


def test_the_REAL_tree_no_longer_IGNORES_the_four_resorbed_declarations():
    """ANCRAGE SUR LE RÉEL : les sept noms que la passe fait entrer sont DÉTECTÉS ; les quatre déclarations
    résorbées ne sont plus dans `scan_calibrated.ignorees` ; `_td_update` et `_untrained_ceiling` sont vus
    comme des COLLISIONS sur leurs deux chemins (donc déclarés QUALIFIÉS, jamais nus)."""
    found = M.scan_instruments()
    for nom in ("plain_readout_ceiling", "additive_argmax_exact_ceiling", "verify_plain_ceiling_witness",
                "_td_update", "_td_update_trace", "_resolve_ceiling", "_untrained_ceiling"):
        assert nom in found, nom
    M.scan_calibrated()
    ign = set(M.scan_calibrated.ignorees)
    for nom in ("plain_readout_ceiling", "additive_argmax_exact_ceiling", "verify_plain_ceiling_witness",
                "src/agents/backend_torch.py::_td_update"):
        assert nom not in ign, (nom, sorted(ign))
    coll = M.scan_collisions()
    assert set(coll.get("_td_update", [])) == {"src/agents/backend_torch.py", "src/agents/torch_batch_model.py"}
    assert set(coll.get("_untrained_ceiling", [])) == {"tools/memory_perception_demand_probe.py",
                                                       "tools/perception_coordination_demand_probe.py"}
