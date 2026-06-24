export interface ExperimentHistory {
  generation: number[];
  fitness: number[];
  accuracy: number[];
  size?: number[];
}

export interface ExperimentMetrics {
  num_nodes: number;
  num_edges: number;
  input_nodes: number;
  hidden_nodes: number;
  output_nodes: number;
  density: number;
  sparsity: number;
  hidden_ratio: number;
  compactness: number;
  modularity: number;
  motif_density: number;
  performance_stability: number;
  emergent_score: number;
  robustness_score: number;
}

export interface ExperimentSummary {
  gate: string;
  latest_fitness: number;
  latest_accuracy: number;
  latest_size?: number;
  num_nodes?: number;
  num_edges?: number;
  sparsity?: number;
  hidden_ratio?: number;
  modularity?: number;
  motif_density?: number;
  performance_stability?: number;
  emergent_score?: number;
  robustness_score?: number;
}

export interface ExperimentDetail {
  gate: string;
  history: ExperimentHistory;
  graph: GraphData | null;
  metrics?: ExperimentMetrics | null;
}

export interface GraphNode {
  id: number;
  label: string;
  type: "input" | "hidden" | "output";
}

export interface GraphLink {
  source: number;
  target: number;
  weight: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface AcademyPayload {
  version_history: Array<{ title: string; description: string }>;
  timeline: string[];
  learning_goals: string[];
}

export interface Article {
  id: string;
  title: string;
  content: string;
  timestamp: string;
}

export interface ConditionSummary {
  name: string;
  n_seeds: number;
  seeds: number[];
  metrics: string[];
}

export interface DistributionSummary {
  name: string;
  vals: number[];
  n: number;
}

export interface ABGroup {
  name: string;
  mean: number;
  std: number;
  vals: number[];
  n: number;
}

export interface ABCompareResult {
  metric: string;
  a: ABGroup;
  b: ABGroup;
  t: number;
  d: number;
  significant: boolean;
  winner: string | null;
  underpowered: boolean;
  verdict_label: string;
  verdict_detail: string;
  t_thresh: number;
  d_thresh: number;
}

export interface RunConfig {
  script_name: string;
  world_type: string;
  base_seed: number;
  n_seeds: number;
  mutation_rate: number | null;
  variable_tested: string;
  tags: string[];
}

export interface RunPreset {
  id: string;
  label: string;
  config: RunConfig;
}

export type QueueStatus = "pending" | "running" | "done" | "error";

export interface QueuedRun {
  id: string;
  seed: number;
  status: QueueStatus;
}

export interface RunSummary {
  run_id: string;
  name: string;
  seed: number;
  commit?: string | null;
  metrics: string[];
}

export interface RunDetail {
  run_id: string;
  name: string;
  seed: number;
  commit?: string | null;
  data: Record<string, number | string>;
  links?: { edr: number[]; articles?: string[] };
}

/** {edr: [run_id, ...]} — runs liés à chaque EDR (badges du dashboard EDR). */
export type EdrLinks = Record<string, string[]>;

/** {run_id: [article_id, ...]} — articles Sociologue liés à chaque run. */
export type ArticleLinks = Record<string, string[]>;

/** Résultat d'un sweep : une métrique tracée le long d'un paramètre balayé (knob). */
export interface SweepResult {
  run_id: string;
  name: string;
  knob: string;
  x: number[];
  series: Record<string, number[]>;
  y_std?: Record<string, number[]>;
  seed: number;
  commit?: string | null;
}
