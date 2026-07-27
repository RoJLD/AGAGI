# Design — WARM-003 : DAgger on-policy contre le plafond de transfert (acc_on-policy 0.734)

Date : 2026-07-18
Statut : design approuvé (cible récurrente masquée + compute modéré)
Record visé : EDR-WARM-003, `gate: G0`, `adopts: [REF-DEMAND-MARKER]`

## Contexte et question

WARM-001 a MESURÉ le mur : le substrat imite l'oracle jusqu'à `acc_enseignant=1.000`, le marqueur bascule
PERCEPTION_DEMANDED, MAIS la survie plafonne ~15 (oracle 200) car `acc_ON-POLICY` (le génome pilotant SES
propres états) plafonne à **0.734** et ne monte pas avec plus d'epochs sur la trajectoire-enseignant. Cause :
dérive de l'état récurrent H + sur-apprentissage de la trajectoire UNIQUE de l'oracle. Le levier canonique
pour ce mode d'échec = **DAgger** : entraîner sur les états que le LEARNER visite lui-même (réétiquetés par
l'oracle), pour que la distribution d'entraînement ↦ la distribution de test.

**Question décisive** : en itérant DAgger, `acc_on-policy` casse-t-il le 0.734 et la survie décolle-t-elle
vers l'oracle ?
- OUI (acc_on-policy ↑, survie ↑) → le verrou EST le transfert de distribution (fixable avec des données
  on-policy) = résultat POSITIF, on installe enfin un survivant.
- NON (acc_on-policy plafonne malgré l'entraînement on-policy) → verrou plus profond : le substrat récurrent
  ne SOUTIENT pas la carte réactive sur 200 ticks auto-pilotés (capacité de rétention, pas de transfert).

## Critère de succès (inchangé + lecture mécaniste)

PASS = marqueur `PERCEPTION_DEMANDED` (within-subject, K≥12) **ET** survie intacte ≥ 0.5·oracle (=100).
Lecture mécaniste par round : la courbe `acc_on-policy` (via `_inworld_accuracy`) + la survie médiane. Le
garde-fou petit-n tient (K≥12 pour le verdict final).

## Régime monde

Identique S2-009 / WARM (cognitive_demand, metab=0.75, cog=12, forage_payoff=0, benchmark_mode,
night_enabled=False, current_era=10_000). Plancher ≈ 7, oracle ≈ 200, acc_on-policy WARM-001 ≈ 0.73.

## Architecture (extension de `tools/warmstart_evolution_inworld.py`)

Réutilise TOUT l'existant (make_cog_world, verdict_demand_marker, _inworld_accuracy, _imitation_accuracy,
_collect_oracle_trajectory, imitate_episode_bptt). NE modifie PAS les outils partagés.

### Composant 1 — `imitate_episode_bptt(..., mask_seq=None)` (extension additive de backend_torch)

Ajoute un paramètre optionnel `mask_seq` (liste de (B,) ∈ {0,1} par pas). Quand fourni, la perte
cross-entropy est pondérée par le masque et normalisée par la somme des masques (au lieu de la moyenne
uniforme) → les pas post-mortem des agents (obs=0) ne polluent PAS le gradient. `mask_seq=None` →
comportement actuel INCHANGÉ (rétro-compatible ; les tests WARM-001 restent verts). Additif : ne touche
aucune autre méthode.

Perte (mask_seq fourni) : `loss = Σ_t Σ_b mask[t,b]·CE(move_logits[t,b], tgt[t,b]) / Σ mask`.

### Composant 2 — `_collect_onpolicy_trajectory(genome, seed, num_agents, max_ticks, metab, cog)`

Déroule une cohorte du génome LEARNER on-policy in-world sous torch (W GELÉ via le patch make_population,
comme `_inworld_accuracy`), et enregistre les séquences fixed-B masquées que le learner visite lui-même.

**Alignement à travers les morts (point délicat, résolu par identité d'objet)** : le monde reconstruit la
pop torch quand B change (mortalité), mais les objets-MODÈLES (`a["model"]`) PERSISTENT. À l'init on fixe
`orig_index = {id(model): i}` pour les `num_agents` modèles initiaux. Dans `forward`, chaque ligne j est
mappée par `id(self.agents[j])` → son index d'origine (survit aux reconstructions ; les morts sont
simplement absents). On remplit `obs_seq[t]` (B=num_agents, 59) avec la ligne à l'index d'origine, `0` pour
les morts ; `tgt_seq[t]` = `2*(bit_a>0)+(bit_b>0)` par ligne vivante ; `mask_seq[t]` = 1 vivant / 0 mort.

**Signal frais** : l'obs est enregistrée DANS `forward` (le `_cog_sig` est re-randomisé au début de
`step()` → l'obs vue par le modèle a le signal du tick ; l'enregistrer hors forward donnerait un signal
périmé). Renvoie `(obs_seq, tgt_seq, mask_seq)`.

### Composant 3 — `run_dagger_warmstart(seed=2026, rounds=8, epochs_per_round=4000, lr=0.5, num_agents=12, max_ticks=200, metab, cog)`

Boucle DAgger avec dataset agrégé :
1. **Round 0 (bootstrap)** : dataset = trajectoire-ENSEIGNANT (`_collect_oracle_trajectory`, mask=1 partout).
   Entraîne une cohorte torch fraîche `epochs_per_round` epochs par `imitate_episode_bptt` (BPTT récurrent).
2. **Rounds 1..R-1** : `_collect_onpolicy_trajectory` sur le génome courant → AGRÈGE (obs/tgt/mask) au
   dataset (DAgger classique : garde toutes les trajectoires vues). Réentraîne `epochs_per_round` epochs
   sur le dataset agrégé (chaque trajectoire = un appel `imitate_episode_bptt` masqué, sommé sur le round).
3. Par round, mesure & trace : `acc_enseignant` (sur traj oracle), `acc_on-policy` (`_inworld_accuracy`),
   survie médiane, et à la fin le verdict marqueur (K≥12). Renvoie `{trend_onpolicy_acc, trend_survival,
   final_genome, final_verdict}`.

Agrégation bornée (≤ rounds trajectoires) → mémoire OK. Chaque trajectoire garde sa longueur propre.

### Composant 4 — entrée / wiring

`main()` (ou une entrée dédiée `WARM_DAGGER_ROUNDS`) : lance `run_dagger_warmstart`, imprime la courbe
acc_on-policy + survie par round + verdict final + PASS/FAIL (barre survie ≥ 100). Compare au 0.734/15 de
WARM-001 (le point de départ = round 0).

## Flux de données

```
round 0 : oracle traj (mask=1) --imitate BPTT--> genome_0 ; mesure acc_on-policy_0 (~0.73), survie_0 (~15)
round r : genome_{r-1} --_collect_onpolicy--> (obs,tgt,mask)_r ; dataset += ; --imitate BPTT (agrégé)-->
          genome_r ; mesure acc_on-policy_r, survie_r
final   : genome_{R-1} --verdict_demand_marker(torch,K=12)--> PASS/FAIL
```

## Gestion d'erreurs / pièges

- torch absent → skip propre (WARM-003 nécessite torch), message.
- W gelé pendant la collecte on-policy (patch make_population restauré en finally) — pas d'apprentissage
  pollueur pendant le rollout.
- non-repro KuzuDB → `memory_retriever.stop()` après chaque rollout.
- masque : normalisation par `Σ mask` (jamais /0 → garde `max(1, Σ mask)`).
- alignement par `id(model)` : robustesse vérifiée par un test (deux agents, une mort forcée → l'alignement
  tient).

## Tests

`tests/sandbox/test_warmstart_evolution_inworld.py` (ajouts) :
- `imitate_episode_bptt` avec `mask_seq` : un pas entièrement masqué n'affecte pas la perte (égale au run
  sans ce pas) ; rétro-compat (mask=None inchangé).
- `_collect_onpolicy_trajectory` : renvoie obs_seq/tgt_seq/mask_seq de même longueur, B=num_agents, masque
  ∈ {0,1}, au moins un pas entièrement vivant au début.
- `run_dagger_warmstart` smoke (rounds=2, epochs=8, num_agents=4, ticks=12) : renvoie les traces bien
  formées + un génome + un verdict, sans exception.
- Non-régression : suite WARM existante (6 tests) verte (mask_seq additif).

## Portée / limites

- Budget modéré (~6-8 rounds). Un NÉGATIF = « DAgger ne casse pas le 0.734 à budget modéré » (pas
  « impossible ») ; distinguerait alors transfert vs rétention (le substrat ne soutient pas la carte).
- DAgger idéal suppose une bonne couverture on-policy ; si le learner meurt très tôt, les premières
  trajectoires sont courtes (peu de couverture) — la boucle est censée s'auto-améliorer (survie ↑ →
  couverture ↑). Si elle stagne, c'est un finding (pas de cercle vertueux).
- Réétiquetage oracle = fonction pure f(bit_a,bit_b) → étiquette exacte disponible sur TOUT état visité
  (avantage propre à cette tâche réactive).

Converge [[EDR-WARM-001]] (le 0.734 qu'on attaque), [[decisive-substrate-thesis-test]],
[[warm-start-transversal-law]], REF-DEMAND-MARKER.
