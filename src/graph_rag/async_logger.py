import threading
import queue
import time
from typing import Dict, Any, Optional, Callable
import logging as log_module

log = log_module.getLogger(__name__)
log_module.basicConfig(level=log_module.INFO)

class AsyncLogger:
    """
    Logger asynchrone pour envoyer des événements (naissances, morts, actions sociales) 
    vers la mémoire KuzuDB (Lattice Memory) sans bloquer la boucle principale du monde.
    Commandement 4: Non-Bloquant (async insertion thread-safe).
    """
    def __init__(self, db_path: str = "data/kuzu_graph.db", adaptive_tuner_callback: Optional[Callable] = None):
        self.queue = queue.Queue()
        self.db_path = db_path
        self.adaptive_tuner_callback = adaptive_tuner_callback
        self._running = False
        self._thread = None
        self._events_processed = 0
        self._events_by_type: Dict[str, int] = {}
        self._error_count = 0
        self._last_latency_ms = 0.0
        self._current_run = None       # provenance : id du Run courant (RUN_START/RUN_END)
        self._shared_db = None

    def set_database(self, db):
        self._shared_db = db
        
    def get_db(self):
        """Expose la DB partagée pour que d'autres composants puissent l'utiliser."""
        if self._shared_db is not None:
            return self._shared_db
        return getattr(self, 'db', None)

    def metrics(self) -> Dict[str, Any]:
        """Snapshot d'observabilité (best-effort, lecture de compteurs in-process, non bloquant)."""
        return {
            "events_processed": self._events_processed,
            "events_by_type": dict(self._events_by_type),
            "error_count": self._error_count,
            "last_latency_ms": round(self._last_latency_ms, 3),
            "queue_size": self.queue.qsize(),
            "running": self._running,
            "db_connected": self.get_db() is not None,
        }

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        log.info("AsyncLogger started")
        
    def stop(self):
        # Wait until queue is empty
        while not self.queue.empty():
            import time
            time.sleep(0.5)
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
        log.info(f"AsyncLogger stopped. Events processed: {self._events_processed}")
            
    def emit(self, event_type: str, payload: Dict[str, Any]):
        """Émet un événement vers le logger asynchrone (non-bloquant)."""
        if not self._running:
            return
            
        self.queue.put({
            "type": event_type,
            "payload": payload,
            "timestamp": int(time.time() * 1000)
        })

    def emit_sync(self, event_type: str, payload: Dict[str, Any], timeout: float = 10.0) -> bool:
        """Émet un événement et BLOQUE jusqu'à ce qu'il soit traité (pour les commits critiques)."""
        if not self._running:
            return False
        
        done_event = threading.Event()
        self.queue.put({
            "type": event_type,
            "payload": payload,
            "timestamp": int(time.time() * 1000),
            "_done_event": done_event  # Signal de complétion
        })
        return done_event.wait(timeout=timeout)
        
    def _init_schema(self, db_conn):
        try:
            db_conn.execute("CREATE NODE TABLE SocialEncounter (id STRING, agent_a STRING, agent_b STRING, spoken_a STRING, spoken_b STRING, PRIMARY KEY (id))")
        except RuntimeError:
            pass
        
        try:
            db_conn.execute("CREATE NODE TABLE AgentThought (id STRING, agent_id STRING, action INT64, value_pred DOUBLE, surprise DOUBLE, inventory_size INT64, PRIMARY KEY (id))")
        except RuntimeError:
            pass

        try:
            db_conn.execute("CREATE NODE TABLE AgentLifespan (id STRING, agent_id STRING, era INT64, score DOUBLE, energy DOUBLE, total_dreams INT64, total_reflexes INT64, PRIMARY KEY (id))")
        except RuntimeError:
            pass

        try:
            db_conn.execute("CREATE NODE TABLE CognitiveSnapshot (id STRING, agent_id STRING, tick INT64, ntm_memory STRING, attention_mask STRING, w_connectome STRING, PRIMARY KEY (id))")
        except RuntimeError:
            pass

    def _worker(self, db_conn=None):
        """Thread asynchrone qui dépile les événements et les insère dans KuzuDB."""
        # Initialisation lazy de KuzuDB pour éviter les problèmes de threads
        max_retries = 5
        db_conn = None
        
        for i in range(max_retries):
            try:
                import kuzu
                if self._shared_db is not None:
                    self.db = self._shared_db
                elif not hasattr(self, 'db') or self.db is None:
                    self.db = kuzu.Database(self.db_path)
                
                db_conn = kuzu.Connection(self.db)
                self._init_schema(db_conn)
                log.info(f"AsyncLogger worker connected to KuzuDB (retry {i})")
                break
            except Exception as e:
                if i < max_retries - 1:
                    log.warning(f"AsyncLogger DB lock retry {i}: {e}")
                    time.sleep(1.0)
                else:
                    log.error(f"AsyncLogger failed to connect: {e}")
                    return
            
        while self._running or not self.queue.empty():
            try:
                event = self.queue.get(timeout=0.1)
                _t0 = time.time()
                self._process_event(event, db_conn)
                self._last_latency_ms = (time.time() - _t0) * 1000.0
                self.queue.task_done()
                self._events_processed += 1
                et = event.get("type", "?")
                self._events_by_type[et] = self._events_by_type.get(et, 0) + 1
            except queue.Empty:
                self._check_pending_article(db_conn)
                continue
            except Exception as e:
                log.error(f"[ERROR in AsyncLogger._worker] {e}", exc_info=True)
                
        if db_conn is not None:
            del db_conn
        if hasattr(self, 'db') and self.db is not None and self._shared_db is None:
            del self.db
        
        import gc
        gc.collect()
        log.info(f"KuzuDB connection released in worker. Processed {self._events_processed} events.")
                
    def _check_pending_article(self, conn):
        import os, json, uuid, datetime
        pending_path = "data/pending_article.json"
        if os.path.exists(pending_path):
            try:
                with open(pending_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                try:
                    conn.execute("CREATE NODE TABLE Article (id STRING, title STRING, content STRING, date STRING, PRIMARY KEY (id))")
                except RuntimeError:
                    pass
                
                art_id = f"art_{uuid.uuid4().hex[:8]}"
                ts = data.get("timestamp", time.time())
                date_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                
                safe_title = data["title"].replace("'", "\\'")
                safe_content = data["content"].replace("'", "\\'")
                
                conn.execute(f"CREATE (a:Article {{id: '{art_id}', title: '{safe_title}', content: '{safe_content}', date: '{date_str}'}})")
                log.info(f"Article inséré dans KuzuDB par AsyncLogger: {data['title']}")
                
                # Sync with the JSON sidecar for Dashboard accessibility
                try:
                    from src.graph_rag.experiment_tracker import ExperimentGraph
                    tracker = ExperimentGraph(db=self.get_db(), read_only=True)
                    tracker._sync_articles_to_json()
                except Exception as sync_e:
                    log.warning(f"Impossible de synchroniser l'article vers le JSON sidecar: {sync_e}")
                
                os.remove(pending_path)
            except Exception as e:
                log.error(f"Erreur lors de l'insertion de l'article en attente: {e}")
    def _process_event(self, event: Dict[str, Any], conn):
        """Traitement effectif de l'événement en base."""
        e_type = event["type"]
        payload = event["payload"]
        timestamp = event["timestamp"]
        
        
        if conn is None:
            # Mode fallback si pas de kuzu — log seulement
            log.debug(f"Event (no KuzuDB): {e_type} @ {timestamp}: {payload}")
            return
            
        # Insertion Kuzu générique via LogEvent
        try:
            import json
            import uuid
            event_id = str(uuid.uuid4())
            payload_str = json.dumps(payload).replace("'", "\\'")
            
            # Initialize LogEvent schema if it doesn't exist
            try:
                conn.execute("CREATE NODE TABLE LogEvent (id STRING, type STRING, timestamp DOUBLE, payload STRING, PRIMARY KEY (id))")
            except Exception:
                pass
                
            conn.execute(f"CREATE (e:LogEvent {{id: '{event_id}', type: '{e_type}', timestamp: {timestamp}, payload: '{payload_str}'}})")
            
            if e_type == "LANGUAGE_ALIGNMENT":
                event_id = f"lang_{timestamp}_{payload.get('a')}_{payload.get('b')}"
                item_type = payload.get("item", "unknown")
                vec = payload.get("vector", [0.0, 0.0, 0.0, 0.0])
                try:
                    conn.execute("CREATE NODE TABLE IF NOT EXISTS LanguageAlignment (id STRING, agent_a STRING, agent_b STRING, item_type STRING, v0 DOUBLE, v1 DOUBLE, v2 DOUBLE, v3 DOUBLE, PRIMARY KEY (id))")
                except Exception:
                    pass
                conn.execute(f"CREATE (l:LanguageAlignment {{id: '{event_id}', agent_a: '{payload.get('a')}', agent_b: '{payload.get('b')}', item_type: '{item_type}', v0: {vec[0]}, v1: {vec[1]}, v2: {vec[2]}, v3: {vec[3]}}})")
                
            elif e_type == "TREASURE_FOUND":
                log.info(f"TREASURE_FOUND: {payload.get('agent_id')}")
                
            elif e_type == "AGENT_THOUGHT":
                log.info(f"AGENT_THOUGHT: {payload}")
                event_id = f"tht_{timestamp}_{payload.get('agent_id')}"
                conn.execute(f"CREATE (t:AgentThought {{id: '{event_id}', agent_id: '{payload.get('agent_id')}', action: {payload.get('action', 0)}, value_pred: {payload.get('value_pred', 0.0)}, surprise: {payload.get('surprise', 0.0)}, inventory_size: {payload.get('inventory_size', 0)}}})")

            elif e_type == "AGENT_LIFESPAN":
                log.info(f"AGENT_LIFESPAN stored for {payload.get('id')}")
                event_id = f"life_{timestamp}_{payload.get('id')}"
                conn.execute(f"CREATE (l:AgentLifespan {{id: '{event_id}', agent_id: '{payload.get('id')}', era: {payload.get('era', 0)}, score: {payload.get('score', 0.0)}, energy: {payload.get('energy', 0.0)}, total_dreams: {payload.get('total_dreams', 0)}, total_reflexes: {payload.get('total_reflexes', 0)}}})")
                
            elif e_type == "NEAR_FIRE":
                agent_id = payload.get("agent_id")
                fire_id = payload.get("fire_id")
                # Ensure Fire exists
                conn.execute(f"MERGE (f:Fire {{id: '{fire_id}'}}) ON MATCH SET f.creation_tick = coalesce(f.creation_tick, {timestamp}) ON CREATE SET f.creation_tick = {timestamp}")
                # Ensure Agent exists
                conn.execute(f"MERGE (a:Agent {{id: '{agent_id}'}})")
                # Upsert NEAR_FIRE relationship
                conn.execute(f"MATCH (a:Agent {{id: '{agent_id}'}}), (f:Fire {{id: '{fire_id}'}}) MERGE (a)-[r:NEAR_FIRE]->(f) ON MATCH SET r.duration = r.duration + 1 ON CREATE SET r.duration = 1")
                
            elif e_type == "FIRE_FUELED":
                fire_id = payload.get("fire_id")
                new_ttl = payload.get("new_ttl")
                agent_id = payload.get("agent_id")
                log.info(f"FIRE_FUELED: Agent {agent_id} fueled Fire {fire_id} to {new_ttl} TTL")
                conn.execute(f"MERGE (f:Fire {{id: '{fire_id}'}}) ON MATCH SET f.max_ttl = {new_ttl} ON CREATE SET f.max_ttl = {new_ttl}, f.creation_tick = {timestamp}")
                
            elif e_type == "SOCIAL_GATHERING":
                fire_id = payload.get("fire_id")
                agent_ids = payload.get("agent_ids", [])
                tribe_size = len(agent_ids)
                tribe_id = f"tribe_{timestamp}_{fire_id}"
                
                try:
                    conn.execute("CREATE NODE TABLE IF NOT EXISTS Tribe (id STRING, size INT64, timestamp DOUBLE, PRIMARY KEY (id))")
                    conn.execute("CREATE REL TABLE IF NOT EXISTS GATHERED_AROUND (FROM Tribe TO Fire)")
                    conn.execute("CREATE REL TABLE IF NOT EXISTS BELONGS_TO_TRIBE (FROM Agent TO Tribe)")
                except Exception:
                    pass
                
                conn.execute(f"CREATE (t:Tribe {{id: '{tribe_id}', size: {tribe_size}, timestamp: {timestamp}}})")
                conn.execute(f"MERGE (f:Fire {{id: '{fire_id}'}}) ON MATCH SET f.creation_tick = coalesce(f.creation_tick, {timestamp}) ON CREATE SET f.creation_tick = {timestamp}")
                conn.execute(f"MATCH (t:Tribe {{id: '{tribe_id}'}}), (f:Fire {{id: '{fire_id}'}}) MERGE (t)-[:GATHERED_AROUND]->(f)")
                
                for a_id in agent_ids:
                    conn.execute(f"MERGE (a:Agent {{id: '{a_id}'}})")
                    conn.execute(f"MATCH (a:Agent {{id: '{a_id}'}}), (t:Tribe {{id: '{tribe_id}'}}) MERGE (a)-[:BELONGS_TO_TRIBE]->(t)")
                                    
            elif e_type == "ERA_RESULT":
                # Log des résultats d'ère dans ExperimentGraph, sur le thread worker (pas de lock conflict)
                version = payload.get("version", "unknown")
                version = payload.get("version", "unknown")
                max_score = payload.get("max_score", 0.0)
                mean_score = payload.get("mean_score", 0.0)
                ticks = payload.get("ticks", 0)
                best_agent_id = payload.get("best_agent_id")
                result_id = f"{version}_res_{ticks}_{timestamp}"
                safe_version = version.replace("'", "\\'")
                try:
                    conn.execute("CREATE NODE TABLE IF NOT EXISTS Result (id STRING, max_score DOUBLE, mean_score DOUBLE, ticks INT64, PRIMARY KEY (id))")
                except Exception:
                    pass
                try:
                    conn.execute(f"MERGE (r:Result {{id: '{result_id}'}}) SET r.max_score = {max_score}, r.mean_score = {mean_score}, r.ticks = {ticks}")
                    conn.execute(f"MATCH (e:Experiment {{name: '{safe_version}'}}), (r:Result {{id: '{result_id}'}}) MERGE (e)-[:YIELDED_RESULT]->(r)")
                    
                    if best_agent_id and best_agent_id != "none":
                        try:
                            conn.execute("CREATE REL TABLE IF NOT EXISTS YIELDED_BEST_AGENT (FROM Result TO Agent)")
                        except Exception:
                            pass
                        conn.execute(f"MERGE (a:Agent {{id: '{best_agent_id}'}})")
                        conn.execute(f"MATCH (r:Result {{id: '{result_id}'}}), (a:Agent {{id: '{best_agent_id}'}}) MERGE (r)-[:YIELDED_BEST_AGENT]->(a)")
                        
                    log.info(f"ERA_RESULT logged: era={version}, max={max_score:.1f}, mean={mean_score:.1f}")
                except Exception as inner_e:
                    log.warning(f"ERA_RESULT partial write: {inner_e}")
                    
            elif e_type == "COGNITIVE_SNAPSHOT":
                agent_id = payload.get("agent_id", "unknown")
                tick = payload.get("tick", 0)
                event_id = f"snap_{timestamp}_{agent_id}_{tick}"
                
                # We expect the payload to contain stringified JSON arrays for ntm_memory, attention_mask, w_connectome
                ntm_str = payload.get("ntm_memory", "[]").replace("'", "\\'")
                att_str = payload.get("attention_mask", "[]").replace("'", "\\'")
                w_str = payload.get("w_connectome", "[]").replace("'", "\\'")
                
                try:
                    conn.execute("CREATE NODE TABLE IF NOT EXISTS CognitiveSnapshot (id STRING, agent_id STRING, tick INT64, ntm_memory STRING, attention_mask STRING, w_connectome STRING, PRIMARY KEY (id))")
                    conn.execute("CREATE REL TABLE IF NOT EXISTS TOOK_SNAPSHOT (FROM Agent TO CognitiveSnapshot)")
                except Exception:
                    pass
                    
                conn.execute(f"CREATE (c:CognitiveSnapshot {{id: '{event_id}', agent_id: '{agent_id}', tick: {tick}, ntm_memory: '{ntm_str}', attention_mask: '{att_str}', w_connectome: '{w_str}'}})")
                conn.execute(f"MERGE (a:Agent {{id: '{agent_id}'}})")
                conn.execute(f"MATCH (a:Agent {{id: '{agent_id}'}}), (c:CognitiveSnapshot {{id: '{event_id}'}}) MERGE (a)-[:TOOK_SNAPSHOT]->(c)")
                log.info(f"COGNITIVE_SNAPSHOT stored for {agent_id} at tick {tick}")
                    
            else:
                log.debug(f"Event {e_type}: {payload}")
                
        except Exception as e:
            self._error_count += 1
            log.error(f"KuzuDB insert error for {e_type}: {e}")
        finally:
            # Signal completion si emit_sync() attend
            done_event = event.get("_done_event")
            if done_event is not None:
                done_event.set()
            
# Instance globale (Singleton) — utilisée par le monde
logger = AsyncLogger()
