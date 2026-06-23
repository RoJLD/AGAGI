import type { RunConfig } from "../types";

export interface ValidationResult {
  errors: string[];
  warnings: string[];
}

const MAX_SEED = 2 ** 31;
const MAX_BATCH = 64;

/** Validation pure d'une config de lancement. errors = bloquant ; warnings = méthodo (non bloquant). */
export function validateRunConfig(c: RunConfig): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!c.script_name) errors.push("Choisis un script principal.");
  if (!Number.isInteger(c.base_seed) || c.base_seed < 0 || c.base_seed >= MAX_SEED) {
    errors.push("Graine de base hors plage [0, 2³¹).");
  }
  if (!Number.isInteger(c.n_seeds) || c.n_seeds < 1) {
    errors.push("Nombre de seeds ≥ 1 requis.");
  } else if (c.n_seeds > MAX_BATCH) {
    errors.push(`Nombre de seeds ≤ ${MAX_BATCH} (garde-fou mono-machine).`);
  }
  if (c.mutation_rate !== null && (c.mutation_rate < 0 || c.mutation_rate > 1)) {
    errors.push("Taux de mutation ∈ [0, 1].");
  }

  if (c.n_seeds >= 1 && c.n_seeds < 4) {
    warnings.push("Puissance faible : R < 4 — vise ≥ 4 seeds avant de conclure (Commandement 15).");
  }
  if (!c.variable_tested.trim()) {
    warnings.push("Variable testée non renseignée (recommandé : 1 seule variable par run).");
  }
  return { errors, warnings };
}
