---
id: EDR-INFRA-001
type: EDR
title: "Deux défauts d'INSTRUMENTATION affectant toutes les mesures de survie torch : le monde écrit dans l'état récurrent (3/6 génomes, +37 %) et le memory_retriever tournait pendant chaque simulation"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
---

## Question
Deux dettes signalées en marge de l'arc WARM-005→009, jamais mesurées : (A) le monde écrit-il réellement
dans l'état récurrent par aliasing mémoire, et est-ce inerte ? (B) l'instrument de survie respecte-t-il
la règle du dépôt sur la mémoire ambiante ?

## Défaut 1 — l'aliasing des bancs torch n'est PAS inerte
`TorchPopulationModel.forward` renvoie une **VUE** de `self.H` (`backend_torch` ~L144 :
`logits = H_new[:, N-O:N]` puis `.cpu().numpy()` partage le storage sur CPU). Le monde y écrit :
`world_1_stoneage:1289` (`logits[last_action] -= 0.1`, pénalité anti-répétition) et `:966`
(`batch_logits[idx] = consensus_logits`, consensus social). **Ces écritures mutent donc l'état récurrent.**

Mesure — bras INTACT dans les deux cas, seule diffère la prise en compte des écritures du monde dans `H`
(pop nue **aliasée** vs `_DecoupledTorchPop` **découplée**), sur l'étalon `GroundTruthCarryWorld`,
K=3 ères, 6 génomes persistés :

| génome | aliasé (écritures → H) | découplé | |
|---|---|---|---|
| ag00 | `[9.0, 9.0, 9.0]` | `[9.0, 9.0, 9.0]` | idem |
| **ag02** | **`[50.5, 46.0, 55.0]`** | **`[35.0, 36.0, 41.0]`** | **DIFFÉRENT (+37 %)** |
| ag04 | `[22.0, 25.5, 26.5]` | `[22.0, 25.5, 25.0]` | DIFFÉRENT |
| ag05 | `[10.5, 11.0, 11.0]` | `[10.5, 11.0, 11.0]` | idem |
| ag06 | `[50.5, 53.0, 50.5]` | `[50.0, 53.0, 50.5]` | DIFFÉRENT |
| ag09 | `[16.0, 16.0, 18.0]` | `[16.0, 16.0, 18.0]` | idem |

**3/6 génomes diffèrent, jusqu'à +37 %.**

> ⚠️ **Ceci CORRIGE une conclusion antérieure.** La revue de WARM-008 avait conclu « prod ≈ découplé, le
> découplage est inutile » — mais sur **3 génomes d'un seul monde**. Sur l'étalon et 6 génomes, c'est faux.
> Généralisation depuis un échantillon saillant : classe **E9** du registre des erreurs.

**PORTÉE : bancs torch UNIQUEMENT.** `use_torch_inworld = False` par défaut
(`world_1_stoneage:46`) → la **production tourne en `LegacyPopulationModel`**, vérifié sans état aliasé
(aucun attribut d'état exposé, `shares_memory` négatif). Ce n'est donc **pas** une dette de production.

## Défaut 2 — le `memory_retriever` tournait pendant TOUTES les simulations
`_torch_survival_eras` n'arrêtait le retriever qu'**APRÈS** la boucle de simulation, alors que la règle du
dépôt est de l'arrêter **AVANT** (mémoire ambiante KuzuDB → runs non reproductibles ; cf.
`famine_harshness_probe` qui, lui, le fait correctement). Vérifié pendant la sim : `_running = True`,
thread daemon vivant. **Toutes les mesures de survie de l'arc WARM ont tourné dans cet état.**

Corrigé (arrêt + `clear()` avant la boucle). **Reproductibilité vérifiée après correctif** :
`run1 == run2` exactement (`[50.5, 46.0, 55.0]`). Le défaut était donc **réel mais bénin** ici — ce qui ne
pouvait pas se savoir sans le mesurer.

## Contrôle de contamination (et son résultat contre-intuitif)
La première mesure du défaut 1 avait été produite pendant qu'une suite de tests tournait en parallèle —
contention du lock KuzuDB, violation d'une règle documentée. Refaite **sous bail exclusif**
(`tools/jobs/lease.py`), elle est **identique au chiffre près**. La contention était donc inerte *pour
cette mesure* — mais pas en général : la suite de tests concurrente, elle, a bien terminé en timeout.
Passer d'« affirmé » à « établi » a coûté un re-run de 10 min.

## Verdict
**`TORCH_BENCH_ALIASING_IS_REAL__RETRIEVER_RAN_DURING_ALL_SURVIVAL_MEASUREMENTS`** — deux défauts
d'instrumentation, tous deux affectant l'ensemble des mesures de survie torch du dépôt. L'aliasing est
**non inerte** (3/6, +37 %) et non corrigé (décision en attente) ; le retriever est **corrigé**, et son
effet mesuré **nul** sur la reproductibilité.

## Conséquences
* **Pour WARM-005/007/008** : leurs bras `grab_off` corrigés étaient déjà découplés, donc protégés ; mais
  toute comparaison entre un bras découplé et un bras aliasé mélange deux interventions. À vérifier avant
  de réutiliser un chiffre de survie torch de l'arc.
* **DÉCISION en attente (P1.4)** : corriger l'aliasing en production changerait **toutes les baselines
  torch** ; ne pas corriger exige un test qui **épingle** le comportement pour qu'il ne dérive pas
  silencieusement. Hors périmètre d'une session : code partagé, arbre partagé.
* **Correctifs livrés** : `tools/jobs/` (bail sur ressource nommée, run gouverné, doctor — 11/11 tests),
  arrêt du retriever avant boucle, et l'injection `world_cls` qui a rendu ces mesures possibles sur étalon.

## Leçons (registre des erreurs)
* **E10** — *toute règle documentée sans application exécutable finit violée* : la règle KuzuDB existait
  de longue date et a été enfreinte **3×** en une journée (moi 2×, le code d'instrument 1×). D'où
  `tools/jobs/lease.py`, qui rend la contention **impossible** au lieu de déconseillée.
* **E9** — la conclusion « le découplage est inutile » venait de 3 génomes d'un monde ; 6 génomes sur
  étalon la réfutent. Non automatisable → justifie l'obligation de revue.
* **Méthodo** : ces deux défauts n'ont été trouvés qu'en construisant un **étalon à vérité-terrain**.
  Un instrument non calibré ne se contente pas d'échouer, il **produit un résultat**.

Converge [[EDR-WARM-007]], [[EDR-WARM-008]], [[REF-EXPERIMENT-PREFLIGHT]], REF-DEMAND-MARKER.
