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
l'Actor-Critic existant. Alternative (pure RL / reward-shaping sur l'atteinte) : plus faible — le champion
a évolué sous RL et a échoué (NAV-001) ; l'aux supervisé exploite directement le signal linéairement présent.

## Jalons (dé-risqués)

**M1 — offline, rapide, couplage minimal (preuve de concept).**
Charger les paires `(H, oracle_dir)` capturées par `tools/nav_localization_probe.capture` ; entraîner une
tête `torch.nn.Linear(N→4)` par gradient sur ces paires ; montrer que `argmax(head(H)) == oracle_dir` monte
vers l'accord de décodage (~0.8). **Prouve que la tête d'action PEUT apprendre le mapping** (le probe montre
qu'un readout *frais* décode à 0.81 ; M1 le refait par gradient torch). Zéro modif de la boucle in-world.

**M2 — in-world (intégration).**
Câbler `nav_aux_weight` + faire passer `oracle_dirs` du monde à `learn` (le monde calcule déjà le label via
`_reach_oracle_action`). Entraîner en forage Lewis. Flag OFF par défaut (parité prod, EDR 140/141).

## Critères de succès (mesurables, bancs existants)

1. **M1** : accuracy `head(H)→oracle_dir` (test) ≥ ~0.75 (proche du décodage linéaire 0.81 de NAV-001).
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
