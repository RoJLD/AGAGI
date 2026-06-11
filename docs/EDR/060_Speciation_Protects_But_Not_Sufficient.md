# EDR 060 : Spéciation — elle protège l'innovation (ça marche), mais ce n'est pas suffisant

## Contexte

EDR 058 : l'architecture ne grandit jamais (172) car le HoF élitiste strict tue l'innovation immature.
Lever (NEAT) : la **spéciation par taille** (`persistence.SPECIATE`) réserve une niche à chaque taille
→ un 173-nœuds garde un siège et peut mûrir. Test sur la tâche-MÉMOIRE (transient), A/B ON vs OFF,
6 seeds × 20 ères. Départage : *protection* (perf monte) vs *demande* (archis préservées mais inutiles).

## Résultat

| | mammouth/ère | nodes (moy / max) |
|---|---|---|
| OFF | 1.09 ± 0.28 | 172.0 / **172** |
| SPEC | 1.04 ± 0.25 | 172.1 / **174** |

t=−0.33, d=−0.19 → pas de différence de perf.

## Lecture — la protection MARCHE, mais ne suffit pas

- **✅ La spéciation fait son travail** : des architectures à **173-174 nœuds apparaissent et
  PERSISTENT** (3 seeds/6), là où c'était *verrouillé à 172* (046/049/058). **La croissance est
  désormais POSSIBLE** — l'innovation immature n'est plus tuée à la naissance.
- **❌ Mais pas utile (à cette échelle)** : perf inchangée (1.04 vs 1.09), moyenne ~172 (les grandes
  archis sont *préservées* mais ne *prolifèrent* ni n'*aident*).

> **Protection NÉCESSAIRE mais pas SUFFISANTE.** Deux causes possibles, non exclusives : (a) la
> demande est trop petite — 1 bit de mémoire ne *justifie* pas un plus gros cerveau ; (b) 20 ères ne
> suffisent pas à *mûrir* le nouveau nœud (l'optimiser en quelque chose d'utile). On a débloqué la
> *possibilité* de grandir ; il manque une *raison* et le *temps*.

## L'unification, raffinée

- Le **diagnostic** (EDR 058 : la sélection stricte tue la nouveauté) **tient** — et la spéciation le
  confirme *par construction* (protéger → la nouveauté survit enfin).
- Le **lever** « protéger la nouveauté » est **conceptuel** ; l'implémentation est *frontière-
  spécifique* : **par taille** pour le NAS (testée ici, protège bien), **par comportement/distance
  génétique** pour le langage (protéger les lignées porteuses de convention — *non testé*). Mon
  expérience a validé la spéciation-par-taille comme *protection*, pas comme *solution complète*.

## Suites (ciblées)

1. **Spéciation + demande de mémoire PLUS GROSSE** (multi-bits : retenir le type de *plusieurs*
   apex, ou sur un *délai* plus long) + **plus d'ères** → la croissance protégée devient-elle utile ?
2. **Spéciation par comportement** pour le langage (protéger les lignées à convention) → la loterie
   ~25 % monte-t-elle ? (le pendant langage, non testé).
3. C'est typiquement ce qu'un **#8** itérerait : proposer demande+protection, mesurer, raffiner.

## Statut

- `SPECIATE` : seam construit (off par défaut), **protège l'innovation** (max 174 vs 172). 138 tests.
- NAS re-cadré (encore) : *protection acquise* ; reste demande-suffisante + maturation.

## Variables d'expérience

Taille de la demande de mémoire (bits, délai), nb d'ères (maturation), spéciation par taille vs
comportement, profondeur des niches (1 vs K agents/taille).
