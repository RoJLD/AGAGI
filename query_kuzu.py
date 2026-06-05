from src.graph_rag.experiment_tracker import ExperimentGraph

def main():
    tracker = ExperimentGraph()
    
    print("\n=== ASTKG: EXPERIMENTS & RESULTS ===")
    res = tracker.conn.execute("MATCH (e:Experiment)-[:YIELDED_RESULT]->(r:Result) RETURN e.name, r.max_score, r.mean_score, r.ticks ORDER BY r.ticks DESC LIMIT 5")
    while res.has_next():
        row = res.get_next()
        print(f"[{row[0]}] Ticks: {row[3]} | Max Score: {row[1]:.1f} | Mean Score: {row[2]:.1f}")
        
    print("\n=== ASTKG: CAPABILITIES ===")
    res = tracker.conn.execute("MATCH (e:Experiment)-[:HAS_CAPABILITY]->(c:Capability) RETURN e.name, c.name")
    while res.has_next():
        row = res.get_next()
        print(f"[{row[0]}] -> {row[1]}")
        
    print("\n=== ASTKG: INTERPRETATIONS ===")
    res = tracker.conn.execute("MATCH (e:Experiment)-[:HAS_INTERPRETATION]->(i:Interpretation) RETURN e.name, i.text")
    has_interp = False
    while res.has_next():
        has_interp = True
        row = res.get_next()
        print(f"[{row[0]}] {row[1]}")
        
    if not has_interp:
        print("Aucune interpretation consignée.")
        print("-> Ajout de l'interprétation initiale de la V7.5...")
        tracker.log_interpretation(
            version="V7.5_Genetics", 
            text="La V7.5 a introduit le Model Merging et l'accouplement. L'environnement est tres punitif (les 100 agents meurent en moins de 100 ticks). Cependant, des evenements de transfert horizontal sont documentes. Nous devons laisser la Seed AI tourner plus longtemps ou adoucir la penalite d'energie avant de complexifier vers la V8."
        )
        print("Interprétation ajoutée !")

if __name__ == "__main__":
    main()
