import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchPilotage, type PilotageV1, type Roadmap, type RoadmapEntree } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { PILOTAGE_POLL } from "../../lib/polling";
import { BACKLOG_REL, mesure, messageIndisponible, vscodeHref } from "../../lib/pilotage";
import { Badge } from "../ui/Badge";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Field } from "../ui/Field";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";
import { Stat } from "../ui/Stat";
import { AveugleBanner } from "./AveugleBanner";

const STATUTS = ["ouverte", "close", "perimee", "illisible"] as const;
const LIBELLE_STATUT: Record<string, string> = {
  ouverte: "ouverte",
  close: "close",
  perimee: "périmée",
  illisible: "illisible",
};

/** « ouverte » n'est PAS un Badge plein : `--color-accent` et `--color-success` ont la même valeur dans les deux
 *  thèmes, donc teal et success ne se distinguaient que par le texte. Contour local, primitive inchangée. */
function StatutBadge({ statut }: { statut: string }) {
  if (statut === "ouverte") return <span className="badge pilotage-ouverte">ouverte</span>;
  const v =
    statut === "close" ? "success" : statut === "perimee" ? "warning" : statut === "illisible" ? "danger" : "purple";
  return <Badge variant={v}>{LIBELLE_STATUT[statut] ?? statut}</Badge>;
}

/** Badge d'une clause : `success` satisfaite / `warning` non / `purple` invérifiable (la primitive n'a pas de
 *  variante neutre, spec §3.3). La raison est du TEXTE visible, jamais un `title` (inatteignable au clavier). */
function ClauseBadge({ satisfaite }: { satisfaite: boolean | null }) {
  if (satisfaite === true) return <Badge variant="success">satisfaite</Badge>;
  if (satisfaite === false) return <Badge variant="warning">non satisfaite</Badge>;
  return <Badge variant="purple">invérifiable</Badge>;
}

function Lien({ href, label, children }: { href: string | null; label: string; children: string }) {
  if (!href) return <>{children}</>;
  return (
    <a href={href} aria-label={label}>
      {children}
    </a>
  );
}

function Chemins({ e, racine }: { e: RoadmapEntree; racine: string | null | undefined }) {
  if (!e.chemins.length && !e.chemins_non_captes) return <span className="text-dim">aucun</span>;
  return (
    <>
      <ul className="pilotage-chemins">
        {e.chemins.map((c) => (
          <li key={c.rel}>
            {c.existe ? (
              <Lien href={vscodeHref(racine, c.rel, c.ligne)} label={`ouvrir ${c.rel} dans VS Code`}>
                {c.rel}
              </Lien>
            ) : (
              <>
                <s>{c.rel}</s> <span className="text-dim">(absent)</span>
              </>
            )}
          </li>
        ))}
      </ul>
      {e.chemins_non_captes > 0 && (
        <span className="text-dim">+ {e.chemins_non_captes} non reconnu(s) par le motif</span>
      )}
    </>
  );
}

function Clause({ e }: { e: RoadmapEntree }) {
  return (
    <>
      {e.clause ? (
        <div>
          <ClauseBadge satisfaite={e.clause.satisfaite} />{" "}
          <code>
            {e.clause.pred}={e.clause.arg}
          </code>
          {e.clause.raison && <div className="text-dim">{e.clause.raison}</div>}
        </div>
      ) : (
        <span className="text-dim">sans clause</span>
      )}
      {e.holds.map((h, i) => (
        <div key={i}>
          <span className="text-dim">tient :</span> <ClauseBadge satisfaite={h.satisfaite} />{" "}
          <code>
            {h.pred}={h.arg}
          </code>
        </div>
      ))}
    </>
  );
}

function Direction({ rm }: { rm: Roadmap }) {
  if (!rm.direction.rangs.length) return <p className="text-dim">Aucune entrée ne porte de rang.</p>;
  return (
    <Panel className="mb-4">
      <div className="pilotage-defilement">
        <table className="runs-table" aria-label="Direction : rangs tranchés et statut de chaque entrée">
          <thead>
            <tr>
              <th>Rang</th>
              <th>Entrées</th>
            </tr>
          </thead>
          <tbody>
            {rm.direction.rangs.map((r) => (
              <tr key={r.rang}>
                <td>{r.rang}</td>
                <td>
                  {r.p_items.map((p, i) => (
                    <span key={`${p}-${i}`} className="pilotage-rang-item">
                      {p} <StatutBadge statut={r.statuts[i] ?? "?"} />
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function lireListe(v: unknown): string[] {
  return Array.isArray(v) ? v.map((x) => (typeof x === "string" ? x : JSON.stringify(x))) : [];
}

/** `portes_agi` recopie `records_graph.json["roadmap"]` (type libre dans le schéma) : lue champ par champ. */
function PortesAgi({ data, rm }: { data: PilotageV1; rm: Roadmap }) {
  if (!rm.portes_agi) return <Empty message={messageIndisponible(data.aveugle, "portes_agi", "Portes G0-G4")} />;
  const cles = Object.keys(rm.portes_agi).sort();
  if (!cles.length) return <p className="text-dim">records_graph.json ne publie aucune porte G (clé roadmap vide).</p>;
  return (
    <div className="pilotage-portes-agi mb-4">
      {cles.map((k) => {
        const p = rm.portes_agi![k];
        const o = typeof p === "object" && p !== null ? (p as Record<string, unknown>) : {};
        const records = lireListe(o.tested_by);
        return (
          <Panel key={k} as="article">
            <h4>{k}</h4>
            <p>
              statut : <strong>{typeof o.status === "string" ? o.status : "non publié"}</strong>
            </p>
            <p className="text-dim">SDR : {typeof o.sdr === "string" ? o.sdr : "non publié"}</p>
            <p className="text-dim">
              {Array.isArray(o.tested_by)
                ? `${records.length} record(s) : ${records.join(", ") || "aucun"}`
                : "records : non publiés"}
            </p>
          </Panel>
        );
      })}
    </div>
  );
}

function Rythme({ data, rm }: { data: PilotageV1; rm: Roadmap }) {
  const prio = Object.keys(rm.comptes.par_priorite).sort();
  const c = data.charge;
  const fenetre = c?.fenetre;
  const depuis = fenetre && typeof fenetre.depuis === "string" ? fenetre.depuis : null;
  const jours = fenetre && typeof fenetre.jours === "number" ? fenetre.jours : null;
  return (
    <>
      <p className="text-dim">
        Comptes recomputés par le backend le {new Date(data.generated_at * 1000).toLocaleString("fr-FR")} — aucun
        pourcentage d'avancement : le backlog grossit en travaillant, les entrées closes restent.
      </p>
      <div className="row mb-4">
        {prio.map((p) => {
          const n = rm.comptes.par_priorite[p];
          return (
            <Stat
              key={p}
              label={`${p} — ouvertes / closes / périmées`}
              value={`${n.ouvertes} / ${n.closes} / ${n.perimees}`}
            />
          );
        })}
        <Stat label="Têtes d'entrée (blocs)" value={rm.comptes.blocs} />
        <Stat label="Numéros" value={rm.comptes.numeros} />
        <Stat label="Illisibles" value={rm.comptes.illisibles} />
        <Stat
          label={
            depuis !== null && jours !== null
              ? `Science / méthodo (fichiers, ${jours} j depuis ${depuis})`
              : "Science / méthodo (fenêtre non publiée)"
          }
          value={mesure(c?.ratio_science_methodo, (v) => v.toFixed(2))}
        />
      </div>
    </>
  );
}

function Entrees({ data, rm }: { data: PilotageV1; rm: Roadmap }) {
  const [priorite, setPriorite] = useState("");
  const [statut, setStatut] = useState("");
  const priorites = [...new Set(rm.entrees.map((e) => e.priorite).filter((p): p is string => !!p))].sort();
  const vues = rm.entrees.filter((e) => (!priorite || e.priorite === priorite) && (!statut || e.statut === statut));
  const nonCaptes = vues.reduce((s, e) => s + e.chemins_non_captes, 0);
  const racine = data.repo_root;
  return (
    <>
      <div className="row mb-4">
        <Field label="Priorité">
          <select value={priorite} onChange={(ev) => setPriorite(ev.target.value)}>
            <option value="">toutes</option>
            {priorites.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Statut">
          <select value={statut} onChange={(ev) => setStatut(ev.target.value)}>
            <option value="">tous</option>
            {STATUTS.map((s) => (
              <option key={s} value={s}>
                {LIBELLE_STATUT[s]}
              </option>
            ))}
          </select>
        </Field>
        <span className="text-dim">
          {vues.length} entrée(s) affichée(s) sur {rm.entrees.length}
        </span>
      </div>
      <Panel>
        <div className="pilotage-defilement">
          <table className="runs-table" aria-label="Entrées du backlog">
            <thead>
              <tr>
                <th>N°</th>
                <th>Rang</th>
                <th>Statut</th>
                <th>Date du statut</th>
                <th>Titre</th>
                <th>Clause</th>
                <th>Chemins cités</th>
              </tr>
            </thead>
            <tbody>
              {vues.map((e) => (
                <tr key={`${e.num}-${e.bloc}`}>
                  <td className="pilotage-nowrap">
                    <Lien
                      href={vscodeHref(racine, BACKLOG_REL, e.lignes[0])}
                      label={`ouvrir ${e.num} dans VS Code (${BACKLOG_REL}, ligne ${e.lignes[0]})`}
                    >
                      {e.num}
                    </Lien>
                  </td>
                  <td>{e.rang ?? <span className="text-dim">sans rang</span>}</td>
                  <td>
                    <StatutBadge statut={e.statut} />
                    {e.raison_illisible && <div className="text-dim">{e.raison_illisible}</div>}
                  </td>
                  <td className="pilotage-nowrap">{e.date ?? <span className="text-dim">non datée</span>}</td>
                  <td>{e.titre}</td>
                  <td>
                    <Clause e={e} />
                  </td>
                  <td>
                    <Chemins e={e} racine={racine} />
                  </td>
                </tr>
              ))}
              {!vues.length && (
                <tr>
                  <td colSpan={7} className="text-dim">
                    Aucune entrée ne correspond aux filtres.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
      {nonCaptes > 0 && (
        <p className="text-dim">
          {nonCaptes} chemin(s) cité(s) non reconnu(s) par le motif du cliquet : la liste des chemins affichés est
          incomplète.
        </p>
      )}
    </>
  );
}

/** Onglet Roadmap : trois lectures de l'avancement (direction, portes G0-G4, rythme) et les entrées du backlog,
 *  LUES de `GET /api/pm/pilotage` — le parsing et l'évaluation des clauses sont faits par `tools/pm/pilotage.py`. */
export function PilotageRoadmapView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.pilotage,
    queryFn: () => fetchPilotage(),
    ...PILOTAGE_POLL,
  });

  if (isLoading) return <Loading label="Chargement du pilotage…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — pilotage inconnu." />;

  const rm = data.roadmap;
  return (
    <div className="pilotage-view">
      <h2>Roadmap</h2>
      <AveugleBanner lignes={data.aveugle} />
      {!rm ? (
        <Empty message={messageIndisponible(data.aveugle, "roadmap", "Roadmap")} />
      ) : (
        <>
          <h3>Direction</h3>
          <Direction rm={rm} />
          <h3>Portes G0-G4</h3>
          <PortesAgi data={data} rm={rm} />
          <h3>Rythme</h3>
          <Rythme data={data} rm={rm} />
          <h3>Entrées du backlog</h3>
          <Entrees data={data} rm={rm} />
        </>
      )}
    </div>
  );
}
