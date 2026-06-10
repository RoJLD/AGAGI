import os

from src.metaprog.secure_sandbox import validate_code, run_sandboxed, first_def_name


def validate_and_install_mutation(code_str: str) -> bool:
    """
    Sandboxing et Validation (Commandements 6 & 7 ; durci EDR 035).
    Gate AST + test ISOLÉ (hors-repo) AVANT d'écrire le fichier live `generated_ops.py`.
    Le code n'atteint le chemin chargé en live que s'il a passé la sécurité.
    """
    # 1. Gate statique : rejet immédiat du code dangereux (sans rien écrire/exécuter).
    ok, reason = validate_code(code_str)
    if not ok:
        print(f"[META-PROG] Code REJETE par le gate AST : {reason}")
        return False

    # 2. Test isolé (dossier temporaire hors-repo, subprocess -I, timeout) sur le code généré.
    fn = first_def_name(code_str) or "new_activation"   # nom détecté (Swish, custom_activation…)
    test_code = (
        "import numpy as np\n"
        f"_r = {fn}(np.array([-1.0, 0.0, 1.0]))\n"
        "assert _r.shape == (3,)\n"
        "assert not np.isnan(_r).any() and not np.isinf(_r).any()\n"
        "print('ok')\n"
    )
    ok2, reason2 = run_sandboxed(code_str, test_code)
    if not ok2:
        print(f"[META-PROG] Validation isolee echouee : {reason2}")
        return False

    # 3. Seulement maintenant : écrire le fichier live (chargé par l'agent après re-validation).
    sandbox_dir = os.path.join(os.path.dirname(__file__), "sandbox")
    os.makedirs(sandbox_dir, exist_ok=True)
    with open(os.path.join(sandbox_dir, "generated_ops.py"), "w", encoding="utf-8") as f:
        f.write(code_str)
    print("[META-PROG] Code validation passed (secure) !")
    return True

def compile_bytecode_to_python(bytecode) -> str:
    """
    Traduit l'array de bytecode de l'agent en code Python valide.
    L'agent écrit ainsi son propre algorithme d'activation.
    """
    lines = [
        "import numpy as np",
        "",
        "def new_activation(x):",
        "    # Code auto-généré par l'évolution (Pilier E)",
    ]
    
    if bytecode is None or len(bytecode) == 0:
        lines.append("    return np.tanh(x)")
        return "\n".join(lines) + "\n"
        
    for op in bytecode:
        op = int(op)
        if op == 0:
            lines.append("    x = np.tanh(x)")
        elif op == 1:
            lines.append("    x = np.maximum(x, 0)")
        elif op == 2:
            lines.append("    x = x * 0.5")
        elif op == 3:
            lines.append("    x = x + 0.1")
        elif op == 4:
            lines.append("    x = np.sin(x)")
        elif op == 5:
            lines.append("    x = np.cos(x)")
        elif op == 6:
            lines.append("    x = np.exp(-np.abs(x))") # Safe exp
        elif op == 7:
            lines.append("    x = np.log1p(np.abs(x))") # Safe log
            
    lines.append("    return x")
    return "\n".join(lines) + "\n"
