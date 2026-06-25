# Carnet de labo / annotations (design)

Date : 2026-06-25
Vague : H (pistes net-new) — item H4
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Les runs portent provenance, KPIs et liens (EDR, articles), mais **aucun moyen d'annoter** : pas de
place pour consigner une observation (« seed 3 a divergé », « à recroiser avec EDR 099 »). La
capitalisation de la recherche se perd hors du dépôt.

## Objectif

Un **carnet de labo** : notes **horodatées append-only** attachées aux runs. On **écrit** les notes
là où on voit le run (Historique des runs), on **lit** le journal chronologique inter-runs dans un
nouvel onglet **Carnet**. Deep-link Carnet → run.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Modèle | Journal **append-only horodaté** (pas de champ écrasable). Une note = `{id, text, ts}`. |
| Cible | **Runs** uniquement v1 (l'unité déjà reliée). EDR/conditions/articles différés. |
| Écriture | Inline dans `RunsHistoryView` (panneau de détail du run sélectionné) : ajout + suppression par note. |
| Lecture | Onglet **Carnet** (famille Connaissance) : flux chronologique read-only inter-runs + deep-link run. |
| Store | `results/run_notes.json` = `{run_id: [{id, text, ts}]}`, même moule que `run_links.json`. |
| Backend | Patch-and-handoff vers `feat/d1-prod-pairing` (comme `/api/runs/distributions` #59). |

## Architecture

### 1. Backend — store + endpoints (PR séparée dans `feat/d1-prod-pairing`)

Store JSON `results/run_notes.json`, robuste au manquant/corrompu (pattern `_load_links`).

- `backend/app/schemas.py` :
  ```python
  class RunNote(BaseModel):
      id: str
      text: str
      ts: str          # ISO 8601 UTC

  class NoteCreate(BaseModel):
      text: str

  class NoteFeedItem(BaseModel):
      run_id: str
      run_name: str
      id: str
      text: str
      ts: str
  ```
- `runs_service` (nouveau store) :
  - `list_notes(run_id) -> list[dict]` : notes du run, triées par `ts` croissant.
  - `add_note(run_id, text) -> dict` : `text` strippé non vide requis ; `id = uuid4().hex[:8]`,
    `ts = datetime.now(timezone.utc).isoformat()` ; append + save ; renvoie la note créée.
  - `delete_note(run_id, note_id) -> bool` : retire la note ; save ; renvoie True si retirée.
  - `all_notes() -> list[dict]` : aplatit toutes les notes, attache `run_name` (map `run_id→name` via
    `_scan`), triées par `ts` **décroissant**.
- `backend/app/routes/runs.py` :
  - `GET /api/runs/{run_id}/notes` → `list[RunNote]`.
  - `POST /api/runs/{run_id}/notes` (body `NoteCreate`) → `RunNote` ; 400 si `text` vide.
  - `DELETE /api/runs/{run_id}/notes/{note_id}` → 404 si absente, sinon `{deleted: true}`.
  - `GET /api/notes` → `list[NoteFeedItem]` (flux agrégé).
- `tests/test_backend.py` (à la racine du dépôt) : roundtrip (add → list → delete), `text` vide rejeté (400),
  agrégat `all_notes` trié décroissant avec `run_name`.
- Régénérer `frontend/openapi.json` + `frontend/src/api/schema.ts` (drift gate).

> Les mutations passent par le gate token API existant (cf. PATCH `/links`) — aucun traitement
> spécial frontend (apiFetch ajoute `Authorization` si `VITE_API_TOKEN`).

### 2. Frontend — types & clés

- `frontend/src/types.ts` :
  ```ts
  export interface RunNote { id: string; text: string; ts: string }
  export interface NoteFeedItem extends RunNote { run_id: string; run_name: string }
  ```
- `frontend/src/api/queryKeys.ts` : `runs.notes: (runId: string) => ["runs", "notes", runId] as const`
  et clé de flux `notes: ["notes"] as const`.

### 3. `components/RunNotes.tsx` (inline, écriture)

Composant autonome `RunNotes({ runId }: { runId: string })` :
- `useQuery(queryKeys.runs.notes(runId), () => apiFetch<RunNote[]>(`/api/runs/${enc}/notes`))`.
- Add : `useMutation` POST `{text}` → `onSuccess` invalide `runs.notes(runId)` + `notes` + `notify(...)`.
- Delete : `useMutation` DELETE → invalide idem.
- Rendu : titre « Carnet », liste horodatée (`new Date(ts).toLocaleString()` + texte + bouton
  supprimer par note), `<textarea>` + bouton « Ajouter » (désactivé si vide ou mutation en cours).
- États : liste vide → « Aucune note pour ce run. » ; erreur de chargement → message inline discret
  (la dégradation jusqu'à propagation backend reste douce). Utilise `useToast`, `Button`, `Field`.

### 4. Intégration `RunsHistoryView`

- Importer `useHashRoute` : `const { query } = useHashRoute(TAB_KEYS, "runs")` ; initialiser
  `selected` depuis `query.run` (`useState<string | null>(query.run || null)`) → deep-link Carnet→run
  ouvre directement le détail (le changement d'onglet remonte la vue, l'état initial capte `query.run`).
- Dans le panneau de détail (`selected`), après la section « Articles Sociologue liés », rendre
  `<RunNotes runId={selected} />`.

### 5. `components/CarnetView.tsx` + onglet (lecture)

- `useQuery(queryKeys.notes, () => apiFetch<NoteFeedItem[]>("/api/notes"))`.
- États Loading / ErrorState(onRetry) / Empty (« Aucune note. Annote des runs depuis l'Historique. »).
- Rendu : flux chronologique (déjà trié décroissant) — par item : date, `run_name`, texte, lien
  « → run » qui appelle `navigate("runs", { run: item.run_id })` (via `useHashRoute(TAB_KEYS,
  "carnet").navigate`, pattern ProvenanceView).
- `tabs.ts` : clé `"carnet"` famille **Connaissance** (icône lucide `NotebookPen`). `App.tsx` : lazy
  `CarnetView` + branche `tab === "carnet"`. Hors `showSidebar`.

## Tests

- Backend (`test_backend.py`) : add→list→delete roundtrip ; `text` vide → 400 ; `all_notes` agrégé
  trié décroissant + `run_name` correct ; delete d'une note absente → 404.
- `RunNotes.test.tsx` : liste vide (message) ; rendu d'une note (date + texte) ; ajout (mock POST →
  invalidation/refetch → note visible) ; suppression. Mock `apiFetch` + wrapper QueryClient + mock
  `useToast`.
- `RunsHistoryView.test.tsx` (existant, étendre) : `query.run` ouvre le détail du run (deep-link) —
  mock `useHashRoute` renvoyant `{ query: { run: <id> }, … }`.
- `CarnetView.test.tsx` : Loading ; Empty ; rendu du flux (fixture) ; clic « → run » appelle
  `navigate("runs", { run })` (mock du hook / spy).

## Risques

- **Propagation backend** : tant que les endpoints notes ne sont pas sur `main`, GET 404 → liste
  vide/erreur douce, POST échoue → toast d'erreur. Dégradation propre, identique à Cohorte.
- **`ts` & repro** : le store notes est hors boucle sim (aucun impact reproductibilité KuzuDB). `ts`
  stampé backend ; tests assertent forme/ordre, pas la valeur exacte.
- **Deep-link sans remount** : si l'utilisateur est déjà sur l'onglet runs, `navigate` depuis le
  Carnet change l'onglet (remonte la vue) → l'état initial capte `query.run`. Couvert par le fait que
  `App` rend conditionnellement chaque vue.
- **Coordination** : frontend = `frontend/src/**` + `docs/**` ; backend = PR séparée dans
  `feat/d1-prod-pairing`. Aucun conflit.

## Non-objectifs (YAGNI v1)

- Notes sur EDR / conditions / articles.
- Édition d'une note en place (on supprime + réajoute).
- Markdown riche, pièces jointes, tags, recherche/filtre dans le Carnet.
- Auteur/multi-utilisateur (mono-utilisateur local).

## Périmètre des fichiers

Frontend (→ `main`) — Créés : `components/RunNotes.tsx` (+ test), `components/CarnetView.tsx`
(+ test). Modifiés : `types.ts`, `api/queryKeys.ts`, `components/RunsHistoryView.tsx` (+ test étendu),
`tabs.ts`, `App.tsx`.
Backend (→ `feat/d1-prod-pairing`) : `backend/app/schemas.py`, `backend/app/services/runs_service.py`,
`backend/app/routes/runs.py`, `tests/test_backend.py` (racine), régén `frontend/openapi.json` +
`frontend/src/api/schema.ts`.

## Suite

Plan d'implémentation via `writing-plans`, tâches TDD :
(1) types + queryKeys ;
(2) `RunNotes` (query + mutations add/delete) ;
(3) intégration `RunsHistoryView` + deep-link `query.run` ;
(4) `CarnetView` + onglet + lazy ;
(5) backend store + 4 endpoints (patch-and-handoff d1).
Chacune testée.
