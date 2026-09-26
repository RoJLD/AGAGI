import { afterEach, expect, test, vi } from "vitest";

vi.mock("./client", () => ({ apiFetch: vi.fn().mockResolvedValue({}) }));
import { apiFetch } from "./client";
import { fetchPilotage, FRAIS_TIMEOUT_MS } from "./pm";

const mocked = apiFetch as ReturnType<typeof vi.fn>;
afterEach(() => mocked.mockClear());

test("le poll appelle /api/pm/pilotage, sans recalcul ni timeout étendu", async () => {
  await fetchPilotage();
  expect(mocked).toHaveBeenCalledWith("/api/pm/pilotage");
});

test("frais=1 passe un timeout AU-DELÀ du majorant mesuré de snapshot() (18,1 s)", async () => {
  await fetchPilotage(true);
  const [chemin, init] = mocked.mock.calls[0];
  expect(chemin).toBe("/api/pm/pilotage?frais=1");
  expect(init.timeoutMs).toBeGreaterThan(18_000);
  expect(init.timeoutMs).toBe(FRAIS_TIMEOUT_MS);
});
