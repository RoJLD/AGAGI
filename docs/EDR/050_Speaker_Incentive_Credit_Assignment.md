---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-050
type: EDR
title: "Incitation du locuteur — échec par crédit temporel (4ᵉ design manqué = l'argument #8)"
status: legacy
gate: G3
---

# EDR 050 : Incitation du locuteur — échec par crédit temporel (4ᵉ design manqué = l'argument #8)

## Contexte

EDR 048 : le langage (047) reste faible car le **silence** domine (altruisme du signal). Remède
classique : la **réciprocité** — `world.speaker_reward` prime un agent qui a annoncé (signalé
adjacent) un Mammouth *effectivement tué par le pack*. A/B (ON 5.0 vs OFF), monde de Lewis 2 réf.

## Résultat — pire, pas mieux

| | silence (près apex) | MI(token;Mammouth/Leurre) | baseline |
|---|---|---|---|
| ON (réciprocité) | **89 %** | 0.0012 | 0.0021 |
| OFF | 69 % | 0.0076 | 0.0034 |

> La prime a **augmenté** le silence (69→89 %) et **baissé** le référentiel. L'inverse de l'attendu.

## Pourquoi — bug de crédit temporel (+ découplage)

1. **Crédit temporel.** La prime arrive **au tick de la mise à mort** ; le signalement a eu lieu
   *bien des ticks plus tôt*. Le policy gradient (TD, crédit d'action) crédite donc l'action *du tick
   du kill* (attaquer/rester) — **pas l'action de signaler**. On renforce la mauvaise action. Pour
   récompenser le signal, il faudrait la prime *au tick du signal* (ou des traces d'éligibilité).
2. **Découplage.** « Adjacent à un Mammouth qui meurt + émet un token » ≠ « signal causalement
   utile ». Le kill vient du *pack* (attaquants cumulés), pas du signal → la prime récompense
   *être-au-kill*, pas *signaler-utilement* + injecte du bruit de fitness (5.0) qui dégrade la
   sélection.

## La vraie leçon — le pattern des designs manqués

| EDR | Mécanisme conçu à la main | Défaut (trouvé *par la mesure*) |
|---|---|---|
| 045 | pression de convergence | gameable (token constant) |
| 048 | 3 référents | silence (altruisme) + dilution d'affordance |
| 049 | monde Lewis-3 pour le NAS | mauvaise demande + collapse |
| **050** | réciprocité du locuteur | **crédit temporel** (crédite le kill, pas le signal) |

> **4 designs manuels, 3+ échecs — chacun par un défaut subtil trouvé *après coup*.** Le seul succès
> net (047) était la demande la *plus simple/propre*. **Concevoir le bon mécanisme est un problème de
> RECHERCHE difficile** : une seule tentative à la main rate presque toujours.

## Conséquence — c'est l'argument empirique du #8

- **Itérer** : un générateur (LLM) qui propose des *centaines* de designs et **mesure** chacun
  battrait le taux de réussite misérable de la conception à la main. Nos échecs ne sont pas un
  problème — ils *démontrent* pourquoi il faut un itérateur.
- **Mesurer** : on a attrapé *chaque* défaut par la mesure (jamais supposé correct). C'est la
  discipline non négociable (EDR 039/041) — surtout pour un générateur automatique.

## Suite (la bonne version, si on y revient à la main)

- Prime **au tick du signal** conditionnée à un recrutement dans les k ticks suivants (trace
  d'éligibilité), pas à la mise à mort différée.
- Crédit **causal** (un auditeur s'est rapproché *après* le signal), pas la simple co-présence.
- Mais : c'est exactement le genre d'itération que le **#8** devrait porter — pas une 5ᵉ tentative
  manuelle.

## Variables d'expérience

Timing de la prime (signal vs kill), trace d'éligibilité, crédit causal, magnitude, `speaker_reward`.
