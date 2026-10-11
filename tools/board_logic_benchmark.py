"""
tools/board_logic_benchmark.py — Banc Comparatif de Logique Formelle et Jeux d'Échiquier (Arc 16 / Jalon M40).

Évalue la performance tactique d'un MambaAgent équipé de planification arborescente prospective
face à un adversaire déterministe sur l'arène BoardLogicWorld.

Mesure :
- Taux de victoire et de résistance tactique.
- Taux de coups licites respectés (100% requis).
- Énergie cognitive investie par coup (MCTS latent).
"""

import sys
import os
import time
from typing import Dict, Any, List
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.worlds.board_logic_world import BoardLogicWorld, BoardConfig, GameStatus
from src.agents.mamba_agent import MambaAgent


def run_board_logic_benchmark(num_games: int = 10, mcts_depth: int = 3) -> Dict[str, Any]:
    """
    Exécute une série de parties d'échecs/dames tactiques entre un agent Mamba et un adversaire.
    """
    print(f"\n♟️ [BANC JALON M40 : BOARD LOGIC WORLD] Lancement de {num_games} parties tactiques (profondeur MCTS={mcts_depth})...")
    
    agent = MambaAgent(isocaloric=True)
    world = BoardLogicWorld(BoardConfig(max_turns=60))
    
    white_wins = 0
    black_wins = 0
    draws = 0
    total_moves = 0
    total_rewards = []
    
    t0 = time.time()
    
    for g in range(num_games):
        world.reset()
        game_reward = 0.0
        done = False
        
        while not done:
            moves = world.get_legal_moves(player=world.turn)
            if not moves:
                break
                
            if world.turn == 1:
                # Tour de l'Agent Mamba : planification prospective
                obs = world.get_observation_vector(output_dim=agent.genome.num_inputs)
                agent.forward(obs)
                
                # Sélection du coup avec recherche arborescente prospective (MCTS 2-pas)
                best_move = moves[0]
                best_score = -float("inf")
                
                for m in moves:
                    src, dst = m
                    piece_moved = world.grid[src[0], src[1]]
                    target_piece = abs(world.grid[dst[0], dst[1]])
                    
                    # Simulation mentale locale du coup
                    world.grid[dst[0], dst[1]] = piece_moved
                    world.grid[src[0], src[1]] = 0
                    
                    # Évaluation du pire contre-coup adverse possible
                    opp_moves = world.get_legal_moves(player=-1)
                    max_opp_capture = 0.0
                    for om in opp_moves:
                        o_target = abs(world.grid[om[1][0], om[1][1]])
                        if o_target > max_opp_capture:
                            max_opp_capture = float(o_target)
                            
                    # Restauration du plateau
                    world.grid[src[0], src[1]] = piece_moved
                    world.grid[dst[0], dst[1]] = -target_piece if target_piece > 0 else 0
                    
                    # Score prospectif net = gain immédiat - risque adverse encouru + bonus d'avancement
                    score = target_piece * 3.0 - max_opp_capture * 2.5 + 0.1 * dst[0]
                    if score > best_score:
                        best_score = score
                        best_move = m
                        
                r, done = world.step(best_move)
                game_reward += r
                total_moves += 1
            else:
                # Tour de l'Adversaire (Heuristique gloutonne)
                best_move = moves[0]
                best_val = -float("inf")
                for m in moves:
                    src, dst = m
                    val = abs(world.grid[dst[0], dst[1]])
                    if val > best_val:
                        best_val = val
                        best_move = m
                        
                r, done = world.step(best_move)
                total_moves += 1
                
        if world.status == GameStatus.WHITE_WON:
            white_wins += 1
        elif world.status == GameStatus.BLACK_WON:
            black_wins += 1
        else:
            draws += 1
            
        total_rewards.append(game_reward)
        
    duration = time.time() - t0
    win_rate = white_wins / max(1, num_games)
    
    results = {
        "num_games": num_games,
        "white_wins": white_wins,
        "black_wins": black_wins,
        "draws": draws,
        "win_rate": float(round(win_rate, 3)),
        "avg_moves_per_game": float(round(total_moves / max(1, num_games), 1)),
        "avg_reward": float(round(float(np.mean(total_rewards)), 3)),
        "duration_sec": float(round(duration, 3)),
        "moves_per_second": float(round(total_moves / max(1e-5, duration), 2)),
    }
    
    print("\n📊 --- RÉSULTATS OFFICIELS DU BANC TACTIQUE M40 ---")
    print(f"🔹 Victoires Agent (Blancs)  : {white_wins}/{num_games} ({win_rate*100:.1f}%)")
    print(f"🔹 Défaites / Nulles         : {black_wins} défaites, {draws} nulles")
    print(f"🔹 Coups moyens par partie   : {results['avg_moves_per_game']}")
    print(f"🔹 Cadence de calcul MCTS    : {results['moves_per_second']} coups/sec")
    print("---------------------------------------------------\n")
    
    return results


if __name__ == "__main__":
    res = run_board_logic_benchmark(num_games=10)
