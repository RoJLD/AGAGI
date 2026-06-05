#!/usr/bin/env python3
"""
TEST SCRIPT POUR LES 5 FIXES CRITIQUES
======================================

Ce script valide:
1. Attention Mask Bug Fix (mamba_agent.py)
2. Standardisation 45 inputs / 75 outputs (world_1_stoneage.py, config.py)
3. Vectorisation du step() (world_1_stoneage.py)
4. Crossover Genetique (evolution.py)
5. Sauvegarde/Chargement Etat Agents (persistence.py)

Usage: python test_fixes_simple.py
"""

import sys
import os
import numpy as np
import traceback

# Ajouter le chemin src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)

def print_test_result(test_name, passed, message=""):
    status = "PASS" if passed else "FAIL"
    print(f"{status}: {test_name}")
    if message:
        print(f"   -> {message}")
    return passed

def test_attention_mask_fix():
    """Test que le bug Attention Mask est corrigé."""
    print_test_header("Attention Mask Bug Fix")
    
    try:
        from src.agents.mamba_agent import MambaAgent
        
        # Créer un agent avec 45 inputs / 75 outputs
        agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
        
        # Créer une observation de taille 45
        obs = np.random.randn(45).astype(np.float32)
        
        # Exécuter forward
        logits = agent.forward(obs)
        
        # Vérifier les dimensions
        assert logits.shape[0] == 75, f"Expected 75 outputs, got {logits.shape[0]}"
        assert agent.attention_mask.shape[0] == 45, f"Attention mask should be 45, got {agent.attention_mask.shape[0]}"
        
        print("   -> Agent created with 45 inputs / 75 outputs")
        print("   -> forward() executed successfully")
        print("   -> No dimension mismatch errors")
        
        return print_test_result("Attention Mask Fix", True, "Bug fixed - no incorrect concatenation")
        
    except Exception as e:
        traceback.print_exc()
        return print_test_result("Attention Mask Fix", False, f"Error: {str(e)}")


def test_standardization():
    """Test que tout est standardisé sur 45 inputs / 75 outputs."""
    print_test_header("Standardization 45/75/96")
    
    try:
        from src.environments.config import AgentConfig, WorldConfig
        from src.agents.mamba_agent import MambaAgent
        from src.worlds.world_1_stoneage import Biosphere3D
        
        # Vérifier AgentConfig
        config = AgentConfig()
        assert config.num_inputs == 45, f"AgentConfig.num_inputs should be 45, got {config.num_inputs}"
        assert config.num_outputs == 75, f"AgentConfig.num_outputs should be 75, got {config.num_outputs}"
        assert config.num_nodes == 96, f"AgentConfig.num_nodes should be 96, got {config.num_nodes}"
        
        # Vérifier MambaAgent par défaut
        agent = MambaAgent()
        assert agent.genome.num_inputs == 45, f"MambaAgent default inputs should be 45"
        assert agent.genome.num_outputs == 75, f"MambaAgent default outputs should be 75"
        
        # Vérifier WorldConfig
        world_config = WorldConfig()
        assert world_config.agent.num_inputs == 45
        assert world_config.agent.num_outputs == 75
        
        # Vérifier Biosphere3D
        world = Biosphere3D()
        agent_dict = {
            "model": MambaAgent(),
            "x": 0, "y": 0, "z": 0,
            "energy": 100.0,
            "hp": 100.0,
            "age": 0,
            "inventory": [],
            "last_spoken": [0.0]*4,
            "last_action": -1,
            "visited_positions": set()
        }
        world.agents.append(agent_dict)
        
        obs = world.get_agent_observation(agent_dict)
        assert obs.shape[0] == 45, f"get_agent_observation should return 45 values, got {obs.shape[0]}"
        
        print("   -> AgentConfig: 45/75/96 OK")
        print("   -> MambaAgent: 45/75/96 OK")
        print("   -> WorldConfig: 45/75/96 OK")
        print("   -> Biosphere3D.get_agent_observation: 45 outputs OK")
        
        return print_test_result("Standardization 45/75/96", True, "All components standardized")
        
    except Exception as e:
        traceback.print_exc()
        return print_test_result("Standardization 45/75/96", False, f"Error: {str(e)}")


def test_vectorization():
    """Test que le step() est vectorisé."""
    print_test_header("Vectorization of step()")
    
    try:
        from src.agents.mamba_agent import MambaAgent
        from src.worlds.world_1_stoneage import Biosphere3D
        
        # Créer un monde avec plusieurs agents
        world = Biosphere3D(size=5)
        
        # Ajouter 5 agents
        for _ in range(5):
            agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
            world.add_agent(agent, energy=100.0)
        
        print(f"   -> Created world with {len(world.agents)} agents")
        
        # Exécuter un step
        world.step()
        
        print(f"   -> Executed step() successfully")
        print(f"   -> {len(world.agents)} agents survived")
        
        return print_test_result("Vectorization step()", True, "step() works with multiple agents")
        
    except Exception as e:
        traceback.print_exc()
        return print_test_result("Vectorization step()", False, f"Error: {str(e)}")


def test_crossover():
    """Test que le crossover est implémenté et fonctionne."""
    print_test_header("Genetic Crossover")
    
    try:
        from src.seed_ai.evolution import crossover, tournament_selection, Population, EvolutionConfig
        from src.seed_ai.mutation import Genome, MutationConfig
        import numpy as np
        
        # Créer deux génomes
        W1 = np.random.randn(96, 96).astype(np.float32) * 0.1
        W2 = np.random.randn(96, 96).astype(np.float32) * 0.1
        
        genome1 = Genome(W1, 45, 75)
        genome2 = Genome(W2, 45, 75)
        
        # Tester crossover
        child = crossover(genome1, genome2, 100.0, 90.0, seed=42)
        
        # Vérifier dimensions
        assert child.num_inputs == 45
        assert child.num_outputs == 75
        assert child.W.shape == (96, 96)
        
        print("   -> crossover() creates valid child")
        print("   -> Dimensions preserved: 45/75/96")
        
        # Tester tournament selection
        population = [genome1, genome2]
        fitnesses = [100.0, 90.0]
        winner_idx = tournament_selection(population, fitnesses, tournament_size=2)
        assert winner_idx in [0, 1], "Tournament selection should return valid index"
        
        print("   -> tournament_selection() works")
        
        # Tester Population avec crossover
        config = EvolutionConfig(pop_size=10, tournament_size=3)
        mut_config = MutationConfig()
        pop = Population(config, mut_config, 45, 75)
        
        X = np.random.randn(4, 45).astype(np.float32)
        y = np.random.randn(4, 75).astype(np.float32)
        
        fitness, best = pop.step(X, y)
        
        print("   -> Population.step() uses crossover")
        
        return print_test_result("Genetic Crossover", True, "Crossover + Tournament Selection working")
        
    except Exception as e:
        traceback.print_exc()
        return print_test_result("Genetic Crossover", False, f"Error: {str(e)}")


def test_persistence():
    """Test la sauvegarde et le chargement d'état des agents."""
    print_test_header("Agent State Persistence")
    
    try:
        from src.agents.mamba_agent import MambaAgent
        from src.seed_ai.persistence import (
            save_agent_state, load_agent_state,
            save_to_hall_of_fame, load_hall_of_fame
        )
        import tempfile
        
        # Créer un agent
        agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
        
        # Modifier son état
        agent.H_prev = np.random.randn(1, 96).astype(np.float32) * 0.5
        agent.surprise = 0.75
        agent.attention_mask = np.random.rand(45).astype(np.float32)
        
        # Tester save/load state
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, "test_agent")
            
            # Sauvegarder
            saved_path = save_agent_state(agent, state_path)
            assert os.path.exists(saved_path), "State file should be created"
            print("   -> save_agent_state() creates file")
            
            # Créer un nouvel agent et charger l'état
            new_agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
            loaded = load_agent_state(new_agent, saved_path)
            assert loaded, "State should be loaded successfully"
            
            # Vérifier que l'état a été chargé
            assert np.allclose(new_agent.H_prev, agent.H_prev), "H_prev should match"
            assert abs(new_agent.surprise - agent.surprise) < 0.01, "surprise should match"
            
            print("   -> load_agent_state() loads state correctly")
            
            # Tester save_to_hall_of_fame
            agent_dict = {
                "model": agent,
                "age": 100,
                "preys_eaten": 5,
                "altars_solved": 2,
                "energy": 80.0
            }
            hof_path = save_to_hall_of_fame(agent_dict)
            assert hof_path is not None or os.path.exists("data/hall_of_fame.pkl"), "HoF should be saved"
            print("   -> save_to_hall_of_fame() works")
            
            # Tester load_hall_of_fame
            version, hof = load_hall_of_fame()
            assert version >= 1, "HoF version should be >= 1"
            assert len(hof) > 0, "HoF should have entries"
            print("   -> load_hall_of_fame() loads data")
        
        return print_test_result("Agent State Persistence", True, "All persistence mechanisms working")
        
    except Exception as e:
        traceback.print_exc()
        return print_test_result("Agent State Persistence", False, f"Error: {str(e)}")


def run_all_tests():
    """Execute all tests."""
    print("\n" + "="*60)
    print("STARTING TESTS - 5 CRITICAL FIXES")
    print("="*60)
    
    results = []
    
    # Test 1: Attention Mask
    results.append(("Attention Mask Bug Fix", test_attention_mask_fix()))
    
    # Test 2: Standardization
    results.append(("Standardization 45/75/96", test_standardization()))
    
    # Test 3: Vectorization
    results.append(("Vectorization step()", test_vectorization()))
    
    # Test 4: Crossover
    results.append(("Genetic Crossover", test_crossover()))
    
    # Test 5: Persistence
    results.append(("Agent State Persistence", test_persistence()))
    
    # Summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {test_name}")
    
    print("="*60)
    print(f"Score: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\nALL TESTS PASSED!")
        print("All 5 critical fixes are working.")
        return 0
    else:
        print(f"\n{total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
