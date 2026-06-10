# EDR 044 : Architecture de la boucle RSI (#8) — câblée, NON armée

## Objet

Cadrer **concrètement** la boucle d'auto-amélioration (#8) — périmètre, format de proposition,
point de branchement exact, sécurité — et poser le **harnais** complet, **sans appel LLM** (seam
explicitement désarmé). Le jour de l'armement : *une seule ligne* à changer.

## La boucle (5 temps) et où chaque brique de la session sert

```
DÉTECTER     superviseur réflexif : plateau/famine multi-ères         (EDR 036)
  -> PROPOSER    un `Proposer` (générateur de changement)             (EDR 044, ce doc)
  -> VALIDER     sandbox sécurisée : gate AST + exécution isolée       (EDR 035)
  -> MESURER     le changement améliore-t-il *vraiment* ? (falsifier)  (EDR 039/041)
  -> ENREGISTRER ontologie KuzuDB : Hypothesis/Fact                    (EDR 032/034)
```

## Décision (V18.25) — `src/metaprog/rsi_loop.py`

- **Le générateur est une abstraction `Proposer`**, pas un appel LLM en dur :
  - `TemplateProposer` — sûr, non-LLM, **le défaut** (catalogue d'activations) → fait tourner et
    tester TOUTE la boucle sans dépendance externe.
  - `LLMProposer` — **>>> LE SEAM DU #8, NON ARMÉ <<<** : lève `NotImplementedError`. La boucle
    retombe automatiquement sur le `TemplateProposer` (zéro risque).
- **Format de proposition** : `Proposal{kind, name, code, rationale}` — contrat stable que le LLM
  devra respecter.
- **Périmètre minimal** : `ALLOWED_KINDS = {"activation"}` (fonctions `f(x)->x` pures numpy). On
  donne au système **le pouce avant la main** ; élargir un cran à la fois (récompense → règle de
  monde → architecture/NAS).
- **`evaluate_proposal`** : périmètre + gate AST + test isolé. **N'installe pas** (effet de bord
  explicite au caller).
- **`rsi_step(context, proposer, graph)`** : PROPOSER → VALIDER → ENREGISTRER (ontologie).

## Point de branchement EXACT (pour armer plus tard)

Dans `supervisor.analyze_metrics`, la détection de famine (réflexive, EDR 036) déclenche
aujourd'hui `generate_and_test_new_activation` (gabarit). **Armer le #8 = router ce point par
`rsi_step(context, proposer=LLMProposer())`** où `context = {"trend": <compute_trend>, "recent":
<propositions de l'ontologie>}`. Rien d'autre à changer : validation, repli, enregistrement sont
déjà en place.

## Sécurité — conditions d'armement (non négociables)

1. **Conteneur jetable** : l'AST gate (EDR 035) est la *digue* ; un LLM adversarial déterminé
   reste un risque → exécuter la boucle armée dans un conteneur isolé/éphémère.
2. **Périmètre borné** : commencer à `activation` seulement ; n'élargir `ALLOWED_KINDS` qu'après
   éprouvé.
3. **Falsification systématique** (EDR 039/041) : n'**installer** une proposition que si elle
   *améliore mesurablement* (multi-points/multi-métriques), pas si elle « compile ». Le LLM amplifie
   le bruit si on lui fait confiance sans mesurer.

## Statut

**NON ARMÉ.** Tout le harnais tourne avec le `TemplateProposer` (6 tests verts dont « le LLM lève
NotImplementedError »). La boucle est *prête* ; les mains de la graine ne sont pas encore ouvertes.

## Quand armer

À la prochaine **vraie impasse** qu'aucun levier doux ne franchit — candidates identifiées : le
**langage référentiel** (EDR 042/043) et l'**architecture/NAS** (axe C7, 0 EDR, EDR 034). Décision
utilisateur, délibérée.

## Variables d'expérience

`ALLOWED_KINDS` (périmètre), choix du Proposer, format/contenu du `context` fourni au LLM, critère
d'installation (seuil d'amélioration, multi-points).
