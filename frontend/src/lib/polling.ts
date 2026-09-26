/** Options react-query communes au sondage du statut sandbox (3 composants).
 *  Pas de polling en arrière-plan ; cache 2 s pour éviter le refetch au montage. */
export const STATUS_POLL = {
  refetchInterval: 3000,
  staleTime: 2000,
  refetchIntervalInBackground: false,
} as const;

/** Options react-query du pilotage (3 vues, MÊME queryKey : une seule requête réseau). 30 s : la flotte servie
 *  est le BOARD.json du tick PM (20-30 min) et roadmap/portes/charge sont en cache 30 s côté backend — sonder plus
 *  vite ne rendrait rien de plus frais. Pas de sondage en arrière-plan. */
export const PILOTAGE_POLL = {
  refetchInterval: 30_000,
  staleTime: 5_000,
  refetchIntervalInBackground: false,
} as const;

/** Options react-query pour une query live de LiveDashboard, à intervalle donné.
 *  staleTime 0 (données fraîches à l'affichage) ; pas de polling en arrière-plan. */
export function livePoll(intervalMs: number) {
  return {
    refetchInterval: intervalMs,
    staleTime: 0,
    refetchIntervalInBackground: false,
  } as const;
}
