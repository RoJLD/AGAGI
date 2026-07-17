# S2 within-subject perception-ablation — FINDING : l'edge de survie du champion n'est PAS causalement perceptif

**Statut : instrument livré (bras d'ablation-perception within-subject câblé dans `s2_demand`) + run décisif rendu.**
Le verdict S2 « le monde EXIGE l'intelligence », robuste en survie between-subject, est **désambiguïsé causalement** :
within-subject, **la perception n'est pas le levier de survie du champion**. Finding NÉGATIF décisif — le marqueur
between-subject faux-positive pour la demande de PERCEPTION, exactement comme S2-001 le prédisait, désormais confirmé
in-world sur la biosphère réelle.

## La question

Le fil S2 avait établi **EXIGE** BETWEEN-subject (champion HoF bat les baselines en survie 3.4–4.7×, EDR 124). Mais
S2-001 (`world_demand_marker_probe.py`) avait montré, sur mondes à vérité-terrain, que « un survivant compétent existe »
FAUX-POSITIVE : le champion peut gagner par un autre facteur (corps/génome) que la capacité testée. Le témoin CAUSAL sûr
= **ablation WITHIN-subject** du MÊME champion. Cet arc câble ce témoin dans le benchmark réel.

## L'instrument (livré, PR)

- `ObsAblatedMambaBatchModel` (`src/agents/ablation_models.py`) : enveloppe le VRAI moteur champion et **row-shuffle
  l'obs par tick** (agent i reçoit l'obs réelle d'un autre → décorrèle perception↔état propre, distribution préservée).
- Condition `champion_obs_ablated` dans `s2_demand` + `verdict_within_subject` (`s2_stats`) : champion vs champion_ablé
  (l'ablation effondre-t-elle la survie ?) corroboré par ablé vs random. Verdicts gelés {NON-CAUSAL, CAUSAL-PARTIEL,
  CAUSAL-FULL, CAUSAL-CRITIQUE}. Le verdict est signe-aware (revue finale) : ablé PIRE que random = CAUSAL-CRITIQUE
  (perception essentielle), pas un faux CAUSAL-PARTIEL.

## Le run décisif (stoneage, K=12, max_ticks=200, 20 agents, RAG-off `_disable_kuzu`, seed 2026)

| | verdict | Cliff δ | p |
|---|---|---|---|
| **between** (champion vs random_action) | **EXIGE** | +0.92 | 0.0025 (ratio survie 3.4–4.2×) |
| **within** champion vs champion_ablé | **NON-CAUSAL** | +0.066 | 0.131 (non-signif.) |
| corroborant : champion_ablé vs random | — | **+0.891** | 0.0025 |

Ablater la perception du champion **n'effondre PAS** sa survie (δ=0.066, p=0.13) — et le champion ablé **écrase toujours**
le random (δ=0.891, ~4×, comme le champion intact). L'avantage de survie du champion est donc **perception-INDÉPENDANT**.

## Validation de l'ablation (ce N'EST PAS un artefact d'ablation faible)

Caveat de la revue finale : un NON-CAUSAL serait artefactuel si le row-shuffle ne mordait pas (obs homogènes entre
agents). Mesuré sur un rollout stoneage du champion :
- **shuffle rel-distance = 0.674** (0 = identité, ~1.4 = totalement décorrélé) → l'obs vue après shuffle diffère de
  ~67 % de sa norme : **vraie intervention**.
- obs inter-agent std = 0.117 ; frac obs non-nulle = 0.29 → l'obs est **informative et diverse**, pas homogène.

L'ablation change réellement la perception ; la survie n'y répond pas → **NON-CAUSAL genuine**.

## Interprétation

**Le monde EXIGE une compétence de survie — mais cette compétence n'est PAS la perception (ici).** L'edge 4× du
champion vient d'un facteur perception-indépendant : corps/métabolisme/politique réflexe. Cohérent avec le régime
DÉFAUT (dur) où la cohorte s'effondre vite (20→3 agents en 35 ticks) : l'endurance métabolique prime sur la chasse
guidée par l'obs. Le marqueur between-subject « champion bat baselines » mesurait donc une compétence de survie RÉELLE,
mais l'attribuait à tort à la PERCEPTION — le faux-positif exact de S2-001, confirmé in-world.

## Extension régime SWEET (0.25/3.0) — le finding est RÉGIME-ROBUSTE

Rejoué au sweet-spot (base_metabolism=0.25, forage_payoff=3.0, K=12, RAG-off) pour fermer le caveat d'effet-plancher :

| Régime | survie médiane (champ/ablé/random) | BETWEEN champ vs random | WITHIN |
|---|---|---|---|
| DÉFAUT (dur) | ~4× le random | **EXIGE** (δ=0.92, p=0.0025) | **NON-CAUSAL** (δ=0.066) |
| SWEET (0.25/3.0) | 39 / 36 / 38.5 (≈ égaux) | **PAS d'edge** (δ=−0.043, p=0.224) | **NON-CAUSAL** (δ=0.055) |

Les deux régimes convergent : **la perception n'est JAMAIS le levier causal de survie du champion**. En dur, l'edge 4×
existe mais est perception-indépendant (métabolique/corporel). En sweet, l'edge DISPARAÎT (champion ≈ random ≈ ablé ~38
ticks) : quand le forage est facile, l'intelligence ne discrimine pas la survie. **Le NON-CAUSAL du régime dur n'est
donc PAS un artefact d'effet-plancher — il tient à travers les régimes.** Le caveat régime est FERMÉ : le verdict
between-subject EXIGE faux-positive robustement pour la demande de PERCEPTION.

## Caveats restants (consignés)

1. **Cohorte survivante** : mesuré sur les agents vivants (dernier quart), appariement par ère.
2. **Sous-question ouverte** : le diagnostic n'a pas pu mesurer la sensibilité-action directement (le monde construit
   le batch-model en interne depuis des dicts d'agents, `env.agents` ≠ objets `.genome`). Reste ouvert : le champion
   IGNORE-t-il l'obs, ou l'utilise-t-il sans que ça compte pour la survie ? Les deux → NON-CAUSAL ; distinction = refinement.

## Convergence

Confirme in-world l'instrument [[within-subject-demand-marker]] (le témoin causal = ablation within-subject, pas
between-subject) et son application S2-001. Recoupe [[lewis-energy-economy-wall]] (« le mur EST la politique/substrat »),
le fil [[s2-world-demand-thread]] (EXIGE en survie mais pas en life_score ; ici : EXIGE en survie mais pas causalement
en perception), et la thèse substrat/crédit. Extension naturelle : rejouer l'arm au régime sweet + trancher la
sous-question (obs-ignorée vs obs-inutile) — non retenu ici (choix robla « consigner le finding »).
