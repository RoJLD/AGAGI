import os
import csv
import matplotlib.pyplot as plt

def main():
    log_file = os.path.join("results", "metacognition_logs.csv")
    
    if not os.path.exists(log_file):
        print(f"Le fichier {log_file} est introuvable.")
        print("Assurez-vous que la simulation a tourné et généré des logs de métacognition.")
        return
        
    ticks = []
    eras = []
    mean_energy = []
    mean_surprise = []
    mean_doubt = []
    
    with open(log_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # On utilise un index global pour l'axe X (le temps continu)
            ticks.append(i)
            eras.append(int(row["era"]))
            mean_energy.append(float(row["mean_energy"]))
            mean_surprise.append(float(row["mean_surprise"]))
            mean_doubt.append(float(row["mean_doubt"]))
            
    if not ticks:
        print("Le fichier de log est vide.")
        return

    # Création de la figure
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle('Évolution de la Métacognition AGIseed (Population Mamba)', fontsize=16)
    
    # Graphe 1 : Énergie Moyenne
    ax1.plot(ticks, mean_energy, label="Énergie Moyenne", color="green")
    ax1.set_ylabel("Énergie")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper left")
    
    # Graphe 2 : Surprise (Test-Time Compute déclencheur)
    ax2.plot(ticks, mean_surprise, label="Surprise Moyenne (Chocs)", color="orange")
    ax2.set_ylabel("Surprise [0 - 1]")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left")
    
    # Graphe 3 : Doute (Entropie de Shannon)
    ax3.plot(ticks, mean_doubt, label="Doute Moyen (Entropie Motrice)", color="purple")
    ax3.set_xlabel("Ticks d'observation (x10)")
    ax3.set_ylabel("Doute (Entropie) [0 - 1]")
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="upper left")
    
    # Mettre en évidence les changements d'ère
    current_era = eras[0]
    for i, era in enumerate(eras):
        if era != current_era:
            for ax in [ax1, ax2, ax3]:
                ax.axvline(x=i, color='gray', linestyle='--', alpha=0.3)
            current_era = era
            
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    save_path = os.path.join("results", "metacognition_plot.png")
    plt.savefig(save_path)
    print(f"Graphique sauvegardé avec succès dans : {save_path}")
    plt.show()

if __name__ == "__main__":
    main()
