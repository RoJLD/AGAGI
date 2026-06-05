import os
import json
import kuzu

class ExperimentGraph:
    def __init__(self, db_path="data/kuzu_graph.db", db=None, read_only=False):
        self.db_path = db_path
        
        if db is not None:
            self.db = db
            self.conn = kuzu.Connection(self.db)
            if not read_only:
                self._init_schema()
            return
            
        # Retry logic for OS file locks
        import time
        max_retries = 5
        for i in range(max_retries):
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                self.db = kuzu.Database(db_path, read_only=read_only)
                break
            except RuntimeError as e:
                if "Could not set lock on file" in str(e) and i < max_retries - 1:
                    print(f"[ExperimentGraph] KuzuDB locked, retrying {i+1}/{max_retries}...")
                    time.sleep(1.0)
                else:
                    raise
                    
        self.conn = kuzu.Connection(self.db)
        if not read_only:
            self._init_schema()

    def _init_schema(self):
        # Create Node Tables
        try:
            self.conn.execute("CREATE NODE TABLE Experiment(name STRING, description STRING, PRIMARY KEY (name))")
        except RuntimeError:
            pass
            
        try:
            self.conn.execute("CREATE NODE TABLE Capability(name STRING, type STRING, PRIMARY KEY (name))")
        except RuntimeError:
            pass

        try:
            self.conn.execute("CREATE NODE TABLE Result(id STRING, max_score DOUBLE, mean_score DOUBLE, ticks INT64, PRIMARY KEY (id))")
        except RuntimeError:
            pass

        try:
            self.conn.execute("CREATE NODE TABLE Interpretation(id STRING, text STRING, PRIMARY KEY (id))")
        except RuntimeError:
            pass

        # V12: Systeme Scientifique
        for table in [
            "CREATE NODE TABLE Experiment(id STRING, title STRING, start_time TIMESTAMP, parameters STRING, PRIMARY KEY (id))",
            "CREATE NODE TABLE Agent(id STRING, generation INT64, fitness DOUBLE, survival_time INT64, genome STRING, PRIMARY KEY (id))",
            "CREATE NODE TABLE Action(type STRING, count INT64, avg_reward DOUBLE, PRIMARY KEY (type))",
            "CREATE NODE TABLE Fact(id STRING, content STRING, confidence DOUBLE, PRIMARY KEY (id))",
            "CREATE NODE TABLE Hypothesis(id STRING, text STRING, status STRING, priority INT64, PRIMARY KEY (id))",
            "CREATE NODE TABLE Conclusion(id STRING, text STRING, impact STRING, PRIMARY KEY (id))",
            "CREATE NODE TABLE Opening(id STRING, text STRING, priority INT64, PRIMARY KEY (id))",
            "CREATE NODE TABLE CognitiveState (state_id STRING, type STRING, cluster_center STRING, PRIMARY KEY (state_id))",
            "CREATE NODE TABLE Fire (id STRING, creation_tick INT64, PRIMARY KEY (id))",
            "CREATE NODE TABLE Article (id STRING, title STRING, content STRING, date STRING, PRIMARY KEY (id))",
            "CREATE NODE TABLE Species (name STRING, base_inputs INT64, base_outputs INT64, base_nodes INT64, traits STRING, PRIMARY KEY (name))",
            "CREATE NODE TABLE WorldVersion (name STRING, type STRING, complexity INT64, PRIMARY KEY (name))",
            "CREATE NODE TABLE CognitiveSnapshot (id STRING, agent_id STRING, tick INT64, ntm_memory STRING, attention_mask STRING, w_connectome STRING, PRIMARY KEY (id))"
        ]:
            try:
                self.conn.execute(table)
            except RuntimeError:
                pass
        
        for rel in [
            "CREATE REL TABLE EXHIBITS (FROM Agent TO CognitiveState, frequency DOUBLE)",
            "CREATE REL TABLE TRANSITIONS_TO (FROM CognitiveState TO CognitiveState, prob DOUBLE)",
            "CREATE REL TABLE PRODUCES(FROM Experiment TO Agent)",
            "CREATE REL TABLE PARENT_OF(FROM Agent TO Agent)",
            "CREATE REL TABLE PERFORMED(FROM Agent TO Action, timestamp TIMESTAMP, success_rate DOUBLE)",
            "CREATE REL TABLE SUPPORTS(FROM Fact TO Hypothesis)",
            "CREATE REL TABLE CONTRADICTS(FROM Fact TO Hypothesis)",
            "CREATE REL TABLE VALIDATES(FROM Fact TO Conclusion)",
            "CREATE REL TABLE LEADS_TO(FROM Conclusion TO Opening)",
            "CREATE REL TABLE NEAR_FIRE(FROM Agent TO Fire, duration INT64)",
            "CREATE REL TABLE IN_TRIBE(FROM Agent TO Agent, fire_id STRING, score DOUBLE)",
            "CREATE REL TABLE BELONGS_TO_SPECIES (FROM Agent TO Species)",
            "CREATE REL TABLE RAN_IN_WORLD (FROM Experiment TO WorldVersion)",
            "CREATE REL TABLE TOOK_SNAPSHOT (FROM Agent TO CognitiveSnapshot)",
            "CREATE REL TABLE TIMELINE_NEXT (FROM Species TO Species)"
        ]:
            try:
                self.conn.execute(rel)
            except RuntimeError:
                pass

        # Create Rel Tables
        try:
            self.conn.execute("CREATE REL TABLE DERIVED_FROM(FROM Experiment TO Experiment)")
        except RuntimeError:
            pass

        try:
            self.conn.execute("CREATE REL TABLE HAS_CAPABILITY(FROM Experiment TO Capability)")
        except RuntimeError:
            pass

        try:
            self.conn.execute("CREATE REL TABLE YIELDED_RESULT(FROM Experiment TO Result)")
        except RuntimeError:
            pass

        try:
            self.conn.execute("CREATE REL TABLE HAS_INTERPRETATION(FROM Experiment TO Interpretation)")
        except RuntimeError:
            pass

        # V12: Relations scientifiques
        for rel in [
            "CREATE REL TABLE TESTS_HYPOTHESIS(FROM Experiment TO Hypothesis)",
            "CREATE REL TABLE PRODUCED_FACT(FROM Experiment TO Fact)",
            "CREATE REL TABLE LEADS_TO_CONCLUSION(FROM Fact TO Conclusion)",
            "CREATE REL TABLE OPENS_TO(FROM Conclusion TO Opening)",
            "CREATE REL TABLE SUPPORTS(FROM Fact TO Hypothesis)",
            "CREATE REL TABLE REFUTES(FROM Fact TO Hypothesis)",
        ]:
            try:
                self.conn.execute(rel)
            except RuntimeError:
                pass

    def log_experiment(self, version: str, parent_version: str, capabilities: list, description: str=""):
        # Upsert Experiment
        self.conn.execute(f"MERGE (e:Experiment {{name: '{version}'}}) SET e.description = '{description}'")
        
        # Link to parent if exists
        if parent_version:
            self.conn.execute(f"MERGE (p:Experiment {{name: '{parent_version}'}})")
            self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (p:Experiment {{name: '{parent_version}'}}) MERGE (e)-[:DERIVED_FROM]->(p)")

        # Link capabilities
        for cap in capabilities:
            self.conn.execute(f"MERGE (c:Capability {{name: '{cap}'}}) SET c.type = 'feature'")
            self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (c:Capability {{name: '{cap}'}}) MERGE (e)-[:HAS_CAPABILITY]->(c)")

    def log_world_and_species(self, version: str, world_type: str, species_name: str, traits: list):
        import json
        traits_json = json.dumps(traits).replace("'", "\\'")
        
        # Merge World
        self.conn.execute(f"MERGE (w:WorldVersion {{name: '{world_type}'}}) ON CREATE SET w.type = '{world_type}', w.complexity = 1")
        # Link Experiment to World
        self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (w:WorldVersion {{name: '{world_type}'}}) MERGE (e)-[:RAN_IN_WORLD]->(w)")
        
        # Merge Species
        self.conn.execute(f"MERGE (s:Species {{name: '{species_name}'}}) ON CREATE SET s.traits = '{traits_json}' ON MATCH SET s.traits = '{traits_json}'")
        # Ensure Agents produced by Experiment belong to Species
        # We assume the Experiment PRODUCED some agents, or we just link Experiment directly to Species
        # Actually, in strategy.py we look for: (e:Experiment)-[:PRODUCES]->(a:Agent)-[:BELONGS_TO_SPECIES]->(s:Species)
        # But PRODUCES and Agent aren't strictly always populated. Let's add a direct link from Experiment to Species for safety:
        self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (s:Species {{name: '{species_name}'}}) MERGE (e)-[:CREATED_SPECIES]->(s)")

    def log_hyperparameters(self, version: str, params: dict):
        import json
        hp_id = f"hp_{version}"
        params_str = json.dumps(params).replace("'", "\\'")
        
        try:
            self.conn.execute("CREATE NODE TABLE Hyperparameters(id STRING, params STRING, PRIMARY KEY (id))")
            self.conn.execute("CREATE REL TABLE HAS_HYPERPARAMETERS(FROM Experiment TO Hyperparameters)")
        except RuntimeError:
            pass
            
        self.conn.execute(f"MERGE (h:Hyperparameters {{id: '{hp_id}'}}) ON MATCH SET h.params = '{params_str}' ON CREATE SET h.params = '{params_str}'")
        self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (h:Hyperparameters {{id: '{hp_id}'}}) MERGE (e)-[:HAS_HYPERPARAMETERS]->(h)")

    def log_results(self, version: str, max_score: float, mean_score: float, ticks: int):
        result_id = f"{version}_res_{ticks}"
        self.conn.execute(f"MERGE (r:Result {{id: '{result_id}'}}) SET r.max_score = {max_score}, r.mean_score = {mean_score}, r.ticks = {ticks}")
        self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (r:Result {{id: '{result_id}'}}) MERGE (e)-[:YIELDED_RESULT]->(r)")

    def log_interpretation(self, version: str, text: str):
        # Allow safe alphanumeric ID
        import uuid
        interp_id = f"interp_{uuid.uuid4().hex[:8]}"
        safe_text = text.replace("'", "\\'")
        self.conn.execute(f"MERGE (i:Interpretation {{id: '{interp_id}'}}) SET i.text = '{safe_text}'")
        self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (i:Interpretation {{id: '{interp_id}'}}) MERGE (e)-[:HAS_INTERPRETATION]->(i)")

    def log_cognitive_state(self, version: str, state_id: str, state_type: str, cluster_center: str):
        safe_cluster = cluster_center.replace("'", "\\'")
        self.conn.execute(f"MERGE (c:CognitiveState {{state_id: '{state_id}'}}) SET c.type = '{state_type}', c.cluster_center = '{safe_cluster}'")
        self.conn.execute(f"MATCH (e:Experiment {{name: '{version}'}}), (c:CognitiveState {{state_id: '{state_id}'}}) MERGE (e)-[:OBSERVED_STATE]->(c)")

    def _articles_json_path(self) -> str:
        return os.path.join(os.path.dirname(self.db_path), "articles.json")

    def log_article(self, article_id: str, title: str, content: str, date: str):
        safe_title = title.replace("'", "\\'")
        safe_content = content.replace("'", "\\'")
        safe_date = date.replace("'", "\\'")
        self.conn.execute(f"MERGE (a:Article {{id: '{article_id}'}}) SET a.title = '{safe_title}', a.content = '{safe_content}', a.date = '{safe_date}'")
        # Sync to JSON sidecar for cross-platform reading (Docker backend)
        self._sync_articles_to_json()

    def _sync_articles_to_json(self):
        """Dump all articles from KuzuDB to a JSON file for Docker/cross-process reading."""
        try:
            articles = self.get_all_articles()
            json_path = self._articles_json_path()
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ExperimentGraph] Erreur sync articles JSON: {e}")

    def get_all_articles(self) -> list[dict]:
        res = self.conn.execute("MATCH (a:Article) RETURN a.id, a.title, a.content, a.date ORDER BY a.date DESC")
        articles = []
        while res.has_next():
            row = res.get_next()
            articles.append({
                "id": row[0],
                "title": row[1],
                "content": row[2],
                "date": row[3]
            })
        return articles
