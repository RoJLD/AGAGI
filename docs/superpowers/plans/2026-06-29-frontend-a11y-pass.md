# Passe a11y transverse (J3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Améliorer l'accessibilité clavier/lecteur d'écran sur 5 points (focus visible, toasts ARIA+fermeture, aria-label canvas/svg, double-label Sweep), frontend-only, sans changement visuel.

**Architecture:** Deux tâches. (1) Cœur testable : règle `:focus-visible` globale (CSS) + toasts `role`/`aria-live` + bouton de fermeture (ToastContext) avec tests. (2) Ajouts d'attributs : `role="img"`/`aria-label` sur les canvas (LiveWorld, FlatlandViewer) et le svg (TimelineViewer), retrait de l'`aria-label` redondant de SweepView, avec extension/ajustement des tests existants.

**Tech Stack:** React 18 + TypeScript strict + @tanstack/react-query v5 + Vitest + Testing Library + CSS.

## Global Constraints

- **Frontend-only**, sur `feat/frontend-a11y-pass` → PR vers `main`. Aucune touche backend.
- **Langue** : libellés/commentaires en français.
- **Pas d'emoji** dans le code ni les commits.
- **TypeScript** : zéro `any`, types explicites.
- **Zéro changement visuel** : le focus ring n'apparaît qu'au clavier (`:focus-visible`) ; les toasts gardent leur timeout 4 s.
- **Anneau de focus** : `outline: 2px solid var(--color-accent); outline-offset: 2px;`.
- **Toasts** : erreur → `role="alert"` + `aria-live="assertive"` ; succès/info → `role="status"` + `aria-live="polite"`. Bouton de fermeture `aria-label="Fermer"`.
- **Commits** : chaque commit se termine par le trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- **Tests/typage** depuis `frontend/` : `npx vitest run <chemin>` et `npx tsc --noEmit`. Un seul appel bash composé (`cd frontend && ...`).

---

### Task 1: Focus visible (CSS) + toasts ARIA + bouton fermer

**Files:**
- Modify: `frontend/src/styles.css` (règle `:focus-visible` + `.toast-dismiss`)
- Modify: `frontend/src/contexts/ToastContext.tsx` (`dismiss`, `role`/`aria-live`, bouton)
- Create: `frontend/src/contexts/ToastContext.test.tsx`

**Interfaces:**
- Consumes: `ToastProvider`, `useToast` (existants).
- Produces: chaque toast porte `role`/`aria-live` + un bouton `aria-label="Fermer"` qui retire le toast.

- [ ] **Step 1: Écrire les tests toasts (échec)**

Créer `frontend/src/contexts/ToastContext.test.tsx` :

```tsx
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { afterEach, test, expect } from "vitest";
import { ToastProvider, useToast } from "./ToastContext";

afterEach(() => cleanup());

function Trigger({ kind }: { kind: "success" | "error" | "info" }) {
  const { notify } = useToast();
  return <button onClick={() => notify(`Message ${kind}`, kind)}>go-{kind}</button>;
}

test("un toast d'erreur expose role=alert", () => {
  render(<ToastProvider><Trigger kind="error" /></ToastProvider>);
  fireEvent.click(screen.getByText("go-error"));
  expect(screen.getByRole("alert").textContent).toContain("Message error");
});

test("un toast de succès expose role=status", () => {
  render(<ToastProvider><Trigger kind="success" /></ToastProvider>);
  fireEvent.click(screen.getByText("go-success"));
  expect(screen.getByRole("status").textContent).toContain("Message success");
});

test("le bouton Fermer retire le toast", () => {
  render(<ToastProvider><Trigger kind="info" /></ToastProvider>);
  fireEvent.click(screen.getByText("go-info"));
  expect(screen.getByText("Message info")).toBeTruthy();
  fireEvent.click(screen.getByLabelText("Fermer"));
  expect(screen.queryByText("Message info")).toBeNull();
});
```

- [ ] **Step 2: Lancer les tests pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/contexts/ToastContext.test.tsx`
Expected : FAIL (pas de `role`/bouton « Fermer » encore).

- [ ] **Step 3: Implémenter `ToastContext.tsx` (role + dismiss + bouton)**

Dans `frontend/src/contexts/ToastContext.tsx`, ajouter la fonction `dismiss` et modifier le rendu. Le corps de `ToastProvider` devient :

```tsx
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  const notify = (message: string, kind: ToastKind = "info") => {
    const id = nextId.current++;
    setToasts((prev) => [...prev, { id, kind, message }].slice(-3));
    setTimeout(() => dismiss(id), 4000);
  };

  return (
    <ToastContext.Provider value={{ notify }}>
      {children}
      <div className="toast-container">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast toast--${t.kind}`}
            role={t.kind === "error" ? "alert" : "status"}
            aria-live={t.kind === "error" ? "assertive" : "polite"}
          >
            <span>{t.message}</span>
            <button type="button" className="toast-dismiss" aria-label="Fermer" onClick={() => dismiss(t.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
```

(Les imports, `ToastKind`, `Toast`, `ToastApi`, `ToastContext`, `useToast` restent inchangés.)

- [ ] **Step 4: Lancer les tests toasts pour vérifier le succès**

Run : `cd frontend && npx vitest run src/contexts/ToastContext.test.tsx`
Expected : PASS (3 tests).

- [ ] **Step 5: Ajouter les règles CSS (focus visible + bouton fermer)**

Dans `frontend/src/styles.css`, à la fin du fichier, ajouter :

```css
/* Accessibilité : anneau de focus clavier (n'apparaît qu'au clavier via :focus-visible). */
.btn:focus-visible,
.tab:focus-visible,
.field input:focus-visible,
.field select:focus-visible,
textarea:focus-visible,
.checkbox-inline input:focus-visible,
.toast-dismiss:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* Bouton de fermeture des toasts. */
.toast-dismiss {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 1.1rem;
  line-height: 1;
  padding: 0;
  margin-left: auto;
}
```

- [ ] **Step 6: Vérifier le typage et la suite ciblée**

Run : `cd frontend && npx tsc --noEmit`
Expected : 0 erreur.

Run : `cd frontend && npx vitest run src/contexts/ToastContext.test.tsx`
Expected : PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/styles.css frontend/src/contexts/ToastContext.tsx frontend/src/contexts/ToastContext.test.tsx
git commit -m "$(cat <<'EOF'
feat(J3): focus-visible global + toasts ARIA (role/aria-live) + bouton de fermeture

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: aria-label canvas/svg + retrait double-label SweepView

**Files:**
- Modify: `frontend/src/components/parcours/LiveDashboard.tsx` (`LiveWorld` `<canvas>`)
- Modify: `frontend/src/components/FlatlandViewer.tsx` (`<canvas>`)
- Modify: `frontend/src/components/TimelineViewer.tsx` (`<svg>` ligne 96)
- Modify: `frontend/src/components/SweepView.tsx` (retrait `aria-label` input)
- Modify: `frontend/src/components/parcours/LiveDashboard.test.tsx` (assertion aria-label canvas)
- Modify: `frontend/src/components/SweepView.test.tsx` (requête `getByLabelText` → `getByRole`)

**Interfaces:**
- Consumes: composants existants. Aucune nouvelle interface produite.

- [ ] **Step 1: Étendre le test `LiveDashboard` (échec)**

Dans `frontend/src/components/parcours/LiveDashboard.test.tsx`, ajouter ce test à la fin :

```tsx
test("le canvas du monde expose role=img et un aria-label", () => {
  renderWithClient(<LiveDashboard />);
  expect(screen.getByLabelText("Visualisation 2D du monde sandbox (agents, proies, objets, arbres)")).toBeTruthy();
});
```

- [ ] **Step 2: Lancer le test pour vérifier l'échec**

Run : `cd frontend && npx vitest run src/components/parcours/LiveDashboard.test.tsx`
Expected : FAIL (le canvas n'a pas encore d'`aria-label`).

- [ ] **Step 3: Ajouter `role`/`aria-label` au canvas `LiveWorld`**

Dans `frontend/src/components/parcours/LiveDashboard.tsx`, sur le `<canvas>` de `LiveWorld`, ajouter `role` et `aria-label` (conserver `ref`/`width`/`height`/`style`) :

```tsx
      <canvas
        ref={canvasRef}
        width={400}
        height={400}
        role="img"
        aria-label="Visualisation 2D du monde sandbox (agents, proies, objets, arbres)"
        style={{ border: "1px solid var(--color-border)", borderRadius: "var(--radius-sm)", background: "var(--color-bg)", width: "100%", height: "auto" }}
      />
```

- [ ] **Step 4: Lancer le test pour vérifier le succès**

Run : `cd frontend && npx vitest run src/components/parcours/LiveDashboard.test.tsx`
Expected : PASS.

- [ ] **Step 5: Ajouter `role`/`aria-label` au canvas `FlatlandViewer`**

Dans `frontend/src/components/FlatlandViewer.tsx`, sur le `<canvas>` (conserver `ref`/`width`/`height`/`style`/handlers) :

```tsx
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        role="img"
        aria-label="Carte Flatland 2D (terrain, agents, proies, objets)"
        style={{ width: "100%", height: "100%", touchAction: "none", cursor: "grab" }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      />
```

- [ ] **Step 6: Ajouter `aria-label` au svg `TimelineViewer`**

Dans `frontend/src/components/TimelineViewer.tsx` ligne 96 :

```tsx
      <svg ref={svgRef} width="100%" height={400} className="topology-svg" aria-label="Timeline généalogique des agents (KuzuDB)" />
```

- [ ] **Step 7: Retirer l'`aria-label` redondant de `SweepView` + ajuster son test**

Dans `frontend/src/components/SweepView.tsx`, sur l'`<input type="checkbox">` des séries, **retirer** la ligne `aria-label={s.label}` (le nom accessible vient du `<label>` englobant + texte `{s.label}`). Le bloc devient :

```tsx
          <label key={s.id} className="checkbox-inline">
            <input
              type="checkbox"
              checked={shownIds.includes(s.id)}
              onChange={() => toggleId(s.id)}
            />
            {s.label}
          </label>
```

Dans `frontend/src/components/SweepView.test.tsx`, ligne ~65, remplacer la requête `getByLabelText` (qui s'appuyait sur l'`aria-label`) par `getByRole` (qui lit le nom accessible du label englobant) :

```tsx
    const second = screen.getByRole("checkbox", { name: "lewis · median_competence" }) as HTMLInputElement;
```

- [ ] **Step 8: Vérifier le typage et toute la suite**

Run : `cd frontend && npx tsc --noEmit`
Expected : 0 erreur.

Run : `cd frontend && npx vitest run`
Expected : toute la suite verte (incluant `ToastContext`, `LiveDashboard` étendu, `SweepView` ajusté).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/parcours/LiveDashboard.tsx frontend/src/components/FlatlandViewer.tsx frontend/src/components/TimelineViewer.tsx frontend/src/components/SweepView.tsx frontend/src/components/parcours/LiveDashboard.test.tsx frontend/src/components/SweepView.test.tsx
git commit -m "$(cat <<'EOF'
feat(J3): aria-label canvas (LiveWorld/Flatland) + svg Timeline ; retire le double-label SweepView

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Notes d'exécution

- 2 tâches, frontend-only, sur `feat/frontend-a11y-pass` → PR vers `main`.
- Task 1 = cœur testable (toasts + focus CSS). Task 2 = ajouts d'attributs + ajustements de tests existants.
- Le mock `LiveDashboard.test` renvoie `{ size: 0, … }` : `LiveWorld` ne dessine pas mais rend bien le
  `<canvas>` (le JSX rend toujours le canvas) → l'`aria-label` est assertable.
- Ne PAS changer les couleurs en dur de FlatlandViewer (réservé à J6) ; ne toucher QUE `role`/`aria-label`.
