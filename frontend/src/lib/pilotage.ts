/** Lecture de `pilotage_v1` pour la famille « Pilotage » — AUCUN recalcul : ces fonctions mettent en forme ce que
 *  `GET /api/pm/pilotage` publie (spec 2026-09-22 §3.3). Principe du dépôt (porte 14 appliquée à la vue) : une
 *  valeur absente se DIT (« non mesuré », « indisponible »), jamais un 0 ni une liste vide. */

export type BlocPilotage = "flotte" | "roadmap" | "portes" | "charge" | "portes_agi";

/** Préfixe des lignes `aveugle` qui NOMMENT chaque bloc, lus sur `tools/pm/pilotage.py` et
 *  `backend/app/services/pilotage_service.py` (lignes « <bloc> : bloc refusé par le modèle de la route » comprises).
 *  `charge` n'est `null` que si la flotte ET les compteurs manquent : ses deux causes sont les siennes. */
const MOTIFS: Record<BlocPilotage, RegExp> = {
  flotte: /^flotte\s*:/,
  roadmap: /^(backlog|roadmap)\s*:/,
  portes: /^portes\s*:/,
  charge: /^(charge|compteurs du PM|flotte)\s*:/,
  portes_agi: /^(portes_agi|graphe de records)\s*:/,
};

/** Lignes qui aveuglent TOUT le pilotage : mode dégradé du service, racine de dépôt suspecte. */
const GLOBALES = /^(pilotage:|racine résolue suspecte)/;

/** Les lignes `aveugle` qui expliquent un bloc `null` : les globales d'abord, puis celles du bloc. */
export function lignesDuBloc(aveugle: readonly string[], bloc: BlocPilotage): string[] {
  return [...aveugle.filter((l) => GLOBALES.test(l)), ...aveugle.filter((l) => MOTIFS[bloc].test(l))];
}

/** Message d'un bloc `null` : la raison publiée par le backend, ou l'aveu qu'il n'en a publié aucune — jamais
 *  un bloc vide qui ressemblerait à « rien à signaler ». */
export function messageIndisponible(aveugle: readonly string[], bloc: BlocPilotage, libelle: string): string {
  const lignes = lignesDuBloc(aveugle, bloc);
  if (lignes.length) return `${libelle} indisponible — ${lignes.join(" · ")}`;
  return `${libelle} indisponible — le backend n'a publié aucune ligne d'aveuglement qui nomme ce bloc (bloc null sans raison publiée : à signaler)`;
}

export const NON_MESURE = "non mesuré";

/** Un nombre publié, ou « non mesuré » pour `null` / absent / non fini — jamais un 0 de repli. */
export function mesure(v: number | null | undefined, fmt: (n: number) => string = String): string {
  return typeof v === "number" && Number.isFinite(v) ? fmt(v) : NON_MESURE;
}

const nf1 = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

/** Durée lisible (s, min, h, j). `null` -> « non mesuré ». */
export function formatAge(s: number | null | undefined): string {
  return mesure(s, (v) => {
    const a = Math.max(0, v);
    if (a < 60) return `${Math.round(a)} s`;
    if (a < 3600) return `${Math.round(a / 60)} min`;
    if (a < 86400) return `${nf1.format(a / 3600)} h`;
    return `${nf1.format(a / 86400)} j`;
  });
}

/** Lien `vscode://file/` bâti sur le `repo_root` DE TÊTE (POSIX, casse d'origine — jamais `flotte.repo_root`, que
 *  le board normalise en minuscules). `null` sans racine : un lien vers un chemin inconnu serait un décor.
 *  La ligne n'est ajoutée que si elle est fournie (celle d'une entrée est une position dans le BACKLOG). */
export function vscodeHref(repoRoot: string | null | undefined, rel: string, ligne?: number | null): string | null {
  if (!repoRoot) return null;
  const racine = repoRoot.replace(/\\/g, "/").replace(/\/+$/, "");
  const chemin = rel.replace(/\\/g, "/").replace(/^\/+/, "");
  const suffixe = typeof ligne === "number" ? `:${ligne}` : "";
  return `vscode://file/${encodeURI(`${racine}/${chemin}`)}${suffixe}`;
}

export const BACKLOG_REL = "docs/roadmap/PRIORITES_ET_DETTES.md";

// ------------------------------------------------------------------------------------------------------------
// `flotte` est `dict | None` SANS modèle (son contrat appartient au board, session PM) : `schema.ts` la type
// `{[key: string]: unknown}`. Elle est donc LUE ici, champ par champ ; une clé absente ou d'un type inattendu
// rend `null` (« non publié »), et une entrée illisible est COMPTÉE, jamais retirée en silence.

export interface SessionVue {
  nom: string;
  branche: string | null;
  /** `null` : clé absente ou illisible dans le tableau — « non publié », jamais une liste vide. */
  claims: string[] | null;
  inferes: string[] | null;
  fichiers: number | null;
  /** P2.118 : écritures Bash POSSIBLES, comptées jamais nommées ; `null` = jamais compté (hook absent). */
  bashEcritures: number | null;
  /** `false` : session sans bulletin — claims et fichiers en vol INCONNUS, pas nuls. `null` : non publié. */
  bulletin: boolean | null;
  heartbeatAt: number | null;
}

export interface AlerteVue {
  id: string;
  cle: string;
  gravite: string;
  message: string;
  preuve: unknown;
}

export interface Liste<T> {
  items: T[];
  illisibles: number;
}

export interface FlotteVue {
  sessions: Liste<SessionVue> | null;
  alertes: Liste<AlerteVue> | null;
  mortes: string[] | null;
  /** Les lignes d'aveuglement DU TABLEAU lui-même : une liste vide calculée sur une source aveugle n'est pas un
   *  négatif (le board met `claims_inferes = []` quand le backlog est illisible, 0 session quand le registre l'est). */
  aveugle: string[];
}

/** Le tableau est-il aveugle sur la source dont la ligne commence par `prefixe` (gabarits de `tools/pm/board.py`) ? */
export function flotteAveugleSur(f: FlotteVue, prefixe: string): boolean {
  return f.aveugle.some((l) => l.startsWith(prefixe));
}

/** `tools/pm/board.py::PEREMPTION_S` (= TTL du bail pm) : au-delà, aucun tick n'a renouvelé le bail — le tableau
 *  décrit une heure passée et le rôle PM est vacant. Le JSON ne le publie pas : recopié ici, et un témoin Python
 *  (`test_le_seuil_de_peremption_du_FRONT_suit_celui_du_tableau`) rougit si l'un bouge sans l'autre. */
export const PEREMPTION_TABLEAU_S = 7_200;

/** Paraphrase de `board.CECITE_FICHIERS` (absente du JSON) : ce que la colonne « fichiers en vol » ne voit pas. */
export const CECITE_FICHIERS =
  "Fichiers en vol : seuls les outils d'édition (Edit, Write, MultiEdit, NotebookEdit) les nomment. Un script lancé par Bash qui réécrit un fichier n'y laisse aucun nom — il est seulement compté (« écritures Bash non nommées ») ; A1 et les P-items inférés ne voient pas ces écritures.";

function estObjet(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function chaines(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

function nombreOuNull(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function liste<T>(v: unknown, lire: (o: Record<string, unknown>) => T | null): Liste<T> | null {
  if (!Array.isArray(v)) return null;
  const items: T[] = [];
  let illisibles = 0;
  for (const x of v) {
    const lu = estObjet(x) ? lire(x) : null;
    if (lu === null) illisibles += 1;
    else items.push(lu);
  }
  return { items, illisibles };
}

export function lireFlotte(flotte: Record<string, unknown>): FlotteVue {
  return {
    sessions: liste(flotte.sessions, (o) => ({
      nom: (typeof o.name === "string" && o.name) || (typeof o.session_id === "string" && o.session_id) || "?",
      branche: typeof o.branch === "string" ? o.branch : null,
      claims: Array.isArray(o.claims) ? chaines(o.claims) : null,
      inferes: Array.isArray(o.claims_inferes) ? chaines(o.claims_inferes) : null,
      fichiers: Array.isArray(o.files_touched) ? o.files_touched.length : null,
      bashEcritures: nombreOuNull(o.bash_ecritures_possibles),
      bulletin: typeof o.bulletin === "boolean" ? o.bulletin : null,
      heartbeatAt: nombreOuNull(o.heartbeat_at),
    })),
    alertes: liste(flotte.alertes, (o) =>
      typeof o.message === "string"
        ? {
            id: typeof o.id === "string" ? o.id : "?",
            cle: typeof o.cle === "string" ? o.cle : String(o.message),
            gravite: typeof o.gravite === "string" ? o.gravite : "?",
            message: o.message,
            preuve: o.preuve,
          }
        : null,
    ),
    mortes: Array.isArray(flotte.sessions_mortes) ? chaines(flotte.sessions_mortes) : null,
    aveugle: chaines(flotte.aveugle),
  };
}
