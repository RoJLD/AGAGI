# -*- coding: utf-8 -*-
"""P2.136 — promotion d'E21 : le hook PostToolUse Bash SIGNALE une commande dont le canal shell a pu transformer le
texte (heredoc porteur d'échappements ou de backticks, backtick nu entre guillemets doubles, `-m` porteur
d'échappements). Il ne bloque pas — en PostToolUse la mutilation a déjà eu lieu — : il le dit à l'agent, par la seule
forme documentée (un JSON hookSpecificOutput.additionalContext seul sur stdout, code 0), et dit quoi faire.

Troisième occurrence, celle qui a déclenché la promotion (2026-09-26, agagi-32) : un script écrit par un heredoc
`python - <<'EOF'` a reçu ses continuations de ligne en « \\n » LITTÉRAUX ; pytest n'a reçu aucun chemin et a lancé
ZÉRO test — un vert qui ne mesurait rien, attrapé parce que le COMPTE de tests était lu.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from tools.pm import bash_hook as H  # noqa: E402

# La commande du 2026-09-26, dans sa forme : un heredoc dont le corps porte des « \\\n » destinés à devenir des
# continuations de ligne dans le script écrit. Chaîne BRUTE : ce sont bien trois barres obliques inverses puis « n ».
_COMMANDE_DU_JOUR = r'''SCR="C:/scratch/p2122" && python - "$SCR" <<'EOF'
import sys, os
S = sys.argv[1]
q = os.path.join(S, "lin133.sh")
open(q, "w", encoding="utf-8", newline="\n").write("echo debut\n"
    + "python -m pytest -q --timeout=600 tests/sandbox/test_refutateur_workflow_refus.py \\\n"
    + "  tests/sandbox/test_refutateur_temoins.py 2>&1 | tail -3\n")
print("script Linux pret")
EOF'''


def test_P2_136_CONTRE_EXEMPLE_le_heredoc_du_jour_est_SIGNALE():
    """LE CONTRE-EXEMPLE GELÉ : la forme exacte de la 3e occurrence d'E21."""
    assert "heredoc" in H.mutilation_possible(_COMMANDE_DU_JOUR)


def test_P2_136_un_backtick_NU_entre_guillemets_doubles_est_SIGNALE_le_mecanisme_du_2026_09_07():
    """La 1re occurrence : « mon `git commit` NU » est parti « mon  NU ». Entre apostrophes, ou échappé, bash ne
    substitue rien : pas de signal."""
    assert H.mutilation_possible('git commit -m "mon `git commit` NU"') == ["substitution"]
    assert H.mutilation_possible('python -c "print(`id`)"') == ["substitution"]
    assert H.mutilation_possible("git commit -m 'mon `git commit` NU'") == []
    assert H.mutilation_possible('git commit -m "mon \\`git commit\\` NU"') == []


def test_P2_136_un_message_m_porteur_d_echappement_est_SIGNALE():
    """Un `-m` entre guillemets doubles qui porte « \\n » : git reçoit une barre oblique et un « n », pas un saut."""
    assert H.mutilation_possible('git commit -m "ligne 1\\nligne 2"') == ["message"]


def test_P2_136_SPECIFICITE_un_heredoc_sain_et_les_commandes_ordinaires_se_TAISENT():
    """Sans ce cas, un signal qui crierait toujours serait appris par cœur, puis ignoré."""
    sain = "python - <<'EOF'\nprint('bonjour')\nx = 1 + 2\nEOF"
    for commande in (sain, "ls -la", 'python -c "print(1)"', "git status --short", "echo 'a `b` c'", "", None):
        assert H.mutilation_possible(commande) == [], commande


def test_P2_136_main_emet_le_JSON_additionalContext_et_se_TAIT_sinon(capsys):
    """La sortie du hook : un JSON seul sur stdout, hookEventName PostToolUse, le motif et le remède dans le texte ;
    rien du tout pour une commande saine. Le code reste 0 : le hook ne bloque jamais."""
    assert H.main(stdin=json.dumps({"tool_input": {"command": 'echo "mon `date` NU"'}})) == 0
    sortie = json.loads(capsys.readouterr().out)
    contexte = sortie["hookSpecificOutput"]["additionalContext"]
    assert sortie["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "E21" in contexte and "substitution" in contexte and "Write" in contexte
    assert H.main(stdin=json.dumps({"tool_input": {"command": "ls -la"}})) == 0
    assert capsys.readouterr().out == ""
