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
    
    # Récupérer l'évolution de l'entretien du feu
    try:
        results_fire = conn.execute("MATCH (f:Fire) WHERE f.max_ttl IS NOT NULL RETURN f.creation_tick, f.max_ttl ORDER BY f.creation_tick")
    except Exception as e:
        print(f"Erreur KuzuDB (Feu): {e}")
        return

    ticks_fire = []
    max_ttls = []

    while results_fire.has_next():
        row = results_fire.get_next()
        ticks_fire.append(float(row[0] or 0))
        max_ttls.append(float(row[1] or 0))

    # Récupérer l'évolution de la taille des tribus
    try:
        results_tribe = conn.execute("MATCH (t:Tribe) RETURN t.timestamp, t.size ORDER BY t.timestamp")
    except Exception as e:
        print(f"Erreur KuzuDB (Tribe): {e}")
        return

    ticks_tribe = []
    sizes = []

    while results_tribe.has_next():
        row = results_tribe.get_next()
        ticks_tribe.append(float(row[0] or 0))
        sizes.append(float(row[1] or 0))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=False)
    fig.suptitle("Émergence des Tribus et Maîtrise du Feu (EXP-9)", fontsize=16)

    # Graphe 1 : Durée de vie des feux (Fueling)
    if ticks_fire:
        ax1.scatter(ticks_fire, max_ttls, color='red', alpha=0.6, s=50)
        ax1.set_ylabel("TTL Maximum du Feu (Ticks)")
        ax1.set_title("Effort d'entretien du feu (Maîtrise du Feu)")
        ax1.grid(True, alpha=0.3)
    else:
        ax1.text(0.5, 0.5, "Aucun feu entretenu (FIRE_FUELED) enregistré", horizontalalignment='center', verticalalignment='center')

    # Graphe 2 : Taille des tribus (Regroupement)
    if ticks_tribe:
        # Lissage par moyenne glissante
        window = max(1, len(sizes) // 20)
        smoothed_sizes = [sum(sizes[max(0, i-window):i+1]) / len(sizes[max(0, i-window):i+1]) for i in range(len(sizes))]
        ax2.plot(ticks_tribe, smoothed_sizes, color='blue', linewidth=2, label="Taille Moyenne (Glissante)")
        ax2.scatter(ticks_tribe, sizes, color='lightblue', alpha=0.3, s=20, label="Rassemblements")
        ax2.set_xlabel("Ticks (Temps global)")
        ax2.set_ylabel("Nombre d'agents par Feu")
        ax2.set_title("Taille des Tribus (SOCIAL_GATHERING) la Nuit")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    else:
        ax2.text(0.5, 0.5, "Aucune tribu (SOCIAL_GATHERING) enregistrée", horizontalalignment='center', verticalalignment='center')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    os.makedirs("results", exist_ok=True)
    save_path = os.path.join("results", "tribe_evolution_plot.png")
    plt.savefig(save_path)
    print(f"Graphique tribal sauvegardé dans : {save_path}")
    # plt.show()

if __name__ == "__main__":
    main()
