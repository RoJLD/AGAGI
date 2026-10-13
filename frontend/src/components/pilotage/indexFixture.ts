import type { IndexV1 } from "../../api/pm";

/** Réponse index_v1 factice, TYPÉE contre le schéma généré (tsc rougit si le contrat change sous elle). */
export function indexFixture(over: Partial<IndexV1> = {}): IndexV1 {
  return {
    schema: "index_v1",
    generated_at: 1_790_430_000,
    repo_root: "C:/Users/robla/VScode_Project/AGAGI",
    aveugle: [],
    dates: { generated_at: 1_790_429_400, age_s: 600, head: "abc", historique: "complet" },
    familles: [
      {
        nom: "record",
        motif: "*.md",
        repertoire: "docs/EDR",
        exclus: ["README.md"],
        fichiers: 4,
        indexes: 2,
        illisibles: [{ chemin: "docs/EDR/003_c.md", raison: "frontmatter_yaml_invalide" }],
        champs_introuvables: {
          titre: { frontmatter_absent: 1 },
          date_declaree: { frontmatter_absent: 2 },
          etat: { frontmatter_absent: 1 },
          date_ajout_git: {},
          liens: {},
        },
        format_declare: { date: 0, etat: 0, sujet: 0, liens: 0, fichiers: 2 },
      },
      {
        nom: "adr",
        motif: "*.md",
        repertoire: "docs/ADR",
        exclus: null,
        fichiers: null,
        indexes: null,
        illisibles: null,
        champs_introuvables: null,
        format_declare: null,
      },
    ],
    hors_familles: { n: 12, repertoires: { "docs/roadmap": 10, "docs/specs": 2 } },
    artefacts: [
      {
        famille: "record",
        chemin: "docs/EDR/001_a.md",
        titre: "Perception demandée",
        date_declaree: null,
        date_source: null,
        date_ajout_git: "2026-09-01",
        etat: "X_DEMANDED",
        etat_source: "verdict",
        regime: null,
        scelle: null,
        gate: "G1",
        liens: [{ rel: "tests", cible: "SDR-G1" }],
      },
      {
        famille: "record",
        chemin: "docs/EDR/002_b.md",
        titre: null,
        date_declaree: null,
        date_source: null,
        date_ajout_git: null,
        etat: null,
        etat_source: null,
        regime: null,
        scelle: null,
        gate: null,
        liens: [],
      },
    ],
    ...over,
  };
}
