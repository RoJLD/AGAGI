/** Options react-query communes au sondage du statut sandbox (3 composants).
 *  Pas de polling en arrière-plan ; cache 2 s pour éviter le refetch au montage. */
export const STATUS_POLL = {
  refetchInterval: 3000,
  staleTime: 2000,
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
