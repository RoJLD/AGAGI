import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { AveugleBanner } from "./AveugleBanner";

afterEach(() => cleanup());

test("aucune ligne : rien n'est rendu", () => {
  const { container } = render(<AveugleBanner lignes={[]} />);
  expect(container.innerHTML).toBe("");
});

test("une source absente est un STATUT poli, chaque ligne affichée en entier", () => {
  const lignes = [
    "backlog : docs/roadmap/PRIORITES_ET_DETTES.md introuvable",
    "portes : tools/hooks/pre-commit illisible",
  ];
  render(<AveugleBanner lignes={lignes} />);
  const statut = screen.getByRole("status");
  expect(statut.getAttribute("aria-live")).toBe("polite");
  for (const l of lignes) expect(statut.textContent).toContain(l);
  expect(screen.queryByRole("alert")).toBeNull();
});

test("une ligne « pilotage: » (exception du service) est une ALERTE", () => {
  render(<AveugleBanner lignes={["pilotage: ValueError: boum", "flotte : BOARD.json introuvable"]} />);
  expect(screen.getByRole("alert").textContent).toContain("pilotage: ValueError: boum");
  expect(screen.getByRole("status").textContent).toContain("flotte : BOARD.json introuvable");
});
