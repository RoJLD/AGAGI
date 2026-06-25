# EDR 108 : La sélection diverse (tournoi) ne rescousse PAS l'apex — la sélection n'est pas le levier

## Contexte

EDR 105 a montré (corollaire mécanistique) que le carry élitiste top-3 dans la boucle évolutive
monoculturise → l'apex DÉCLINE (ère0 0.228 → ères6-11 0.082). Hypothèse à tester : une **sélection
diversité-préservante** (tournoi sur toute la population, vs top-3) stoppe-t-elle le déclin (issue 1,
sélection coupable) — ou l'apex plafonne-t-il quand même (issue 2, répertoire-monde = verrou) ?

Méthode (spec/plan `2026-06-25-Diverse-Selection-Apex`) : knob `EVP_SELECT` dans
`tools/evolve_ceiling_probe.py`. `elitist` = top-3 (baseline EDR 105) ; `diverse` = tirer
`n_carry=12` parents par `tournament_selection` (`tournament_size=3`) sur TOUTE la population de l'ère.
Cap de population `EVP_POP_CAP=200` (réutilise `config.max_population` ; corrige le runaway d'EDR 105).
**Garde-fou anti-théâtre** : métrique `genome_diversity` (std de `genome.W.mean()`) par ère — VÉRIFIER
que `diverse` est plus divers AVANT tout verdict apex. A/B × 3 graines, K=12, 40 agents, 300 ticks,
preserve_dims=True, sweet spot.

## Constat — mécanisme INCONCLUSIF, apex NON rescoussé

| mesure (moy 3 graines) | elitist | diverse |
|---|---|---|
| **genome_diversity (moy ères)** | **0.0011** | **0.0011** (ratio 1.07 — au plancher, NE SÉPARE PAS) |
| `frac_apex` ère0 → ères6-11 | **0.228 → 0.082** | 0.228 → **0.097** |
| population `n` (fin d'ère, ères tardives) | ~55 | ~72 |

Contrastes :
- **paire diverse−elitist** (frac_apex, n=36 graine×ère) : diverse>elitist 21 ères, < 11, **sign_p 0.110
  (NON significatif)**, Δmoy **+0.019**.
- **corrélation `genome_diversity` × `frac_apex`** (n=72) = **−0.247** (négative).
- **contrôle de cohérence** : le bras `elitist` reproduit le déclin d'EDR 105 **EXACTEMENT** (0.228→0.082)
  → le harnais est validé.

## Garde-fou déclenché — la diversité génomique mesurée est au PLANCHER (issue 3 partielle)

> La métrique `genome_diversity` (std de `W.mean()`) est **au plancher pour les DEUX bras** (~0.001,
> ratio 1.07) : elle NE valide PAS que le bras `diverse` a préservé plus de diversité génomique. Deux
> lectures : (a) la métrique est trop grossière (`W.mean()` écrase la structure : deux topologies très
> différentes ont la même moyenne) ; (b) la dynamique écologique INTRA-ère effondre la diversité quelle
> que soit la largeur du carry (12 vs 3 parents seedés). L'indice population (diverse 72 vs elitist 55 en
> fin d'ère) suggère une VRAIE différence de dynamique, mais qui ne remonte pas au niveau génomique mesuré.

Conséquence disciplinée : **je ne peux PAS attribuer proprement le résultat apex à la diversité** — la
distinction issue 1 / issue 2 reste partiellement ouverte sur le plan du mécanisme.

## Verdict — la sélection n'est PAS le levier de rescousse

> Indépendamment du mécanisme de diversité, le résultat apex est NET : **la sélection diverse ne
> rescousse PAS l'apex**. Le bras `diverse` décline encore (0.228 → 0.097), n'est PAS significativement
> au-dessus de l'élitiste (sign_p 0.110, Δ+0.019), et la corrélation diversité×apex reste NÉGATIVE
> (−0.247, cohérent EDR 105). Élargir le carry par tournoi — le correctif que pointait EDR 105 — laisse
> l'apex s'effondrer vers ~0.10.

Issue 1 (sélection coupable, apex rescoussé) **réfutée**. Issue 2 (répertoire-monde = verrou) **renforcée**
mais non close à 100% (caveat diversité). Convergence : EDR 104 (dose de diversité plate) + EDR 105
(croissance réseau n'aide pas) + EDR 108 (sélection diverse ne rescousse pas) → ni la dose, ni la
capacité réseau, ni le schéma de sélection ne lèvent l'apex. **Le verrou est en amont du moteur évolutif :
le répertoire/affordances du monde.**

## Signification — l'érosion de diversité d'EDR 105 est réelle mais la réparer ne suffit pas

EDR 105 avait identifié un vrai mécanisme (carry élitiste → érosion → déclin). EDR 108 montre que le
**réparer (tournoi large) ne suffit pas** : soit la réparation ne mord pas (diversité écrasée par
l'écologie intra-ère), soit elle mord (population plus saine) mais l'apex ne suit toujours pas. Dans les
deux cas, **le plafond apex survit au correctif de sélection** → il n'est pas porté par le schéma de
sélection. Cf. [[coop-competence-is-population-property]] (la diversité porte l'apex en STATIQUE, EDR 104,
mais on ne parvient pas à la MAINTENIR dynamiquement par la seule sélection),
[[nas-bottleneck-is-substrate-not-search]] (le goulot est le substrat/monde, pas la recherche).

## Anti-théâtre & limites honnêtes

- **Mécanisme vérifié AVANT verdict** (garde-fou respecté) : la métrique au plancher est RAPPORTÉE, pas
  cachée → le verdict apex est posé malgré l'inconclusivité du mécanisme, en le bornant explicitement.
- **Contrôle de cohérence** : élitiste = EDR 105 exact (harnais validé, pas de dérive inter-run).
- **Cap pop a tenu** : `pop_cap=200` jamais saturé (n max ~110), zéro explosion/timeout (corrige le
  hazard EDR 105).
- Trajectoire par ère (jamais scalaire nu), contraste apparié, corrélation, régime absolu.
- **Caveat instrument** : `genome_diversity = std(W.mean())` trop grossière → pour trancher proprement
  issue 1 vs 2, une métrique de diversité COMPORTEMENTALE (std des `mammoth_kills`/`preys_eaten`, ou
  distance génomique par paires) est requise (re-run avec logging enrichi).

## Statut

- Sélection (élitiste→diverse tournoi) : **pas un levier de rescousse de l'apex** (NS, Δ+0.019). Issue 1
  réfutée, issue 2 renforcée.
- **Pistes** :
  1. **Métrique de diversité comportementale** (cheap re-run) pour clore issue 1 vs 2 : le bras diverse
     est-il vraiment plus divers COMPORTEMENTALEMENT ? Si oui + apex plat → issue 2 fermée nette.
  2. **Pivot répertoire-monde** (option a, la piste amont) : la convergence 104/105/108 le désigne →
     diagnostiquer le répertoire d'affordances (coverage `map_elites_compare`) puis enrichir une
     affordance créant des stratégies distinctes utiles. STONEAGE-only (zéro collision Lewis/sessions //).
  3. Intervention de diversité plus forte (niching / MAP-Elites / nouveauté) si on veut épuiser le levier
     diversité — mais rendement décroissant vu 104/108.

## Variables d'expérience

`select` (elitist/diverse), `n_carry` (12), `tournament_size` (3 ; plus petit = plus diversifiant),
`pop_cap` (200 ; a tenu). Métrique-garde : `genome_diversity` (ICI au plancher → re-spécifier en
comportemental). Le `preserve_dims=True` fixé (moot apex, EDR 105).
