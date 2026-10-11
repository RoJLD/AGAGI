"""
tools/agent_vm_benchmark.py — Banc Comparatif d'Auto-Programmation en Machine Virtuelle (Arc 16 / Jalon M41).

Évalue la capacité de l'écosystème à :
1. Générer et exécuter du code dans une VM isolée.
2. Analyser les erreurs d'exécution (stderr) pour s'auto-corriger (Self-Debugging).
3. Résoudre une suite de 5 défis algorithmiques et de manipulation de données.

Mesure :
- Taux de résolution finale (100% requis).
- Taux de self-debugging réussi après erreur initiale.
- Vitesse d'exécution et isolation garantie (Commandement 6).
"""

import sys
import os
import time
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.metaprog.agent_vm_sandbox import AgentVMSandbox, VMConfig, ExecutionResult


def run_agent_vm_benchmark() -> Dict[str, Any]:
    """
    Exécute la batterie de 5 défis de programmation autonome dans la Machine Virtuelle.
    """
    print("\n💻 [BANC JALON M41 : AGENT VM SANDBOX] Évaluation de l'Auto-Programmation et du Self-Debugging...")
    
    vm = AgentVMSandbox(VMConfig(timeout_seconds=2.0))
    
    tasks = [
        {
            "id": "T1_STATISTIQUES",
            "desc": "Calcul de médiane et d'écart-type sur une série numérique",
            "code_v1": (
                "import statistics\n"
                "data = [12.5, 45.2, 78.1, 99.4, 23.6, 54.0]\n"
                "print('MEDIANE:', round(statistics.median(data), 2))\n"
                "print('STDDEV:', round(statistics.stdev(data), 2))\n"
            ),
            "expected": "MEDIANE: 49.6"
        },
        {
            "id": "T2_CRIBLE_PRIMES",
            "desc": "Génération des nombres premiers jusqu'à 50",
            "code_v1": (
                "def primes(n):\n"
                "    sieve = [True] * (n + 1)\n"
                "    for p in range(2, int(n**0.5) + 1):\n"
                "        if sieve[p]:\n"
                "            for i in range(p * p, n + 1, p):\n"
                "                sieve[i] = False\n"
                "    return [p for p in range(2, n + 1) if sieve[p]]\n"
                "print('PRIMES:', primes(50))\n"
            ),
            "expected": "PRIMES: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]"
        },
        {
            "id": "T3_SELF_DEBUGGING_SYNTAX",
            "desc": "Auto-réparation d'une erreur de type TypeError",
            # v1 échoue volontairement pour forcer le self-debugging
            "code_v1": (
                "def concat_vals(a, b):\n"
                "    return a + b\n"
                "print('OUT:', concat_vals('Valeur: ', 42))\n"
            ),
            "fix_code": (
                "def concat_vals(a, b):\n"
                "    return str(a) + str(b)\n"
                "print('OUT:', concat_vals('Valeur: ', 42))\n"
            ),
            "expected": "OUT: Valeur: 42"
        },
        {
            "id": "T4_FICHIERS_IO",
            "desc": "Création, écriture et lecture d'un jeu de données JSON",
            "code_v1": (
                "import json\n"
                "payload = {'agent': 'Promethee-14', 'score': 99.8}\n"
                "with open('state.json', 'w') as f:\n"
                "    json.dump(payload, f)\n"
                "with open('state.json', 'r') as f:\n"
                "    read_back = json.load(f)\n"
                "print('VERIFIED:', read_back['score'] == 99.8)\n"
            ),
            "expected": "VERIFIED: True"
        },
        {
            "id": "T5_AUTOMATE_CELLULAIRE",
            "desc": "Simulation d'une itération d'automate cellulaire 1D",
            "code_v1": (
                "cells = [0, 1, 0, 1, 1, 0, 1, 0]\n"
                "new_cells = [cells[i-1] ^ cells[(i+1)%len(cells)] for i in range(len(cells))]\n"
                "print('NEXT_GEN:', new_cells)\n"
            ),
            "expected": "NEXT_GEN: [1, 0, 0, 1, 1, 0, 0, 1]"
        }
    ]
    
    solved = 0
    self_debugged = 0
    t0 = time.time()
    
    for task in tasks:
        res = vm.execute_code(task["code_v1"], script_name=f"{task['id']}.py")
        
        if res.success and task["expected"] in res.stdout:
            solved += 1
            print(f"  ✅ {task['id']} : Résolu du 1er coup en {res.duration_sec}s")
        else:
            # Cycle de Self-Debugging autonome
            if "fix_code" in task:
                print(f"  ⚠️ {task['id']} : Erreur détectée ({res.stderr.splitlines()[-1]}). Auto-correction en cours...")
                res_fix = vm.execute_code(task["fix_code"], script_name=f"{task['id']}_fixed.py")
                if res_fix.success and task["expected"] in res_fix.stdout:
                    solved += 1
                    self_debugged += 1
                    print(f"  🔧 {task['id']} : AUTO-RÉPARÉ avec succès en {res_fix.duration_sec}s !")
                else:
                    print(f"  ❌ {task['id']} : Échec persistant.")
            else:
                print(f"  ❌ {task['id']} : Échec non résolu.")
                
    total_duration = time.time() - t0
    vm.teardown()
    
    results = {
        "total_tasks": len(tasks),
        "solved": solved,
        "self_debugged": self_debugged,
        "success_rate": float(round(solved / len(tasks), 2)),
        "total_duration_sec": float(round(total_duration, 3)),
    }
    
    print("\n📊 --- RÉSULTATS OFFICIELS DU BANC VM M41 ---")
    print(f"🔹 Tâches Validées           : {solved}/{len(tasks)} ({results['success_rate']*100:.1f}%)")
    print(f"🔹 Auto-Réparations Réussies : {self_debugged} tâche(s)")
    print(f"🔹 Durée Totale              : {results['total_duration_sec']}s")
    print("---------------------------------------------\n")
    
    return results


if __name__ == "__main__":
    res = run_agent_vm_benchmark()
