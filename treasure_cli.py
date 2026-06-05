import argparse
from src.graph_rag.experiment_tracker import ExperimentGraph

def main():
    parser = argparse.ArgumentParser(description="AGIseed Treasure Box (CLI pour l'ASTKG KuzuDB)")
    subparsers = parser.add_subparsers(dest="command")

    # Commande: top
    subparsers.add_parser("top", help="Affiche les 5 meilleures Ères simulées.")
    
    # Commande: secrets
    subparsers.add_parser("secrets", help="Affiche tous les secrets d'évolution consignés.")

    # Commande: add-secret
    add_parser = subparsers.add_parser("add-secret", help="Consigne une nouvelle interprétation (Secret) pour une expérience.")
    add_parser.add_argument("version", type=str, help="La version de l'expérience (ex: V7.5_Genetics)")
    add_parser.add_argument("text", type=str, help="Le texte du secret/interprétation")

    args = parser.parse_args()

    # Si pas de commande, on affiche l'aide
    if not args.command:
        parser.print_help()
        return

    # KuzuDB Tracker
    try:
        tracker = ExperimentGraph()
    except Exception as e:
        print(f"Erreur de chargement du Graph (la simulation est peut-être en train de verrouiller la DB) : {e}")
        return

    if args.command == "top":
        print("\n🏆 === HALL OF FAME DES ÈRES ===")
        res = tracker.conn.execute("MATCH (e:Experiment)-[:YIELDED_RESULT]->(r:Result) RETURN e.name, r.max_score, r.mean_score, r.ticks ORDER BY r.ticks DESC LIMIT 5")
        while res.has_next():
            row = res.get_next()
            print(f"[{row[0]}] Survie: {row[3]} Ticks | Score Max: {row[1]:.1f} | Moyenne: {row[2]:.1f}")

    elif args.command == "secrets":
        print("\n📜 === SECRETS D'ÉVOLUTION CONSIGNÉS ===")
        res = tracker.conn.execute("MATCH (e:Experiment)-[:HAS_INTERPRETATION]->(i:Interpretation) RETURN e.name, i.text")
        has_secrets = False
        while res.has_next():
            has_secrets = True
            row = res.get_next()
            print(f"[{row[0]}] {row[1]}")
        if not has_secrets:
            print("Aucun secret consigné pour le moment. L'univers est encore jeune.")

    elif args.command == "add-secret":
        tracker.log_interpretation(args.version, args.text)
        print(f"✅ Secret ajouté avec succès à {args.version} !")

if __name__ == "__main__":
    main()
