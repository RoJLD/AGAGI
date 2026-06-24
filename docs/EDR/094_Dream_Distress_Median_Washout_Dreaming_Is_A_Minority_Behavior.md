# EDR 094 : Signature de détresse non-concluante — le dreaming est une conduite de minorité (lavage par la médiane)

## Contexte

EDR 093 a laissé un paradoxe : la population *portant* l'organe MCTS survit ~9% mieux (q2b 1.087)
mais les agents qui *rêvent* ont une compétence-survie plus basse (q2a −0.04). Phase 1-A
(corrélationnel, `tools/dream_distress_probe.py`, livré en subagent-driven + revue Opus) : les rêves
se concentrent-ils chez les agents proches de la mort (signature de détresse) ? Métrique = taux de
rêve médian (`dreams/age`) des court-vivants vs long-vivants (filtre âge ≥ 10), 5 seeds, sweet spot.

## Constat — verdict NEUTRE, mais artefact de mesure

| seed | rate_short | rate_long | delta | n_short | n_long |
|---|---|---|---|---|---|
| 0-4 | **0.000** | **0.000** | **0.000** | 35-54 | 38-61 |

VERDICT NEUTRE (median_delta 0.000, sign_p 1.0). Les groupes sont bien peuplés (filtre âge ≥ 10
fonctionne), mais **le taux de rêve médian est nul dans les DEUX groupes**.

## Cause-racine — lavage par la médiane

`rate_short = rate_long = 0.000` avec ~50 agents/groupe signifie que **l'agent médian ne rêve
jamais** (`median(total_dreams) = 0`). Le dreaming est une **conduite de MINORITÉ** (concentrée chez
quelques agents), pas une propriété de population. La médiane — robuste mais aveugle aux événements
rares — la rate intégralement. Le NEUTRE n'est donc PAS « pas de signal de détresse » : c'est
« l'instrument ne peut pas voir un signal porté par une minorité ».

> Même leçon qu'EDR 092 (la sonde mesurait les survivants, vides sous extinction) sous un autre
> visage : **le bon agrégat dépend de la rareté de l'événement**. Le dreaming probe (EDR 093)
> rapportait `total_dreams_seen` élevé MAIS étalé ; on aurait dû anticiper que la médiane le raterait.

## Signification — le paradoxe Q2a reframé

> Les « rêveurs qui font pire » (q2a < 0) sont une **petite minorité**, pas un effet de population.
> La question causale reste ouverte, mais elle se pose désormais sur une sous-population rare : un
> agrégat médian est le mauvais outil. Honnêteté : Phase 1-A est **non-concluante par construction**
> sur cet événement rare — ce n'est pas un échec scientifique, c'est une **limite d'instrument
> correctement diagnostiquée** (et le garde-fou « décomposition rapportée, jamais le label nu » l'a
> exposée : sans les `rate_short/long = 0.000` per-seed, on aurait pris le NEUTRE pour un résultat).

## Statut

- Phase 1-A livrée et opérationnelle, mais sa métrique (taux médian par longévité) est **aveugle à un
  dreaming rare**. NE PAS conclure « pas de détresse » à partir de ce NEUTRE.
- **Prochain** — deux voies, toutes deux indépendantes des médianes de population :
  1. **Métrique rare-event-aware** (cheap) : restreindre à la sous-population des **rêveurs**
     (`total_dreams>0`) et comparer leur âge à celui des non-rêveurs. NOTE : c'est exactement ce que
     `q2a` (EDR 093) calcule déjà — il valait **−0.04** (rêveurs marginalement pires), corrélationnel
     et sous-puissant. Donc l'analyse corrélationnelle a probablement atteint sa limite : refaire un
     agrégat observationnel ne tranchera pas cause vs corrélat.
  2. **Phase 2 — intervention causale** (`force_dream` gated, ON/OFF forcé à organe constant) :
     tranche cause vs corrélat sans dépendre d'aucun agrégat observationnel. C'est la voie définitive.

## Variables d'expérience

Agrégat (médiane vs moyenne vs sous-population rêveurs), métrique de longévité, seuil `age_floor`,
fenêtre temporelle du rêve (Phase 1-B), intervention causale `force_dream` (Phase 2).
