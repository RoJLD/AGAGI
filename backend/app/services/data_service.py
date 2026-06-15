from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from ..schemas import (
    AcademyItem,
    AcademyPayload,
    Article,
    ExperimentDetail,
    ExperimentHistory,
    ExperimentSummary,
    GraphData,
    GraphEdge,
    GraphNode,
)


class ExperimentDataService:
    def __init__(self, results_path: Path):
        self.results_path = results_path

    def available_gates(self) -> list[str]:
        if not self.results_path.exists():
            return []

        gates = set()
        for path in self.results_path.glob("*_history.*"):
            if path.suffix.lower() in {".json", ".csv"}:
                gates.add(path.name.split("_history.")[0].upper())

        return sorted(gates)

    def _history_path(self, gate: str) -> Path:
        json_path = self.results_path / f"{gate.lower()}_history.json"
        csv_path = self.results_path / f"{gate.lower()}_history.csv"
        return json_path if json_path.exists() else csv_path

    def _topology_json_path(self, gate: str) -> Path:
        return self.results_path / f"{gate.lower()}_topology.json"

    def _topology_txt_path(self, gate: str) -> Path:
        return self.results_path / f"{gate.lower()}_topology.txt"

    def _dot_path(self, gate: str) -> Path:
        return self.results_path / f"{gate.lower()}_topology.dot"

    def _read_json(self, path: Path) -> Any:
        if not path.exists():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_history_csv(self, path: Path) -> ExperimentHistory:
        if not path.exists():
            raise FileNotFoundError(path)

        generations: list[int] = []
        fitness: list[float] = []
        accuracy: list[float] = []
        size: list[int] = []

        with path.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                generations.append(int(row["generation"]))
                fitness.append(float(row["fitness"]))
                accuracy.append(float(row["accuracy"]))
                if row.get("size") not in (None, ""):
                    size.append(int(row["size"]))

        return ExperimentHistory(
            generation=generations,
            fitness=fitness,
            accuracy=accuracy,
            size=size if size else None,
        )

    def _parse_graph_from_txt(self, path: Path) -> GraphData:
        if not path.exists():
            raise FileNotFoundError(path)

        content = path.read_text(encoding="utf-8")
        node_count = 0
        input_nodes: list[int] = []
        output_nodes: list[int] = []
        links: list[GraphEdge] = []

        for line in content.splitlines():
            if "Nombre de nœuds" in line:
                node_count = int(line.split(":", 1)[1].strip())
            elif line.strip().startswith("Entrées"):
                input_nodes = [int(token) for token in re.findall(r"\d+", line)]
            elif line.strip().startswith("Sorties"):
                output_nodes = [int(token) for token in re.findall(r"\d+", line)]
            elif "->" in line:
                match = re.search(r"(\d+)\s*->\s*(\d+)\s*:\s*([-+]?[0-9]*\.?[0-9]+)", line)
                if match:
                    links.append(
                        GraphEdge(
                            source=int(match.group(1)),
                            target=int(match.group(2)),
                            weight=float(match.group(3)),
                        )
                    )

        if node_count == 0:
            node_count = max([edge.target for edge in links] + [edge.source for edge in links]) + 1

        nodes: list[GraphNode] = []
        for node_id in range(node_count):
            if node_id in input_nodes:
                node_type = "input"
            elif node_id in output_nodes:
                node_type = "output"
            else:
                node_type = "hidden"
            nodes.append(GraphNode(id=node_id, label=f"N{node_id}", type=node_type))

        return GraphData(nodes=nodes, links=links)

    def _parse_graph_from_dot(self, path: Path) -> GraphData:
        if not path.exists():
            raise FileNotFoundError(path)

        nodes: dict[int, GraphNode] = {}
        links: list[GraphEdge] = []
        content = path.read_text(encoding="utf-8")

        for line in content.splitlines():
            node_match = re.match(r"^\s*(\d+)\s+\[label=\"([^\"]+)\"", line)
            if node_match:
                node_id = int(node_match.group(1))
                label = node_match.group(2)
                if label.startswith("I"):
                    node_type = "input"
                elif label.startswith("O"):
                    node_type = "output"
                else:
                    node_type = "hidden"
                nodes[node_id] = GraphNode(id=node_id, label=label, type=node_type)
                continue

            edge_match = re.match(r"^\s*(\d+)\s*->\s*(\d+)\s*\[label=\"([-+]?[0-9]*\.?[0-9]+)\"", line)
            if edge_match:
                links.append(
                    GraphEdge(
                        source=int(edge_match.group(1)),
                        target=int(edge_match.group(2)),
                        weight=float(edge_match.group(3)),
                    )
                )

        if not nodes:
            raise ValueError(f"Aucun nœud trouvé dans le fichier Graphviz : {path}")

        return GraphData(nodes=list(nodes.values()), links=links)

    def _load_graph_data(self, gate: str) -> GraphData | None:
        json_path = self._topology_json_path(gate)
        dot_path = self._dot_path(gate)
        txt_path = self._topology_txt_path(gate)

        if json_path.exists():
            return GraphData(**self._read_json(json_path))
        if dot_path.exists():
            return self._parse_graph_from_dot(dot_path)
        if txt_path.exists():
            return self._parse_graph_from_txt(txt_path)

        return None

    def _graph_metrics(self, graph: GraphData | None) -> dict[str, float | int]:
        if graph is None:
            return {
                "num_nodes": 0,
                "num_edges": 0,
                "input_nodes": 0,
                "hidden_nodes": 0,
                "output_nodes": 0,
                "density": 0.0,
                "sparsity": 1.0,
                "hidden_ratio": 0.0,
            }

        num_nodes = len(graph.nodes)
        num_edges = len(graph.links)
        input_nodes = sum(1 for node in graph.nodes if node.type == "input")
        output_nodes = sum(1 for node in graph.nodes if node.type == "output")
        hidden_nodes = sum(1 for node in graph.nodes if node.type == "hidden")

        max_edges = num_nodes * (num_nodes - 1) / 2 if num_nodes > 1 else 1
        density = min(num_edges / max_edges, 1.0)
        sparsity = 1.0 - density
        hidden_ratio = hidden_nodes / num_nodes if num_nodes else 0.0

        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "input_nodes": input_nodes,
            "hidden_nodes": hidden_nodes,
            "output_nodes": output_nodes,
            "density": density,
            "sparsity": sparsity,
            "hidden_ratio": hidden_ratio,
        }

    def _compactness(self, size: int) -> float:
        return 1.0 / (1.0 + max(size, 1))

    def _performance_stability(self, history: ExperimentHistory) -> float:
        if len(history.accuracy) < 2:
            return 1.0

        values = history.accuracy
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        stddev = variance ** 0.5
        span = max(values) - min(values)
        denominator = span if span > 1e-8 else max(1.0, abs(mean))
        normalized = min(1.0, stddev / denominator)
        return round(max(0.0, 1.0 - normalized), 4)

    def _topology_modularity(self, graph: GraphData | None) -> float:
        if graph is None or not graph.nodes:
            return 0.0

        adjacency: dict[int, set[int]] = {node.id: set() for node in graph.nodes}
        for link in graph.links:
            adjacency[link.source].add(link.target)
            adjacency[link.target].add(link.source)

        visited: set[int] = set()
        components = 0
        for node_id in adjacency:
            if node_id not in visited:
                components += 1
                stack = [node_id]
                visited.add(node_id)
                while stack:
                    current = stack.pop()
                    for neighbor in adjacency[current]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            stack.append(neighbor)

        modularity = components / max(1.0, len(graph.nodes) / 3.0)
        return round(min(1.0, modularity), 4)

    def _motif_density(self, graph: GraphData | None) -> float:
        if graph is None or not graph.nodes:
            return 0.0

        degree: dict[int, int] = {node.id: 0 for node in graph.nodes}
        for link in graph.links:
            degree[link.source] += 1
            degree[link.target] += 1

        branching_nodes = sum(1 for count in degree.values() if count >= 2)
        return round(branching_nodes / len(graph.nodes), 4)

    def _score_emergent_intelligence(self, accuracy: float, fitness: float, compactness: float, hidden_ratio: float, max_fitness: float) -> float:
        normalized_fitness = fitness / max_fitness if max_fitness else 0.0
        return round(
            accuracy * 0.45 + normalized_fitness * 0.25 + compactness * 0.2 + hidden_ratio * 0.1,
            4,
        )

    def _score_robustness(self, accuracy: float, stability: float, sparsity: float, modularity: float, motif_density: float, hidden_ratio: float) -> float:
        return round(
            accuracy * 0.25
            + stability * 0.25
            + modularity * 0.2
            + (1.0 - sparsity) * 0.15
            + motif_density * 0.15,
            4,
        )

    def list_experiments(self) -> list[ExperimentSummary]:
        gates = self.available_gates()
        histories: dict[str, ExperimentHistory] = {}
        graph_data: dict[str, GraphData | None] = {}

        for gate in gates:
            histories[gate] = self.get_history(gate)
            graph_data[gate] = self._load_graph_data(gate)

        max_fitness = max((history.fitness[-1] for history in histories.values()), default=1.0)
        max_size = max(
            (
                history.size[-1]
                if history.size
                else (len(graph_data[gate].nodes) + len(graph_data[gate].links) if graph_data[gate] else 1)
            )
            for gate, history in histories.items()
        )
        max_size = max(max_size, 1)

        experiments: list[ExperimentSummary] = []
        for gate in gates:
            history = histories[gate]
            graph = graph_data[gate]
            metrics = self._graph_metrics(graph)
            latest_size = history.size[-1] if history.size else metrics["num_nodes"] + metrics["num_edges"]
            compactness = self._compactness(latest_size)
            performance_stability = self._performance_stability(history)
            topology_modularity = self._topology_modularity(graph)
            motif_density = self._motif_density(graph)
            emergent_score = self._score_emergent_intelligence(
                history.accuracy[-1], history.fitness[-1], compactness, metrics["hidden_ratio"], max_fitness
            )
            robustness_score = self._score_robustness(
                history.accuracy[-1],
                performance_stability,
                metrics["sparsity"],
                topology_modularity,
                motif_density,
                metrics["hidden_ratio"],
            )

            experiments.append(
                ExperimentSummary(
                    gate=gate,
                    latest_fitness=history.fitness[-1],
                    latest_accuracy=history.accuracy[-1],
                    latest_size=latest_size,
                    num_nodes=metrics["num_nodes"],
                    num_edges=metrics["num_edges"],
                    sparsity=metrics["sparsity"],
                    hidden_ratio=metrics["hidden_ratio"],
                    modularity=topology_modularity,
                    motif_density=motif_density,
                    performance_stability=performance_stability,
                    emergent_score=emergent_score,
                    robustness_score=robustness_score,
                )
            )

        return experiments

    def get_history(self, gate: str) -> ExperimentHistory:
        path = self._history_path(gate)
        if not path.exists():
            raise FileNotFoundError(path)

        if path.suffix.lower() == ".json":
            return ExperimentHistory(**self._read_json(path))
        if path.suffix.lower() == ".csv":
            return self._read_history_csv(path)

        raise FileNotFoundError(path)

    def get_graph(self, gate: str) -> dict[str, Any]:
        json_path = self._topology_json_path(gate)
        dot_path = self._dot_path(gate)
        txt_path = self._topology_txt_path(gate)

        if json_path.exists():
            return self._read_json(json_path)
        if dot_path.exists():
            return self._parse_graph_from_dot(dot_path).model_dump()
        if txt_path.exists():
            return self._parse_graph_from_txt(txt_path).model_dump()

        raise FileNotFoundError(f"Topologie introuvable pour {gate}")

    def get_dot(self, gate: str) -> str:
        path = self._dot_path(gate)
        if not path.exists():
            raise FileNotFoundError(path)
        return path.read_text(encoding="utf-8")

    def get_detail(self, gate: str) -> ExperimentDetail:
        history = self.get_history(gate)
        graph = None
        metrics = None
        graph_data = self._load_graph_data(gate)

        try:
            graph = self.get_graph(gate)
            if graph_data is not None:
                graph_metrics = self._graph_metrics(graph_data)
                latest_size = history.size[-1] if history.size else graph_metrics["num_nodes"] + graph_metrics["num_edges"]
                compactness = self._compactness(latest_size)
                performance_stability = self._performance_stability(history)
                topology_modularity = self._topology_modularity(graph_data)
                motif_density = self._motif_density(graph_data)
                metrics = {
                    "num_nodes": graph_metrics["num_nodes"],
                    "num_edges": graph_metrics["num_edges"],
                    "input_nodes": graph_metrics["input_nodes"],
                    "hidden_nodes": graph_metrics["hidden_nodes"],
                    "output_nodes": graph_metrics["output_nodes"],
                    "density": graph_metrics["density"],
                    "sparsity": graph_metrics["sparsity"],
                    "hidden_ratio": graph_metrics["hidden_ratio"],
                    "compactness": compactness,
                    "modularity": topology_modularity,
                    "motif_density": motif_density,
                    "performance_stability": performance_stability,
                    "emergent_score": self._score_emergent_intelligence(
                        history.accuracy[-1], history.fitness[-1], compactness, graph_metrics["hidden_ratio"], max(1, history.fitness[-1])
                    ),
                    "robustness_score": self._score_robustness(
                        history.accuracy[-1],
                        performance_stability,
                        graph_metrics["sparsity"],
                        topology_modularity,
                        motif_density,
                        graph_metrics["hidden_ratio"],
                    ),
                }
        except FileNotFoundError:
            graph = None

        return ExperimentDetail(gate=gate, history=history, graph=graph, metrics=metrics)

    def _repo_root(self) -> Path:
        return self.results_path.parent

    def _load_edr_findings(self) -> list[dict]:
        for p in (
            self._repo_root() / "backend" / "app" / "edr_findings.json",
            self.results_path / "edr_findings.json",
        ):
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8")).get("findings", []) or []
                except Exception:  # noqa: BLE001
                    return []
        return []

    def _recent_edr_docs(self, limit: int = 6) -> list[tuple[int, str]]:
        d = self._repo_root() / "docs" / "EDR"
        out: list[tuple[int, str]] = []
        if d.is_dir():
            for p in d.glob("[0-9][0-9][0-9]_*.md"):
                m = re.match(r"^(\d{3})_(.+)\.md$", p.name)
                if m:
                    out.append((int(m.group(1)), m.group(2).replace("_", " ")))
        out.sort(key=lambda x: x[0], reverse=True)
        return out[:limit]

    def get_academy_data(self) -> AcademyPayload:
        """Academy dérivée des EDR (et non plus des portes logiques figées) :
        derniers EDR documentés = jalons ; findings curés = timeline narrée."""
        findings = self._load_edr_findings()
        recent = self._recent_edr_docs()

        version_history = [
            AcademyItem(title=f"EDR {num:03d}", description=title) for num, title in recent
        ] or [AcademyItem(title="AGIseed", description="Journal des décisions expérimentales (EDR).")]

        timeline: list[str] = []
        for f in sorted(findings, key=lambda x: x.get("edr", 0)):
            title = f.get("title", "")
            insight = (f.get("insight") or "").strip()
            if len(insight) > 180:
                insight = insight[:177] + "..."
            timeline.append(f"EDR {f.get('edr', '?')} — {title}" + (f" : {insight}" if insight else ""))
        if not timeline:
            timeline = ["Aucune découverte curée dans edr_findings.json."]

        learning_goals = [
            "Lire l'histoire du projet par ses décisions (EDR), pas par des versions figées.",
            "Distinguer un signal réel d'un bruit : multi-seed, puissance, taille d'effet (Commandement 15).",
            "Powerer avant de conclure ; valider ou revert, une variable à la fois.",
            "Relier chaque découverte du Sociologue à l'expérience (run) qui l'a produite.",
        ]
        return AcademyPayload(version_history=version_history, timeline=timeline, learning_goals=learning_goals)

    def stream_experiment_updates(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for gate in self.available_gates():
            history = self.get_history(gate)
            for i, generation in enumerate(history.generation):
                events.append(
                    {
                        "gate": gate,
                        "generation": generation,
                        "fitness": history.fitness[i],
                        "accuracy": history.accuracy[i],
                        "size": history.size[i] if history.size else None,
                    }
                )
        return events

    def get_articles(self) -> list[Article]:
        """Read articles directly from KuzuDB.
        Utilise l'instance partagée de l'AsyncLogger si disponible (puisque le backend tourne flatland_server dans le même processus).
        """
        import kuzu
        from src.graph_rag.async_logger import logger as async_logger
        
        db_path = "/app/data/kuzu_graph.db" if Path("/app/data/kuzu_graph.db").exists() else "data/kuzu_graph.db"
        
        try:
            # Tente de récupérer la DB partagée si le serveur Flatland tourne
            db = async_logger.get_db()
            if db is None:
                # Sinon ouvre en read-only
                db = kuzu.Database(db_path, read_only=True)
            
            conn = kuzu.Connection(db)
            query = "MATCH (a:Article) RETURN a.id, a.title, a.content, a.date ORDER BY a.date DESC"
            results = conn.execute(query)
            articles = []
            while results.has_next():
                a_id, title, content, date_str = results.get_next()
                articles.append(Article(
                    id=a_id,
                    title=title,
                    content=content,
                    date=date_str
                ))
            return articles
        except Exception as e:
            print(f"[get_articles] Erreur lecture KuzuDB: {e}")
            return []
        finally:
            if 'conn' in locals(): del conn
            if 'db' in locals() and db != async_logger.get_db(): del db
