# G4 — Accessibilité + cohérence des états + typage d3 (design)

Date : 2026-06-24
Vague : G (dette & qualité) — item G4 (clôt la Vague G)
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Quatre grappes de dette qualité, indépendantes mais regroupées dans un même cycle :

- **A. a11y navigation** : la nav d'onglets globale ([App.tsx:41-57](frontend/src/App.tsx#L41-L57)) est faite de `<button>` bruts dans des `<div class="tab-family">`, sans `role="tablist"`/`tab`/`aria-selected`, sans navigation clavier (flèches), et la zone de contenu n'est pas un `role="tabpanel"`. `StepBar` (G3) a déjà une partie du pattern mais en double.
- **B. Cohérence des états + labels** : trois vues affichent un `<p>Chargement…</p>` ad hoc au lieu de la primitive `Loading` ([AcademyView:46](frontend/src/components/AcademyView.tsx#L46), [EvolutionView:47](frontend/src/components/EvolutionView.tsx#L47), [TopologyView:37](frontend/src/components/TopologyView.tsx#L37)). Le composant `Field` rend un `<label>` mais sans l'associer au contrôle (`htmlFor` quasi jamais fourni) → labels non liés sur tous les formulaires.
- **C. Typage d3** : `TimelineViewer` contient 13 `any` (API `{ nodes: any[]; links: any[] }` + accessors `(d: any)`) ; `TopologyViewer` en garde 2. `TopologyViewer` est déjà bien typé (modèle `NodeDatum`/`LinkDatum`).
- **D. Dette reportée** : champ mort `bestRobustGate` calculé jamais lu ([GateSidebar:44](frontend/src/components/GateSidebar.tsx#L44), G2) ; `.step-pill--done` visuellement indistinct (G3) ; warning Node `--localstorage-file` répété dans la sortie de test (infra test G3).

## Objectif

Clore la Vague G : accessibilité de la navigation (pattern tablist WAI-ARIA complet via une **primitive partagée**), uniformisation des états Loading/Error/Empty + association des labels de formulaire, suppression des `any` d3, et nettoyage de la dette reportée. Additif, sans changement de comportement fonctionnel (hors a11y/clavier).

### Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Périmètre | A + B + C + D en un seul cycle. |
| a11y nav | Extraire une **primitive `Tabs` accessible partagée** (role tablist/tab/tabpanel, aria-selected, roving tabindex + flèches/Home/End) ; la nav globale ET `StepBar` la consomment. |
| Activation clavier | **Manuelle** : les flèches déplacent le focus, Entrée/Espace/clic active (APG — l'activation change toute la vue). |
| Field | **Inclus** : association programmatique label↔contrôle via `useId`. |
| Typage d3 | `TimelineViewer` + `TopologyViewer` seulement ; **les tests restent exclus du tsconfig**. |

### Non-objectifs (YAGNI)

- Ne PAS inclure les tests dans le type-check tsconfig (chantier séparé si voulu un jour).
- Pas de refonte visuelle des vues ; uniquement la substitution des états ad hoc par les primitives.
- Pas de changement de comportement runtime du d3 (typage pur, garanti par le build).
- Pas de nouvelle dépendance (pas de lib de tabs tierce — primitive maison).

## Architecture

### 1. Primitive `Tabs` accessible (`components/ui/Tabs.tsx`)

Une `TabList` qui encapsule la logique ARIA + clavier une seule fois.

```ts
export interface TabItem {
  id: string;            // clé technique (sert d'id de tab et de cible aria)
  label: string;
  icon?: LucideIcon;
  group?: string;        // sous-groupement visuel (familles) — n'affecte pas la séquence roving
  state?: "active" | "done" | "todo";  // hook de style optionnel (StepBar)
}

export function tabId(id: string): string;     // -> `tab-${id}` (pour aria-labelledby du panel)
export function panelId(id: string): string;   // -> `panel-${id}`

export function TabList(props: {
  items: TabItem[];
  activeId: string;
  onSelect: (id: string) => void;
  ariaLabel: string;
  orientation?: "horizontal" | "vertical";  // défaut horizontal
}): JSX.Element;
```

Comportement :
- Conteneur `role="tablist"` `aria-label={ariaLabel}` `aria-orientation`.
- Chaque item : `<button role="tab" id={tabId(item.id)} aria-selected={item.id === activeId} aria-controls={panelId(item.id)} tabIndex={item.id === activeId ? 0 : -1}>`.
- **Roving tabindex** : un seul tab à `tabIndex=0` (l'actif). Flèches ←/→ (horizontal) ou ↑/↓ (vertical) déplacent le **focus** sur le tab voisin (avec wrap), Home/End vont au premier/dernier. **Activation manuelle** : Entrée/Espace/clic appellent `onSelect`. Le focus suit la touche ; l'activation ne se produit qu'au clic/Entrée/Espace.
- `group` : insère un séparateur visuel (`<div class="tab-group">` ou attribut `data-group`) entre groupes, mais la séquence de navigation au clavier est **plate et unique** sur tous les items dans l'ordre.
- `state` : ajoute une classe (`is-done`/`is-active`) pour le style ; sans effet ARIA.

La primitive ne possède PAS le panneau : chaque consommateur câble son `role="tabpanel"` via `panelId(activeId)` + `aria-labelledby={tabId(activeId)}`.

### 2. Migration des consommateurs (A)

- **`App.tsx`** : remplacer la nav par `<TabList items={NAV_ITEMS} activeId={tab} onSelect={setTab} ariaLabel="Sections du dashboard" />`. `NAV_ITEMS` dérive de `TAB_FAMILIES` (label + icon + `group: family`). La `<section className="panel">` reçoit `role="tabpanel"`, `id={panelId(tab)}`, `aria-labelledby={tabId(tab)}`, et `tabIndex={0}` (focusable pour les AT). Le `key={tab}` de l'`ErrorBoundary` est conservé.
- **`StepBar.tsx`** : réimplémenté au-dessus de `TabList` — `items` = les 4 étapes avec `state` dérivé de `reached`/`current`, `onSelect` = la navigation d'étape existante. Le visuel pastille + index est porté par les classes `.step-pill*` (via `state` + un rendu custom si nécessaire). Les tests `StepBar.test.tsx`/`ParcoursView.test.tsx` doivent rester verts (mêmes `data-testid="step-<id>"`, mêmes rôles).

Note : si le rendu pastille de StepBar (numéro d'index + libellé) ne se réduit pas proprement au rendu standard de `TabList`, `TabList` accepte un `renderLabel?(item): ReactNode` optionnel pour personnaliser le contenu interne du bouton tout en gardant rôles/clavier. À trancher à l'implémentation ; défaut = label + icône.

### 3. États + labels (B)

- Substituer les `<p>Chargement…</p>` ad hoc par `<Loading label=…/>` dans AcademyView, EvolutionView, TopologyView. Vérifier que chacune route aussi error→`<ErrorState>` et vide→`<Empty>` (les primitives existent et sont déjà utilisées ailleurs).
- **`Field`** : générer un id via `useId()`, l'appliquer en `htmlFor` sur le `<label>`, et l'injecter dans l'enfant unique via `cloneElement` **uniquement si l'enfant n'a pas déjà d'`id`** (sinon respecter l'id fourni). Cas géré : `Field` enveloppant un `<select>`/`<input>` simple (le cas universel du code). Si l'enfant n'est pas un élément unique clonable, retomber sur le comportement actuel (label non lié) sans planter.

### 4. Typage d3 (C)

- **`TimelineViewer`** : définir
  ```ts
  type TimelineNode = { id: string; label: string } & d3.SimulationNodeDatum;
  type TimelineLink = d3.SimulationLinkDatum<TimelineNode>;
  ```
  typer la query (`{ nodes: TimelineNode[]; links: TimelineLink[] }`), `forceSimulation<TimelineNode>`, `forceLink<TimelineNode, TimelineLink>`, et tous les accessors (`(d: TimelineNode)` / `(d: TimelineLink)`) — `d.source`/`d.target` deviennent `TimelineNode` après init (cast local documenté si besoin, comme TopologyViewer). Zéro `any`.
- **`TopologyViewer`** : resserrer les 2 `any` — `.id((d) => d.id)` typé `NodeDatum` (l'id est `number`, aligner la signature `forceLink` `.id`), et le `as any` du drag remplacé par le typage `d3.DragBehavior<SVGGElement, NodeDatum, NodeDatum | d3.SubjectPosition>` + `.call(dragBehavior)` typé. Si un cast résiduel est strictement inévitable (friction connue des types d3), le restreindre au minimum et le commenter — pas de `any` nu.
- Les tests restent hors `tsconfig` (`exclude` inchangé).

### 5. Dette (D)

- Supprimer `bestRobustGate` de `summaryMetrics` dans `GateSidebar.tsx` (calcul + champ ; vérifier zéro lecture).
- `.step-pill--done` : ajouter un repère visuel distinct (✓ ou bordure/couleur accent) via tokens CSS.
- Traquer la source du warning `--localstorage-file` (probablement un argument node/poolOptions dans `vite.config.ts` ou `test.setup.ts` introduit en G3) et l'éliminer pour une sortie de test pristine.
- `aria-label="Topology graph"` ([TopologyViewer.tsx:106](frontend/src/components/TopologyViewer.tsx#L106)) → « Graphe de topologie ».

## Tests

- **`Tabs`** (`ui/Tabs.test.tsx`) : rôles (`tablist`/`tab`), `aria-selected` sur l'actif, roving tabindex (actif=0, autres=-1), flèches ←/→ déplacent le focus (avec wrap), Home/End, **activation manuelle** (focus via flèche n'appelle pas `onSelect` ; Entrée/Espace/clic l'appellent), `aria-controls`/`panelId`.
- **`StepBar`/`ParcoursView`** : tests existants restent verts (mêmes testid/rôles) — filet de non-régression du refactor.
- **`Field`** (`ui/Field.test.tsx`) : le `<label>` est associé au contrôle (`getByLabelText` retourne l'input ; l'id généré relie `htmlFor`↔`id`) ; un id fourni par le caller est respecté.
- **États** : AcademyView/EvolutionView/TopologyView rendent `Loading` (role="status") en chargement.
- **d3** : pas de test runtime (type-only) — le `npm run build` (tsc) est la garantie ; viewers couverts par leurs tests existants pour la non-régression de rendu.

## Risques

- **Refactor `Tabs` touche StepBar** (composant clé du Parcours G3). Mitigation : tests StepBar/ParcoursView existants comme filet ; conserver `data-testid`/rôles ; le `renderLabel` optionnel évite de dénaturer le visuel pastille.
- **Field `cloneElement`** : fragile si l'enfant n'est pas un élément unique. Mitigation : garde `isValidElement` + fallback non-bloquant ; ne cloner que pour injecter l'id absent.
- **Typage d3** : friction connue des types `@types/d3` (drag/forceLink). Mitigation : suivre le pattern déjà fonctionnel de `TopologyViewer` ; type-only, build-gated, aucun changement runtime.
- **Coordination session parallèle** : périmètre strictement `frontend/src/**` (+ `docs/**`) ; commits path-scopés ; aucun fichier backend → pas de conflit avec `feat/d1-prod-pairing`.

## Périmètre des fichiers

Créés :
- `frontend/src/components/ui/Tabs.tsx` + `Tabs.test.tsx`
- `frontend/src/components/ui/Field.test.tsx`

Modifiés :
- `frontend/src/App.tsx` (nav → `TabList`, `<section>` → tabpanel)
- `frontend/src/components/parcours/StepBar.tsx` (réimplémenté sur `TabList`)
- `frontend/src/components/ui/Field.tsx` (association `useId`)
- `frontend/src/components/AcademyView.tsx`, `EvolutionView.tsx`, `TopologyView.tsx` (états → primitives)
- `frontend/src/components/TimelineViewer.tsx`, `TopologyViewer.tsx` (typage d3)
- `frontend/src/components/GateSidebar.tsx` (supprimer `bestRobustGate`)
- `frontend/src/styles.css` (`.step-pill--done` distinct ; styles tablist/tab-group si besoin)
- `frontend/vite.config.ts` ou `frontend/src/test.setup.ts` (warning `--localstorage-file`)

## Suite

Plan d'implémentation via `writing-plans`, découpé en tâches TDD (ordre pressenti : primitive `Tabs` → migration nav globale + tabpanel → réimplémentation StepBar → Field a11y → uniformisation des états → typage TimelineViewer → typage TopologyViewer → nettoyage dette D), chacune testée et indépendamment livrable.
