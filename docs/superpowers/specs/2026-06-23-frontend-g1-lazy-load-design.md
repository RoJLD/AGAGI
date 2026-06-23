# Design — G1 : lazy-load + découpage du bundle frontend

Date : 2026-06-23
Statut : validé (brainstorming)
Vague : G1 (dette & qualité frontend — audit 2026-06-23)

## Problème

Le bundle initial charge `recharts` (**438 kB / 132 kB gzip**, le plus gros chunk) et `d3` (~107 kB)
alors que :
- `recharts` n'est utilisé que par `SandboxView` ([SandboxView.tsx:11](../../../frontend/src/components/SandboxView.tsx)) ;
- `d3` n'est utilisé que par `TopologyViewer`, `TimelineViewer`, `FlatlandViewer` ;
- ces vues ne sont **pas** l'onglet d'atterrissage (`edr`).

`App.tsx` importe **toutes** les vues statiquement ([App.tsx:1-26](../../../frontend/src/App.tsx)) et il n'existe
**aucun `React.lazy`/`Suspense`**. Le `manualChunks` de `vite.config.ts` *groupe* recharts/d3 dans des chunks
vendor séparés, mais comme le graphe initial les référence (imports statiques), ils restent **chargés au
démarrage**. `manualChunks` groupe ; il ne diffère pas.

## Objectif

Sortir les vues lourdes du chemin critique : chaque onglet (sauf la landing) devient un chunk **asynchrone**
chargé à la demande. Réduire la taille du chunk initial ; `recharts-*.js` / `d3-*.js` ne sont fetchés qu'au
clic sur Sandbox / Topologie / Timeline / Temps réel.

## Approche

`React.lazy` sur les vues d'onglet + une **unique** frontière `<Suspense>` autour du switch d'onglets dans
`App.tsx`. Les composants sont en **exports nommés** → wrapper :
`lazy(() => import("./components/X").then((m) => ({ default: m.X })))`.

### Périmètre (approche A retenue)
- **Lazy** : `SandboxView` (recharts+d3+canvas), `TopologyViewer` (d3, feuille rendue dans l'onglet inline
  `topology`), `TimelineViewer` (d3), `FlatlandViewer` (canvas), `LaboratoryView`, `RunsHistoryView`,
  `HealthView`, `LiveMetrics`, `RunLauncher`, `ABComparisonView`.
- **Eager (conservé)** : `EDRDashboard` (onglet d'atterrissage `edr` → premier paint instantané) ;
  `ComparisonChart` et `RadarChart` (SVG léger, pas de lib, rendus dans l'onglet inline `comparison`) ;
  primitives `ui/`, `ErrorBoundary`, `Loading`.
- **Hors périmètre** : l'extraction des onglets inline `evolution`/`comparison`/`academy` (= G2). On ne touche
  pas à leur structure ; seul `TopologyViewer` (lib d3) y est lazy-loadé comme composant feuille.

### Frontière Suspense
Une seule, dans `App.tsx`, à l'intérieur de l'`ErrorBoundary` existante, autour du bloc de switch d'onglets :

```tsx
<ErrorBoundary key={tab}>
  <Suspense fallback={<Loading label="Chargement de la vue…" />}>
    {tab === "edr" && <EDRDashboard />}
    {/* … tous les autres onglets … */}
  </Suspense>
</ErrorBoundary>
```

`TopologyViewer` étant rendu à l'intérieur de l'onglet `topology` (lui-même dans ce Suspense), son chargement
asynchrone est couvert par la même frontière.

### Vite
`manualChunks` est **conservé tel quel** : il continue de regrouper `react`/`d3`/`recharts` en chunks vendor
nommés. Le lazy-load suffit à rendre `d3`/`recharts` asynchrones (plus aucun import eager ne les tire dans le
graphe initial). Aucune modification de `vite.config.ts` requise.

## Unités touchées
- `frontend/src/App.tsx` — remplacer les imports statiques des vues lazy par des `const X = lazy(...)` ;
  ajouter l'import `lazy, Suspense` de React et `Loading` ; envelopper le switch d'onglets dans `<Suspense>`.
  C'est le **seul** fichier modifié.

## Gestion d'erreur
- Le chargement d'un chunk peut échouer (réseau). L'`ErrorBoundary` par onglet (déjà présente, `key={tab}`)
  capture l'échec d'un `import()` dynamique et affiche son fallback d'erreur — aucun nouveau mécanisme requis.
- Pendant le chargement : fallback `Loading` du `<Suspense>`.

## Tests / vérification
- **Mesure bundle (preuve principale)** : `npm --prefix frontend run build` avant/après ; consigner la taille
  du chunk initial `index-*.js` et confirmer que `recharts-*.js` / `d3-*.js` apparaissent comme chunks
  **séparés non chargés à l'entrée** (plus référencés par l'entrée). Attendu : chute du chunk initial de
  l'ordre de recharts+d3 (~545 kB brut / ~167 kB gzip) moins ce que la landing utilise.
- **Non-régression** : les 15 tests Vitest existants passent ; build `tsc` vert.
- **Test ciblé** : un test RTL vérifiant que `App` rend le fallback `Suspense` puis la vue (avec `apiFetch`
  mocké) pour au moins un onglet lazy — confirme que la frontière Suspense est correctement câblée.
- Pas de changement d'API REST → pas de drift OpenAPI/`schema.ts`.

## Hors scope (YAGNI)
- Préchargement (prefetch) des chunks au survol des onglets.
- Extraction des onglets inline (G2).
- Remplacement de recharts par du SVG maison (décision viz séparée).
- Modification du `manualChunks`.
