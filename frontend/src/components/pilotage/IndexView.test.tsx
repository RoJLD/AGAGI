import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

vi.mock("../../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../api/client")>()),
  apiFetch: vi.fn(),
}));
import { apiFetch, ApiError } from "../../api/client";
import { IndexView } from "./IndexView";
import { indexFixture } from "./indexFixture";

const mocked = apiFetch as ReturnType<typeof vi.fn>;
function rendre(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}
beforeEach(() => mocked.mockResolvedValue(indexFixture()));
afterEach(() => {
  cleanup();
  mocked.mockReset();
});

test("table des familles : comptes, exclus, illisibles avec raison, champs introuvables par raison", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const rec = within(t).getByText("record").closest("tr")!;
  expect(within(rec).getByText("4")).toBeTruthy();
  expect(within(rec).getByText("README.md")).toBeTruthy();
  expect(within(rec).getByText(/frontmatter_yaml_invalide/)).toBeTruthy();
  expect(within(rec).getAllByText("1 (frontmatter_absent 1)")).toHaveLength(2); // titre ET état
  expect(within(rec).getByText("2 (frontmatter_absent 2)")).toBeTruthy(); // date déclarée
  expect(mocked).toHaveBeenCalledWith("/api/pm/index");
});

test("famille à répertoire absent : « inconnu », jamais 0", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const adr = within(t).getByText("adr").closest("tr")!;
  expect(within(adr).getAllByText("inconnu").length).toBeGreaterThan(0);
  expect(within(adr).queryByText("0")).toBeNull();
  expect(within(adr).queryByText("aucun")).toBeNull(); // exclus non lus : jamais « aucun » (revue du pas 1, I5)
});

test("format déclaré : un compte par clé, sans seuil ni couleur", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const rec = within(t).getByText("record").closest("tr")!;
  expect(within(rec).getByText("date 0 · etat 0 · sujet 0 · liens 0 sur 2")).toBeTruthy();
  expect(rec.querySelector(".badge")).toBeNull();
});

test("champ introuvable : « introuvable », jamais une propriété du FICHIER ; sans instantané, la date d'ajout est « inconnue »", async () => {
  // Revue finale du plan 1 (I1) : « sans titre » s'affichait pour 34 records qui ONT un titre « # » (frontmatter
  // absent) et « non déclaré » pour 16 résultats dont le verdict est un dict (type_inattendu) — l'index sait
  // seulement qu'il n'a pas TROUVÉ le champ.
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Artefacts indexés" });
  const b = within(t).getByText("docs/EDR/002_b.md").closest("tr")!;
  expect(within(b).getAllByText("introuvable")).toHaveLength(4); // titre, date déclarée, date d'ajout, état
  for (const affirme of ["sans titre", "non déclarée", "non déclaré", "sans date d'ajout"]) {
    expect(within(b).queryByText(affirme)).toBeNull();
  }
  cleanup();
  mocked.mockResolvedValue(indexFixture({ dates: null }));
  rendre(<IndexView />);
  const t2 = await screen.findByRole("table", { name: "Artefacts indexés" });
  expect(within(within(t2).getByText("docs/EDR/002_b.md").closest("tr")!).getByText("inconnue")).toBeTruthy();
});

test("instantané daté dans le FUTUR : dit, jamais ramené à « 0 s »", async () => {
  // Revue finale du plan 1 (I2) : le backend sert l'âge négatif ET une ligne ; formatAge le bornait à 0.
  mocked.mockResolvedValue(
    indexFixture({ dates: { generated_at: 1, age_s: -120, head: "abc", historique: "complet" } }),
  );
  rendre(<IndexView />);
  expect(await screen.findByText(/daté dans le futur/)).toBeTruthy();
  expect(screen.queryByText(/instantané de 0 s/)).toBeNull();
});

test("famille NON LUE choisie au filtre : dite non lue, jamais une table vide « 0 affiché(s) »", async () => {
  // Revue finale du plan 1 (I3) : adr a fichiers null ; la choisir rendait une table vide et « 0 affiché(s) ».
  rendre(<IndexView />);
  await screen.findByRole("table", { name: "Artefacts indexés" });
  expect(screen.getByText(/familles non lues : adr/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Famille"), { target: { value: "adr" } });
  expect(screen.getByText(/famille adr non lue par l'index/i)).toBeTruthy();
  expect(screen.queryByRole("table", { name: "Artefacts indexés" })).toBeNull();
  expect(screen.queryByText(/^0 affiché/)).toBeNull();
});

test("case « sans date d'ajout » : ne garde que les artefacts sans date", async () => {
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Artefacts indexés" });
  expect(within(t).getByText("docs/EDR/001_a.md")).toBeTruthy();
  fireEvent.click(screen.getByLabelText(/sans date/));
  const t2 = screen.getByRole("table", { name: "Artefacts indexés" });
  expect(within(t2).queryByText("docs/EDR/001_a.md")).toBeNull();
  expect(within(t2).getByText("docs/EDR/002_b.md")).toBeTruthy();
});

test("bloc null : l'Empty porte SA ligne, ou avoue qu'aucune ligne ne le nomme ; jamais une cause inventée", async () => {
  // Revue finale du plan 1 (M1, M2) : la règle du lot 1 (spec §3.5) — « bloc null → Empty avec SA ligne ».
  const refus = "familles : bloc refusé par le modèle de la route (x) -- servi à null, les autres blocs restent servis";
  mocked.mockResolvedValue(indexFixture({ familles: null, aveugle: [refus] }));
  rendre(<IndexView />);
  expect(await screen.findByText(/^Familles indisponibles — familles : bloc refusé/)).toBeTruthy();
  cleanup();
  mocked.mockResolvedValue(indexFixture({ familles: null, aveugle: [] }));
  rendre(<IndexView />);
  expect(await screen.findByText(/^Familles indisponibles — .*aucune ligne/)).toBeTruthy();
  cleanup();
  mocked.mockResolvedValue(indexFixture({ hors_familles: null, aveugle: ["index: RuntimeError: x"], dates: null }));
  rendre(<IndexView />);
  await screen.findByRole("alert");
  expect(screen.queryByText(/pas d'instantané git complet/)).toBeNull();
  expect(screen.getByRole("alert").textContent).toContain("quatre blocs");
});

test("compte absent d'un bloc lu : « inconnu », jamais « 0 » ni « undefined »", async () => {
  // Revue finale du plan 1 (M3) : une clé absente de champs_introuvables s'affichait « 0 », de format_declare « undefined ».
  const f = indexFixture();
  const rec = {
    ...f.familles![0],
    champs_introuvables: { titre: { frontmatter_absent: 1 } },
    format_declare: { fichiers: 2 },
  };
  mocked.mockResolvedValue({ ...f, familles: [rec] });
  rendre(<IndexView />);
  const t = await screen.findByRole("table", { name: "Familles d'artefacts" });
  const ligne = within(t).getByText("record").closest("tr")!;
  expect(within(ligne).getAllByText("inconnu").length).toBeGreaterThanOrEqual(3); // date déclarée, état, date d'ajout
  expect(ligne.textContent).not.toContain("undefined");
});

test("dates : âge et état de l'historique publiés ; instantané absent → dit, pas de date inventée", async () => {
  rendre(<IndexView />);
  expect(await screen.findByText(/historique complet, instantané de 10 min/)).toBeTruthy();
  cleanup();
  const ligne = "dates : DATES_GIT.json introuvable à C:/x/data/pm/DATES_GIT.json -- écrivain jamais passé";
  mocked.mockResolvedValue(indexFixture({ dates: null, hors_familles: null, aveugle: [ligne] }));
  rendre(<IndexView />);
  expect(await screen.findByText(/Dates d'ajout indisponibles/)).toBeTruthy();
  expect(screen.getByText(/Fichiers hors familles : inconnus/)).toBeTruthy();
  expect(screen.getByRole("status").textContent).toContain(ligne);
});

test("hors familles : le compte et ses répertoires", async () => {
  rendre(<IndexView />);
  expect(await screen.findByText("12 fichier(s) suivi(s) hors familles : docs/roadmap 10 · docs/specs 2")).toBeTruthy();
});

test("filtre de famille et de texte ; au-delà de la limite, la coupe est DITE", async () => {
  const beaucoup = Array.from({ length: 305 }, (_, i) => ({
    ...indexFixture().artefacts![0],
    chemin: `docs/EDR/${i}.md`,
  }));
  mocked.mockResolvedValue(indexFixture({ artefacts: beaucoup }));
  rendre(<IndexView />);
  // Revue finale du plan 1 (M6) : le dénominateur nomme ce qu'il compte (retenus par le filtre / indexés).
  expect(await screen.findByText(/^300 affiché\(s\) sur 305 retenu\(s\) par le filtre — affinez-le/)).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Texte"), { target: { value: "docs/EDR/12" } });
  expect(screen.getByText(/retenu\(s\) par le filtre sur 305 artefact\(s\) indexé\(s\)/)).toBeTruthy();
});

test("mode dégradé : alerte + Empty ; backend injoignable : ErrorState", async () => {
  mocked.mockResolvedValue(
    indexFixture({
      aveugle: ["index: ImportError: No module named 'yaml'"],
      dates: null,
      familles: null,
      hors_familles: null,
      artefacts: null,
    }),
  );
  rendre(<IndexView />);
  expect((await screen.findByRole("alert")).textContent).toContain("index: ImportError");
  expect(screen.getByText(/^Familles indisponibles — index: ImportError/)).toBeTruthy();
  cleanup();
  mocked.mockRejectedValue(new ApiError(0, "/api/pm/index", "Timeout après 10000 ms"));
  rendre(<IndexView />);
  expect((await screen.findByRole("alert")).textContent).toContain("Erreur de chargement");
});
