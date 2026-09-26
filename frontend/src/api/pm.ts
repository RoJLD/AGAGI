import { apiFetch } from "./client";
import type { components } from "./schema";

/** Types GÉNÉRÉS depuis `backend/app/schemas.py` (`make api-types`) — jamais recopiés à la main. */
export type PilotageV1 = components["schemas"]["PilotageV1"];
export type Roadmap = components["schemas"]["Roadmap"];
export type RoadmapEntree = components["schemas"]["RoadmapEntree"];
export type Porte = components["schemas"]["Porte"];
export type Charge = components["schemas"]["Charge"];

/** Timeout du recalcul `?frais=1`. Mesuré le 2026-09-24 : `snapshot()` coûte 15,6-18,1 s (spec §3.2), or `apiFetch`
 *  coupe à 10 s par défaut — le seul chemin qui paie encore ce coût expirerait par construction. Marge sur le
 *  majorant. */
export const FRAIS_TIMEOUT_MS = 40_000;

/** Le poll sert le `BOARD.json` du tick PM (jamais un recalcul) ; `frais` force un recalcul en mémoire côté
 *  backend. Chemins LITTÉRAUX, premier argument direct d'`apiFetch` : la seule forme que la porte de parité
 *  (`tools/parity_check.py`, `_FE_CALL`) compte comme consommation de la route. */
export function fetchPilotage(frais = false): Promise<PilotageV1> {
  if (frais) return apiFetch<PilotageV1>("/api/pm/pilotage?frais=1", { timeoutMs: FRAIS_TIMEOUT_MS });
  return apiFetch<PilotageV1>("/api/pm/pilotage");
}
