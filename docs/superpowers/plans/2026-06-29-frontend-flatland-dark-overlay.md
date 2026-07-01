# J6 — Overlay FlatlandViewer lisible en dark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre l'overlay de métriques de `FlatlandViewer` lisible en thème sombre en déplaçant son chrome (couleurs) d'inline en dur vers des classes CSS à tokens DS.

**Architecture:** Le bug dark vient de styles inline en dur (`rgba(255,255,255,0.86)`, `#ccc`) qui court-circuitent la cascade de thème. Fix structurel : 2 classes CSS à tokens (`.flatland-frame`, `.flatland-overlay`) dans styles.css + remplacement des 2 `style={{…}}` par `className` dans le composant. Géométrie inchangée, seules les couleurs deviennent des tokens.

**Tech Stack:** React 18, TypeScript strict, CSS variables (tokens DS theme-aware), Vitest, @testing-library/react.

## Global Constraints

- Frontend-only — aucun fichier backend touché.
- TypeScript strict, **zéro `any`**.
- `cd frontend && npx tsc --noEmit` → 0 erreur ; `cd frontend && npx vitest run` → suite verte.
- Géométrie de l'overlay inchangée (seules les couleurs deviennent des tokens).
- Commits **path-scoped** (`git commit -- <chemins>`, jamais `git add -A`) — tree partagé, sessions parallèles.
- Worktree : `c:\Users\robla\VScode_Project\AGAGI-front`. Branche : `feat/frontend-ds-coherence` (depuis `main`).
- Trailer commit : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## File Structure

- **Modify** `frontend/src/styles.css` — ajouter 2 classes `.flatland-frame` / `.flatland-overlay` (couleurs en tokens).
- **Modify** `frontend/src/components/FlatlandViewer.tsx:179-180` — inline → className.
- **Create** `frontend/src/components/FlatlandViewer.test.tsx` — smoke test du câblage classe↔overlay.

---

### Task 1: Overlay FlatlandViewer en classes à tokens + smoke test

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/components/FlatlandViewer.tsx:179-180`
- Create: `frontend/src/components/FlatlandViewer.test.tsx`

**Interfaces:**
- Consumes : tokens CSS déjà définis dans `styles.css` (`--color-surface`, `--color-text`, `--color-border`, theme-aware via la cascade `[data-theme]`/`.dark`).
- Produces : classes CSS `.flatland-frame`, `.flatland-overlay`. Le composant `FlatlandViewer()` garde sa signature sans props.

- [ ] **Step 1: Écrire le smoke test qui échoue**

Créer `frontend/src/components/FlatlandViewer.test.tsx` :

```tsx
import { render, screen, cleanup } from "@testing-library/react";
import { vi, test, expect, afterEach } from "vitest";

// useWebSocket ouvre une vraie WebSocket dans un effet -> on le mocke (pas de réseau en test).
vi.mock("../hooks/useWebSocket", () => ({ useWebSocket: () => ({ status: "closed" }) }));
import { FlatlandViewer } from "./FlatlandViewer";

afterEach(() => cleanup());

test("l'overlay des métriques porte la classe DS flatland-overlay", () => {
  render(<FlatlandViewer />);
  const title = screen.getByText("Flatland Metrics");
  expect(title.parentElement?.className).toBe("flatland-overlay");
});

test("le conteneur porte la classe DS flatland-frame", () => {
  const { container } = render(<FlatlandViewer />);
  expect(container.querySelector(".flatland-frame")).toBeTruthy();
});
```

Note : `FlatlandViewer()` ne prend pas de props. Le draw effect garde `if (!ctx) return`
(getContext renvoie null en jsdom) → rendu sans throw. `frame` est null (WS mockée fermée)
donc seul le bloc de base de l'overlay rend (« Flatland Metrics », Ticks, Agents).

- [ ] **Step 2: Lancer le test, vérifier qu'il échoue**

Run: `cd frontend && npx vitest run src/components/FlatlandViewer.test.tsx`
Expected: FAIL — `expect("...").toBe("flatland-overlay")` échoue car le div overlay a encore
un `style` inline et pas de `className` (className vaut `""`).

- [ ] **Step 3: Ajouter les 2 classes à tokens dans styles.css**

Dans `frontend/src/styles.css`, ajouter ces règles juste après le bloc `.live-stat strong { … }` (autour de la ligne 335) :

```css
/* Conteneur + overlay métriques Flatland — couleurs en tokens DS (theme-aware).
   Géométrie en px littéraux (identique à l'inline d'origine) : seules les
   COULEURS sont tokenisées (le bug dark est purement chromatique). */
.flatland-frame {
  width: 100%;
  height: 600px;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border);
}
.flatland-overlay {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
  min-width: 260px;
  padding: 8px;
  border-radius: 6px;
  background: color-mix(in srgb, var(--color-surface) 86%, transparent);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
```

- [ ] **Step 4: Remplacer les styles inline par className dans FlatlandViewer.tsx**

Dans `frontend/src/components/FlatlandViewer.tsx`, remplacer la ligne 179 :

```tsx
    <div style={{ width: "100%", height: "600px", border: "1px solid #ccc", position: "relative", overflow: "hidden" }}>
```

par :

```tsx
    <div className="flatland-frame">
```

et la ligne 180 :

```tsx
      <div style={{ position: "absolute", top: 10, left: 10, background: "rgba(255,255,255,0.86)", padding: 8, borderRadius: 6, zIndex: 10, minWidth: 260 }}>
```

par :

```tsx
      <div className="flatland-overlay">
```

Ne pas toucher au reste (le `<div style={{ fontWeight: 700, marginBottom: 6 }}>Flatland Metrics</div>`
reste inline — propriétés non-couleur ; le `<canvas>` et ses handlers inchangés).

- [ ] **Step 5: Lancer le smoke test, vérifier qu'il passe**

Run: `cd frontend && npx vitest run src/components/FlatlandViewer.test.tsx`
Expected: PASS — les 2 tests verts.

- [ ] **Step 6: Vérifier l'absence de couleur de chrome en dur + la suite + le typage**

Run: `grep -nE "rgba\(255,255,255|#ccc" frontend/src/components/FlatlandViewer.tsx`
Expected: aucun résultat (plus de couleur de chrome en dur dans le composant).

Run: `cd frontend && npx vitest run`
Expected: suite complète verte (aucune régression).

Run: `cd frontend && npx tsc --noEmit`
Expected: 0 erreur.

- [ ] **Step 7: Commit**

```bash
git commit -m "fix(J6): overlay FlatlandViewer lisible en dark (inline -> classes a tokens)

Deplace le chrome de l'overlay (border #ccc, bg rgba blanc en dur) vers
2 classes CSS a tokens (.flatland-frame/.flatland-overlay) ; surface
translucide theme-aware via color-mix + color:var(--color-text) explicite.
Couleurs-monde du canvas laissees (semantiques). Smoke test du cablage.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>" -- frontend/src/styles.css frontend/src/components/FlatlandViewer.tsx frontend/src/components/FlatlandViewer.test.tsx
```

---

## Notes d'exécution

- **Tâche unique** : 3 fichiers, un seul déliverable cohérent (l'overlay lisible en dark).
- **Pas de revue finale séparée** : 1 tâche, frontend-only ; si la revue de tâche est propre et les gates vérifiées (tsc 0, suite verte, grep vide), la revue whole-branch est repliée dans la revue de tâche.
- **Modèle SDD** : transcription mécanique (CSS + 2 remplacements + test fournis verbatim) → implémenteur haiku ; reviewer sonnet.
- **Contrôle dark visuel** : reste manuel (jsdom n'évalue ni `color-mix` ni la cascade de thème) ; le smoke test garde le câblage classe↔overlay, le grep garde l'absence de couleur en dur.
