"""
tests/sandbox/test_claude_code_llm_fn.py — P2.66 : `claude_code_llm_fn` (src/metaprog/llm_proposer_fn.py),
un terminal Claude Code comme `llm_fn(prompt) -> str` du #8.

Dispositif : un FAUX exécutable `claude` — un script Python derrière un shim (`claude.cmd` sous Windows,
`claude` shell sous POSIX) — posé dans le `tmp_path` du test. Le PATH du test est RÉDUIT à ce seul
répertoire : le vrai `claude` de la machine n'est atteignable par AUCUNE résolution. Aucun appel réel,
jamais. Le faux binaire ne fait que trois choses selon le cas : ré-imprimer stdin, imprimer un texte
fixe, ou échouer/dormir — et il ENREGISTRE son argv (le prompt ne doit jamais y figurer : il passe par
STDIN, limite de ligne de commande sous Windows).

Ce n'est PAS un instrument (aucun motif du cliquet ne capte `claude_code_llm_fn`) : il ne produit aucune
affirmation scientifique, il transporte un texte.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from src.metaprog.llm_proposer_fn import claude_code_llm_fn

# Prélude commun du faux `claude` : enregistre argv (hors argv[0]) dans ARGV_FILE, lit TOUT stdin en
# octets (jamais via l'encodage de la console : sous Windows elle n'est pas UTF-8). Le corps propre à
# chaque cas est concaténé à la suite.
_PRELUDE = """\
import json, os, sys, time
argv = sys.argv[1:]
with open({argv_file!r}, "w", encoding="utf-8") as f:
    json.dump(argv, f, ensure_ascii=False)
data = sys.stdin.buffer.read()
"""

_BODY_ECHO = "sys.stdout.buffer.write(data)\n"
_BODY_TEXT = "sys.stdout.buffer.write({text!r}.encode('utf-8'))\n"
_BODY_FAIL = ("sys.stderr.buffer.write('FAUX CLAUDE : panne simulee 0xC0FFEE'.encode('utf-8'))\n"
              "sys.exit(3)\n")
_BODY_SLEEP = "time.sleep({seconds!r})\nsys.stdout.buffer.write(b'trop tard')\n"


def _install_fake_claude(tmp_path, body, name="claude"):
    """Écrit le faux `claude` (script + shim) dans tmp_path ; rend (chemin du shim, chemin argv.json)."""
    argv_file = tmp_path / "argv.json"
    script = tmp_path / "fake_claude.py"
    script.write_text(_PRELUDE.format(argv_file=str(argv_file)) + body, encoding="utf-8")
    if sys.platform == "win32":
        shim = tmp_path / f"{name}.cmd"
        # `%*` transmet la queue d'arguments telle quelle, y compris l'argument VIDE de --allowedTools.
        shim.write_text(f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        shim = tmp_path / name
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        shim.chmod(0o755)
    return shim, argv_file


def _restrict_path_to(monkeypatch, directory):
    """PATH = ce seul répertoire (pas un préfixe) : le vrai `claude` de la machine devient inatteignable."""
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.delenv("AGAGI_CLAUDE_BIN", raising=False)


# ------------------------------------------------------------------------------------------------
# Résolution du binaire : PATH nu, variable d'environnement, argument explicite.
# ------------------------------------------------------------------------------------------------

def test_texte_ok_via_path_nu(tmp_path, monkeypatch):
    # Le faux claude imprime un texte fixe ; il est trouvé sous le nom NU "claude" via le PATH réduit.
    text = '{"name": "lewis_ref05", "params": {"lewis": true}, "rationale": "pression référentielle"}'
    _install_fake_claude(tmp_path, _BODY_TEXT.format(text=text))
    _restrict_path_to(monkeypatch, tmp_path)
    resolved = shutil.which("claude")
    assert resolved is not None and os.path.dirname(resolved).lower() == str(tmp_path).lower(), \
        "le seul `claude` atteignable doit être le FAUX"
    fn = claude_code_llm_fn()
    assert fn("peu importe") == text            # stdout BRUT, rien n'est parsé ici


def test_texte_ok_via_agagi_claude_bin(tmp_path, monkeypatch):
    # PATH vide de tout `claude` ; c'est AGAGI_CLAUDE_BIN qui désigne le faux (chemin complet du shim).
    shim, _ = _install_fake_claude(tmp_path, _BODY_TEXT.format(text="via env"), name="pas_claude")
    vide = tmp_path / "vide"
    vide.mkdir()
    _restrict_path_to(monkeypatch, vide)
    with pytest.raises(FileNotFoundError):       # sans la variable : rien à appeler (contraste)
        claude_code_llm_fn()("x")
    monkeypatch.setenv("AGAGI_CLAUDE_BIN", str(shim))
    assert claude_code_llm_fn()("x") == "via env"


def test_binary_explicite_prime_sur_env_et_path(tmp_path, monkeypatch):
    shim, _ = _install_fake_claude(tmp_path, _BODY_TEXT.format(text="via binary="), name="autre")
    vide = tmp_path / "vide"
    vide.mkdir()
    _restrict_path_to(monkeypatch, vide)
    monkeypatch.setenv("AGAGI_CLAUDE_BIN", str(tmp_path / "n_existe_pas"))
    assert claude_code_llm_fn(binary=str(shim))("x") == "via binary="


# ------------------------------------------------------------------------------------------------
# Contrat d'erreur : exit != 0 -> RuntimeError (stderr dedans) ; timeout -> TimeoutExpired REMONTÉE.
# ------------------------------------------------------------------------------------------------

def test_exit_non_nul_leve_runtimeerror_avec_stderr(tmp_path, monkeypatch):
    _install_fake_claude(tmp_path, _BODY_FAIL)
    _restrict_path_to(monkeypatch, tmp_path)
    with pytest.raises(RuntimeError) as exc:
        claude_code_llm_fn()("x")
    msg = str(exc.value)
    assert "panne simulee 0xC0FFEE" in msg      # le stderr du binaire est DANS le message
    assert "3" in msg                            # et son code de retour


@pytest.mark.timeout(60)
def test_timeout_remonte_timeoutexpired(tmp_path, monkeypatch):
    # Le faux claude dort 2 s ; timeout_s = 0.4 -> subprocess.TimeoutExpired remontée, jamais avalée
    # (une réponse absente ne doit pas devenir une chaîne vide que parse_demand_response rejetterait
    # comme « reponse LLM sans JSON » : l'appelant doit SAVOIR que c'est un timeout).
    _install_fake_claude(tmp_path, _BODY_SLEEP.format(seconds=2.0))
    _restrict_path_to(monkeypatch, tmp_path)
    with pytest.raises(subprocess.TimeoutExpired):
        claude_code_llm_fn(timeout_s=0.4)("x")


# ------------------------------------------------------------------------------------------------
# Transport : le prompt passe par STDIN, intact ; argv exact ; sortie brute.
# ------------------------------------------------------------------------------------------------

def test_stdin_recu_intact_accents_et_lignes(tmp_path, monkeypatch):
    _install_fake_claude(tmp_path, _BODY_ECHO)
    _restrict_path_to(monkeypatch, tmp_path)
    prompt = ("Ligne 1 : é, ç, €, à, ù — « guillemets »\n"
              "Ligne 2 : Réponds UNIQUEMENT en JSON : {\"name\": \"…\", \"params\": {}}\n"
              "\tLigne 3 avec tabulation, puis une ligne vide :\n"
              "\n"
              "Dernière ligne sans saut final")
    assert claude_code_llm_fn()(prompt) == prompt


def test_argv_exact_et_prompt_absent_des_argv(tmp_path, monkeypatch):
    _, argv_file = _install_fake_claude(tmp_path, _BODY_TEXT.format(text="ok"))
    _restrict_path_to(monkeypatch, tmp_path)
    sentinel = "PROMPT_SENTINELLE_9f3c_ne_doit_pas_etre_un_argument"
    assert claude_code_llm_fn()(sentinel) == "ok"
    argv = json.loads(argv_file.read_text(encoding="utf-8"))
    assert argv == ["-p", "--output-format", "text", "--allowedTools", ""]
    assert all(sentinel not in a for a in argv)


def test_allowed_tools_est_transmis_tel_quel(tmp_path, monkeypatch):
    _, argv_file = _install_fake_claude(tmp_path, _BODY_TEXT.format(text="ok"))
    _restrict_path_to(monkeypatch, tmp_path)
    claude_code_llm_fn(allowed_tools="Read,Grep")("x")
    argv = json.loads(argv_file.read_text(encoding="utf-8"))
    assert argv[argv.index("--allowedTools") + 1] == "Read,Grep"
