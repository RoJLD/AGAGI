# J4 — Extraction du pilote de file RunLauncher (`lib/queue.ts`)

> Vague J, item J4. Frontend-only. Robustesse RunLauncher : la state machine de file
> multi-seed n'est aujourd'hui pas testée (intriquée dans un `useEffect`).

## Objectif

Extraire le pilote séquentiel de la file multi-seed de `RunLauncher.tsx` vers un module
**pur** `lib/queue.ts`, testable sans React/réseau/timers, et corriger un bug latent de
matching seed-vs-id au passage.

## Contexte (état actuel)

Tout le pilote vit dans `RunLauncher.tsx` :
- `enqueue` (l.59-71) : construit `n_seeds` items, dédup par `id` (`script#seed`).
- `useEffect` polling (l.95-124) : pilote séquentiel (le backend ne tient qu'un subprocess).
  Utilise une ref `launched: { seed, sawRunning }` + la garde `sawRunning`.
- `counts` (l.126-129) : tally par statut.

Trois pièces d'état séparées : `useState queue`, `useState queueRunning`, `useRef launched`.
Aucun test ne couvre ces transitions.

### Bug latent corrigé

Le driver marque `done`/`error` par `it.seed === seed` (l.104, 120) alors que la dédup
est par `id`. Le chemin **erreur** (l.120) n'a même pas de garde de statut → deux items de
scripts différents partageant une seed seraient marqués `error` ensemble. Le réducteur pur
trace l'item courant **par id**, ce qui élimine le bug ; un test le verrouille.

## Architecture : functional core / imperative shell

`queueTick` ne lance aucun `fetch` ni `setState` — il retourne un **descripteur d'effet** que
le shell (composant) interprète. Tout le séquencement se teste par assertions pures.

### État modélisé (un seul objet)

```ts
interface QueueState {
  items: QueuedRun[];                                   // {id, seed, status}
  running: boolean;                                     // file active (ex-queueRunning)
  current: { id: string; sawRunning: boolean } | null;  // ex-launched, clé par ID
}
```

### Effet

```ts
type QueueEffect =
  | { type: "start"; id: string; seed: number }  // shell → startRun(seed)
  | { type: "complete" }                          // shell → notify "file terminée"
  | { type: "none" };
```

### API pure (`frontend/src/lib/queue.ts`)

| Fonction | Signature | Rôle |
|---|---|---|
| `buildQueueItems` | `(config: RunConfig) => QueuedRun[]` | n_seeds items `{id:`${script}#${base+i}`, seed, status:"pending"}` |
| `mergeQueue` | `(prev: QueuedRun[], incoming: QueuedRun[]) => QueuedRun[]` | dédup par `id`, append des nouveaux, ordre préservé |
| `queueTick` | `(state: QueueState, sandboxRunning: boolean) => { state: QueueState; effect: QueueEffect }` | un pas du pilote séquentiel |
| `applyStartFailure` | `(state: QueueState, id: string) => QueueState` | event async : item `id`→`error`, clear `current` si `current.id===id` |
| `stopQueue` | `(state: QueueState) => QueueState` | bouton Stop : `running:false, current:null` |
| `queueCounts` | `(items: QueuedRun[]) => Record<QueueStatus, number>` | tally par statut |

## Logique `queueTick` (transcription fidèle l.95-124, clé-par-id)

```
queueTick(state, sandboxRunning):
  si !state.running                          → { state, none }

  si state.current:
    si sandboxRunning                        → current.sawRunning=true ; { state, none }
    sinon si current.sawRunning:
      items[current.id]: running→done        → current=null ; { state, none }
    sinon                                     → { state, none }   // latence : patiente
    // return : pas de nouveau lancement tant qu'un current existe

  sinon (pas de current):
    si sandboxRunning                         → { state, none }   // sandbox occupée : attendre
    next = premier item "pending"
    si !next                                  → running=false ; { state, complete }
    sinon:
      items[next.id]: pending→running
      current={id:next.id, sawRunning:false}  → { state, start(next.id, next.seed) }
```

Invariant clé conservé — **la garde `sawRunning`** : après `POST /start`, la sandbox n'est
pas instantanément `running` (latence de polling). On attend d'avoir *vu* `running=true` une
fois avant d'accepter `running=false` comme « terminé », sinon on conclurait un run avant
qu'il démarre.

Pureté : `queueTick` ne mute jamais `state` ni `state.items` en place — il retourne de
nouveaux objets/tableaux (le shell compare la référence pour décider de commit).

## Recâblage `RunLauncher.tsx`

- Remplacer `useState queue` + `useState queueRunning` + `useRef launched` par un unique
  `useState<QueueState>({ items: [], running: false, current: null })`.
- `enqueue` : `setState(s => ({ ...s, items: mergeQueue(s.items, buildQueueItems(config)) }))`.
- `useEffect` polling : `const { state: next, effect } = queueTick(state, statusQuery.data.running)`
  → `setState(next)` si `next !== state` → exécute l'effet :
  - `start` → `startRun(seed).catch(() => setState(s => applyStartFailure(s, id)))`
  - `complete` → `notify("File de runs terminée.", "success")`
  - `none` → rien.
- Bouton Stop → `setState(stopQueue)`. Bouton Vider → `setState(s => ({ ...s, items: [] }))`
  (inchangé, gardé sur `!running`). Affichage compteurs → `queueCounts(state.items)`.

### Garde-fou anti-boucle de re-render

Le tick reste **déclenché par le signal de poll** (`statusQuery.data` en dépendance), comme
aujourd'hui. On ne commit l'état que s'il diffère (`next !== state`). `queueTick` est
idempotent à signal constant : un 2ᵉ appel avec le même `sandboxRunning` retourne `none` et
un état égal (référence inchangée quand aucune transition), donc pas de re-déclenchement.

## Tests

### `frontend/src/lib/queue.test.ts` (pur — cœur de J4)

- `buildQueueItems` : n items, ids/seeds corrects, tous `pending`.
- `mergeQueue` : dédup par id, ordre préservé, append des nouveaux.
- `queueTick` — un test par transition :
  - idle + pending + sandbox libre → effet `start`, item→running, current posé
  - current + sandbox running → `sawRunning=true`, effet none
  - current + sawRunning + sandbox libre → item→done **par id**, current cleared
  - current + **pas** sawRunning + sandbox libre → patiente (pas de done prématuré)
  - pas de current + sandbox running (ad hoc) → attente, pas de start
  - plus aucun pending → effet `complete`, running=false
  - `!running` → effet none, état inchangé
  - **deux items même seed, ids différents** → seul l'id lancé passe done (verrou anti-bug)
- `applyStartFailure` : seul cet id → `error`, current cleared ; deux items même seed → un seul.
- `stopQueue` : `running=false`, `current=null`.
- `queueCounts` : tally correct (statuts absents = 0 ou clé absente, cf. usage `?? 0`).

### `frontend/src/components/RunLauncher.test.tsx` (smoke shell)

Test léger de câblage (apiFetch mocké, pas de recharts/timers) : render + clic « Enfiler »
ajoute `n_seeds` badges `pending` dans la file. Valide que le shell délègue bien au module pur.

## Hors-scope (YAGNI)

- Pas de parallélisme de runs (le backend reste mono-subprocess).
- Pas de persistance de la file (reste en mémoire de session).
- Pas de retry automatique sur erreur.
- Pas de refonte UI : présentation badges/compteurs inchangée.

## Contraintes globales

- Frontend-only (aucun fichier backend touché).
- TypeScript strict, **zéro `any`**.
- `tsc` 0 erreur, suite verte.
- Commits path-scoped (tree partagé — sessions parallèles).
- Branche : `feat/frontend-queue-extraction` (depuis `origin/main`), PR vers `main`.
