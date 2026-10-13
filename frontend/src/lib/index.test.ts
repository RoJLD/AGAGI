import { describe, expect, test } from "vitest";
import { detailRaisons, filtrerArtefacts, LIMITE_AFFICHAGE, messageIndex, totalIntrouvables } from "./index";
import type { IndexArtefact } from "../api/pm";

const A = (o: Partial<IndexArtefact>): IndexArtefact => ({
  famille: "spec",
  chemin: "docs/x.md",
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
  ...o,
});

describe("comptes de champs introuvables", () => {
  test("total et détail par raison, dans l'ordre décroissant", () => {
    const c = { frontmatter_absent: 34, cle_absente: 2 };
    expect(totalIntrouvables(c)).toBe(36);
    expect(detailRaisons(c)).toBe("frontmatter_absent 34 · cle_absente 2");
  });
  test("aucun champ introuvable : 0 MESURÉ, détail vide", () => {
    expect(totalIntrouvables({})).toBe(0);
    expect(detailRaisons({})).toBe("");
  });
});

describe("filtrerArtefacts", () => {
  const arts = [
    A({ famille: "record", titre: "Perception", chemin: "docs/EDR/1.md", date_ajout_git: "2026-09-01" }),
    A({ famille: "spec", titre: null, chemin: "docs/superpowers/specs/2026-09-26-p.md" }),
  ];
  test("famille, texte (titre OU chemin), sans date d'ajout", () => {
    expect(filtrerArtefacts(arts, { famille: "record", texte: "", sansDate: false })).toHaveLength(1);
    expect(filtrerArtefacts(arts, { famille: "", texte: "2026-09-26", sansDate: false })[0].famille).toBe("spec");
    expect(filtrerArtefacts(arts, { famille: "", texte: "percep", sansDate: false })[0].famille).toBe("record");
    expect(filtrerArtefacts(arts, { famille: "", texte: "", sansDate: true })[0].famille).toBe("spec");
  });
  test("sans date d'ajout : un champ ABSENT (le schéma le déclare optionnel) compte comme sans date", () => {
    const { date_ajout_git: _omis, ...sansCle } = A({ famille: "adr", chemin: "docs/ADR/1.md" });
    expect(filtrerArtefacts([sansCle as IndexArtefact], { famille: "", texte: "", sansDate: true })).toHaveLength(1);
  });
  test("la limite d'affichage est un nombre déclaré", () => {
    expect(LIMITE_AFFICHAGE).toBe(300);
  });
});

describe("messageIndex", () => {
  test("un bloc null porte SES lignes et celles du mode dégradé, jamais un silence (revue finale, M2)", () => {
    const av = ["familles : bloc refusé (x)", "artefacts : autre", "index: RuntimeError: y", "dates : z"];
    expect(messageIndex(av, "familles", "Familles")).toBe(
      "Familles indisponibles — familles : bloc refusé (x) · index: RuntimeError: y",
    );
    expect(messageIndex([], "artefacts", "Artefacts")).toMatch(/^Artefacts indisponibles — .*aucune ligne/);
  });
});
