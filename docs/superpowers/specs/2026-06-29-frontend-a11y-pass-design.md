# Passe a11y transverse (J3) — design

Date : 2026-06-29
Vague : J (audit transverse) — item J3 (a11y).
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

L'audit a11y (Vague J) relève cinq lacunes d'accessibilité, toutes frontend-only :
1. **Aucune règle `:focus-visible`** dans `styles.css` → focus clavier quasi invisible (les `.btn`/`.tab`/
   inputs réinitialisent le border ; en dark le ring natif est peu contrasté).
2. **Toasts sans ARIA ni fermeture** (`ToastContext`) : `<div className="toast …">` non annoncé aux
   lecteurs d'écran ; pas de bouton de fermeture (disparition par `setTimeout` 4 s seulement).
3. **Canvas monde sans `role`/`aria-label`** : `LiveWorld` (LiveDashboard) et `FlatlandViewer` opaques
   aux technologies d'assistance.
4. **SVG `TimelineViewer` sans `aria-label`** (incohérent vs `TopologyViewer`/`ProvenanceGraph` qui en ont).
5. **Double-label SweepView** : `<input aria-label={s.label}>` redondant à l'intérieur d'un `<label>`
   contenant déjà le texte `{s.label}` (pattern incorrect, dommage réel nul).

## Objectif

Une passe a11y couvrant les 5 points + un bouton de fermeture accessible sur les toasts. **Frontend-only,
zéro changement de comportement visuel** (le focus ring n'apparaît qu'au clavier).

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Périmètre | Passe complète (5 items) **+ bouton « × » de fermeture** des toasts. |
| Focus ring | Règle `:focus-visible` globale via `var(--color-accent)` (token existant : `#0f766e` clair / `#2dd4bf` dark). |
| Toasts | `role` par type (erreur→`alert` ; succès/info→`status`+`aria-live="polite"`) + `dismiss(id)` + bouton. Timeout 4 s conservé. |
| Item 5 (Sweep) | Retrait de l'`aria-label` redondant (nom accessible = label englobant). Le plus mineur. |
| Backend | Aucune touche. |

## Architecture

### 1. Focus visible — `frontend/src/styles.css`

Ajouter une règle `:focus-visible` (n'affecte que la navigation clavier ; aucune régression souris) :

```css
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
```

### 2. Toasts ARIA + bouton fermer — `frontend/src/contexts/ToastContext.tsx`

- Une fonction `dismiss(id: number)` = `setToasts((prev) => prev.filter((t) => t.id !== id))`.
- Rendu de chaque toast :
  ```tsx
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
  ```
- `styles.css` : petite règle `.toast-dismiss` (bouton transparent, couleur héritée, curseur pointer).

### 3. Canvas monde — `role="img"` + `aria-label`

- `frontend/src/components/parcours/LiveDashboard.tsx` (`LiveWorld`, `<canvas>`) :
  `role="img" aria-label="Visualisation 2D du monde sandbox (agents, proies, objets, arbres)"`.
- `frontend/src/components/FlatlandViewer.tsx` (`<canvas>`) :
  `role="img" aria-label="Carte Flatland 2D (terrain, agents, proies, objets)"`.

### 4. SVG TimelineViewer — `frontend/src/components/TimelineViewer.tsx:96`

`<svg ref={svgRef} … aria-label="Timeline généalogique des agents (KuzuDB)" />`. L'attribut statique
survit au rendu D3 (qui ne fait qu'ajouter des enfants).

### 5. Double-label SweepView — `frontend/src/components/SweepView.tsx:93-99`

Retirer `aria-label={s.label}` de l'`<input>` ; le nom accessible vient du `<label className="checkbox-inline">`
englobant + texte `{s.label}`.

## Tests

- **`frontend/src/contexts/ToastContext.test.tsx`** (nouveau) : un composant de test qui appelle `notify` ;
  - `notify(msg, "error")` → un élément `role="alert"` contenant le message ;
  - `notify(msg, "success")` → un élément `role="status"` ;
  - clic sur le bouton « Fermer » (`getByLabelText("Fermer")`) retire le toast.
- **`frontend/src/components/parcours/LiveDashboard.test.tsx`** (existant, étendu) : le canvas `LiveWorld`
  expose `role="img"` et un `aria-label` (via `getByLabelText`/`getByRole("img")`).
- **`SweepView.test.tsx`** (existant) : maintenu vert ; si une requête `getByLabelText` sur les cases
  régresse après le retrait de l'`aria-label`, la basculer sur `getByRole("checkbox", { name })`
  (fonctionne avec le label englobant).
- **FlatlandViewer / TimelineViewer** : ajouts d'attributs vérifiés par `tsc`/build (D3 + WebSocket peu
  testables en jsdom ; pas de nouveau test imposé).
- **Focus-visible** : CSS, non testable en jsdom → vérifié au build.

## Risques

- **Retrait de l'`aria-label` SweepView** : peut affecter un `getByLabelText` du test existant (l'`aria-label`
  avait été ajouté en H3 pour fiabiliser jsdom). Mitigation : basculer la requête sur
  `getByRole("checkbox", { name })`. Aucun impact runtime (le nom accessible reste `s.label`).
- **`aria-live` + `role`** : `role="alert"` implique déjà `aria-live="assertive"` et `role="status"`
  implique `polite` ; on pose les deux explicitement (redondant mais sans effet négatif, plus lisible).
- **`role="img"` sur un `<canvas>` actif** : purement déclaratif, n'altère pas le rendu.

## Non-objectifs (YAGNI)

- Refonte des couleurs en dur de `FlatlandViewer` (→ J6).
- Mémo perf `cssVar`/`vizColors` (→ J2b), partage WS (→ J2c).
- Toute autre vue / tout autre composant non listé.

## Périmètre des fichiers

Frontend-only (→ `main`). Modifiés : `styles.css`, `contexts/ToastContext.tsx`,
`components/parcours/LiveDashboard.tsx`, `components/FlatlandViewer.tsx`, `components/TimelineViewer.tsx`,
`components/SweepView.tsx`. Tests : `contexts/ToastContext.test.tsx` (créé),
`components/parcours/LiveDashboard.test.tsx` (étendu), `components/SweepView.test.tsx` (ajusté si nécessaire).

## Suite

Plan d'implémentation via `writing-plans`. Découpage probable en **2 tâches** : (1) focus-visible CSS +
toasts ARIA/dismiss (cœur testable) ; (2) attributs `role`/`aria-label` canvas/svg + retrait double-label
SweepView (ajouts d'attributs).
