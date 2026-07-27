---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-028
type: EDR
title: "Persistance — sevrer le crit, faire émerger la coopération robuste"
status: legacy
gate: G2
---

# EDR 028 : Persistance — sevrer le crit, faire émerger la coopération robuste

## Contexte — fiabiliser la Vague 0quater

L'EDR 027 a fait émerger la chaîne moyens→fins bout à bout, mais **intermittente** et — soupçon —
dépendante du **coup critique chanceux** (EDR 022). Question de la persistance : si on **sèvre**
le crit (anneal → 0), la chasse au Mammouth tient-elle via une stratégie *robuste* ?

> *Bug de cadencement corrigé au passage* : dans les curricula, chaque ère recréait un monde avec
> `current_era=1` → le crit valait `0.6·anneal(1,·) ≈ 0.57` **en permanence**, jamais sevré. On
> pilote désormais le crit (et les scaffolds) par une **ère globale**.

## Test 1 — la chasse à l'apex est CRIT-DÉPENDANTE

Rareté 6 fixe, crit annelé 0.6→0 sur 20 ères puis 15 ères sevrées :

| Phase | Mammouths/ère |
|---|---|
| AVEC crit | **0.70** |
| SEVRÉ (crit=0) | **0.20** (−71 %) |

> Les **crafts persistent** (~2/ère) mais les lances ne tuent plus l'apex sans crit. **La
> coopération n'émerge PAS spontanément** — c'est un problème de *coordination* (faire converger 2
> agents sur le même Mammouth) que rien n'incitait. L'hypothèse « coop prendra le relais » réfutée.

## Décision (V18.15) — récompense de GROUPE sur l'apex

Le Mammouth (`hp ≥ 50`) nourrit **tout le pack qui l'a attaqué** (chaque attaquant vivant reçoit
la pleine récompense), au lieu du seul tueur. La coopération est déjà *avantageuse*
mécaniquement (2 lances one-shotent, la riposte ne frappe que le plus proche) ; cette prime crée
la pression **sélective** pour rejoindre les chasses → la coordination s'installe.

- `attacked_prey["attackers"]` (set) enregistré à chaque coup ; à la mort de l'apex, distribution
  à tous les attaquants vivants. Petit gibier : inchangé (tueur seul).

## Test 2 — la coopération PERSISTE le sevrage

| | crit seul | **+ récompense de groupe** |
|---|---|---|
| AVEC crit | 0.70 | 0.70 |
| **SEVRÉ (crit=0)** | 0.20 (s'effondre) | **0.67 (persiste)** |

> **À crit=0, la chasse à l'apex tient (0.67 ≈ 0.70).** Le crit peut être **entièrement sevré** ;
> la **coopération prend le relais**. La béquille de la chance cède à une vraie stratégie sociale.

## Conclusion

La persistance est résolue : **la coopération est le relais robuste, et elle émerge dès qu'on
l'incite** (la prime de groupe). Le projet tient désormais une chaîne moyens→fins *non
crit-dépendante* — pont direct vers l'**Arc 5 (Tribu)**. 106 tests verts.

## Limites & suites

- L'apex-hunting est **robuste mais pas encore dominant** : à rareté 6, `proies_moy ≈ 0.6` (la
  chaîne tient mais ne nourrit pas encore toute la population). Augmenter la fréquence (vies plus
  longues, sélection plus longue, ramper `craft_level` conjointement).
- **Stun (jet visé)** reste un relais solo possible (skill fin, non forçable) — exploration future.
- Prime de groupe à **anneler** elle aussi à terme (qu'elle n'entretienne pas un acquis).

## Variables d'expérience

Part de récompense par attaquant (pleine vs partagée), seuil apex, `crit_eras`, durée de vie.
