import { test, expect } from "vitest";
import { buildNavItems, TAB_FAMILIES, TAB_KEYS } from "./tabs";
import tabsSrc from "./tabs.ts?raw";

test("buildNavItems aplatit les familles en items ordonnés avec group + icône", () => {
  const items = buildNavItems(TAB_FAMILIES);
  // ordre = concat des familles, même nombre que TAB_KEYS
  expect(items.map((i) => i.id)).toEqual(TAB_KEYS as unknown as string[]);
  // chaque item porte le nom de famille en group + une icône
  const parcours = items.find((i) => i.id === "parcours")!;
  expect(parcours.group).toBe("Expérimentation");
  expect(parcours.label).toBe("Parcours");
  expect(typeof parcours.icon).toBe("object");
});

test("famille Pilotage : trois onglets, libellés et icônes — l'assertion générique ci-dessus passerait sans elle", () => {
  const pilotage = buildNavItems(TAB_FAMILIES).filter((i) => i.group === "Pilotage");
  expect(pilotage.map((i) => [i.id, i.label])).toEqual([
    ["flotte", "Flotte"],
    ["roadmap", "Roadmap"],
    ["portes", "Portes"],
  ]);
  for (const i of pilotage) expect(typeof i.icon).toBe("object");
});

test("tabs.ts n'importe pas Map de lucide-react (il masquerait le global Map) : MapIcon", () => {
  // Assertion sur le SOURCE : lucide exporte Map === MapIcon, donc comparer les valeurs ne peut pas échouer.
  const imports = tabsSrc.match(/import\s*\{([^}]*)\}\s*from\s*"lucide-react"/)![1];
  const noms = imports.split(",").map((n) => n.trim());
  expect(noms).toContain("MapIcon");
  expect(noms).not.toContain("Map");
});
