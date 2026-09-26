"""P2.116 : le pre-commit porte son compte d'appels au diff de l'index dans une VARIABLE (`APPELS_ATTENDUS`) et se
REFUSE si le recompte diverge — sur la copie QUI TOURNE (`$0`) et sur celle de l'INDEX (ce qui sera committé).

Le défaut : ce compte n'était publié que dans deux commentaires (pre-commit, commit-msg), recomputés par UN témoin de
la suite complète (`test_hook_on_merge.py::test_le_nombre_d_appels_annonce_dans_les_commentaires_se_RECOMPUTE`),
qu'aucune porte, ni la porte 15, ni la CI n'exécutaient. Vrai de chaque côté, FAUX à l'union de la fusion pm-portes
(17 puis 20), attrapé par une revue et non par un cliquet.

Ces cas extraient le bloc `AGAGI:APPELS-ATTENDUS` VERBATIM du hook versionné, le posent dans un crochet JOUET dont on
connaît le compte, et l'exécutent avec `sh`. Aucun ne touche le dépôt réel : hors dépôt, `GIT_CEILING_DIRECTORIES`
borne la découverte de git ; dans le dépôt jetable, l'environnement est purgé de `GIT_*` (règle à deux faces du dépôt :
un sous-processus qui vise un AUTRE dépôt isole ses variables git, sinon un GIT_INDEX_FILE hérité du commit en cours
ferait juger l'index du commit extérieur).
"""
import os
import re
import shutil
import subprocess

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PRE_COMMIT = os.path.join(_ROOT, "tools", "hooks", "pre-commit")
_DEBUT = "# >>> AGAGI:APPELS-ATTENDUS >>>"
_FIN = "# <<< AGAGI:APPELS-ATTENDUS <<<"
_MOTIF = re.compile(r"^[^#\n]*git diff --cached --name-only", re.M)     # celui du hook et de test_hook_on_merge
_DECL = re.compile(r"^APPELS_ATTENDUS=(\d+)", re.M)

pytestmark = pytest.mark.skipif(shutil.which("sh") is None,
                                reason="sh introuvable : le bloc shell du hook n'est pas exécutable ici")


def _lire(chemin):
    with open(chemin, encoding="utf-8") as fh:
        return fh.read()


def _bloc():
    src = _lire(_PRE_COMMIT)
    i = src.find(_DEBUT)
    j = src.find(_FIN, i)
    assert i >= 0 and j > i, "bloc AGAGI:APPELS-ATTENDUS absent de tools/hooks/pre-commit"
    return src[i:j + len(_FIN)]


def _jouet(declare, appels, crlf=False):
    """Un crochet jouet : le bloc réel, sa déclaration remplacée par `declare`, puis `appels` lignes que le motif
    compte (`:` est le no-op du shell : rien ne s'exécute)."""
    bloc = _DECL.sub(f"APPELS_ATTENDUS={declare}", _bloc(), count=1)
    corps = "#!/bin/sh\nfail=0\n" + bloc + "\n" + ": git diff --cached --name-only\n" * appels + "exit $fail\n"
    return corps.replace("\n", "\r\n") if crlf else corps


def _env(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CEILING_DIRECTORIES"] = str(tmp_path.parent)
    return env


def _lancer(tmp_path, texte, cwd=None):
    p = tmp_path / "pre-commit-jouet"
    p.write_bytes(texte.encode("utf-8"))
    r = subprocess.run(["sh", str(p)], cwd=str(cwd or tmp_path), capture_output=True, env=_env(tmp_path),
                       timeout=60)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")


def _depot_avec_index(tmp_path, contenu_hook):
    """Dépôt jetable dont l'INDEX porte `tools/hooks/pre-commit` = `contenu_hook` (stagé, jamais committé)."""
    if shutil.which("git") is None:
        pytest.skip("git introuvable")
    d = tmp_path / "jetable"
    (d / "tools" / "hooks").mkdir(parents=True)
    (d / "tools" / "hooks" / "pre-commit").write_bytes(contenu_hook.encode("utf-8"))
    env = _env(tmp_path)
    for args in (["init", "-q"], ["add", "tools/hooks/pre-commit"]):
        r = subprocess.run(["git", "-C", str(d), *args], capture_output=True, env=env, timeout=60)
        assert r.returncode == 0, r.stderr.decode("utf-8", errors="replace")
    return d


def test_le_hook_REEL_declare_EXACTEMENT_ses_appels():
    src = _lire(_PRE_COMMIT)
    decl = _DECL.findall(src)
    assert len(decl) == 1, f"une seule déclaration APPELS_ATTENDUS attendue, trouvé {decl}"
    reel = len(_MOTIF.findall(src))
    assert reel > 0 and int(decl[0]) == reel, (decl[0], reel)


def test_le_motif_s_EXCLUT_de_lui_meme_le_bloc_seul_ne_compte_AUCUN_appel():
    """Le bloc cite le texte cherché (dans `grep -c '^[^#]*…'`) : s'il se comptait, ajouter le bloc aurait changé le
    compte qu'il vérifie. `[^#]*` ne franchit pas le « # » de sa propre classe de caractères."""
    assert _MOTIF.findall(_bloc()) == []


def test_CONTRE_EXEMPLE_GELE_une_copie_qui_declare_20_et_porte_21_appels_est_REFUSEE(tmp_path):
    rc, sortie = _lancer(tmp_path, _jouet(20, 21))
    assert rc == 1, sortie
    assert "APPELS" in sortie and "21" in sortie and "20" in sortie, sortie


def test_la_meme_copie_COHERENTE_passe(tmp_path):
    rc, sortie = _lancer(tmp_path, _jouet(21, 21))
    assert rc == 0, sortie


@pytest.mark.skipif(os.name != "nt", reason="la copie déployée n'est en CRLF que sous Windows (core.autocrlf)")
def test_une_copie_deployee_en_CRLF_se_juge_comme_en_LF(tmp_path):
    """Mesuré le 2026-09-26 : la copie déployée dans .git/hooks est ENTIÈREMENT en CRLF (747 lignes). Le sh de Git pour
    Windows retire le \\r d'une affectation ; ce cas le fige, pour que la vérification ne se retourne pas contre la
    flotte le jour où ce comportement changerait."""
    assert _lancer(tmp_path, _jouet(21, 21, crlf=True))[0] == 0
    assert _lancer(tmp_path, _jouet(20, 21, crlf=True))[0] == 1


def test_la_copie_de_l_INDEX_incoherente_est_REFUSEE_meme_quand_celle_qui_tourne_est_coherente(tmp_path):
    """La moitié qui protège la FLOTTE : un hook incohérent committé puis recopié bloquerait tous les worktrees
    (core.hooksPath est absolu). C'est l'INDEX qui se juge au commit, avant le cp."""
    depot = _depot_avec_index(tmp_path, _jouet(20, 21))
    rc, sortie = _lancer(tmp_path, _jouet(21, 21), cwd=depot)
    assert rc == 1, sortie
    assert "INDEX" in sortie, sortie


def test_une_copie_d_index_SANS_declaration_est_celle_d_une_branche_anterieure_DITE_et_non_bloquante(tmp_path):
    depot = _depot_avec_index(tmp_path, "#!/bin/sh\n" + ": git diff --cached --name-only\n" * 3 + "exit 0\n")
    rc, sortie = _lancer(tmp_path, _jouet(21, 21), cwd=depot)
    assert rc == 0, sortie
    assert "anterieure" in sortie, sortie


def test_hors_depot_la_copie_de_l_index_est_DITE_non_verifiee_jamais_tue(tmp_path):
    rc, sortie = _lancer(tmp_path, _jouet(21, 21))
    assert rc == 0 and "NON verifiee" in sortie, sortie
