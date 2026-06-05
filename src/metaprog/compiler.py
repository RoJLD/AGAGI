import subprocess
import os

def validate_and_install_mutation(code_str: str) -> bool:
    """
    Sandboxing et Validation (Commandements 6 & 7).
    Prend du code généré par l'IA, l'écrit dans la sandbox et lance pytest.
    """
    sandbox_dir = os.path.join(os.path.dirname(__file__), "sandbox")
    os.makedirs(sandbox_dir, exist_ok=True)
    
    ops_file = os.path.join(sandbox_dir, "generated_ops.py")
    with open(ops_file, "w", encoding="utf-8") as f:
        f.write(code_str)
        
    # Run pytest on the sandbox
    test_file = os.path.join(sandbox_dir, "test_metaprog.py")
    try:
        # Timeout de 5.0 secondes (Commandement 6) pour éviter les boucles infinies
        result = subprocess.run(
            ["pytest", test_file, "-q"],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        if result.returncode == 0:
            print("[META-PROG] Code validation passed!")
            # Si succès, le fichier generated_ops.py est prêt à l'emploi.
            # Dans l'avenir, on l'injectera dans le dictionnaire de MutationConfig.
            return True
        else:
            print(f"[META-PROG] Validation failed:\n{result.stdout}\n{result.stderr}")
            return False
        return False
    except subprocess.TimeoutExpired:
        print("[META-PROG] Validation timed out (Infinite loop ?)")
        return False

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
