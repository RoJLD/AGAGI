"""
src/worlds/board_logic_world.py — Arène de Logique Formelle et Jeux Tactiques (Arc 16 / Jalon M40).

Permet aux agents d'exercer leur recherche arborescente prospective (MCTS latent)
sur des environnements de règles déterministes pures (échecs/dames tactiques 8x8),
sans dépendance à la faim biologique.

Conformité aux 12 Commandements AGIseed :
- Commandement 1 (Flexible): BoardConfig entièrement configurable.
- Commandement 2 (Modulaire): Logique de jeu strictement isolée.
- Commandement 3 (Haute Performance): Détection vectorisée des pièces et projections NumPy.
- Commandement 9 (Stabilité Numérique): Normalisation unitaire des observations dans [-1.0, 1.0].
"""

from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import List, Tuple, Dict, Any, Optional
import numpy as np


class PieceType(IntEnum):
    """Identifiants numériques des pièces sur le plateau."""
    EMPTY = 0
    PAWN_WHITE = 1
    KNIGHT_WHITE = 2
    BISHOP_WHITE = 3
    ROOK_WHITE = 4
    QUEEN_WHITE = 5
    KING_WHITE = 6
    
    PAWN_BLACK = -1
    KNIGHT_BLACK = -2
    BISHOP_BLACK = -3
    ROOK_BLACK = -4
    QUEEN_BLACK = -5
    KING_BLACK = -6


class GameStatus(str, Enum):
    ONGOING = "ONGOING"
    WHITE_WON = "WHITE_WON"
    BLACK_WON = "BLACK_WON"
    DRAW = "DRAW"


@dataclass
class BoardConfig:
    grid_size: int = 8
    max_turns: int = 100
    win_reward: float = 1.0
    loss_reward: float = -1.0
    capture_reward_scale: float = 0.15
    step_penalty: float = -0.01
    eps: float = 1e-12


class BoardLogicWorld:
    """
    Arène de jeu de plateau tactique sur grille discrète.
    Permet l'évaluation de la planification tactique adverse.
    """

    def __init__(self, config: Optional[BoardConfig] = None):
        self.config = config or BoardConfig()
        self.grid_size = self.config.grid_size
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.int8)
        self.turn = 1  # 1 = Blancs (Agent), -1 = Noirs (Adversaire)
        self.turn_count = 0
        self.status = GameStatus.ONGOING
        self.reset()

    def reset(self) -> np.ndarray:
        """Réinitialise la position standard des pièces."""
        self.grid.fill(PieceType.EMPTY)
        self.turn = 1
        self.turn_count = 0
        self.status = GameStatus.ONGOING
        
        # Disposition simplifiée tactique 8x8
        # Rangée 0 et 1 : Pièces blanches
        self.grid[0, :] = [
            PieceType.ROOK_WHITE, PieceType.KNIGHT_WHITE, PieceType.BISHOP_WHITE, PieceType.QUEEN_WHITE,
            PieceType.KING_WHITE, PieceType.BISHOP_WHITE, PieceType.KNIGHT_WHITE, PieceType.ROOK_WHITE
        ]
        self.grid[1, :] = PieceType.PAWN_WHITE
        
        # Rangée 6 et 7 : Pièces noires
        self.grid[6, :] = PieceType.PAWN_BLACK
        self.grid[7, :] = [
            PieceType.ROOK_BLACK, PieceType.KNIGHT_BLACK, PieceType.BISHOP_BLACK, PieceType.QUEEN_BLACK,
            PieceType.KING_BLACK, PieceType.BISHOP_BLACK, PieceType.KNIGHT_BLACK, PieceType.ROOK_BLACK
        ]
        
        return self.grid.copy()

    def get_legal_moves(self, player: int = 1) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Génère la liste de tous les coups légaux pour le joueur spécifié.
        Chaque coup est ((r_src, c_src), (r_dst, c_dst)).
        """
        legal_moves = []
        if self.status != GameStatus.ONGOING:
            return legal_moves

        # Trouver toutes les pièces du joueur
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                p = self.grid[r, c]
                if (player == 1 and p > 0) or (player == -1 and p < 0):
                    moves = self._get_piece_moves(r, c, p)
                    legal_moves.extend(moves)

        return legal_moves

    def _get_piece_moves(self, r: int, c: int, piece: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        moves = []
        p_type = abs(piece)
        direction = 1 if piece > 0 else -1  # Blanc avance vers le bas (indices croissants), noir vers le haut

        # PIONS
        if p_type == PieceType.PAWN_WHITE:
            nr = r + direction
            if 0 <= nr < self.grid_size and self.grid[nr, c] == PieceType.EMPTY:
                moves.append(((r, c), (nr, c)))
            # Captures diagonales
            for dc in [-1, 1]:
                nc = c + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    target = self.grid[nr, nc]
                    if (piece > 0 and target < 0) or (piece < 0 and target > 0):
                        moves.append(((r, c), (nr, nc)))

        # CAVALIERS
        elif p_type == PieceType.KNIGHT_WHITE:
            jumps = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
            for dr, dc in jumps:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    target = self.grid[nr, nc]
                    if target == PieceType.EMPTY or (piece > 0 and target < 0) or (piece < 0 and target > 0):
                        moves.append(((r, c), (nr, nc)))

        # TOURS, FOUS, REINE
        elif p_type in (PieceType.ROOK_WHITE, PieceType.BISHOP_WHITE, PieceType.QUEEN_WHITE):
            directions = []
            if p_type in (PieceType.ROOK_WHITE, PieceType.QUEEN_WHITE):
                directions.extend([(0, 1), (0, -1), (1, 0), (-1, 0)])
            if p_type in (PieceType.BISHOP_WHITE, PieceType.QUEEN_WHITE):
                directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])

            for dr, dc in directions:
                step = 1
                while True:
                    nr, nc = r + dr * step, c + dc * step
                    if not (0 <= nr < self.grid_size and 0 <= nc < self.grid_size):
                        break
                    target = self.grid[nr, nc]
                    if target == PieceType.EMPTY:
                        moves.append(((r, c), (nr, nc)))
                    else:
                        if (piece > 0 and target < 0) or (piece < 0 and target > 0):
                            moves.append(((r, c), (nr, nc)))
                        break
                    step += 1

        # ROIS
        elif p_type == PieceType.KING_WHITE:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                        target = self.grid[nr, nc]
                        if target == PieceType.EMPTY or (piece > 0 and target < 0) or (piece < 0 and target > 0):
                            moves.append(((r, c), (nr, nc)))

        return moves

    def step(self, move: Tuple[Tuple[int, int], Tuple[int, int]]) -> Tuple[float, bool]:
        """
        Exécute un coup licite, résout les captures et met à jour l'état.
        Renvoie (reward, done).
        """
        if self.status != GameStatus.ONGOING:
            return 0.0, True

        src, dst = move
        piece = self.grid[src[0], src[1]]
        target = self.grid[dst[0], dst[1]]

        reward = self.config.step_penalty

        # Si capture
        if target != PieceType.EMPTY:
            capture_val = abs(target) * self.config.capture_reward_scale
            reward += capture_val if self.turn == 1 else -capture_val
            
            # Victoire par capture de roi
            if abs(target) == PieceType.KING_WHITE:
                self.grid[dst[0], dst[1]] = piece
                self.grid[src[0], src[1]] = PieceType.EMPTY
                if self.turn == 1:
                    self.status = GameStatus.WHITE_WON
                    return reward + self.config.win_reward, True
                else:
                    self.status = GameStatus.BLACK_WON
                    return reward + self.config.loss_reward, True

        # Déplacement de la pièce
        self.grid[dst[0], dst[1]] = piece
        self.grid[src[0], src[1]] = PieceType.EMPTY

        self.turn_count += 1
        self.turn = -self.turn  # Alterne le tour

        # Limite maximale de tours
        if self.turn_count >= self.config.max_turns:
            self.status = GameStatus.DRAW
            return reward, True

        return reward, False

    def get_observation_vector(self, output_dim: int = 59) -> np.ndarray:
        """
        Projette l'état du plateau dans un vecteur 1D normalisé dans [-1.0, 1.0],
        compatible avec les entrées sensorielles (I = 59) de MambaAgent.
        """
        # Aplatir le plateau 8x8 = 64 éléments normalisés par la valeur max de pièce (6.0)
        flat_board = (self.grid.flatten().astype(np.float32)) / 6.0

        if len(flat_board) >= output_dim:
            # Compression par moyenne de blocs si la dimension demandée est plus petite
            indices = np.linspace(0, len(flat_board) - 1, output_dim, dtype=int)
            obs = flat_board[indices]
        else:
            # Padding si output_dim > 64
            obs = np.pad(flat_board, (0, output_dim - len(flat_board)), mode='constant')

        obs = np.clip(obs, -1.0, 1.0)
        return obs.astype(np.float32)
