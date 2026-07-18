---
id: EDR-156
type: EDR
title: Transfert ZERO-SHOT cross-world POSITIF (famine<->stoneage, 2-7x tabula, 12/12 seeds) — mais c'est le noyau de survie PARTAGE qui transfere, pas une competence world-specifique (qui n'existe pas)
status: accepted
gate: G1
tests: [SDR-G1]
verdict: TRANSFERE_NOYAU_PARTAGE
---

# EDR 129 : Transfert zéro-shot cross-world — POSITIF pour le noyau de survie partagé

## Contexte

`SDR-G1` (north-star) : « un champion évolué dans le monde A atteint la compétence dans le monde B
jamais vu mieux que tabula-rasa ». **EDR-116** avait mesuré ce transfert **NEUTRE** — mais sur une
facette différente : le transfert **développemental à compute égal** (les deux bras *ré-évoluent* T ères
sur la cible ; le curriculum accélère-t-il l'apprentissage ?). Il restait la facette la plus littérale du
north-star : la **généralisation ZÉRO-SHOT** — lâcher un champion fini, sans aucune ré-évolution, dans un
monde jamais vu. EDR-118/126 ont livré le 2ᵉ monde genuinement distinct (FamineWorld) et un champion
famine compétent : le zéro-shot est enfin mesurable, dans les DEUX sens.

## Méthode

Sonde `tools/cross_world_transfer.py` (TDD, 5/5 : 4 purs + 1 smoke intégration). Primitive : cohorte fixe
(`benchmark_mode`, nuit OFF, scaffolds OFF, `memory_retriever` neutralisé) au **sweet-spot métabolique**
(EDR 085 : `base_metabolism=0.25`, `forage_payoff=3.0`). **Ce détail est décisif** : sans le sweet-spot,
la survie est au plancher létal, insensible au monde ET au génome — un contrôle a montré tabula = champion
= 15-17 ticks partout, et tout ratio de transfert vaudrait ~1 **par artefact**. Au sweet-spot, la survie
redevient sensible au génome (condition nécessaire, codifiée en test).

KPI `transfer_ratio` = survie(champ A dans B) / survie(tabula-rasa dans B), **apparié par seed d'éval**
(K=12 seeds, 12 agents, 300 ticks), test de signe binomial. Tabula-rasa = `MambaAgent` à init aléatoire
(même setup perceptuel que le champion, y compris le même mismatch de dims). 3 champions famine (HoF
dédiés seeds 42/43/44, EDR-155) → stoneage ; champion stoneage global (md5 `844ed69`) → famine.

**Note dims (honnêteté)** : famine=59/108, stoneage=64/126 (contrat I/O partiel : stoneage ajoute 5 obs /
18 actions d'affordances propres). Le mismatch est absorbé par le padding dynamique du batch model : un
champion famine (59) dans stoneage ne *perçoit même pas* les 5 obs stoneage-spécifiques → il ne peut
transférer que le **noyau de forage partagé**. C'est un handicap perceptuel pour le champion, pas un
avantage → le résultat positif est mesuré MALGRÉ lui.

## Constat — TRANSFERE dans les 4 bras (12/12 seeds, sign_p plancher)

| source → cible | verdict | ratio médian | n_fav | sign_p | survie champ | survie tabula |
|---|---|---|---|---|---|---|
| famine s42 → stoneage | **TRANSFERE** | 4.57 | 12/12 | 0.0005 | 72.2 | 17.8 |
| famine s43 → stoneage | **TRANSFERE** | 7.05 | 12/12 | 0.0005 | 135.8 | 17.8 |
| famine s44 → stoneage | **TRANSFERE** | 2.05 | 12/12 | 0.0005 | 36.0 | 17.8 |
| stoneage → famine | **TRANSFERE** | 3.96 | 12/12 | 0.0005 | 63.8 | 18.0 |

`sign_p=0.00049` = le minimum atteignable à n=12 (12/12 favorables). Robuste sur les 3 champions famine
(malgré une compétence absolue très variable : 36 → 136) ET dans les deux sens. **Premier G1 positif.**

**Interchangeabilité (pilote, seed 42, 5 ères)** : le champion famine dans stoneage (78.5) ≥ le champion
NATIF stoneage dans stoneage (71.0) ; le champion stoneage dans famine (70.0) ≈ le champion natif famine
(66.0). Les champions sont ~interchangeables entre mondes.

## Lecture (double, honnête)

- **Positif** : la généralisation zéro-shot du north-star est CONFIRMÉE et powered — un champion évolué
  dans un monde survit un monde jamais vu à 2-7× tabula-rasa, aussi bien qu'un champion natif. Le substrat
  produit une compétence **réellement transférable** (contraste avec le NEUTRE développemental d'EDR-116 :
  ce sont deux facettes distinctes de G1).
- **Déflationniste (le nerf)** : le transfert est « parfait » parce qu'il n'existe qu'**une seule
  compétence** — la survie world-générale (forager, gérer le tank d'énergie) — et elle est générale *par
  construction*. Les affordances world-spécifiques (craft en stoneage, stockage en famine) ne deviennent
  JAMAIS compétence (EDR-111 tool-gate ; EDR-155 stockage redondant), donc il n'y a **rien de
  world-spécifique à échouer à généraliser**. « Généralisation parfaite » ⟺ « absence de spécialisation ».
  Cohérent avec le connectome plat ([[intelligence-typing-flat-connectome]], [[nas-bottleneck-is-substrate-not-search]]).

## Conséquences

- **`SDR-G1`** : la facette **zéro-shot** est POSITIVE (premier signal net). Reste `open` : le north-star
  fort — généraliser une compétence **composée/spécialisée** — n'est pas testé faute de spécialisation à
  transférer. Le verrou se déplace donc du « transfert » vers l'**émergence d'une compétence
  world-spécifique** (compositional binding, [[coop-competence-is-population-property]] EDR-125/128 ;
  tool-gate EDR-111). Tant qu'aucune compétence spécialisée n'émerge, le transfert restera trivialement
  parfait et non informatif au-delà du noyau partagé.
- **Prochaines pistes** (par ordre) : (1) faire ÉMERGER une compétence world-spécifique (durcir la famine
  pour EXIGER le stockage — cf. EDR-155 §Conséquences — ou débloquer le tool-gate stoneage), PUIS
  re-mesurer si CETTE compétence transfère ou reste locale ; (2) transfert vers un 3ᵉ monde à noyau moins
  partagé (soup/agricultural/industrial) pour tester la limite du « noyau partagé suffit ».

## Caveats (honnêteté)

1. **Métrique unique** (survie censurée). Pas d'analyse comportementale du forage transféré.
2. **Interchangeabilité = pilote n=1 seed** (5 ères) ; seul le verdict vs-tabula est powered (K=12). Le
   sur-classement du natif (78.5 vs 71) n'est PAS powered — lu comme « au moins équivalent », pas « meilleur ».
3. **Noyau partagé** : famine hérite de stoneage → le forage est commun. Le résultat mesure le transfert de
   ce noyau ; il ne se généralise pas nécessairement à une paire de mondes à noyaux disjoints.
4. **Mismatch de dims** absorbé par padding (pas de ré-entraînement des projections) — le champion transfère
   avec un handicap perceptuel, ce qui borne l'interprétation vers le bas (le vrai transfert est ≥ mesuré).
5. **n=3 champions** côté famine→stoneage (1 seul côté stoneage→famine, HoF global unique) ; le pattern est
   4/4 bras TRANSFERE mais l'asymétrie de réplication est réelle.
