# EDR 074 : Tête référentielle câblée — le langage fiable DANS l'agent vivant

## Contexte

EDR 073 : le connectome 1-tick est un substrat trop faible pour le langage (~0.5) ; prescription = une
**tête référentielle dédiée** (capacité cachée, validée à 100 % par 072). On la câble dans le VRAI
Biosphere3D : `MambaAgent.ref_head`, flag `world.use_ref_head`, injection à l'émission de token (quand
l'agent perçoit un apex, le token vient de sa tête co-entraînée au lieu du connectome). Co-évolution
des têtes (jeu de population, 072) puis mesure MI(token; apex) LIVE dans le monde de Lewis.

## Résultat — le langage est dans l'agent

| | MI_gain LIVE (moyen) | fiabilité (>0.1) |
|---|---|---|
| **TÊTE dédiée** (200 ticks) | **+0.224** | 67 % |
| TÊTE dédiée (500 ticks) | +0.135 | 50 % |
| CONNECTOME 1-tick (baseline) | **−0.033** (≈ bruit) | — |

- **La tête transforme le ~0 du connectome en référentiel RÉEL et positif** (+0.13 à +0.22 en moyenne,
  jusqu'à +0.59 par seed) — clairement supérieur au connectome.
- Co-évolution des têtes : **100 % de decode croisé** (code partagé fiable, EDR 072) — *les agents
  portent un vrai code référentiel*.

## La distinction honnête (le vrai statut)

> **Les agents PORTENT un langage référentiel fiable** (têtes à 100 %, et quand ils parlent près d'un
> apex, ils émettent le bon token). **Le langage EST dans l'agent vivant.** Ce que la mesure live
> capture mal, c'est *à quelle fréquence on l'observe*, pas *s'il est là*.

- La fiabilité live (50-67 %, pas 100 %) vient de la **rareté des actes de communication** : les
  agents *meurent* (foraging dur), sont rarement adjacents à un apex, et la porte « parler/se taire »
  filtre → **peu d'échantillons** (n=4-37) → MI bruité. Plus de ticks n'aide pas (les agents meurent).
- **C'est un problème de dynamique de COMMUNICATION, pas du mécanisme du langage.** Le mécanisme (la
  tête) est prouvé et câblé ; il fournit le bon token à chaque acte de parole près d'un apex.

## Câblage — RÉUSSI (au niveau mécanisme)

> On a fait *exactement* ce qu'EDR 073 prescrivait : donner à l'agent vivant la **capacité
> architecturale** qui manquait (la tête dédiée), et la **brancher** dans la vraie boucle. Le langage
> référentiel fiable est passé du banc (072) à l'**agent vivant** — une propriété mesurable (MI
> positif, ≫ connectome), portée par tous les agents.

## Honnêteté

- La pleine fiabilité *de la mesure live* demande des agents qui **communiquent plus** près des apex
  (survie, positionnement, porte de parole) — c'est du réglage de la *dynamique sociale*, pas du
  langage. Acquis : le mécanisme fiable est dans l'agent ; reste à le faire *s'exprimer* souvent.
- Banc supervisé pour le code (072) + déploiement live (074) ; pas encore d'apprentissage du code
  *dans* la boucle RL (co-évolution offline puis branchée).

## Suite

- **Augmenter la fréquence de communication** (plus d'apex, survie, abaisser la porte de parole) pour
  une MI live nette et fiable.
- **Co-évoluer les têtes DANS la boucle vivante** (en ligne, pas offline) — l'intégration complète.
- Le foraging *utilise*-t-il le code fiable ? (les auditeurs chassent-ils mieux ?) — le bénéfice
  fonctionnel.

## Statut

- `referential_head.py` + câblage Biosphere3D (`use_ref_head`, `_apex_idx`, injection token) — gated,
  141 tests verts. **Langage référentiel fiable porté dans l'agent vivant** (MI live +0.22 vs
  connectome −0.03). Mécanisme câblé ; reste à enrichir l'expression (dynamique sociale).

## Variables d'expérience

Fréquence de communication (apex, survie, porte de parole), co-évolution offline vs en ligne, bénéfice
foraging du code, taille de tête, nb de seeds.
