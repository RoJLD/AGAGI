# Design C4 — Sécurité & Sandbox (backend)

> Spec de conception. Chantier 4 (dernier) de la **roadmap backend** (Observabilité → A/B live →
> Stubs/CI → Sécurité). Issu du scan (sécurité : CORS `*`, pas d'auth ; « durcir la sandbox avant la
> RSI »). Brainstorm 2026-06-22. Suite de C1/C2/C3.

## 1. Problème

Le risque dominant n'est pas « pas d'auth » mais une **exécution de code quasi-arbitraire** :
`/api/sandbox/start` (non authentifié) prend `script_name` **du corps de la requête** et lance
`subprocess.Popen([sys.executable, script_name], cwd=PROJECT_ROOT)` avec pour seule garde un
`os.path.isfile`. Donc :
1. `script_name = "../../../x.py"` **s'évade** de `PROJECT_ROOT` (path traversal, même classe que C1).
2. N'importe quel `tools/*.py` est lançable.
3. Couplé à `CORS allow_origins=["*"]`, **n'importe quel site web visité** peut POSTer sur
   `localhost:8000` et déclencher un run.

C'est le garde-fou réclamé **avant d'armer la RSI** (Phase 3) : une boucle auto-modifiante derrière un
endpoint ouvert serait le pire scénario.

## 2. Décisions (figées)

| # | Fix | Posture |
|---|---|---|
| 1 | Whitelist scripts + confinement chemin | **Toujours actif** (sans tradeoff) |
| 2 | CORS restreint à l'origine frontend | **Toujours actif** (sans tradeoff) |
| 3 | Auth par token (header) sur endpoints mutateurs | **Opt-in** via `AGISEED_API_TOKEN` |
| 4 | Timeout subprocess (watchdog) | **Opt-in** via `AGISEED_SANDBOX_TIMEOUT` |
| 5 | Périmètre | backend ; *pas* d'intégration frontend du token (autre session) |

## 3. Architecture

```
backend/app/security.py  (NOUVEAU)
  API_TOKEN = os.environ.get("AGISEED_API_TOKEN") or None   # vide -> None (ouvert)
  require_token(x_api_token: Header(None), authorization: Header(None)) -> None
    - API_TOKEN None  -> autorise (ouvert, preserve le local)
    - sinon : exige X-API-Token == API_TOKEN  OU  Authorization "Bearer <API_TOKEN>", sinon HTTP 401

backend/app/main.py
  CORS allow_origins lus depuis AGISEED_CORS_ORIGINS (CSV) ; defaut localhost:5173,4173 ; plus de "*"

backend/app/routes/{sandbox,flatland,sociologist}.py
  dependencies=[Depends(require_token)] sur les endpoints MUTATEURS :
    sandbox : POST /start, POST /stop, POST /action, DELETE /curriculum_state
    flatland: POST /runs, DELETE /runs/{run_id}
    sociologist: POST /analyze
  (les GET du dashboard restent ouverts)

backend/app/services/sandbox_service.py
  _is_allowed_script(name) -> bool   # dans get_available_scripts() ET chemin resolu dans PROJECT_ROOT
  start(config) : refuse si non autorise -> {"status":"error","message":"Script non autorise: ..."} AVANT tout Popen
  _watchdog(proc, timeout) : thread daemon qui tue proc apres timeout (si AGISEED_SANDBOX_TIMEOUT defini)
```

## 4. Whitelist de scripts + confinement (toujours actif)

```python
def _is_allowed_script(self, name: str) -> bool:
    if not name or not name.endswith(".py"):
        return False
    # 1) confinement : le chemin resolu doit rester DANS PROJECT_ROOT (rejette ../../)
    resolved = os.path.realpath(os.path.join(PROJECT_ROOT, name))
    root = os.path.realpath(PROJECT_ROOT)
    if os.path.commonpath([resolved, root]) != root:
        return False
    # 2) whitelist : doit etre un script DECOUVERT (racine + tools), pas un fichier arbitraire
    return name.replace("\\", "/") in set(self.get_available_scripts())
```

`start()` : tout en haut, après la lecture de `main_script`, si `not self._is_allowed_script(main_script)`
→ retourner `{"status": "error", "message": f"Script non autorisé : {main_script}"}` **avant** la
vérification `isfile` et tout `Popen`/`subprocess.run` (migration incluse). Tue traversal + scripts
arbitraires ; le picker du dashboard (qui propose `get_available_scripts()`) reste pleinement fonctionnel.

## 5. CORS restreint (toujours actif)

```python
import os
_origins = os.environ.get("AGISEED_CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
```

Plus de `*`. *(Note : `allow_origins=["*"]` + `allow_credentials=True` est de toute façon invalide CORS —
les navigateurs le rejettent. La liste explicite corrige aussi ça.)*

## 6. Auth opt-in (`backend/app/security.py`)

```python
import os
from fastapi import Header, HTTPException

API_TOKEN = os.environ.get("AGISEED_API_TOKEN") or None   # "" ou absent -> None (ouvert)

def require_token(x_api_token: str | None = Header(default=None),
                  authorization: str | None = Header(default=None)) -> None:
    if API_TOKEN is None:
        return                                            # ouvert (dev local)
    if x_api_token == API_TOKEN:
        return
    if authorization and authorization.removeprefix("Bearer ").strip() == API_TOKEN:
        return
    raise HTTPException(status_code=401, detail="Token invalide ou manquant")
```

Lecture de l'env **au moment de l'appel** indirectement : `API_TOKEN` est résolu à l'import du module.
Pour la testabilité, le test re-set `security.API_TOKEN` directement (monkeypatch de l'attribut module),
pas seulement l'env. *(Le `require_token` lit la globale `API_TOKEN` du module → monkeypatch fiable.)*

Application : `@router.post("/start", dependencies=[Depends(require_token)])` etc. Importer
`from ..security import require_token` et `from fastapi import Depends` dans chaque route concernée.

## 7. Timeout subprocess opt-in (watchdog)

```python
def _start_watchdog(self, proc, timeout_s: float):
    def _kill_after():
        end = time.time() + timeout_s
        while time.time() < end:
            if proc.poll() is not None:
                return                      # termine seul
            time.sleep(1.0)
        if proc.poll() is None:
            self._logs.append(f"⏱️ Timeout {timeout_s}s atteint -> arret du process")
            try: proc.terminate(); proc.wait(timeout=5)
            except Exception:
                try: proc.kill()
                except Exception: pass
    threading.Thread(target=_kill_after, daemon=True).start()
```

Dans `start()`, après le `Popen` du main : `timeout = os.environ.get("AGISEED_SANDBOX_TIMEOUT")` ; si
défini et numérique > 0 → `self._start_watchdog(self._processes["main"], float(timeout))`. Non défini →
aucun watchdog (runs longs préservés). *(Mémoire/CPU cap cross-platform = différé : Windows exige des Job
Objects, hors périmètre.)*

## 8. Gestion d'erreurs

- Script non autorisé → `{"status":"error", ...}` ; **jamais** de `Popen`/`subprocess.run` (ni migration).
- Auth requise + token absent/faux → **401** (pas 500). `API_TOKEN` vide → traité comme `None` (ouvert).
- Watchdog best-effort (`terminate` puis `kill`), n'affecte pas un run sous le délai ni un run sans timeout.
- CORS : origine non listée → pas d'`Access-Control-Allow-Origin` permissif (comportement standard du middleware).
- Aucun changement de comportement pour les GET du dashboard (restent ouverts).

## 9. Tests

- **`tests/test_security.py`** (TestClient) :
  - `require_token` : `API_TOKEN=None` → un endpoint mutateur (ex. `POST /api/flatland/runs`) passe (pas 401).
  - `API_TOKEN` set (monkeypatch `security.API_TOKEN`) + header absent → **401** ; + `X-API-Token` correct
    → pas 401 ; + `Authorization: Bearer <token>` correct → pas 401 ; + mauvais token → 401.
- **`tests/test_sandbox.py`** (extension) :
  - `_is_allowed_script("main_biosphere.py")` → True (script découvert) ; `"../../evil.py"` → False ;
    `"__inconnu__.py"` → False ; `"main_biosphere.txt"` → False.
  - `start({"script_name": "../../x.py"})` → `status:"error"`, message « non autorisé », et **aucun
    process** créé (`get_status()["running"] is False`).
  - `_start_watchdog` : lancer un subprocess factice (`python -c "import time; time.sleep(30)"`) avec
    `timeout_s=1` → après ~2-3 s, `proc.poll()` n'est plus `None` (tué).
- **`tests/test_backend.py`** ou `test_security.py` : CORS — `OPTIONS`/`GET` avec `Origin:
  http://evil.example` ne renvoie pas `access-control-allow-origin: http://evil.example`.
- **Non-régression** : la liste CI (C1/C2/C3) reste verte ; ajouter `test_security.py` à la CI.

## 10. Critères de succès

1. `start` refuse tout script hors whitelist/traversal **sans lancer de process**.
2. CORS n'est plus `*` ; configurable par env.
3. Auth : ouverte si `AGISEED_API_TOKEN` absent ; 401 si défini et token manquant/faux ; OK si correct.
4. Timeout opt-in tue un run au-delà du délai quand `AGISEED_SANDBOX_TIMEOUT` est défini.
5. Endpoints GET du dashboard inchangés ; suites de tests vertes ; CI étendue.

## 11. Hors périmètre (YAGNI)

- **Intégration frontend du token** (le dashboard envoie `X-API-Token`) — session frontend.
- **Caps mémoire/CPU** du subprocess — cross-platform difficile (Windows Job Objects), différé.
- **Auth multi-utilisateur / JWT / rôles** — surdimensionné pour un outil local single-user.
- **Rate-limiting** des endpoints — hors périmètre.
- **HTTPS/TLS** — affaire du déploiement (reverse proxy), pas du code applicatif.

## 12. Dépendances

- `backend/app/main.py` (CORS, `include_router`), `routes/{sandbox,flatland,sociologist}.py`,
  `services/sandbox_service.py` (`start`, `get_available_scripts`, `get_status`) — existants.
- FastAPI `Depends`/`Header`/`HTTPException` — déjà utilisés. Aucune dépendance nouvelle.
- `tests/test_backend.py`, `tests/test_sandbox.py` (TestClient, `SandboxService`) — existants.
