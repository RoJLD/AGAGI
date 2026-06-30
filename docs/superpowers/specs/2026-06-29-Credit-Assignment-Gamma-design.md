# Design — γ-sweep : l'horizon d'attribution de crédit étrangle-t-il le craft→apex ?

Date : 2026-06-29

## Question scientifique

EDR 111 (tool-gate) a montré que le substrat ne pivote PAS vers l'outil quand le monde l'exige : sous gate,
le craft n'émerge pas (`frac_tool` plancher) et l'apex s'effondre. Convergence 104-111 : ni capacité réseau
(105/110), ni sélection (108), ni diversité (104), ni durcissement du monde (111) ne lèvent l'apex → le
verrou est la **capacité d'apprentissage du substrat**.

Hypothèse mécanistique précise : l'apprentissage intra-vie (Actor-Critic TD(0), `compute_policy_gradient`)
**est actif en prod** ET son `td_error` est explicitement conçu pour le crédit TEMPOREL (« crafter coûte
maintenant → pouvoir chasser l'apex plus tard »). MAIS `γ=0.9` est hardcodé → l'horizon effectif
≈ 1/(1−γ) = **10 ticks**, alors que la chaîne grab→rub→craft→chasse s'étale sur **100-300 ticks**. La valeur
escomptée d'un apex 100 ticks après le craft = 0.9¹⁰⁰ ≈ 0.00003 ≈ 0 → le mécanisme censé lier craft↔apex
est mathématiquement étranglé par γ. **Relever γ (étendre l'horizon) fait-il émerger la stratégie
craft→apex ?**

Puzzle qui motive : `scaffold_craft=5.0` (récompense IMMÉDIATE au craft) + `novelty_bonus` (précurseurs,
EDR 014) sont DÉJÀ actifs, et pourtant `frac_tool` reste au plancher (~0.01). L'incitation immédiate ne
suffit pas → c'est cohérent avec un déficit de crédit TEMPOREL sur la chaîne longue (le craft ne « paie »
que via l'apex futur, hors de portée à γ=0.9).

## Contexte (vérité terrain)

- `td_error(reward, value, next_value, gamma=0.9) = reward + gamma*next_value - value`
  (`src/seed_ai/policy_gradient.py:24-33`). Docstring : « γ règle l'horizon (myope ↔ prévoyant) ».
- Actor-Critic TD(0) one-step, update DIFFÉRÉ d'un tick (la transition (s,a,r) est mise à jour au tick
  suivant quand V(s') est connu) : `src/agents/mamba_agent.py:778-821`. `lr_actor, lr_critic, gamma =
  0.04, 0.05, 0.9` **hardcodés** (`mamba_agent.py:783`). Appelé en prod chaque tick (`world_1_stoneage.py:1444`).
- Critic = value head (nœud de sortie 28), bootstrap online vers `r + γV(s')`.
- Patron de knob établi : `MambaBatchModel.PLAN_BIAS = 0.0` (attribut de CLASSE, `mamba_agent.py:311`, lu en
  `:807`). On mirroite ce patron pour γ (pas de champ `WorldConfig`, l'apprentissage vit dans le modèle).
- Scaffolds craft actifs : `scaffold_craft=5.0` (`world_1_stoneage.py:120`), `novelty_bonus`
  (`scale=3.0`, `world_1_stoneage.py:1440`), `crit_chance` annelé (EDR 022).

## Hypothèse (3 issues)

1. **Horizon = verrou (RÉPARABLE)** : à γ=0.99/0.999, `frac_tool` ET `frac_apex` MONTENT (dose-réponse avec
   l'horizon) ET la chasse de base tient → l'attribution de crédit temporel était le verrou → tuner γ en
   prod = levier majeur, premier mécanisme qui LÈVE l'apex.
2. **Horizon éliminé** : γ↑ ne change rien (chasse saine) → le crédit temporel n'est pas le verrou → le
   substrat est limité plus profond (représentation/exploration/connectivité) → pivot piste A (connectivité)
   ou TD(λ).
3. (garde-fou) **Instable** : γ↑ DÉSTABILISE l'apprentissage (variance ↑, valeur explose) → la chasse de
   base s'effondre → résultat CONFONDU (« horizon pas le verrou » indistinct de « γ a cassé l'apprentissage »)
   → rapporter l'instabilité, ce n'est PAS une réfutation propre de l'hypothèse horizon.

## Architecture — unités

### Unité 1 — knob `TD_GAMMA` (modèle)

`src/agents/mamba_agent.py` : ajouter un attribut de CLASSE `MambaBatchModel.TD_GAMMA = 0.9` (près de
`PLAN_BIAS`, `:311`). Dans `compute_policy_gradient` (`:783`), remplacer le `gamma` hardcodé du tuple par
la lecture de `MambaBatchModel.TD_GAMMA` (garder `lr_actor=0.04`, `lr_critic=0.05` inchangés). Défaut 0.9
= byte-identique au comportement actuel (non-régression).

### Unité 2 — propagation `EVP_GAMMA` (probe)

`tools/evolve_ceiling_probe.py` : dans `main`/`run_evolution`, lire `EVP_GAMMA` (défaut "0.9") et l'assigner
à `MambaBatchModel.TD_GAMMA` AVANT la boucle d'ères (import de `MambaBatchModel` requis). Le knob est global
au modèle, posé une fois.

### Unité 3 — sweep A/B/C (pas de code)

Sweep `EVP_GAMMA ∈ {0.9, 0.99, 0.999}` × 3 seeds, mêmes params que 108/109/111 (K=12, 40 agents, 300 ticks,
sweet spot 0.25/3, preserve_dims=1, select=elitist). **Détection de succès par EXIT CODE python** (piège
EDR 108 : `2>/dev/null` avale `TRAJ`). JSON `results/evolve_ceiling_probe_0.json` s'écrase → copier
immédiatement par run.

## Instrument & verdict

Trajectoire PAR ÈRE, appariée par seed :
- **`frac_tool`** (`spears_crafted`) : le craft émerge-t-il quand l'horizon s'étend ?
- **`frac_apex`** (`mammoth_kills`) : l'apex monte-t-il (dose-réponse avec γ) ?
- **`median_competence`** (inclut `frac_hunt` 0.4) + `n` (survie/population) : SANTÉ de l'apprentissage —
  garde-fou issue 3. Si la chasse de base s'effondre à γ élevé → instabilité, null confondu.
Contraste apparié γ_haut − γ=0.9 ; régime absolu ; dose-réponse vs log-horizon.

## Contrôles de cohérence & anti-théâtre

- **Cohérence contrôle** : γ=0.9 DOIT reproduire l'apex 108/109/111 (ère0 ≈ 0.228, late ≈ 0.082) → harnais
  validé, γ non-régressif. Écart → non-repro signalé.
- **Garde-fou santé d'apprentissage** : distinguer « horizon pas le verrou » (chasse saine, apex plat) de
  « γ a cassé l'apprentissage » (chasse effondrée). Mesuré explicitement AVANT le verdict.
- **Mécanisme avant verdict** : la dose-réponse (monotone avec l'horizon) EST la signature mécanistique ; si
  l'apex monte à γ=0.99 mais pas plus à 0.999, c'est cohérent avec un horizon-seuil (~100 ticks = chaîne
  craft→apex). Rapporter la forme, pas juste un scalaire.
- Trajectoire par ère, contraste apparié, données perdues/runs échoués rapportés honnêtement.
- Verdict BORNÉ : si transition partielle (apex monte un peu, chasse légèrement dégradée), décrire sans
  surclaim.

## Tests

- **Non-régression** : `MambaBatchModel.TD_GAMMA == 0.9` par défaut → `compute_policy_gradient` byte-identique
  à l'actuel ; `test_evolve_ceiling_probe` + `test_diverse_selection` restent verts.
- **Smoke knob** : poser `MambaBatchModel.TD_GAMMA = 0.99` (ou via `EVP_GAMMA`) → la valeur lue dans
  `compute_policy_gradient` est 0.99 (vérifier que le knob se propage jusqu'à l'update). Test ciblé sur la
  lecture de γ (pas un run complet).

## Hors périmètre (YAGNI)

- Pas d'eligibility traces TD(λ) (2ᵉ chantier si γ null — teste la VITESSE de propagation, pas l'HORIZON).
- Pas de sweep `lr_actor`/`lr_critic` (confond l'effet horizon).
- Pas de re-architecture, pas de touche au dreaming/planner (réfutés, `FORCE_DREAM=None`, `PLAN_BIAS=0.0`
  inchangés). Stoneage-only (zéro collision Lewis/EDR 110).

## Suite (selon issue)

- **Issue 1 (horizon = verrou)** : câbler γ optimal en prod (défaut `MambaBatchModel.TD_GAMMA`) + re-tester
  l'apex global (le premier levier qui lève le plafond) ; éventuellement TD(λ) pour accélérer.
- **Issue 2 (horizon éliminé, sain)** : pivot piste A (connectivité I→caché→O, le connectome 97% I/O) ou
  TD(λ) (propagation lente vs horizon court).
- **Issue 3 (instable)** : ajouter une stabilisation (normalisation d'avantage, clip de valeur) avant de
  re-tester l'horizon.

## Variables d'expérience

`TD_GAMMA` (knob central, défaut 0.9 = contrôle, sweep {0.9, 0.99, 0.999}) ; `EVP_GAMMA` ; détection succès
par exit code. Réutilise tous les autres knobs de 108/109/111 (select, n_carry, pop_cap, preserve_dims,
sweet spot, mammoth_hp=100 défaut). EDR cible = **112** (109=diversité comportementale, 110=capacity-nav
Lewis mergé, 111=tool-gate apex ; à reconfirmer libre à l'écriture).
