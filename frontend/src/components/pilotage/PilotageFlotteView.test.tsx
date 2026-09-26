import type { ReactNode } from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

// Mock PARTIEL : ApiError reste la vraie classe (ErrorState en dépend), seul apiFetch est remplacé.
vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  apiFetch: vi.fn(),
}));
import { apiFetch, ApiError } from "../../api/client";
import type { PilotageV1 } from "../../api/pm";
import { PilotageFlotteView } from "./PilotageFlotteView";
import { pilotageDegrade, pilotageFixture } from "./fixture";

const mocked = apiFetch as ReturnType<typeof vi.fn>;

function rendre(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return { qc, ...render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>) };
}

/** Une réponse dont la flotte porte ses propres champs (le reste = fixture). */
function avecFlotte(f: Record<string, unknown>, over: Partial<PilotageV1> = {}): PilotageV1 {
  const base = pilotageFixture();
  return { ...base, flotte: { ...base.flotte!, ...f }, ...over };
}

const tableSessions = () => screen.findByRole("table", { name: /Sessions vivantes/ });

beforeEach(() => mocked.mockResolvedValue(pilotageFixture()));
afterEach(() => {
  cleanup();
  mocked.mockReset();
});

test("lit /api/pm/pilotage et rend sessions, alertes et charge", async () => {
  rendre(<PilotageFlotteView />);
  const table = await tableSessions();
  expect(mocked).toHaveBeenCalledWith("/api/pm/pilotage");
  expect(within(table).getByText("agagi-e2")).toBeTruthy();
  expect(within(table).getByText("P2.114")).toBeTruthy();
  expect(within(table).getByText("il y a 10 min")).toBeTruthy(); // 1_790_430_000 - 1_790_429_400
  expect(screen.getByText(/memory\.md touché par 3 sessions/)).toBeTruthy();
  expect(screen.getByText("A1 alerte").className).toContain("badge--danger");
  expect(screen.getByText("A7 info").className).toContain("badge--warning");
  expect(screen.getByText("17 min")).toBeTruthy(); // âge de la flotte : 1000 s
});

test("fichiers en vol : le compte Bash P2.118 voyage À CÔTÉ de la liste, et la cécité est dite", async () => {
  rendre(<PilotageFlotteView />);
  const table = await tableSessions();
  expect(within(table).getByText("2 (+3 écriture(s) Bash non nommée(s))")).toBeTruthy();
  expect(screen.getByText(/Un script lancé par Bash qui réécrit un fichier n'y laisse aucun nom/)).toBeTruthy();
});

test("une session SANS bulletin dit « sans bulletin », jamais 0 fichier en vol", async () => {
  rendre(<PilotageFlotteView />);
  const table = await tableSessions();
  const ligne = within(table).getByText("agagi-88").closest("tr")!;
  expect(within(ligne).getAllByText("sans bulletin")).toHaveLength(3);
  expect(within(ligne).queryByText("0")).toBeNull();
});

test("backlog aveugle CÔTÉ TABLEAU : les P-items inférés sont inconnus, jamais « aucun »", async () => {
  mocked.mockResolvedValue(avecFlotte({ aveugle: ["backlog (chemins cités par les entrées)"] }));
  rendre(<PilotageFlotteView />);
  const table = await tableSessions();
  const ligne = within(table).getByText("agagi-e2").closest("tr")!;
  expect(within(ligne).getByText("inconnu (backlog aveugle côté tableau)")).toBeTruthy();
  expect(within(ligne).queryByText("P2.107")).toBeNull();
});

test("registre aveugle et 0 session : « sessions INCONNUES », jamais « aucune session »", async () => {
  mocked.mockResolvedValue(avecFlotte({ sessions: [], alertes: [], aveugle: ["registre natif (~/.claude/sessions)"] }));
  rendre(<PilotageFlotteView />);
  const table = await tableSessions();
  expect(within(table).getByText(/Sessions INCONNUES : le tableau est aveugle sur le registre natif/)).toBeTruthy();
  expect(screen.queryByText("Aucune session vivante recensée par le tableau.")).toBeNull();
  expect(screen.getByText(/Aucune alerte dans le tableau — qui est aveugle sur : registre natif/)).toBeTruthy();
});

test("contrôle : sans aveuglement, zéro session et zéro alerte se disent comme des mesures", async () => {
  mocked.mockResolvedValue(avecFlotte({ sessions: [], alertes: [], aveugle: [] }));
  rendre(<PilotageFlotteView />);
  await tableSessions();
  expect(screen.getByText("Aucune session vivante recensée par le tableau.")).toBeTruthy();
  expect(screen.getByText("Aucune alerte dans le tableau.")).toBeTruthy();
});

test("une charge à champs null rend quatre Stat « non mesuré » et aucun zéro", async () => {
  const base = pilotageFixture();
  mocked.mockResolvedValue(
    pilotageFixture({
      charge: { ...base.charge!, sims_en_vol: null, cpu_pct: null, bails_vivants: null, flotte_age_s: null },
    }),
  );
  const { container } = rendre(<PilotageFlotteView />);
  await tableSessions();
  const stats = [...container.querySelectorAll(".stat strong")].map((s) => s.textContent);
  expect(stats).toEqual(["non mesuré", "non mesuré", "non mesuré", "non mesuré"]);
});

test("tableau PÉRIMÉ (âge > TTL du bail pm) : dit en tête, et les sessions sont datées", async () => {
  const base = pilotageFixture();
  mocked.mockResolvedValue(pilotageFixture({ charge: { ...base.charge!, flotte_age_s: 23_312 } }));
  rendre(<PilotageFlotteView />);
  expect(await screen.findByText(/Tableau PÉRIMÉ : mesuré il y a 6,5 h/)).toBeTruthy();
  expect(screen.getByText("Sessions (à l'heure du tableau PÉRIMÉ)")).toBeTruthy();
});

test("contrôle : un tableau frais n'est PAS marqué périmé", async () => {
  rendre(<PilotageFlotteView />);
  await tableSessions();
  expect(screen.queryByText(/Tableau PÉRIMÉ/)).toBeNull();
});

test("flotte null : Empty qui reprend la ligne d'aveuglement, jamais une table vide", async () => {
  const ligne = "flotte : BOARD.json introuvable (ou JSON illisible) à C:/x/data/pm/BOARD.json";
  mocked.mockResolvedValue(pilotageFixture({ flotte: null, aveugle: [ligne] }));
  rendre(<PilotageFlotteView />);
  expect(await screen.findByText(`Flotte indisponible — ${ligne}`)).toBeTruthy();
  expect(screen.queryByRole("table")).toBeNull();
});

test("mode dégradé : alerte + Empty par bloc, rien d'inventé", async () => {
  mocked.mockResolvedValue(pilotageDegrade());
  rendre(<PilotageFlotteView />);
  expect((await screen.findByRole("alert")).textContent).toContain("pilotage: ImportError");
  expect(screen.getByText(/^Charge indisponible — pilotage: ImportError/)).toBeTruthy();
  expect(screen.getByText(/^Flotte indisponible — pilotage: ImportError/)).toBeTruthy();
});

test("backend injoignable : ErrorState avec « Réessayer », jamais une vue vide", async () => {
  mocked.mockRejectedValue(new ApiError(0, "/api/pm/pilotage", "Timeout après 10000 ms"));
  rendre(<PilotageFlotteView />);
  const alerte = await screen.findByRole("alert");
  expect(alerte.textContent).toContain("Erreur de chargement");
  expect(alerte.textContent).toContain("/api/pm/pilotage");
  expect(within(alerte).getByRole("button", { name: "Réessayer" })).toBeTruthy();
});

test("le recalcul est DÉSACTIVÉ quand le dernier tableau annonce une simulation en vol", async () => {
  const base = pilotageFixture();
  mocked.mockResolvedValue(pilotageFixture({ charge: { ...base.charge!, sims_en_vol: 2 } }));
  rendre(<PilotageFlotteView />);
  const bouton = (await screen.findByRole("button", { name: /Recalculer la flotte/ })) as HTMLButtonElement;
  expect(bouton.disabled).toBe(true);
  expect(screen.getByText(/2 simulation\(s\) en vol/)).toBeTruthy();
});

test("frais=1 : timeout > 18 s, et le recalcul PLUS RÉCENT survit au sondage suivant d'un tableau plus vieux", async () => {
  const { qc } = rendre(<PilotageFlotteView />);
  const bouton = (await screen.findByRole("button", { name: /Recalculer la flotte/ })) as HTMLButtonElement;
  expect(bouton.disabled).toBe(false);
  const base = pilotageFixture();
  const frais = avecFlotte({ generated_at: base.generated_at }, { charge: { ...base.charge!, flotte_age_s: 3 } });
  mocked.mockResolvedValueOnce(frais);
  fireEvent.click(bouton);
  await waitFor(() => expect(screen.getByText("3 s")).toBeTruthy());
  const appel = mocked.mock.calls.find((c) => c[0] === "/api/pm/pilotage?frais=1");
  expect(appel![1].timeoutMs).toBeGreaterThan(18_000);
  expect(screen.getByText(/Recalculée à la demande/)).toBeTruthy();
  // Le sondage suivant rapporte le VIEUX tableau (le serveur ne garde pas le recalcul) — avec une simulation en vol,
  // signe VISIBLE qu'il a bien été appliqué (React Query notifie après act : attendre ce signe, pas le supposer).
  mocked.mockResolvedValue(pilotageFixture({ charge: { ...base.charge!, sims_en_vol: 1 } }));
  await act(() => qc.refetchQueries({ queryKey: ["pm", "pilotage"] }));
  await waitFor(() => expect(screen.getByText(/1 simulation\(s\) en vol/)).toBeTruthy());
  expect(screen.getByText("3 s")).toBeTruthy(); // la flotte affichée reste la plus récente
});

test("un recalcul REFUSÉ par le serveur est dit à côté du bouton", async () => {
  rendre(<PilotageFlotteView />);
  const bouton = await screen.findByRole("button", { name: /Recalculer la flotte/ });
  const refus = "frais=1 refusé : 1 simulation(s) en vol d'après le dernier tableau connu";
  mocked.mockResolvedValueOnce(pilotageFixture({ aveugle: [refus] }));
  fireEvent.click(bouton);
  expect(await screen.findByText(refus, { selector: "span" })).toBeTruthy();
});

test("recalcul en échec : ErrorState ; son « Réessayer » disparaît si une simulation est désormais en vol", async () => {
  const { qc } = rendre(<PilotageFlotteView />);
  const bouton = await screen.findByRole("button", { name: /Recalculer la flotte/ });
  mocked.mockRejectedValueOnce(new ApiError(0, "/api/pm/pilotage?frais=1", "Timeout après 40000 ms"));
  fireEvent.click(bouton);
  const alerte = await screen.findByRole("alert");
  expect(alerte.textContent).toContain("Timeout après 40000 ms");
  expect(within(alerte).getByRole("button", { name: "Réessayer" })).toBeTruthy();
  const base = pilotageFixture();
  mocked.mockResolvedValue(pilotageFixture({ charge: { ...base.charge!, sims_en_vol: 1 } }));
  await act(() => qc.refetchQueries({ queryKey: ["pm", "pilotage"] }));
  await waitFor(() => expect(screen.getByText(/1 simulation\(s\) en vol/)).toBeTruthy());
  expect(within(screen.getByRole("alert")).queryByRole("button", { name: "Réessayer" })).toBeNull();
});
