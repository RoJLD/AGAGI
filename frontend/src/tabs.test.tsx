import { test, expect } from "vitest";
import { buildNavItems, TAB_FAMILIES, TAB_KEYS } from "./tabs";

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
