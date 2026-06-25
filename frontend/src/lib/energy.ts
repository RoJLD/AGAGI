import type { EnergyPhases } from "../types";

export interface EnergyBar {
  name: string;
  value: number;
  pct: number;
}

const PHASES: { key: keyof EnergyPhases; label: string }[] = [
  { key: "brain", label: "cerveau" },
  { key: "action", label: "action" },
  { key: "biologie", label: "biologie" },
  { key: "mouvement", label: "mouvement" },
];

const BIO: { key: keyof EnergyPhases; label: string }[] = [
  { key: "bio_metab", label: "métab" },
  { key: "bio_terrain", label: "terrain" },
  { key: "bio_carry", label: "port" },
  { key: "bio_autres", label: "autres" },
];

function toBars(
  phases: EnergyPhases,
  defs: { key: keyof EnergyPhases; label: string }[],
  total: number,
): EnergyBar[] {
  return defs
    .map((d) => {
      const value = phases[d.key];
      return { name: d.label, value, pct: total ? (100 * value) / total : 0 };
    })
    .sort((a, b) => b.value - a.value);
}

/** 4 phases en part du net (tri décroissant). Si net == 0, pct = 0. */
export function buildPhaseBreakdown(phases: EnergyPhases): EnergyBar[] {
  return toBars(phases, PHASES, phases.net);
}

/** 4 composantes biologie en part du drain bio (somme des 4 ; tri décroissant). Si somme == 0, pct = 0. */
export function buildBioBreakdown(phases: EnergyPhases): EnergyBar[] {
  const bioNet = phases.bio_metab + phases.bio_terrain + phases.bio_carry + phases.bio_autres;
  return toBars(phases, BIO, bioNet);
}
