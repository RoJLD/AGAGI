# Roadmap Backend — AGIseed (axe ⚙️ Infrastructure)

> **Domaine** : serveur FastAPI (`backend/app/`), persistance KuzuDB, observabilité/provenance,
> A/B multi-run, sécurité/sandbox, CI. Au service de la méthode expérimentale (Commandement 15).
> **Périmètre** : `backend/`, `tools/` d'infra, `.github/workflows/`. La science → `SCIENCE.md` /
> `NAS.md` ; le frontend → `FRONTEND.md`. **Someday** → `../BACKLOG.md` (§Backend).
>
> Extrait de l'ancien `roadmap.md` (split du 2026-06-24) pour séparer infra et science.

---

## Roadmap backend C1-C4 — ✅ COMPLÈTE

> Les 4 chantiers backend sont livrés. Conservés ici comme trace + caveats à garder en tête.

### C1 — Observabilité & Provenance ✅
**Ledger de provenance** (`/api/provenance` : seed + commit + config_hash + git_dirty ↔ KPIs ; nœud
`Run` KuzuDB, `ERA_RESULT`→`Run`), **santé KuzuDB** (`/api/health/kuzu` : reachable/writable/schema/
counts → tue les *données fantômes*), **drain KuzuDB instrumenté** (`/api/observability/logger` :
queue/latence/events/erreurs). Le **verdict S2** apparaît au dashboard *via le ledger*.
*(spec/plan : `../superpowers/{specs,plans}/2026-06-15-C1-Observability-Provenance*`)*
**Reste** : checkpoint reproductible binaire (HoF + RNG + WM).

### C2 — A/B live multi-run ✅
N runs flatland concurrents (cap `MAX_RUNS=4`) comparant 2 lignées côte à côte : **`FlatlandServer`
paramétré** (overrides whitelistés + `label`), **`FlatlandManager`** (dict de runs, cycle de vie,
`default` legacy préservé), router REST `/api/flatland/runs` (POST/GET/DELETE → 429/400/404) et
WebSocket `/ws/flatland/{run_id}` (legacy `/ws/flatland` intact).
> ⚠️ **Caveat** : le moteur consomme `np.random` **global** → deux runs concurrents = flux entrelacés,
> **non appariés et non reproductibles**. L'A/B live est **observationnel** ; la mesure rigoureuse
> (appariement seedé) reste l'affaire du harness offline (D1/S2).
*(spec/plan : `../superpowers/{specs,plans}/2026-06-15-C2-Flatland-Multirun*`)*

### C3 — Brancher stubs + dette/CI ✅
**Honnêteté** : `strategy.py` ne renvoie plus le mock `StoneAge (Mock)` ; flag `source` ∈
{`live`,`empty`,`error`}. **Bug dormant corrigé** : nœud `Article` à double schéma (`timestamp` vs
`date`) → `/sociologist/articles` renvoyait `[]` ; **unifié sur `date`**. **Couverture** :
`test_sandbox`/`test_strategy`/`test_sociologist`. **CI** : la pipeline exécute enfin C1/C2/C3.
*(spec/plan : `../superpowers/{specs,plans}/2026-06-16-C3-Stubs-Dette-CI*`)*

### C4 — Sécurité & sandbox ✅
Ferme le trou **RCE** de `/api/sandbox/start` : **whitelist de scripts + confinement `PROJECT_ROOT`**
(`_is_allowed_script` tue le path-traversal) ; **CORS restreint** (`AGISEED_CORS_ORIGINS`, plus de
wildcard) ; **auth opt-in par token** (`require_token`, `AGISEED_API_TOKEN`) sur les endpoints
mutateurs ; **timeout subprocess opt-in** (`AGISEED_SANDBOX_TIMEOUT`). **Couverture** : `test_security`
+ `test_sandbox`. *(spec/plan : `../superpowers/{specs,plans}/2026-06-22-C4-Securite-Sandbox*`)*
> ⚠️ **Reste (durcissement profond, AVANT RSI en prod)** : conteneur isolé + limites mémoire/réseau.
> La whitelist ferme le RCE *applicatif*, **pas** l'isolation OS — pré-requis pour armer la RSI
> (`src/metaprog/`, cf. `NAS.md` §X1).

---

## Reste backend (priorisé)
1. **Checkpoint reproductible binaire** (HoF + RNG + World Model) — repro end-to-end, pas que le RNG.
2. **Durcir l'isolation OS de la sandbox** (conteneur / cgroups / pas de réseau) — **gate de la RSI**.
3. **Drain KuzuDB** : dégradation gracieuse si DB absente, alerte si queue > 1000 / timeout > 5 s.
4. **Versioning des résultats** : relier chaque KPI à (commit, config_hash, gènes) de façon requêtable.

## Garde-fous backend (méthodo)
- **Budget compute** *(angle-mort CRITIQUE)* : la rigueur multi-seed × K-éval × R-runs explose sur
  mono-machine. Profiling / parallélisme / early-stopping **avant** les benchmarks science (S2/S4).
- **Sécurité** : RCE applicatif fermé (C4). Reste l'isolation OS avant d'armer la RSI en prod.
