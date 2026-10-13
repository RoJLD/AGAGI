import type { IndexArtefact } from "../api/pm";

/** Affichage borné et DIT : au-delà, la table écrit « n affichés sur m — affinez le filtre », jamais une coupe muette. */
export const LIMITE_AFFICHAGE = 300;

/** Somme des champs introuvables d'une famille pour un champ. `{}` est un 0 MESURÉ (l'index a tout lu) ; l'appelant
 *  distingue lui-même le bloc absent (`champs_introuvables` null → « inconnu »), jamais ramené à 0 ici. */
export function totalIntrouvables(c: Record<string, number> | null | undefined): number {
  return Object.values(c ?? {}).reduce((s, n) => s + n, 0);
}

/** « raison n · raison n », par compte décroissant : la raison est publiée, jamais seulement le total. */
export function detailRaisons(c: Record<string, number> | null | undefined): string {
  return Object.entries(c ?? {})
    .sort((a, b) => b[1] - a[1])
    .map(([r, n]) => `${r} ${n}`)
    .join(" · ");
}

export interface FiltreIndex {
  famille: string;
  texte: string;
  sansDate: boolean;
}

/** Filtre de la table des artefacts. Les champs du schéma généré sont OPTIONNELS (`?: string | null`) : l'absence
 *  d'une date d'ajout se teste par `== null`, qui couvre `null` ET `undefined`. */
export function filtrerArtefacts(arts: IndexArtefact[], f: FiltreIndex): IndexArtefact[] {
  const t = f.texte.trim().toLowerCase();
  return arts.filter(
    (a) =>
      (!f.famille || a.famille === f.famille) &&
      (!t || a.chemin.toLowerCase().includes(t) || (a.titre ?? "").toLowerCase().includes(t)) &&
      (!f.sansDate || a.date_ajout_git == null),
  );
}
