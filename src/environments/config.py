from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import json
import os

@dataclass
class MutationConfig:
    weight_mutate_rate: float = 0.8
    weight_mutate_power: float = 0.5
    add_node_rate: float = 0.1
    add_connection_rate: float = 0.3
    prune_rate: float = 0.1
    weight_init_std: float = 2.0

@dataclass
class AgentConfig:
    num_inputs: int = 59  # 46 inputs existants + 5 Memory Recall + 3 EXP-9 + 5 NTM_Read
    num_outputs: int = 108 # 29 actions + 20 NTM Heads + 59 Attention Mask = 108
    num_nodes: int = 172  # V17 NTM+Actor-Critic
    energy_start: float = 100.0
    energy_breed: float = 30.0
    energy_max: float = 100.0
    ttc_momentum_decay: float = 0.8
    mutation: MutationConfig = field(default_factory=MutationConfig)

@dataclass
class PreyConfig:
    hp: float
    damage: float
    moves_per_tick: float


@dataclass
class BiomeConfig:
    plains_drain: float = 0.1
    forest_drain: float = 0.05
    water_drain: float = 0.5
    desert_drain: float = 1.0

@dataclass
class WorldConfig:
    size: int = 10
    num_altars: int = 3
    prey_mode: str = "semi"
    target_prey_count: int = 15  # recalibrage C : plafond de proies (modéré)
    treasure_reward: float = 30.0
    fruit_tree_ratio: float = 0.2
    use_3d: bool = False
    active_exp_variable: str = "LANGUAGE"  # "LANGUAGE", "RAG", "METAPROG", "NONE"
    
    # Thermodynamique & MCTS / TTC
    ttc_base_cost: float = 0.01
    ttc_night_penalty: float = 2.5
    ttc_surprise_scale: float = 1.0
    
    # Surprise-Triggered HGT
    hgt_surprise_threshold: float = 0.75
    hgt_surprise_power: float = 0.2

    # Évaluation ROBUSTE du HoF (EDR 078/079) : K>1 -> ré-évaluer les candidats sur K ères et moyenner
    # avant de committer au HoF (de-bruite la sélection ; lève le plateau de compétence). 0/1 = off.
    robust_hof_K: int = 0

    # Reproductibilité / provenance (D1) : None -> graine tirée et LOGGÉE au boot (run rejouable
    # a posteriori) ; int fixe -> run pleinement reproductible. Défaut None = comportement historique.
    experiment_seed: Optional[int] = None

    # Économie d'énergie (EDR 084) : la survie plafonne (~70 ticks) car 79% starvent. Ces deux leviers
    # règlent le sweet spot dureté↔soutenabilité. Défauts = comportement historique (non-régression).
    base_metabolism: float = 1.0   # multiplicateur du drain de base par tick (↓ = survie plus longue)
    forage_payoff: float = 1.0     # multiplicateur de la nutrition d'une proie (↑ = foraging plus payant)
    # NAS Axe D-2 : KWTA sur les nœuds cachés. 1.0 = off (non-régression). <1.0 = fraction de cachés
    # gardés actifs (sparsité IMPOSÉE, pas sélectionnée). Sweep modéré 0.3-0.7.
    kwta_keep_frac: float = 1.0

    # NAS Axe D-1 (coût métabolique d'activation) : énergie drainée par nœud actif/tick.
    # 0.0 = off (non-régression bit-exacte). Seule variable d'expérience ; sweep typique 0 -> 0.01.
    metabolic_cost_coef: float = 0.0

    agent: AgentConfig = field(default_factory=AgentConfig)
    biome: BiomeConfig = field(default_factory=BiomeConfig)
    preys: Dict[str, PreyConfig] = field(default_factory=lambda: {
        "Lapin": PreyConfig(hp=1.0, damage=0.0, moves_per_tick=2),
        "Cerf": PreyConfig(hp=3.0, damage=0.0, moves_per_tick=1),
        "Sanglier": PreyConfig(hp=5.0, damage=10.0, moves_per_tick=0.5), # 0.5 means 50% chance to move
        "Mammouth": PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)
    })
    item_physics: Dict[str, tuple] = field(default_factory=lambda: {
        "Meat": (0.5, 0.0, 1.0, 0.1, 0.0),
        "Spear": (2.0, 1.0, 0.0, 0.5, 0.5),
        "Rock": (1.0, 0.5, 0.0, 0.8, 0.0),
        "rock": (1.0, 0.5, 0.0, 0.8, 0.0),
        "stick": (0.5, 0.2, 0.0, 0.6, 1.0),
        "Wood": (1.0, 0.5, 0.0, 0.6, 1.0),
        "Spark": (0.0, 0.0, 0.0, 0.0, 0.0),
        "Fire": (0.0, 0.0, 0.0, 0.0, 0.0),
        "Fruit": (0.5, 0.0, 1.0, 0.1, 0.0),
        "Seed": (0.1, 0.0, 0.1, 0.1, 0.0)
    })
    
    @classmethod
    def load_from_json(cls, path: str) -> 'WorldConfig':
        if not os.path.exists(path):
            return cls()
        with open(path, 'r') as f:
            data = json.load(f)
            
        # Recursive parsing to build dataclasses
        agent_data = data.pop('agent', {})
        mut_data = agent_data.pop('mutation', {})
        biome_data = data.pop('biome', {})
        preys_data = data.pop('preys', {})
        
        mut_cfg = MutationConfig(**mut_data)
        agent_cfg = AgentConfig(**agent_data, mutation=mut_cfg)
        biome_cfg = BiomeConfig(**biome_data)
        
        preys_cfg = {}
        for k, v in preys_data.items():
            preys_cfg[k] = PreyConfig(**v)
        
        # If preys weren't in JSON, it will use default_factory which is fine unless we explicitly pass an empty dict
        if preys_cfg:
            return cls(**data, agent=agent_cfg, biome=biome_cfg, preys=preys_cfg)
        return cls(**data, agent=agent_cfg, biome=biome_cfg)
