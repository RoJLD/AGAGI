from src.metaprog.compiler import validate_and_install_mutation

def generate_and_test_new_activation():
    """
    Superviseur Codeur (Pilier 4).
    Simule la génération de code par un LLM (via LangGraph) pour créer de nouvelles
    fonctions d'activation vectorisées (Commandement 3 & 7).
    """
    print("[SUPERVISOR-CODER] Generating new activation function 'Swish'...")
    
    # Simulation du code LLM (ex: Swish = x * sigmoid(x))
    llm_code = """import numpy as np

def custom_activation(x):
    # Swish activation : f(x) = x * sigmoid(x)
    # Excellente pour contrer la disparition du gradient tout en gardant une non-linéarité
    return x * (1.0 / (1.0 + np.exp(-x)))
"""
    
    success = validate_and_install_mutation(llm_code)
    if success:
        print("[SUPERVISOR-CODER] New activation function 'Swish' successfully installed into the sandbox.")
    else:
        print("[SUPERVISOR-CODER] Mutation was rejected by the sandbox tests.")
        
    return success

if __name__ == "__main__":
    generate_and_test_new_activation()
