import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.graph_rag.sociologist import Sociologist

def main():
    parser = argparse.ArgumentParser(description="Run the Sociologist to compare two experiment versions.")
    parser.add_argument("--baseline", type=str, required=True, help="Baseline version (e.g. V15)")
    parser.add_argument("--intervention", type=str, required=True, help="Intervention version (e.g. V16)")
    args = parser.parse_args()

    soc = Sociologist()
    print(f"Analysant {args.baseline} vs {args.intervention}...")
    res = soc.publish_article(args.baseline, args.intervention)
    if res:
        print(f"\n--- Article Publié ({res[0]}) ---")
        print(res[1])
        print("-----------------------------------")
        
if __name__ == "__main__":
    main()
