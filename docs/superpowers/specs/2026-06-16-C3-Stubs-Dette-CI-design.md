# Design C3 — Brancher les stubs + Dette/CI (backend)

> Spec de conception. Chantier 3 de la **roadmap backend** (Observabilité → A/B live → Stubs/CI →
> Sécurité). Issu du scan (Dev #5 « nettoyer stubs ») et de la cartographie backend. Brainstorm
> 2026-06-16. Suite de C1 (observabilité) et C2 (multi-run).

## 1. Problème

Trois dettes liées par un thème : **des endpoints qui mentent ou échouent en silence**, et un trou de
couverture qui les laisse passer.

1. **`strategy.py` ment** : quand KuzuDB n'a pas de données de stratégie, il renvoie un **mock silencieux**
   (`StoneAge (Mock)`, `Tabula_Rasa`/`NTM_Memory` avec des fitness inventés, l.100-130) — la « donnée
   fantôme » que C1 dénonce. Le schéma interrogé (`WorldVersion`/`CREATED_SPECIES`/`Experiment`) *existe*
   (créé par `experiment_tracker.py`) mais n'est peuplé que si un run appelle ces méthodes.
2. **Le nœud `Article` a deux schémas incompatibles** : `Sociologist` (`src/graph_rag/sociologist.py:109`)
   crée `Article{… timestamp}` (int), contre `date` (string) partout ailleurs (`async_logger:185`,
   `experiment_tracker:223`, `librarian`). La route `/sociologist/articles` interroge `a.timestamp` →
   colonne inexistante → `except` → **renvoie toujours `[]`** (bug dormant, jamais vu).
3. **Trou CI** : `ci.yml:27` ne lance que `test_backend.py` + `test_visualization.py`. **Les tests C1
   (`test_observability`) et C2 (`test_flatland_manager`) ne tournent pas en CI** → régressions possibles.

## 2. Décisions (figées)

| # | Fork | Choix |
|---|---|---|
| 1 | Stub strategy | **Honnêteté** : supprimer le mock, renvoyer un état vide + flag `source` |
| 2 | Schéma Article | **Unifier sur `date`** (string) — `Sociologist` est l'intrus, on le corrige |
| 3 | CI | Ajouter `test_observability` + `test_flatland_manager` + nouveaux tests C3 à la ligne pytest |
| 4 | Test sandbox | **Inclus** — chemins d'erreur + statut/logs, **sans** lancer de vrai subprocess |
| 5 | Périmètre | backend + 1 fichier moteur (`src/graph_rag/sociologist.py`) ; *pas* de frontend |

## 3. Architecture

```
backend/app/routes/strategy.py
  get_strategy_tree() : supprimer le fallback mock (l.100-130) ; ajouter "source":
    - resultats DB -> {"tree":..., "sankey":..., "source": "live"}
    - DB vide       -> {"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "empty"}
    - exception     -> {"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "error"}

src/graph_rag/sociologist.py
  publish_article() : CREATE (a:Article {... timestamp: N}) -> {... date: 'YYYY-mm-dd HH:MM:SS'}
    (date_str via datetime.fromtimestamp(...).strftime, comme async_logger:160)

backend/app/routes/sociologist.py
  ArticleResponse : champ timestamp:int -> date:str
  get_articles()  : query "a.timestamp ORDER BY a.timestamp DESC" -> "a.date ORDER BY a.date DESC"
                    et row[3] -> date (string)

.github/workflows/ci.yml
  l.27 pytest : + tests/test_observability.py tests/test_flatland_manager.py
                + tests/test_strategy.py tests/test_sociologist.py tests/test_sandbox.py

tests/ (nouveaux)
  test_strategy.py   : DB vide -> source:"empty", mock absent
  test_sociologist.py: /sociologist/articles contre DB temp Article{date} -> renvoie l'article
  test_sandbox.py    : get_status()/stop()/start(erreurs)/get_logs() sans subprocess
```

## 4. `strategy.py` — honnête

Supprimer le bloc `else:` du fallback mock (l.100-130). Restructurer :
- `has_results` vrai → construire `tree_data`/`sankey_data` comme aujourd'hui, ajouter `"source": "live"`.
- `has_results` faux → `{"tree": {}, "sankey": {"nodes": [], "links": []}, "source": "empty"}`.
- `except` (l.136-138) → ajouter `"source": "error"`.

Le frontend distingue ainsi *vide légitime* (pas encore de run) de *vrai* — fini le faux `StoneAge (Mock)`.
**Backward-compatible** : `tree`/`sankey` restent présents ; `source` est purement additif.

## 5. `Article` — unifier sur `date`

`date` est le schéma majoritaire (3 créateurs sur 4) et celui que `data_service`/`/api/articles`
servent déjà. On aligne l'intrus :
- **`src/graph_rag/sociologist.py`** : calculer `date_str = datetime.datetime.fromtimestamp(time.time())
  .strftime("%Y-%m-%d %H:%M:%S")` et remplacer `timestamp: {timestamp}` par `date: '{date_str}'` dans le
  `CREATE (a:Article …)`. *(Le `return article_id, content` est inchangé.)*
- **`backend/app/routes/sociologist.py`** : `ArticleResponse.timestamp:int` → `date:str` ; requête
  `RETURN a.id, a.title, a.content, a.date ORDER BY a.date DESC` ; mapping `row[3]` → `"date"`.

`date` est un string `"YYYY-mm-dd HH:MM:SS"` qui trie lexicographiquement = chronologiquement → `ORDER BY
a.date DESC` correct.

## 6. CI — fermer le trou

`ci.yml:27` :
```yaml
run: python -m pytest tests/test_backend.py tests/sandbox/test_visualization.py
     tests/test_observability.py tests/test_flatland_manager.py
     tests/test_strategy.py tests/test_sociologist.py tests/test_sandbox.py -q
```
*(Liste explicite plutôt que `tests/` entier : la suite complète inclut des tests longs/lourds — biosphère, KuzuDB lourde — inadaptés à la CI. On ajoute les tests backend rapides.)*

## 7. Tests

- **`tests/test_strategy.py`** (TestClient ou service) : `GET /api/strategy/strategy_tree` sur une DB
  absente/vide → `source` ∈ {`"empty"`, `"error"`} ; la réponse ne contient **pas** `"StoneAge (Mock)"`
  ni `"Tabula_Rasa"` (preuve que le mock est mort).
- **`tests/test_sociologist.py`** : créer une DB KuzuDB temp avec une table `Article(id,title,content,date)`
  + 1 ligne ; pointer `kuzu_service.db_path` dessus (monkeypatch) ; `GET /api/sociologist/articles` →
  renvoie l'article avec son `date` (prouve le fix). DB absente → `[]` (pas d'exception).
- **`tests/test_sandbox.py`** (instancier `SandboxService()` frais, **aucun** subprocess) :
  - `get_status()` → `running: False`.
  - `stop()` → `{"status": "success", "message": "Aucune expérimentation en cours"}`.
  - `start({})` → erreur "Aucun script principal spécifié".
  - `start({"script_name": "__nope__.py"})` → erreur "Script introuvable".
  - `get_logs()` → `[]` ; après `svc._logs.append("x")` → `["x"]`.
  - `get_available_scripts()` → liste non vide (contient des `.py`).

## 8. Gestion d'erreurs

- `strategy_tree` ne lève jamais (try/except global déjà présent) ; `source:"error"` sur exception.
- `sociologist/articles` : DB absente/illisible → `[]` (comportement conservé).
- Aucun test ne lance de vrai subprocess (sandbox) ni de vrai run biosphère.
- Le fix `Sociologist` ne change pas la signature (`publish_article` renvoie toujours `(article_id, content)`).

## 9. Critères de succès

1. `strategy_tree` ne renvoie **jamais** `StoneAge (Mock)` ; `source` distingue live/empty/error.
2. `/sociologist/articles` renvoie les articles réels (schéma `date`) au lieu de `[]`.
3. La CI exécute les tests C1, C2 et C3.
4. `test_sandbox`/`test_strategy`/`test_sociologist` verts ; suites backend non régressées.

## 10. Hors périmètre (YAGNI)

- **Câbler `experiment_tracker` (WorldVersion/CREATED_SPECIES) dans les runners** pour peupler la stratégie
  réelle — plus gros, incertain ; C3 rend juste le vide honnête.
- **UI frontend** « pas encore de données » qui consomme `source` — session backend.
- **Dé-dupliquer `/api/articles` (data_service) vs `/sociologist/articles`** — redondance notée, pas traitée.
- **Test sandbox de bout en bout** (lancer un vrai `main_biosphere`) — trop lourd pour la CI.
- **Auth** sur ces endpoints — Chantier 4.

## 11. Dépendances

- `strategy.py`, `sociologist.py` (route + classe `src/graph_rag/sociologist.py`), `sandbox_service.py`,
  `kuzu_service.py` — existants.
- `ci.yml` — existant. `tests/test_backend.py` (TestClient), patterns KuzuDB temp — existants.
- C1 (`/api/health/kuzu` rend le vide visible) — livré. Pas de dépendance de code dure.
