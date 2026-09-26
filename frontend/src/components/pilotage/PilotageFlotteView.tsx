import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchPilotage, type Charge, type PilotageV1 } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { PILOTAGE_POLL } from "../../lib/polling";
import {
  CECITE_FICHIERS,
  flotteAveugleSur,
  formatAge,
  lireFlotte,
  mesure,
  messageIndisponible,
  NON_MESURE,
  PEREMPTION_TABLEAU_S,
  type AlerteVue,
  type SessionVue,
} from "../../lib/pilotage";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";
import { Stat } from "../ui/Stat";
import { AveugleBanner } from "./AveugleBanner";

const pct = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

/** `Stat` refuse `null` (value: string | number, tsconfig strict) : la conversion se fait ICI, jamais dans la
 *  primitive — une valeur absente est « non mesuré », jamais 0 (spec §3.3). */
function Charges({ charge }: { charge: Charge }) {
  const bails = charge.bails_vivants;
  return (
    <div className="row mb-4">
      <Stat label="Simulations en vol" value={mesure(charge.sims_en_vol)} />
      <Stat label="CPU instantané (1 s)" value={mesure(charge.cpu_pct, (v) => `${pct.format(v)} %`)} />
      <Stat
        label="Bails vivants"
        value={bails == null ? NON_MESURE : bails.length ? `${bails.length} : ${bails.join(", ")}` : "0"}
      />
      <Stat label="Âge de la flotte" value={formatAge(charge.flotte_age_s)} />
    </div>
  );
}

function variante(gravite: string) {
  return gravite === "alerte" ? "danger" : gravite === "info" ? "warning" : "purple";
}

function Alerte({ a }: { a: AlerteVue }) {
  return (
    <li className="pilotage-alerte">
      <Badge variant={variante(a.gravite)}>
        {a.id} {a.gravite}
      </Badge>{" "}
      {a.message}
      {a.preuve !== undefined && (
        <details>
          <summary>preuve</summary>
          <pre className="pilotage-preuve">{JSON.stringify(a.preuve, null, 1)}</pre>
        </details>
      )}
    </li>
  );
}

const Dim = ({ children }: { children: string }) => <span className="text-dim">{children}</span>;

/** Une cellule de liste : « sans bulletin » (inconnue), la source aveugle côté tableau, « non publié » (clé
 *  absente), ou le contenu mesuré — « aucun » n'est écrit que pour une liste VUE vide. */
function liste(s: SessionVue, v: string[] | null, aveugle: string | null) {
  if (s.bulletin === false) return <Dim>sans bulletin</Dim>;
  if (aveugle) return <Dim>{aveugle}</Dim>;
  if (v === null) return <Dim>non publié</Dim>;
  return v.join(", ") || "aucun";
}

/** « 3 » ou « 3 (+2 écriture(s) Bash non nommée(s)) » — même forme que `board._fichiers_en_vol` (P2.118). */
function fichiers(s: SessionVue) {
  if (s.bulletin === false) return <Dim>sans bulletin</Dim>;
  if (s.fichiers === null) return <Dim>non publié</Dim>;
  const bash = s.bashEcritures ? ` (+${s.bashEcritures} écriture(s) Bash non nommée(s))` : "";
  return `${s.fichiers}${bash}`;
}

function Flotte({ data, perime }: { data: PilotageV1; perime: boolean }) {
  if (!data.flotte) return <Empty message={messageIndisponible(data.aveugle, "flotte", "Flotte")} />;
  const f = lireFlotte(data.flotte);
  const now = data.generated_at;
  const backlogAveugle = flotteAveugleSur(f, "backlog") ? "inconnu (backlog aveugle côté tableau)" : null;
  return (
    <>
      <h3>Sessions{perime ? " (à l'heure du tableau PÉRIMÉ)" : ""}</h3>
      {f.sessions === null ? (
        <Empty message="Le tableau ne publie pas de liste de sessions (clé absente ou illisible) — inconnu, pas vide." />
      ) : (
        <Panel className="mb-4">
          <div className="pilotage-defilement">
            <table className="runs-table" aria-label="Sessions vivantes au moment du tableau">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Branche</th>
                  <th>P-items revendiqués</th>
                  <th>P-items inférés</th>
                  <th>Fichiers en vol</th>
                  <th>Heartbeat</th>
                </tr>
              </thead>
              <tbody>
                {f.sessions.items.map((s, i) => (
                  <tr key={`${s.nom}-${i}`}>
                    <td>{s.nom}</td>
                    <td>{s.branche ?? <Dim>inconnue</Dim>}</td>
                    <td>{liste(s, s.claims, null)}</td>
                    <td>{liste(s, s.inferes, backlogAveugle)}</td>
                    <td>{fichiers(s)}</td>
                    <td>{s.heartbeatAt === null ? NON_MESURE : `il y a ${formatAge(now - s.heartbeatAt)}`}</td>
                  </tr>
                ))}
                {!f.sessions.items.length && (
                  <tr>
                    <td colSpan={6} className="text-dim">
                      {flotteAveugleSur(f, "registre natif")
                        ? "Sessions INCONNUES : le tableau est aveugle sur le registre natif — pas « aucune session »."
                        : "Aucune session vivante recensée par le tableau."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {f.sessions.illisibles > 0 && (
            <p className="text-dim">{f.sessions.illisibles} entrée(s) de session illisible(s), non affichée(s).</p>
          )}
          <p className="text-dim">{CECITE_FICHIERS}</p>
        </Panel>
      )}
      {f.mortes !== null && f.mortes.length > 0 && (
        <p className="text-dim">Sessions mortes écartées : {f.mortes.join(", ")}</p>
      )}

      <h3>Alertes</h3>
      {f.alertes === null ? (
        <Empty message="Le tableau ne publie pas de liste d'alertes (clé absente ou illisible) — inconnu, pas « 0 alerte »." />
      ) : (
        <>
          <ul className="pilotage-alertes">
            {f.alertes.items.map((a, i) => (
              <Alerte key={`${a.cle}-${i}`} a={a} />
            ))}
          </ul>
          {!f.alertes.items.length && (
            <p className="text-dim">
              {f.aveugle.length
                ? `Aucune alerte dans le tableau — qui est aveugle sur : ${f.aveugle.join(" · ")}. Une alerte de ces sources peut manquer.`
                : "Aucune alerte dans le tableau."}
            </p>
          )}
          {f.alertes.illisibles > 0 && (
            <p className="text-dim">{f.alertes.illisibles} alerte(s) illisible(s), non affichée(s).</p>
          )}
        </>
      )}
    </>
  );
}

/** Onglet Flotte : sessions, alertes et charge, LUES de `GET /api/pm/pilotage` (qui sert le `BOARD.json` du tick PM
 *  avec son âge). Aucun recalcul ici ; `?frais=1` est un clic explicite, refusé quand une simulation est en vol.
 *
 *  Le serveur ne garde pas un recalcul (seul le poll est en cache) : le résultat de `?frais=1` reste donc LOCAL à
 *  cette vue, affiché tant que sa flotte est plus récente que celle du sondage — jamais écrasé en silence par un
 *  tableau plus vieux au sondage suivant. */
export function PilotageFlotteView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.pilotage,
    queryFn: () => fetchPilotage(),
    ...PILOTAGE_POLL,
  });
  const frais = useMutation({ mutationFn: () => fetchPilotage(true) });

  if (isLoading) return <Loading label="Chargement du pilotage…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — pilotage inconnu." />;

  const genere = (p: PilotageV1 | undefined) => {
    const g = p?.flotte?.generated_at;
    return typeof g === "number" ? g : -Infinity;
  };
  const recalcul = frais.data && genere(frais.data) > genere(data) ? frais.data : null;
  const vue = recalcul ?? data;
  const refusFrais = (frais.data?.aveugle ?? []).filter((l) => l.startsWith("frais=1"));
  const sims = data.charge?.sims_en_vol;
  const simsEnVol = typeof sims === "number" && sims > 0;
  const age = vue.charge?.flotte_age_s;
  const perime = typeof age === "number" && age > PEREMPTION_TABLEAU_S;

  return (
    <div className="pilotage-view">
      <h2>Flotte</h2>
      <p className="text-dim">
        {recalcul
          ? `Recalculée à la demande le ${new Date(recalcul.generated_at * 1000).toLocaleString("fr-FR")} — le serveur ne la garde pas : le tableau du tick reprend la main dès qu'il est plus récent.`
          : "Servie depuis BOARD.json, écrit par le tick PM : sa fraîcheur est celle du tick, et son âge est affiché ci-dessous. Le sondage de 30 s ne la recalcule jamais."}
      </p>
      {perime && (
        <div className="aveugle-banner">
          <div role="status" className="aveugle-banner__bloc aveugle-banner__bloc--alerte">
            <strong>Tableau PÉRIMÉ : mesuré il y a {formatAge(age)}.</strong> Au-delà de{" "}
            {formatAge(PEREMPTION_TABLEAU_S)}, aucun tick n'a renouvelé le bail du PM : le rôle est vacant, et sessions
            et alertes décrivent CETTE heure-là.
          </div>
        </div>
      )}
      <AveugleBanner lignes={vue.aveugle} />
      {vue.charge ? (
        <Charges charge={vue.charge} />
      ) : (
        <Empty message={messageIndisponible(vue.aveugle, "charge", "Charge")} />
      )}
      <div className="row mb-4">
        <Button variant="ghost" size="sm" disabled={simsEnVol || frais.isPending} onClick={() => frais.mutate()}>
          Recalculer la flotte (≈ 20 s, charge la machine)
        </Button>
        {simsEnVol && (
          <span className="text-dim">
            Désactivé : {sims} simulation(s) en vol d'après le dernier tableau — un seul run lourd à la fois.
          </span>
        )}
        {frais.isPending && (
          <span role="status" className="text-dim">
            Recalcul en cours… les données affichées restent celles du dernier sondage, avec leur âge.
          </span>
        )}
        {refusFrais.map((l, i) => (
          <span key={i} role="status" className="text-dim">
            {l}
          </span>
        ))}
      </div>
      {frais.isError && <ErrorState error={frais.error} onRetry={simsEnVol ? undefined : () => frais.mutate()} />}
      <Flotte data={vue} perime={perime} />
    </div>
  );
}
