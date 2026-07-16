# J6 — Overlay FlatlandViewer lisible en dark (cohérence DS)

> Vague J, item J6 (périmètre réduit à l'item (a), le seul vrai défaut).
> Frontend-only. Corriger l'overlay de métriques FlatlandViewer illisible en thème sombre.

## Objectif

Rendre l'overlay de métriques de `FlatlandViewer` lisible dans les deux thèmes en
déplaçant son chrome (couleurs) depuis des styles inline en dur vers des classes CSS
à tokens DS, comme le reste de l'app.

## Contexte mesuré

`FlatlandViewer.tsx` style l'overlay et son conteneur en inline avec des couleurs en dur :

- ligne 179 (conteneur) : `border: "1px solid #ccc"`
- ligne 180 (overlay) : `background: "rgba(255,255,255,0.86)"` (blanc opaque-ish)

L'overlay n'a **pas** de `color` explicite → le texte hérite du token `--color-text`,
qui est clair en dark. Résultat en thème sombre : **texte clair sur panneau blanc en dur = illisible.**

### Cause racine

Le style inline en dur court-circuite le système de thème : `rgba(255,255,255,0.86)` ne
participe pas à la cascade `[data-theme="dark"]` (styles.css:107) → il reste blanc quoi
qu'il arrive, pendant que le texte suit le token et devient invisible. Le fix DS-cohérent
est **structurel** (inline → classe tokenisée), pas une substitution de couleur.

## Tokens disponibles (theme-aware, styles.css)

| Token | Light | Dark |
|---|---|---|
| `--color-surface` | `#ffffff` | `#1e293b` |
| `--color-text` | `#0f172a` | `#f1f5f9` |
| `--color-border` | `#e2e8f0` | `#334155` |

Pas de token de surface translucide → on en fabrique un localement via `color-mix` pour
préserver l'intention (panneau semi-transparent laissant voir la carte dessous).

## Changements

### 1. `frontend/src/styles.css` — deux classes à tokens

Ajouter (à proximité des autres règles de composants live, p.ex. après `.live-stat*`) :

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

### 2. `frontend/src/components/FlatlandViewer.tsx` — inline → className

- ligne 179 : `<div style={{ width: "100%", height: "600px", border: "1px solid #ccc", position: "relative", overflow: "hidden" }}>` → `<div className="flatland-frame">`
- ligne 180 : `<div style={{ position: "absolute", top: 10, left: 10, background: "rgba(255,255,255,0.86)", padding: 8, borderRadius: 6, zIndex: 10, minWidth: 260 }}>` → `<div className="flatland-overlay">`

Le `<div style={{ fontWeight: 700, marginBottom: 6 }}>Flatland Metrics</div>` (ligne 181)
reste inline : ce sont des propriétés non-couleur (poids/marge), pas concernées par le thème.

### Hors-scope explicite

**Couleurs de terrain/géo du canvas** (`#84cc6c` plains, `#5c92ff` water, `#2d7a36` forest,
`#5c4033` trunk, etc., lignes 87-99) **laissées telles quelles** : sémantiques-monde
dessinées sur le canvas (une forêt est verte quel que soit le thème UI, comme une carte),
pas du chrome d'interface. `ctx.fillStyle` ne lit pas les CSS vars sans résolution, et ces
couleurs ne relèvent pas de la cohérence DS.

## Tests

- **Créer** `frontend/src/components/FlatlandViewer.test.tsx` — smoke léger (le rendu canvas
  n'est pas testable en jsdom) : monter le composant (hook `useWebSocket` mocké si nécessaire)
  et vérifier que le panneau overlay porte `className="flatland-overlay"` et que
  « Flatland Metrics » rend. Garde anti-régression du câblage classe↔overlay.
- Le contrôle visuel dark (rendu effectif du `color-mix`) reste manuel : jsdom n'évalue pas
  `color-mix` ni la cascade de thème.

## Gates (critères de succès)

1. `cd frontend && npx tsc --noEmit` → 0 erreur.
2. `cd frontend && npx vitest run` → suite verte (incl. le nouveau smoke).
3. `grep -nE "rgba\(255,255,255|#ccc" frontend/src/components/FlatlandViewer.tsx` → aucun résultat
   (plus de couleur de chrome en dur dans le composant).

## Hors-scope (YAGNI — descopé du panier J6 audit)

- (b) composant `<Stat>` / migration `.live-stat` : `.live-stat` utilise déjà les tokens
  (pas un bug) ; refactor de consistance différé.
- (c) décision emojis dans les titres : décision de politique, différée.
- Tokenisation des couleurs-monde du canvas (sémantiques, pas du chrome).

## Contraintes globales

- Frontend-only (aucun fichier backend touché).
- TypeScript strict, **zéro `any`**.
- `tsc` 0 erreur, suite verte.
- Géométrie de l'overlay inchangée (seules les couleurs deviennent des tokens).
- Commits path-scoped (tree partagé — sessions parallèles).
- Branche : `feat/frontend-ds-coherence` (depuis `main`), PR vers `main`.
- Trailer commit : `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
