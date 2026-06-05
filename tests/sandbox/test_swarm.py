import numpy as np
import pytest
from src.swarm.router import CognitiveRouter, RouterConfig
from src.swarm.consensus import WeightedConsensus, ConsensusConfig
from src.swarm.hgt import HorizontalGeneTransfer, HGTConfig

def test_cognitive_router():
    config = RouterConfig(similarity_threshold=0.5, metric="cosine")
    router = CognitiveRouter(config)
    
    router.announce_route("agent_1", np.array([1.0, 0.0, 0.0]))
    router.announce_route("agent_2", np.array([0.0, 1.0, 0.0]))
    
    # Query very similar to agent_1
    query = np.array([0.9, 0.1, 0.0])
    target = router.route(query)
    assert target == "agent_1", "Router failed to route to the most similar agent."
    
    # Query below threshold (if we increase threshold)
    router.config.similarity_threshold = 0.99
    target2 = router.route(np.array([0.5, 0.5, 0.0]))
    assert target2 is None, "Router should return None when similarity is below threshold."

def test_weighted_consensus():
    config = ConsensusConfig(temperature=1.0)
    consensus = WeightedConsensus(config)
    
    preds = [
        ("agent_1", np.array([1.0, 1.0]), 10.0), # High fitness
        ("agent_2", np.array([0.0, 0.0]), 0.0),  # Low fitness
    ]
    
    result = consensus.vote(preds)
    # The result should be very close to [1.0, 1.0] due to high fitness difference (softmax scaling)
    assert np.allclose(result, np.array([1.0, 1.0]), atol=0.1), "Consensus did not weight high-fitness prediction properly."

def test_hgt_transfer():
    config = HGTConfig(crossover_rate=0.5, mutation_rate=0.0)
    hgt = HorizontalGeneTransfer(config)
    
    recipient = np.zeros((10, 10))
    donor = np.ones((10, 10))
    
    offspring = hgt.transfer_layer(recipient, donor)
    
    # Roughly half should be 1s and half 0s due to 50% crossover rate
    mean_val = np.mean(offspring)
    assert 0.3 <= mean_val <= 0.7, "HGT crossover rate distribution is skewed."
    assert offspring.shape == (10, 10), "HGT altered weight shape."
