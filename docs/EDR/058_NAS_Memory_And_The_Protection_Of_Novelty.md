# EDR 058 : NAS-mémoire — l'architecture ne grandit toujours pas, et POURQUOI (unification)

## Contexte

EDR 046/049 : forcer `add_node` ne fait pas grandir l'architecture (HoF figé à 172) — attribué à
« le monde ne demande pas plus de cerveau ». EDR 058 : on crée une **demande de mémoire** (type
d'apex *transitoire* — révélé au 1ᵉʳ contact puis caché → l'agent doit RETENIR pour rester/fuir),
`world.transient_apex`. La croissance est-elle enfin sélectionnée ?

## Résultat — toujours figé

A/B transient ON vs OFF (add_node=0.6), 6 seeds × 16 ères :

| | taille connectome HoF (moy ± σ) | mammouth/ère |
|---|---|---|
| OFF | **172.0 ± 0.0** | 1.35 |
| MEM (transient) | **172.0 ± 0.0** | 1.09 |

- **Zéro croissance**, toutes seeds, exactement 172 (comme 046/049). t=0.00.
- La mémoire fait *un peu moins bien* (1.09 vs 1.35) : la demande **mord** légèrement (sans l'indice
  persistant, les agents discriminent moins bien), mais ils ne **compensent pas** en grandissant.

## Le vrai obstacle (révélé en inspectant `add_node`)

`add_node` est le **split NEAT NEUTRE** : couper une connexion i→j (poids w), insérer un nœud
passe-plat (i→new = 1.0, new→j = w). Ce n'est PAS un nœud disruptif aléatoire → la croissance n'est
pas catastrophique. **Et pourtant l'architecture ne grandit jamais (046/049/058).**

> La non-linéarité (tanh + seuil sur le nouveau nœud) coûte un *chouïa* de fitness. Or le HoF est un
> **top-10 élitiste STRICT, sans protection** : la moindre structure novatrice, même quasi-neutre,
> est immédiatement battue par les 172-nœuds rodés → les enfants agrandis n'atteignent **jamais** le
> top-10 → **la croissance n'a jamais la chance de mûrir.** C'est *la* leçon de NEAT : il faut la
> **spéciation** pour PROTÉGER l'innovation le temps qu'elle s'optimise.

## L'unification (langage ⊕ architecture)

| Frontière | Novauté à faire émerger | Pourquoi ça échoue |
|---|---|---|
| Langage (054) | une convention référentielle faible | sélection (`life_score`) **aveugle** à elle |
| Architecture (058) | un nœud caché immature | sélection élitiste stricte la **bat** avant maturité |

> **Une sélection élitiste stricte par une fitness établie TUE la nouveauté — convention faible OU
> structure immature — avant qu'elle ne fasse ses preuves.** Les deux frontières de l'AGI sont
> bloquées par le **même** mur : *rien ne protège l'immature*. Ce n'est pas un défaut de demande,
> c'est un défaut de **dynamique de sélection**.

## Conséquence — le vrai lever (commun)

**Protéger la nouveauté/immaturité** le temps qu'elle mûrisse :
- **Spéciation** (NEAT) : faire concourir les agents agrandis *entre eux* d'abord, pas contre les
  champions rodés.
- **Niches / pool d'innovation** : un HoF séparé pour les lignées novatrices (architecture ou
  convention), réintégrées seulement une fois optimisées.
- Lien langage : la « sélection alignée » (055-057) tentait ça pour la convention mais échouait sur
  une *mesure* par-agent bruitée ; la spéciation est une approche *structurelle* plutôt que par
  récompense.

## Statut

- `transient_apex` : seam construit (off par défaut), 137 tests verts. La demande de mémoire *mord*
  (perf ↓) mais 1 bit ne sature pas — et de toute façon la croissance n'est pas *protégée*.
- **NAS re-cadré** : l'obstacle n'est pas la demande mais l'**absence de protection de l'innovation**
  (spéciation). C'est le prochain lever — et il vaut aussi pour le langage.

## Variables d'expérience

Spéciation (oui/non), pool d'innovation séparé, taille de la demande de mémoire (bits, délai), poids
de protection, durée.
