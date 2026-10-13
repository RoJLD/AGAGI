"""P2.157 (2026-10-13) — contre-exemples GELÉS du bloc AGAGI:INTERPRETE de `tools/hooks/pre-commit`.

Le crochet lançait ses portes avec le « python » du PATH. Le 30/09, un Python 3.14 SANS numpy ni pytest s'est installé
en tête du PATH des processus de la batcave : la porte 15 refusait tout commit qui la déclenchait, et une porte qui
avalerait l'ImportError rendrait vert. Le bloc CHOISIT l'interpréteur (AGAGI_PYTHON épinglé, puis python, python3,
py -3.13) et REFUSE s'il n'en trouve aucun qui ait numpy ET pytest.

Ces cas posent, dans un dépôt git JETABLE, un crochet JOUET fait des blocs AGAGI:INTERPRETE et AGAGI:PORTE-ABSENTE
copiés VERBATIM du crochet versionné, puis une porte fantôme qui dit quel interpréteur l'a lancée. Le PATH du crochet
est RÉDUIT à un dossier de cales (`python`, `python3`, `py`) dont chacune lance soit le VRAI interpréteur de ce test,
soit le même en `-S` — donc SANS site-packages, donc sans numpy ni pytest. Aucun ne touche le dépôt réel ; `GIT_*` est
retiré (règle à deux faces : un dépôt jetable n'est pas le dépôt courant).
"""
import os
import shutil
import subprocess
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PRE_COMMIT = os.path.join(_ROOT, "tools", "hooks", "pre-commit")
_BLOCS = ("AGAGI:INTERPRETE", "AGAGI:PORTE-ABSENTE")
_GIT = shutil.which("git")
_REEL = sys.executable.replace("\\", "/")

pytestmark = pytest.mark.skipif(_GIT is None, reason="git introuvable : le crochet n'est pas mesurable ici")


def _lire(chemin):
    with open(chemin, encoding="utf-8") as fh:
        return fh.read()


def _bloc(nom):
    src = _lire(_PRE_COMMIT)
    debut, fin = f"# >>> {nom} >>>", f"# <<< {nom} <<<"
    i = src.find(debut)
    assert i >= 0, f"marqueur « {debut} » absent de tools/hooks/pre-commit"
    j = src.find(fin, i)
    assert j >= 0, f"marqueur « {fin} » absent de tools/hooks/pre-commit"
    return src[i:j + len(fin)]


def _hook_jouet():
    return ("#!/bin/sh\nfail=0\n" + "\n".join(_bloc(n) for n in _BLOCS) + "\n"
            "PYTHONIOENCODING=utf-8 python tools/check_fantome.py || {\n"
            "  echo \"REFUS DE LA PORTE FANTOME\"\n  fail=1\n}\nexit $fail\n")


# La porte fantôme dit QUI l'a lancée ET si numpy lui était trouvable : une cale « -S » lance le MÊME exécutable que le
# vrai interpréteur, donc `sys.executable` seul ne distinguerait pas les deux.
_FANTOME = ("import sys, importlib.util as u\n"
            "print('fantome-execute par ' + sys.executable + ' | numpy=' + str(u.find_spec('numpy') is not None))\n")


def _cale(dossier, nom, sans_dependances, lanceur=False):
    """Une cale shell nommée `nom` : le vrai interpréteur, ou le même en -S (sans numpy ni pytest). `lanceur` imite
    `py` : elle avale l'option de version « -3.13 » qui précède les arguments."""
    corps = "#!/bin/sh\n"
    if lanceur:
        corps += "if [ \"$1\" = \"-3.13\" ]; then shift; fi\n"
    corps += f"exec \"{_REEL}\" {'-S ' if sans_dependances else ''}\"$@\"\n"
    p = os.path.join(dossier, nom)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(corps)
    os.chmod(p, 0o755)


class _Depot:
    def __init__(self, tmp_path, cales, epingle=None):
        self.p = str(tmp_path / "jetable")
        os.makedirs(os.path.join(self.p, "tools"))
        dossier_cales = str(tmp_path / "cales")
        os.makedirs(dossier_cales)
        for nom, sans, lanceur in cales:
            _cale(dossier_cales, nom, sans, lanceur)
        self.env_git = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        chemin = [dossier_cales]
        if os.name == "nt":
            # Git pour Windows cherche l'interpréteur du shebang (`/bin/sh`) dans le PATH : sans le dossier de `sh`,
            # « cannot spawn .githooks/pre-commit » (mesuré au premier essai). Ce dossier ne doit porter AUCUN python,
            # sinon il deviendrait un candidat que le test ne maîtrise pas. Sous Linux, le shebang est absolu.
            sh = shutil.which("sh")
            assert sh, "sh introuvable : Git pour Windows ne peut pas lancer le crochet"
            d = os.path.dirname(sh)
            intrus = [f for f in os.listdir(d) if f.lower().split(".")[0] in ("python", "python3", "py")]
            assert not intrus, f"le dossier de sh porte un interpréteur : {intrus}"
            chemin.append(d)
        self.env_crochet = dict(self.env_git, PATH=os.pathsep.join(chemin))
        self.env_crochet.pop("AGAGI_PYTHON", None)
        if epingle is not None:
            self.env_crochet["AGAGI_PYTHON"] = epingle
        self.git("init", "-q", "-b", "base", ".", env=self.env_git)
        hooks = os.path.join(self.p, ".githooks")
        os.makedirs(hooks)
        with open(os.path.join(hooks, "pre-commit"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_hook_jouet())
        os.chmod(os.path.join(hooks, "pre-commit"), 0o755)
        with open(os.path.join(self.p, "tools", "check_fantome.py"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_FANTOME)
        self.git("add", "tools/check_fantome.py", env=self.env_git)
        self.git("commit", "-q", "--no-verify", "-m", "base", env=self.env_git)
        self.git("config", "core.hooksPath", hooks, env=self.env_git)
        self.tete = self.git("rev-parse", "HEAD", env=self.env_git)[1].strip()

    def git(self, *args, env, check=True):
        r = subprocess.run([_GIT, "-C", self.p, "-c", "user.name=t", "-c", "user.email=t@t", *args],
                           capture_output=True, env=env, timeout=120)
        sortie = (r.stdout + r.stderr).decode("utf-8", errors="replace")
        if check and r.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} a échoué ({r.returncode}) :\n{sortie}")
        return r.returncode, sortie

    def commit_essai(self):
        with open(os.path.join(self.p, "essai.txt"), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        self.git("add", "essai.txt", env=self.env_git)
        code, sortie = self.git("commit", "-q", "-m", "essai", env=self.env_crochet, check=False)
        tete = self.git("rev-parse", "HEAD", env=self.env_git)[1].strip()
        return code, sortie, tete != self.tete


def _lance_par(sortie):
    """(exécutable normalisé, numpy trouvable) de la porte fantôme, ou None si aucune porte n'a tourné."""
    lignes = [l for l in sortie.splitlines() if l.startswith("fantome-execute par ")]
    if not lignes:
        return None
    exe, _, numpy = lignes[-1][len("fantome-execute par "):].rpartition(" | numpy=")
    return os.path.normcase(os.path.realpath(exe.strip())), numpy.strip() == "True"


_VRAI = (os.path.normcase(os.path.realpath(sys.executable)), True)      # le vrai interpréteur, AVEC numpy


def test_P2_157_un_interpreteur_EPINGLE_sans_numpy_est_REFUSE_jamais_remplace(tmp_path):
    """AGAGI_PYTHON désigne un Python sans numpy ni pytest, et un BON `python` attend dans le PATH : le crochet doit
    REFUSER, pas se rabattre sur lui — une épingle cassée remplacée en silence serait la classe E32."""
    sans = tmp_path / "epingle_sans"
    sans.mkdir()
    _cale(str(sans), "python", sans_dependances=True)
    d = _Depot(tmp_path, [("python", False, False)], epingle=str(sans / "python").replace("\\", "/"))
    code, sortie, avance = d.commit_essai()
    assert code != 0 and not avance, sortie
    assert "REFUS (P2.157)" in sortie and "AGAGI_PYTHON" in sortie and "SANS numpy, pytest" in sortie, sortie
    assert _lance_par(sortie) is None, "une porte a tourné malgré le refus :\n" + sortie


def test_P2_157_un_interpreteur_EPINGLE_qui_convient_lance_les_portes(tmp_path):
    d = _Depot(tmp_path, [("python", True, False)], epingle=_REEL)
    code, sortie, avance = d.commit_essai()
    assert code == 0 and avance, sortie
    assert _lance_par(sortie) == _VRAI, sortie
    assert "interpréteur des portes : " + _REEL in sortie, sortie


def test_P2_157_sans_epingle_le_PREMIER_candidat_qui_convient_gagne_et_le_choix_est_DIT(tmp_path):
    """Le `python` du PATH n'a pas numpy (le cas mesuré de la batcave) : `python3`, qui l'a, lance les portes."""
    d = _Depot(tmp_path, [("python", True, False), ("python3", False, False)])
    code, sortie, avance = d.commit_essai()
    assert code == 0 and avance, sortie
    assert _lance_par(sortie) == _VRAI, sortie
    assert "interpréteur des portes : python3 (Python " in sortie, sortie


def test_P2_157_le_lanceur_py_3_13_est_le_DERNIER_repli(tmp_path):
    d = _Depot(tmp_path, [("python", True, False), ("python3", True, False), ("py", False, True)])
    code, sortie, avance = d.commit_essai()
    assert code == 0 and avance, sortie
    assert _lance_par(sortie) == _VRAI, sortie
    assert "interpréteur des portes : py -3.13 (Python " in sortie, sortie


def test_P2_157_AUCUN_candidat_ne_convient_REFUS_qui_nomme_CHAQUE_essai(tmp_path):
    d = _Depot(tmp_path, [("python", True, False)])
    code, sortie, avance = d.commit_essai()
    assert code != 0 and not avance, sortie
    assert "REFUS (P2.157)" in sortie, sortie
    for essai in ("python (Python ", "SANS numpy, pytest", "python3 (absent)", "py -3.13 (absent)"):
        assert essai in sortie, f"essai non nommé : {essai!r}\n{sortie}"
    assert _lance_par(sortie) is None, "une porte a tourné malgré le refus :\n" + sortie


def test_P2_157_le_choix_precede_TOUTE_porte_du_crochet_versionne():
    """Le bloc ne protège que s'il passe AVANT la première porte : déplacé plus bas, des portes tourneraient sous un
    interpréteur non vérifié. Et le lanceur de PORTE-ABSENTE consomme bien le choix."""
    src = _lire(_PRE_COMMIT)
    fin = src.find("# <<< AGAGI:INTERPRETE <<<")
    assert fin >= 0
    premiere = min(i for i in (src.find("\n" + l) for l in src.splitlines()
                               if not l.lstrip().startswith("#") and "python tools/check_" in l) if i >= 0)
    assert fin < premiere, "une porte est lancée AVANT le choix de l'interpréteur"
    assert 'command "${AGAGI_PY:-python}" ${AGAGI_PY_ARG:-} "$@"' in _bloc("AGAGI:PORTE-ABSENTE")
