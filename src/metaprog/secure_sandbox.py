"""
src/metaprog/secure_sandbox.py — Sandbox sécurisée pour le code auto-généré (EDR 035, Vague 2).

Prérequis de la RSI (Commandement 6) : AVANT d'exécuter du code généré (par bytecode ou, demain,
par un vrai LLM), le valider et l'isoler. Défense en DEUX TEMPS, portable (Windows inclus) :

  1. GATE STATIQUE (AST) — `validate_code` : rejette le code dangereux *avant* tout écriture/exécution.
     Allowlist d'imports (deny-by-default), blocage des appels de capacités (exec/eval/open/…) et des
     accès dunder (`__globals__`, `__class__`… = vecteurs d'évasion de sandbox).
  2. EXÉCUTION ISOLÉE — `run_sandboxed` : dossier temporaire HORS-repo, subprocess `python -I -S`
     (mode isolé : ignore env & site), environnement scrubé, timeout strict, nettoyage.

L'isolation OS-complète (conteneur/seccomp) reste la cible long terme ; ici, la digue est l'AST gate.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile

# Seuls ces modules peuvent être importés par le code généré (deny-by-default).
ALLOWED_MODULES = {"numpy", "math"}

# Appels (par nom) interdits : capacités système & vecteurs d'évasion.
FORBIDDEN_CALLS = {
    "exec", "eval", "compile", "__import__", "open", "input", "breakpoint",
    "globals", "locals", "vars", "getattr", "setattr", "delattr", "memoryview",
    "exit", "quit", "help",
}
# Noms interdits utilisés directement.
FORBIDDEN_NAMES = {"__builtins__", "__import__", "__loader__", "__spec__"}


class _Validator(ast.NodeVisitor):
    def __init__(self):
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            top = alias.name.split(".")[0]
            if top not in ALLOWED_MODULES:
                self.violations.append(f"import interdit: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        top = (node.module or "").split(".")[0]
        if top not in ALLOWED_MODULES:
            self.violations.append(f"from-import interdit: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            self.violations.append(f"appel interdit: {node.func.id}")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Accès dunder = évasion classique (__globals__, __class__, __subclasses__, …).
        if node.attr.startswith("__") and node.attr.endswith("__"):
            self.violations.append(f"acces dunder interdit: {node.attr}")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in FORBIDDEN_NAMES:
            self.violations.append(f"nom interdit: {node.id}")
        self.generic_visit(node)


def validate_code(code: str):
    """(ok: bool, raison: str). Gate statique : rejette le code dangereux sans l'exécuter."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"syntaxe invalide: {e}"
    v = _Validator()
    v.visit(tree)
    if v.violations:
        return False, "; ".join(sorted(set(v.violations)))
    return True, "ok"


def first_def_name(code: str):
    """Nom de la 1re fonction définie (pour tester le code généré sans coder le nom en dur)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return node.name
    return None


def run_sandboxed(code: str, test_code: str, timeout: float = 5.0):
    """Valide (AST) PUIS exécute le test dans un dossier temporaire isolé (hors-repo),
    subprocess `python -I -S`, env scrubé, timeout. Renvoie (ok: bool, raison: str)."""
    ok, reason = validate_code(code)
    if not ok:
        return False, f"REJETE par l'AST gate: {reason}"
    ok_t, reason_t = validate_code(test_code)
    if not ok_t:
        return False, f"test REJETE par l'AST gate: {reason_t}"

    work = tempfile.mkdtemp(prefix="agiseed_sbx_")     # HORS du repo
    try:
        # Code + test combinés en UN fichier (pas d'import croisé ; `new_activation` défini au-dessus).
        script = code.rstrip() + "\n\n# --- test injecté ---\n" + test_code
        path = os.path.join(work, "sbx_script.py")
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        # `-I` : ignore env & user-site, retire le dossier du script de sys.path (site système
        # conservé -> numpy OK). Env scrubé. Dossier temporaire hors-repo. Timeout strict.
        env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
        try:
            result = subprocess.run(
                [sys.executable, "-I", path],
                cwd=work, capture_output=True, text=True, timeout=timeout, env=env,
            )
        except subprocess.TimeoutExpired:
            return False, "timeout (boucle infinie ?)"
        if result.returncode == 0:
            return True, "ok"
        return False, f"echec test: {result.stderr.strip()[:300]}"
    finally:
        shutil.rmtree(work, ignore_errors=True)
