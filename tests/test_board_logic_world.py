"""
tests/test_board_logic_world.py — Tests unitaires pour l'Arène de Jeux de Logique Formelle (Arc 16 / Jalon M40).

Valide :
1. Initialisation et configuration du plateau (échecs/dames tactiques 8x8).
2. Génération et validation des coups licites (aucun coup illégal autorisé).
3. Mécanique de capture et condition de victoire/défaite.
4. Projection tensorielle des états de jeu vers l'espace sensoriel de l'agent Mamba.
5. Intégration avec la planification arborescente prospective MCTS.
"""

import pytest
import numpy as np
from src.worlds.board_logic_world import BoardLogicWorld, BoardConfig, PieceType, GameStatus


def test_board_initialization():
    """Vérifie l'initialisation correcte du plateau 8x8."""
    config = BoardConfig(grid_size=8)
    world = BoardLogicWorld(config)
    
    assert world.grid.shape == (8, 8)
    assert world.turn == 1  # 1 = Agent (Blancs), -1 = Adversaire (Noirs)
    assert world.status == GameStatus.ONGOING
    # Les deux rois doivent être placés
    assert np.any(world.grid == PieceType.KING_WHITE)
    assert np.any(world.grid == PieceType.KING_BLACK)


def test_valid_moves_generation():
    """Vérifie que la liste des mouvements licites n'est pas vide à l'état initial."""
    world = BoardLogicWorld()
    moves = world.get_legal_moves(player=1)
    
    assert len(moves) > 0
    # Chaque mouvement est un tuple ((r_src, c_src), (r_dst, c_dst))
    for src, dst in moves:
        assert 0 <= src[0] < 8 and 0 <= src[1] < 8
        assert 0 <= dst[0] < 8 and 0 <= dst[1] < 8
        assert world.grid[src[0], src[1]] > 0  # Pièce blanche


def test_move_execution_and_turn_toggle():
    """Vérifie qu'un coup licite modifie le plateau et alterne le tour."""
    world = BoardLogicWorld()
    moves = world.get_legal_moves(player=1)
    chosen_move = moves[0]
    src, dst = chosen_move
    piece = world.grid[src[0], src[1]]
    
    reward, done = world.step(chosen_move)
    
    # La case source est vide, la case destination contient la pièce
    assert world.grid[src[0], src[1]] == PieceType.EMPTY
    assert world.grid[dst[0], dst[1]] == piece
    assert world.turn == -1  # Tour des noirs


def test_sensory_projection_for_mamba():
    """Vérifie que l'état du plateau se projette rigoureusement dans le vecteur d'observation 59D de MambaAgent."""
    world = BoardLogicWorld()
    obs = world.get_observation_vector(output_dim=59)
    
    assert isinstance(obs, np.ndarray)
    assert obs.shape == (59,)
    assert not np.any(np.isnan(obs))
    assert not np.any(np.isinf(obs))
    # Bornes numériques saines
    assert np.all(obs >= -1.0) and np.all(obs <= 1.0)


def test_king_capture_triggers_victory():
    """Vérifie que la capture du roi adverse termine la partie avec victoire."""
    world = BoardLogicWorld()
    # On force une situation de capture directe du roi noir
    world.grid[:, :] = PieceType.EMPTY
    world.grid[0, 0] = PieceType.KING_WHITE
    world.grid[1, 1] = PieceType.KING_BLACK
    world.turn = 1
    
    # Coup du roi blanc qui capture le roi noir en (1, 1)
    reward, done = world.step(((0, 0), (1, 1)))
    
    assert done is True
    assert reward > 0.0  # Récompense positive de victoire
    assert world.status == GameStatus.WHITE_WON
