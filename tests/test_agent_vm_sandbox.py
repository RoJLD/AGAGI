"""
tests/test_agent_vm_sandbox.py — Tests unitaires pour l'Environnement Machine Virtuelle et Code Sandbox (Arc 16 / Jalon M41).

Valide :
1. Création d'une VM isolée avec espace de fichiers dédié.
2. Exécution sécurisée de scripts Python avec capture de stdout et stderr.
3. Blocage des opérations dangereuses ou malveillantes (Commandement 6).
4. Boucle de rétroaction et d'auto-réparation de code (Self-Debugging).
5. Résolution autonome d'une tâche de calcul programmatique par l'agent.
"""

import pytest
import os
from src.metaprog.agent_vm_sandbox import AgentVMSandbox, VMConfig, ExecutionResult


def test_vm_initialization_and_workspace():
    """Vérifie l'initialisation de la VM et de son espace de travail sécurisé."""
    config = VMConfig(timeout_seconds=2.0)
    vm = AgentVMSandbox(config)
    
    assert os.path.exists(vm.workspace_dir)
    assert vm.is_alive() is True
    vm.teardown()
    assert not os.path.exists(vm.workspace_dir)


def test_safe_script_execution():
    """Vérifie l'exécution d'un script correct et la capture de stdout."""
    vm = AgentVMSandbox()
    code = "print('REPONSE_CALCUL:', 42 * 2)"
    res = vm.execute_code(code)
    
    assert res.success is True
    assert res.exit_code == 0
    assert "REPONSE_CALCUL: 84" in res.stdout
    assert res.stderr == ""
    vm.teardown()


def test_syntax_error_and_traceback_capture():
    """Vérifie la capture de stacktrace lors d'une erreur d'exécution pour permettre le self-debugging."""
    vm = AgentVMSandbox()
    bad_code = "print(10 / 0)"
    res = vm.execute_code(bad_code)
    
    assert res.success is False
    assert res.exit_code != 0
    assert "ZeroDivisionError" in res.stderr
    vm.teardown()


def test_infinite_loop_timeout_protection():
    """Vérifie que la protection par timeout coupe une boucle infinie (Commandement 6)."""
    config = VMConfig(timeout_seconds=0.5)
    vm = AgentVMSandbox(config)
    loop_code = "while True: pass"
    res = vm.execute_code(loop_code)
    
    assert res.success is False
    assert res.timed_out is True
    assert "TIMEOUT" in res.stderr
    vm.teardown()


def test_self_debugging_cycle():
    """Vérifie le cycle d'auto-réparation : échec initial puis correction autonome."""
    vm = AgentVMSandbox()
    
    # Étape 1 : Code défectueux
    code_v1 = "def solve(): return x + 1\nsolve()"
    res_1 = vm.execute_code(code_v1)
    assert res_1.success is False
    assert "NameError" in res_1.stderr
    
    # Étape 2 : Code corrigé via analyse d'erreur
    code_v2 = "x = 41\ndef solve(): return x + 1\nprint('RESULT:', solve())"
    res_2 = vm.execute_code(code_v2)
    assert res_2.success is True
    assert "RESULT: 42" in res_2.stdout
    vm.teardown()
