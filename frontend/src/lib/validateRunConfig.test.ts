import { describe, it, expect } from "vitest";
import { validateRunConfig } from "./validateRunConfig";
import type { RunConfig } from "../types";

const base: RunConfig = {
  script_name: "main_biosphere.py",
  world_type: "stoneage",
  base_seed: 0,
  n_seeds: 4,
  mutation_rate: null,
  variable_tested: "robust_hof_K",
  tags: [],
};

describe("validateRunConfig", () => {
  it("config valide = aucune erreur ni warning", () => {
    const r = validateRunConfig(base);
    expect(r.errors).toEqual([]);
    expect(r.warnings).toEqual([]);
  });

  it("graine négative = erreur", () => {
    expect(validateRunConfig({ ...base, base_seed: -1 }).errors.length).toBeGreaterThan(0);
  });

  it("R < 4 = warning de puissance", () => {
    expect(validateRunConfig({ ...base, n_seeds: 2 }).warnings.some((w) => w.includes("Puissance"))).toBe(true);
  });

  it("mutation_rate hors [0,1] = erreur", () => {
    expect(validateRunConfig({ ...base, mutation_rate: 2 }).errors.length).toBeGreaterThan(0);
  });

  it("variable testée vide = warning", () => {
    expect(validateRunConfig({ ...base, variable_tested: "" }).warnings.some((w) => w.includes("Variable"))).toBe(true);
  });
});
