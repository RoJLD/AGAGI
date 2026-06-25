# EDR 105 : La croissance topologique accumulée ne lève PAS le plafond apex — la capacité réseau est éliminée comme verrou

## Contexte

Tout le plafond apex (~0.16-0.21, EDR 097/102/103/104) avait été mesuré sur des populations
**non-évolutives** (la sonde charge des génomes et tourne UNE ère). Le « substrat » avait deux lectures :
(a) **capacité réseau** (le diagnostic « hidden=5/172 » était en grande partie l'artefact du bug
`from_genome` qui ré-aplatissait le champion à 172 à chaque ré-import, empêchant la croissance topologique
de s'accumuler entre générations — [[from-genome-flattens-architecture]]) ; (b) **répertoire
comportemental du monde**. Le fix `preserve_dims` (prod, PR #58) débloque l'accumulation. **Question : quand
la croissance s'accumule (`preserve_dims=True`), les réseaux grossissent-ils ET l'apex monte-t-il — ou
plafonne-t-il (→ verrou = répertoire-monde, pas la capacité réseau) ?**

Méthode (spec/plan `2026-06-25-Evolve-Ceiling-Probe`) : nouvel outil `tools/evolve_ceiling_probe.py`,
harnais évolutif PROPRE (carry des top-3 champions EN MÉMOIRE entre ères, déterministe, `preserve_dims`
appliqué au ré-import inter-ère — seul endroit où l'aplatissement mord). A/B `preserve_dims ∈ {True, False}`,
K=12 ères, 40 agents, 300 ticks, stoneage sweet spot, 3 graines visées.

## Constat — la taille monte, l'apex NON

| mesure | preserve=True (3 graines) | preserve=False (contrôle) |
|---|---|---|
| `mean_nodes` ère0 → ère11 | **172.6 → 175.2** (accumule : +5.1/+0.4/+2.3 par graine) | **172.1 → 172.0** (plat, −0.1) |
| `frac_apex` ère0 → ères6-11 | **0.228 → 0.082** (DÉCLINE, −0.146) | 0.151 → ~0.08 (plat/scatter) |
| population `n` ère0 → ère11 | 110 → 55 (rétrécit) | 126 → 52 |
| `cap_hits` (node_cap=512) | 0 (jamais atteint) | 0 |

**Contrastes décisifs :**
- **Corrélation interne `mean_nodes` × `frac_apex` (True, n=36 points ère×graine) = −0.176.** Plus de nœuds
  n'aide PAS l'apex — au contraire. La graine qui a le plus grossi (T_s0, +5.1) a le PIRE effondrement
  d'apex (0.29 → 0.05).
- **Paire True−False (graine 0, appariée par ère) : True>False 7/12 ères, sign_p 0.774 (NON significatif),
  Δmoy +0.023.** À génération égale, la croissance ne confère AUCUN avantage apex.

## Verdict — capacité réseau ÉLIMINÉE comme verrou de l'apex

> La croissance topologique s'accumule bien sous `preserve_dims=True` (taille +2.6 en moyenne vs contrôle
> plat à 172) — le mécanisme du fix prod est VIVANT. Mais l'apex **ne suit pas** : corrélation taille×apex
> **négative (−0.18)**, et à génération égale la croissance ne bat pas le contrôle (sign_p 0.774). **Le
> plafond apex N'EST PAS levé par de plus gros réseaux.** La capacité réseau est éliminée comme verrou ;
> il reste le **répertoire comportemental du monde**.

Issue 3 (pas de croissance) écartée (taille monte clairement vs contrôle plat). Issue 1 (apex monte)
réfutée. **Issue 2 retenue.** Cohérent avec « connectome 97% I/O » ([[nas-d1-metabolic-cost-refuted]]) et
EDR 103 (archi « en plus » du champion inerte) : la topologie supplémentaire ne calcule rien d'utile pour
la chasse apex.

## Signification — l'apex DÉCLINE par érosion de diversité (EDR 104 dynamique)

Constat structurant indépendant : l'apex est MAXIMAL à l'ère 0 (soupe HoF fraîche, diverse) puis DÉCLINE
(0.228 → 0.082) à mesure que la population descend des top-3 champions portés — dans les DEUX bras. C'est
[[coop-competence-is-population-property]] (EDR 104) qui se REJOUE dans la boucle évolutive : **le carry
élitiste top-3 est une monoculturisation progressive → érode la diversité → l'apex tombe.** Sous ce régime
évolutif, l'apex ne peut que DESCENDRE (érosion de diversité), jamais monter via de plus gros cerveaux.

> Caveat de confond (traité par le contraste apparié) : le bras True confond croissance (+) et érosion de
> diversité (−). C'est pourquoi le verdict s'appuie sur (1) la corrélation interne taille×apex NÉGATIVE et
> (2) la paire True−False (les deux bras partageant l'érosion, leur différence isole la croissance) — pas
> sur la trajectoire True brute.

> Convergence (7ᵉ ligne) : comme EDR 090/095/096/102/103/104 et NAS D1/D2/A2, ni la recherche, ni la
> sélection, ni la diversité-réglage, ni désormais la **capacité réseau** ne sont le verrou de la
> compétence apex. Reste le **répertoire/affordances du monde** ([[nas-bottleneck-is-substrate-not-search]],
> [[world-floor-survivability-gate]]) — la seule piste amont restante.

## Anti-théâtre & limites honnêtes

- **Croissance modeste** (+2.6 moy) : à `add_node_rate=0.2` + sélection élitiste + reset par extinction,
  la croissance est lente. MAIS la corrélation est NÉGATIVE (pas juste nulle) et la plus forte croissance
  donne le pire apex → un volume de croissance plus grand n'inverserait pas le signe.
- **Contrôle False mince (n=1)** : `preserve=False` graines 1 et 2 ont **explosé en population** (runaway,
  timeout 240s — hazard connu, le harnais n'a pas de cap de population, seul `node_cap` borne les nœuds).
  Finding instrument : le régime aplati est explosion-prone à 2/3 graines. Le verdict repose sur le bras
  True (3 graines, corrélation interne) + la paire graine-0, pas sur un contrôle False complet — signalé,
  pas masqué.
- Trajectoire par ère (jamais scalaire nu), contraste apparié, régime absolu (taille ET apex), `cap_hits`
  rapporté (0), explosions loguées et non silencieusement abandonnées.

## Statut

- Capacité réseau ÉLIMINÉE comme verrou de l'apex (corrélation −0.18, paire sign_p 0.774). Le fix
  `preserve_dims` est vivant (taille accumule) mais n'achète pas d'apex. Trilogie substrat-réseau close :
  D2 (sparsité imposée efficace) + EDR 103 (archi champion inerte) + EDR 105 (croissance n'aide pas).
- **Piste restante (la seule amont)** : le **répertoire comportemental du monde**. Diagnostiquer puis
  enrichir une affordance qui crée des stratégies DISTINCTES utiles (≠ survie/forage/coop-apex actuels), de
  sorte que l'évolution ait quelque chose à exploiter au-delà du plafond. + corollaire : tester une
  sélection NON-élitiste (préservant la diversité) puisque le carry top-3 érode l'apex.

## Variables d'expérience

`preserve_dims` (AXE, accumulation ON/OFF), K ères (profondeur ; ici 12), graines (réplicats ; False
limité par explosion), `add_node_rate` (prod 0.2 ; un sweep de croissance plus agressive serait un
chantier distinct mais la corrélation négative en réduit l'intérêt), schéma de sélection (top-3 élitiste
= érode la diversité → tester tournoi/diversité). Garde-fou compute : cap de population à ajouter au
harnais si le bras False est re-tenté.
