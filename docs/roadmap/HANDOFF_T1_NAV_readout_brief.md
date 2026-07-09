# Brief T1 — Entraîner la tête d'action NAV par gradient (prêt-à-exécuter)

> Élabore la cible **T1** de [`HANDOFF_TORCH_READOUT_CREDIT.md`](HANDOFF_TORCH_READOUT_CREDIT.md).
> Destiné à la session torch. Vérifié 2026-07-02 : **aucune session parallèle sur T1** (la session
> disjoint-heads/C1 est CLOSE — PR #136 « clôture arc 152→192 » ; cible distincte). T1 est libre.

## Objectif (une ligne)

Entraîner par gradient la **tête d'action** du substrat torch pour qu'elle convertisse la direction-cible
**déjà présente dans H** en le bon déplacement → fermer `p_reach` de ~0.52 vers l'oracle ~0.875 (EDR 114).

## Preuve que c'est le bon levier (et non l'encodeur)

- **EDR-NAV-001** : H décode la direction-correcte à **0.81** (≈ plafond obs 0.96), mais `émise==correct`
  = **0.03**. Le signal est là ; la tête d'action ne l'exploite pas. → readout, pas encodeur.
- **EDR-NAV-002** : la détresse énergétique est aussi richement dans H (0.89-0.91) → « encodeur OK »
  robuste. Corollaire méthodo : **utiliser un label-cible EXOGÈNE** (l'oracle de position ; l'énergie,
  endogène, ne marche pas).

## Points d'accroche (déjà en place dans `src/agents/backend_torch.py`)

- Substrat LTC différentiable, `self.W` = `Parameter` entraînable (SGD, `self.opt`), autograd.
- **Tête d'action** : `forward` → `logits = H_new[:, self.N - self.O : self.N]` ; move logits = `out[:, :8]`
  (N/S/E/O = indices 0/1/2/3, cf. `_reach_oracle_action` du monde : 0=N 1=S 2=E 3=O).
- **Apprentissage** : `learn`/`_td_update` = Actor-Critic TD(0) par autograd (`loss.backward()`, `opt.step()`,
  `_write_back` Baldwin). C'est LÀ qu'on ajoute le terme auxiliaire.
- **Label exogène** : `Biosphere3D._reach_oracle_action(agent)` (flag `reach_oracle`, EDR 114) donne
  déjà le pas glouton correct. Le réutiliser comme cible supervisée (ne PAS override l'action — juste
  fournir le label).

## Approche recommandée : perte auxiliaire supervisée (flag OFF par défaut)

Ajouter à `_td_update` un terme gaté :
```
# gaté par un flag (ex. self.nav_aux_weight > 0, défaut 0.0 -> non-régressif)
if self.nav_aux_weight > 0 and oracle_dirs is not None:   # oracle_dirs (B,) in {0,1,2,3} ou -1 (=ignore)
    mask = oracle_dirs >= 0
    L_nav = F.cross_entropy(out[mask, :4], oracle_dirs[mask])   # tête move -> direction-oracle
    loss = loss + self.nav_aux_weight * L_nav
```
Le gradient traverse `out = readout(H_new(W))` → ajuste la tête d'action (et W) pour mapper la direction
présente dans H vers le bon logit. **Ne touche pas l'encodeur explicitement** ; l'aux loss est additive à
l'Actor-Critic existant. Alternative (reward-shaping per-pas dense) : **désormais étayée aussi** — EDR-NAV-003
montre que le readout est RL-récupérable dès que le signal est dense (le champion a échoué NON par incapacité
mais par signal de forage trop clairsemé). L'aux supervisé reste le plus dense/direct ; le shaping est une
route équivalente. Le risque n'est plus « le readout est-il entraînable » (résolu) mais « fournir le signal ».

## Jalons (dé-risqués)

**M1 — offline ✅ FAIT (EDR-NAV-003, `tools/nav_readout_trainability.py`).**
Non pas « un Linear sait-il fitter » (redondant avec le ridge NAV-001) mais la **fourche de conception** :
sur les mêmes paires `(H, correct)` figées, deux readouts identiques (seule la perte diffère) — SUPERVISÉ
(CE oracle) vs RL (REINFORCE-bandit dense aligné). **RÉSULTAT (n=17411, déterministe) : RL_RECOVERS
(recovery +0.923 ; SUP 0.858 / RL 0.822 ≈ ridge 0.825)**. → **le readout de navigation EST RL-récupérable**
dès qu'on lui donne un signal per-pas dense. L'échec in-world (émise==correct=0.03) est donc un problème de
**DENSITÉ/ALIGNEMENT du signal**, PAS de trainabilité du readout. **Fourche résolue** : les DEUX routes sont
étayées — (a) aux supervisé (signal le plus dense) OU (b) reward-shaping per-pas dense ; le choix devient un
détail d'implémentation, pas un risque.

**M2 — in-world (intégration).**
Câbler `nav_aux_weight` + faire passer `oracle_dirs` du monde à `learn` (le monde calcule déjà le label via
`_reach_oracle_action`). Entraîner en forage Lewis. Flag OFF par défaut (parité prod, EDR 140/141).

## Critères de succès (mesurables, bancs existants)

1. **M1** ✅ : SUP 0.858 / RL 0.822 (recovery +0.923) → RL_RECOVERS (EDR-NAV-003). Fourche résolue.
2. **M2 — probe** : relancer `tools/nav_localization_probe` sur la politique torch → `émise==correct`
   monte de ~0.03 vers ~0.8 ; `H→correct` reste haut (encodeur intact).
3. **M2 — survie** : `tools/lewis_survival_sweep._measure_forage(disable_repro=True)` → `p_reach` de
   ~0.52 vers ~0.875 (borne oracle, EDR 114 ; de-confondu 114b).
4. **Non-régression** : `nav_aux_weight=0` (défaut) → sortie byte-identique au backend torch actuel.

## Coordination & garde-fous

- **Ownership** : `src/agents/backend_torch.py` (+ un petit hook monde→learn pour `oracle_dirs`). Territoire
  session torch. Discipline **flag OFF par défaut**.
- **Ne PAS** : toucher l'encodeur récurrent (disculpé 3× : NAV-001/002, disjoint 190-191) ; refonte archi #5
  (réfutée EDR 153) ; override l'action par l'oracle en prod (l'oracle est un LABEL d'entraînement, pas la
  politique).
- **Pont inter-murs** (EDR-NAV-002) : après M2, re-mesurer la **survie** Lewis — un readout NAV réparé
  pourrait lever aussi le mur d'énergie (la détresse énergétique est aussi dans H), même si l'énergie seule
  n'était pas mesurable.

## Risques / questions ouvertes

- L'aux supervisé pourrait dégrader d'autres têtes (grab/rub/value) si `nav_aux_weight` trop grand → sweeper
  le poids ; surveiller `p_cap`/life_score hors flag.
- Le label oracle est un **pas glouton 1-pas** (pas BFS) : plafond ~0.875 avec obstacles (EDR 114), suffisant.
- Généralisation hors-oracle : après entraînement supervisé, vérifier que la politique atteint SANS le label
  (le label ne sert qu'à l'entraînement ; à l'inférence, la tête doit décoder H seule).
