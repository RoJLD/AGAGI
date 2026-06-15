/**
 * Pont entre les tokens CSS et les contextes JS qui ne comprennent pas `var()`
 * (canvas 2D, props `stroke`/`fill` de recharts).
 *
 * - `VIZ` / `ACCENT` : chaînes `var(--*)` utilisables dans `style={{ fill: ... }}` (SVG).
 * - `cssVar()` : valeur RÉSOLUE d'un token (hex) pour le canvas et recharts.
 */

export const VIZ = [
  "var(--viz-1)",
  "var(--viz-2)",
  "var(--viz-3)",
  "var(--viz-4)",
  "var(--viz-5)",
  "var(--viz-6)",
] as const;

export const ACCENT = "var(--color-accent)";

/** Lit la valeur calculée d'une variable CSS sur :root. Ex: cssVar("--viz-1") -> "#0d9488". */
export function cssVar(name: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Récupère d'un coup les couleurs data-viz résolues (pour canvas / recharts). */
export function vizColors(): string[] {
  return ["--viz-1", "--viz-2", "--viz-3", "--viz-4", "--viz-5", "--viz-6"].map(cssVar);
}
