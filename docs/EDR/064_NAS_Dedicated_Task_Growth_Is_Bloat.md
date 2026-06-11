# EDR 064 : Tâche-mémoire dédiée — la croissance d'architecture est du BLOAT (clôture NAS)

## Contexte

EDR 062 : le foraging ne sature pas le connectome. On sort du foraging et on construit un **banc
cognitif pur** (`tools/mem_nas.py`, auto-contenu : Genome + recurrent_forward + apply_mutations) :
**rappel parallèle de K bits après un délai** (la mémoire vit dans les nœuds cachés). A/B K=1 (trivial)
vs K=6 (sature ~3 nœuds cachés initiaux), spéciation ON, dims fixes I=O=8.

## Bug de driver attrapé (gain de méthode)

`apply_mutations(genome, config)` fait `genome = genome.clone()` et **renvoie le mutant** — j'ignorais
la valeur de retour (je mutais une copie jetée). Diagnostic : `add_node` direct grandit (19→20) mais
`apply_mutations` « ne grandissait pas » → la croissance était *masquée par mon driver*. Corrigé
(`child = apply_mutations(parent, mc)`), la croissance apparaît. **Sans le diagnostic, on concluait
« pas de croissance » à tort.**

## Résultat — le trivial bloate le plus

| | nodes (moy ± σ) | accuracy |
|---|---|---|
| K1 (trivial, 1 bit) | **35.5 ± 1.4** | **1.00** (parfait) |
| K6 (mémoire, 6 bits) | 26.2 ± 1.8 | 0.78 |

t=−8.88, d=−5.61 → **significatif, mais K1 (le trivial) grandit le PLUS.** L'inverse de l'hypothèse
« demande → croissance ».

**Suivi (le vrai test) — la capacité aide-t-elle ?** K6 croissance ON vs figé à 19 nœuds :

| K6 | accuracy |
|---|---|
| croissance (→26) | 0.783 |
| figé (19) | 0.774 |

→ **négligeable. Plus de nœuds n'aide PAS la tâche mémoire.**

## Conclusion robuste (046 → 064) — le NAS ne marche pas dans AGIseed

> **La croissance UTILE d'architecture n'a pas lieu**, ni en foraging ni sur une tâche cognitive
> dédiée. Doublement établi :
> 1. La croissance observée est du **BLOAT NEUTRE** : le trivial (K1, fitness saturée → dérive libre)
>    gonfle *plus* que le dur (K6, sélection serrée → add_node disruptif pénalisé). **La croissance est
>    portée par le MOU, pas par la demande.**
> 2. **Plus de capacité n'améliore pas** la tâche mémoire (0.78 à 19 ou 26 nœuds).

**Le goulot n'est pas la demande**, c'est mécanique : (a) `add_node` (split NEAT) est neutre-à-
disruptif, jamais immédiatement utile ; (b) la recherche par **mutation seule** (sans gradient) ne sait
pas *optimiser* un plus gros réseau pour exploiter la capacité.

## Le chemin d'un vrai NAS (hors portée actuelle)

- Un **opérateur de croissance UTILE** (pas un split aléatoire neutre) — ajouter de la structure qui
  *aide* dès l'insertion.
- De l'**apprentissage par GRADIENT** (BPTT) pour optimiser les grands réseaux récurrents — la
  mutation seule ne suffit pas (c'est *pourquoi* on utilise le gradient pour la mémoire).
- C'est un **changement fondamental** d'architecture évolutive ; candidat pour le #8 (proposer un
  opérateur de croissance / un schéma d'apprentissage), ou une refonte dédiée.

## Statut

- Banc `mem_nas` : seam réutilisable (auto-contenu, hors foraging). Spéciation + add_node *marchent*
  (croissance observable) — mais produisent du bloat, pas de l'utilité.
- **Arc NAS (046-064) : clos sur un négatif robuste.** Comme le langage (053-057), une frontière
  *honnêtement caractérisée* : ce qui manque est nommé (opérateur utile + gradient), pas vague.

## Variables d'expérience

Opérateur de croissance (split neutre vs utile), algorithme d'apprentissage (mutation vs gradient),
métrique (node-count confondu par le bloat ; mesurer l'utilité = accuracy vs capacité), tâche.
