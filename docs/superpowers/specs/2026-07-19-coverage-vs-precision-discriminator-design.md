# Design — WARM-004 : discriminateur COUVERTURE vs PRÉCISION (ferme l'hypothèse ouverte de WARM-003)

Date : 2026-07-19
Statut : design approuvé (deux tests A+B)
Record visé : mise à jour d'EDR-WARM-003 (hypothèse ouverte → tranchée) ou EDR-WARM-004 selon le résultat.

## Contexte et question

EDR-WARM-003 : DAgger on-policy monte `acc_on-policy` à 0.988 et double la survie (15→35, marqueur 5.04),
mais plafonne loin de l'oracle (200). La revue finale a établi que le MÉCANISME du gap résiduel est une
**hypothèse OUVERTE** — le banc ne départage pas :
- **(a) COUVERTURE** (principale) : le learner meurt à ~35 → ne visite jamais les états tardifs → ne les
  apprend pas. `acc=0.99` est mesurée sur la fenêtre pré-mortem (tronquée + biais-survivant) donc
  quasi-tautologique. Plateau de survie et fenêtre d'accuracy = LE MÊME horizon.
- **(b) PRÉCISION** : le learner « sait » partout, mais ses ~1% d'erreurs résiduelles tombent aux états
  critiques (basse énergie, une erreur = mort).

## Les deux mesures qui tranchent

**(A) Test de COUVERTURE** — accuracy du génome DAgger sur les états **TARDIFS de l'ORACLE** (ticks > 35),
qu'il n'a jamais visités. On rejoue le génome (forward torch, sans grad, W gelé) sur la trajectoire de
l'oracle et on binne l'accuracy PAR TICK.
- accuracy s'effondre sur les bins tardifs → **COUVERTURE** (il ne sait pas hors de son vécu).
- accuracy reste haute (~0.99) partout → **PAS la couverture** (il sait même là où il n'est jamais allé).

**(B) Test de PRÉCISION** — accuracy sur son PROPRE rollout, binnée par **ÉNERGIE au moment de la décision**
(bins critiques basse-énergie vs confortables).
- chute spécifique en basse énergie → **PRÉCISION aux états critiques**.
- accuracy uniforme sur l'énergie → **PAS la précision**.

**Table de décision :** A basse → couverture. A haute + B chute → précision. A haute + B plate → NI l'un ni
l'autre (chercher ailleurs : p.ex. dynamique métabolique inéluctable au-delà de l'horizon entraîné). Les
quatre cases sont interprétables — le test ne peut pas « ne rien dire ».

## Régime

Identique S2-009/WARM (cognitive_demand, metab=0.75, cog=12, forage_payoff=0, benchmark_mode,
night_enabled=False, current_era=10_000). seed=2026, num_agents=12, max_ticks=200.

## Architecture (extension de `tools/warmstart_evolution_inworld.py`)

### Composant 1 — `_collect_diag_trajectory(driver, genome=None, ...) -> (obs_seq, tgt_seq, mask_seq, energy_seq)`

Collecteur de diagnostic unifié, **pleine longueur** (jusqu'à `max_ticks`, PAS de troncature à la 1ʳᵉ mort)
et **masqué**, alignant chaque ligne à son index d'origine par `id(model)` (les objets-modèles persistent
aux reconstructions de pop / ré-instanciations du batch model). Deux modes :
- `driver="oracle"` : `env.batch_model_cls = _RecordingOracleMasked` (chemin NON-torch ; l'oracle pilote,
  les génomes sont ignorés) → donne les états TARDIFS de l'oracle (ticks 35→200) que le learner ne visite
  jamais. **C'est la donnée que l'actuel `_collect_oracle_trajectory` ne peut PAS fournir** (il tronque à
  la 1ʳᵉ mort ≈ 35).
- `driver="genome"` : `use_torch_inworld=True` + pop torch enregistreuse GELÉE (lr=0, patch
  `make_population` restauré en `finally`) portant `genome` → rollout on-policy du learner.

**Énergie** : lue DANS le `forward` depuis l'env (closure sur `e`), donc à l'instant de la DÉCISION (avant
la résolution biologique du tick), alignée comme le reste par `id(model)`. On ne devine PAS une colonne
d'obs. Morts → obs 0 / tgt 0 / mask 0 / énergie NaN.

**Étiquette oracle** : `tgt = 2*(bit_a>0)+(bit_b>0)` (cols BIT_A=12/BIT_B=13), fonction pure → disponible
sur TOUT état visité, quel que soit le pilote.

### Composant 2 — `accuracy_binned(genome, obs_seq, tgt_seq, mask_seq, bin_ids, n_bins) -> list[dict]`

Rejoue `genome` sous forward **torch** (`TorchPopulationModel`, `torch.no_grad`, W gelé — pas de monde,
pur replay) sur `obs_seq` depuis H=0, compare `argmax(out[:, :8])` à `tgt_seq[t]`, et agrège l'accuracy par
bin selon `bin_ids[t]` (tableau (B,) d'index de bin par agent, ou -1 = ignorer). Ne compte que les entrées
`mask_seq[t]==1`. Renvoie par bin : `{bin, n, acc}`.

Deux fabriques de bins :
- `bins_by_tick(mask_seq, edges)` → bin = index du segment de tick (p.ex. edges=[0,35,70,120,200]).
- `bins_by_energy(energy_seq, mask_seq, edges)` → bin = index du segment d'énergie (p.ex.
  edges=[0,20,40,60,80,101]).

### Composant 3 — `run_coverage_precision_diagnostic(...)`

1. Reproduit le génome DAgger (`run_dagger_warmstart(rounds=6, …)`) — **le génome de WARM-003 n'avait pas
   été persisté** ; on le SAUVE cette fois (`results/warm003_dagger_genome.npz`) pour ne plus re-payer.
2. **Test A** : `_collect_diag_trajectory(driver="oracle")` → `accuracy_binned(genome, …, bins_by_tick)`.
3. **Test B** : `_collect_diag_trajectory(driver="genome", genome=g)` → `accuracy_binned(g, …, bins_by_energy)`.
4. Imprime les deux tables + le verdict selon la table de décision ci-dessus.

**Contrôle POSITIF de l'instrument** : passer l'ORACLE lui-même au test A est impossible (l'oracle n'est pas
un génome) ; on utilise à la place un **contrôle NÉGATIF** = génome aléatoire (accuracy ≈ hasard 0.25 dans
tous les bins), qui valide que `accuracy_binned` discrimine bien.

## Gestion d'erreurs / pièges

- torch absent → diagnostic skip propre.
- `bins_by_energy` : agents morts → énergie NaN → bin -1 (ignoré).
- Replay pur (Composant 2) sans monde : pas de contention KuzuDB ; les collectes (Composant 1) en font.
- `memory_retriever.stop()` après chaque collecte. Patch `make_population` restauré en `finally`.
- Sauvegarde génome : créer `results/` s'il n'existe pas (piège déjà rencontré).

## Tests

- `_collect_diag_trajectory(driver="oracle")` : longueur > 35 (dépasse la troncature de l'ancien collecteur),
  masque ∈{0,1}, énergie finie là où mask=1, B=num_agents.
- `_collect_diag_trajectory(driver="genome")` : idem, B=num_agents.
- `accuracy_binned` : sur un génome aléatoire → accuracy ≈ hasard dans chaque bin peuplé (contrôle négatif,
  discrimination de l'instrument) ; les `n` par bin somment au total masqué.
- `bins_by_tick` / `bins_by_energy` : mapping correct sur un cas jouet.
- Non-régression : suite WARM existante (9 tests) verte (tout est ADDITIF).

## Portée / limites

- Le test A rejoue le génome sur la trajectoire de l'ORACLE : son état récurrent H suit alors l'historique
  de l'oracle, pas le sien. C'est le contrefactuel VOULU (« s'il se trouvait dans ces états-là, déciderait-il
  juste ? »), mais ce n'est pas identique à « y arriver par lui-même ».
- L'accuracy reste une mesure de DÉCISION ; elle ne mesure pas la dynamique énergétique. Le cas « A haute +
  B plate » renverrait explicitement vers une cause non-décisionnelle.
- Budget : dominé par la reproduction du DAgger (~40 min) ; les collectes/replays sont marginaux.

Converge [[EDR-WARM-003]] (ferme son hypothèse ouverte), [[EDR-WARM-001]], REF-DEMAND-MARKER.
