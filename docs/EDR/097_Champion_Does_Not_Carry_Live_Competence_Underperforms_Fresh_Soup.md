---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-097
type: EDR
title: "Le champion HoF ne porte PAS la compétence vivante — il fait pire que la soupe fraîche"
status: legacy
gate: G1
---

# EDR 097 : Le champion HoF ne porte PAS la compétence vivante — il fait pire que la soupe fraîche

## Contexte

Réparation métrique couche-2 (EDR 096, PR #50) + câblage de la récolte (`mammoth_kills`/
`spears_crafted` dans `agent_stats`, sans quoi la métrique réparée était inerte). Premier run sur la
dimension enfin VIVANTE : expérience B (champion-vs-frais), `tools/target_competence_probe.py`, cible
stoneage, sweet spot (0.25/3.0), 8 ères, 40 agents, 300 ticks. Question : les clones du champion HoF
expriment-ils plus de compétence apex/outil que la soupe fraîche ?

## Constat — la métrique est VIVANTE, et le champion sous-performe

| bras | median_C | frac_apex (moy) | frac_tool (moy) | mammouth (moy/ère) |
|---|---|---|---|---|
| **tabula** (soupe fraîche) | **0.313** | **0.211** | 0.016 | 29.0 |
| **champion** (clones HoF #1) | **0.256** | **0.162** | 0.014 | 18.1 |

- **Métrique vivante confirmée sur données réelles** : les deux bras à ~0.26-0.31 (VERDICT=SIGNAL,
  seuil 0.15), TRÈS au-dessus de l'ancien plancher mort (~0.07). Le câblage fonctionne ; `frac_apex` est
  le moteur (cohérent avec EDR 096 : apex 0.217).
- **Transfert NÉGATIF** : champion/tabula = **0.816**, `Δapex = −0.049`. Le champion ne bat tabula que
  **1 ère sur 8** (apparié par seed) → test de signe `sign_p ≈ 0.07` (< 0.1). Le champion HoF ne porte
  PAS une compétence apex/outil transférable ; une population fraîche diverse fait **mieux**.

## Caveat — monoculture vs diversité (confond non disjoint)

Le bras champion est une **monoculture** : UN génome (HoF #1) cloné ×40. Le bras tabula est une
population **diverse** (soupe fraîche). Or l'apex-prédation est COOPÉRATIVE (chasse en pack, dégâts
cumulés, EDR 096). Le déficit du champion peut donc venir de DEUX causes non séparées par cette sonde :
(a) le génome champion manque individuellement de compétence apex, OU (b) une monoculture de 40 clones
identiques coordonne MOINS bien le pack qu'une population diverse (pas de différenciation de rôles, tous
le même comportement). La sonde ne tranche pas. Mais le verdict opérationnel tient : **le champion TEL
QUE DÉPLOYÉ (cloné) ne transfère aucun avantage apex** — au contraire.

## Signification

> Le HoF n'est pas un réservoir de compétence vivante transférable. Cohérent avec EDR 090 (les
> champions stoneage ne transfèrent pas la survie à Lewis) et la méta-leçon parallèle
> [[nas-bottleneck-is-substrate-not-search]] (substrat pauvre → la sélection ne produit pas de
> compétence riche). Ici, le champion ne porte même pas un avantage sur SON propre monde, mesuré sur
> le signal vivant.

Anti-théâtre : sur l'ancienne métrique morte (autel 0.6 ≡ 0), les deux bras auraient été au plancher →
ce signal négatif (et la révélation que la métrique vivante MARCHE) serait resté invisible. La
réparation + le câblage étaient la condition de mesurabilité.

## Statut

- B livré. **Verdict : champion < frais** sur la compétence vivante (transfert négatif, sign_p~0.07),
  avec le caveat monoculture-vs-diversité.
- **Prochain** :
  1. **Expérience A** (transfert curriculum, en cours) : l'ÉCHAFAUDAGE développemental (≠ un champion
     cloné) construit-il plus de compétence vivante que tabula à budget égal ? C'est le vrai test du
     curriculum (et il n'a pas le confond monoculture : les deux bras partent de soupe fraîche).
  2. **Disjoindre le confond** (barreau suivant, si pertinent) : bras « champion dilué » (quelques
     clones dans une soupe diverse) vs monoculture pure → isole l'effet diversité de l'effet génome.

## Variables d'expérience

Composition du bras champion (monoculture vs dilution), nombre de champions distincts (top-K HoF vs #1
seul), `coop_reward` (ablation → l'apex coop disparaît ?), K ères / seeds (puissance), métrique
(median_C vs frac_apex brut).
