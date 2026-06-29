# Design — G0 : le monde EXIGE-t-il l'intelligence ? (benchmark champion vs aléatoire)

> **Date** : 2026-06-29 · **Statut** : design validé (brainstorming), avant plan d'implémentation.
> **Porte** : G0 du [`FIL_DIRECTEUR_AGI`](../../roadmap/FIL_DIRECTEUR_AGI.md) (record `SDR-G0`).
> **Dépend de** : rien (porte de validité, fondation). **Débloque** : G1 (transfert north-star) —
> sans G0, `transfer_ratio` mesure du bruit.

---

## 1. Question falsifiable

**Un champion évolué survit-il significativement mieux qu'un agent à politique aléatoire, dans chaque
monde aval ?** Si le ratio ≈ 1 → le monde est *factice* (n'exige aucune politique) → toute mesure de
« compétence » ou de « transfert » y est du bruit. C'est `SDR-G0`.

> Renforcé par **EDR 110** (capacité réseau réfutée comme levier du mur Lewis ; convergence
> surdéterminée vers le répertoire-monde) : avant de mesurer le transfert (G1), il faut prouver que les
> mondes cibles *discriminent* réellement la politique.

## 2. Décisions de cadrage (brainstorming)

| Décision | Choix | Raison |
|---|---|---|
| **Dummy** | **Politique aléatoire** (actions uniformes/tick) | garde l'incarnation, retire la politique → contraste propre « le monde récompense-t-il une bonne politique » |
| **Mondes** | **stoneage + Lewis** | prod (sweet-spot survie) + régime DUR (config létale) ; harnais générique sur `world_type` |
| **Compute** | **séquentiel d'abord (YAGNI)** | réutilise `robust_evaluate`/`seed_at` ; optimiser seulement si intenable |
| **Champion** | **évolué inline, seedé** | auto-contenu, reproductible, SANS dépendance à l'état KuzuDB |
| **Régime létal** | **verdict INCONCLUSIF** | si champion ET aléatoire au plancher → ne pas trancher FACTICE à tort |

## 3. Composants

### 3.1 `RandomPolicyAgent` (dans `src/agents/random_policy_agent.py`)
Sous-classe de `MambaAgent` qui **override le seul calcul de politique** (`forward`) pour renvoyer des
actions **uniformes aléatoires de forme identique** à la sortie de `MambaAgent.forward`. Tout le reste
(observation, énergie, métabolisme, corps, `from_genome`) est hérité → le dummy ne diffère du champion
*que* par la politique. L'implémenteur lira `src/agents/mamba_agent.py` (`forward` ligne 438, contrat
batch `(batch_obs, env_surprise_batch) -> tuple`) pour matcher exactement la forme de sortie.

> Garde-fou de conception : le random doit consommer le RNG seedé (reproductible) ET varier entre ticks.

### 3.2 `tools/world_demand_benchmark.py`
Orchestre G0 :
1. **Évolue un champion** en stoneage pour `T_eras` ères seedées (réutilise le chemin d'évolution prod —
   `build_population`/sélection — comme `tools/evolve_ceiling_probe.py`), sélectionne le meilleur par
   `robust_evaluate`, le **gèle** (génome).
2. Pour chaque `world_type` ∈ {stoneage, Lewis} × chaque seed ∈ R :
   - éval **champion** (K clones, `robust_evaluate`-like) → `survival_competence` (médiane âges).
   - éval **aléatoire** (K clones, `RandomPolicyAgent` depuis le MÊME génome gelé — corps identique,
     politique aléatoire) → `survival_competence`.
   - appariement strict : mêmes seeds, mêmes mondes pour les deux bras (`seed_at(base, i)`).
3. Agrège, calcule le verdict (section 5), écrit `results/world_demand_benchmark.json`, imprime.

> Lewis = config létale réutilisée de `tools/lewis_survival_sweep.py` (`_setup_critical` via
> `tools/lewis_critical.py`). Le champion est évolué en stoneage (sweet spot) PUIS testé en Lewis (pas
> ré-évolué) — cohérent avec EDR 090 (transfert de survie stoneage→Lewis).

## 4. Flux de données

```
seed_at(base,0) -> évolue champion (stoneage, T_eras) -> genome_champion (gelé)
pour world in {stoneage, lewis}:
  pour i in range(R):
    seed_at(base, i)
    c_i = survival_competence( eval(genome_champion,   policy=appris,   world, K) )
    r_i = survival_competence( eval(genome_champion,   policy=aléatoire, world, K) )
  -> agrège {c_i}, {r_i} -> ratio + sign test -> verdict(world)
-> JSON + print
```

## 5. KPI & verdict (par monde)

- **KPI** : `survival_competence` (médiane des âges normalisée, `src/curriculum/competence.py`).
- **`demand_ratio`** = médiane({c_i}) / médiane({r_i}) (garde anti division-par-zéro).
- **Test de signe binomial appairé** : nombre de seeds où `c_i > r_i` sur R → `sign_p`.
- **Verdict** (évalué dans CET ordre — INCONCLUSIF prime sur EXIGE) :
  1. **INCONCLUSIF** : médiane({c_i}) **ET** médiane({r_i}) sous `FLOOR_AGE` (régime létal — personne ne
     survit) → le monde ne discrimine pas faute de survie, à re-régler (PAS factice). Vérifié EN PREMIER :
     au plancher, un `demand_ratio` élevé n'est que du bruit et ne doit pas déclencher EXIGE.
  2. **EXIGE** : `demand_ratio ≥ DEMAND_THRESHOLD` **ET** `sign_p < ALPHA` (hors plancher).
  3. **FACTICE** : sinon (ratio ≈ 1 ou non significatif, hors plancher).
- Constantes loggées : `DEMAND_THRESHOLD` (défaut 1.5), `ALPHA` (0.05), `FLOOR_AGE` (à caler sur
  `AGE_REF`), `R` (défaut 8), `K` (défaut 3), `T_eras`. R/seuils = variables d'expérience (Commandement 15).

## 6. Garde-fous anti-théâtre

1. **Sanity du dummy** : avant tout verdict, vérifier que l'aléatoire est *réellement* dégradé —
   logger `entropy` d'action ou simplement exiger `médiane({r_i}) < médiane({c_i})` au global ; si le
   random survit AUSSI bien que le champion partout, c'est un signal d'alarme (champion non compétent
   ou monde factice), surfacé, pas masqué.
2. **Appariement strict** : mêmes `(seed, world, K)` pour les deux bras (sinon confond bruit de monde).
3. **Plancher létal** → INCONCLUSIF (section 5), jamais FACTICE par défaut.
4. **Reproductibilité** : `seed_at` aux frontières ; `memory_retriever.stop()` avant la boucle sim
   (mémoire [[biosphere-ambient-memory-nonrepro]]) ; run rejouable via le seed boot.

## 7. Tests (TDD)

- `RandomPolicyAgent.forward` : sortie de forme identique à `MambaAgent.forward` ; varie entre deux
  ticks ; déterministe sous seed fixe (même seed → même séquence).
- `demand_verdict(champion_scores, random_scores, **seuils)` (fonction pure extraite) :
  - EXIGE quand champion ≫ random (ratio > seuil, sign_p < alpha).
  - FACTICE quand champion ≈ random (ratio ~1).
  - INCONCLUSIF quand les deux séries sont sous `FLOOR_AGE`.
  - appariement : longueurs égales requises (sinon erreur).
- Smoke : un run minuscule (T_eras=1, R=2, K=1, max_ticks réduit) produit un JSON avec un verdict par
  monde, sans crash, reproductible (deux runs même seed → mêmes scores).

## 8. Périmètre & non-buts

- **Dans le périmètre** : `RandomPolicyAgent`, `tools/world_demand_benchmark.py` (évolution champion +
  éval appariée + verdict pur + JSON), tests, **run réel** powered → **EDR** (verdict EXIGE/FACTICE/
  INCONCLUSIF par monde) consigné dans `docs/EDR/` avec frontmatter `tests: [SDR-G0]` (alimente le
  graphe de [[fil-directeur-agi-gates]]).
- **Hors périmètre (backlog/différé)** : parallélisme multiprocess (YAGNI, seulement si intenable —
  pièges [[multiprocess-experiment-hazards]]) ; early-stopping ; mondes agricultural/industrial/soup ;
  opt-in `main_biosphere`.

## 9. Risques

| Risque | Mitigation |
|---|---|
| Lewis au plancher pour les DEUX bras (EDR 110) | verdict INCONCLUSIF (pas FACTICE) ; re-régler la létalité |
| Contrat `forward` mal matché (forme actions) | test de forme `RandomPolicyAgent` vs `MambaAgent` ; implémenteur lit `mamba_agent.py` |
| Compute trop lourd en séquentiel | échelle modérée chronométrée ; optimisation différée (YAGNI) |
| Champion inline pas assez compétent | sélection par `robust_evaluate` (dé-bruitée) ; sanity-check du contraste avant verdict |
| Non-repro (KuzuDB ambiant) | `memory_retriever.stop()` avant sim ; `seed_at` aux frontières |

## 10. Critères de succès du chantier

1. `RandomPolicyAgent` + `world_demand_benchmark.py` livrés, tests verts.
2. Run réel powered : un verdict par monde (stoneage, Lewis) avec ratio + sign_p, JSON écrit.
3. EDR consigné (frontmatter `tests: [SDR-G0]`) → `tools/consolidate_records.py` peuple `tested_by[G0]`.
4. Si stoneage = EXIGE → la validité du substrat de prod est établie ; G1 peut démarrer dessus.
