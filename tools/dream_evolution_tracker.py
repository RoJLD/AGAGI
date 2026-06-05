import kuzu
import matplotlib.pyplot as plt
import os

def main():
    db_path = "data/kuzu_graph.db"
    if not os.path.exists(db_path):
        print(f"La base {db_path} est introuvable.")
        return

    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    
    # Récupérer l'évolution des rêves (MCTS) et des scores au fil des ères
    try:
        results = conn.execute("MATCH (l:AgentLifespan) RETURN l.era, avg(l.total_dreams), avg(l.total_reflexes), avg(l.score) ORDER BY l.era")
    except Exception as e:
        print(f"Erreur KuzuDB: {e}")
        return

    eras = []
    avg_dreams = []
    avg_reflexes = []
    avg_scores = []

    while results.has_next():
        row = results.get_next()
        era = int(row[0])
        # Filtre les ères erronées
        if era <= 0:
            continue
        eras.append(era)
        avg_dreams.append(float(row[1] or 0))
        avg_reflexes.append(float(row[2] or 0))
        avg_scores.append(float(row[3] or 0))

    if not eras:
        print("Aucune donnée d'AgentLifespan trouvée.")
        return

    # Calcul du ratio MCTS / Reflexes
    dream_ratios = []
    for d, r in zip(avg_dreams, avg_reflexes):
        total = d + r
        dream_ratios.append((d / total * 100) if total > 0 else 0)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
    fig.suptitle('Montée en Compétence Métacognitive (MCTS) - EXP-8', fontsize=16)

    # Graphe 1 : Rêves moyens par agent par ère
    ax1.plot(eras, avg_dreams, marker='o', color='purple', linewidth=2)
    ax1.set_ylabel("Nombre moyen de rêves (MCTS)")
    ax1.set_title("Évolution absolue du Test-Time Compute (TTC)")
    ax1.grid(True, alpha=0.3)

    # Graphe 2 : Pourcentage du temps passé à rêver
    ax2.plot(eras, dream_ratios, marker='s', color='orange', linewidth=2)
    ax2.set_ylabel("% du temps en Rêve")
    ax2.set_title("Ratio MCTS vs Réflexes")
    ax2.grid(True, alpha=0.3)

    # Graphe 3 : Score moyen de l'ère
    ax3.plot(eras, avg_scores, marker='^', color='green', linewidth=2)
    ax3.set_xlabel("Ère")
    ax3.set_ylabel("Score (Fitness)")
    ax3.set_title("Évolution de la Performance Globale")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    os.makedirs("results", exist_ok=True)
    save_path = os.path.join("results", "dream_evolution_plot.png")
    plt.savefig(save_path)
    print(f"Graphique de métacognition sauvegardé dans : {save_path}")
    plt.show()

if __name__ == "__main__":
    main()
