# Job manager AGAGI — design, inspiré de Quant-lab `cmex_crypto.batch`

**Date** : 2026-07-21 · **Statut** : proposition, non implémentée
**Source d'inspiration** : `C:\Users\robla\VScode_Project\Quant-lab`, module `src/cmex_crypto/batch/`
(4 modules, ~420 lignes) et sa spec `docs/specs/2026-06-16-job-manager-sota-reference.md` — recherche
à 5 angles, 19 sources, 88 claims dont 25 vérifiés par vote adversarial à 3.

## Ce que Quant-lab a déjà tranché (à ne pas refaire)

Son verdict, vérifié : **construire le gouverneur intégré, réutiliser les primitives.** Aucun outil
étudié ne livre les 7 fonctions en local-first sans démon (`pueue` exige un démon ; `loky`/joblib/Dask/Ray
sont des exécuteurs de *fonctions*, pas des gouverneurs de *sous-processus*). Mais chaque sous-problème
correspond à une primitive permissive à réutiliser : **psutil** (kill d'arbre, garde RAM, identité
PID+`create_time`), **threadpoolctl** (cap BLAS/OMP), **filelock** (bail TTL, ⚠️ jugé immature).
Le travail maison se réduit à **la colle + le registre de bails**.

Découpage retenu là-bas : `lease.py` (bail JSON TTL + heartbeat) · `pool.py` (cap de concurrence,
garde-mémoire, timeout → kill d'arbre) · `doctor.py` (reap des orphelins) · `budget.py` (BLAS mono-thread).

## Ce dont AGAGI a réellement besoin — mesuré, pas supposé

⚠️ Correction d'un diagnostic hâtif du même jour : j'ai d'abord attribué un échec de fork à des
**processus orphelins**. Mesure : **zéro orphelin, 18 Go libres sur 64**. La panne était une défaillance
de fork Cygwin/MSYS, transitoire. **Le reaping d'orphelins n'est donc PAS le besoin dominant d'AGAGI** —
contrairement à Quant-lab, dont le `doctor.py` répond à un incident réel de famine mémoire (2026-06-11).

Les besoins **effectivement mesurés** aujourd'hui, par ordre de gravité :

| # | Besoin | Preuve mesurée |
|---|---|---|
| **B1** | **Sérialisation sur ressource nommée exclusive** (KuzuDB) | Deux sims concurrentes → lock disputé → **mesure contaminée** (« 3/6 génomes diffèrent » produit sous contention, à refaire) + suite de tests en timeout. Violé **2×** dans la journée. |
| **B2** | **Timeout par job → kill de l'ARBRE** | Mémoire projet documente le danger orphelin ; **aucune implémentation** n'existe (`grep psutil` sur `tools/` + `src/` = 0 résultat). E10. |
| **B3** | **Visibilité** : quels jobs tournent, depuis quand | Aucune. Les runs longs sont suivis à la main. |
| **B4** | Garde RAM à l'admission | Non déclenché aujourd'hui (18 Go libres), mais les runs longs grossissent. Prudentiel. |
| **B5** | Cap BLAS/OMP | Non mesuré. numpy+torch → sur-souscription plausible sous jobs concurrents. À mesurer avant d'implémenter. |

## L'écart de conception avec Quant-lab — et c'est le cœur

Quant-lab gouverne par **cap de concurrence** : un nombre (`min(cpu-2, requested)`). AGAGI a une
contrainte de nature différente : **KuzuDB est une ressource EXCLUSIVE nommée**. Deux sims de monde ne
peuvent pas coexister, quel que soit le nombre de cœurs ; mais une sim et un run de tests purs le peuvent.

Un cap global à 1 serait donc à la fois **trop strict** (il sérialiserait des jobs indépendants) et
**mal ciblé** (il ne dit pas *pourquoi*). La primitive juste est le **bail sur ressource nommée** :

```python
with job(name="warm009-ablation", resources=["kuzu"], timeout_s=3600) as j:
    ...                      # un autre job demandant "kuzu" attend ou échoue bruyamment
```

C'est l'adaptation réelle, pas une copie : `lease.py` de Quant-lab devient un registre
**{ressource → bail}** plutôt qu'un simple compteur de slots.

## Plan minimal proposé (par valeur décroissante)

1. **`tools/jobs/lease.py`** — bail JSON `runs/leases/<resource>.json` : `pid`, `create_time`
   (anti-réutilisation de PID), `ttl`, `heartbeat`, `owner`. Reprendre l'API injectable de Quant-lab
   (`now`, `leases_dir`) qui la rend testable sans horloge murale. **Remplace `tools/sim_session.py`**,
   dont le verrou fichier actuel n'a ni TTL, ni heartbeat, ni récupération après crash.
2. **`tools/jobs/run.py`** — lancement de sous-processus avec `timeout_s` → `_kill_tree` (psutil,
   `children(recursive=True)` → terminate → wait → kill). Couvre B2.
3. **`tools/jobs/doctor.py`** — `--report` par défaut, `--kill` explicite. **Jamais** le processus courant
   ni ses ancêtres. Couvre B3, et B1 en résiduel (bail périmé après crash).
4. *(différé)* garde RAM (B4) et cap BLAS (B5) — **à mesurer avant d'implémenter**, conformément au
   protocole : ne pas construire contre un besoin supposé (le reaping d'orphelins vient d'illustrer le coût
   de cette erreur).

## Garde-fous propres à ce chantier

- **Un job manager est un INSTRUMENT** au sens de `REF-EXPERIMENT-PREFLIGHT` : il doit être **calibré**
  (le cliquet le détectera comme non calibré) et entrer au registre des erreurs s'il en produit une.
- Tuer des processus est **destructif et peu réversible** : dry-run par défaut, kill sur flag explicite,
  jamais d'auto-kill silencieux. Les bails d'autres sessions ne sont jamais réapés (arbre partagé).
- **Ne PAS reprendre `filelock`** : jugé immature par la revue Quant-lab (Fév–Juin 2026). Le bail JSON
  maison, testable et injectable, suffit.

## Décision demandée

Ce chantier ne figure pas au backlog actuel. S'il est retenu, il s'insère en **P1** (il rend E10
exécutable pour de bon et supprime la cause mesurée de la contamination B1), avant P2 calibration.
Coût estimé : **~4 h** pour les points 1-3, tests compris.

Cf. [`../roadmap/PRIORITES_ET_DETTES.md`](../roadmap/PRIORITES_ET_DETTES.md) ·
[`../REF/REGISTRE_ERREURS.md`](../REF/REGISTRE_ERREURS.md) (E10) · `tools/sim_session.py` (à remplacer)
