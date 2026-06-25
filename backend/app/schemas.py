from __future__ import annotations

from typing import Any

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


# --- Runs (instrument scientifique) — response_models : durcit le typage + précise le codegen TS ---
class RunSummary(BaseModel):
    run_id: str
    name: str
    seed: int
    commit: str | None = None
    metrics: list[str]


class RunLinks(BaseModel):
    edr: list[int] = []
    articles: list[str] = []


class RunDetail(BaseModel):
    run_id: str
    name: str
    seed: int
    commit: str | None = None
    data: dict[str, Any]
    links: RunLinks


class ConditionSummary(BaseModel):
    name: str
    n_seeds: int
    seeds: list[int]
    metrics: list[str]


class ABGroup(BaseModel):
    name: str
    mean: float
    std: float
    vals: list[float]
    n: int


class ABCompareResult(BaseModel):
    metric: str
    a: ABGroup
    b: ABGroup
    t: float
    d: float
    significant: bool
    winner: str | None = None
    underpowered: bool
    verdict_label: str
    verdict_detail: str
    t_thresh: float
    d_thresh: float


class DistributionSummary(BaseModel):
    name: str
    vals: list[float]
    n: int


class EnergyPhases(BaseModel):
    brain: float
    action: float
    biologie: float
    mouvement: float
    net: float
    n_agents: float
    bio_metab: float
    bio_terrain: float
    bio_carry: float
    bio_autres: float


class Decomposition(BaseModel):
    run_id: str
    name: str
    seed: int
    commit: str | None = None
    phases: EnergyPhases
    verdict: str
    bio_verdict: str


class RunNote(BaseModel):
    id: str
    text: str
    ts: str


class NoteCreate(BaseModel):
    text: str


class NoteFeedItem(BaseModel):
    run_id: str
    run_name: str
    id: str
    text: str
    ts: str


class SweepResult(BaseModel):
    """Un sweep : une métrique tracée le long d'un paramètre balayé (knob).
    x = valeurs du paramètre ; series[<metric>] = série Y de même longueur ;
    y_std[<metric>] = écart-type optionnel (bande de variance)."""
    run_id: str
    name: str
    knob: str
    x: list[float]
    series: dict[str, list[float]]
    y_std: dict[str, list[float]] | None = None
    seed: int
    commit: str | None = None
