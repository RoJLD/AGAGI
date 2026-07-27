---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-051
type: EDR
title: "Le #8 sur les demandes de monde — la boucle marche, la mesure est le goulot"
status: legacy
gate: foundational
---

# EDR 051 : Le #8 sur les demandes de monde — la boucle marche, la mesure est le goulot

## Contexte

EDR 046/050 : le vrai levier d'émergence est la **demande de monde**, et concevoir la bonne est une
**recherche** (4 designs manuels, 3+ échecs). On étend le #8 au périmètre `world_demand` et on
construit la boucle qui **propose + mesure + classe** les demandes — pour transformer notre recherche
manuelle en itération mesurée.

## Construit (rsi_loop.py)

- `ALLOWED_KINDS += "world_demand"` ; `Proposal.params` (attrs à poser sur le monde).
- `WorldDemandProposer` : **catalogue dirigé** des demandes conçues à la main (047 succès, 045/050
  échecs). Le `LLMProposer` s'y substituerait pour en *inventer*.
- `rsi_demand_step(context, measure_fn, ...)` : PROPOSER → MESURER (via callback injecté : applique
  la demande, évolue, renvoie un score) → ENREGISTRER (ontologie). **rsi_loop reste agnostique du
  monde** (la mesure est injectée). 8 tests verts.

## Démo (mode dirigé, sans LLM live)

La boucle propose les 3 demandes, en évolue chacune (12 ères, même départ) et mesure
`I(token ; Mammouth/Leurre)` :

| Demande | MI mesuré |
|---|---|
| speaker_reciprocity (050) | **0.0157** ← retenue |
| referential_pressure (045) | 0.0081 |
| lewis_2ref (047) | 0.0030 |

> La boucle **n'a pas** re-découvert `lewis_2ref` (047). Elle a classé par le **bruit**.

## Pourquoi — et la vraie leçon

- **12 ères/demande = sous-puissant.** Tous les MI sont tombés à 0.003–0.016, *sous* les 0.033 de
  l'EDR 047 (qui a besoin de ~24 ères pour s'exprimer). `lewis_2ref` est arrivé *dernier* faute de
  temps pour exprimer son signal. Le classement n'a mesuré que du bruit.

> **Un générateur itératif ne vaut QUE ce que vaut sa mesure.** Proposer 1000 demandes est inutile
> si chaque évaluation est trop bruitée pour les classer — la boucle **optimiserait le bruit**. Le
> goulot du #8 n'est PAS le générateur (facile) mais le **coût + la puissance de chaque évaluation**
> (assez d'ères + de seeds). Armer le #8 sans évaluations puissantes = armer une machine à
> sur-apprendre le bruit.

## Statut

- ✅ #8 `world_demand` **construit, testé, démontré** mécaniquement.
- ⚠️ La démo a exposé le **vrai chantier** : un **harnais d'évaluation PUISSANT** (multi-ères +
  multi-seeds + dénoising) — sinon le classement est du bruit.
- 🔒 `LLMProposer` toujours non armé. Avant de l'armer : d'abord le harnais d'évaluation puissant,
  *puis* le conteneur (EDR 044).

## Conséquence (recadre la priorité du #8)

Le chemin vers un #8 utile n'est pas « brancher le LLM » mais, dans l'ordre :
1. **Harnais d'évaluation puissant** (la contrainte démontrée ici) ;
2. demandes *ciblées + survivables* au catalogue (EDR 049) ;
3. *ensuite* le LLM dans un conteneur, qui propose + lit les échecs via l'ontologie.

C'est la discipline de mesure (EDR 039/041) érigée en **architecture** : la boucle est aussi fiable
que sa mesure, pas plus.

## Variables d'expérience

ères/seeds par évaluation (puissance), métrique cible, catalogue de demandes, dénoising
(permutation/baseline), `WorldDemandProposer`.
