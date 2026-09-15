"""Témoins de la porte 17 (`tools/check_io_overlap.py`) — aucun NOUVEAU génome persisté dont les blocs
d'entrée et de sortie se chevauchent (classe E24, P2.46 (d), 2026-09-15).

Ce que la porte doit savoir faire, et ce qu'on gèle ici : la réponse connue du champion (64 + 126 dans
172 = 18) et d'un génome frais (0) ; un `.npz` sans les trois entiers est RAPPORTÉ, jamais compté 0 ;
le verdict distingue nouveau / aggravé / connu ; et l'invariant du dépôt — tout sujet chevauchant est
GELÉ dans la baseline — sans jamais figer le NOMBRE de génomes (E25 : on gèle l'invariant, pas la valeur).
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.check_io_overlap import _load_baseline, etat, overlap_of, scan, scan_npz  # noqa: E402


def test_overlap_of_known_answers():
    assert overlap_of(64, 126, 172) == 18          # le champion HoF (mesuré le 2026-09-08)
    assert overlap_of(59, 108, 172) == 0           # un génome frais : 5 nœuds cachés
    assert overlap_of(10, 10, 20) == 0             # frontière exacte : zéro caché, zéro chevauchement
    assert overlap_of(10, 11, 20) == 1


def _npz(path, ni, no, nn, keys=True):
    if keys:
        np.savez(path, W=np.zeros((nn, nn), np.float32), num_inputs=ni, num_outputs=no, num_nodes=nn)
    else:
        np.savez(path, W=np.zeros((nn, nn), np.float32))


def test_scan_npz_detects_overlap_and_REPORTS_unreadable_files_instead_of_counting_zero(tmp_path):
    d = tmp_path / "genomes"
    (d / "lot").mkdir(parents=True)
    _npz(d / "lot" / "sain.npz", 59, 108, 172)
    _npz(d / "lot" / "chevauche.npz", 64, 126, 172)
    _npz(d / "lot" / "sans_entiers.npz", 0, 0, 4, keys=False)
    (d / "lot" / "corrompu.npz").write_bytes(b"pas un npz")
    sujets, illisibles = scan_npz(str(d))
    assert sujets["lot/sain.npz"]["overlap"] == 0
    assert sujets["lot/chevauche.npz"]["overlap"] == 18
    assert "lot/sans_entiers.npz" not in sujets and "lot/sans_entiers.npz" in illisibles
    assert not any(k.startswith("lot/corrompu") for k in sujets)
    assert any(k.startswith("lot/corrompu.npz") for k in illisibles)


def test_etat_blocks_NEW_and_AGGRAVATED_overlaps_and_passes_KNOWN_ones():
    sujets = {"a.npz": {"overlap": 0}, "b.npz": {"overlap": 3}, "hof#0": {"overlap": 18}, "c.npz": {"overlap": 5}}
    e = etat(sujets, {"hof#0": 18, "c.npz": 2})
    assert e["sujets"] == 4 and e["chevauchants"] == 3
    assert e["nouveaux"] == ["b.npz"]              # chevauchant, hors baseline
    assert e["aggraves"] == ["c.npz"]              # connu à 2, mesuré à 5
    assert e["connus"] == ["hof#0"]
    # NO-OP apparié : le même état, baseline complète et à niveau -> rien ne bloque
    e2 = etat(sujets, {"hof#0": 18, "c.npz": 5, "b.npz": 3})
    assert e2["nouveaux"] == [] and e2["aggraves"] == []


def test_the_gate_CAN_FAIL_a_zeroed_overlap_would_hide_the_champion():
    """CONTRE-EXEMPLE GELÉ : si `overlap_of` rendait 0 (mutation de la porte 15), le champion HoF
    passerait pour sain. Ce test est le témoin qui doit ROUGIR."""
    assert overlap_of(64, 126, 172) > 0


def test_repository_invariant_every_overlapping_subject_is_frozen_in_the_baseline():
    """L'INVARIANT (pas la valeur) : aucun sujet chevauchant hors baseline, aucun aggravé. Le nombre de
    génomes n'est PAS gelé — un nouveau lot SAIN doit passer sans toucher ce test."""
    sujets, illisibles = scan()
    assert sujets, "aucun génome persisté balayé : le périmètre est vide, le test ne prouverait rien"
    e = etat(sujets, _load_baseline())
    assert e["nouveaux"] == [] and e["aggraves"] == [], e
    assert illisibles == [], illisibles


def test_baseline_only_freezes_overlapping_subjects_with_their_measured_overlap():
    b = _load_baseline()
    assert b and all(int(v) > 0 for v in b.values())
    assert all(k.startswith("hall_of_fame") for k in b), "au gel du 2026-09-15 seul le HoF principal chevauche"
    json.dumps(b)
