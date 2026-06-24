# Roadmap Frontend / UI-UX — AGIseed Dashboard

> **But** : faire passer le dashboard de *visualiseur* à **instrument de méthode expérimentale**,
> au service du chercheur qui lance, compare et valide des expériences (Commandement 15 :
> *1 variable, multi-seed, powerer avant de conclure*).
>
> **Périmètre** : `frontend/` (React 18 + Vite 5 + TS + D3 + recharts) et les points
> `backend/app/` qui le conditionnent directement. La roadmap **scientifique** reste `roadmap.md`.
>
> Source : audit du 2026-06-14 (cette session).

---

## Architecture actuelle

```
React SPA (App.tsx) ──fetch/WS──> FastAPI (backend/app/main.py) ──┬─> results/*.{csv,json}  (data_service)
 9 onglets, état 100% local        8 routers                      ├─> KuzuDB              (articles, timeline)
 pas de routeur ni de store                                       └─> subprocess python  (sandbox_service)
```

- **Onglets** : `edr`, `live`, `evolution`, `comparison`, `topology`, `academy`, `laboratoire`, `timeline`, `sandbox`.
- **Viz** : D3 force-graph (topology, timeline), SVG fait main (evolution, EDR, sparklines), canvas 2D (sandbox LiveWorld, FlatlandViewer), recharts (télémétrie uniquement).

### Acquis à préserver
- `SandboxView` = pupitre de contrôle (script, `seed`, `mutation_rate`, monde, modules post-mortem, live world + console + télémétrie + god-mode).
- Biosphère live via WebSocket `/ws/flatland` (`LiveMetrics`).
- Dashboard EDR narratif (`EDRDashboard`).

---

## Problèmes recensés (par sévérité)

### P0 — Bugs / incohérences visuelles
| # | Problème | Localisation |
|---|---|---|
| P0-1 | **Tokens CSS fantômes** : `--color-bg/-accent/-text/-text-dim/-border` référencés 11× mais **jamais définis** → fallback navigateur, contrastes cassés | `LaboratoryView.tsx`, `SandboxView.tsx` vs `styles.css` |
| P0-2 | **Deux thèmes télescopés** : App/dashboard = clair (`#f8fafc`) ; panneaux live = sombre catppuccin codé en dur (`#1e1e2e`, `#cba6f7`) | `styles.css` vs `SandboxView.tsx`/`LiveMetrics.tsx` |
| P0-3 | **Styles inline massifs** (~50 dans SandboxView) → non thémable, dupliqué | `SandboxView.tsx`, `LaboratoryView.tsx` |
| P0-4 | **Onglets = clés techniques brutes** (`edr`, `laboratoire`…) sans libellés humains ni icônes | `App.tsx` |

### P1 — Architecture frontend
| # | Problème |
|---|---|
| P1-1 | **Aucun data-layer** : `fetch` brut par composant, pas de cache → **polling massif** (`setInterval` 500 ms / 1 s / 2 s / 3 s / 5 s), boucles concurrentes, sans backoff ni annulation |
| P1-2 | **Pas d'états loading/error/empty unifiés** ni de toasts ; gestion d'erreur en `string` ad hoc |
| P1-3 | **Pas de routing** : onglet en `useState` → URL non partageable/bookmarkable |
| P1-4 | **Composant mort** : `FlatlandViewer.tsx` (pan/zoom, terrain, HP bars) défini mais jamais monté ; doublonné par le `LiveWorld` minimal de Sandbox |

### P2 — Dette repo / qualité
| # | Problème |
|---|---|
| P2-1 | **Artefacts à la racine** : `dump.txt`, `dump2.txt`, `SandboxView_full.tsx`, `SandboxView_recovered.json`, `recover.py`, `extract.py` |
| P2-2 | **Tests quasi nuls** : 1 e2e Playwright, pas de Vitest/RTL |
| P2-3 | **`recharts` sous-utilisé** (télémétrie seule) vs SVG fait main partout → stack viz incohérente |

### P3 — Backend en rapport direct
| # | Problème |
|---|---|
| P3-1 | **CORS `*` + aucune auth** ; sandbox lance des scripts Python **arbitraires** sans limites (cf. garde-fous roadmap avant RSI) |
| P3-2 | **API « fichier » fragile** : télémétrie en *tail* CSV, monde via `state.json`, god-mode via `interventions.json` ; pas de schéma versionné |
| P3-3 | **`/ws/evolution` rejoue tout l'historique** en boucle au lieu d'un vrai flux |
| P3-4 | **Stubs** : `academy` en dur dans `data_service` ; strategy/sociologist partiellement mockés |

---

## Le gap central : l'UX scientifique

Le projet revendique une méthode forte ; **l'outil ne la soutient pas encore.**

| Besoin chercheur | Aujourd'hui | Manque |
|---|---|---|
| Lancer une expé reproductible | Sandbox OK, config inline | presets, validation, **file d'attente de runs**, provenance (commit+config ↔ KPI) |
| Comparer 2 lignées **rigoureusement** | onglet `comparison` = barres descriptives | **IC, taille d'effet, multi-seed, A/B live** (déjà demandé roadmap #5 Dev) |
| Savoir si un résultat *tient* | rien | overlay multi-seed, bandes de variance |
| Capitaliser les findings | Sociologue (LLM) OK | lien finding ↔ run ↔ EDR |

---

## Roadmap priorisée (vagues)

### Vague F0 — Fondations (débloque tout le reste)
1. **Design system réel** : définir les tokens CSS manquants (P0-1), thème clair **+ sombre** unifié (P0-2), primitives (Button, Card, Select, Field, Badge, Stat, Tabs) pour tuer les styles inline (P0-3).
2. **Couche données** : `react-query` (ou store + hook WS unique) → supprime le polling redondant (P1-1), centralise loading/error/empty (P1-2), prépare le cache nécessaire au A/B.
3. **Nettoyage repo** : supprimer les artefacts (P2-1), monter ou retirer `FlatlandViewer` (P1-4).

### Vague F1 — Coquille & navigation
4. **Routing** (URL par onglet + état sélectionné) (P1-3) ; libellés/icônes d'onglets humains (P0-4).
5. **Layout responsive** propre, topbar + sidebar repensées.
6. **Toasts + error boundary** globaux.

### Vague F2 — Instrument scientifique (cœur de valeur)
7. **Lanceur d'expériences** : presets, validation de config, **file de runs**, provenance (hash config + commit ↔ KPI).
8. **A/B rigoureux** : comparaison multi-seed avec **IC / taille d'effet / bandes de variance** ; overlay de lignées.
9. **Vue run-en-cours ↔ historique** unifiée ; lien finding (Sociologue) ↔ run ↔ EDR.

### Vague F3 — Durcissement
10. **Tests** : Vitest + RTL (unitaire/intégration) + e2e Playwright élargi (P2-2) ; CI.
11. **Backend** : schémas versionnés pour state/telemetry (P3-2), vrai flux `/ws/evolution` (P3-3), retirer les stubs (P3-4).
12. **Sécurité** : auth + CORS restreint + sandbox bornée **avant** toute exposition réseau (P3-1).

---

## Definition of Done (transverse)
- Zéro style inline pour la couleur/espacement (tout via tokens/primitives).
- Zéro `setInterval` de polling brut hors couche données.
- Thème clair/sombre cohérent sur tous les onglets.
- Chaque vue a des états loading/error/empty explicites.
- URL partageable pour onglet + sélection.

---

## Plan d'implémentation consolidé (specs sous-agents, 2026-06-14)

> Issu de 4 agents de conception en lecture seule. Détails complets : voir les specs ci-dessous.
> **Principe d'exécution** : on ne parallélise que des fichiers disjoints. Tout ce qui touche
> `App.tsx`/`styles.css` est séquencé.

### Décisions d'architecture retenues
| Sujet | Décision |
|---|---|
| **Tokens / thème** | Tokens CSS réels dans `styles.css` ; thème **clair (défaut) + sombre** via `[data-theme]` ; hook `useTheme` (localStorage + `prefers-color-scheme`). Palette data-viz dédiée (`--viz-1..6`) lisible clair ET sombre. Module `theme.ts` pour recharts/canvas (où `var()` ne passe pas). |
| **Primitives UI** | `frontend/src/components/ui/` : `Button`, `Panel`, `Field`, `Badge`, `Stat` → tuent les styles inline. |
| **Couche données** | `@tanstack/react-query` v5 + hook WS unique `useWebSocket` (reconnexion/backoff). Module `api/client.ts` (`BASE_URL`, `apiFetch`, `wsUrl`, `ApiError`) + `queryKeys`. Supprime les **5 `setInterval`** et la double requête `/api/experiments`. Polling déclaratif `enabled: sandboxRunning`. |
| **États transverses** | `ui/Loading`, `ui/ErrorState`, `ui/Empty`, `ErrorBoundary` (par onglet), `ToastContext`. |
| **Navigation** | Routing **maison par hash** (`#/sandbox?gate=...`), pas de `react-router` (SPA plate, pas de rewrite serveur). Onglets = objets `{key,label,icon,family}` ; libellés FR + icônes `lucide-react` ; 4 familles (Observation / Analyse / Expérimentation / Connaissance). |
| **FlatlandViewer** | **Monter** (supérieur à `LiveWorld`) dans l'onglet Sandbox **après** vérif que `/ws/flatland` est alimenté ; sinon le passer en source-en-prop. Retirer `LiveWorld` une fois la parité prouvée. |
| **UX scientifique** | Objet **Run** = extension du JSON `Harness.save()` (`results/<run_id>.json`) + `results/runs_index.json`. Backend `runs_service` + endpoints `/api/runs*` réutilisant `src/seed_ai/eval_harness.welch/verdict` (zéro nouvelle dép Python). Lanceur (presets localStorage, validation, **file multi-seed séquentielle**), vue **A/B** (bandes IC 95 %, Cohen's d, verdict aligné sur les seuils `t≥2.5, d≥0.8`), liaison **finding ↔ run ↔ EDR**. |
| **Tests** | `vitest` + RTL (unitaire/intégration) ; e2e Playwright élargi (nav par `data-testid`, hash bookmarkable) ; corriger le bug CI port `8000`→`8001`. |

### Dépendances nouvelles proposées
- `@tanstack/react-query@^5` (dep) — cache/dédup/backoff, supprime le polling manuel.
- `lucide-react` (dep) — icônes d'onglets (tree-shakable ; repli emoji = 0 dép possible).
- `vitest` + `jsdom` + `@testing-library/{react,jest-dom,user-event}` (dev) — tests.
- Aucune dép de routing (hash maison).

### Vagues d'exécution (anti-conflit)
- **Vague A — Fondations (frontend-only, parallélisable : fichiers disjoints)**
  - A1 Design system : `styles.css` (tokens) + `useTheme` + `ui/{Button,Panel,Field,Badge,Stat}` + `theme.ts`.
  - A2 Infra données : `api/client.ts`, `queryKeys`, `useWebSocket`, `ui/{Loading,ErrorState,Empty}`, `ErrorBoundary`, `ToastContext`, `QueryClientProvider` dans `main.tsx`, ajout deps.
  - A3 Nettoyage : supprimer `dump.txt`, `dump2.txt`, `SandboxView_full.tsx`, `SandboxView_recovered.json`, `recover.py`, `extract.py` + `.gitignore`.
- **Vague B — Migration des vues (séquencé sur `App.tsx`, parallèle par composant)** : brancher chaque composant sur react-query + tokens + primitives ; routing hash + onglets FR/icônes + toggle thème + `ErrorBoundary` dans `App.tsx` (1 seul propriétaire) ; monter FlatlandViewer.
- **Vague C — Instrument scientifique** : backend `runs_service`/endpoints, puis `RunnerPanel`+`RunQueuePanel`, `ABComparisonView`/`ABVerdictCard`, liaison findings.
- **Vague D — Durcissement** : tests Vitest/RTL + e2e élargi + CI ; (sécurité backend = `roadmap.md`, hors front).

### Frontend-only vs besoin backend
- **Frontend-only** : tout A et B, presets/validation/file (UI), rendu bandes IC + verdict.
- **Backend requis** : endpoints `/api/runs*` (scan `results/`, calcul welch/Cohen), `POST /analyze` par `run_id`, extension `Harness.save()`.

---

## Automatisation — auto-injection au frontend (idées à faire, 2026-06-15)

> Cadre : **détecter → scaffolder → curer**. On automatise les **données** et les **types**, pas l'UX
> (générer des composants génériques tuerait la valeur design). La gate *détecte* le drift ; ces idées
> le *suppriment par construction* ou le *réparent*.

**Déjà automatique (vues data-driven livrées)** : nouveaux runs/résultats → onglet *Historique des runs* + conditions/métriques *A/B* ; nouveaux EDR → *Academy* (`get_academy_data` dérive de `docs/EDR`+`edr_findings.json`) ; articles Sociologue → *Laboratoire*.

**État (par ROI décroissant) :**
1. ✅ **Codegen OpenAPI → TS** — `npm run gen:api` / `make api-types` (npx `openapi-typescript` sur `/openapi.json`) + **drift-gate CI** (`git diff --exit-code`). Drift *schéma↔types* supprimé par génération. *(livré)*
2. ✅ **Scaffolder de carte EDR** — `parity_check --fix` / `make edr-stubs` : appose un stub (`stub:true`, séries vides) pour chaque EDR documenté non curé ; `EDRDashboard` les garde en section « non curés ». Gendarme → assistant. *(livré)*
3. ✅ **Onglet EDR « 100 % couverture »** — `GET /api/edr/docs` + section « non curés » dans `EDRDashboard`. *(livré)*
4. ✅ **Vue « Santé / parité »** — onglet Santé rendant `GET /api/health/parity` (rapport `parity_check`). *(livré)*
5. *(plus loin, YAGNI)* **Manifest-driven tabs** — onglets déclarés dans un manifeste `{clé→endpoint→composant}` ; nouvel item = onglet auto-monté. À ne faire que si les vues cessent d'être sur-mesure.

---

## État d'avancement (2026-06-22)
- **F0** ✅ · **F1** (routing/onglets/toasts/ErrorBoundary ✅ ; **F1.5 responsive/topbar/sidebar ✅**) · **F2** (lanceur+presets+file ✅, A/B IC/Cohen/verdict ✅, **Historique runs + deep-link A/B ✅**) · **F3.10 tests ✅**.
- **F2.9** ✅ lien *finding ↔ run ↔ EDR* (PATCH `/api/runs/{id}/links`, badges « runs liés », store `results/run_links.json`).
- **F3.11** ✅ `response_models` Pydantic sur `/api/runs` (durcit le typage + précise le codegen TS).
- **F3.12** ✅ sécurité **opt-in / env-gated / non-breaking** : sandbox bornée (liste blanche, anti-traversal, *actif*), CORS via `AGAGI_CORS_ORIGINS`, auth Bearer via `AGAGI_API_TOKEN` (mutations `/api`), front `VITE_API_TOKEN`. Gate : 8 tests dans `tests/test_backend.py` (CI) ; `.env.example` backend+front.
- **Tokenisation d3 dark-mode** ✅ : `TopologyViewer` (label nœuds → `--color-on-accent`), `EDRDashboard` (chrome graphiques → `--color-text-*`/`--color-border-subtle`), `TimelineViewer` (liens/nœuds/labels → tokens + `--viz-*`). `RadarChart` était déjà tokenisé. Canvas *monde/jeu* (`FlatlandViewer`, `SandboxView`) laissés en couleurs sémantiques (indépendantes du thème, par design).
- **Articles Sociologue ↔ runs** ✅ : `/sociologist/analyze` lie l'article aux conditions comparées (sidecar `results/article_links.json`, pattern F2.9) ; `GET /api/runs/article-links` (inverse `{run_id: [article_id]}`) + `RunLinks.articles` ; badges « N article(s) » et deep-link Laboratoire dans `RunsHistoryView`. Boucle finding↔run↔EDR↔article bouclée.
- **WS `/ws/evolution` temps-réel** ✅ : suivi live d'un run lancé. Producteur `emit_progress` (opt-in env `AGISEED_LIVE_PROGRESS`, no-op par défaut) instrumenté dans `CurriculumRunner` ; sandbox arme/vide le puits ; `/ws/evolution` tail -f ; vue « Évolution en direct » (sparkline) dans l'onglet Évolution.
- **Roadmap frontend (features F0→F3) : terminée.** → ouverture de la **Vague G (dette & qualité)** ci-dessous.

---

## Vague G — Dette & qualité (audit 2026-06-23)

Audit complet du frontend (architecture, UX/a11y, design system, perf/bundle, tests). Base saine et cohérente ; tokenisation dark quasi complète ; `strict: true`. Les pistes ci-dessous sont **indépendantes** (chacune = son cycle spec → plan → impl) et **priorisées par ROI** (impact / effort / risque).

### G1 — Perf : lazy-load + découpage bundle  ⭐ priorité 1 (quick win)
*Impact élevé · effort faible · risque quasi nul.*
- `recharts` (**438 kB / 132 kB gzip**, le plus gros chunk) n'est importé que par `SandboxView` ([SandboxView.tsx:11](frontend/src/components/SandboxView.tsx#L11)) mais chargé au démarrage ; `d3` (~107 kB) via Topology/Timeline ; **aucun `React.lazy`/`Suspense`** ([App.tsx:1-26](frontend/src/App.tsx#L1-L26)).
- Action : `React.lazy` + `Suspense` (fallback `Loading`) sur les vues lourdes (`SandboxView`+recharts, `TopologyViewer`/`TimelineViewer`+d3, `FlatlandViewer`). Mesurer la chute du chunk initial.

### G2 — Architecture : dégonfler le god-component App.tsx  · priorité 2
*Impact moyen (maintenabilité/testabilité) · effort moyen · risque faible.*
- App.tsx = **381 lignes** ; extraction incohérente : 7 onglets sont des composants, mais `evolution`/`comparison`/`topology`/`academy` sont rendus **inline** avec helpers chart (`createLinePath`, `ChartLine`, `createStabilitySeries`) et `summaryMetrics` ([App.tsx:32-124](frontend/src/App.tsx#L32-L124), [241-364](frontend/src/App.tsx#L241-L364)).
- Action : extraire `EvolutionView` / `ComparisonView` / `TopologyView` / `AcademyView` (+ helpers chart dans `lib/`), App ne garde que le shell + routing. Synergie avec G1 (vues extraites = lazy-load propre) et G4 (vues isolées = testables).

### G3 — UX : parcours chercheur guidé  · priorité 3 (plus de valeur perçue, design-lourd)
*Impact produit élevé · effort élevé (design d'interaction) · risque moyen.*
- Aujourd'hui lancer (Sandbox) → suivre (Évolution/Temps réel) → comparer (Comparaison) → historique (Runs) = 4 onglets disjoints, sans fil conducteur ; le live est même séparé du lanceur.
- Action : concevoir un flux d'expérimentation cohérent (lancer→suivre live au même endroit→comparer→conclure). Le plus aligné avec l'intention produit initiale (« le scientifique qui visualise ET lance »). À brainstormer à part.

### G4 — Accessibilité + cohérence des états  · priorité 4 (transverse, interleavable)
*Impact moyen (qualité/inclusivité) · effort faible-moyen · risque faible.*
- a11y faible (12 `aria-`/`role`, surtout `role="img"` SVG) ; nav onglets en `<button>` bruts sans `role="tablist"`/`aria-selected` ([App.tsx:156-172](frontend/src/App.tsx#L156-L172)) ; états « Chargement... » ad hoc inline au lieu des primitives `Loading`/`Empty` ([App.tsx:261](frontend/src/App.tsx#L261), [321](frontend/src/App.tsx#L321), [361](frontend/src/App.tsx#L361)).
- Typage d3 : `TopologyViewer`/`TimelineViewer` truffés de `(d: any)` ; tests exclus du tsconfig ; couverture basse (~15 tests / ~17 composants).
- Action : sémantique tablist + `aria-selected`/focus, labels de formulaires, uniformiser loading/error/empty ; typer les callbacks d3.

**Ordre recommandé** : G1 (gain immédiat, débloque rien) → G2 (assainit, prépare G1bis + G4) → G3 (flagship UX) → G4 (interleavable en continu). Réordonnançable selon priorité produit.
