import type { PilotageV1 } from "../../api/pm";

/** Réponse `pilotage_v1` factice pour les tests des vues — TYPÉE contre le schéma généré : `tsc` (donc
 *  `npm run build`) rougit si le contrat du backend change sous elle. Formes recopiées d'un `GET /api/pm/pilotage`
 *  réel (2026-09-26), réduites. */
export const RACINE = "C:/Users/robla/VScode_Project/AGAGI";

export function pilotageFixture(over: Partial<PilotageV1> = {}): PilotageV1 {
  return {
    schema: "pilotage_v1",
    generated_at: 1_790_430_000,
    repo_root: RACINE,
    aveugle: [],
    flotte: {
      generated_at: 1_790_429_000,
      repo_root: "c:/users/robla/vscode_project/agagi",
      aveugle: [],
      sessions: [
        {
          name: "agagi-e2",
          session_id: "a203",
          branch: "feat/d1-prod-pairing",
          claims: ["P2.114"],
          claims_inferes: ["P2.107"],
          files_touched: ["tools/pm/snapshot.py", "tests/sandbox/test_pm_snapshot.py"],
          bash_ecritures_possibles: 3,
          bulletin: true,
          heartbeat_at: 1_790_429_400,
        },
        {
          name: "agagi-88",
          session_id: "b88",
          branch: null,
          claims: [],
          claims_inferes: [],
          files_touched: [],
          bulletin: false,
        },
      ],
      sessions_mortes: [],
      alertes: [
        {
          id: "A1",
          cle: "A1:x",
          gravite: "alerte",
          message: "memory.md touché par 3 sessions vivantes",
          preuve: { fichier: "memory.md" },
        },
        {
          id: "A7",
          cle: "A7:b88",
          gravite: "info",
          message: "agagi-88 active depuis 3 h sans P-item",
          preuve: { session: "agagi-88" },
        },
      ],
      charge_connue: { sims_en_vol: 0, cpu_pct: 5.3, bails_vivants: [] },
      worktrees: [],
      bails: { live: [], dead: [] },
    },
    roadmap: {
      direction: {
        rangs: [
          { rang: "1", p_items: ["P1.6", "P2.73"], statuts: ["close", "ouverte"] },
          { rang: "14 ter", p_items: ["P2.78"], statuts: ["close"] },
        ],
      },
      entrees: [
        {
          num: "P2.78",
          nums: ["P2.78"],
          bloc: 0,
          priorite: "P2",
          rang: "14 ter",
          statut: "close",
          date: "2026-09-22",
          titre: "garde de coût — voir [ADR-004](docs/ADR/ADR-004.md) pour le détail",
          lignes: [671, 697],
          clause: { pred: "grep_present", arg: "tools/cost_guard.py::process_time", satisfaite: true, raison: null },
          holds: [],
          chemins: [
            { rel: "tools/cost_guard.py", existe: true, ligne: null },
            { rel: "tools/disparu.py", existe: false, ligne: null },
          ],
          chemins_non_captes: 2,
        },
        {
          num: "P2.114",
          nums: ["P2.114"],
          bloc: 1,
          priorite: "P2",
          rang: null,
          statut: "ouverte",
          date: null,
          titre: "frais=1 depuis un worktree",
          lignes: [2226, 2236],
          clause: {
            pred: "path_present",
            arg: "x/y.md",
            satisfaite: null,
            raison: "existe ICI mais n'est PAS SUIVI par git",
          },
          holds: [],
          chemins: [],
          chemins_non_captes: 0,
        },
        {
          num: "P2.120",
          nums: ["P2.120"],
          bloc: 3,
          priorite: "P2",
          rang: "6",
          statut: "ouverte",
          date: "2026-09-26",
          titre: "une clause NON satisfaite et une affirmation permanente rompue",
          lignes: [2300, 2310],
          clause: { pred: "grep_present", arg: "tools/x.py::y", satisfaite: false, raison: null },
          holds: [{ pred: "grep_absent", arg: "tools/z.py::w", satisfaite: false }],
          chemins: [],
          chemins_non_captes: 0,
        },
        {
          num: "P3.9",
          nums: ["P3.9"],
          bloc: 2,
          priorite: null,
          rang: null,
          statut: "illisible",
          date: null,
          titre: "**P3.9 — tête cassée",
          lignes: [3000, 3004],
          clause: null,
          holds: [],
          chemins: [],
          chemins_non_captes: 0,
          raison_illisible: "IndexError: list index out of range",
        },
      ],
      comptes: {
        par_priorite: { P2: { ouvertes: 2, closes: 1, perimees: 0 } },
        blocs: 4,
        numeros: 4,
        illisibles: 1,
      },
      portes_agi: {
        G0: { sdr: "SDR-G0", status: "PASSED", tested_by: ["EDR-001", "EDR-002"] },
        G1: { sdr: "SDR-G1", status: "OPEN", tested_by: [] },
      },
    },
    portes: [
      {
        num: "1",
        module: "tools.check_record_links",
        titre: "graphe de records",
        temoins: ["tests/sandbox/test_record_links.py::test_orphelin"],
        mutations: 2,
        baseline: { chemin: "tools/record_link_baseline.json", existe: true, dette: null },
      },
      {
        num: "4",
        module: "tools.check_backlog_freshness",
        titre: "fraîcheur du backlog",
        temoins: ["tests/sandbox/test_backlog_freshness.py"],
        mutations: 3,
        baseline: { chemin: "tools/backlog_freshness_baseline.json", existe: true, dette: 2 },
      },
      {
        num: "7",
        module: "tools.check_staged_authorship",
        titre: null,
        temoins: null,
        mutations: null,
        baseline: null,
      },
      {
        num: "12",
        module: "tools.check_data_paths",
        titre: "chemins de données",
        temoins: ["tests/sandbox/test_data_paths.py::test_x"],
        mutations: 1,
        baseline: { chemin: "tools/data_paths_baseline.json", existe: false, dette: null },
      },
    ],
    charge: {
      sims_en_vol: 0,
      cpu_pct: 5.3,
      bails_vivants: [],
      flotte_age_s: 1000,
      ratio_science_methodo: 0.83,
      fichiers: { science: 10, methodo: 12, autre: 3 },
      fenetre: { depuis: "2026-08-27", jours: 30 },
    },
    ...over,
  };
}

/** Le mode dégradé du service : une exception NOMMÉE, les quatre blocs à null. */
export function pilotageDegrade(): PilotageV1 {
  return pilotageFixture({
    aveugle: ["pilotage: ImportError: tools.pm indisponible dans ce processus"],
    flotte: null,
    roadmap: null,
    portes: null,
    charge: null,
  });
}
