---
id: ADR-004
type: ADR
title: Fourche strategique P3.7 -- AGAGI devient un HARNAIS (demande GENEREE + mesure) pointe sur un apprenant a poids que robla possede ; le connectome cesse d'etre le sujet
status: accepted
gate: foundational
motivates: []
triggers: []
tests: []
adopts: [REF-DEMAND-MARKER, REF-EXPERIMENT-PREFLIGHT, REF-POET-2019, REF-ELM-2022]
---
# ADR-004 — La fourche stratégique : « le monde EXIGE » vs « la demande est CONÇUE »

**Date** : 2026-09-16. **Décideur** : robla, sur sept questions posées le 2026-09-15/16. **Ferme** : P3.7
(`docs/roadmap/PRIORITES_ET_DETTES.md`, bloc « 🧭 2026-09-15 »). **Spec** :
`docs/superpowers/specs/2026-09-16-harness-contracts-design.md`.

## Contexte (mesuré, pas raconté)

Après 293 records et 3,5 mois, le graphe dit : la survie seule n'a aucun gradient cognitif ([[EDR-EVO-016]] :
0/12 lecteurs même quand lire double la vie) ; le crédit in-world publié EFFACE un bassin pré-formé
([[EDR-S2-CREDIT-RETENTION]] : 36 → 8, 12/12) et le mur est le MÉCANISME de crédit, pas la récompense (P4.8) ;
cinq leviers de sélection agnostiques réfutés ; **proxy 9 / in-world 0** inchangé depuis le 2026-07-10. Les
résultats POSITIFS pointent tous vers « a priori pré-formé + gradient » (loi warm-start sur 6 fils, bilinéaire,
DAgger). Débit : 26 commits science contre 78 méthodo depuis le 09-01 ; zéro preprint.

North-star déclaré par robla : « donner au modèle un jeu de logique, un nouveau monde, un WSL, un corps robot —
et qu'il apprenne tout seul ».

## Décision

**Branche (b) avec (a) dedans.** AGAGI devient un **harnais** qui (1) GÉNÈRE des environnements exigeants et des
architectures, (2) MESURE si un apprenant a réellement appris. Concrètement :

1. **Sujet** : un modèle **à poids** que robla possède. AGAGI cherche aussi les **architectures** gagnantes.
2. **Espace d'architectures ouvert** (actor-critic torch + BPTT, Dreamer, transformer, connectome, architectures
   composées avec un LLM) sous une règle d'entrée : **une famille n'entre qu'avec son propre contrôle positif**
   (classe E2 sinon). Premier entrant : le connectome torch bilinéaire (contrôle positif d'ACQUISITION connu :
   0,932 vs 0,271 sur `(q+key)%K`, n=12).
3. **Première famille d'environnements** : jeux de logique **vérifiables**, générés par le proposeur ; les tâches
   proxy existantes portées d'abord. Stoneage devient UN environnement parmi d'autres.
4. **Deux fils** : la lignée S2/stoneage continue (bail `kuzu`) ; le harnais est CPU pur, sans bail.
5. **Proposeur** : Claude Code (`claude -p`, contrat `llm_fn(str) -> str`) ; code généré sous `secure_sandbox` +
   **revue humaine** avant d'entrer dans la famille. Pas de conteneur EDR 044 en v1 ; Learners générés hors v1.
6. **Publication** : preprint MÉTHODO maintenant (cliquet de calibration, pré-inscription, mutation des portes,
   registre d'erreurs, à partir des records existants) ; résultats du harnais dans un second papier.
7. **Critère à 3 mois** : UN record à trois conditions — (i) une tâche GÉNÉRÉE exige X (ablation within-subject
   hors bande de bruit) ; (ii) ≥ 1 architecture ACQUIERT X à dose publiée, au-dessus de la référence lr=0
   appariée ET du plafond de l'incapable, n ≥ 12 ; (iii) l'ablation d'UNE pièce ANNULE l'acquisition.
   **Sans (ii) à 3 mois, cet ADR est amendé et P3.7 rouverte.**

Le registre de pièces (spec §2.2) porte la question de robla « artificiel ↔ organique » : chaque pièce a sa forme
artificielle, son analogue biologique avec solidité, sa variante « sans », et une prédiction de lésion (maillon
`inferred`). Une pièce n'est candidate « du puzzle » que si elle est nécessaire dans **≥ 2 familles**.

## Ce que cette décision RÉFUTE ou SUSPEND

- La thèse fondatrice « le bon n'est pas dit mais trouvé, si le monde l'EXIGE » n'est **pas** abandonnée : elle
  passe de « conçue à la main » à « GÉNÉRÉE et mesurée ». Si aucune des N premières tâches générées n'exige rien
  hors bande de bruit, ce sera gravé comme résultat (branche scellée), pas découvert.
- Le connectome stoneage **cesse d'être le sujet** de la cognition ; il reste une famille de l'espace (avec son
  contrôle positif) et le fil S2 continue ses propres questions.
- Les branches écartées : (c) statu quo — valeur attendue bornée par les 293 records (« pourquoi REINFORCE sans
  BPTT n'apprend pas », déjà connu du champ).

## Conséquences

- Nouveaux instruments (tous calibrés à réponse connue avant tout torch) : `assert_task_contract`,
  `assert_learner_contract`, `harness_verdict_lecture`, `measure_noise_floor`, `measure_ablated_bayes_ceiling`,
  `run_harness_cell` — dans `src/seed_ai/` et `tools/harness/` (périmètre des quatre cliquets, vérifié).
- P2.66 se ferme par `claude_code_llm_fn` ; P4.10 est re-spécifié : la génération vit dans
  `tools/harness/propose.py` (modules Task numpy-only), pas dans `rsi_loop.ALLOWED_KINDS`.
- Un fait corrigé en conception : le plafond gelé du substrat plain (34/36 = 0,944,
  `tools/plain_substrate_ceiling.py:155`) dépasse le bilinéaire (0,932) — la nécessité de la pièce `bilinear` ne
  peut être qu'une nécessité d'**ACQUISITION à dose**, jamais de représentation ; le premier verdict NECESSARY
  attendu vient de `recurrent_state` (cellule B du spec).
- Dettes ouvertes par cette décision, à inscrire au backlog avec preuve : sham bilinéaire apparié ; Task à shift
  (hypothèse neuromodulée) ; sandbox torch pour Learners générés (EDR 044) ; `count_learning_events` aveugle à
  `imitate_episode_bptt`.
