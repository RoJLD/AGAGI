from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class ForageLevel(BaseModel):
    metab: float
    p_reach: float
    p_cap: float
    income_t: float
    drain_t: float
    mean_captures: float
    mean_contacts: float
    mean_min_dist: float
    n_agents: float


class ForageFunnel(BaseModel):
    run_id: str
    name: str
    seed: int
    commit: str | None = None
    verdict: str
    levels: list[ForageLevel]


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


class RoadmapRang(BaseModel):
    rang: str
    p_items: list[str]
    statuts: list[str]


class RoadmapDirection(BaseModel):
    rangs: list[RoadmapRang]


class RoadmapClause(BaseModel):
    pred: str
    arg: str
    satisfaite: bool | None
    raison: str | None = None


class RoadmapHold(BaseModel):
    pred: str
    arg: str
    satisfaite: bool | None


class RoadmapChemin(BaseModel):
    rel: str
    existe: bool
    ligne: int | None = None


class RoadmapEntree(BaseModel):
    num: str
    nums: list[str]
    bloc: int
    priorite: str | None
    rang: str | None
    statut: str
    date: str | None
    titre: str
    lignes: list[int]
    clause: RoadmapClause | None = None
    holds: list[RoadmapHold] = []
    chemins: list[RoadmapChemin] = []
    chemins_non_captes: int
    raison_illisible: str | None = None


class RoadmapComptesPriorite(BaseModel):
    ouvertes: int
    closes: int
    perimees: int


class RoadmapComptes(BaseModel):
    par_priorite: dict[str, RoadmapComptesPriorite]
    blocs: int
    numeros: int
    illisibles: int


class Roadmap(BaseModel):
    direction: RoadmapDirection
    entrees: list[RoadmapEntree]
    comptes: RoadmapComptes
    portes_agi: dict[str, Any] | None = None


class PorteBaseline(BaseModel):
    chemin: str
    existe: bool
    dette: int | None = None


class Porte(BaseModel):
    num: str
    module: str
    titre: str | None = None
    temoins: list[str] | None = None
    mutations: int | None = None
    baseline: PorteBaseline | None = None


class Charge(BaseModel):
    sims_en_vol: int | None = None
    cpu_pct: float | None = None
    bails_vivants: list[str] | None = None
    flotte_age_s: float | None = None
    ratio_science_methodo: float | None = None
    fichiers: dict[str, int] | None = None
    fenetre: dict[str, Any] | None = None


class PilotageV1(BaseModel):
    """Enveloppe de `pilotage_v1`.

    ⚠️ `flotte` est `dict | None` SANS modèle strict : son contrat appartient au board (session PM) et
    évolue chez son propriétaire. Ce n'est PAS pour éviter un refus de clé neuve : en pydantic v2, un
    `response_model` IGNORE en silence une clé qu'il ne déclare pas (`model_config` par défaut n'est pas
    `extra="forbid"`), il ne lève pas dessus. Le vrai risque qu'un modèle nommé introduirait est un
    changement de TYPE d'un champ existant (le board rend un `str` là où le modèle attend un nombre, par
    exemple) : LÀ, pydantic lève une `ValidationError` à la sérialisation de la réponse, HORS du
    `try/except` du service. `roadmap`, `portes` et `charge` sont typés en modèles nommés parce que le
    frontend en a besoin (sinon `openapi-typescript` rend `{[key: string]: unknown}`, inutilisable sous
    `tsconfig strict`) — et ils COURENT ce risque : `charge` recopie des champs de `BOARD.json` et de
    `ROLES_COUNTS.json`, `roadmap.portes_agi` recopie `records_graph.json`, trois sources que
    `tools/pm/pilotage.py` ne possède pas (mesuré : un seul champ de type inattendu donnait un 500). Le
    service valide donc chaque bloc contre CE modèle, dans son filet, et un bloc refusé devient `null` plus
    une ligne `aveugle` qui le nomme (`backend/app/services/pilotage_service.py`).
    ⚠️ `schema` masque un attribut de `BaseModel` en pydantic v2 : d'où l'alias.
    """
    model_config = ConfigDict(populate_by_name=True)

    schema_: str = Field(alias="schema")
    generated_at: float
    repo_root: str | None = None
    aveugle: list[str]
    flotte: dict | None = None
    roadmap: Roadmap | None = None
    portes: list[Porte] | None = None
    charge: Charge | None = None


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
