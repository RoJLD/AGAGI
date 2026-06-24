# Ticket de suivi — minors différés G3/G4 (design)

Date : 2026-06-24
Statut : design approuvé, exécution inline en un commit de code.

## Problème

Les revues finales de G3/G4 ont laissé des minors différés. Six recensés ; deux non
corrigeables proprement (exclus) :
- **c** (états Topology limités à la section motifs) : layout hérité, hors périmètre.
- **f** (warning Node `--localstorage-file`) : bruit de Node 25 (webstorage expérimental),
  pas de fix repo propre, absent en CI LTS.

## Périmètre (b, d, e, a — par priorité)

- **b — landmark `<nav>` (a11y).** La nav globale rend un `<div role="tablist">` (primitive
  `TabList`) sans landmark de navigation. Envelopper le `TabList` de [App.tsx](frontend/src/App.tsx)
  dans `<nav className="topbar-nav">`. Le `<nav>` porte le landmark ; le `TabList` garde son
  `role="tablist"` + `aria-label="Sections du dashboard"`. Le `<nav>` n'a PAS d'`aria-label`
  (nav unique → landmark suffit, évite la double annonce). CSS `.topbar-nav { display: contents; }`
  pour ne pas perturber le flex `.topbar-right` (le landmark reste exposé aux AT).
- **d — commentaires casts d3.** Dans [TimelineViewer.tsx](frontend/src/components/TimelineViewer.tsx),
  commenter les casts `as TimelineNode` (tick `d.source`/`d.target` lignes 71-74 ; `append("title")`
  ligne 67) : `d3.SimulationLinkDatum.source/target` est typé `string | number | T`, résolu en `T`
  par la simulation après init. Pure lisibilité, zéro changement runtime.
- **e — factorisation CSS.** Dans [styles.css](frontend/src/styles.css), fusionner
  `.step-bar .tab.is-done .step-pill__index` et `.step-bar .tab.is-active .step-pill__index`
  (déclarations identiques) en un sélecteur groupé.
- **a — test orientation verticale `TabList`.** Ajouter à [Tabs.test.tsx](frontend/src/components/ui/Tabs.test.tsx)
  un test `orientation="vertical"` : `ArrowDown`/`ArrowUp` déplacent le focus (avec wrap) et
  n'appellent pas `onSelect`. Verrouille le chemin `orientation` aujourd'hui non exercé.

## Contraintes

- TypeScript strict, no `any`. Copie FR. CSS tokens only.
- Périmètre `frontend/src/**` + `styles.css` (+ ce spec). Aucun fichier backend.
- Gate : `npm --prefix frontend run test` (complet) + `npm --prefix frontend run build` verts.
- Commit de code unique (les changements sont indépendants et triviaux).

## Non-objectifs

- Pas de restructuration du layout des vues (c) ni de hack pour le warning Node (f).
- Pas de refonte ; uniquement les 4 corrections ci-dessus.

## Risques

- **b / `display: contents`** : technique standard pour ajouter un landmark sans box ; le rôle
  `navigation` du `<nav>` reste exposé aux AT dans les navigateurs modernes. Vérif build + smoke.
- Coordination session parallèle : frontend-only, commits path-scopés.
