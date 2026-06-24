import os
import kuzu
import json
import time
import uuid
import datetime

class Sociologist:
    def __init__(self, db_path=None):
        if db_path == "mock":
            return
        if db_path is None:
            # Assumes running from root
            db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kuzu_graph.db")
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        self._init_schema()
        
    def _init_schema(self):
        try:
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Article (id STRING, title STRING, content STRING, date STRING, PRIMARY KEY (id))")
        except Exception:
            pass
            
        try:
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS ANALYZES_BASELINE (FROM Article TO Experiment)")
        except Exception:
            pass
            
        try:
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS ANALYZES_INTERVENTION (FROM Article TO Experiment)")
        except Exception:
            pass

    def get_experiment_stats(self, version: str):
        query = f"""
        MATCH (e:Experiment {{name: '{version}'}})-[:YIELDED_RESULT]->(r:Result)
        RETURN AVG(r.max_score), AVG(r.mean_score), COUNT(r)
        """
        res = self.conn.execute(query)
        if res.has_next():
            row = res.get_next()
            return {
                "avg_max_score": row[0] or 0.0,
                "avg_mean_score": row[1] or 0.0,
                "runs_count": row[2] or 0
            }
        return {"avg_max_score": 0.0, "avg_mean_score": 0.0, "runs_count": 0}

    def generate_narrative(self, baseline: str, intervention: str, stats_base: dict, stats_inter: dict):
        diff_score = stats_inter["avg_max_score"] - stats_base["avg_max_score"]
        diff_percent = (diff_score / max(1, stats_base["avg_max_score"])) * 100 if stats_base["avg_max_score"] > 0 else 0
        
        narrative = f"### Rapport Analytique : {baseline} vs {intervention}\n\n"
        narrative += f"- **Baseline ({baseline})** : {stats_base['runs_count']} runs explorés. Score Max Moyen = {stats_base['avg_max_score']:.2f}.\n"
        narrative += f"- **Intervention ({intervention})** : {stats_inter['runs_count']} runs explorés. Score Max Moyen = {stats_inter['avg_max_score']:.2f}.\n\n"
        
        if diff_score > 0:
            narrative += f"🟢 **Conclusion Positive** : L'intervention a généré un progrès évolutif avec une hausse de **+{diff_percent:.2f}%** du score de survie max.\n"
            narrative += "L'architecture ou l'hyperparamètre ajouté apporte un avantage adaptatif clair."
        else:
            narrative += f"🔴 **Régression Temporaire ou Échec** : L'intervention a causé une baisse de **{diff_percent:.2f}%** du score de survie max.\n"
            narrative += "Selon la Loi du Sociologue (Commandement 15), si la complexité ajoutée n'a pas encore été assimilée par les mutations, c'est une régression temporaire normale. Si l'expérience est mature, il faut réévaluer la mécanique."
            
        # Optional: Call LLM if API key exists
        if os.getenv("OPENAI_API_KEY"):
            try:
                import openai
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Tu es l'IA Sociologue du projet AGIseed. Rédige un court rapport scientifique (1 paragraphe) très professionnel expliquant ce résultat évolutif. Pas de blabla, direct au but."},
                        {"role": "user", "content": f"Analyse ces données : {narrative}"}
                    ]
                )
                narrative += "\n\n**Synthèse IA :**\n" + response.choices[0].message.content
            except Exception as e:
                narrative += f"\n\n*(Erreur génération IA OpenAI: {e})*"
        elif os.getenv("GEMINI_API_KEY"):
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                model = genai.GenerativeModel('gemini-1.5-flash')
                prompt = "Tu es l'IA Sociologue du projet AGIseed. Rédige un court rapport scientifique (1 paragraphe) très professionnel expliquant ce résultat évolutif. Voici les données:\n" + narrative
                response = model.generate_content(prompt)
                narrative += "\n\n**Synthèse IA :**\n" + response.text
            except Exception as e:
                narrative += f"\n\n*(Erreur génération IA Gemini: {e})*"
                
        return narrative

    def publish_article(self, baseline: str, intervention: str):
        stats_base = self.get_experiment_stats(baseline)
        stats_inter = self.get_experiment_stats(intervention)
        
        if stats_base["runs_count"] == 0 or stats_inter["runs_count"] == 0:
            print(f"Erreur: Données insuffisantes. Runs Baseline: {stats_base['runs_count']}, Runs Intervention: {stats_inter['runs_count']}")
            return None
            
        content = self.generate_narrative(baseline, intervention, stats_base, stats_inter)
        
        article_id = str(uuid.uuid4())[:8]
        title = f"Étude de l'évolution : {intervention}"
        date_str = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")

        # Save to KuzuDB (schéma Article unifié sur `date`, cohérent avec async_logger/experiment_tracker)
        safe_content = content.replace("'", "\\'")
        query = f"""
        CREATE (a:Article {{id: '{article_id}', title: '{title}', content: '{safe_content}', date: '{date_str}'}})
        """
        self.conn.execute(query)
        
        # Link to experiments
        try:
            self.conn.execute(f"MATCH (a:Article {{id: '{article_id}'}}), (e:Experiment {{name: '{baseline}'}}) MERGE (a)-[:ANALYZES_BASELINE]->(e)")
        except Exception as e:
            print("Warning linking baseline:", e)
            
        try:
            self.conn.execute(f"MATCH (a:Article {{id: '{article_id}'}}), (e:Experiment {{name: '{intervention}'}}) MERGE (a)-[:ANALYZES_INTERVENTION]->(e)")
        except Exception as e:
            print("Warning linking intervention:", e)
            
        return article_id, content
