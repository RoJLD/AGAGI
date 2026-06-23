# Design — `/ws/evolution` : suivi live d'un run lancé

Date : 2026-06-23
Statut : validé (brainstorming)

## Problème

L'endpoint WebSocket `/ws/evolution` est **dormant** : il rejoue `data_service.stream_experiment_updates()`,
c.-à-d. une liste finie de générations historiques relues depuis les CSV de résultats, avec un `sleep(0.05)`.
Aucun composant frontend ne le consomme. Le live « biosphère » (`LiveMetrics` via `/ws/flatland`) existe et
fonctionne, mais il n'y a **aucun suivi temps-réel des métriques d'évolution** (fitness / accuracy / taille
par génération) d'une expérience lancée depuis le Bac à sable.

## Objectif

Quand on lance une expérience via le Bac à sable, streamer **en direct** ses métriques par génération dans une
nouvelle vue « Évolution en direct ». Contrainte forte : **zéro risque de non-reproductibilité** et **zéro
impact** sur les runs CLI / tests / sessions parallèles.

## Principe directeur

Découplage maximal par **observation d'un artefact** (tail d'un fichier), pas d'accès à la simulation :

- Le producteur (run) **append** des événements JSONL dans un puits, **uniquement si activé** par une variable
  d'environnement posée par le sandbox au lancement. Sinon : **no-op total**.
- Le WS **tail -f** ce fichier et pousse chaque événement. Il n'importe pas la sim, ne la bloque pas, survit à
  son crash (le fichier persiste).

L'env-gate est ce qui neutralise le risque non-repro : append-only fichier, aucun accès au KuzuDB ambiant,
aucun chemin de code modifié pour un run non lancé par le sandbox.

## Architecture (5 unités)

### 1. Producteur — `src/seed_ai/live_progress.py` (nouveau)

```python
def emit_progress(event: dict) -> None:
    """Append un événement de progression au puits live SI AGISEED_LIVE_PROGRESS est défini.
    No-op sinon (runs CLI / tests). Ne propage JAMAIS d'exception : la télémétrie ne doit pas
    pouvoir faire échouer le run qu'elle observe."""
```

- Lit `os.environ.get("AGISEED_LIVE_PROGRESS")`. Vide/absent → `return` immédiat.
- Sinon : ouvre le fichier en append, écrit `json.dumps(event) + "\n"`, le tout sous `try/except: pass`.
- **Schéma d'événement** : `{"run": str, "generation": int, "fitness": float, "accuracy": float | None, "size": int | None}`.
  Champs absents tolérés côté consommateur.

### 2. Instrumentation — `src/seed_ai/evolution.py`

- **Un seul** appel `emit_progress({...})` dans la boucle d'évolution, une fois par génération (là où
  `self.generation`, la fitness du meilleur et la taille sont disponibles).
- Opt-in via env → le comportement par défaut (CLI, tests) est strictement inchangé.
- MVP : on instrumente **uniquement** cette boucle centrale. Les autres scripts (`tools/*.py`) peuvent adopter
  le contrat plus tard en important `emit_progress`.

### 3. Câblage sandbox — `backend/app/services/sandbox_service.py`

Dans `start()`, avant le `Popen` du process principal :
- Définir `env["AGISEED_LIVE_PROGRESS"] = str(PROGRESS_PATH)` avec `PROGRESS_PATH = results/live_progress.jsonl`.
- **Vider** le fichier (le (re)créer tronqué) pour que chaque run reparte propre.
- Un seul run actif à la fois : déjà garanti par `start()` (rejet si un run tourne) → un seul fichier fixe suffit.

### 4. Service tail + WS — `backend/app/services/live_progress_service.py` (nouveau) + `main.py`

- Service de lecture incrémentale : conserve un offset, lit les octets ajoutés depuis le dernier read, découpe
  en lignes complètes, parse chaque ligne JSON (skip si invalide). **Reset de l'offset si la taille du fichier
  a rétréci** (signal d'un nouveau run qui a tronqué le fichier).
- `/ws/evolution` réécrit (remplace le rejeu de `stream_experiment_updates`) :
  1. `accept()`.
  2. Boucle : lit les nouveaux événements via le service, les envoie en `send_json`, `await asyncio.sleep(intervalle)`
     (~0.25 s). Fichier absent → on poll sans erreur jusqu'à apparition ou déconnexion.
  3. `WebSocketDisconnect` → sortie propre.
- Chemin du fichier **overridable** (paramètre / attribut) pour les tests.

### 5. Vue — `frontend/src/components/LiveEvolution.tsx` (nouveau)

- Consomme `/ws/evolution` via le hook existant `useWebSocket` (reconnect/backoff déjà gérés).
- Accumule les événements en points (buffer borné, ex. 200), groupés par `run`/gate.
- Rend des sparklines fitness / accuracy / taille par génération (réutilise le style `chart-svg` / tokens viz).
- Empty state : « Aucun run en cours — lance une expérience via le Bac à sable. »
- Câblage onglet : **par défaut, nouvel onglet « Évolution en direct »** (famille *Expérimentation*). Exception :
  si `tabs.ts` expose déjà une clé `evolution` dormante / sans contenu réel, on la réutilise plutôt que d'en
  ajouter une. Décision finale prise à l'implémentation après lecture de `tabs.ts`, mais le défaut est le nouvel onglet.

## Flux de données

```
sandbox.start (pose env + vide fichier)
   → boucle d'évo : emit_progress(event)  [si env défini]
      → append results/live_progress.jsonl
         → WS /ws/evolution : tail -f, parse, send_json
            → useWebSocket → LiveEvolution : sparklines
```

## Gestion d'erreur

| Point | Comportement |
|---|---|
| `emit_progress` | `try/except: pass` — jamais d'exception propagée |
| Env absent | no-op (runs CLI / tests inchangés) |
| Fichier absent au connect WS | poll jusqu'à apparition / déconnexion, sans erreur |
| Truncation (nouveau run) | taille < offset → reset offset |
| Ligne JSON invalide | skip la ligne |
| Déconnexion client | sortie propre (`WebSocketDisconnect`) |
| Front WS coupé | reconnect/backoff (hook existant) + empty state |

## Tests

- **Backend unit** :
  - `emit_progress` no-op quand `AGISEED_LIVE_PROGRESS` absent ; écrit une ligne JSONL quand présent (tmp_path).
  - Service tail : lecture incrémentale (2 reads successifs → seulement les nouvelles lignes) ; reset sur
    truncation ; skip ligne invalide.
  - WS : `TestClient.websocket_connect("/ws/evolution")` avec chemin overridé vers un tmp ; écrire un événement →
    le recevoir.
- **Frontend** : test de rendu `LiveEvolution` (liste d'événements → points / sparklines ; empty state).
- **Pas de changement OpenAPI** (les WS ne sont pas dans le schéma) → pas de drift, pas de regen `schema.ts`.

## Scope / YAGNI

- Instrumentation limitée à la boucle d'évo centrale (`evolution.py`) ; contrat documenté pour adoption ultérieure.
- Un seul fichier de progression, chemin fixe, cohérent avec « un run actif ».
- Pas de persistance long-terme des événements live (le fichier est éphémère, vidé à chaque run) ; l'historique
  reste servi par `results/<name>_<seed>.json` et l'onglet Historique des runs.

## Hors scope

- Instrumenter tous les scripts d'expérience.
- Multi-run concurrent / multi-fichiers.
- Rejeu historique via WS (déjà couvert par les vues data-driven existantes).
