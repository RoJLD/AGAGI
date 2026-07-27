---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-089
type: EDR
title: "VOID structurel : la létalité (qu'exige 088) et la survie longue (qu'exige 083) sont INCOMPATIBLES"
status: legacy
gate: G3
---

# EDR 089 — VOID structurel : la létalité (qu'exige 088) et la survie longue (qu'exige 083) sont INCOMPATIBLES

## Contexte

Power EDR 083 sur le levier #1 qu'il diagnostique : la **survie longue**. 083 (R=4) : co-évoluer l'USAGE
du langage (auditeurs évoluent à écouter `in_hear`, non imposé) donnait FIABLE−BRUITÉ = +0.29 ± 0.65 SE
(sous 2 SE) — sur substrat **court** (survivants=0). Hypothèse pré-enregistrée : sur le sweet-spot
d'énergie (085), avec R≥8 apparié, la survie longue **déverrouille** l'effet. Design (pré-enreg
`docs/superpowers/specs/2026-06-15-EDR089-*`) : `tools/coevolve_use_long.py` (moteur 083 déparasité +
`Harness` + `exp_stats` + runner **multiprocess**), métrique Mammouths tués, **gate de validité : survie
médiane > 120 ticks**.

## Le verdict : VOID au gate — et la raison est structurelle

Le pilote (mp, R=3) sur le sweet-spot **échoue le gate** : survie médiane = **20 ticks** (≪ 120).
Diagnostic 1 (nourriture) : le Lewis `_setup3` fixe `target_prey_count = 4` (food-scarce). Correctif
`= 15` (le défaut, celui d'087) → re-gate : survie **37 ticks**. **Toujours VOID.**

> Le fix nourriture a aidé (20→37) mais n'a PAS passé le gate. **Le verrou n'est pas la famine — c'est le
> COMBAT.** Le monde de Lewis (`_setup3`) a **8 apex qui ripostent** (4 Leurre dmg 50 + 4 Ours dmg 30) :
> les champions HoF (évolués en *stoneage*, pas en Lewis) foncent dans les apex et meurent à ~37 ticks,
> quels que soient l'énergie et la nourriture.

## La tension structurelle (le finding)

> **Le substrat à survie LONGUE qu'083 réclame est INCOMPATIBLE avec la létalité que 088 EXIGE.**
>
> - **088** a montré que le contenu du langage ne paye que si la distinction est *décisionnellement
>   coûteuse* → il faut des **Leurres mortels** (sinon discriminer ne sert à rien).
> - **083/089** ont besoin que les agents **survivent assez longtemps** pour co-évoluer l'écoute/l'évitement.
>
> Ces deux exigences se **contredisent** : des Leurres mortels → survie courte → pas le temps d'évoluer
> l'évitement → l'usage du langage ne peut pas être sélectionné. **Chicken-and-egg** : il faut survivre
> pour évoluer l'évitement, et l'évitement pour survivre. Le bootstrap est cassé parce que le point de
> départ (champions stoneage) **n'évite pas** les Leurres.

C'est pourquoi 082/083 voyaient « survivants=0 » et pourquoi 087/088 (sur le même type de monde létal)
ne trouvaient pas le langage payant : **ce n'est pas un réglage d'énergie, c'est une contradiction de
demandes.** Le « débloquer la survie » (085/086) qui semblait acquis ne tient pas dès qu'on remet la
létalité que le langage référentiel exige.

## Ce que dit le contraste (sur substrat INVALIDE — pas la réponse)

Sur le substrat court (gate échoué), FIABLE−BRUITÉ(kills) = **−1.21 ± 0.62 SE** (FIABLE *pire*,
Wilcoxon p=0.18). **Non interprétable** (substrat VOID), mais cohérent avec « pas d'avantage » : sans
survie, écouter ne sert à rien (on meurt avant d'exploiter le signal). Le `net` (kills−leurre_hits) est
aussi négatif → FIABLE ne réduit pas non plus les coups de Leurre sur ce substrat.

## Le vrai levier (re-pointé) : un CURRICULUM de létalité

Pour casser le chicken-and-egg, il faut un **substrat survivable au départ** qui **durcit
progressivement** : létalité douce (peu/pas de Leurres mortels) → laisser l'évitement + l'usage du signal
co-évoluer → **monter** la létalité par paliers une fois l'avoidance acquise. C'est le design d'un
**curriculum** (Arc 5 / `CurriculumRunner` dormant, cf. roadmap Dev), pas un réglage d'un seul monde.
Tester « le langage paye » exige d'abord **fabriquer des agents qui survivent ET discriminent** — les
deux ne s'obtiennent pas d'un coup sur un monde figé.

## Honnêteté & méthode

- **VOID, pas un négatif sur l'hypothèse** : le gate (pré-enregistré comme condition de validité) a fait
  son travail — il a empêché de conclure sur un substrat où la prémisse (survie longue) est fausse.
- **Outillage qui a payé** : le **runner multiprocess** (construit cette session, `mp == seq` vérifié) a
  ramené le pilote de ~96 min à **~12 min** → le diagnostic (VOID → food → combat) a pu se faire en
  quelques itérations rapides. Sans ça, ce mur aurait coûté des heures.
- **Finding repro adjacent** : la biosphère injectait de la **mémoire ambiante** (KuzuDB non filtré par
  run) dans les obs → non-reproductibilité sous sessions parallèles ; corrigé ici (retriever stoppé avant
  la boucle) et noté comme dette core-engine (les EDR 083/087/088 sur le chemin non-clean sont à lire
  avec ce caveat). Voir aussi l'instabilité connectome (EDR 086 redux) qui ressurgit sous co-évolution
  longue (NaN `value_pred`, bénin pour la métrique `life_score` mais réel).

## Variables d'expérience

Létalité des apex (nombre/dégâts de Leurre/Ours) **× survie** (le couple bloquant), `target_prey_count`,
sweet-spot énergie (085), substrat de départ des champions (stoneage vs Lewis), **curriculum de létalité**
(le levier non testé). Provenance : `results/coevolve_use_long_189.json` (substrat court, VOID) ;
gate-check prey=15 → survie médiane 37. Outils : `tools/coevolve_use_long.py` (mp), `src/seed_ai/exp_stats.py`.
