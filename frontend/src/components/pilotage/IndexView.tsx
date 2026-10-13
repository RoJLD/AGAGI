import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchIndex, type IndexFamille } from "../../api/pm";
import { queryKeys } from "../../api/queryKeys";
import { detailRaisons, filtrerArtefacts, LIMITE_AFFICHAGE, totalIntrouvables } from "../../lib/index";
import { formatAge, vscodeHref } from "../../lib/pilotage";
import { INDEX_POLL } from "../../lib/polling";
import { Empty } from "../ui/Empty";
import { ErrorState } from "../ui/ErrorState";
import { Field } from "../ui/Field";
import { Loading } from "../ui/Loading";
import { Panel } from "../ui/Panel";
import { AveugleBanner } from "./AveugleBanner";

const CHAMPS = ["titre", "date_declaree", "etat", "date_ajout_git"] as const;
const LIBELLE: Record<(typeof CHAMPS)[number], string> = {
  titre: "Titre introuvable",
  date_declaree: "Date déclarée introuvable",
  etat: "État introuvable",
  date_ajout_git: "Date d'ajout introuvable",
};
const Dim = ({ children }: { children: string }) => <span className="text-dim">{children}</span>;

function Introuvable({ c }: { c: Record<string, number> | undefined }) {
  const n = totalIntrouvables(c);
  return <>{n ? `${n} (${detailRaisons(c)})` : "0"}</>;
}

/** Une valeur déclarée et sa source (« 2026-09-01 (frontmatter) »), la source omise si le backend ne la nomme pas. */
const avecSource = (v: string, source: string | null | undefined) => (source ? `${v} (${source})` : v);

function LigneFamille({ f }: { f: IndexFamille }) {
  const inconnu = f.fichiers == null;
  return (
    <tr>
      <td>{f.nom}</td>
      <td className="pilotage-nowrap">
        {f.repertoire == null ? (
          <Dim>inconnu</Dim>
        ) : (
          <code>
            {f.repertoire}/{f.motif}
          </code>
        )}
      </td>
      <td>{inconnu ? <Dim>inconnu</Dim> : f.fichiers}</td>
      <td>{f.indexes == null ? <Dim>inconnu</Dim> : f.indexes}</td>
      <td>{f.exclus == null ? <Dim>inconnu</Dim> : f.exclus.length ? f.exclus.join(", ") : <Dim>aucun</Dim>}</td>
      <td>
        {f.illisibles == null ? (
          <Dim>inconnu</Dim>
        ) : f.illisibles.length ? (
          <ul className="pilotage-chemins">
            {f.illisibles.map((i) => (
              <li key={i.chemin}>
                {i.chemin} <span className="text-dim">({i.raison})</span>
              </li>
            ))}
          </ul>
        ) : (
          "0"
        )}
      </td>
      {CHAMPS.map((c) => (
        <td key={c}>{f.champs_introuvables == null ? <Dim>inconnu</Dim> : <Introuvable c={f.champs_introuvables[c]} />}</td>
      ))}
      <td>
        {f.format_declare == null ? (
          <Dim>inconnu</Dim>
        ) : (
          `date ${f.format_declare.date} · etat ${f.format_declare.etat} · sujet ${f.format_declare.sujet} · liens ${f.format_declare.liens} sur ${f.format_declare.fichiers}`
        )}
      </td>
    </tr>
  );
}

/** Onglet Index (P2.87) : les familles d'artefacts du dépôt et ce que l'index n'a PAS su lire, LUS de
 *  `GET /api/pm/index`. Aucun champ inventé : « sans titre », « sans date d'ajout », « inconnu » disent l'absence. */
export function IndexView() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.pm.index,
    queryFn: () => fetchIndex(),
    ...INDEX_POLL,
  });
  const [famille, setFamille] = useState("");
  const [texte, setTexte] = useState("");
  const [sansDate, setSansDate] = useState(false);

  if (isLoading) return <Loading label="Chargement de l'index…" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return <Empty message="Réponse vide du backend — index inconnu." />;

  const degrade = data.aveugle.filter((a) => a.startsWith("index:"));
  const raisonDegrade = degrade.length ? ` — ${degrade.join(" · ")}` : "";
  const vus = data.artefacts ? filtrerArtefacts(data.artefacts, { famille, texte, sansDate }) : [];
  const affiches = vus.slice(0, LIMITE_AFFICHAGE);
  return (
    <div className="pilotage-view">
      <h2>Index des artefacts</h2>
      <p className="text-dim">
        Relu depuis les fichiers du dépôt à chaque sondage (60 s) ; les dates d'ajout viennent de DATES_GIT.json, écrit
        par le tick PM là où l'historique git est complet.{" "}
        {data.dates
          ? `Dates : historique ${data.dates.historique}, instantané de ${formatAge(data.dates.age_s)}.`
          : "Dates d'ajout indisponibles (voir les lignes d'aveuglement)."}
      </p>
      <AveugleBanner
        lignes={data.aveugle}
        prefixeDegrade="index:"
        titreDegrade="Index en mode dégradé : familles et artefacts servis à null"
      />
      {!data.familles ? (
        <Empty message={`Familles indisponibles${raisonDegrade}`} />
      ) : (
        <Panel className="mb-4">
          <div className="pilotage-defilement">
            <table className="runs-table" aria-label="Familles d'artefacts">
              <thead>
                <tr>
                  <th>Famille</th>
                  <th>Motif</th>
                  <th>Fichiers</th>
                  <th>Indexés</th>
                  <th>Exclus</th>
                  <th>Illisibles</th>
                  {CHAMPS.map((c) => (
                    <th key={c}>{LIBELLE[c]}</th>
                  ))}
                  <th>Format déclaré (par clé)</th>
                </tr>
              </thead>
              <tbody>
                {data.familles.map((f) => (
                  <LigneFamille key={f.nom} f={f} />
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      <p>
        {data.hors_familles
          ? `${data.hors_familles.n} fichier(s) suivi(s) hors familles : ${detailRaisons(data.hors_familles.repertoires)}`
          : "Fichiers hors familles : inconnus (pas d'instantané git complet)."}
      </p>
      {!data.artefacts ? (
        <Empty message={`Artefacts indisponibles${raisonDegrade}`} />
      ) : (
        <>
          <div className="row mb-4">
            <Field label="Famille">
              <select value={famille} onChange={(e) => setFamille(e.target.value)}>
                <option value="">toutes</option>
                {(data.familles ?? []).map((f) => (
                  <option key={f.nom} value={f.nom}>
                    {f.nom}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Texte">
              <input value={texte} onChange={(e) => setTexte(e.target.value)} placeholder="titre ou chemin" />
            </Field>
            <label className="checkbox-inline">
              <input type="checkbox" checked={sansDate} onChange={(e) => setSansDate(e.target.checked)} /> sans date
              d'ajout
            </label>
            <span className="text-dim">
              {affiches.length < vus.length
                ? `${affiches.length} affiché(s) sur ${vus.length} — affinez le filtre`
                : `${vus.length} affiché(s) sur ${data.artefacts.length}`}
            </span>
          </div>
          <Panel>
            <div className="pilotage-defilement">
              <table className="runs-table" aria-label="Artefacts indexés">
                <thead>
                  <tr>
                    <th>Famille</th>
                    <th>Titre</th>
                    <th>Chemin</th>
                    <th>Date déclarée</th>
                    <th>Date d'ajout</th>
                    <th>État</th>
                  </tr>
                </thead>
                <tbody>
                  {affiches.map((a) => {
                    const href = vscodeHref(data.repo_root, a.chemin);
                    return (
                      <tr key={a.chemin}>
                        <td>{a.famille}</td>
                        <td>{a.titre ?? <Dim>sans titre</Dim>}</td>
                        <td>
                          {href ? (
                            <a href={href} aria-label={`ouvrir ${a.chemin} dans VS Code`}>
                              {a.chemin}
                            </a>
                          ) : (
                            a.chemin
                          )}
                        </td>
                        <td className="pilotage-nowrap">
                          {a.date_declaree ? avecSource(a.date_declaree, a.date_source) : <Dim>non déclarée</Dim>}
                        </td>
                        <td className="pilotage-nowrap">{a.date_ajout_git ?? <Dim>sans date d'ajout</Dim>}</td>
                        <td>{a.etat ? avecSource(a.etat, a.etat_source) : <Dim>non déclaré</Dim>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
