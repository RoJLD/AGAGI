import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", () => ({ apiFetch: vi.fn() }));
import { apiFetch } from "../../api/client";
import { queryKeys } from "../../api/queryKeys";
import { PILOTAGE_POLL } from "../../lib/polling";
import { PilotageFlotteView } from "./PilotageFlotteView";
import { PilotagePortesView } from "./PilotagePortesView";
import { PilotageRoadmapView } from "./PilotageRoadmapView";
import { pilotageFixture } from "./fixture";

afterEach(() => cleanup());

test("les trois vues partagent UNE requête (même queryKey) et sondent toutes avec PILOTAGE_POLL", async () => {
  const mocked = apiFetch as ReturnType<typeof vi.fn>;
  mocked.mockResolvedValue(pilotageFixture());
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <PilotageFlotteView />
      <PilotageRoadmapView />
      <PilotagePortesView />
    </QueryClientProvider>,
  );
  await screen.findByRole("table", { name: "Portes du hook pre-commit" });
  await screen.findByRole("table", { name: "Entrées du backlog" });
  await screen.findByRole("table", { name: /Sessions vivantes/ });
  expect(mocked.mock.calls.filter((c) => c[0] === "/api/pm/pilotage")).toHaveLength(1);
  const query = qc.getQueryCache().find({ queryKey: queryKeys.pm.pilotage })!;
  const options = query.observers.map((o) => o.options);
  expect(options).toHaveLength(3);
  for (const o of options) {
    expect(o.refetchInterval).toBe(PILOTAGE_POLL.refetchInterval);
    expect(o.staleTime).toBe(PILOTAGE_POLL.staleTime);
    expect(o.refetchIntervalInBackground).toBe(false);
  }
});
