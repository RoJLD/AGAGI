# Spec — Coût métabolique d'activation (NAS Axe D-1)

> **Statut** : design validé (2026-06-24), prêt pour plan d'implémentation.
> **Roadmap** : [`docs/roadmap/NAS.md`](../../roadmap/NAS.md) §2 Axe D — D1.
> ⚠️ **Collision de nom** : le « D1 » backend = RNG/Harness (`2026-06-13-D1-RNG-Harness`). Ici, « D1 »
> = l'item *Axe D / D1* de la roadmap NAS (coût métabolique). On utilise `metabolic_cost_*` dans le code
> pour lever l'ambiguïté.

## 1. Intention

Rendre le **calcul métabolique** : chaque nœud actif d'un connectome coûte de l'énergie par tick.
La sélection naturelle de la biosphère favorise alors les connectomes **parcimonieux/efficients** —
*l'efficacité trouvée, pas donnée* (thèse fondatrice).

**Isomorphisme** : la contrainte énergétique stricte de l'insecte (fiche bio-inspiration §3 :
fitness = précision / nb d'activations) ≡ l'économie métabolique de la biosphère, où les organismes
**meurent de famine** (mémoire *mur Lewis* : famine en ~5 ticks par coût d'action). D1 transforme cette
fitness en pression de sélection émergente, et fournit un levier direct sur le mur Lewis.

## 2. Décision de design (validée)

- **Métrique de coût** = **comptage de nœuds actifs** : `active_count = |{ i : |H_i| > eps }|`.
  Choisie pour coller au *sparse coding* biologique (1-2 % actifs, corps pédonculés) et pour récompenser
  directement un futur KWTA (Axe D-2, synergie). *(Alternative magnitude `Σ|H|` écartée.)*
- **Seuil** `eps` configurable (`metabolic_active_eps`, défaut **0.1** ; `H` post-`tanh` ∈ [-1,1]).
- **Gating** par coefficient `metabolic_cost_coef` (défaut **0.0** ⇒ non-régression bit-exacte).
  Opt-in ; **seule variable** d'expérience (Commandement 15).

## 3. Architecture — data flow

Chemin de production = `MambaBatchModel.forward` (calcule `H (B, max_N)` par tick) → écriture sur agents
→ `world_1_stoneage._resolve_biology` (applique le drain). Deux touches :

1. **`src/agents/mamba_agent.py` — `MambaBatchModel.forward`** : après la dernière itération TTC
   (H final), calculer par agent `active_count_i = int(np.sum(np.abs(H[i]) > eps))` (le padding à 0
   ne dépasse jamais `eps`, donc compter la ligne entière est correct). Écrire dans la boucle de
   write-back (~`:640`) : `a.last_activation_cost = active_count_i`. Initialiser `last_activation_cost=0`
   dans `MambaAgent.__init__` (robustesse si forward jamais appelé).

2. **`src/worlds/world_1_stoneage.py` — `_resolve_biology` (`:617`)** : ajouter, après le drain de base,
   ```
   coef = getattr(self.config, "metabolic_cost_coef", 0.0)
   if coef > 0.0:
       drain += coef * getattr(agent["model"], "last_activation_cost", 0)
   ```
   placé **avant** les modulateurs nuit/feu (`:621-629`) — **décision** : le coût métabolique EST
   modulé par la thermodynamique (cohérent : penser coûte plus cher la nuit, moins près du feu).

## 4. Config

`src/environments/config.py` (près de `base_metabolism`, `:70`) :
- `metabolic_cost_coef: float = 0.0` — coût énergétique par nœud actif/tick. Sweep typique 0 → 0.01
  (N≈172 ⇒ drain additionnel max ≈ 0.17 vs base ≈ 1.0).
- `metabolic_active_eps: float = 0.1` — seuil d'activité d'un nœud.

## 5. Non-régression & 1-variable

- `metabolic_cost_coef = 0.0` ⇒ aucun terme ajouté ⇒ drain **bit-identique** au baseline. Garanti par
  le `if coef > 0.0`.
- La mesure d'`active_count` dans le forward est **inconditionnelle** (toujours calculée, peu coûteuse,
  utile au KPI) mais **sans effet** tant que coef=0 → pas un changement de comportement de sélection.

## 6. Protocole de mesure (X2)

Harness apparié multi-seed (`Harness`/`seed_boundary`, infra RNG existante). Comparer `coef=0` (baseline)
vs `coef>0` (balayage), **appariés par seed**. KPIs :
- **(a) Compétence** (life_score robuste) — vérifier non-collapse.
- **(b) Ratio d'efficacité = compétence / nb_moyen_de_nœuds_actifs** — la métrique de la fiche §3.
- **(c) Sparsité moyenne** = `active_count` moyen / N — descend-elle sous pression ?
- **Verdict** (transfer-ratio / signe binomial) : le coût métabolique **augmente-t-il (b)** sans
  effondrer (a) ? Balayage du coef depuis ~0.

## 7. Risques & mitigations

| Risque | Mitigation |
|---|---|
| Coef trop haut → famine de masse (collapse population) | Balayage depuis ~0 ; garde-fou Lewis ; surveiller (a) |
| Coût pénalise les « penseurs » MCTS (plus de ticks actifs) | Attendu et désirable (penser doit coûter) ; documenter l'interaction avec `mcts_drain` |
| `active_count` mesuré dans l'espace paddé fausse le compte | Padding = 0 < eps ⇒ non compté ; test dédié |
| Collision conceptuelle avec `phenotype_energy_drain` (statique) | D1 est **dynamique** (par tick) ; additif, orthogonal |

## 8. Tests (TDD)

1. `coef=0` ⇒ `drain` bit-identique au baseline (snapshot sur agent fixe).
2. `coef>0` ⇒ `drain` croît linéairement avec `last_activation_cost`.
3. `active_count` : un `H` avec k valeurs > eps et padding nul ⇒ compte = k.
4. À `coef` fixe, un connectome plus sparse (moins de nœuds actifs) subit un drain moindre ⇒ survie ≥.
5. Repro seedée : deux runs même seed ⇒ `active_count` et `drain` identiques.

## 9. Hors-périmètre (fast-follow)

- **D2 — KWTA / sparse coding** (forcer top-k% actifs) : synergie directe, spec séparé.
- **D3 — nœuds typés** : enrichissement de l'espace de recherche, spec séparé.
- Application à d'autres mondes que `world_1_stoneage` (Lewis/Soup) : après validation stoneage.
