import type { QueuedRun, QueueStatus, RunConfig } from "../types";

/** État complet du pilote de file (remplace queue + queueRunning + launched). */
export interface QueueState {
  items: QueuedRun[];
  running: boolean;
  current: { id: string; sawRunning: boolean } | null;
}

/** Descripteur d'effet retourné par queueTick ; exécuté par le shell React. */
export type QueueEffect =
  | { type: "start"; id: string; seed: number }
  | { type: "complete" }
  | { type: "none" };

/** Construit n_seeds items pending (graine = base + i, id = script#seed). */
export function buildQueueItems(config: RunConfig): QueuedRun[] {
  return Array.from({ length: config.n_seeds }, (_, i) => ({
    id: `${config.script_name}#${config.base_seed + i}`,
    seed: config.base_seed + i,
    status: "pending" as QueueStatus,
  }));
}

/** Dédup par id : append les items dont l'id n'est pas déjà présent. */
export function mergeQueue(prev: QueuedRun[], incoming: QueuedRun[]): QueuedRun[] {
  return [...prev, ...incoming.filter((it) => !prev.some((p) => p.id === it.id))];
}

/** Met à jour le statut de l'item d'id `id` (retourne un nouveau tableau). */
function setStatus(items: QueuedRun[], id: string, status: QueueStatus): QueuedRun[] {
  return items.map((it) => (it.id === id ? { ...it, status } : it));
}

/**
 * Un pas du pilote séquentiel (le backend ne tient qu'un subprocess).
 * Pur : ne mute rien, retourne { state, effect }. Idempotent à signal constant.
 * La garde sawRunning évite de marquer "done" pendant la latence de polling
 * avant que la sandbox passe running.
 */
export function queueTick(
  state: QueueState,
  sandboxRunning: boolean,
): { state: QueueState; effect: QueueEffect } {
  if (!state.running) return { state, effect: { type: "none" } };

  if (state.current) {
    if (sandboxRunning) {
      if (state.current.sawRunning) return { state, effect: { type: "none" } };
      return {
        state: { ...state, current: { ...state.current, sawRunning: true } },
        effect: { type: "none" },
      };
    }
    if (state.current.sawRunning) {
      return {
        state: { ...state, items: setStatus(state.items, state.current.id, "done"), current: null },
        effect: { type: "none" },
      };
    }
    return { state, effect: { type: "none" } }; // latence : pas encore running, on patiente
  }

  if (sandboxRunning) return { state, effect: { type: "none" } }; // sandbox occupée : attendre
  const next = state.items.find((it) => it.status === "pending");
  if (!next) {
    return { state: { ...state, running: false }, effect: { type: "complete" } };
  }
  return {
    state: {
      ...state,
      items: setStatus(state.items, next.id, "running"),
      current: { id: next.id, sawRunning: false },
    },
    effect: { type: "start", id: next.id, seed: next.seed },
  };
}

/** Event async : l'item d'id `id` a échoué au démarrage -> error, clear current. */
export function applyStartFailure(state: QueueState, id: string): QueueState {
  return {
    ...state,
    items: setStatus(state.items, id, "error"),
    current: state.current?.id === id ? null : state.current,
  };
}

/** Bouton Stop : arrête la file et oublie le run courant. */
export function stopQueue(state: QueueState): QueueState {
  return { ...state, running: false, current: null };
}

/** Tally par statut (clés absentes pour les statuts absents ; consommé avec ?? 0). */
export function queueCounts(items: QueuedRun[]): Partial<Record<QueueStatus, number>> {
  return items.reduce<Partial<Record<QueueStatus, number>>>((acc, it) => {
    acc[it.status] = (acc[it.status] ?? 0) + 1;
    return acc;
  }, {});
}
