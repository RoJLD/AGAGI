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
} as const;
