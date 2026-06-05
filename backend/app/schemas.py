from __future__ import annotations

from pydantic import BaseModel


class GraphEdge(BaseModel):
    source: int
    target: int
    weight: float


class GraphNode(BaseModel):
    id: int
    label: str
    type: str


class GraphData(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphEdge]


class ExperimentMetrics(BaseModel):
    num_nodes: int
    num_edges: int
    input_nodes: int
    hidden_nodes: int
    output_nodes: int
    density: float
    sparsity: float
    hidden_ratio: float
    compactness: float
    modularity: float
    motif_density: float
    performance_stability: float
    emergent_score: float
    robustness_score: float


class ExperimentHistory(BaseModel):
    generation: list[int]
    fitness: list[float]
    accuracy: list[float]
    size: list[int] | None = None


class ExperimentSummary(BaseModel):
    gate: str
    latest_fitness: float
    latest_accuracy: float
    latest_size: int | None = None
    num_nodes: int | None = None
    num_edges: int | None = None
    sparsity: float | None = None
    hidden_ratio: float | None = None
    modularity: float | None = None
    motif_density: float | None = None
    performance_stability: float | None = None
    emergent_score: float | None = None
    robustness_score: float | None = None


class ExperimentDetail(BaseModel):
    gate: str
    history: ExperimentHistory
    graph: GraphData | None = None
    metrics: ExperimentMetrics | None = None


class Article(BaseModel):
    id: str
    title: str
    content: str
    date: str


class AcademyItem(BaseModel):
    title: str
    description: str


class AcademyPayload(BaseModel):
    version_history: list[AcademyItem]
    timeline: list[str]
    learning_goals: list[str]
