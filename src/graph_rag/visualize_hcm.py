import os
import kuzu
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class HCMConfig:
    db_path: str = "data/experiment_graph.db"
    min_prob_threshold: float = 0.0

class KuzuHCMVisualizer:
    def __init__(self, config: HCMConfig):
        self.config = config
        self.db = kuzu.Database(self.config.db_path)
        self.conn = kuzu.Connection(self.db)

    def fetch_nodes(self) -> List[Tuple[str, str]]:
        query = "MATCH (c:CognitiveState) RETURN c.state_id, c.type"
        results = self.conn.execute(query).get_as_df()
        
        nodes = []
        for _, row in results.iterrows():
            nodes.append((str(row['c.state_id']), str(row['c.type'])))
        return nodes

    def fetch_edges(self) -> List[Tuple[str, str, float]]:
        query = "MATCH (a:CognitiveState)-[t:TRANSITIONS_TO]->(b:CognitiveState) RETURN a.state_id, b.state_id, t.prob"
        results = self.conn.execute(query).get_as_df()
        
        edges = []
        for _, row in results.iterrows():
            prob = float(row['t.prob'])
            if prob >= self.config.min_prob_threshold:
                edges.append((str(row['a.state_id']), str(row['b.state_id']), prob))
        return edges

    def generate_mermaid(self) -> str:
        nodes = self.fetch_nodes()
        edges = self.fetch_edges()

        mermaid_lines = ["graph TD"]
        
        # Add nodes
        for state_id, state_type in nodes:
            # Escape special characters for Mermaid
            clean_type = state_type.replace('"', "'")
            mermaid_lines.append(f'    {state_id}["{state_id}\\n{clean_type}"]')
            
        # Add edges
        for source, target, prob in edges:
            mermaid_lines.append(f'    {source} -->|{prob:.2f}| {target}')
            
        return "\n".join(mermaid_lines)

def main():
    config = HCMConfig()
    visualizer = KuzuHCMVisualizer(config)
    mermaid_str = visualizer.generate_mermaid()
    
    print("```mermaid")
    print(mermaid_str)
    print("```")

if __name__ == "__main__":
    main()
