---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-049
type: EDR
title: "NAS sous demande — l'architecture ne grandit toujours pas (recette raffinée)"
status: legacy
gate: foundational
---

# EDR 049 : NAS sous demande — l'architecture ne grandit toujours pas (recette raffinée)

## Contexte

EDR 046 : dans le monde de base, forcer `add_node_rate` ne fait pas grandir l'architecture (HoF
figé à 172) — pas de demande. EDR 047 : la *demande* fait émerger le langage. On applique la même
recette au NAS : A/B `add_node_rate` (0.6 vs 0.2) dans le **monde exigeant Lewis-3**.

## Résultat — toujours figé

| add_node_rate | HoF nodes (moy / max) | proies_moy |
|---|---|---|
| 0.6 (forcé ×3) | **172 / 172** | 0.36 |
| 0.2 (défaut) | 172 / 172 | 0.30 |

> Même dans le monde Lewis-3, l'architecture **ne grandit pas**. Et `proies≈0.3` : la population
> **survit à peine** (les Leurres la déciment).

## Pourquoi — la recette raffinée

1. **Mauvaise demande.** Lewis-3 demande de la **perception + signalisation**, que 172 nœuds
   gèrent — pas de la **mémoire / computation** qui *saturerait* le connectome. Pour faire grandir
   l'architecture, il faut une tâche qui sature la **capacité représentationnelle/mémorielle**
   (horizon long, nombreux états simultanés à maintenir), pas seulement perceptivement plus riche.

2. **Pas de signal de sélection.** Avec `proies≈0.3`, la population s'effondre → l'évolution n'a
   presque rien à sélectionner → rien ne grandit (les champions à 172 restent, intacts).

> **Recette raffinée :** « la demande crée la capacité » exige que la demande **CIBLE** la capacité
> précise (référentielle pour le langage, **mémorielle/computationnelle** pour l'architecture) ET un
> monde **survivable** (sinon pas de sélection). Un « monde plus dur » générique ne suffit pas — le
> monde de Lewis a marché *pour le langage* car il ciblait *exactement* le besoin référentiel.

## Bilan des deux renforcements (047→049)

| Frontière | Demande créée | Résultat |
|---|---|---|
| Langage (047) | référentielle (2 réf., survivable) | ✅ émergence (faible : MI 0.033) |
| Langage+ (048) | 3 réf. | ❌ pas de lexique (silence ; altruisme du signal) |
| Architecture (049) | Lewis-3 (perception, non-survivable) | ❌ pas de croissance (mauvaise demande + collapse) |

**Une seule des quatre frontières a cédé — et faiblement.** Honnêteté : la recette est *vraie mais
exigeante* — concevoir la *bonne* demande ciblée + survivable est le vrai travail.

## Suites (ciblées)

- **NAS** : une tâche-MÉMOIRE survivable (ex. se souvenir du type d'apex après s'en être éloigné,
  pour le signaler/agir plus tard) → saturer le connectome récurrent.
- **Langage** : incitation du locuteur alignée + affordances distinctes (EDR 048).
- **#8** : exactement ce qu'un générateur devrait *itérer* — proposer des demandes ciblées, mesurer,
  raffiner. On vient de faire trois itérations à la main ; le LLM en ferait des centaines.

## Variables d'expérience

Type de demande (perception vs mémoire vs computation), survivabilité du monde, `add_node_rate`,
horizon temporel de la tâche.
