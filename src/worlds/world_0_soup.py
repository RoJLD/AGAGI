import numpy as np
from src.seed_ai.mutation import apply_mutations, MutationConfig
from src.environments.physics import DynamicPhysicsRegistry

# V13: Imports matériels et physiques
try:
    from src.environments.crafting import ITEM_REGISTRY, attempt_combine
except ImportError:
    ITEM_REGISTRY = {}
    def attempt_combine(inventory): pass

try:
    from src.environments.projectiles import ProjectilePhysics
except ImportError:
    class ProjectilePhysics:
        @staticmethod
        def simulate(start_pos, aim_vec, force, weight, geometry, size, preys):
            return start_pos, None

class Biosphere3D:
    """
    V13: Mise à jour Matérielle.
    - Arbres, roches, branches (crafting items).
    - Inventaire dynamique via des sacs.
    - Physique avancée des projectiles.
    - Metacognition et écologie proportionnelle conservées de la V12.
    """
    def __init__(self, size: int = 10, num_altars: int = 3, prey_mode: str = "semi"):
        self.size = size
        self.num_altars = num_altars
        self.prey_mode = prey_mode
        self.physics_registry = DynamicPhysicsRegistry()
        self.pheromone_map = np.zeros((size, size, size), dtype=np.float32)
        self.geometry = np.zeros((size, size, size), dtype=int)
        
        # V13: Éléments générés
        self.items = []
        self._generate_geometry()
        self._generate_trees()
        
        self.agents = []
        self.mut_config = MutationConfig(
            weight_mutate_rate=0.8,
            weight_mutate_power=0.5,
            add_node_rate=0.1,
            add_connection_rate=0.3,
            prune_rate=0.1,
            weight_init_std=2.0
        )
        
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
                "z": np.random.randint(0, self.size),
                "bit_a": np.random.choice([-1.0, 1.0]),
                "bit_b": np.random.choice([-1.0, 1.0])
            })
            
        for _ in range(5):
            self._spawn_rocks()
            
        self.ticks = 0

    def _generate_geometry(self):
        for _ in range(10):
            x, y = np.random.randint(0, self.size, 2)
            for z in range(self.size):
                if np.random.rand() > 0.3:
                    self.geometry[z, y, x] = 1
        for _ in range(5):
            x, y = np.random.randint(0, self.size, 2)
            self.geometry[0, y, x] = 2
            if self.size > 1: self.geometry[1, y, x] = 2
        for _ in range(5):
            x, y = np.random.randint(0, self.size, 2)
            for z in range(2, self.size):
                self.geometry[z, y, x] = 3

    def _generate_trees(self):
        """V13: Génère des arbres (Tronc:4, Feuilles:5) et fait tomber des bâtons."""
        num_trees = max(1, self.size // 3)
        for _ in range(num_trees):
            tx = np.random.randint(1, self.size - 1)
            ty = np.random.randint(1, self.size - 1)
            # Tronc
            for z in range(0, min(3, self.size)):
                self.geometry[z, ty, tx] = 4
            # Feuilles
            leaf_z = min(3, self.size - 1)
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < self.size and 0 <= ny < self.size:
                        if dx != 0 or dy != 0:
                            self.geometry[leaf_z, ny, nx] = 5
                            
            # Bâtons (sticks)
            for _ in range(np.random.randint(1, 4)):
                stick_type = np.random.choice(["stick_short", "stick_long"])
                sx = np.clip(tx + np.random.choice([-1, 1]), 0, self.size-1)
                sy = np.clip(ty + np.random.choice([-1, 1]), 0, self.size-1)
                self.items.append({
                    "x": sx, "y": sy, "z": 0, "type": stick_type
                })

    def _spawn_rocks(self):
        """V13: Remplace les balles. Fait apparaitre des roches."""
        while True:
            bx = np.random.randint(0, self.size)
            by = np.random.randint(0, self.size)
            bz = np.random.randint(0, self.size)
            if self.geometry[bz, by, bx] == 0:
                rock_type = np.random.choice(["rock_small", "rock_medium", "rock_large"], p=[0.5, 0.3, 0.2])
                self.items.append({"x": bx, "y": by, "z": bz, "type": rock_type})
                break

    def _spawn_prey_instance(self, p_type):
        while True:
            x = np.random.randint(0, self.size)
            y = np.random.randint(0, self.size)
            
            if p_type == "flying":
                z = np.random.choice([self.size-1, self.size-2])
            else:
                z = np.random.choice([0, 1])
                
            if self.geometry[z, y, x] == 0:
                self.preys.append({"x": x, "y": y, "z": z, "type": p_type, "stunned": 0})
                break

    def _spawn_worms(self):
        for _ in range(5):
            wx = np.random.randint(0, self.size)
            wy = np.random.randint(0, self.size)
            self.worms.append({"x": wx, "y": wy, "z": 0})

    def _spawn_preys(self):
        types_needed = ["classic", "classic", "classic", "fast", "fast", "fast", "flying", "flying", "flying"]
        for t in types_needed:
            self._spawn_prey_instance(t)

    def _spawn_treasure(self):
        while True:
            self.treasure_x = np.random.randint(0, self.size)
            self.treasure_y = np.random.randint(0, self.size)
            self.treasure_z = np.random.randint(0, self.size)
            if self.geometry[self.treasure_z, self.treasure_y, self.treasure_x] == 0:
                break

    def add_agent(self, genome, x=None, y=None, z=None, energy=50.0):
        if x is None: x = np.random.randint(0, self.size)
        if y is None: y = np.random.randint(0, self.size)
        if z is None: z = np.random.randint(0, self.size)
        
        N = genome.num_nodes
        self.agents.append({
            "x": x, "y": y, "z": z,
            "genome": genome,
            "energy": energy,
            "age": 0,
            "preys_eaten": 0,
            "altars_solved": 0,
            "worms_eaten": 0,
            "H_prev": np.zeros((1, N)),
            "H_history": np.zeros((3, 1, N)),
            "H_potentials": np.zeros((1, N)),
            "last_action": -1,
            "last_spoken": 0,
            "last_surprise": 0.0,
            "throw_feedback": 0,
            "throw_feedback_ttl": 0,
            "status": {"jumping": False, "ducking": False},
            "inventory": [],  # V13: Liste d'IDs d'objets en chaîne de caractères
            "visited_positions": set()
        })

    def item_physics(self, item_type):
        if isinstance(item_type, dict):
            item_type = item_type.get("type", "unknown")
        if not isinstance(item_type, str):
            item_type = str(item_type)
        return self.physics_registry.get_properties(item_type)

    def _get_agent_observation(self, agent) -> np.ndarray:
        min_dist = 999999
        closest_prey = self.preys[0]
        for p in self.preys:
            dist = abs(p["x"]-agent["x"]) + abs(p["y"]-agent["y"]) + abs(p["z"]-agent["z"])
            if dist < min_dist:
                min_dist = dist
                closest_prey = p
                
        dn = max(0, agent["y"] - closest_prey["y"]) / self.size
        ds = max(0, closest_prey["y"] - agent["y"]) / self.size
        de = max(0, closest_prey["x"] - agent["x"]) / self.size
        dw = max(0, agent["x"] - closest_prey["x"]) / self.size
        dup = max(0, closest_prey["z"] - agent["z"]) / self.size
        ddown = max(0, agent["z"] - closest_prey["z"]) / self.size
        
        pheromone = min(1.0, self.pheromone_map[agent["z"], agent["y"], agent["x"]])
        abs_x = agent["x"] / self.size
        abs_y = agent["y"] / self.size
        abs_z = agent["z"] / self.size
        
        altar_active = 0.0
        bit_a = 0.0
        bit_b = 0.0
        
        for altar in self.altars:
            if altar["x"] == agent["x"] and altar["y"] == agent["y"] and altar["z"] == agent["z"]:
                altar_active = 1.0
                bit_a = altar["bit_a"]
                bit_b = altar["bit_b"]
                break
                
        adjacent_energy = 0.0
        nearest_word = 0
        for other in self.agents:
            if other is not agent and other["x"] == agent["x"] and other["y"] == agent["y"] and other["z"] == agent["z"]:
                adjacent_energy = max(adjacent_energy, other["energy"] / 100.0)
                nearest_word = other.get("last_spoken", 0)
                
        lidar = np.zeros(6, dtype=np.float32)
        ax, ay, az = agent["x"], agent["y"], agent["z"]
        lidar[0] = self.geometry[az, ay-1, ax] if ay > 0 else 1
        lidar[1] = self.geometry[az, ay+1, ax] if ay < self.size-1 else 1
        lidar[2] = self.geometry[az, ay, ax+1] if ax < self.size-1 else 1
        lidar[3] = self.geometry[az, ay, ax-1] if ax > 0 else 1
        lidar[4] = self.geometry[az+1, ay, ax] if az < self.size-1 else 1
        lidar[5] = self.geometry[az-1, ay, ax] if az > 0 else 1
        lidar /= 3.0
        
        is_flying = 1.0 if closest_prey["type"] == "flying" else 0.0
        is_stunned = 1.0 if closest_prey["stunned"] > 0 else 0.0
        in_hear = nearest_word / 10.0
        
        in_surprise = agent.get("last_surprise", 0.0)
        
        worm_nearby = 0.0
        for w in self.worms:
            if w["x"] == agent["x"] and w["y"] == agent["y"] and w["z"] == agent["z"]:
                worm_nearby = 1.0
                break
        
        in_throw_result = agent.get("throw_feedback", 0) / 1.0

        # --- V13: Observations Matérielles ---
        in_slot1_type = 0.0
        in_slot2_type = 0.0
        in_slot1_weight = 0.0
        
        def item_to_float(t_str):
            mapping = {"rock_small": 0.1, "rock_medium": 0.2, "rock_large": 0.3,
                       "stick_short": 0.4, "stick_long": 0.5, "bag_small": 0.6, "bag_large": 0.7}
            return mapping.get(t_str, (hash(t_str) % 10) / 10.0)

        if len(agent["inventory"]) > 0:
            item1 = agent["inventory"][0]
            in_slot1_type = item_to_float(item1)
            in_slot1_weight = float(ITEM_REGISTRY.get(item1).poids if item1 in ITEM_REGISTRY else 1.0)
            
        if len(agent["inventory"]) > 1:
            item2 = agent["inventory"][1]
            in_slot2_type = item_to_float(item2)

        in_nearby_item_type = 0.0
        in_nearby_item_count = 0.0
        
        nearby_items = [i for i in self.items if i["x"] == agent["x"] and i["y"] == agent["y"] and i["z"] == agent["z"]]
        if nearby_items:
            in_nearby_item_type = item_to_float(nearby_items[0]["type"])
            in_nearby_item_count = min(len(nearby_items), 10.0) / 10.0
        # -------------------------------------

        base_obs = [dn, ds, de, dw, dup, ddown, 1.0, pheromone, abs_x, abs_y, abs_z, altar_active, bit_a, bit_b, adjacent_energy, in_hear]
        meta_obs = [in_surprise, worm_nearby, in_throw_result]
        v13_obs = [in_slot1_type, in_slot2_type, in_slot1_weight, in_nearby_item_type, in_nearby_item_count]
        
        # NEW: Add observations to reach 45 inputs (match V14)
        # Terrain type one-hot encoding (4 values) - default to 0
        terrain_one_hot = [0.0]*4
        # Note: world_0_soup.py doesn't have terrain_type, so keeping as zeros
        v14_obs = terrain_one_hot + [agent["energy"] / 100.0]
        
        # Distance to treasure
        dist_to_treasure = (abs(agent["x"] - self.treasure_x) + abs(agent["y"] - self.treasure_y) + abs(agent["z"] - self.treasure_z)) / (self.size * 3)
        v14_obs += [dist_to_treasure, min(len(self.preys), 20) / 20.0, min(agent["age"], 1000) / 1000.0]
        
        # Item in hand properties (from inventory)
        in_hand_weight = in_hand_sharpness = in_hand_edibility = in_hand_friction = in_hand_flam = 0.0
        if len(agent["inventory"]) > 0:
            item = agent["inventory"][0]
            in_hand_weight, in_hand_sharpness, in_hand_edibility, in_hand_friction, in_hand_flam = self.item_physics(item)
        v14_obs += [in_hand_weight, in_hand_sharpness, in_hand_edibility, in_hand_friction, in_hand_flam]
        
        # Total: 16 (base) + 6 (lidar) + 2 (prey) + 3 (meta) + 5 (v13) + 13 (v14) = 45 entrées
        full_obs = base_obs + lidar.tolist() + [is_flying, is_stunned] + meta_obs + v13_obs + v14_obs
        return np.array([full_obs], dtype=np.float32)

    def _move_preys(self):
        for p in self.preys:
            if p["stunned"] > 0:
                p["stunned"] -= 1
                if p["z"] > 0 and self.geometry[p["z"]-1, p["y"], p["x"]] == 0:
                    p["z"] -= 1
                continue
                
            if self.prey_mode == "static":
                continue
                
            moves_this_tick = 1
            if p["type"] == "fast": moves_this_tick = 2
            elif p["type"] == "flying": moves_this_tick = 1 if np.random.rand() < 0.3 else 0
            elif p["type"] == "classic": moves_this_tick = 1 if np.random.rand() < 0.5 else 0
            
            for _ in range(moves_this_tick):
                action = -1
                if len(self.agents) > 0:
                    min_dist = 9999
                    closest = self.agents[0]
                    for a in self.agents:
                        d = abs(a["x"]-p["x"]) + abs(a["y"]-p["y"]) + abs(a["z"]-p["z"])
                        if d < min_dist:
                            min_dist = d
                            closest = a
                            
                    dx = closest["x"] - p["x"]
                    dy = closest["y"] - p["y"]
                    
                    if abs(dx) > abs(dy):
                        action = 3 if dx > 0 else 2
                    else:
                        action = 0 if dy > 0 else 1
                        
                nx, ny, nz = p["x"], p["y"], p["z"]
                if action == 0 and ny > 0: ny -= 1
                elif action == 1 and ny < self.size - 1: ny += 1
                elif action == 2 and nx > 0: nx -= 1
                elif action == 3 and nx < self.size - 1: nx += 1
                
                if self.geometry[nz, ny, nx] == 0:
                    p["x"], p["y"], p["z"] = nx, ny, nz

    def _can_move_to(self, x, y, z, agent):
        if x < 0 or x >= self.size or y < 0 or y >= self.size or z < 0 or z >= self.size:
            return False
        geo = self.geometry[z, y, x]
        if geo == 1 or geo == 4: return False  # Les troncs (4) sont bloquants
        if geo == 2 and not agent["status"]["jumping"]: return False
        if geo == 3 and not agent["status"]["ducking"]: return False
        return True

    def step(self):
        from src.seed_ai.rl_evolution import recurrent_forward
        from src.seed_ai.persistence import save_to_hall_of_fame, load_hall_of_fame
        
        self.ticks += 1
        self.pheromone_map *= 0.90
        self._move_preys()
        
        target_prey_count = max(9, len(self.agents) // 5)
        while len(self.preys) < target_prey_count:
            prey_type = np.random.choice(["classic", "classic", "fast", "flying"])
            self._spawn_prey_instance(prey_type)
        
        new_agents = []
        survivors = []
        
        for agent in self.agents:
            agent["age"] += 1
            
            if agent.get("throw_feedback_ttl", 0) > 0:
                agent["throw_feedback_ttl"] -= 1
            else:
                agent["throw_feedback"] = 0
            
            obs = self._get_agent_observation(agent)
            
            preds, H_prev, H_history, H_potentials, surprise = recurrent_forward(
                agent["genome"], obs, agent["H_prev"], agent["H_history"], agent["H_potentials"]
            )
            
            agent["H_prev"] = H_prev
            agent["H_history"] = H_history
            agent["H_potentials"] = H_potentials
            agent["last_surprise"] = surprise
            
            logits = preds[0].copy()
            if agent["last_action"] != -1:
                logits[agent["last_action"]] += 0.1
                
            action = int(np.argmax(logits[:6]))
            cognitive_out = float(logits[6])
            
            do_jump = float(logits[7]) > 0
            do_duck = float(logits[8]) > 0
            do_grab = float(logits[9]) > 0
            do_throw = float(logits[10]) > 0
            
            agent["out_share"] = float(logits[11])
            agent["out_accept"] = float(logits[12])
            agent["out_mate"] = float(logits[13])
            
            aim_vec = np.array([float(logits[14]), float(logits[15]), float(logits[16])])
            word = int(np.clip((logits[17] + 1) * 5, 0, 10))
            agent["last_spoken"] = word
            
            # V13: Nouvelles actions modulaires
            do_combine = float(logits[18]) > 0 if len(logits) > 18 else False
            do_drop = float(logits[19]) > 0 if len(logits) > 19 else False
            
            agent["last_action"] = action
            agent["energy"] -= 1.0
            
            # V13: Gestion de l'inventaire et du poids
            carry_weight = sum(ITEM_REGISTRY.get(i).poids if i in ITEM_REGISTRY else 1.0 for i in agent["inventory"]) if ITEM_REGISTRY else len(agent["inventory"]) * 0.5
            agent["energy"] -= carry_weight * 0.5
            
            inv_capacity = 2
            if "bag_large" in agent["inventory"]: inv_capacity = 10
            elif "bag_small" in agent["inventory"]: inv_capacity = 5
                
            agent["status"]["jumping"] = do_jump
            agent["status"]["ducking"] = do_duck
            if do_jump or do_duck: agent["energy"] -= 1.0
            
            nx, ny, nz = agent["x"], agent["y"], agent["z"]
            if action == 0: ny -= 1
            elif action == 1: ny += 1
            elif action == 2: nx += 1
            elif action == 3: nx -= 1
            elif action == 4: nz += 1
            elif action == 5: nz -= 1
            
            if self._can_move_to(nx, ny, nz, agent):
                if carry_weight == 0 or np.random.rand() > (carry_weight * 0.1):
                    agent["x"], agent["y"], agent["z"] = nx, ny, nz
            else:
                agent["energy"] -= 2.0
                
            self.pheromone_map[agent["z"], agent["y"], agent["x"]] += 1.0
            
            pos_key = (agent["x"], agent["y"], agent["z"])
            if pos_key not in agent["visited_positions"]:
                agent["visited_positions"].add(pos_key)
                agent["energy"] += 0.5
            
            # --- V13: ACTIONS MATÉRIELLES ---
            # 1. Grab
            if do_grab and len(agent["inventory"]) < inv_capacity:
                for itm in self.items:
                    if itm["x"] == agent["x"] and itm["y"] == agent["y"] and itm["z"] == agent["z"]:
                        agent["inventory"].append(itm["type"])
                        self.items.remove(itm)
                        agent["energy"] += 2.0
                        break
                        
            # 2. Drop
            if do_drop and len(agent["inventory"]) > 0:
                item_to_drop = agent["inventory"].pop(-1)
                self.items.append({"x": agent["x"], "y": agent["y"], "z": agent["z"], "type": item_to_drop})
                
            # 3. Combine
            if do_combine and len(agent["inventory"]) >= 2:
                try:
                    res = attempt_combine(agent["inventory"])
                    if res:
                        # Success: remove ingredients and add result
                        agent["inventory"].clear()
                        agent["inventory"].append(res)
                        agent["energy"] -= 1.0
                except Exception:
                    pass
                        
            # 4. Throw
            if do_throw and len(agent["inventory"]) > 0:
                item_type = agent["inventory"].pop(0)
                weight = ITEM_REGISTRY.get(item_type).poids if ITEM_REGISTRY and item_type in ITEM_REGISTRY else 1.0
                
                norm = np.linalg.norm(aim_vec)
                if norm > 0: aim_vec = aim_vec / norm
                else: aim_vec = np.array([0,1,0])
                    
                is_full = agent["energy"] > 50.0
                force = 10.0 if is_full else 5.0
                
                try:
                    end_pos, hit_prey = ProjectilePhysics.simulate(
                        start_pos=(agent["x"], agent["y"], agent["z"]),
                        aim_vec=aim_vec,
                        force=force,
                        weight=weight,
                        geometry=self.geometry,
                        size=self.size,
                        preys=self.preys
                    )
                except Exception:
                    end_pos, hit_prey = (agent["x"], agent["y"], agent["z"]), None
                    
                self.items.append({"x": end_pos[0], "y": end_pos[1], "z": end_pos[2], "type": item_type})
                
                if hit_prey:
                    hit_prey["stunned"] = 20
                    agent["throw_feedback"] = 1
                    agent["throw_feedback_ttl"] = 5
                else:
                    agent["throw_feedback"] = -1
                    agent["throw_feedback_ttl"] = 5
            # --------------------------------
            
            # Autels
            for altar in self.altars:
                if altar["x"] == agent["x"] and altar["y"] == agent["y"] and altar["z"] == agent["z"]:
                    expected_sign = -1.0 if altar["bit_a"] == altar["bit_b"] else 1.0
                    if cognitive_out * expected_sign > 0:
                        agent["energy"] += 20.0
                        agent["altars_solved"] += 1
                        for p in self.preys: p["stunned"] = 10
                        altar["x"] = np.random.randint(0, self.size)
                        altar["y"] = np.random.randint(0, self.size)
                        altar["z"] = np.random.randint(0, self.size)
                        altar["bit_a"] = np.random.choice([-1.0, 1.0])
                        altar["bit_b"] = np.random.choice([-1.0, 1.0])
                    break
            
            # Chasse
            eaten_prey = None
            for p in self.preys:
                if agent["x"] == p["x"] and agent["y"] == p["y"] and agent["z"] == p["z"]:
                    agent["energy"] += 50.0
                    agent["preys_eaten"] += 1
                    eaten_prey = p
                    break
            if eaten_prey:
                self.preys.remove(eaten_prey)
                self._spawn_prey_instance(eaten_prey["type"])
            
            if do_duck and agent["z"] == 0:
                eaten_worm = None
                for w in self.worms:
                    if w["x"] == agent["x"] and w["y"] == agent["y"] and w["z"] == agent["z"]:
                        agent["energy"] += 10.0
                        agent["worms_eaten"] = agent.get("worms_eaten", 0) + 1
                        eaten_worm = w
                        break
                if eaten_worm:
                    self.worms.remove(eaten_worm)
                    wx = np.random.randint(0, self.size)
                    wy = np.random.randint(0, self.size)
                    self.worms.append({"x": wx, "y": wy, "z": 0})
                
            if agent["x"] == self.treasure_x and agent["y"] == self.treasure_y and agent["z"] == self.treasure_z:
                if agent["out_accept"] > 0:
                    hof = load_hall_of_fame()
                    if len(hof) > 0:
                        best_genome = hof[0][1]
                        min_N = min(agent["genome"].num_nodes, best_genome.num_nodes)
                        agent["genome"].W[:min_N, :min_N] = 0.5 * agent["genome"].W[:min_N, :min_N] + 0.5 * best_genome.W[:min_N, :min_N]
                        agent["energy"] += 30.0
                    self._spawn_treasure()
                
            if agent["energy"] > 0:
                if agent["energy"] >= 100.0:
                    save_to_hall_of_fame(agent)
                    agent["energy"] = 50.0
                    child_genome = apply_mutations(agent["genome"], self.mut_config)
                    new_agents.append((child_genome, agent["x"], agent["y"], agent["z"], 50.0))
                survivors.append(agent)
            else:
                # Sur la mort, relachement des items
                if len(agent["inventory"]) > 0:
                    for it_type in agent["inventory"]:
                        self.items.append({"x": agent["x"], "y": agent["y"], "z": agent["z"], "type": it_type})
                save_to_hall_of_fame(agent)
                
        self.agents = survivors
        
        # --- PASSE DE RÉSOLUTION SOCIALE ---
        social_new_agents = []
        for i, a in enumerate(self.agents):
            for j, b in enumerate(self.agents):
                if i >= j: continue
                if a["x"] == b["x"] and a["y"] == b["y"] and a["z"] == b["z"]:
                    if a["out_accept"] > 0 and b["out_share"] > 0:
                        min_N = min(a["genome"].num_nodes, b["genome"].num_nodes)
                        W_B_mapped = np.zeros_like(a["genome"].W)
                        W_B_mapped[:min_N, :min_N] = b["genome"].W[:min_N, :min_N]
                        a["genome"].W = 0.9 * a["genome"].W + 0.1 * W_B_mapped
                        a["H_prev"][:, :min_N] = 0.5 * a["H_prev"][:, :min_N] + 0.5 * b["H_prev"][:, :min_N]
                    elif b["out_accept"] > 0 and a["out_share"] > 0:
                        min_N = min(b["genome"].num_nodes, a["genome"].num_nodes)
                        W_A_mapped = np.zeros_like(b["genome"].W)
                        W_A_mapped[:min_N, :min_N] = a["genome"].W[:min_N, :min_N]
                        b["genome"].W = 0.9 * b["genome"].W + 0.1 * W_A_mapped
                        b["H_prev"][:, :min_N] = 0.5 * b["H_prev"][:, :min_N] + 0.5 * a["H_prev"][:, :min_N]
                    
                    if a["out_mate"] > 0 and b["out_mate"] > 0 and a["energy"] > 30.0 and b["energy"] > 30.0:
                        a["energy"] -= 15.0
                        b["energy"] -= 15.0
                        import copy
                        rand_choice = np.random.rand()
                        if rand_choice < 0.33:
                            child_genome = copy.deepcopy(a["genome"])
                        elif rand_choice < 0.66:
                            child_genome = copy.deepcopy(b["genome"])
                        else:
                            child_genome = copy.deepcopy(a["genome"])
                            min_N = min(a["genome"].num_nodes, b["genome"].num_nodes)
                            child_genome.W[:min_N, :min_N] = (a["genome"].W[:min_N, :min_N] + b["genome"].W[:min_N, :min_N]) / 2.0
                            
                        child_genome = apply_mutations(child_genome, self.mut_config)
                        social_new_agents.append((child_genome, a["x"], a["y"], a["z"], 30.0))

        for (g, x, y, z, e) in new_agents + social_new_agents:
            self.add_agent(g, x, y, z, e)

    def render(self):
        print(f"--- BIOSPHERE V13 | {len(self.agents)} AGENTS EN VIE | TICK: {self.ticks} ---")
        if len(self.agents) == 0:
            print("EXTINCTION TOTALE.")
            return
            
        z_level = self.agents[0]["z"]
        print(f"Caméra Z={z_level} (M:Mur, m:Muret, P:Plafond, t:Tronc, l:Feuilles, r/s:Items, @:Classique, F:Rapide, V:Volante, *:Stun)")
        
        print("=" * (self.size * 2))
        for y in range(self.size):
            row = ""
            for x in range(self.size):
                geo = self.geometry[z_level, y, x]
                
                agent_here = [a for a in self.agents if a["x"] == x and a["y"] == y and a["z"] == z_level]
                item_here = [i for i in self.items if i["x"] == x and i["y"] == y and i["z"] == z_level]
                prey_here = [p for p in self.preys if p["x"] == x and p["y"] == y and p["z"] == z_level]
                
                if len(prey_here) > 0:
                    p = prey_here[0]
                    if p["stunned"] > 0: row += "* "
                    elif p["type"] == "fast": row += "F "
                    elif p["type"] == "flying": row += "V "
                    else: row += "@ "
                elif x == self.treasure_x and y == self.treasure_y and self.treasure_z == z_level:
                    row += "T "
                elif len(item_here) > 0:
                    t = item_here[0]["type"]
                    if "rock" in t: row += "r "
                    elif "stick" in t: row += "s "
                    else: row += "i "
                elif len(agent_here) > 0:
                    a = agent_here[0]
                    if len(a["inventory"]) > 0:
                        row += "8 "
                    else:
                        row += f"{len(agent_here)} "
                else:
                    is_altar = False
                    for altar in self.altars:
                        if altar["x"] == x and altar["y"] == y and altar["z"] == z_level:
                            is_altar = True
                            break
                    if is_altar:
                        row += "A "
                    elif geo == 1: row += "M "
                    elif geo == 2: row += "m "
                    elif geo == 3: row += "P "
                    elif geo == 4: row += "t "
                    elif geo == 5: row += "l "
                    else: row += ". "
            print(row)
        print("=" * (self.size * 2))
