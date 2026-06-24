# G3 — Parcours chercheur guidé (design)

Date : 2026-06-24
Vague : G (dette & qualité) — item G3
Statut : design approuvé, prêt pour le plan d'implémentation.

## Problème

Le parcours expérimental réel — **lancer → suivre en live → comparer → conclure** — est
éclaté sur 5 onglets disjoints, sans fil conducteur, avec deux paires de vues qui se
chevauchent :

- **Lancer** : onglet `sandbox` = `RunLauncher` (multi-seed reproductible) empilé sur
  `SandboxView` (ad-hoc + dashboard live inline).
- **Suivre** : doublé — le live inline de `SandboxView` (`/api/sandbox/state|logs|telemetry`)
  **et** l'onglet `live` (`FlatlandViewer` + `LiveMetrics` lus de `live_progress.jsonl`).
  Les deux observent **le même subprocess** (le run arme `AGISEED_LIVE_PROGRESS` au lancement).
- **Comparer** : doublé — `ComparisonView` (A/B quantitatif, deep-link `?ab=`) **et**
  `LaboratoryView` (le Sociologue LLM génère un article narratif).
- **Conclure** : `RunsHistoryView` (historique, liens run↔EDR↔article).

Le chercheur doit sauter d'onglet en onglet en perdant le contexte du run qu'il suit, et chaque
onglet refait son propre `useState` isolé : il n'existe aucune notion d'« expérience active ».

Contrainte structurante : **le backend ne tient qu'un seul subprocess à la fois**
(`RunLauncher` pilote une file séquentielle). Le parcours est donc intrinsèquement
mono-expérience-active.

## Objectif

Introduire un **Parcours chercheur guidé** : une vue dédiée qui orchestre les composants
existants en 4 étapes (Lancer → Suivre → Comparer → Conclure), reliées par un état
« expérience active » partagé. Additif et réversible : les onglets actuels survivent pour
l'accès expert. Aucune refonte de navigation, aucun nouvel endpoint backend.

Le vrai actif durable est le **modèle d'état partagé**, pas l'écran : il transforme les vues
actuelles en briques réutilisables et devient l'endroit où, plus tard et sans risque, on pourra
converger les vues doublées.

### Non-objectifs (YAGNI)

- Pas de fusion des vues doublées (live sandbox vs onglet live ; comparison vs laboratoire) —
  on les laisse coexister ; le Parcours les *orchestre*.
- Pas de support multi-expériences simultanées (le backend ne le permet pas).
- Pas de courbes d'évolution live (`FlatlandViewer`/`LiveMetrics`) dans l'étape Suivre pour
  cette itération — **évolution future** si pertinent.
- Pas de refonte de la navigation globale ni de suppression d'onglets.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Ambition | Vue « Parcours » dédiée orchestrant l'existant + état « run actif » partagé (pas un simple fil léger, pas une refonte). |
| Étape Lancer | `RunLauncher` (multi-seed reproductible) — lancement canonique. L'ad-hoc reste dans l'onglet `sandbox` expert. |
| Étape Suivre | Dashboard sandbox riche (monde 2D, console, télémétrie cognitive, superviseur, god-mode). Courbes d'évolution live = future. |
| Étape Comparer | `ComparisonView` (A/B quantitatif). |
| Étape Conclure | Génération article Sociologue (`LaboratoryView`) **puis** archivage : liens article↔run↔EDR. |
| Navigation | Stepper **souple** : 4 étapes toujours cliquables, étape pertinente mise en avant + CTA « étape suivante », indices contextuels si prérequis manquant. Jamais de verrou dur. |
| Landing | Le Parcours devient l'écran d'accueil par défaut (remplace `edr` comme onglet par défaut). EDR reste à un clic. |
| Live | Extraction du dashboard live de `SandboxView` dans un composant réutilisable `LiveDashboard`. |

## Architecture

### 1. État « expérience active »

Nouveau contexte React `frontend/src/contexts/ActiveExperimentContext.tsx` :

```ts
interface ActiveExperiment {
  condition: string;        // nom de condition / variable testée (fil conducteur)
  variableTested: string;
  scriptName: string;
  worldType: string;
  seeds: number[];          // base..base+n
  launchedAt: number;       // timestamp (ms)
  baseline?: string;        // condition de référence choisie à l'étape Comparer
}
```

- **Persistance `localStorage`** (clé `agiseed.activeExperiment`) : les sims sont longues, un
  reload ne doit pas perdre le fil. Sérialisation JSON ; lecture défensive (try/catch →
  `null` si corrompu/absent).
- Le contexte ne stocke **qu'un descripteur**, jamais l'état serveur : les données live/résultats
  restent lues du backend via react-query (pas de cache stale).
- API du provider : `{ activeExperiment, setActiveExperiment(exp), updateActiveExperiment(patch), clearActiveExperiment() }`.
- Le `ActiveExperimentProvider` enveloppe l'app à côté du `ToastContext` existant.

### 2. `ParcoursView` (orchestrateur)

Dossier `frontend/src/components/parcours/` :

- `ParcoursView.tsx` — détient l'étape courante (`step: "lancer"|"suivre"|"comparer"|"conclure"`),
  synchronisée à l'URL via le `useHashRoute` existant (`#/parcours?step=suivre`). Rend la `StepBar`
  puis l'étape active.
- `StepBar.tsx` — 4 pastilles cliquables (état : faite / active / à venir), sémantique accessible
  (`role="tablist"`, `aria-current`/`aria-selected`, navigation clavier). Sert aussi de modèle pour
  G4 (nav onglets globale).
- `NextStepButton.tsx` — CTA contextuel (« Suivre le run en direct → », « Comparer les résultats → »,
  « Conclure & publier → »).
- Un wrapper mince par étape, **réutilisant les composants existants sans les réécrire** :

  | Étape | Réutilise | Rôle du wrapper |
  |---|---|---|
  | Lancer | `RunLauncher` | à l'enfilage/lancement de la file, appelle `setActiveExperiment(...)` (condition = `variable_tested`, seeds, script, monde). |
  | Suivre | `LiveDashboard` (extrait) | monte le dashboard live ; indice `Empty` si aucun run actif. |
  | Comparer | `ComparisonView` | pré-remplit l'A/B avec `condition` du contexte ; `updateActiveExperiment({ baseline })` quand l'utilisateur choisit la référence. |
  | Conclure | `LaboratoryView` + bloc liens de `RunsHistoryView` | pré-remplit baseline/intervention depuis le contexte ; expose l'archivage (liens run↔EDR↔article). |

### 3. Extraction `LiveDashboard`

Refactor **mécanique** : déplacer `LiveWorld`, `LiveConsole`, `LiveTelemetry`, `LiveSupervisor`,
`GodModePanel` de `SandboxView.tsx` vers `frontend/src/components/parcours/LiveDashboard.tsx`
(ou `components/live/LiveDashboard.tsx`). `SandboxView` l'importe et le rend quand `running`
(comportement strictement préservé) ; l'étape Suivre le rend aussi. Source unique, zéro duplication.

### 4. Guidage (dérivation de progression)

Pas de machine à états lourde — dérivation simple :

- **Lancer** : fait dès qu'il existe un `activeExperiment`.
- **Suivre** : actif tant que `/api/sandbox/status.running`.
- **Comparer** : disponible dès qu'une `condition` existe.
- **Conclure** : disponible après Comparer (souple — jamais verrouillé dur).

Si `!activeExperiment` sur Suivre/Comparer/Conclure → encart `Empty` :
« Aucune expérience active — commence par *Lancer*, ou choisis une condition existante »
(deep-link vers les conditions de l'historique des runs).

### 5. Placement & navigation

- Nouvelle clé `"parcours"` en tête de `TAB_KEYS` ; entrée dans `TAB_FAMILIES` en tête de la
  famille « Expérimentation » (icône lucide `Route` ou `Compass`).
- **Défaut de route** : l'argument passé à `useHashRoute(TAB_KEYS, "edr")` dans `App.tsx` passe de
  `"edr"` à `"parcours"` (accueil). EDR reste accessible. Le hook lui-même n'est pas modifié.
- `showSidebar` inchangé (le Parcours gère sa propre mise en page, pas de `GateSidebar`).

### 6. Données

**Zéro nouvel endpoint backend.** Tout réutilise les queries react-query existantes ; la dédup par
`queryKey` fait que monter `ComparisonView`/`LiveDashboard` dans le Parcours ne déclenche pas de
fetch réseau supplémentaire si l'onglet correspondant a déjà chargé.

## Lazy-loading (synergie G1)

`ParcoursView` est ajouté au découpage `React.lazy` + `Suspense` d'`App.tsx` comme les autres
vues lourdes (il tire `RunLauncher`/`ComparisonView`/recharts). Comme c'est l'écran d'accueil, on
vérifiera que son chunk reste raisonnable ; sinon les sous-étapes (Comparer/recharts) peuvent être
lazy à l'intérieur du Parcours.

## Tests

- `ActiveExperimentContext` : set/get, `updateActiveExperiment` (merge partiel), `clear`,
  persistance localStorage (round-trip + lecture défensive sur valeur corrompue).
- `ParcoursView` : rendu des 4 étapes, navigation stepper (clic libre + sync URL), CTA « étape
  suivante », indices `Empty` quand pas de run actif.
- `StepBar` : sémantique a11y (role/aria-current), navigation clavier.
- Extraction `LiveDashboard` : test de non-régression — `SandboxView` rend toujours le dashboard
  quand `running`.

Pile : Vitest + Testing Library, cohérent avec l'existant.

## Risques

- **Principal** : extraction des composants live hors de `SandboxView`. Mitigation : extraction
  mécanique (déplacement sans changement de logique) + test de non-régression sur `SandboxView`.
- **Landing par défaut** : changer le défaut de `useHashRoute` ne doit pas casser les deep-links
  existants (`#/...`) — vérifier que seul le cas « aucun hash » est affecté.
- **Coordination session parallèle** : travail strictement frontend (`frontend/src/**`, `docs/**`),
  commits path-scopés ; aucun fichier backend touché → pas de conflit avec `feat/d1-prod-pairing`.

## Périmètre des fichiers

Créés :
- `frontend/src/contexts/ActiveExperimentContext.tsx`
- `frontend/src/components/parcours/ParcoursView.tsx`
- `frontend/src/components/parcours/StepBar.tsx`
- `frontend/src/components/parcours/NextStepButton.tsx`
- `frontend/src/components/parcours/LiveDashboard.tsx` (extrait de SandboxView)
- Étapes : `StepLancer.tsx`, `StepSuivre.tsx`, `StepComparer.tsx`, `StepConclure.tsx`
  (wrappers minces — regroupables dans `ParcoursView` si triviaux)
- Tests associés.

Modifiés :
- `frontend/src/tabs.ts` (clé + famille `parcours`)
- `frontend/src/App.tsx` (lazy `ParcoursView`, branche `tab === "parcours"`, provider, défaut)
- `frontend/src/main.tsx` ou `App.tsx` (montage `ActiveExperimentProvider`)
- `frontend/src/components/SandboxView.tsx` (importe `LiveDashboard` au lieu des composants inline)

## Suite

Plan d'implémentation via la skill `writing-plans`, découpé en tâches (état partagé d'abord, puis
extraction LiveDashboard, puis ParcoursView + StepBar, puis câblage des 4 étapes, puis intégration
nav/landing), chacune testée.
