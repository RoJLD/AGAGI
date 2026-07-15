# S2 — bras d'ablation-perception WITHIN-SUBJECT : rendre « le monde EXIGE l'intelligence » CAUSAL

## Contexte

Le fil S2 a établi **EXIGE** de façon robuste : le champion HoF bat tous les baselines en SURVIE (3.4–4.7×,
p=0.0025, Cliff δ 0.92–0.97, 4–5 mondes ; EDR 124). Le faux-VOID du gate `life_score` est corrigé end-to-end
(`verdict_from_survival_cmps`, #132). **Mais ce verdict est BETWEEN-subject** (champion vs baselines) — et **S2-001**
(`tools/world_demand_marker_probe.py`) a montré, sur mondes à vérité-terrain, que ce marqueur **faux-positive** :
un survivant compétent peut exister dans un monde qui n'exige PAS la capacité, et gagner par un autre facteur
(corps/génome) plutôt que par la perception. Le témoin CAUSAL sûr = **ablation WITHIN-subject** : décorréler la
perception du MÊME champion et mesurer la chute de survie. C'est la reco in-world consignée (S2-001,
[[within-subject-demand-marker]]) : « brancher un bras d'ablation-perception à `s2_demand` — bon marché, zéro
ré-évolution ».

## Objectif

Câbler un bras d'**ablation-perception within-subject** dans `s2_demand` : une condition `champion_obs_ablated`
(même génome champion, même moteur, mais **obs décorrélée de l'état réel**) + un **verdict CAUSAL** apparié. Si
ablater la perception effondre la survie du champion → **EXIGE devient CAUSAL** (la perception est causalement
porteuse), fermant le caveat « survivant ≠ marqueur » in-world. Additif, zéro ré-évolution, une passe d'éval.

## Architecture (additive — ne touche PAS `mamba_agent.py`/`backend_torch.py`/`world_1_stoneage.py`)

### 1. `src/agents/ablation_models.py` (CREATE) — `ObsAblatedMambaBatchModel`
Wrapper drop-in de `MambaBatchModel` (même interface `forward(batch_obs, env_surprise_batch=None) -> (logits,
compute_spent)`, injecté via `env.batch_model_cls`). Il **enveloppe un vrai `MambaBatchModel`** (le moteur champion,
poids/génome réels) et, à chaque tick, **permute les lignes de `batch_obs`** (agent i reçoit l'obs RÉELLE d'un autre
agent) AVANT de déléguer au forward interne :

```python
class ObsAblatedMambaBatchModel:
    """Ablation-perception within-subject : même champion (MambaBatchModel réel), mais obs décorrélée de
    l'état propre par row-shuffle par tick. Décorrèle perception↔réalité en préservant EXACTEMENT la
    distribution marginale de l'obs. Le shuffle vient du flux np.random SEEDÉ global (comme les baselines,
    world_1:seam) → appariement/déterminisme préservés, JAMAIS un RNG privé."""
    def __init__(self, agents, world_model=None):
        self._inner = MambaBatchModel(agents, world_model=world_model)
        self.agents = agents
    def forward(self, batch_obs, env_surprise_batch=None):
        B = batch_obs.shape[0]
        if B == 0:
            return self._inner.forward(batch_obs, env_surprise_batch)
        perm = np.random.permutation(B)                 # décorrèle obs↔agent (flux seedé global)
        return self._inner.forward(batch_obs[perm], env_surprise_batch)
    def compute_policy_gradient(self, *a, **k):
        return self._inner.compute_policy_gradient(*a, **k)   # champion figé -> no-op délégué
```
Note : le wrapper NE zéro-fixe PAS `surprise` (contrairement aux baselines) — on garde tout le pipeline perceptif
RÉEL du champion (surprise/curiosité/World-Model), simplement nourri d'une obs décorrélée. C'est l'ablation propre :
seule la perception change, tout le reste est le champion authentique.

### 2. `champion_obs_ablated` — nouvelle condition dans `tools/s2_demand.py`
```python
CONDITIONS = { ...,
    "champion_obs_ablated": {"batch_model_cls": ObsAblatedMambaBatchModel, "fresh_genome": False},
}
```
Génome champion (`fresh_genome=False`) + moteur à obs ablée. `run_condition` la déroule à l'identique des autres
(mêmes ères seedées, cohorte fixe, RAG-off), rendant la survie individuelle appariable par ère.

### 3. Verdict within-subject — `verdict_within_subject` (CREATE dans `src/seed_ai/s2_stats.py`)
Réutilise `_compare(a, b, "survival")` (Cliff δ + bootstrap ratio + p apparié) déjà éprouvé par `s2_verdict` :
```python
def verdict_within_subject(champion, champion_ablated, random_action,
                           alpha=ALPHA, cliff_thresh=CLIFF_THRESH, equiv_margin=EQUIV_MARGIN):
    causal   = _compare(champion, champion_ablated, "survival")     # champion >> ablaté ?
    residual = _compare(champion_ablated, random_action, "survival")# ablaté ≈ random ?
    is_causal = (causal["p"] < alpha) and (causal["cliff"] >= cliff_thresh)
    edge_fully_perceptual = abs(residual["cliff"]) < equiv_margin   # ablaté indiscernable du random
    if not is_causal:
        verdict = "NON-CAUSAL"          # ablater la perception NE nuit PAS -> l'edge n'était pas perceptif (surprenant)
    elif edge_fully_perceptual:
        verdict = "CAUSAL-FULL"         # la perception explique TOUT l'avantage (ablaté = random)
    else:
        verdict = "CAUSAL-PARTIEL"      # la perception explique une PART (ablaté > random résiduel)
    return {"verdict": verdict, "causal_cmp": causal, "residual_cmp": residual,
            "is_causal": is_causal, "edge_fully_perceptual": edge_fully_perceptual}
```
Seuils GELÉS = les mêmes que le S2 canonique (`ALPHA`, `CLIFF_THRESH`, `EQUIV_MARGIN` de `s2_stats`). On ne
préjuge PAS : `NON-CAUSAL` est un résultat possible et significatif (il dirait que l'edge du champion n'est pas
perceptif — à investiguer).

### 4. Intégration `run_s2`
Ajouter, à côté du verdict between-subject existant (inchangé), un bloc `within` par monde :
`report["worlds"][w]["within"] = verdict_within_subject(conds["champion"], conds["champion_obs_ablated"],
conds["random_action"])`. `_print_table` affiche la ligne within (verdict CAUSAL + Cliff causal + Cliff résiduel).

## Flux de données
Champion HoF → `run_condition` sous 3 conditions pertinentes (`champion`, `champion_obs_ablated`, `random_action`)
→ survie individuelle par ère → `verdict_within_subject` → verdict CAUSAL. Le between-subject (5 conditions) reste
calculé et rapporté tel quel ; le within est un AJOUT.

## Portée & régime (gelés)
- **Monde** : **stoneage** (Biosphere3D — le monde diagnostic de référence), extensible aux autres mondes ensuite.
- **K = 12** (plancher pré-enregistré `K_FLOOR`), **max_ticks = 200** (aligné sur le run S2 vérifié end-to-end
  2026-07-10, stoneage K=6 max_ticks=200), **num_agents = 20**. Extensible aux autres mondes/K ensuite.
- **RAG-off** (`_disable_kuzu` / `with_db=False`) : conservateur ET l'ablation porte sur la PERCEPTION, pas la RAG.
- **Déterminisme** : `Harness` seedé ; le row-shuffle tire du flux global seedé → appariement préservé, 2 runs même
  seed reproductibles.

## Gestion d'erreurs / garde-fous
- **HoF requis** : `load_champion_genome` lève si vide (pas de champion → pas de run). Vérifier `hall_of_fame.pkl`
  présent dans le worktree AVANT le run (via `HOF_PATH`).
- **Garde-fou de sens** : si `champion_obs_ablated` survit AUSSI BIEN que `champion` (NON-CAUSAL), NE PAS le lire
  comme un bug — c'est un verdict falsifiable (l'edge ne serait pas perceptif). Le corroborant `residual` (ablaté vs
  random) désambiguïse.
- **Multiprocess/KuzuDB** : réutiliser la discipline `s2_demand` existante (cohorte fixe, `memory_retriever.stop()`,
  RAG-off) ; aucun ProcessPool ajouté.

## Tests (`tests/` du worktree)
- **`ObsAblatedMambaBatchModel`** : (a) délègue au forward interne (mêmes shapes de sortie que `MambaBatchModel`
  sur un mini-batch) ; (b) le shuffle DÉCORRÈLE — sur un batch d'obs distinctes, l'obs vue par l'agent i ≠ son
  obs propre (au moins pour un B où la permutation n'est pas identité) ; (c) B=0 ne casse pas ; (d) déterminisme :
  2 forwards au même état RNG global → mêmes logits.
- **`verdict_within_subject`** : sur survies synthétiques — (a) champion≫ablaté & ablaté≈random → `CAUSAL-FULL` ;
  (b) champion≫ablaté & ablaté>random → `CAUSAL-PARTIEL` ; (c) champion≈ablaté → `NON-CAUSAL`. Verdict ∈ ensemble gelé.
- **Contrat** : `champion_obs_ablated` présent dans `CONDITIONS` ; `run_s2` rend un bloc `within` par monde.

## Résultat attendu (pré-enregistré, non préjugé)
- **CAUSAL-FULL / CAUSAL-PARTIEL** attendu (S2-001 corrobore : ablation-perception effondre la survie) → **EXIGE
  devient CAUSAL in-world**, ferme le caveat « survivant ≠ marqueur », consolide EDR 124.
- **NON-CAUSAL** = finding fort et inattendu (l'avantage survie du champion ne viendrait pas de la perception mais
  d'un autre facteur — corps/génome/politique fixe) → à investiguer AVANT toute conclusion.

## Risques
- Lignée : le S2 canonique vit sur origin/main (ce worktree) ; d1 a un `s2_demand` périmé — ne PAS y toucher.
- Compute biosphère (stoneage K=12) : ~dizaines de min, run en arrière-plan.
- Champion HoF disponible dans le worktree : à vérifier au plan.
