import { useQuery } from "@tanstack/react-query";
import { fetchPilotage, type Porte } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { PILOTAGE_POLL } from "../../lib/polling";
import { messageIndisponible, vscodeHref } from "../../lib/pilotage";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";
import { AveugleBanner } from "./AveugleBanner";

function Baseline({ p, racine }: { p: Porte; racine: string | null | undefined }) {
  const b = p.baseline;
  // `null` = non RECENSÉE par la table BASELINES de tools/pm/pilotage.py, jamais « la porte n'en a pas ».
  if (!b) return <span className="text-dim">non recensée (BASELINES)</span>;
  if (!b.existe) {
    return (
      <>
        <s>{b.chemin}</s> <span className="text-dim">(absent)</span>
      </>
    );
  }
  const href = vscodeHref(racine, b.chemin);
  return href ? (
    <a href={href} aria-label={`ouvrir ${b.chemin} dans VS Code`}>
      {b.chemin}
    </a>
  ) : (
    <>{b.chemin}</>
  );
}

/** Onglet Portes : l'inventaire des gardes du hook pre-commit, LU de `GET /api/pm/pilotage` — rien n'est exécuté. */
export function PilotagePortesView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.pilotage,
    queryFn: () => fetchPilotage(),
    ...PILOTAGE_POLL,
  });

  if (isLoading) return <Loading label="Chargement du pilotage…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — pilotage inconnu." />;

  const racine = data.repo_root;
  return (
    <div className="pilotage-view">
      <h2>Portes</h2>
      <p className="text-dim">
        Inventaire recomputé depuis le hook pre-commit, joint à check_gate_mutation.PORTES pour les mutations — aucune
        porte n'est exécutée d'ici.
      </p>
      <AveugleBanner lignes={data.aveugle} />
      {!data.portes ? (
        <Empty message={messageIndisponible(data.aveugle, "portes", "Portes")} />
      ) : (
        <>
          <p>{data.portes.length} porte(s) branchée(s) au hook.</p>
          <Panel>
            <div className="pilotage-defilement">
              <table className="runs-table" aria-label="Portes du hook pre-commit">
                <thead>
                  <tr>
                    <th>N°</th>
                    <th>Module</th>
                    <th>Titre</th>
                    <th>Témoins</th>
                    <th>Mutations</th>
                    <th>Baseline</th>
                    <th>Dette gelée</th>
                  </tr>
                </thead>
                <tbody>
                  {data.portes.map((p) => (
                    <tr key={p.num}>
                      <td>{p.num}</td>
                      <td>
                        <code>{p.module}</code>
                      </td>
                      <td>{p.titre ?? <span className="text-dim">non publié</span>}</td>
                      <td>
                        {p.temoins ? (
                          <ul className="pilotage-chemins">
                            {p.temoins.map((t) => (
                              <li key={t}>
                                <code>{t}</code>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-dim">non publiés</span>
                        )}
                      </td>
                      <td>
                        {p.mutations == null ? <span className="text-dim">non mutée (hors PORTES)</span> : p.mutations}
                      </td>
                      <td>
                        <Baseline p={p} racine={racine} />
                      </td>
                      <td>
                        {p.baseline?.dette == null ? <span className="text-dim">non comptée</span> : p.baseline.dette}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
