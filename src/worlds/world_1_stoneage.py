from typing import List, Dict, Any, Tuple
import numpy as np
import uuid

from src.worlds.base_world import BaseWorld
from src.environments.projectiles import ProjectilePhysics
try:
    from src.environments.crafting import ITEM_REGISTRY, attempt_combine
except ImportError:
    ITEM_REGISTRY = {}
    def attempt_combine(ingredients): return None

from src.seed_ai.mutation import apply_mutations, MutationConfig
from src.environments.config import WorldConfig
from src.graph_rag.async_logger import logger
from src.agents.mamba_agent import MambaBatchModel
from src.agents.world_model import WorldModel
from src.environments.stone_economy import prey_reward, weapon_damage, has_spear, can_craft_spear, anneal, approach_reward, is_craft_ingredient, state_signature, novelty_bonus, try_craft_spear, crit_chance, attack_damage
from src.graph_rag.memory_retriever import AsyncMemoryRetriever
from src.swarm.consensus import WeightedConsensus, ConsensusConfig
from src.swarm.hgt import HorizontalGeneTransfer, HGTConfig
from src.environments.physics import DynamicPhysicsRegistry

class Biosphere3D(BaseWorld):
    """
    V14 TensorWorld (Refactored)
    - Utilise Configuration centralisée (WorldConfig).
    - Exécute les modèles via MambaBatchModel (Vectorisation).
    - Logs asynchrones vers KuzuDB.
    - Code modulaire (physique, biologie, social).
    - Supporte 2D et 3D via config.use_3d
    """
    def __init__(self, config: WorldConfig = None):
        self.config = config or WorldConfig()
        self.size = self.config.size
        # World Model partagé par la population (Vague 0, levier 1) : alimente la
        # vraie surprise / curiosité. Possédé par le monde -> persiste sur toute l'ère.
        self.world_model = WorldModel(self.config.agent.num_inputs)
        # Seam d'injection (S2) : classe du batch model lue à l'inférence. Défaut = MambaBatchModel
        # (inchangé). Le runner S2 le remplace par un BaselineBatchModel (RandomAction/Reflex) APRÈS
        # construction du monde -> baselines sans connectome, zéro fork. Spec §11.
        self.batch_model_cls = MambaBatchModel
        # Mode benchmark (S2) : cohorte FIXE -> désactive reproduction/mutation/HGT pendant la
        # mesure (sinon la lignée est immortelle et la survie sature au cap, blocker panel). Défaut
        # False = comportement historique. L'apprentissage intra-vie reste actif. Spec §4.
        self.benchmark_mode = False
        # Curriculum (EDR 017) : "grab" = entraînement de la collecte (monde sûr, nuit off).
        self.training_mode = None
        # AXE CRAFT (EDR 018) : complexité de la mécanique de craft. 0 = auto-craft (tenir
        # tranchant+manche -> lance, sans action). Le curriculum rampe 0->1->2... par maîtrise.
        self.craft_level = 0
        # ε-greedy (EDR 019) : en entraînement, proba d'action aléatoire (mouvement + grab)
        # -> explorer le geste pour qu'il se déclenche, soit récompensé, et évolue.
        self.explore_eps = 0.0
        # Découplage pour le curriculum 2D (EDR 027) : contrôler la nuit indépendamment du
        # training_mode (monde hybride : proies+matériaux régénérés MAIS nuit off + ε on).
        self.night_enabled = True
        self.big_kills = 0  # gros gibier tué (bout de la chaîne moyens->fins, EDR 027)
        # Portée du signal (EDR 038) : 0 = same-cell (legacy) ; >0 = on entend les agents
        # proches (Manhattan <= radius), atténué -> le signal peut RECRUTER le pack (Arc 5).
        self.hear_radius = 0
        # Coopération (EDR 028) : True = l'apex nourrit tout le pack ; False (ablation EDR 039) =
        # tueur seul (permet de mesurer l'apport réel de la coopération).
        self.coop_reward = True
        # Coût & porte du signal (EDR 042) : signaler n'est possible que si les logits de langage
        # dépassent speak_threshold, et coûte signal_cost d'énergie -> signal SÉLECTIF (informatif)
        # au lieu de constant (bruit, EDR 037). Défaut 0/0 = legacy (tout le monde parle).
        self.speak_threshold = 0.0
        self.signal_cost = 0.0
        # Brouillage du signal (EDR 043) : True = remplace le token par un token ALÉATOIRE
        # (présence préservée, SENS détruit). Si la portée aide encore -> c'est la présence,
        # pas le contenu, qui porte le bénéfice (arbitre de l'EDR 042).
        self.scramble_signal = False
        # Pression RÉFÉRENTIELLE (EDR 045, arming #8 dirigé sur le langage) : récompense la
        # CONVERGENCE sur un token partagé près de l'apex -> rend le CONTENU du signal payant
        # (vs présence seule, EDR 043). Le token DEVIENT « Mammouth ici ». 0 = off (legacy).
        self.referential_scale = 0.0
        # Incitation du LOCUTEUR (EDR 050) : réciprocité — un agent qui a signalé près d'un
        # Mammouth EFFECTIVEMENT tué par le pack touche une prime. Vainc l'altruisme du signal
        # (EDR 048 : le silence gagne car parler ne profite qu'à l'auditeur). 0 = off.
        self.speaker_reward = 0.0
        # Sélection ALIGNÉE sur la convention (EDR 055) : prime la DISTINCTION référentielle —
        # un agent qui emploie des tokens DIFFÉRENTS près du Mammouth vs du Leurre. Comble l'angle
        # mort de life_score (EDR 054 : sélection aveugle au langage). Anti-piège 045 : un token
        # constant -> distinction nulle -> zéro prime (non gameable). 0 = off.
        self.align_selection = 0.0
        # Demande de MÉMOIRE (EDR 058, NAS) : si True, le type d'apex (Mammouth/Leurre) n'est révélé
        # qu'au PREMIER contact, puis caché. L'agent doit le RETENIR (état récurrent H) pour décider
        # rester/fuir -> sature la mémoire -> devrait sélectionner la croissance architecturale.
        self.transient_apex = False
        # Suivi du token d'apex (EDR 063) : accumule par agent l'histogramme des tokens émis près du
        # Mammouth -> `_apex_token` (dominant). Sert à la spéciation PAR COMPORTEMENT pour le langage.
        self.track_apex_token = False
        # Tête référentielle DÉDIÉE (EDR 074) : si True, quand un agent perçoit un apex, son token vient
        # de sa `ref_head` co-entraînée (apex->token, code partagé fiable) au lieu du connectome 1-tick
        # faible (EDR 073). -> langage FIABLE dans l'agent vivant (vs 25% loterie mutation).
        self.use_ref_head = False
        # Décode-et-agis (EDR 075) : si True, un auditeur décode le token du locuteur le plus proche
        # (via le Wd de sa tête) et APPROCHE si prédit Mammouth/Ours, FUIT si Leurre. Teste le BÉNÉFICE
        # FONCTIONNEL du langage fiable (à distance, Mammouth et Leurre sont indistinguables -> le
        # signal seul permet de chasser le bon et d'éviter le piège).
        self.decode_act = False
        self.leurre_hits = 0        # compteur : attaques de Leurre (piège) -> à minimiser
        # Sevrage de la prime de groupe (EDR 030) : la prise d'apex passe de « pleine
        # récompense à chacun » (scaffold) à « partagée entre le pack » (économie réaliste).
        self.group_reward_eras = 20
        # Coup CRITIQUE annealé (EDR 022, « forcer le destin ») : la lance seule ne tue pas
        # le Mammouth (riposte mortelle) ; un crit décisif (proba décroissante par monde) le
        # terrasse -> amorce le lien lance->apex, puis se sèvre. Persistance (feu/retraite) : à venir.
        self.crit_base = 0.6
        self.crit_eras = 20
        self.crit_mult = 3.0
        # Rareté recalibrée (C) : nb max de proies régénérées par step vers le plafond.
        # Variable d'expérience : règle la capacité de charge écologique du monde.
        self.prey_regen_burst = 3
        # Scaffold (A) : bonus annelés enseignant l'échelle de compétence (EDR 012/013).
        # Variables d'expérience.
        self.scaffold_eps = 0.5       # approche du gibier
        self.scaffold_grab = 1.0      # collecte d'un ingrédient de craft
        self.scaffold_craft = 5.0     # craft d'une lance (jalon)
        self.scaffold_bighit = 2.0    # coup porté à un gros gibier
        self.scaffold_eras = 30
        # Curiosité (réparation moteur évolutif, EDR 014) : récompense intrinsèque
        # = erreur de prédiction du World Model -> drive l'exploration d'actions/états
        # nouveaux (grab, rub...). S'auto-annèle (la surprise chute quand le monde est
        # appris, propriété RND). Variable d'expérience.
        self.curiosity_scale = 2.0
        # Nouveauté count-based (EDR 014) : récompense les configs d'inventaire rares
        # -> tire vers les précurseurs du craft (tenir rock+stick). Ne sature pas.
        self.novelty_counts = {}
        self.novelty_scale = 3.0
        self.physics_registry = DynamicPhysicsRegistry(self.config.item_physics)
        self.num_altars = self.config.num_altars
        self.prey_mode = self.config.prey_mode
        self.use_3d = getattr(self.config, 'use_3d', False)
        self.dim_z = self.size if self.use_3d else 1
        
        self.pheromone_map = np.zeros((self.dim_z, self.size, self.size), dtype=np.float32)
        self.geometry = np.zeros((self.dim_z, self.size, self.size), dtype=int)
        
        # Biomes (2D only for now, but can be extended)
        self.terrain_type = np.zeros((self.size, self.size), dtype=int)
        for y in range(self.size):
            for x in range(self.size):
                if np.random.rand() < 0.3:
                    self.terrain_type[y, x] = np.random.choice([0, 1, 2, 3])
                else:
                    if y >= self.size // 2 and x >= self.size // 2:
                        self.terrain_type[y, x] = 2
                    elif y < self.size // 2 and x < self.size // 2:
                        self.terrain_type[y, x] = 1
                    else:
                        self.terrain_type[y, x] = 0

        self.items = []
        self._generate_geometry()
        self._generate_trees()
        
        self.agents = []
        
        self.preys = []
        self._spawn_preys()
        self.worms = []
        self._spawn_worms()
        self._spawn_treasure()
        
        self.altars = []
        for _ in range(self.num_altars):
            self.altars.append({
                "x": np.random.randint(0, self.size),
                "y": np.random.randint(0, self.size),
                "bit_a": np.random.choice([-1.0, 1.0]),
                "bit_b": np.random.choice([-1.0, 1.0])
            })
            
        for _ in range(18):
            self._spawn_rocks()
            
        self.ticks = 0
        self.dead_agents = []
        self.consensus = WeightedConsensus(ConsensusConfig())
        self.hgt = HorizontalGeneTransfer(HGTConfig())
        
        logger.start()
        self.memory_retriever = AsyncMemoryRetriever(logger)
        self.memory_retriever.start()

    def reset(self):
        """Réinitialise l'environnement (pas les agents)."""
        self.ticks = 0
        self.items = []
        self._generate_trees()
        for _ in range(18):
            self._spawn_rocks()
        self.preys = []
        self._spawn_preys()
        self.worms = []
        self._spawn_worms()
        self.pheromone_map.fill(0.0)
        self.is_night = False
        
    def get_agent_observation(self, agent: dict) -> np.ndarray:
        # Dummy implementation to satisfy BaseWorld ABC.
        # TensorWorld uses get_batch_observations instead.
        return np.zeros(self.config.agent.num_inputs, dtype=np.float32)

    def _generate_geometry(self):
        for _ in range(10):
            x, y, z = np.random.randint(0, self.size, 3) if self.use_3d else (*np.random.randint(0, self.size, 2), 0)
            z = min(z, self.dim_z - 1)
            if np.random.rand() > 0.3:
                self.geometry[z, y, x] = 1
        for _ in range(5):
            x, y, z = np.random.randint(0, self.size, 3) if self.use_3d else (*np.random.randint(0, self.size, 2), 0)
            z = min(z, self.dim_z - 1)
            self.geometry[z, y, x] = 2

    def _generate_trees(self):
        self.trees = []
        self.tree_data = []
        num_trees = max(1, self.size // 3)
        for _ in range(num_trees):
            tx, ty, tz = np.random.randint(1, self.size - 1, 3) if self.use_3d else (*np.random.randint(1, self.size - 1, 2), 0)
            tz = min(tz, self.dim_z - 1)
            self.trees.append((tx, ty, tz))
            self.geometry[tz, ty, tx] = 4
            is_fruit = np.random.rand() < self.config.fruit_tree_ratio
            cooldown = np.random.randint(50, 150) if is_fruit else 0
            self.tree_data.append({"is_fruit": is_fruit, "cooldown": cooldown})
            for fz in range(max(0, tz-1), min(self.dim_z, tz+2)):
                for fy in range(max(0, ty-1), min(self.size, ty+2)):
                    for fx in range(max(0, tx-1), min(self.size, tx+2)):
                        if self.geometry[fz, fy, fx] == 0:
                            self.geometry[fz, fy, fx] = 5
            for _ in range(np.random.randint(1, 4)):
                stick_type = np.random.choice(["stick", "stick_short", "stick_long", "Wood"])
                sx = np.clip(tx + np.random.choice([-1, 1]), 0, self.size-1)
                sy = np.clip(ty + np.random.choice([-1, 1]), 0, self.size-1)
                sz = tz
                self.items.append({"x": sx, "y": sy, "z": sz, "type": stick_type, "weight": 1.0})

    def _spawn_rocks(self):
        while True:
            bx, by, bz = np.random.randint(0, self.size, 3) if self.use_3d else (*np.random.randint(0, self.size, 2), 0)
            bz = min(bz, self.dim_z - 1)
            if self.geometry[bz, by, bx] == 0:
                self.items.append({"x": bx, "y": by, "z": bz, "type": "rock", "weight": np.random.uniform(1.0, 10.0)})
                break

    def _decode_act_override(self, agent, action):
        """Décode-et-agis (EDR 075) : l'auditeur décode le token du locuteur le plus proche (via le Wd
        de sa tête) et oriente son mouvement — APPROCHER si Mammouth/Ours prédit, FUIR si Leurre. Teste
        le bénéfice fonctionnel du langage fiable. Renvoie l'action (0-3) éventuellement réorientée."""
        model = agent.get("model")
        rh = getattr(model, "ref_head", None) if model is not None else None
        if rh is None:
            return action
        R = max(getattr(self, "hear_radius", 0), 1)
        best, bestd = None, 1e9
        for o in self.agents:
            if o is agent:
                continue
            ls = o.get("last_spoken", [0.0] * 4)
            if all(abs(v) < 0.01 for v in ls) or ls == [99.0] * 4:   # silence ou marqueur spark
                continue
            if self._apex_idx(o) is None:   # ne réagir qu'aux locuteurs RÉELLEMENT près d'un apex
                continue                    # (sinon bruit de bavardage) -> isole la qualité du TOKEN
            d = abs(o["x"] - agent["x"]) + abs(o["y"] - agent["y"])
            if d <= R and d < bestd:
                bestd, best = d, o
        if best is None:
            return action
        tok = np.array(best["last_spoken"], dtype=float)
        pred = int(np.argmax(tok @ rh["Wd"]))            # token -> apex (0 Mam, 1 Ours, 2 Leurre)
        dx, dy = best["x"] - agent["x"], best["y"] - agent["y"]
        if pred == 2:                                    # Leurre -> fuir (inverser la direction)
            dx, dy = -dx, -dy
        if dx == 0 and dy == 0:
            return action
        self.decode_act_fires = getattr(self, "decode_act_fires", 0) + 1   # diagnostic : le mécanisme s'active-t-il ?
        if abs(dx) >= abs(dy):                           # action : 2=E(nx+1) 3=W(nx-1) 1=S(ny+1) 0=N(ny-1)
            return 2 if dx > 0 else 3
        return 1 if dy > 0 else 0

    def _apex_idx(self, agent):
        """0 Mammouth / 1 Ours / 2 Leurre si l'agent est adjacent à un apex, sinon None (EDR 074)."""
        idx = {"Mammouth": 0, "Ours": 1, "Leurre": 2}
        for p in self.preys:
            if p["type"] in idx and abs(agent["x"] - p["x"]) + abs(agent["y"] - p["y"]) <= 1:
                return idx[p["type"]]
        return None

    def _spawn_prey_instance(self, p_type):
        while True:
            x, y, z = np.random.randint(0, self.size, 3) if self.use_3d else (*np.random.randint(0, self.size, 2), 0)
            z = min(z, self.dim_z - 1)
            if self.geometry[0, y, x] == 0:
                cfg = self.config.preys.get(p_type, None)
                hp = cfg.hp if cfg else 1.0
                self.preys.append({"x": x, "y": y, "type": p_type, "stunned": 0, "hp": hp})
                break

    def _spawn_worms(self):
        for _ in range(5):
            wx, wy, wz = np.random.randint(0, self.size, 3) if self.use_3d else (*np.random.randint(0, self.size, 2), 0)
            wz = min(wz, self.dim_z - 1)
            self.worms.append({"x": wx, "y": wy, "z": wz})

    def _spawn_preys(self):
        for t in ["Lapin"]*3 + ["Cerf"]*2 + ["Sanglier"]*2 + ["Mammouth"]:
            self._spawn_prey_instance(t)

    def _spawn_treasure(self):
        while True:
            tx, ty, tz = np.random.randint(0, self.size, 3) if self.use_3d else (*np.random.randint(0, self.size, 2), 0)
            tz = min(tz, self.dim_z - 1)
            if self.geometry[tz, ty, tx] == 0:
                self.treasure_x, self.treasure_y, self.treasure_z = tx, ty, tz
                break

    def add_agent(self, agent_model, x=None, y=None, z=None, energy=None):
        if x is None: x = np.random.randint(0, self.size)
        if y is None: y = np.random.randint(0, self.size)
        if z is None: z = np.random.randint(0, self.dim_z) if self.use_3d else 0
        if energy is None: energy = self.config.agent.energy_start
        agent_id = str(uuid.uuid4())[:8]
        
        agent = {
            "id": agent_id,
            "model": agent_model,
            "x": x, "y": y, "z": z,
            "energy": energy,
            "hp": 100.0 + agent_model.phenotype_hp_bonus,
            "confort": 50.0,
            "age": 0,
            "preys_eaten": 0,
            "mammoth_kills": 0,
            "altars_solved": 0,
            "spears_crafted": 0,
            "last_action": -1,
            "inventory": [],
            "inv_capacity": agent_model.phenotype_inv_capacity,
            "throw_feedback": 0.0,
            "throw_feedback_ttl": 0,
            "last_spoken": [0.0]*4,
            "status": {"jumping": False, "ducking": False},
            "visited_positions": set()
        }
        
        # Injection de la révélation mémorielle (LangGraph Librarian)
        if hasattr(agent_model, "memory_recall"):
            agent["memory_recall"] = list(agent_model.memory_recall)
            
        self.agents.append(agent)
        logger.emit("AGENT_BIRTH", {"id": agent_id, "x": x, "y": y})

    def item_physics(self, item_type):
        if isinstance(item_type, dict):
            item_type = item_type.get("type", "unknown")
        if not isinstance(item_type, str):
            item_type = str(item_type)
        return self.physics_registry.get_properties(item_type)

    def get_batch_observations(self) -> np.ndarray:
        if not self.agents:
            return np.array([])
            
        N = len(self.agents)
        ax = np.array([a["x"] for a in self.agents])
        ay = np.array([a["y"] for a in self.agents])
        
        # To get direction to closest prey
        dn = np.zeros(N, dtype=np.float32)
        ds = np.zeros(N, dtype=np.float32)
        de = np.zeros(N, dtype=np.float32)
        dw = np.zeros(N, dtype=np.float32)
        is_flying = np.zeros(N, dtype=np.float32)
        is_stunned = np.zeros(N, dtype=np.float32)
        # Perception de PROXIMITÉ du type d'apex (EDR 047, jeu de Lewis) : +1 Mammouth (bon),
        # -1 Leurre (piège), 0 sinon — perçu SEULEMENT si adjacent. À distance, indistinguable
        # -> crée la demande référentielle (il faut le signal pour savoir lequel).
        on_apex_type = np.zeros(N, dtype=np.float32)
        if self.preys:
            px = np.array([p["x"] for p in self.preys])
            py = np.array([p["y"] for p in self.preys])
            for i in range(N):
                dists = np.abs(px - ax[i]) + np.abs(py - ay[i])
                closest_idx = np.argmin(dists)
                p = self.preys[closest_idx]
                dn[i] = max(0, ay[i] - p["y"]) / self.size
                ds[i] = max(0, p["y"] - ay[i]) / self.size
                de[i] = max(0, p["x"] - ax[i]) / self.size
                dw[i] = max(0, ax[i] - p["x"]) / self.size
                is_flying[i] = 1.0 if p["type"] in ["Lapin", "Cerf"] else 0.0
                is_apex = p["type"] in ("Mammouth", "Ours", "Leurre")
                if dists[closest_idx] <= 1 and is_apex:           # adjacent à un apex -> on perçoit le type
                    # Mémoire (EDR 058) : si transient_apex, révélé SEULEMENT au premier contact
                    # (puis caché) -> l'agent doit le RETENIR pour rester/fuir. Sature la mémoire.
                    reveal = (not self.transient_apex) or (not self.agents[i].get("_adj_apex_prev", False))
                    if reveal:
                        on_apex_type[i] = {"Mammouth": 1.0, "Ours": 0.5, "Leurre": -1.0}[p["type"]]
                    self.agents[i]["_adj_apex_prev"] = True
                else:
                    self.agents[i]["_adj_apex_prev"] = False
                is_stunned[i] = 1.0 if p.get("stunned", 0) > 0 else 0.0

        # Lidar using advanced indexing (with padding to handle borders safely)
        padded_geom = np.pad(self.geometry[0], 1, mode='constant', constant_values=1)
        # Shift coords because of padding (+1)
        lidar_n = padded_geom[ay, ax + 1] / 3.0
        lidar_s = padded_geom[ay + 2, ax + 1] / 3.0
        lidar_e = padded_geom[ay + 1, ax + 2] / 3.0
        lidar_w = padded_geom[ay + 1, ax] / 3.0
        
        # Grid variables extraction
        pheromone = np.clip(self.pheromone_map[0, ay, ax], 0.0, 1.0)
        
        altar_active = np.zeros(N, dtype=np.float32)
        bit_a = np.zeros(N, dtype=np.float32)
        bit_b = np.zeros(N, dtype=np.float32)
        for altar in self.altars:
            mask = (ax == altar["x"]) & (ay == altar["y"])
            altar_active[mask] = 1.0
            bit_a[mask] = altar["bit_a"]
            bit_b[mask] = altar["bit_b"]
            
        # Vectorized adj_energy and in_hear (Tensor Lidar)
        dx = ax[:, None] == ax[None, :]
        dy = ay[:, None] == ay[None, :]
        same_cell = dx & dy  # Shape (N, N)
        np.fill_diagonal(same_cell, False)
        
        agent_energies = np.array([a["energy"] / 100.0 for a in self.agents], dtype=np.float32)
        energy_matrix = np.where(same_cell, agent_energies[None, :], 0.0)
        adj_energy = np.max(energy_matrix, axis=1)
        
        spoken_arr = np.array([a.get("last_spoken", [0.0]*4) for a in self.agents], dtype=np.float32)
        radius = getattr(self, "hear_radius", 0)
        if radius > 0:
            # Portée du signal (EDR 038) : entendre les agents proches, atténué par la distance
            # -> capacité physique de RECRUTEMENT (le sens reste à émerger, non scripté).
            dist = np.abs(ax[:, None] - ax[None, :]) + np.abs(ay[:, None] - ay[None, :])  # Manhattan
            atten = np.maximum(0.0, 1.0 - dist / (radius + 1.0))
            np.fill_diagonal(atten, 0.0)
            in_hear = np.max(spoken_arr[None, :, :] * atten[:, :, None], axis=1)
        else:
            spoken_matrix = np.where(same_cell[:, :, None], spoken_arr[None, :, :], 0.0)
            in_hear = np.max(spoken_matrix, axis=1)
                    
        worm_nearby = np.zeros(N, dtype=np.float32)
        for w in self.worms:
            worm_nearby[(ax == w["x"]) & (ay == w["y"])] = 1.0
            
        # Inventory & State
        in_throw = np.array([a.get("throw_feedback", 0.0) for a in self.agents], dtype=np.float32)
        in_surprise = np.array([a["model"].surprise for a in self.agents], dtype=np.float32)
        in_hp = np.array([a["hp"] / 100.0 for a in self.agents], dtype=np.float32)
        in_confort = np.array([a.get("confort", 50.0) / 100.0 for a in self.agents], dtype=np.float32)
        is_night_arr = np.ones(N, dtype=np.float32) if getattr(self, 'is_night', False) else np.zeros(N, dtype=np.float32)
        
        fire_nearby = np.zeros(N, dtype=np.float32)
        for f in self.items:
            if f.get("type") == "Fire":
                mask = (np.abs(ax - f["x"]) <= 1) & (np.abs(ay - f["y"]) <= 1)
                fire_nearby[mask] = 1.0
        
        in_slot1_type = np.zeros(N, dtype=np.float32)
        in_slot2_type = np.zeros(N, dtype=np.float32)
        in_slot1_weight = np.zeros(N, dtype=np.float32)
        
        for i, a in enumerate(self.agents):
            if len(a["inventory"]) > 0:
                in_slot1_type[i] = 1.0
                item = a["inventory"][0]
                w, _, _, _, _ = self.item_physics(item)
                in_slot1_weight[i] = w
            if len(a["inventory"]) > 1:
                in_slot2_type[i] = 1.0
                
        # Items grid
        grid_item_count = np.zeros((self.size, self.size), dtype=np.float32)
        for it in self.items:
            grid_item_count[it["y"], it["x"]] += 1.0
            
        in_nearby_item_count = np.zeros(N, dtype=np.float32)
        in_nearby_item_type = np.zeros(N, dtype=np.float32)
        padded_items = np.pad(grid_item_count, 1, mode='constant', constant_values=0)
        
        for i in range(N):
            # 3x3 window around agent (padded space)
            window = padded_items[ay[i]:ay[i]+3, ax[i]:ax[i]+3]
            count = np.sum(window)
            in_nearby_item_count[i] = min(count, 10.0) / 10.0
            in_nearby_item_type[i] = 1.0 if count > 0 else 0.0

        terrain_1 = np.zeros(N, dtype=np.float32)
        terrain_2 = np.zeros(N, dtype=np.float32)
        terrain_3 = np.zeros(N, dtype=np.float32)
        terrain_4 = np.zeros(N, dtype=np.float32)
        for i, a in enumerate(self.agents):
            terrain_type = self.terrain_type[a["y"], a["x"]]
            if terrain_type == 0: terrain_1[i] = 1.0
            elif terrain_type == 1: terrain_2[i] = 1.0
            elif terrain_type == 2: terrain_3[i] = 1.0
            elif terrain_type == 3: terrain_4[i] = 1.0
            
        dist_treasure = np.array([(abs(a["x"] - self.treasure_x) + abs(a["y"] - self.treasure_y))/(self.size * 2) for a in self.agents], dtype=np.float32)
        num_preys = np.ones(N, dtype=np.float32) * min(len(self.preys), 20) / 20.0
        agent_age = np.array([min(a["age"], 1000)/1000.0 for a in self.agents], dtype=np.float32)
        inv_size = np.array([min(len(a["inventory"]), 10)/10.0 for a in self.agents], dtype=np.float32)
            
        # Compile batch_obs [N, 45] (or whatever original size was, looks like ~45 inputs)
        # Original inputs were: dn, ds, de, dw, dup, ddown, 1.0, pheromone, abs_x, abs_y, abs_z, altar_active, bit_a, bit_b, adj_energy
        # + in_hear(4) + lidar(6) + is_flying, is_stunned, in_surprise, worm_nearby, in_throw, in_doubt
        # + in_slot1_type, in_slot2_type, in_slot1_weight, in_nearby_item_type, in_nearby_item_count, in_hp
        # + terrain(4) + energy + dist_treasure + num_preys + agent_age + inv_size
        
        # EXP-10 : Graph-RAG Memory Recall (Active Epistemics: wired to sensory observations)
        if getattr(self.config, "active_exp_variable", "NONE") == "RAG":
            in_mem = np.zeros((N, 5), dtype=np.float32)
            for i in range(N):
                q = [float(dn[i]), float(ds[i]), float(de[i]), float(dw[i]), float(pheromone[i])]
                in_mem[i] = self.memory_retriever.get_rag_memory(str(self.agents[i]["id"]), q)
        else:
            in_mem = np.array([self.memory_retriever.get_memory_vector(str(a["id"])) for a in self.agents], dtype=np.float32)
        
        # NTM Memory (Explicit Differential Memory)
        ntm_mem = np.array([a["model"].explicit_memory for a in self.agents], dtype=np.float32)
        if ntm_mem.shape[1] != 5:
            ntm_mem = np.zeros((N, 5), dtype=np.float32) # Fallback if agent is not updated yet
            
        # Manager Goal (Hierarchical)
        manager_goal = np.array([getattr(a["model"], "goal_vector", np.zeros(5)) for a in self.agents], dtype=np.float32)
        if len(manager_goal.shape) < 2 or manager_goal.shape[1] != 5:
            manager_goal = np.zeros((N, 5), dtype=np.float32)
            
        obs = np.column_stack([
            dn, ds, de, dw, on_apex_type, np.zeros(N), np.ones(N), pheromone,
            ax/self.size, ay/self.size, np.zeros(N), altar_active, bit_a, bit_b, adj_energy,
            in_hear[:,0], in_hear[:,1], in_hear[:,2], in_hear[:,3],
            lidar_n, lidar_s, lidar_e, lidar_w, np.zeros(N), np.zeros(N),
            is_flying, is_stunned, in_surprise, worm_nearby, in_throw, np.zeros(N),
            in_slot1_type, in_slot2_type, in_slot1_weight, in_nearby_item_type, in_nearby_item_count, in_hp,
            terrain_1, terrain_2, terrain_3, terrain_4,
            in_hp, dist_treasure, num_preys, agent_age, inv_size,
            in_mem[:,0], in_mem[:,1], in_mem[:,2], in_mem[:,3], in_mem[:,4],
            in_confort, is_night_arr, fire_nearby,
            ntm_mem[:,0], ntm_mem[:,1], ntm_mem[:,2], ntm_mem[:,3], ntm_mem[:,4],
            manager_goal[:,0], manager_goal[:,1], manager_goal[:,2], manager_goal[:,3], manager_goal[:,4]
        ])
        
        # Ensure exact shape for backward compatibility
        expected_size = self.config.agent.num_inputs
        if obs.shape[1] < expected_size:
            padding = np.zeros((N, expected_size - obs.shape[1]))
            obs = np.concatenate([obs, padding], axis=1)
        elif obs.shape[1] > expected_size:
            obs = obs[:, :expected_size]
            
        return obs

    def _move_preys(self):
        fire_pos = [(f["x"], f["y"]) for f in self.items if f.get("type") == "Fire"]
        for p in self.preys:
            if p.get("stunned", 0) > 0:
                p["stunned"] -= 1
                continue
                
            fled = False
            for fx, fy in fire_pos:
                if abs(p["x"] - fx) <= 2 and abs(p["y"] - fy) <= 2:
                    p["x"] += 1 if p["x"] > fx else -1
                    p["y"] += 1 if p["y"] > fy else -1
                    p["x"] = np.clip(p["x"], 0, self.size - 1)
                    p["y"] = np.clip(p["y"], 0, self.size - 1)
                    fled = True
                    break
            if fled: continue
                
            cfg = self.config.preys.get(p["type"], None)
            moves_per_tick = cfg.moves_per_tick if cfg else 0
            
            # Handle fractional moves (e.g. 0.2 means 20% chance to move)
            moves = int(moves_per_tick)
            if np.random.rand() < (moves_per_tick - moves):
                moves += 1
            
            if self.agents:
                closest = min(self.agents, key=lambda a: abs(a["x"]-p["x"]) + abs(a["y"]-p["y"]))
                dx, dy = closest["x"] - p["x"], closest["y"] - p["y"]
                
                # Riposte (C, fairness) : le gibier ne blesse que l'agent qui l'ATTAQUE
                # (même case), pas par simple proximité. Un agent prudent survit ;
                # tuer un Mammouth exige de l'attaquer -> prendre 50 -> donc une lance.
                if cfg and cfg.damage > 0 and dx == 0 and dy == 0:
                    closest["hp"] -= cfg.damage
                    continue
                    
                for _ in range(moves):
                    action = -1
                    if p["type"] in ["Lapin", "Cerf"]:
                        action = 2 if dx > 0 else 3 if abs(dx) > abs(dy) else 1 if dy > 0 else 0
                    else:
                        action = 3 if dx > 0 else 2 if abs(dx) > abs(dy) else 0 if dy > 0 else 1
                        
                    nx, ny = p["x"], p["y"]
                    if action == 0 and ny > 0: ny -= 1
                    elif action == 1 and ny < self.size - 1: ny += 1
                    elif action == 2 and nx > 0: nx -= 1
                    elif action == 3 and nx < self.size - 1: nx += 1
                    if self.geometry[0, ny, nx] == 0:
                        p["x"], p["y"] = nx, ny

    def _resolve_biology(self, agent, action, logits):
        # Base drain (métabolisme). EDR 084 : la survie plafonne car 79% starvent ; `base_metabolism`
        # (config, défaut 1.0) règle le drain pour viser le sweet spot dureté↔soutenabilité.
        drain = getattr(self.config, "base_metabolism", 1.0) * agent["model"].phenotype_energy_drain

        # NAS Axe D-1 : coût métabolique d'activation (gated). Placé avant la modulation nuit/feu
        # pour que "penser" coûte aussi plus cher la nuit (cohérence thermodynamique).
        coef = getattr(self.config, "metabolic_cost_coef", 0.0)
        if coef > 0.0:
            drain += coef * getattr(agent["model"], "last_activation_cost", 0)

        # EXP-9 : Thermodynamique & Nuit
        is_near_fire = any(f.get("type") == "Fire" and abs(agent["x"] - f["x"]) <= 2 and abs(agent["y"] - f["y"]) <= 2 for f in self.items)
        if getattr(self, "is_night", False):
            if is_near_fire:
                drain = drain * 0.5 # Le feu tient chaud
                agent["confort"] = min(100.0, agent.get("confort", 50.0) + 0.1)
                # Récompense douce pour le regroupement
                agent["energy"] += 0.5
            else:
                drain = drain * 2.5 # Froid glacial nocturne
                agent["confort"] = max(0.0, agent.get("confort", 50.0) - 0.5)

        agent["energy"] -= drain
        
        terrain = self.terrain_type[agent["y"], agent["x"]]
        agent["energy"] -= [self.config.biome.plains_drain, self.config.biome.forest_drain, self.config.biome.water_drain, self.config.biome.desert_drain][terrain]

        # A) Scaffold d'approche (annelé) : récompense la réduction de distance au
        # gibier le plus proche -> enseigne la chasse (fix du goulot, EDR 012).
        if self.preys:
            d = min(abs(agent["x"] - p["x"]) + abs(agent["y"] - p["y"]) for p in self.preys)
            lam = anneal(getattr(self, "current_era", 1), self.scaffold_eras)
            agent["energy"] += approach_reward(agent.get("last_prey_dist", d), d, self.scaffold_eps, lam)
            agent["last_prey_dist"] = d

        carry_weight = sum(i.get("weight", 1.0) if isinstance(i, dict) else 1.0 for i in agent["inventory"])
        agent["energy"] -= carry_weight * 0.5
        
        if len(agent["inventory"]) > 0:
            first_item = agent["inventory"][0]
            item_type = first_item.get("type", "") if isinstance(first_item, dict) else str(first_item)
            if item_type == "Fruit" and agent["energy"] < 80:
                agent["energy"] = min(100.0, agent["energy"] + 20.0)
                agent["inventory"].pop(0)
                new_seed = {"x": agent["x"], "y": agent["y"], "z": 0, "type": "Seed", "weight": 0.1, "ttl": 100}
                if len(agent["inventory"]) < agent["inv_capacity"]:
                    agent["inventory"].append(new_seed)
                else:
                    self.items.append(new_seed)
        
        do_jump = float(logits[9]) > 0
        do_duck = float(logits[10]) > 0
        agent["status"]["jumping"] = do_jump
        agent["status"]["ducking"] = do_duck
        if do_jump or do_duck: agent["energy"] -= 1.0
        
        if action == 6 and agent["energy"] > 50.0 and agent["hp"] < 100.0:
            agent["energy"] -= 10.0
            agent["hp"] = min(100.0, agent["hp"] + 10.0)

        # Hunt / Attack (Asymmetrical combat)
        attacked_prey = next((p for p in self.preys if agent["x"] == p["x"] and agent["y"] == p["y"]), None)
        if attacked_prey:
            cfg_atk = self.config.preys.get(attacked_prey["type"], None)
            holds_spear = has_spear(agent["inventory"])
            # Coup CRITIQUE annealé (EDR 022) : décisif uniquement avec une lance contre un
            # gros gibier qui riposte (cfg.damage>0) -> « force le destin » tôt, se sèvre par monde.
            era = getattr(self, "current_era", 1)
            is_crit = (holds_spear and cfg_atk and cfg_atk.damage > 0
                       and np.random.rand() < crit_chance(self.crit_base, era, self.crit_eras))
            # Dégâts dépendant de l'outil (Step 2) : 10 à mains nues, 50 avec une lance ; ×crit_mult sur crit.
            damage_dealt = attack_damage(weapon_damage(holds_spear), is_crit, self.crit_mult)
            attacked_prey["hp"] -= damage_dealt
            attacked_prey.setdefault("attackers", set()).add(agent["id"])  # récompense de groupe (EDR 028)
            logger.emit("PREY_ATTACKED", {"agent_id": agent["id"], "prey_type": attacked_prey["type"], "damage": damage_dealt, "crit": bool(is_crit)})

            # A) Scaffold : prime de courage à frapper un gros gibier (cfg.damage>0), annelé.
            if cfg_atk and cfg_atk.damage > 0:
                agent["energy"] += self.scaffold_bighit * anneal(getattr(self, "current_era", 1), self.scaffold_eras)

            if attacked_prey["hp"] <= 0:
                # Récompense ∝ difficulté (Step 2) : le Lapin sustente, le Mammouth enrichit.
                cfg_prey = self.config.preys.get(attacked_prey["type"], None)
                reward = prey_reward(cfg_prey.hp if cfg_prey else 1.0) * getattr(self.config, "forage_payoff", 1.0)
                if attacked_prey["type"] == "Leurre":
                    # PIÈGE (EDR 047, jeu de Lewis) : aucune récompense — la riposte a déjà puni.
                    # Approcher un Leurre est une PERTE -> il faut le signal pour l'éviter.
                    self.leurre_hits += 1   # EDR 075 : à minimiser (le signal fiable doit l'éviter)
                elif cfg_prey and cfg_prey.hp >= 50:
                    # APEX (Mammouth) : récompense de GROUPE (EDR 028) — la prise nourrit TOUT
                    # le pack qui l'a attaqué -> incite à rejoindre les chasses coopératives
                    # (riposte partagée + dégâts cumulés one-shotent) -> la coordination émerge
                    # par sélection, sans dépendre du crit chanceux.
                    if getattr(self, "coop_reward", True):
                        attackers = attacked_prey.get("attackers", {agent["id"]})
                        pack = [o for o in self.agents if o["id"] in attackers]
                        n = max(1, len(pack))
                        # Prime annealée (EDR 030) : 1.0 (pleine à chacun) -> 1/n (festin partagé).
                        scaffold = anneal(getattr(self, "current_era", 1), self.group_reward_eras)
                        share = scaffold + (1.0 - scaffold) / n
                        for other in pack:
                            other["energy"] = min(self.config.agent.energy_max, other["energy"] + reward * share)
                            other["preys_eaten"] += 1
                            other["mammoth_kills"] = other.get("mammoth_kills", 0) + 1
                    else:
                        # Ablation coopération (EDR 039) : tueur seul.
                        agent["energy"] = min(self.config.agent.energy_max, agent["energy"] + reward)
                        agent["preys_eaten"] += 1
                        agent["mammoth_kills"] = agent.get("mammoth_kills", 0) + 1
                    self.big_kills = getattr(self, "big_kills", 0) + 1
                    # Réciprocité du LOCUTEUR (EDR 050) : les agents qui ont annoncé ce Mammouth
                    # touchent une prime -> parler PAIE pour le parleur (vainc le silence, EDR 048).
                    if self.speaker_reward > 0:
                        signalers = attacked_prey.get("signalers", set())
                        by_id = {o["id"]: o for o in self.agents}
                        for sid in signalers:
                            sp = by_id.get(sid)
                            if sp is not None:
                                sp["energy"] = min(self.config.agent.energy_max, sp["energy"] + self.speaker_reward)
                else:
                    agent["energy"] = min(self.config.agent.energy_max, agent["energy"] + reward)
                    agent["preys_eaten"] += 1
                self.preys.remove(attacked_prey)
                # RARETÉ (Step 2) : plus de respawn instantané — régénération lente ailleurs.
                logger.emit("PREY_KILLED", {"agent_id": agent["id"], "prey_type": attacked_prey["type"], "reward": float(reward)})
            
        if do_duck:
            eaten_worm = next((w for w in self.worms if w["x"] == agent["x"] and w["y"] == agent["y"] and w.get("z", 0) == agent.get("z", 0)), None)
            if eaten_worm:
                agent["energy"] += 10.0
                self.worms.remove(eaten_worm)
                self._spawn_worms() # spawn 1 worm actually
                
        if agent["x"] == self.treasure_x and agent["y"] == self.treasure_y and agent.get("z", 0) == self.treasure_z and float(logits[14]) > 0:
            agent["energy"] += self.config.treasure_reward
            logger.emit("TREASURE_FOUND", {"agent_id": agent["id"]})
            self._spawn_treasure()

    def _resolve_social(self):
        new_agents = []
        for i, a in enumerate(self.agents):
            for j, b in enumerate(self.agents):
                if i >= j: continue
                if a["x"] == b["x"] and a["y"] == b["y"] and a.get("z", 0) == b.get("z", 0):
                    # Remove explicit language alignment reward
                    # We just log if they are talking nearby
                    if a["last_spoken"] != [0.0]*4 or b["last_spoken"] != [0.0]*4:
                        logger.emit("SOCIAL_ENCOUNTER", {"a": a["id"], "b": b["id"], "spoken_a": a["last_spoken"], "spoken_b": b["last_spoken"]})
                        nearby_items = [it for it in self.items if it["x"] == a["x"] and it["y"] == a["y"] and it.get("z", 0) == a.get("z", 0)]
                        if nearby_items and a["last_spoken"] != [0.0]*4 and b["last_spoken"] != [0.0]*4:
                            t1 = nearby_items[0].get("type", "unknown")
                            if getattr(self.config, "active_exp_variable", "NONE") == "LANGUAGE":
                                token_a = np.argmax(a["last_spoken"])
                                token_b = np.argmax(b["last_spoken"])
                                if token_a == token_b:
                                    a["energy"] = min(100.0, a["energy"] + 0.5)
                                    b["energy"] = min(100.0, b["energy"] + 0.5)
                                    logger.emit("LANGUAGE_ALIGNMENT", {"a": a["id"], "b": b["id"], "item": t1, "token": int(token_a)})
                            else:
                                vec_a = np.array(a["last_spoken"])
                                vec_b = np.array(b["last_spoken"])
                                norm_a = np.linalg.norm(vec_a)
                                norm_b = np.linalg.norm(vec_b)
                                if norm_a > 0 and norm_b > 0:
                                    sim = np.dot(vec_a, vec_b) / (norm_a * norm_b)
                                    if sim > 0.8:
                                        a["energy"] = min(100.0, a["energy"] + 0.5)
                                        b["energy"] = min(100.0, b["energy"] + 0.5)
                                        avg_vec = (vec_a + vec_b) / 2.0
                                        logger.emit("LANGUAGE_ALIGNMENT", {"a": a["id"], "b": b["id"], "item": t1, "vector": avg_vec.tolist()})

                    if getattr(self.config, "active_exp_variable", "NONE") in ["INTRINSIC", "TOM"]:
                        pred_a = np.argmax(a["model"].predictor_head)
                        pred_b = np.argmax(b["model"].predictor_head)
                        # Recompense Theory of Mind si A prédit l'action de B et vice versa
                        if pred_a == b.get("last_action", -1):
                            a["energy"] = min(100.0, a["energy"] + 2.0)
                            logger.emit("THEORY_OF_MIND_SUCCESS", {"predictor": a["id"], "target": b["id"], "action": pred_a})
                        if pred_b == a.get("last_action", -1):
                            b["energy"] = min(100.0, b["energy"] + 2.0)
                            logger.emit("THEORY_OF_MIND_SUCCESS", {"predictor": b["id"], "target": a["id"], "action": pred_b})

                    if a["last_spoken"] == [99.0]*4:
                        b["model"].absorb_knowledge(a["model"].genome, learning_rate=0.5)
                        b["energy"] += 5.0
                        logger.emit("KNOWLEDGE_TRANSFER", {"teacher": a["id"], "student": b["id"]})
                        
                    if a["out_mate"] > 0 and b["out_mate"] > 0 and a["energy"] > 30.0 and b["energy"] > 30.0:
                        a["energy"] -= 15.0
                        b["energy"] -= 15.0
                        child_model = a["model"].clone()
                        child_model.mutate()
                        new_agents.append((child_model, a["x"], a["y"], 30.0))
                        logger.emit("MATE", {"parent1": a["id"], "parent2": b["id"]})
        return new_agents

    def _apply_social_consensus(self, batch_logits: np.ndarray) -> np.ndarray:
        if batch_logits.size == 0:
            return batch_logits

        positions = {}
        for idx, agent in enumerate(self.agents):
            pos = (agent["x"], agent["y"])
            positions.setdefault(pos, []).append(idx)

        for pos, indices in positions.items():
            if len(indices) < 2:
                continue

            predictions = []
            for idx in indices:
                logits = batch_logits[idx]
                out_share = float(logits[13]) if len(logits) > 13 else 0.0
                out_accept = float(logits[14]) if len(logits) > 14 else 0.0
                if out_share > 0.5 and out_accept > 0.0:
                    agent = self.agents[idx]
                    fitness = float((agent["energy"] + agent["hp"]) / 200.0)
                    predictions.append((agent["id"], logits, fitness))

            if len(predictions) > 1:
                consensus_logits = self.consensus.vote(predictions)
                for idx in indices:
                    batch_logits[idx] = consensus_logits
                logger.emit("SOCIAL_CONSENSUS", {"position": pos, "group_size": len(indices)})

        return batch_logits

    def _apply_hgt_breeding(self) -> list[tuple]:
        new_agents = []
        for i, a in enumerate(self.agents):
            for j, b in enumerate(self.agents):
                if i >= j:
                    continue
                if a["x"] == b["x"] and a["y"] == b["y"] and a.get("z", 0) == b.get("z", 0):
                    if a["out_share"] > 0.8 and b["out_accept"] > 0.8 and a["energy"] > 60 and b["energy"] > 60:
                        try:
                            offspring_w = self.hgt.transfer_layer(a["model"].genome.W, b["model"].genome.W)
                            child_model = a["model"].clone()
                            child_model.genome.W = offspring_w
                            child_model.update_phenotype()
                            child_model.reset_state()
                            new_agents.append((child_model, a["x"], a["y"], 40.0))
                            a["energy"] -= 15.0
                            b["energy"] -= 15.0
                            logger.emit("HGT_BREEDING", {"parent1": a["id"], "parent2": b["id"], "position": (a["x"], a["y"])})
                        except Exception as e:
                            logger.emit("HGT_FAILED", {"error": str(e), "parents": [a["id"], b["id"]]})
        return new_agents

    def _apply_surprise_hgt(self):
        threshold = getattr(self.config, "hgt_surprise_threshold", 0.75)
        hgt_power = getattr(self.config, "hgt_surprise_power", 0.2)
        
        for agent in self.agents:
            surprise = float(agent["model"].surprise_momentum)
            if surprise > threshold:
                best_neighbor = None
                best_energy = agent["energy"] * 1.2
                
                for other in self.agents:
                    if other is not agent:
                        dist = abs(other["x"] - agent["x"]) + abs(other["y"] - agent["y"])
                        if dist <= 2 and other["energy"] > best_energy:
                            best_energy = other["energy"]
                            best_neighbor = other
                
                if best_neighbor:
                    try:
                        agent["model"].absorb_knowledge(best_neighbor["model"].genome, learning_rate=hgt_power)
                        agent["energy"] = max(5.0, agent["energy"] - 5.0)
                        logger.emit("SURPRISE_HGT", {
                            "student": agent["id"],
                            "teacher": best_neighbor["id"],
                            "surprise": surprise,
                            "position": (agent["x"], agent["y"])
                        })
                    except Exception as e:
                        logger.emit("HGT_FAILED", {"error": str(e), "parents": [agent["id"], best_neighbor["id"]]})

    def step(self):
        self.ticks += 1
        was_night = getattr(self, "is_night", False)
        # Curriculum : pas de nuit (mortelle) en mode entraînement -> les agents survivent
        # assez pour apprendre la collecte.
        self.is_night = ((self.ticks % 100) >= 50) and self.night_enabled and not self.training_mode
        
        # EXP-9: Bonus d'aube (Transition Nuit -> Jour)
        if was_night and not self.is_night:
            for a in self.agents:
                if a["energy"] > 30.0:
                    a["energy"] = min(100.0, a["energy"] + 15.0)
                    logger.emit("DAWN_SURVIVAL", {"agent_id": a["id"], "energy": a["energy"]})
        
        self.pheromone_map *= 0.90
        
        for idx, (tx, ty, *tz_info) in enumerate(self.trees):
            tz = tz_info[0] if tz_info else 0
            if idx < len(self.tree_data) and self.tree_data[idx]["is_fruit"]:
                self.tree_data[idx]["cooldown"] -= 1
                if self.tree_data[idx]["cooldown"] <= 0:
                    spawned = False
                    for dz in [0] if not self.use_3d else [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                if dx == 0 and dy == 0 and dz == 0: continue
                                sx, sy, sz = tx + dx, ty + dy, tz + dz
                                if (0 <= sx < self.size and 0 <= sy < self.size and 
                                    0 <= sz < self.dim_z and self.geometry[sz, sy, sx] == 0):
                                    self.items.append({"x": sx, "y": sy, "z": sz, "type": "Fruit", "weight": 0.5})
                                    spawned = True
                                    break
                            if spawned: break
                        if spawned: break
                    self.tree_data[idx]["cooldown"] = np.random.randint(50, 150)
                    
        self._move_preys()
        
        # RARETÉ recalibrée (C) : régénération en rafale plafonnée — jusqu'à
        # prey_regen_burst proies/step vers le plafond. Assez de flux pour qu'une
        # population persiste (capacité de charge), sans refill instantané.
        spawned = 0
        while (not self.training_mode) and len(self.preys) < self.config.target_prey_count and spawned < self.prey_regen_burst:
            self._spawn_prey_instance(np.random.choice(["Lapin", "Cerf", "Sanglier", "Mammouth"], p=[0.4, 0.3, 0.2, 0.1]))
            spawned += 1

        # Régénération de MATÉRIAUX (EDR 021) : assez de rock+stick pour que le craft soit
        # une stratégie VIABLE dans le monde dur (sinon physiquement marginal). Off en
        # entraînement (le driver gère l'abondance).
        if not self.training_mode:
            _mat_types = ("rock", "stick", "stick_long", "stick_short", "Wood")
            n_mat = sum(1 for it in self.items if it.get("type") in _mat_types)
            if n_mat < 24 and np.random.rand() < 0.5:
                if np.random.rand() < 0.5:
                    self._spawn_rocks()
                else:
                    mx, my = np.random.randint(0, self.size), np.random.randint(0, self.size)
                    self.items.append({"x": int(mx), "y": int(my), "z": 0, "type": "stick", "weight": 1.0})

        if not self.agents:
            return
            
        # VECTORIZED OBSERVATION & BATCHING
        batch_obs = self.get_batch_observations()
        models = [a["model"] for a in self.agents]
        MambaBatchModel.KWTA_KEEP_FRAC = getattr(self.config, "kwta_keep_frac", 1.0)
        batch_model = self.batch_model_cls(models, world_model=self.world_model)

        env_surprise_batch = np.array([a.get("last_env_surprise", 0.0) for a in self.agents])
        
        # RL: Track energy before actions
        old_energies = np.array([a["energy"] for a in self.agents], dtype=np.float32)
        
        batch_logits, compute_spent = batch_model.forward(batch_obs, env_surprise_batch=env_surprise_batch)
        batch_logits = self._apply_social_consensus(batch_logits)

        # Differentiable / Configurable TTC Caloric Cost
        base_cost = getattr(self.config, "ttc_base_cost", 0.01)
        night_mult = getattr(self.config, "ttc_night_penalty", 2.5) if getattr(self, "is_night", False) else 1.0

        for i, agent in enumerate(self.agents):
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e0"] = agent["energy"]                 # EDR099 : energie debut tick
            surprise_val = float(agent["model"].surprise_momentum)
            surprise_scale = 1.0 + surprise_val * getattr(self.config, "ttc_surprise_scale", 1.0)

            brain_cost = base_cost * (1.0 + np.log2(1.0 + compute_spent[i])) * night_mult * surprise_scale
            agent["energy"] = max(0.0, agent["energy"] - float(brain_cost))
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e_brain"] = agent["energy"]            # EDR099 : apres brain_cost
            
            if getattr(self.config, "active_exp_variable", "NONE") == "INTRINSIC":
                # Recompense Intrinsèque : La surprise génère de la dopamine (énergie)
                dopamine = float(agent["model"].surprise_momentum) * 5.0
                agent["energy"] = min(self.config.agent.energy_max, agent["energy"] + dopamine)
                
            k = int(compute_spent[i])
            if k > 0:
                agent["total_dreams"] = agent.get("total_dreams", 0) + k
            else:
                agent["total_reflexes"] = agent.get("total_reflexes", 0) + 1

        new_agents = []
        survivors = []

        for idx, agent in enumerate(self.agents):
            agent["age"] += 1
            logits = batch_logits[idx]

            # 1. Alignement de la Value (DreamerV3/J-EPA)
            # Récompenser l'agent si son 'value_pred' du tour précédent a bien prédit son gain d'énergie réel.
            current_energy = agent["energy"]
            if "last_energy" in agent and "last_value_pred" in agent:
                # delta_e normalisé approximativement
                delta_e = np.clip((current_energy - agent["last_energy"]) / 10.0, -1.0, 1.0)
                error = abs(delta_e - agent["last_value_pred"])
                # Bénédiction épistémique : +0.5 si la prédiction est parfaite
                alignment_reward = max(0.0, 0.5 - error)
                agent["energy"] = min(100.0, agent["energy"] + alignment_reward)
            
            agent["last_energy"] = agent["energy"]
            
            # Reset env_surprise
            agent["last_env_surprise"] = 0.0
            
            # Metacognition: record surprise and doubt
            agent["last_surprise"] = agent["model"].surprise
            probs = np.exp(logits[:6]) / (np.sum(np.exp(logits[:6])) + 1e-9)
            entropy = -np.sum(probs * np.log(probs + 1e-9))
            agent["last_entropy"] = min(entropy / 1.79, 1.0)
            
            if agent["last_action"] != -1:
                logits[agent["last_action"]] -= 0.1
                
            action = int(np.argmax(logits[:8]))
            if getattr(self, "decode_act", False):     # EDR 075 : décoder un signal entendu -> approcher prey / fuir Leurre
                action = self._decode_act_override(agent, action)
            # ε-greedy (EDR 019/025) : en entraînement, explorer l'espace d'action — mouvement
            # aléatoire + forcer les gestes jamais tirés (grab ; rub pour craft_level>=1).
            force_grab = False
            force_rub = False
            if self.explore_eps > 0 and np.random.rand() < self.explore_eps:
                action = np.random.randint(0, 8)
                force_grab = (np.random.rand() < 0.5)
                force_rub = (self.craft_level >= 1 and np.random.rand() < 0.5)
            agent["last_action"] = action
            
            do_throw = float(logits[8]) > 0
            aim_vec = np.array([float(logits[11]), float(logits[12])])
            if getattr(self.config, "active_exp_variable", "NONE") == "LANGUAGE":
                raw_spoken = logits[19:23]
                # Porte « parler/se taire » + coût (EDR 042) : on ne signale que si l'intention
                # de langage dépasse le seuil ; signaler coûte de l'énergie -> signal SÉLECTIF.
                if np.max(np.abs(raw_spoken)) > self.speak_threshold:
                    gumbel_noise = -np.log(-np.log(np.random.uniform(0, 1, size=4) + 1e-10) + 1e-10)
                    temp = 0.1
                    y = np.exp((raw_spoken + gumbel_noise) / temp)
                    token_idx = np.argmax(y / np.sum(y))
                    if self.use_ref_head:                  # EDR 074 : tête référentielle dédiée
                        model = agent.get("model")
                        rh = getattr(model, "ref_head", None) if model is not None else None
                        ai = self._apex_idx(agent) if rh is not None else None
                        if ai is not None:
                            from src.seed_ai.referential_head import speak_token
                            token_idx = speak_token(rh, ai)   # token <- code partagé fiable (apex->token)
                    if getattr(self, "scramble_signal", False):
                        # EDR 087 : BROUILLE le contenu (override la tête) -> bras de contrôle : même
                        # présence + même mécanisme décode-et-agis, mais contenu ALÉATOIRE. Isole le
                        # CONTENU linguistique du téléguidage spatial (audit adversarial).
                        token_idx = np.random.randint(4)
                    one_hot = np.zeros(4)
                    one_hot[token_idx] = 1.0
                    agent["last_spoken"] = [float(l) for l in one_hot]
                    agent["energy"] -= self.signal_cost
                else:
                    agent["last_spoken"] = [0.0] * 4      # silence
            else:
                agent["last_spoken"] = [float(l) for l in logits[19:23]]
            
            agent["out_share"] = float(logits[13]) if len(logits) > 13 else 0.0
            agent["out_accept"] = float(logits[14]) if len(logits) > 14 else 0.0
            agent["out_mate"] = float(logits[15]) if len(logits) > 15 else 0.0

            # EXP-10: Nouveaux logits Métacognitifs (après 25 = rub)
            do_rub = float(logits[25]) if len(logits) > 25 else 0.0
            if force_rub:  # ε-greedy : force le geste rub (craft L1+, EDR 025)
                do_rub = 1.0
            do_dream = float(logits[26]) if len(logits) > 26 else 0.0
            do_memorize = float(logits[27]) if len(logits) > 27 else 0.0
            value_pred = float(logits[28]) if len(logits) > 28 else 0.0
            
            # Maintien de la mémoire à court terme (fade out)
            if "memory_recall" in agent:
                agent["memory_recall"][4] *= 0.95
            else:
                agent["memory_recall"] = [0.0]*5
                
            if do_memorize > 0.5:
                # Émergence de la mémoire : Sauvegarde de la pensée dans KuzuDB
                agent["energy"] += 0.1 # Récompense épistémique
                thought = {
                    "agent_id": str(agent["id"]),
                    "action": int(action),
                    "value_pred": float(value_pred),
                    "surprise": float(agent["last_surprise"]),
                    "inventory_size": int(len(agent["inventory"]))
                }
                logger.emit("AGENT_THOUGHT", thought)
                
                # Injection dans la mémoire de travail (Explicit Memory)
                agent["memory_recall"] = [
                    float(action) / 8.0, 
                    float(value_pred), 
                    float(agent["last_surprise"]), 
                    float(len(agent["inventory"])) / 10.0, 
                    1.0  # Freshness
                ]

            # Adrénaline: Override du Doute en cas d'urgence
            is_in_danger = agent.get("last_surprise", 0.0) > 0.8 or agent["hp"] < 30.0
            
            # NOTE: Le rêve/MCTS est maintenant géré intégralement dans MambaBatchModel.forward().
            # compute_spent[idx] nous dit si l'agent a rêvé (> 0) ou non.
            # On reset simplement le compteur de rêve continu.
            agent["is_dreaming"] = 0
            agent["last_value_pred"] = value_pred
            
            # 4. Throw (Ballistic Physics V14)
            if do_throw and len(agent["inventory"]) > 0:
                thrown_item = agent["inventory"].pop(0)
                if isinstance(thrown_item, str):
                    thrown_item = {"type": thrown_item, "weight": 1.0}
                weight = thrown_item.get("weight", 1.0)
                
                norm = np.linalg.norm(aim_vec)
                if norm > 0: aim_vec = aim_vec / norm
                else: aim_vec = np.array([0,1])
                    
                energy_spent = 10.0 if agent["energy"] > 50.0 else 5.0
                agent["energy"] -= energy_spent
                
                t = 0.0
                dt = 0.1
                az = agent.get("z", 0)
                curr_x, curr_y = float(agent["x"]), float(agent["y"])
                end_pos = (agent["x"], agent["y"], az)
                hit_entity = None
                
                v_x = energy_spent * aim_vec[0]
                v_y = energy_spent * aim_vec[1]
                
                entity_map = {}
                for p in self.preys:
                    entity_map[(p["x"], p["y"], p.get("z", 0))] = p
                for a in self.agents:
                    if a is not agent:
                        entity_map[(a["x"], a["y"], a.get("z", 0))] = a
                
                while t < 2.0:
                    t += dt
                    nx = curr_x + v_x * t
                    ny = curr_y + v_y * t
                    
                    int_x, int_y = int(round(nx)), int(round(ny))
                    
                    if int_x < 0 or int_x >= self.size or int_y < 0 or int_y >= self.size:
                        break
                        
                    if self.geometry[0, int_y, int_x] != 0:
                        end_pos = (int_x, int_y, az)
                        break
                        
                    if (int_x, int_y, az) in entity_map:
                        hit_entity = entity_map[(int_x, int_y, az)]
                        end_pos = (int_x, int_y, az)
                        break
                    
                    end_pos = (int_x, int_y, az)

                thrown_item["x"], thrown_item["y"], thrown_item["z"] = end_pos[0], end_pos[1], end_pos[2]
                
                # EXP-9 : Fueling Fire
                is_fueled = False
                if thrown_item.get("type") == "Wood":
                    for f in self.items:
                        if f.get("type") == "Fire" and f["x"] == end_pos[0] and f["y"] == end_pos[1]:
                            f["ttl"] = min(2000, f.get("ttl", 0) + 500)
                            is_fueled = True
                            logger.emit("FIRE_FUELED", {"agent_id": agent["id"], "fire_id": f.get("id", "unknown"), "new_ttl": f["ttl"]})
                            break
                
                if not is_fueled:
                    self.items.append(thrown_item)
                
                if hit_entity:
                    damage = energy_spent * weight
                    if "energy" in hit_entity:
                        hit_entity["energy"] -= damage
                    else:
                        hit_entity["stunned"] = int(damage * 2)
                    agent["throw_feedback"] = 1.0
                    agent["throw_feedback_ttl"] = 5
                else:
                    agent["throw_feedback"] = -1.0
                    agent["throw_feedback_ttl"] = 5
                    
            # 5. Craft — Lance (AXE CRAFT, EDR 018, paramétré par craft_level) + Spark (feu).
            inv = agent["inventory"]
            phys_list = [self.item_physics(it) for it in inv]
            craft_idx = try_craft_spear(phys_list, do_rub, self.craft_level)
            if craft_idx is not None:
                # Tranchant + manche -> Lance. Consomme les 2 ingrédients (par index).
                agent["energy"] -= 2.0
                agent["inventory"] = [it for k, it in enumerate(inv) if k not in craft_idx]
                spear = {"type": "Spear", "weight": 2.0}
                if len(agent["inventory"]) < agent["inv_capacity"]:
                    agent["inventory"].append(spear)
                else:
                    spear["x"], spear["y"], spear["z"] = agent["x"], agent["y"], 0
                    self.items.append(spear)
                logger.emit("SPEAR_CRAFTED", {"agent_id": agent["id"]})
                agent["spears_crafted"] = agent.get("spears_crafted", 0) + 1  # fitness (EDR 016)
                # Scaffold : jalon de craft (annelé).
                agent["energy"] += self.scaffold_craft * anneal(getattr(self, "current_era", 1), self.scaffold_eras)
            elif do_rub and len(inv) >= 2 and phys_list[0][3] * phys_list[1][3] > 0.5:
                # Spark (feu) — friction, rub-gated, inchangé.
                agent["energy"] -= 2.0
                self.items.append({"x": agent["x"], "y": agent["y"], "z": 0, "type": "Spark", "ttl": 3})
                agent["last_spoken"] = [99.0, 99.0, 99.0, 99.0]

            do_grab = float(logits[24]) if len(logits) > 24 else 0.0
            if force_grab:  # ε-greedy : force le geste de collecte (EDR 019)
                do_grab = 1.0

            # Enregistrer l'action prise pour le crédit d'action du policy gradient (EDR 020).
            agent["_pg"] = {"move": int(action), "grab": 1 if do_grab > 0 else 0,
                            "rub": 1 if do_rub > 0 else 0}

            # 6. Grab (Inventory mechanics)
            if do_grab > 0:
                nearby_items = [i for i in self.items if i["x"] == agent["x"] and i["y"] == agent["y"]]
                if nearby_items:
                    item = nearby_items[0]
                    if len(agent["inventory"]) < agent["inv_capacity"]:
                        agent["inventory"].append(item)
                        self.items.remove(item)
                        agent["energy"] -= 1.0
                        # A) Scaffold : prime de collecte d'un ingrédient de craft (annelé).
                        if is_craft_ingredient(self.item_physics(item)):
                            agent["energy"] += self.scaffold_grab * anneal(getattr(self, "current_era", 1), self.scaffold_eras)
                    else:
                        # LIFO Drop Policy : The last item added is dropped at the agent's feet
                        dropped_item = agent["inventory"].pop(-1)
                        dropped_item["x"] = agent["x"]
                        dropped_item["y"] = agent["y"]
                        dropped_item["z"] = agent.get("z", 0)
                        self.items.append(dropped_item)
                        
                        agent["inventory"].append(item)
                        self.items.remove(item)
                        
                        agent["energy"] -= 2.0  # Moins pénalisant qu'un blocage, mais coûteux en énergie
                        logger.emit("INVENTORY_DROP", {"agent_id": agent["id"], "policy": "LIFO"}) 
                        agent["last_env_surprise"] = 0.5

            # Biology
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e_prebio"] = agent["energy"]           # EDR099 : avant biologie
            self._resolve_biology(agent, action, logits)
            if getattr(self.config, "trace_energy_sinks", False):
                agent["_e_postbio"] = agent["energy"]          # EDR099 : apres biologie, avant mouvement
            
            # Movement (2D: actions 0-3 = N,S,E,W; 3D: actions 4-5 = Up,Down)
            ax, ay, az = int(agent["x"]), int(agent["y"]), int(agent.get("z", 0))
            nx, ny, nz = ax, ay, az
            if action == 0: ny -= 1
            elif action == 1: ny += 1
            elif action == 2: nx += 1
            elif action == 3: nx -= 1
            elif action == 4 and self.use_3d: nz += 1  # Up
            elif action == 5 and self.use_3d: nz -= 1  # Down
            
            # Check bounds and geometry for target position
            nx, ny, nz = int(nx), int(ny), int(nz)
            in_bounds = (0 <= nx < self.size and 0 <= ny < self.size and 0 <= nz < self.dim_z)
            z_layer = int(nz)
            if action < 6 and in_bounds and self.geometry[z_layer, ny, nx] == 0:
                agent["x"], agent["y"], agent["z"] = nx, ny, nz
            elif action < 6:
                agent["energy"] -= 2.0
                
            self.pheromone_map[z_layer, int(agent["y"]), int(agent["x"])] += 1.0
            if getattr(self.config, "trace_energy_sinks", False):
                _e0 = agent.get("_e0", agent["energy"])
                _eb = agent.get("_e_brain", _e0)
                _ep = agent.get("_e_prebio", _eb)
                _epb = agent.get("_e_postbio", _ep)
                ph = agent.setdefault("_e_phases", {"brain": 0.0, "action": 0.0, "biologie": 0.0, "mouvement": 0.0})
                ph["brain"] += _e0 - _eb                       # cout brain_cost
                ph["action"] += _eb - _ep                      # throw + signal + divers (loop2 avant biologie)
                ph["biologie"] += _ep - _epb                   # metab+terrain+carry (peut etre <0 si forage)
                ph["mouvement"] += _epb - agent["energy"]      # penalite mouvement bloque (elif action < 6)

            # Survive / Reproduce
            if getattr(self, 'is_night', False):
                agent["confort"] = max(0.0, agent.get("confort", 50.0) - 1.0)
            else:
                agent["confort"] = min(100.0, agent.get("confort", 50.0) + 0.5)
                
            if agent["energy"] > 80.0 and agent.get("confort", 50.0) > 80.0:
                agent["hp"] = min(100.0 + agent["model"].phenotype_hp_bonus, agent["hp"] + 1.0)
            elif agent["energy"] < 20.0 or agent.get("confort", 50.0) < 20.0:
                agent["hp"] -= 1.0

            if agent["energy"] > 0 and agent["hp"] > 0:
                if agent["energy"] >= self.config.agent.energy_max and not self.benchmark_mode:
                    agent["energy"] = 50.0
                    child_model = agent["model"].clone()
                    child_model.mutate()
                    new_agents.append((child_model, agent["x"], agent["y"], 50.0))
                survivors.append(agent)
            else:
                logger.emit("AGENT_DEATH", {
                    "id": agent["id"], 
                    "age": agent["age"], 
                    "energy": agent["energy"],
                    "total_dreams": agent.get("total_dreams", 0),
                    "total_reflexes": agent.get("total_reflexes", 0),
                    "preys_eaten": agent.get("preys_eaten", 0)
                })
                # Emit structuré pour KuzuDB
                logger.emit("AGENT_LIFESPAN", {
                    "id": agent["id"],
                    "era": getattr(self, "current_era", 0),
                    "score": float(agent["energy"] + agent.get("preys_eaten", 0) * 10.0),
                    "energy": float(agent["energy"]),
                    "total_dreams": int(agent.get("total_dreams", 0)),
                    "total_reflexes": int(agent.get("total_reflexes", 0))
                })
                self.dead_agents.append(agent)
                
        # Pression RÉFÉRENTIELLE (EDR 045) : bonus si un agent proche de l'apex émet un token
        # PARTAGÉ par ses voisins proches -> sélectionne une convention « token = Mammouth ».
        if self.referential_scale > 0 and getattr(self.config, "active_exp_variable", "NONE") == "LANGUAGE":
            r = max(1, self.hear_radius)
            mammoth_pos = [(p["x"], p["y"]) for p in self.preys
                           if (self.config.preys.get(p["type"]) and self.config.preys.get(p["type"]).hp >= 50)]
            if mammoth_pos:
                for a in self.agents:
                    ls = a.get("last_spoken", [0.0] * 4)
                    if not any(abs(v) > 0.01 for v in ls):
                        continue
                    if not any(abs(a["x"] - mx) + abs(a["y"] - my) <= r for mx, my in mammoth_pos):
                        continue
                    tok = int(np.argmax(ls))
                    agree = sum(1 for b in self.agents if b is not a
                                and abs(a["x"] - b["x"]) + abs(a["y"] - b["y"]) <= r
                                and any(abs(v) > 0.01 for v in b.get("last_spoken", [0.0] * 4))
                                and int(np.argmax(b["last_spoken"])) == tok)
                    a["energy"] += self.referential_scale * agree

        # Incitation du LOCUTEUR (EDR 050) : mémoriser qui a signalé (adjacent) près de chaque
        # Mammouth -> prime à la mise à mort (réciprocité). Annoncer une vraie opportunité paie.
        if self.speaker_reward > 0:
            for p in self.preys:
                cfg = self.config.preys.get(p["type"])
                if not (cfg and p["type"] == "Mammouth"):
                    continue
                sig = p.setdefault("signalers", set())
                for a in self.agents:
                    ls = a.get("last_spoken", [0.0] * 4)
                    if any(abs(v) > 0.01 for v in ls) and abs(a["x"] - p["x"]) + abs(a["y"] - p["y"]) <= 1:
                        sig.add(a["id"])

        # Sélection ALIGNÉE (EDR 055) : prime la DISTINCTION référentielle par agent. On accumule
        # par agent l'histogramme des tokens près du Mammouth vs près du Leurre, et on récompense
        # la distance de variation totale entre les deux (tokens distincts par référent). Token
        # constant -> distinction 0 -> 0 prime (anti-piège 045). Comble l'angle mort de life_score.
        if self.align_selection > 0:
            mam = [p for p in self.preys if p["type"] == "Mammouth"]
            leu = [p for p in self.preys if p["type"] == "Leurre"]
            for a in self.agents:
                ls = a.get("last_spoken", [0.0] * 4)
                if any(abs(v) > 0.01 for v in ls):
                    tok = int(np.argmax(ls))
                    if any(abs(a["x"] - p["x"]) + abs(a["y"] - p["y"]) <= 1 for p in mam):
                        a.setdefault("_ref_m", [0, 0, 0, 0])[tok] += 1
                    elif any(abs(a["x"] - p["x"]) + abs(a["y"] - p["y"]) <= 1 for p in leu):
                        a.setdefault("_ref_l", [0, 0, 0, 0])[tok] += 1
                m = np.array(a.get("_ref_m", [0, 0, 0, 0]), dtype=np.float32)
                l = np.array(a.get("_ref_l", [0, 0, 0, 0]), dtype=np.float32)
                if m.sum() >= 1 and l.sum() >= 1:
                    distinction = 0.5 * np.abs(m / m.sum() - l / l.sum()).sum()   # TV distance [0,1]
                    a["energy"] += self.align_selection * distinction
                    a["_ref_distinction"] = float(distinction)   # EDR 056 : entre dans la fitness (HoF)

        # Suivi du token d'apex (EDR 063) : histogramme des tokens émis adjacent à un Mammouth ->
        # token dominant `_apex_token` (4 = silence). Clé de la spéciation par comportement (langage).
        if self.track_apex_token:
            mam = [p for p in self.preys if p["type"] == "Mammouth"]
            for a in self.agents:
                ls = a.get("last_spoken", [0.0] * 4)
                if any(abs(v) > 0.01 for v in ls) and any(abs(a["x"] - p["x"]) + abs(a["y"] - p["y"]) <= 1 for p in mam):
                    a.setdefault("_apex_hist", [0, 0, 0, 0])[int(np.argmax(ls))] += 1
                h = a.get("_apex_hist")
                a["_apex_token"] = int(np.argmax(h)) if h and sum(h) > 0 else 4

        # RL: Compute policy gradient
        new_energies = np.array([a["energy"] for a in self.agents], dtype=np.float32)
        # Récompense = gain d'énergie (extrinsèque) + curiosité (intrinsèque, World Model).
        # La curiosité pousse à explorer les états surprenants (ex. tenir un nouvel objet
        # après un grab) -> sortie du plateau "manger 5 proies" (EDR 014).
        curiosity = np.array([a["model"].surprise for a in self.agents], dtype=np.float32)
        # Nouveauté count-based : configs d'inventaire rares -> précurseurs du craft.
        novelty = np.zeros(len(self.agents), dtype=np.float32)
        for i, a in enumerate(self.agents):
            sig = state_signature(a["inventory"])
            self.novelty_counts[sig] = self.novelty_counts.get(sig, 0) + 1
            novelty[i] = novelty_bonus(self.novelty_counts[sig], self.novelty_scale)
        rewards = (new_energies - old_energies) + self.curiosity_scale * curiosity + novelty
        # Actions prises ce tick (crédit d'action, EDR 020), alignées sur self.agents.
        actions_batch = [a.get("_pg", {"move": -1, "grab": 0, "rub": 0}) for a in self.agents]
        batch_model.compute_policy_gradient(rewards, actions_batch)
                
        self.agents = survivors
        
        seeds_to_remove = []
        for item in self.items:
            if item.get("type") == "Seed":
                ttl = item.get("ttl", 100) - 1
                if ttl <= 0:
                    seeds_to_remove.append(item)
                    sx, sy = item["x"], item["y"]
                    if self.geometry[0, sy, sx] not in [1, 2, 3]: # not wall
                        self.geometry[0, sy, sx] = 4
                        self.trees.append((sx, sy))
                        self.tree_data.append({"is_fruit": True, "cooldown": np.random.randint(50, 150)})
                        for fy in range(max(0, sy-1), min(self.size, sy+2)):
                            for fx in range(max(0, sx-1), min(self.size, sx+2)):
                                if self.geometry[0, fy, fx] == 0:
                                    self.geometry[0, fy, fx] = 5
                        logger.emit("TREE_SPROUTED", {"x": sx, "y": sy})
                else:
                    item["ttl"] = ttl

        # Fire mechanics
        sparks_to_remove = []
        flammable_to_remove = []
        fires_to_add = []
        
        for item in self.items:
            if item.get("type") == "Spark":
                ignited = False
                for other in self.items:
                    if other is not item and other["x"] == item["x"] and other["y"] == item["y"]:
                        _, _, _, _, flam = self.item_physics(other)
                        if flam > 0.5:
                            sparks_to_remove.append(item)
                            if other not in flammable_to_remove:
                                flammable_to_remove.append(other)
                                ttl = 500 if other.get("type") == "Wood" else 50
                                fire_id = f"fire_{self.ticks}_{item['x']}_{item['y']}"
                                fires_to_add.append({"id": fire_id, "x": item["x"], "y": item["y"], "z": 0, "type": "Fire", "ttl": ttl})
                                
                                # Bonus for crafting fire intelligently
                                if other.get("type") == "Wood":
                                    for a in self.agents:
                                        if a["x"] == item["x"] and a["y"] == item["y"]:
                                            a["energy"] += 10.0 # Reward for advanced crafting!
                            ignited = True
                            break
                
                if not ignited:
                    ttl = item.get("ttl", 3) - 1
                    if ttl <= 0:
                        if item not in sparks_to_remove:
                            sparks_to_remove.append(item)
                    else:
                        item["ttl"] = ttl
        
        # Update Fires TTL
        fires_to_remove = []
        for item in self.items:
            if item.get("type") == "Fire":
                ttl = item.get("ttl", 50) - 1
                if ttl <= 0:
                    fires_to_remove.append(item)
                else:
                    item["ttl"] = ttl
                    # Fire gives heat / energy / confort to nearby agents!
                    gathered_agents = []
                    for a in self.agents:
                        if abs(a["x"] - item["x"]) <= 1 and abs(a["y"] - item["y"]) <= 1:
                            # Day or Night, Fire gives some energy (cooking/warmth)
                            a["energy"] = min(100.0, a["energy"] + 0.5)
                            
                            # Confort and gathering effects only apply at night!
                            if getattr(self, 'is_night', False):
                                a["confort"] = min(100.0, a.get("confort", 50.0) + 5.0)
                                gathered_agents.append(a)
                                if "id" in item and "id" in a:
                                    logger.emit("NEAR_FIRE", {"agent_id": a["id"], "fire_id": item["id"]})
                    
                    # EXP-9 : Social Gathering around fire at night
                    if getattr(self, 'is_night', False) and len(gathered_agents) >= 2:
                        agent_ids = [a["id"] for a in gathered_agents]
                        logger.emit("SOCIAL_GATHERING", {"fire_id": item.get("id", "unknown"), "agent_ids": agent_ids})
                        for a in gathered_agents:
                            a["energy"] = min(100.0, a["energy"] + 1.0) # Tribe cohesion bonus

        for s in sparks_to_remove + fires_to_remove + flammable_to_remove + seeds_to_remove:
            if s in self.items:
                self.items.remove(s)
        for f in fires_to_add:
            self.items.append(f)

        
        # Social Resolution
        if self.benchmark_mode:
            social_new_agents, hgt_new_agents = [], []      # cohorte FIXE (S2 spec §4) : pas de repro sociale/HGT
        else:
            social_new_agents = self._resolve_social()
            hgt_new_agents = self._apply_hgt_breeding()
            self._apply_surprise_hgt()
        
        self._add_offspring(new_agents + social_new_agents + hgt_new_agents)

    def _add_offspring(self, offspring):
        """Ajoute la descendance d'un tick en respectant la capacité de charge des agents
        (config.max_population). None = pas de cap (comportement historique). Le cap borne la
        population intra-épisode -> borne le coût O(N²) d'_apply_hgt_breeding (anti-runaway
        survie-longue, post-EDR090)."""
        cap = getattr(self.config, "max_population", None)
        for (g, x, y, e) in offspring:
            if cap is not None and len(self.agents) >= cap:
                break
            self.add_agent(g, x=x, y=y, energy=e)

    def render(self):
        print(f"--- BIOSPHERE V14 TensorWorld | {len(self.agents)} AGENTS EN VIE | TICK: {self.ticks} ---")
        if not self.agents:
            print("EXTINCTION.")
            return
        # Simplified rendering
        print(f"Entities: {len(self.agents)} Agents, {len(self.preys)} Preys, {len(self.items)} Items")
