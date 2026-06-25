/** Clés de query centralisées — évite les chaînes magiques et facilite l'invalidation. */
export const queryKeys = {
  experiments: {
    list: ["experiments"] as const,
    detail: (gate: string) => ["experiments", gate] as const,
    history: (gate: string) => ["experiments", gate, "history"] as const,
    graph: (gate: string) => ["experiments", gate, "graph"] as const,
  },
  academy: ["academy"] as const,
  edr: ["edr"] as const,
  timeline: ["timeline"] as const,
  sociologist: {
    articles: ["sociologist", "articles"] as const,
  },
  strategy: {
    tree: ["strategy", "tree"] as const,
  },
  sandbox: {
    status: ["sandbox", "status"] as const,
    logs: ["sandbox", "logs"] as const,
    telemetry: ["sandbox", "telemetry"] as const,
    article: ["sandbox", "article"] as const,
    state: ["sandbox", "state"] as const,
  },
  runs: {
    list: ["runs"] as const,
    conditions: ["runs", "conditions"] as const,
    detail: (runId: string) => ["runs", "detail", runId] as const,
    edrLinks: ["runs", "edr-links"] as const,
    articleLinks: ["runs", "article-links"] as const,
    compare: (a: string, b: string, metric: string) => ["runs", "compare", a, b, metric] as const,
    distributions: (metric: string) => ["runs", "distributions", metric] as const,
    notes: (runId: string) => ["runs", "notes", runId] as const,
  },
  health: {
    parity: ["health", "parity"] as const,
  },
  sweeps: ["sweeps"] as const,
  notes: ["notes"] as const,
} as const;
