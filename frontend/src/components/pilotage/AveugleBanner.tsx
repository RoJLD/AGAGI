/** Les lignes `aveugle` publiées par un service PM (`pilotage_v1`, `index_v1`), TOUTES affichées en tête de vue, jamais
 *  repliées ni filtrées : une source absente ne doit pas ressembler à une source saine (spec §1, principe 3). Deux
 *  natures, deux rôles (J3) : une exception du service (ligne préfixée `prefixeDegrade`, mode dégradé) est une alerte ;
 *  une source absente est un statut. Le préfixe est un paramètre : chaque service nomme son propre mode dégradé. */
export function AveugleBanner({
  lignes,
  prefixeDegrade = "pilotage:",
  titreDegrade = "Pilotage en mode dégradé : les quatre blocs sont servis à null",
}: {
  lignes: readonly string[];
  prefixeDegrade?: string;
  titreDegrade?: string;
}) {
  if (!lignes.length) return null;
  const exceptions = lignes.filter((l) => l.startsWith(prefixeDegrade));
  const sources = lignes.filter((l) => !l.startsWith(prefixeDegrade));
  return (
    <div className="aveugle-banner">
      {exceptions.length > 0 && (
        <div role="alert" className="aveugle-banner__bloc aveugle-banner__bloc--alerte">
          <strong>{titreDegrade}</strong>
          <ul>
            {exceptions.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      )}
      {sources.length > 0 && (
        <div role="status" aria-live="polite" className="aveugle-banner__bloc">
          <strong>
            {sources.length} ligne{sources.length > 1 ? "s" : ""} d'aveuglement publiée{sources.length > 1 ? "s" : ""}{" "}
            par le backend
          </strong>
          <ul>
            {sources.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
