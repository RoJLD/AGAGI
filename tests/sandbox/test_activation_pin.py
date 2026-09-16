# -*- coding: utf-8 -*-
"""E29 — l'activation du substrat LEGACY dépend d'un fichier NON VERSIONNÉ chargé À CHAUD.

Mesuré le 2026-09-16 : `src/metaprog/sandbox/generated_ops.py` (Swish) est écrit par la boucle
métaprog (`compiler.py:35`), ignoré par git (`.gitignore:72`), absent de HEAD (supprimé à d4982b0,
EDR 035) — et `MambaBatchModel.forward` le recharge à CHAQUE pas dès que son mtime change
(`mamba_agent.py::_get_activation_function`). Conséquences : tout record legacy tourne en Swish sur
cette machine et en tanh sur un clone ; un run peut changer d'activation EN COURS si la boucle
métaprog réécrit le fichier ; aucun bloc `regime` ne le disait.

La garde : un PIN de module (`ACTIVATION_PIN`) — `None` = comportement historique (bit-identique) ;
`"builtin"` = jamais de chargement ; un sha256 = charge SSI le fichier présent a CE hash, sinon LÈVE.
`activation_provenance()` publie ce qui est en vigueur ; `pinned_activation()` gèle l'activation
présente pour la durée d'un run. Chaque cas ci-dessous est un contre-exemple qui PEUT échouer : le
pin doit AGIR (une valeur numérique qui diffère), pas seulement exister.

⚠️ Aucun test n'écrit dans `src/metaprog/sandbox/` (arbre partagé) : le chemin du fichier est
redirigé vers `tmp_path` par `monkeypatch`.
"""
import hashlib
import math
import os
import sys
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.agents import mamba_agent as ma  # noqa: E402

_SWISH_SRC = (
    "import numpy as np\n"
    "\n"
    "def custom_activation(x):\n"
    "    return x * (1.0 / (1.0 + np.exp(-x)))\n"
)
_SWISH_1 = 1.0 / (1.0 + math.exp(-1.0))          # swish(1) = 0.7311
_TANH_1 = math.tanh(1.0)                          # tanh(1)  = 0.7616 — les deux DIFFÈRENT (0.03)


@pytest.fixture
def ops(tmp_path, monkeypatch):
    """Redirige le fichier d'ops vers tmp_path et remet l'état du module à neuf après le test."""
    path = tmp_path / "generated_ops.py"
    monkeypatch.setattr(ma, "_ops_file", lambda: str(path))
    monkeypatch.setattr(ma, "ACTIVATION_PIN", None)
    monkeypatch.setattr(ma, "_cached_activation", np.tanh)
    monkeypatch.setattr(ma, "_cached_mtime", 0.0)
    return path


def _write(path, src=_SWISH_SRC, bump=1.0):
    path.write_text(src, encoding="utf-8")
    # mtime strictement croissant même sur un système de fichiers à la seconde
    t = time.time() + bump
    os.utime(str(path), (t, t))


def _sha(path):
    """Hash NORMALISÉ (CRLF -> LF), comme le pin : `write_text` écrit CRLF sous Windows, et un hash des octets
    bruts différerait de celui du même contenu sur un clone LF — mesuré en écrivant ce fichier (4 rouges)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_pin_None_garde_le_comportement_historique(ops):
    """Contrôle : sans pin, le fichier présent EST chargé (Swish) — c'est ce que les records ont mesuré."""
    _write(ops)
    assert ma._get_activation_function()(1.0) == pytest.approx(_SWISH_1, abs=1e-9)


def test_pin_builtin_ignore_le_fichier_present(ops):
    """Le pin AGIT : fichier Swish présent, pin builtin -> tanh (valeur qui diffère de 0,03)."""
    _write(ops)
    ma.ACTIVATION_PIN = "builtin"
    assert ma._get_activation_function()(1.0) == pytest.approx(_TANH_1, abs=1e-9)


def test_pin_sha_charge_le_fichier_qui_a_CE_hash(ops):
    _write(ops)
    ma.ACTIVATION_PIN = _sha(ops)
    assert ma._get_activation_function()(1.0) == pytest.approx(_SWISH_1, abs=1e-9)


def test_pin_sha_refuse_un_fichier_au_mauvais_hash(ops):
    """Un pin sur un hash que le fichier n'a pas LÈVE — jamais un tanh silencieux."""
    _write(ops)
    ma.ACTIVATION_PIN = "0" * 64
    with pytest.raises(ma.ActivationPinMismatch):
        ma._get_activation_function()


def test_pin_sha_refuse_un_fichier_ABSENT(ops):
    """Le cas du CLONE : le record dit « sha X », le fichier n'existe pas -> refus, pas tanh."""
    ma.ACTIVATION_PIN = "0" * 64
    assert not ops.exists()
    with pytest.raises(ma.ActivationPinMismatch):
        ma._get_activation_function()


def test_pin_sha_attrape_un_ECHANGE_en_cours_de_run(ops):
    """Le mécanisme réel : la boucle métaprog réécrit le fichier PENDANT un run. Sans pin, le pas
    suivant tourne sur la nouvelle activation en silence ; avec pin, il lève."""
    _write(ops)
    ma.ACTIVATION_PIN = _sha(ops)
    ma._get_activation_function()                       # chargé, hash conforme
    _write(ops, src=_SWISH_SRC.replace("np.exp(-x)", "np.exp(-2.0 * x)"), bump=5.0)
    with pytest.raises(ma.ActivationPinMismatch):
        ma._get_activation_function()


def test_sans_pin_l_echange_en_cours_de_run_passe_EN_SILENCE(ops):
    """Le défaut mesuré, gelé comme contrôle : sans pin, la même réécriture change la valeur."""
    _write(ops)
    a = ma._get_activation_function()(1.0)
    _write(ops, src=_SWISH_SRC.replace("np.exp(-x)", "np.exp(-2.0 * x)"), bump=5.0)
    b = ma._get_activation_function()(1.0)
    assert a != b


def test_provenance_publie_source_nom_hash_et_non_versionne(ops):
    _write(ops)
    ma._get_activation_function()
    p = ma.activation_provenance()
    assert p["source"] == "generated_ops.py"
    assert p["sha256"] == _sha(ops)
    assert p["name"] == "custom_activation"
    assert p["versioned"] is False
    assert p["pin"] is None


def test_provenance_sans_fichier_dit_builtin(ops):
    p = ma.activation_provenance()
    assert p["source"] == "builtin" and p["name"] == "tanh" and p["sha256"] is None


def test_pinned_activation_gele_le_hash_present_et_restaure(ops):
    """Le contexte pose un pin = hash du fichier présent (ou builtin), le run entier tourne dessus,
    et l'ambiant est RESTAURÉ en sortie (état global E5)."""
    _write(ops)
    with ma.pinned_activation() as pin:
        assert pin == _sha(ops)
        assert ma.ACTIVATION_PIN == pin
        assert ma._get_activation_function()(1.0) == pytest.approx(_SWISH_1, abs=1e-9)
    assert ma.ACTIVATION_PIN is None


def test_pinned_activation_sans_fichier_pose_builtin(ops):
    with ma.pinned_activation() as pin:
        assert pin == "builtin"
        assert ma._get_activation_function()(1.0) == pytest.approx(_TANH_1, abs=1e-9)
    assert ma.ACTIVATION_PIN is None


def test_pinned_activation_explicite_builtin_force_tanh_meme_fichier_present(ops):
    _write(ops)
    with ma.pinned_activation("builtin"):
        assert ma._get_activation_function()(1.0) == pytest.approx(_TANH_1, abs=1e-9)


def test_le_hash_du_pin_ignore_les_fins_de_ligne(ops):
    """Un fichier VERSIONNÉ est CRLF sur cette machine (autocrlf) et LF sur un clone : le sha du pin doit
    être le même, sinon un record ne se rejoue que sur SA machine. Le contrôle qui peut échouer : deux
    contenus RÉELLEMENT différents doivent, eux, donner deux hashs."""
    ops.write_bytes(_SWISH_SRC.encode("utf-8"))
    lf = ma._ops_sha256(str(ops))
    ops.write_bytes(_SWISH_SRC.replace("\n", "\r\n").encode("utf-8"))
    crlf = ma._ops_sha256(str(ops))
    assert lf == crlf
    ops.write_bytes(_SWISH_SRC.replace("np.exp(-x)", "np.exp(-2.0 * x)").encode("utf-8"))
    assert ma._ops_sha256(str(ops)) != lf


def test_le_fichier_d_activation_du_depot_est_VERSIONNE():
    """Cliquet de P2.75 : `src/metaprog/sandbox/generated_ops.py` est SUIVI par git depuis le 2026-09-16.
    Le re-ignorer (ou le supprimer de l'index) rougit ici — un clone perdrait l'activation de tous les
    records legacy. `None` (git absent) est toléré : on ne fabrique pas un verdict sans instrument."""
    real = ma._ops_file()
    assert os.path.exists(real), "le fichier d'activation legacy a disparu de l'arbre"
    tracked = ma._tracked_by_git(real)
    if tracked is None:
        pytest.skip("git indisponible : versionnement non mesurable ici")
    assert tracked is True


def test_provenance_du_depot_publie_versioned_True_et_le_sha_swish():
    """Le fichier versionné rend `versioned: True` et le sha normalisé de Swish — le lecteur d'un record
    peut vérifier qu'il tourne sous la même activation que la machine des records."""
    p = ma.activation_provenance()
    if p["source"] != "generated_ops.py":
        pytest.skip("aucun fichier d'activation chargé (clone sans le fichier ?)")
    assert p["versioned"] in (True, None)
    assert p["sha256"] == ma._ops_sha256(ma._ops_file())
    assert p["name"] == "custom_activation"
