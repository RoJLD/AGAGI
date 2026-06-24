# Accessibilité + cohérence des états + typage d3 (G4) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clore la Vague G : navigation accessible (pattern tablist WAI-ARIA via une primitive partagée), uniformisation des états Loading/Error/Empty + association des labels de formulaire, suppression des `any` d3, et nettoyage de la dette reportée.

**Architecture:** Une primitive `TabList` accessible (roles ARIA + roving tabindex + flèches + activation manuelle) est extraite, puis consommée par la nav globale (`App.tsx`) ET `StepBar`. Les états ad hoc sont remplacés par les primitives existantes ; `Field` associe son label via `useId`. Le typage d3 suit le modèle déjà en place dans `TopologyViewer`. Aucun changement de comportement fonctionnel (hors a11y/clavier), aucun nouvel endpoint backend.

**Tech Stack:** React 18, TypeScript (strict), Vite, @tanstack/react-query v5, d3 v7, lucide-react, Vitest + @testing-library/react.

## Global Constraints

- TypeScript `strict: true` — aucun `any` introduit (l'objectif de la grappe C est d'en RETIRER).
- Communication/copie UI en **français** ; labels a11y en français.
- Réutiliser les primitives existantes (`Loading`, `Empty`, `ErrorState`, `Button`, `Field`) et les tokens CSS (`var(--...)`) — pas de couleurs en dur.
- Activation clavier des onglets : **manuelle** (flèches = focus ; Entrée/Espace/clic = activation).
- Tests **restent exclus** du tsconfig (`exclude` inchangé).
- Périmètre strictement `frontend/src/**` (+ ce plan / `styles.css` / `vite.config.ts`). Commits path-scopés.
- Chaque commit termine par : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Test : `npm --prefix frontend run test -- <fichier>` (vitest run filtré). Build : `npm --prefix frontend run build`.
- Branche : `feat/frontend-g4-a11y` (déjà créée).

---

## File Structure

Créés :
- `frontend/src/components/ui/Tabs.tsx` — primitive `TabList` accessible + helpers `tabId`/`panelId`.
- `frontend/src/components/ui/Tabs.test.tsx`
- `frontend/src/components/ui/Field.test.tsx`

Modifiés :
- `frontend/src/tabs.ts` — helper `buildNavItems(families)` + export.
- `frontend/src/App.tsx` — nav → `TabList`, `<section>` → `role="tabpanel"`.
- `frontend/src/components/parcours/StepBar.tsx` — réimplémenté sur `TabList`.
- `frontend/src/components/ui/Field.tsx` — association `useId`.
- `frontend/src/components/AcademyView.tsx`, `EvolutionView.tsx`, `TopologyView.tsx` — états → primitives.
- `frontend/src/components/TimelineViewer.tsx`, `TopologyViewer.tsx` — typage d3.
- `frontend/src/components/GateSidebar.tsx` — suppression `bestRobustGate`.
- `frontend/src/styles.css` — styles `.tab-list`/`.tab` + `.step-pill--done` distinct.
- `frontend/vite.config.ts` (best-effort warning Node).

---

## Task 1: Primitive `TabList` accessible

**Files:**
- Create: `frontend/src/components/ui/Tabs.tsx`
- Test: `frontend/src/components/ui/Tabs.test.tsx`

**Interfaces:**
- Consumes: rien (lucide `LucideIcon` type only).
- Produces:
  - `interface TabItem { id: string; label: string; icon?: LucideIcon; group?: string; state?: "active" | "done" | "todo"; }`
  - `tabId(id: string): string` → `tab-${id}` ; `panelId(id: string): string` → `panel-${id}`
  - `TabList(props: { items: TabItem[]; activeId: string; onSelect: (id: string) => void; ariaLabel: string; orientation?: "horizontal" | "vertical"; renderLabel?: (item: TabItem, index: number) => ReactNode; testIdPrefix?: string; className?: string }): JSX.Element`
  - Chaque tab : `data-testid={`${testIdPrefix ?? "tab"}-${id}`}`, `role="tab"`, `id={tabId(id)}`, `aria-selected`, `aria-controls={panelId(id)}`, `tabIndex` roving.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/ui/Tabs.test.tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { afterEach, test, expect, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import { TabList, tabId, panelId } from "./Tabs";

afterEach(() => cleanup());

const ITEMS = [
  { id: "a", label: "Un" },
  { id: "b", label: "Deux" },
  { id: "c", label: "Trois" },
];

test("rend un tablist avec aria-selected et roving tabindex", () => {
  render(<TabList items={ITEMS} activeId="b" onSelect={() => {}} ariaLabel="Sections" />);
  expect(screen.getByRole("tablist").getAttribute("aria-label")).toBe("Sections");
  const tabs = screen.getAllByRole("tab");
  expect(tabs).toHaveLength(3);
  expect(screen.getByTestId("tab-b").getAttribute("aria-selected")).toBe("true");
  expect(screen.getByTestId("tab-b").getAttribute("tabindex")).toBe("0");
  expect(screen.getByTestId("tab-a").getAttribute("tabindex")).toBe("-1");
  expect(screen.getByTestId("tab-b").getAttribute("aria-controls")).toBe(panelId("b"));
});

test("flèches déplacent le focus (avec wrap) sans activer", () => {
  const onSelect = vi.fn();
  render(<TabList items={ITEMS} activeId="a" onSelect={onSelect} ariaLabel="Sections" />);
  const first = screen.getByTestId("tab-a");
  first.focus();
  fireEvent.keyDown(first, { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-b"));
  // wrap depuis le dernier
  screen.getByTestId("tab-c").focus();
  fireEvent.keyDown(screen.getByTestId("tab-c"), { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-a"));
  // activation manuelle : déplacer le focus n'a pas sélectionné
  expect(onSelect).not.toHaveBeenCalled();
});

test("Home/End vont aux extrémités", () => {
  render(<TabList items={ITEMS} activeId="b" onSelect={() => {}} ariaLabel="Sections" />);
  const mid = screen.getByTestId("tab-b");
  mid.focus();
  fireEvent.keyDown(mid, { key: "End" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-c"));
  fireEvent.keyDown(screen.getByTestId("tab-c"), { key: "Home" });
  expect(document.activeElement).toBe(screen.getByTestId("tab-a"));
});

test("Entrée, Espace et clic activent l'onglet", () => {
  const onSelect = vi.fn();
  render(<TabList items={ITEMS} activeId="a" onSelect={onSelect} ariaLabel="Sections" />);
  fireEvent.keyDown(screen.getByTestId("tab-b"), { key: "Enter" });
  fireEvent.keyDown(screen.getByTestId("tab-c"), { key: " " });
  fireEvent.click(screen.getByTestId("tab-b"));
  expect(onSelect.mock.calls.map((c) => c[0])).toEqual(["b", "c", "b"]);
});

test("testIdPrefix personnalise les data-testid", () => {
  render(<TabList items={ITEMS} activeId="a" onSelect={() => {}} ariaLabel="Étapes" testIdPrefix="step" />);
  expect(screen.getByTestId("step-a")).toBeTruthy();
  expect(tabId("a")).toBe("tab-a");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/ui/Tabs.test.tsx`
Expected: FAIL — `./Tabs` n'existe pas.

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/src/components/ui/Tabs.tsx
import { useRef, type KeyboardEvent, type ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  group?: string;
  state?: "active" | "done" | "todo";
}

export const tabId = (id: string): string => `tab-${id}`;
export const panelId = (id: string): string => `panel-${id}`;

interface TabListProps {
  items: TabItem[];
  activeId: string;
  onSelect: (id: string) => void;
  ariaLabel: string;
  orientation?: "horizontal" | "vertical";
  renderLabel?: (item: TabItem, index: number) => ReactNode;
  testIdPrefix?: string;
  className?: string;
}

/** Liste d'onglets accessible (WAI-ARIA tablist) : roving tabindex, navigation
 *  aux flèches/Home/End, activation MANUELLE (Entrée/Espace/clic). Partagée par
 *  la nav globale et le StepBar du Parcours. Le panneau (role=tabpanel) est câblé
 *  par le consommateur via panelId(activeId)/tabId(activeId). */
export function TabList({
  items,
  activeId,
  onSelect,
  ariaLabel,
  orientation = "horizontal",
  renderLabel,
  testIdPrefix = "tab",
  className,
}: TabListProps) {
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const focusAt = (i: number) => {
    const n = items.length;
    if (!n) return;
    const idx = ((i % n) + n) % n; // wrap circulaire
    btnRefs.current[idx]?.focus();
  };

  const onKeyDown = (e: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const nextKey = orientation === "horizontal" ? "ArrowRight" : "ArrowDown";
    const prevKey = orientation === "horizontal" ? "ArrowLeft" : "ArrowUp";
    if (e.key === nextKey) {
      e.preventDefault();
      focusAt(index + 1);
    } else if (e.key === prevKey) {
      e.preventDefault();
      focusAt(index - 1);
    } else if (e.key === "Home") {
      e.preventDefault();
      focusAt(0);
    } else if (e.key === "End") {
      e.preventDefault();
      focusAt(items.length - 1);
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(items[index].id);
    }
  };

  return (
    <div
      className={`tab-list${className ? ` ${className}` : ""}`}
      role="tablist"
      aria-label={ariaLabel}
      aria-orientation={orientation}
    >
      {items.map((item, index) => {
        const isActive = item.id === activeId;
        const prevGroup = index > 0 ? items[index - 1].group : undefined;
        const startsGroup = item.group !== undefined && index > 0 && item.group !== prevGroup;
        const Icon = item.icon;
        return (
          <button
            key={item.id}
            ref={(el) => {
              btnRefs.current[index] = el;
            }}
            role="tab"
            id={tabId(item.id)}
            aria-selected={isActive}
            aria-controls={panelId(item.id)}
            tabIndex={isActive ? 0 : -1}
            data-testid={`${testIdPrefix}-${item.id}`}
            data-group-start={startsGroup || undefined}
            className={`tab${isActive ? " active" : ""}${item.state ? ` is-${item.state}` : ""}`}
            onClick={() => onSelect(item.id)}
            onKeyDown={(e) => onKeyDown(e, index)}
          >
            {renderLabel ? (
              renderLabel(item, index)
            ) : (
              <>
                {Icon ? <Icon size={16} /> : null}
                {item.label}
              </>
            )}
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/ui/Tabs.test.tsx`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/Tabs.tsx frontend/src/components/ui/Tabs.test.tsx
git commit -m "feat(G4): primitive TabList accessible (roving tabindex, flèches, activation manuelle)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Migrer la nav globale d'`App.tsx` sur `TabList` + `tabpanel`

**Files:**
- Modify: `frontend/src/tabs.ts` (helper `buildNavItems`)
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/tabs.test.tsx` (créé)

**Interfaces:**
- Consumes: `TabList`, `tabId`, `panelId`, `TabItem` (Task 1) ; `TAB_FAMILIES` (existant).
- Produces: `buildNavItems(families: TabFamily[]): TabItem[]` dans `tabs.ts`.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/tabs.test.tsx
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
  expect(typeof parcours.icon).toBe("function");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/tabs.test.tsx`
Expected: FAIL — `buildNavItems` n'est pas exporté.

- [ ] **Step 3: Ajouter `buildNavItems` dans `tabs.ts`**

Ajouter l'import du type et la fonction (en bas de `frontend/src/tabs.ts`) :

```ts
import type { TabItem } from "./components/ui/Tabs";

/** Aplatit les familles d'onglets en items pour la primitive TabList (group = nom de famille). */
export function buildNavItems(families: TabFamily[]): TabItem[] {
  return families.flatMap((fam) =>
    fam.tabs.map((t) => ({ id: t.key, label: t.label, icon: t.icon, group: fam.family })),
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/tabs.test.tsx`
Expected: PASS.

- [ ] **Step 5: Brancher `TabList` + tabpanel dans `App.tsx`**

Remplacer l'import et la nav. En tête, ajouter aux imports :

```tsx
import { TabList, tabId, panelId } from "./components/ui/Tabs";
import { TAB_KEYS, TAB_FAMILIES, buildNavItems } from "./tabs";
```

Remplacer le bloc `<nav className="tabs">…</nav>` ([App.tsx:41-57](frontend/src/App.tsx#L41-L57)) par :

```tsx
          <TabList
            items={buildNavItems(TAB_FAMILIES)}
            activeId={tab}
            onSelect={(id) => setTab(id as (typeof TAB_KEYS)[number])}
            ariaLabel="Sections du dashboard"
            className="tabs"
          />
```

Transformer la zone de contenu en panneau : remplacer `<section className="panel">` ([App.tsx:64](frontend/src/App.tsx#L64)) par :

```tsx
        <section
          className="panel"
          role="tabpanel"
          id={panelId(tab)}
          aria-labelledby={tabId(tab)}
          tabIndex={0}
        >
```

(Laisser inchangés : `ErrorBoundary key={tab}`, `Suspense`, et toutes les branches `{tab === "…" && …}`.)

- [ ] **Step 6: Vérifier build + suite**

Run: `npm --prefix frontend run build`
Expected: build OK.

Run: `npm --prefix frontend run test -- src/tabs.test.tsx`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/tabs.ts frontend/src/tabs.test.tsx frontend/src/App.tsx
git commit -m "feat(G4): nav globale sur TabList accessible + zone de contenu role=tabpanel

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Réimplémenter `StepBar` sur `TabList`

**Files:**
- Modify: `frontend/src/components/parcours/StepBar.tsx`
- Test: `frontend/src/components/parcours/StepBar.test.tsx` (existant — garder vert + 1 ajout)

**Interfaces:**
- Consumes: `TabList`, `TabItem` (Task 1) ; `STEP_ORDER`, `ParcoursStep` (existant).
- Produces: `StepBar` (signature inchangée : `{ current, reached, onSelect }`).

Contexte : la signature publique de `StepBar` ne change pas ; seule l'implémentation passe par `TabList`. Les `data-testid="step-<id>"` et `aria-selected` doivent être préservés (via `testIdPrefix="step"`). Le rendu pastille (index + libellé) passe par `renderLabel`.

- [ ] **Step 1: Ajouter le test de non-régression clavier (failing)**

Ajouter à `frontend/src/components/parcours/StepBar.test.tsx` :

```tsx
import { fireEvent } from "@testing-library/react";

test("roving tabindex : l'étape courante est focusable, les autres non", () => {
  render(<StepBar current="suivre" reached={{ lancer: true, suivre: true, comparer: false, conclure: false }} onSelect={() => {}} />);
  expect(screen.getByTestId("step-suivre").getAttribute("tabindex")).toBe("0");
  expect(screen.getByTestId("step-lancer").getAttribute("tabindex")).toBe("-1");
});

test("flèche droite déplace le focus sans activer (activation manuelle)", () => {
  const onSelect = vi.fn();
  render(<StepBar current="lancer" reached={{ lancer: true, suivre: false, comparer: false, conclure: false }} onSelect={onSelect} />);
  const first = screen.getByTestId("step-lancer");
  first.focus();
  fireEvent.keyDown(first, { key: "ArrowRight" });
  expect(document.activeElement).toBe(screen.getByTestId("step-suivre"));
  expect(onSelect).not.toHaveBeenCalled();
});
```

(Le fichier importe déjà `render`, `screen`, `vi`. Ajouter `fireEvent` à l'import `@testing-library/react` s'il manque.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/parcours/StepBar.test.tsx`
Expected: FAIL — l'implémentation actuelle n'a ni roving tabindex ni navigation flèches.

- [ ] **Step 3: Réimplémenter `StepBar` sur `TabList`**

Remplacer tout le contenu de `frontend/src/components/parcours/StepBar.tsx` par :

```tsx
import { TabList, type TabItem } from "../ui/Tabs";
import { STEP_ORDER, type ParcoursStep } from "./steps";

const LABELS: Record<ParcoursStep, string> = {
  lancer: "Lancer",
  suivre: "Suivre",
  comparer: "Comparer",
  conclure: "Conclure",
};

/** Barre d'étapes du parcours — souple : toutes cliquables. Construite sur la
 *  primitive TabList (roles tablist/tab, roving tabindex, flèches, activation
 *  manuelle). Conserve les data-testid `step-<id>` et le visuel pastille. */
export function StepBar({
  current,
  reached,
  onSelect,
}: {
  current: ParcoursStep;
  reached: Record<ParcoursStep, boolean>;
  onSelect: (s: ParcoursStep) => void;
}) {
  const items: TabItem[] = STEP_ORDER.map((s) => ({
    id: s,
    label: LABELS[s],
    state: s === current ? "active" : reached[s] ? "done" : "todo",
  }));

  return (
    <TabList
      items={items}
      activeId={current}
      onSelect={(id) => onSelect(id as ParcoursStep)}
      ariaLabel="Étapes du parcours"
      className="step-bar"
      testIdPrefix="step"
      renderLabel={(item, index) => (
        <>
          <span className="step-pill__index">{index + 1}</span>
          {item.label}
        </>
      )}
    />
  );
}
```

- [ ] **Step 4: Run tests (StepBar + ParcoursView non-régression)**

Run: `npm --prefix frontend run test -- src/components/parcours/StepBar.test.tsx src/components/parcours/ParcoursView.test.tsx`
Expected: PASS (anciens tests `aria-selected`/`onSelect`/testid + nouveaux clavier).

- [ ] **Step 5: Adapter le CSS pastille (porter `.step-pill` sur `.tab`)**

Dans `frontend/src/styles.css`, les boutons sont maintenant `.tab` à l'intérieur de `.tab-list.step-bar`. Mettre à jour les sélecteurs `.step-pill*` pour cibler `.step-bar .tab` (état via `.is-active`/`.is-done`/`.is-todo`). Remplacer le bloc `.step-pill { … }` / `.step-pill--active` / `.step-pill--done` existant par :

```css
/* StepBar bâti sur .tab (TabList) : styles pastille portés sur .step-bar .tab */
.step-bar .tab {
  gap: var(--space-2);
}
.step-bar .tab.is-done {
  color: var(--color-text);
}
.step-bar .tab.is-active .step-pill__index {
  background: var(--color-accent);
  color: var(--color-bg);
}
```

(La règle `.step-pill__index` de base — cercle d'index — est conservée ; on remplace seulement les variantes d'état `--active`/`--done`/`--todo` par les classes `.is-*`. Le traitement distinct de l'état « done » est finalisé en Task 7.)

- [ ] **Step 6: Run build**

Run: `npm --prefix frontend run build`
Expected: build OK.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/parcours/StepBar.tsx frontend/src/components/parcours/StepBar.test.tsx frontend/src/styles.css
git commit -m "refactor(G4): StepBar bâti sur la primitive TabList (clavier APG partagé)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Association label↔contrôle dans `Field`

**Files:**
- Modify: `frontend/src/components/ui/Field.tsx`
- Test: `frontend/src/components/ui/Field.test.tsx` (créé)

**Interfaces:**
- Consumes: rien de nouveau.
- Produces: `Field` (signature publique inchangée) qui associe désormais son `<label>` à l'enfant unique via un id généré.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/src/components/ui/Field.test.tsx
import { render, screen } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { cleanup } from "@testing-library/react";
import { Field } from "./Field";

afterEach(() => cleanup());

test("associe le label à l'input via un id généré", () => {
  render(
    <Field label="Graine">
      <input type="number" />
    </Field>,
  );
  // getByLabelText ne réussit que si label.htmlFor === input.id
  const input = screen.getByLabelText("Graine");
  expect(input.tagName).toBe("INPUT");
});

test("respecte un id fourni par l'appelant", () => {
  render(
    <Field label="Script" htmlFor="my-id">
      <select id="my-id">
        <option>a</option>
      </select>
    </Field>,
  );
  const select = screen.getByLabelText("Script");
  expect(select.getAttribute("id")).toBe("my-id");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/ui/Field.test.tsx`
Expected: FAIL — le 1er test échoue (label non associé : `htmlFor` undefined, input sans id).

- [ ] **Step 3: Write implementation**

Remplacer le contenu de `frontend/src/components/ui/Field.tsx` par :

```tsx
import { cloneElement, isValidElement, useId, type ReactNode } from "react";

interface FieldProps {
  label: string;
  hint?: string;
  htmlFor?: string;
  children: ReactNode;
}

/** Libellé + champ (input/select fourni en children) + indice optionnel.
 *  Associe le label au contrôle : si l'appelant ne fournit pas d'id, on en
 *  génère un (useId) et on l'injecte dans l'enfant unique. */
export function Field({ label, hint, htmlFor, children }: FieldProps) {
  const generatedId = useId();
  // id effectif : priorité à htmlFor explicite, puis id de l'enfant, puis généré.
  const childId =
    isValidElement(children) && typeof children.props.id === "string" ? (children.props.id as string) : undefined;
  const controlId = htmlFor ?? childId ?? generatedId;

  // Injecte l'id dans l'enfant unique s'il n'en a pas déjà un.
  const control =
    isValidElement(children) && !childId ? cloneElement(children, { id: controlId }) : children;

  return (
    <div className="field">
      <label className="field-label" htmlFor={controlId}>
        {label}
      </label>
      {control}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend run test -- src/components/ui/Field.test.tsx`
Expected: PASS (2 tests).

- [ ] **Step 5: Vérifier build + non-régression (RunLauncher utilise Field)**

Run: `npm --prefix frontend run build`
Expected: build OK.

Run: `npm --prefix frontend run test -- src/components/parcours/steps.test.tsx`
Expected: PASS (RunLauncher rendu via StepLancer — pas de régression).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ui/Field.tsx frontend/src/components/ui/Field.test.tsx
git commit -m "feat(G4): Field associe le label au contrôle (useId + id injecté)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Uniformiser les états Loading/Error/Empty (3 vues)

**Files:**
- Modify: `frontend/src/components/AcademyView.tsx`
- Modify: `frontend/src/components/EvolutionView.tsx`
- Modify: `frontend/src/components/TopologyView.tsx`
- Test: les tests existants `AcademyView.test.tsx` / `EvolutionView.test.tsx` / `TopologyView.test.tsx` (garder verts) + 1 assertion Loading.

**Interfaces:**
- Consumes: `Loading`, `ErrorState`, `Empty` (existants).
- Produces: rien (comportement d'affichage uniformisé).

Contexte : les 3 vues affichent un `<p>Chargement…</p>` ad hoc en repli de `data ?`, ce qui conflate chargement / erreur / absence. On expose `isLoading`/`error`/`refetch` et on route vers les primitives. EvolutionView/TopologyView dépendent d'un `gate` (query `enabled: !!gate`) : sans gate sélectionnée, afficher un `Empty` explicite plutôt que « Chargement… ».

- [ ] **Step 1: Write the failing test (AcademyView Loading)**

Ajouter à `frontend/src/components/AcademyView.test.tsx` (créer le bloc s'il manque ; le fichier existe) :

```tsx
test("affiche l'état Loading pendant le chargement", () => {
  (apiFetch as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {})); // jamais résolu
  renderWithClient(<AcademyView />);
  expect(screen.getByText(/Chargement des contenus Academy/)).toBeTruthy();
  expect(screen.getByRole("status")).toBeTruthy(); // primitive Loading
});
```

(Adapter `renderWithClient`/`apiFetch` au harnais existant du fichier — il mocke déjà `../api/client`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend run test -- src/components/AcademyView.test.tsx`
Expected: FAIL — l'ancien repli est un `<p>` sans `role="status"`.

- [ ] **Step 3: AcademyView → primitives**

Dans `frontend/src/components/AcademyView.tsx` : exposer l'état de la query et router. Remplacer la destructuration ([AcademyView.tsx:7-11](frontend/src/components/AcademyView.tsx#L7-L11)) par :

```tsx
  const { data: academy = null, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.academy,
    queryFn: () => apiFetch<AcademyPayload>("/api/academy"),
    staleTime: Infinity,
  });
```

Ajouter l'import en tête : `import { Loading } from "./ui/Loading"; import { ErrorState } from "./ui/ErrorState";`.
Remplacer le repli `) : (<p>Chargement des contenus Academy...</p>)}` ([AcademyView.tsx:45-47](frontend/src/components/AcademyView.tsx#L45-L47)) par :

```tsx
      ) : isLoading ? (
        <Loading label="Chargement des contenus Academy…" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <Loading label="Chargement des contenus Academy…" />
      )}
```

- [ ] **Step 4: EvolutionView → primitives (avec garde gate)**

Dans `frontend/src/components/EvolutionView.tsx` : exposer l'état ([EvolutionView.tsx:16-20](frontend/src/components/EvolutionView.tsx#L16-L20)) :

```tsx
  const { data: detail = null, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.experiments.detail(gate),
    queryFn: () => apiFetch<ExperimentDetail>(`/api/experiments/${gate}`),
    enabled: !!gate,
  });
```

Ajouter imports `Loading`, `ErrorState`, `Empty`. Remplacer le repli `) : (<p>Chargement des données...</p>)}` ([EvolutionView.tsx:46-48](frontend/src/components/EvolutionView.tsx#L46-L48)) par :

```tsx
      ) : !gate ? (
        <Empty message="Sélectionne une porte dans la barre latérale pour voir son évolution." />
      ) : isLoading ? (
        <Loading label="Chargement des données d'évolution…" />
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : (
        <Empty message="Aucune donnée d'évolution pour cette porte." />
      )}
```

- [ ] **Step 5: TopologyView → primitives (avec garde gate)**

Dans `frontend/src/components/TopologyView.tsx` : exposer l'état ([TopologyView.tsx:11-15](frontend/src/components/TopologyView.tsx#L11-L15)) :

```tsx
  const { data: detail = null, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.experiments.detail(gate),
    queryFn: () => apiFetch<ExperimentDetail>(`/api/experiments/${gate}`),
    enabled: !!gate,
  });
```

Ajouter imports `Loading`, `ErrorState`, `Empty`. Remplacer le repli de l'analyse `) : (<p>Chargement de l'analyse...</p>)}` ([TopologyView.tsx:36-38](frontend/src/components/TopologyView.tsx#L36-L38)) par :

```tsx
          ) : !gate ? (
            <Empty message="Sélectionne une porte pour voir l'analyse des motifs." />
          ) : isLoading ? (
            <Loading label="Chargement de l'analyse…" />
          ) : error ? (
            <ErrorState error={error} onRetry={() => refetch()} />
          ) : (
            <Empty message="Aucune métrique de topologie pour cette porte." />
          )}
```

- [ ] **Step 6: Run tests + build**

Run: `npm --prefix frontend run test -- src/components/AcademyView.test.tsx src/components/EvolutionView.test.tsx src/components/TopologyView.test.tsx`
Expected: PASS (existants + nouvelle assertion Loading). Si un test existant supposait le `<p>Chargement…</p>`, l'adapter pour viser la primitive.

Run: `npm --prefix frontend run build`
Expected: build OK.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AcademyView.tsx frontend/src/components/EvolutionView.tsx frontend/src/components/TopologyView.tsx frontend/src/components/AcademyView.test.tsx
git commit -m "feat(G4): uniformiser les états Loading/Error/Empty (Academy/Evolution/Topology)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Typage d3 (TimelineViewer + TopologyViewer)

**Files:**
- Modify: `frontend/src/components/TimelineViewer.tsx`
- Modify: `frontend/src/components/TopologyViewer.tsx`

**Interfaces:**
- Consumes: types `d3.SimulationNodeDatum`, `d3.SimulationLinkDatum`, `d3.DragBehavior`.
- Produces: rien (typage interne ; aucun changement runtime).

Contexte : objectif = **zéro `any`** dans ces deux fichiers, sans changer le comportement. Le build `tsc` est la garantie. `TopologyViewer` est le modèle (`NodeDatum`/`LinkDatum`).

- [ ] **Step 1: Vérifier l'état initial (les `any` existent)**

Run: `npx --prefix frontend grep -n "any" frontend/src/components/TimelineViewer.tsx frontend/src/components/TopologyViewer.tsx` — ou (bash) :
`grep -n ": any\|as any\|any\[\]" frontend/src/components/TimelineViewer.tsx frontend/src/components/TopologyViewer.tsx`
Expected: ~13 occurrences dans TimelineViewer, 2 dans TopologyViewer.

- [ ] **Step 2: Typer `TimelineViewer`**

Dans `frontend/src/components/TimelineViewer.tsx`, ajouter les types en tête (après les imports) :

```tsx
type TimelineNode = { id: string; label: string } & d3.SimulationNodeDatum;
type TimelineLink = d3.SimulationLinkDatum<TimelineNode>;
```

Typer la query ([TimelineViewer.tsx:12-16](frontend/src/components/TimelineViewer.tsx#L12-L16)) :

```tsx
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.timeline,
    queryFn: () => apiFetch<{ nodes: TimelineNode[]; links: TimelineLink[] }>("/api/timeline"),
    staleTime: Infinity,
  });
```

Dans l'effet, typer la simulation et les accessors (remplacer chaque `(d: any)`) :

```tsx
    const simulation = d3
      .forceSimulation<TimelineNode>(data.nodes)
      .force(
        "link",
        d3.forceLink<TimelineNode, TimelineLink>(data.links).id((d) => d.id).distance(100),
      )
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg
      .append("g")
      .selectAll<SVGLineElement, TimelineLink>("line")
      .data(data.links)
      .join("line")
      .style("stroke", "var(--color-border)")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", 2);

    const node = svg
      .append("g")
      .selectAll<SVGCircleElement, TimelineNode>("circle")
      .data(data.nodes)
      .join("circle")
      .attr("r", 10)
      .style("fill", (d) => (d.label === "Agent" ? "var(--viz-2)" : "var(--viz-1)"));

    const label = svg
      .append("g")
      .selectAll<SVGTextElement, TimelineNode>("text")
      .data(data.nodes)
      .join("text")
      .text((d) => d.id)
      .attr("font-size", 10)
      .attr("dx", 12)
      .attr("dy", 4)
      .style("fill", "var(--color-text)");

    node.append("title").text((d) => `${(d as TimelineNode).label}: ${(d as TimelineNode).id}`);

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as TimelineNode).x ?? 0)
        .attr("y1", (d) => (d.source as TimelineNode).y ?? 0)
        .attr("x2", (d) => (d.target as TimelineNode).x ?? 0)
        .attr("y2", (d) => (d.target as TimelineNode).y ?? 0);

      node.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);
      label.attr("x", (d) => d.x ?? 0).attr("y", (d) => d.y ?? 0);
    });
```

(Note : `node.append("title")` renvoie une sélection dont le datum est inféré ; si TS se plaint sur `d.label`, garder le cast local `(d as TimelineNode)` comme montré. Aucun `any`.)

- [ ] **Step 3: Resserrer les 2 `any` de `TopologyViewer`**

Dans `frontend/src/components/TopologyViewer.tsx` :
- Ligne 36 : `.id((d) => d.id as any)` → `.id((d) => d.id)` (le datum est `NodeDatum`, `id: number` ; `forceLink.id` accepte `number | string`). Si TS exige une string, utiliser `.id((d) => String(d.id))` — mais conserver le comportement (l'id reste la clé de jointure). Choisir la variante qui compile sans `any`.
- Ligne 65 : retirer le `as any` du drag en typant explicitement :

```tsx
    const dragBehavior: d3.DragBehavior<SVGGElement, NodeDatum, NodeDatum | d3.SubjectPosition> = d3
      .drag<SVGGElement, NodeDatum>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
```

Et `aria-label="Topology graph"` ([TopologyViewer.tsx:106](frontend/src/components/TopologyViewer.tsx#L106)) → `aria-label="Graphe de topologie"`.

- [ ] **Step 4: Vérifier zéro `any` + build**

Run (bash): `grep -n ": any\|as any\|any\[\]" frontend/src/components/TimelineViewer.tsx frontend/src/components/TopologyViewer.tsx`
Expected: aucun résultat.

Run: `npm --prefix frontend run build`
Expected: build OK (tsc sans erreur — la garantie du typage).

- [ ] **Step 5: Non-régression de rendu**

Run: `npm --prefix frontend run test -- src/components/TopologyView.test.tsx`
Expected: PASS (rendu inchangé). (TimelineViewer n'a pas de test dédié ; le build couvre le typage, le rendu d3 est inchangé.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TimelineViewer.tsx frontend/src/components/TopologyViewer.tsx
git commit -m "refactor(G4): typer les callbacks d3 (Timeline/Topology) — zéro any

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Nettoyage dette (bestRobustGate, `.step-pill--done`, warning Node)

**Files:**
- Modify: `frontend/src/components/GateSidebar.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/vite.config.ts` (best-effort)
- Test: `frontend/src/components/GateSidebar.test.tsx` (garder vert)

**Interfaces:**
- Consumes: rien.
- Produces: rien (nettoyage).

- [ ] **Step 1: Supprimer le champ mort `bestRobustGate`**

Dans `frontend/src/components/GateSidebar.tsx`, supprimer la ligne `bestRobustGate: experiments.reduce(...)` ([GateSidebar.tsx:44](frontend/src/components/GateSidebar.tsx#L44)) de l'objet `summaryMetrics`. Vérifier d'abord par recherche qu'il n'est lu nulle part :

Run (bash): `grep -rn "bestRobustGate" frontend/src`
Expected avant : 1 seule occurrence (la définition). Si une lecture existe, NE PAS supprimer — signaler. Sinon, supprimer la ligne.

- [ ] **Step 2: Vérifier GateSidebar (non-régression)**

Run: `npm --prefix frontend run test -- src/components/GateSidebar.test.tsx`
Expected: PASS (le test n'utilise pas `bestRobustGate`).

- [ ] **Step 3: `.step-pill--done` → repère visuel distinct**

Dans `frontend/src/styles.css`, donner à l'état « done » du StepBar un repère clair (bordure accent + pastille d'index validée). Remplacer la règle `.step-bar .tab.is-done { color: var(--color-text); }` (posée en Task 3) par :

```css
.step-bar .tab.is-done {
  color: var(--color-text);
  border-color: var(--color-accent);
}
.step-bar .tab.is-done .step-pill__index {
  background: var(--color-accent);
  color: var(--color-bg);
}
```

(Distingue visuellement « done » de « todo » — la pastille d'index passe en accent.)

- [ ] **Step 4: Warning Node `--localstorage-file` (best-effort)**

Ce warning provient de la `localStorage` expérimentale intégrée à Node ≥ 22/25 (l'environnement local), PAS de la config du repo — il peut être absent en CI. Investiguer puis :
- Si la source est un argument/poolOption dans `frontend/vite.config.ts` ou `frontend/src/test.setup.ts` : le corriger.
- Sinon (artefact Node/jsdom externe) : NE PAS ajouter de suppression hacky. Documenter dans le rapport que c'est du bruit d'environnement Node 25 (probablement absent en CI) et laisser tel quel.

Run (bash) pour confirmer la source : `cd frontend && NODE_OPTIONS=--trace-warnings npx vitest run src/components/ui/Field.test.tsx 2>&1 | grep -A6 "localstorage-file" | head`
Expected : soit une trace pointant un fichier du repo (→ corriger), soit une trace interne node/jsdom (→ documenter et laisser).

- [ ] **Step 5: Build + suite complète**

Run: `npm --prefix frontend run build`
Expected: build OK.

Run: `npm --prefix frontend run test`
Expected: tous les tests passent.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/GateSidebar.tsx frontend/src/styles.css frontend/vite.config.ts
git commit -m "chore(G4): supprimer bestRobustGate mort + état StepBar 'done' distinct

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

(Si `vite.config.ts` n'a finalement pas été modifié — warning externe — ne pas l'ajouter au commit.)

---

## Self-Review (effectuée)

- **Couverture du spec :** primitive `Tabs` + APG manuel (Task 1) ; nav globale + tabpanel (Task 2) ; StepBar sur la primitive (Task 3) ; Field a11y (Task 4) ; états Loading/Error/Empty (Task 5) ; typage d3 zéro-`any` (Task 6) ; bestRobustGate + `.step-pill--done` + warning (Task 7). Grappes A/B/C/D toutes couvertes. Tests hors tsconfig préservé (non-objectif respecté).
- **Placeholders :** aucun — code complet à chaque step. Le warning Node (Task 7 §4) a un arbre de décision concret, pas un TODO.
- **Cohérence des types :** `TabItem`/`tabId`/`panelId`/`TabList` (props `items/activeId/onSelect/ariaLabel/orientation/renderLabel/testIdPrefix/className`) cohérents entre Tasks 1→3 ; `buildNavItems` (Task 2) produit des `TabItem` ; StepBar (Task 3) réutilise `testIdPrefix="step"` pour préserver les `data-testid` testés par ParcoursView ; `TimelineNode`/`TimelineLink` (Task 6) calqués sur `NodeDatum`/`LinkDatum`.
- **Risque CSS :** Tasks 3 et 7 touchent toutes deux les règles `.step-bar .tab` — l'ordre (Task 3 pose la base, Task 7 raffine `is-done`) est explicite pour éviter un conflit.
- **Coordination :** périmètre `frontend/src/**` (+ `styles.css`, `vite.config.ts`, `docs/**`) — aucun fichier backend, pas de conflit avec `feat/d1-prod-pairing`.
