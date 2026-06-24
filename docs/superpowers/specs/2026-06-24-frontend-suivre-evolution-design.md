# Courbe d'évolution live dans l'étape « Suivre » (design)

Date : 2026-06-24
Statut : design approuvé, exécution inline en un commit de code.
Origine : enhancement explicitement reporté dans le spec G3 (« courbes d'évolution live → future si pertinent »).

## Problème

L'étape « Suivre » du Parcours ([StepSuivre.tsx](frontend/src/components/parcours/StepSuivre.tsx))
ne montre que `<LiveDashboard />` (monde 2D, console, télémétrie cognitive, superviseur, god-mode du
subprocess sandbox). Le signal macro « est-ce que l'expérience progresse ? » — la **fitness par
génération** — n'y est pas. Il vit dans `LiveEvolution` (`/ws/evolution`, alimenté par le run lancé
via `live_progress.jsonl`), aujourd'hui rendu seulement dans `EvolutionView`.

## Objectif

Ajouter la courbe d'évolution live (`LiveEvolution`) **en tête** de l'étape Suivre, au-dessus du
`LiveDashboard`. Hiérarchie : santé évolutive de l'expérience d'abord, détail du monde ensuite.
Compose un composant existant — zéro nouveau composant, zéro endpoint.

## Décisions (cadrage validé)

| Sujet | Décision |
|---|---|
| Quoi | `LiveEvolution` seul (fitness × génération). Écartés : `FlatlandViewer` (duplique le canvas 2D du dashboard), `LiveMetrics` (recoupe la télémétrie cognitive). |
| Placement | `LiveEvolution` en tête, `LiveDashboard` dessous, puis `NextStepButton`. |
| Données | `/ws/evolution` (déjà câblé) ; état « hors-ligne » natif de `LiveEvolution` quand aucun run n'émet. |

## Architecture

`StepSuivre.tsx`, branche active (`hasActive || running`) :
```tsx
return (
  <>
    <LiveEvolution />
    <LiveDashboard />
    <NextStepButton label="Comparer les résultats" onClick={onNext} />
  </>
);
```
La branche vide (`!hasActive && !running → <Empty>`) est inchangée. `LiveEvolution` porte sa propre
en-tête (`<h2>Évolution en direct</h2>`) + badge de statut WS — pas de wrapper supplémentaire.

## Tests

Étendre `frontend/src/components/parcours/steps.test.tsx` :
- Conserver le test d'état vide (`!hasActive && !running → indice`).
- Ajouter : run actif (`running={true}`) → `StepSuivre` rend la courbe (`<h2>Évolution en direct</h2>`)
  ET le dashboard (`Visualisation 2D`). Harnais existant (QueryClient + ToastProvider + `apiFetch`
  mocké ; `LiveEvolution`/`useWebSocket` tolèrent jsdom — déjà couvert par `LiveEvolution.test.tsx`).

## Périmètre & contraintes

- 1 fichier composant (`StepSuivre.tsx`) + 1 test (`steps.test.tsx`).
- TypeScript strict, no `any`. Copie FR. Frontend-only.
- Gate : `npm --prefix frontend run test` (complet) + `npm --prefix frontend run build` verts.
- Branche `feat/frontend-suivre-evolution`, commit de code unique.

## Non-objectifs (YAGNI)

- Pas de `FlatlandViewer`/`LiveMetrics` dans Suivre (doublons).
- Pas de toggle/onglets (placement empilé simple, validé).
- Pas de refonte de `LiveEvolution`.

## Risque

Quasi nul : compose un composant existant et testé. `LiveEvolution` gère seul l'absence de flux WS
(état « hors-ligne »). Frontend-only → aucun conflit avec la session backend parallèle.
