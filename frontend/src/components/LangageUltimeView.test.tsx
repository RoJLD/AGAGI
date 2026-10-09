import { render, screen, waitFor } from "@testing-library/react";
import { test, expect, vi, beforeEach } from "vitest";
import { LangageUltimeView } from "./LangageUltimeView";

vi.mock("../hooks/useWebSocket", () => ({
  useWebSocket: () => ({ status: "open" }),
}));

beforeEach(() => {
  vi.restoreAllMocks();
  // Mock global fetch
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/lu/live_sample")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              timestamp: 100,
              active_mode: "CONTINUOUS_GIGATOKEN_LU",
              latent_dim: 16,
              hear_radius: 3,
              noise_level: 0.05,
              mean_cka: 0.942,
              agents: [
                {
                  id: "ag_alpha",
                  x: 4,
                  y: 5,
                  energy: 82.5,
                  role: "Éclaireur",
                  dsl: "(Agent_alph:AGENT)-[TARGETS]->(Mammouth:CONCEPT)",
                  gigatoken: [0.2, 0.1, -0.3, 0.5, 0.0, 0.1, -0.2, 0.4],
                  human_text_fr: "Agent_alph a pour cible prioritaire Mammouth.",
                  human_text_en: "Agent_alph actively targets Mammouth.",
                  primary_intent: "Chasse",
                  confidence: 0.95,
                },
              ],
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    })
  );
});

test("LangageUltimeView monte et affiche le titre et les cartes KPI", async () => {
  render(<LangageUltimeView />);
  expect(
    screen.getByText(/Langage Ultime \(LU\) — Communication Latente Continue/i)
  ).toBeTruthy();
  expect(screen.getByText(/Fidélité sous bruit σ=0.15/i)).toBeTruthy();

  // Attendre la résolution des agents décompilés
  await waitFor(() => {
    expect(screen.getByText("ag_alpha")).toBeTruthy();
  });
  expect(
    screen.getByText(/"Agent_alph a pour cible prioritaire Mammouth."/i)
  ).toBeTruthy();
  expect(
    screen.getByText(/Foyer Rituel & Transmission Culturelle/i)
  ).toBeTruthy();
  expect(screen.getAllByText(/atténuation acoustique/i).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText(/TRANSMISSIONS AU FOYER/i)).toBeTruthy();
});
