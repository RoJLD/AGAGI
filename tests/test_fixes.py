#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script pour valider les fixes AGIseed
"""
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_attention_mask_fix():
    """Test Task 1: Attention Mask dimensions fix"""
    from src.agents.mamba_agent import MambaAgent
    from src.seed_ai.mutation import Genome
    
    print("Testing Task 1: Attention Mask fix...")
    
    # Creer un agent avec 45 inputs, 75 outputs
    agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
    
    # Creer une observation de taille 45
    obs = np.random.randn(45).astype(np.float32)
    
    # Forward pass ne doit pas planter
    try:
        logits = agent.forward(obs)
        assert logits.shape[0] == 75, f"Expected 75 outputs, got {logits.shape[0]}"
        print("  [OK] Agent.forward() works with 45 inputs")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        return False
    
    # Verifier que genome.num_outputs >= genome.num_inputs + 2
    assert agent.genome.num_outputs >= agent.genome.num_inputs + 2, \
        f"num_outputs ({agent.genome.num_outputs}) must be >= num_inputs ({agent.genome.num_inputs}) + 2"
    print("  [OK] Genome has sufficient outputs for explicit_memory")
    
    # Tester from_genome avec un genome de taille differente
    old_W = np.random.randn(100, 100).astype(np.float32) * 0.1
    old_genome = Genome(old_W, 50, 80)
    agent.from_genome(old_genome)
    assert agent.genome.num_outputs >= agent.genome.num_inputs + 2
    print("  [OK] from_genome() preserves valid dimensions")
    
    print("  [OK] Task 1 PASSED\n")
    return True


def test_standardized_inputs():
    """Test Task 2: Standardized 45 inputs / 75 outputs"""
    from src.worlds.world_0_soup import Biosphere3D as World0
    from src.worlds.world_1_stoneage import Biosphere3D as World1
    from src.environments.config import WorldConfig, AgentConfig
    from src.agents.mamba_agent import MambaAgent
    
    print("Testing Task 2: Standardized 45 inputs / 75 outputs...")
    
    # Creer les deux worlds
    world0 = World0()
    world1_2d = World1(WorldConfig(use_3d=False, agent=AgentConfig(num_inputs=45, num_outputs=75)))
    world1_3d = World1(WorldConfig(use_3d=True, agent=AgentConfig(num_inputs=45, num_outputs=75)))
    
    # Creer un genome pour world_0_soup (qui utilise genome directement)
    from src.seed_ai.mutation import Genome
    genome_w0 = Genome(np.random.randn(96, 96).astype(np.float32) * 0.1, 45, 75)
    
    # Tester world_0_soup
    world0.add_agent(genome_w0, energy=100)
    obs0 = world0._get_agent_observation(world0.agents[0])
    # obs0 is (1, 45) array
    assert obs0.shape == (1, 45) or obs0.shape == (45,), f"world_0_soup: Expected shape (1,45) or (45,), got {obs0.shape}"
    assert obs0.size == 45, f"world_0_soup: Expected 45 inputs, got {obs0.size}"
    print("  [OK] world_0_soup.py produces 45 inputs")
    
    # Tester world_1_stoneage en 2D
    world1_2d.add_agent(MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96), energy=100)
    obs1_2d = world1_2d.get_agent_observation(world1_2d.agents[0])
    assert obs1_2d.size == 45, f"world_1_stoneage 2D: Expected 45 inputs, got {obs1_2d.size}"
    print("  [OK] world_1_stoneage (2D) produces 45 inputs")
    
    # Tester world_1_stoneage en 3D
    world1_3d.add_agent(MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96), energy=100)
    obs1_3d = world1_3d.get_agent_observation(world1_3d.agents[0])
    assert obs1_3d.size == 45, f"world_1_stoneage 3D: Expected 45 inputs, got {obs1_3d.size}"
    print("  [OK] world_1_stoneage (3D) produces 45 inputs")
    
    # Verifier que les agents ont Z en 3D
    assert "z" in world1_3d.agents[0], "3D agent should have z coordinate"
    print("  [OK] 3D agents have z coordinate")
    
    print("  [OK] Task 2 PASSED\n")
    return True


def test_crossover():
    """Test Task 4: Crossover implementation"""
    from src.seed_ai.mutation import Genome
    from src.seed_ai.evolution import crossover, Population, EvolutionConfig, MutationConfig
    
    print("Testing Task 4: Crossover implementation...")
    
    # Creer deux genomes
    W1 = np.random.randn(10, 10).astype(np.float32) * 0.1
    W2 = np.random.randn(10, 10).astype(np.float32) * 0.1
    genome1 = Genome(W1, 45, 75)
    genome2 = Genome(W2, 45, 75)
    
    # Tester crossover
    try:
        child = crossover(genome1, genome2, fitness1=1.0, fitness2=0.5)
        assert child is not None
        assert child.W.shape == (10, 10)
        print("  [OK] crossover() creates valid child genome")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        return False
    
    # Tester Population avec crossover
    config = EvolutionConfig(pop_size=10, generations=1, local_epochs=0, tournament_size=2)
    mut_config = MutationConfig()
    pop = Population(config, mut_config, num_inputs=45, num_outputs=75)
    
    X = np.random.randn(10, 45).astype(np.float32)
    y = np.random.randn(10, 1).astype(np.float32)
    
    try:
        pop.step(X, y)
        print("  [OK] Population.step() with crossover works")
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        return False
    
    print("  [OK] Task 4 PASSED\n")
    return True


def test_save_load_agent_state():
    """Test Task 5: Save/Load agent state"""
    from src.agents.mamba_agent import MambaAgent
    import tempfile
    import os
    
    print("Testing Task 5: Save/Load agent state...")
    
    # Creer un agent
    agent = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
    
    # Sauvegarder l'etat
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_agent")
        saved_path = agent.save_state(path)
        assert os.path.exists(saved_path), f"State file not created at {saved_path}"
        print("  [OK] save_state() creates file")
        
        # Creer un nouvel agent et charger l'etat
        agent2 = MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96)
        assert agent2.load_state(saved_path), "load_state() failed"
        print("  [OK] load_state() loads successfully")
        
        # Verifier que l'etat a ete charge
        assert np.array_equal(agent2.H_prev, agent.H_prev), "H_prev mismatch"
        assert np.array_equal(agent2.H_history, agent.H_history), "H_history mismatch"
        assert np.array_equal(agent2.attention_mask, agent.attention_mask), "attention_mask mismatch"
        assert np.array_equal(agent2.explicit_memory, agent.explicit_memory), "explicit_memory mismatch"
        print("  [OK] State loaded correctly")
    
    print("  [OK] Task 5 PASSED\n")
    return True


def test_vectorized_forward():
    """Test Task 3: Vectorized forward with MambaBatchModel"""
    from src.agents.mamba_agent import MambaAgent, MambaBatchModel
    import numpy as np
    
    print("Testing Task 3: Vectorized forward...")
    
    # Creer plusieurs agents
    agents = [MambaAgent(num_inputs=45, num_outputs=75, num_nodes=96) for _ in range(5)]
    
    # Creer un batch d'observations
    batch_obs = np.random.randn(5, 45).astype(np.float32)
    
    # Creer le modele batch
    batch_model = MambaBatchModel(agents)
    
    try:
        # Forward pass batch
        batch_logits = batch_model.forward(batch_obs)
        assert batch_logits.shape == (5, 75), f"Expected shape (5, 75), got {batch_logits.shape}"
        print("  [OK] MambaBatchModel.forward() works")
        
        # Verifier que les etats des agents ont ete mis a jour
        for agent in agents:
            assert agent.H_prev is not None
            assert agent.surprise >= 0
        print("  [OK] Agent states updated after batch forward")
        
    except Exception as e:
        print(f"  [FAIL] FAILED: {e}")
        return False
    
    print("  [OK] Task 3 PASSED\n")
    return True


def run_all_tests():
    """Execute tous les tests"""
    print("="*60)
    print("AGIseed Fixes Validation Test Suite")
    print("="*60 + "\n")
    
    tests = [
        test_attention_mask_fix,
        test_standardized_inputs,
        test_vectorized_forward,
        test_crossover,
        test_save_load_agent_state,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  [FAIL] Test {test.__name__} CRASHED: {e}\n")
            failed += 1
    
    print("="*60)
    print(f"Results: {passed} PASSED, {failed} FAILED")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
