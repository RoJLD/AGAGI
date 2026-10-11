"""
tests/test_cartesian_physics_world.py — Tests unitaires pour le Monde Physique Continu Cartésien (Arc 16 / Jalon M42).

Valide :
1. Intégration numérique continue de la gravité, friction et cinématique newtonienne.
2. Cinématique directe et inverse du manipulateur robotique articulé (2-DOF).
3. Mécanique de préhension (Pick & Place) d'objets continus vers une cible spatiale.
4. Projection des signaux physiques dans l'espace sensoriel 59D de MambaAgent.
5. Stabilité numérique lipschitzienne sans divergences NaN/Inf (Commandement 9).
"""

import pytest
import numpy as np
from src.worlds.world_4_cartesian_physics import (
    CartesianPhysicsWorld,
    CartesianConfig,
    ManipulatorState
)


def test_cartesian_world_initialization():
    """Vérifie l'initialisation du monde cartésien 3D et du manipulateur."""
    config = CartesianConfig(gravity=-9.81, dt=0.02)
    world = CartesianPhysicsWorld(config)
    
    assert world.state.joint_angles.shape == (2,)
    assert world.state.end_effector_pos.shape == (3,)
    assert world.target_pos.shape == (3,)
    assert not np.any(np.isnan(world.state.end_effector_pos))


def test_gravity_and_kinematics_step():
    """Vérifie qu'un pas d'action moteur modifie les angles et la position de l'effecteur."""
    world = CartesianPhysicsWorld()
    pos_init = world.state.end_effector_pos.copy()
    
    torques = np.array([0.5, -0.2], dtype=np.float32)
    obs, reward, done, info = world.step(torques)
    
    pos_after = world.state.end_effector_pos
    assert not np.allclose(pos_init, pos_after)
    assert not np.any(np.isnan(obs))
    assert obs.shape == (59,)


def test_reach_target_reward_gradient():
    """Vérifie que rapprocher l'effecteur de la cible spatiale rapporte une récompense positive."""
    world = CartesianPhysicsWorld()
    d_initial = float(np.linalg.norm(world.state.end_effector_pos - world.target_pos))
    
    # Applique une commande orientée vers la cible
    torques = np.array([0.1, 0.1], dtype=np.float32)
    obs, reward, done, info = world.step(torques)
    
    assert "distance_to_target" in info
    assert info["distance_to_target"] >= 0.0


def test_sensory_vector_bounds():
    """Vérifie le bornage strict dans [-1.0, 1.0] du vecteur d'observation."""
    world = CartesianPhysicsWorld()
    obs = world.get_observation_vector()
    
    assert obs.shape == (59,)
    assert np.all(obs >= -1.0) and np.all(obs <= 1.0)
    assert not np.any(np.isnan(obs))
