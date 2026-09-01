"""Cliquet : aucun test ne doit AVALER sa propre assertion — un test qui ne peut pas échouer ne teste rien.

Mesuré le 2026-09-01 dans `tests/test_fixes.py` : trois tests entouraient leurs assertions d'un
`try/except Exception` qui imprimait « [FAIL] » puis faisait `return False`. `AssertionError` hérite
d'`Exception`, donc l'échec était attrapé, et pytest — qui ne regarde que les exceptions qui REMONTENT —
comptait le test comme PASSÉ.

⚠️ CE N'ÉTAIT PAS THÉORIQUE. En retirant le `try/except`, `test_vectorized_forward` a immédiatement
ÉCHOUÉ : `MambaBatchModel.forward` renvoie un TUPLE `(preds, compute_spent)` (`mamba_agent.py:512`),
et le test le traitait comme un tableau **depuis un changement d'API**. Il « passait » en imprimant
[FAIL] dans un flux que personne ne lit. Une assertion avalée ne cache pas rien — elle cachait ça.

NUANCE, et elle est essentielle : un `except` qui appelle `pytest.fail(...)` ou qui RE-LÈVE n'avale
rien, il TRADUIT un crash en échec. C'est légitime et fréquent. Les signaler serait interdire un idiome
correct, et le cliquet deviendrait du bruit qu'on désactive.
"""
import ast
import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

_TESTS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Dette LÉGATAIRE gelée. VIDE, et c'est délibéré : les 4 cas connus ont été corrigés dans la même
# passe. Ajouter une entrée ici demande d'écrire POURQUOI le test ne peut pas laisser remonter.
_TOLERES = frozenset()


def _handler_relaie(handler):
    """Ce gestionnaire TRADUIT-il l'échec (pytest.fail / raise) au lieu de l'avaler ?"""
    for n in ast.walk(handler):
        if isinstance(n, ast.Raise):
            return True
        if isinstance(n, ast.Call):
            f = n.func
            nom = getattr(f, "attr", None) or getattr(f, "id", None)
            if nom in ("fail", "skip", "xfail", "exit"):
                return True
    return False


def _est_large(handler):
    """`except:` nu, `except Exception`, `except BaseException` — tout ce qui capture AssertionError."""
    t = handler.type
    if t is None:
        return True
    if isinstance(t, ast.Name):
        return t.id in ("Exception", "BaseException", "AssertionError")
    if isinstance(t, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id in ("Exception", "BaseException", "AssertionError")
                   for e in t.elts)
    return False


def _scan():
    """[(fichier, test, ligne)] pour chaque test dont une assertion est avalée."""
    trouve = []
    for root, _, files in os.walk(_TESTS):
        if "__pycache__" in root:
            continue
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            try:
                tree = ast.parse(io.open(path, encoding="utf-8", errors="ignore").read())
            except SyntaxError:
                continue
            rel = os.path.relpath(path, os.path.dirname(_TESTS)).replace(os.sep, "/")
            for node in ast.walk(tree):
                if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
                    continue
                for essai in [n for n in ast.walk(node) if isinstance(n, ast.Try)]:
                    a_assert = any(isinstance(n, ast.Assert)
                                   for corps in essai.body for n in ast.walk(corps))
                    if not a_assert:
                        continue
                    if any(_est_large(h) and not _handler_relaie(h) for h in essai.handlers):
                        trouve.append((rel, node.name, essai.lineno))
                        break
    return trouve


def test_no_test_swallows_its_own_assertion():
    """⚠️ LE cliquet. Baseline VIDE : aucune dette tolérée."""
    avales = [(f, n, l) for f, n, l in _scan() if f"{f}::{n}" not in _TOLERES]
    assert not avales, (
        "test(s) dont l'assertion est AVALÉE par un `except` large — ils ne peuvent pas échouer :\n"
        + "\n".join(f"    {f}:{l}  {n}" for f, n, l in avales)
        + "\n  Laisser l'assertion REMONTER, ou traduire le crash avec `pytest.fail(...)`.")


def test_the_detector_SEES_a_swallowed_assertion(tmp_path, monkeypatch):
    """⚠️ Garde de la garde. Sans ce cas, un détecteur cassé rendrait une liste vide et le cliquet
    ci-dessus passerait au vert en ne vérifiant plus rien (classe E4)."""
    d = tmp_path / "tests"
    d.mkdir()
    (d / "test_faux.py").write_text(
        "def test_avale():\n"
        "    try:\n"
        "        assert 1 == 2\n"
        "    except Exception:\n"
        "        pass\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "_TESTS", str(d))
    assert any(n == "test_avale" for _, n, _ in _scan()), "le détecteur ne voit plus rien"


def test_the_detector_SPARES_a_handler_that_relays_the_failure(tmp_path, monkeypatch):
    """⚠️ SPÉCIFICITÉ. Un `except` qui appelle `pytest.fail` TRADUIT un crash en échec — idiome
    correct et fréquent. Le signaler rendrait le cliquet inutilisable, donc désactivé."""
    d = tmp_path / "tests"
    d.mkdir()
    (d / "test_ok.py").write_text(
        "import pytest\n"
        "def test_traduit():\n"
        "    try:\n"
        "        assert 1 == 1\n"
        "    except Exception as e:\n"
        "        pytest.fail(str(e))\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "_TESTS", str(d))
    assert _scan() == [], "un gestionnaire qui relaie l'échec ne doit pas être signalé"
