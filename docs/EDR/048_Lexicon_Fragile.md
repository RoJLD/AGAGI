# EDR 048 : Renforcer le langage — le lexique ne scale pas (correctif honnête à l'EDR 047)

## Contexte

EDR 047 : le langage référentiel émerge sous demande (2 référents, MI 0→0.033). On *renforce* :
3 référents (Mammouth=appel, Ours=appel récompensé, Leurre=danger), 36 ères, et on mesure le
**lexique** (token dominant par référent).

## Résultat — pas de lexique plus riche

| | MI(token ; référent /3) | baseline | token dominant |
|---|---|---|---|
| AVANT | 0.0145 | 0.0057 | **silence** (83–97 %) |
| APRÈS 36 ères | 0.0142 (plat) | 0.0072 | **silence** (83–92 %) |

> Le 3ᵉ référent **n'enrichit pas** le lexique. Le signal reste **faible** (~0.014 — *plus faible*
> que les 0.033 de l'EDR 047 à 2 référents) et le « token » dominant pour *tous* les référents est le
> **silence**. Pas de tokens distincts par référent : **aucun lexique**.

## Pourquoi (le correctif)

1. **Altruisme du signal** : celui qui *parle* bénéficie peu — c'est l'**auditeur** qui profite de
   l'info. Sans incitation directe du locuteur (réciprocité, sélection de parentèle), le **silence**
   est l'attracteur par défaut → la majorité se tait. C'est un problème *connu* et profond de
   l'évolution de la communication.
2. **Dilution d'affordance** : Mammouth et Ours appellent tous deux le pack (même réponse) → aucun
   besoin de tokens *distincts* pour eux. Au mieux un signal binaire « venir / éviter », pas un
   lexique de 3.

## Conséquence — tempérer l'EDR 047

L'émergence du langage (EDR 047, MI 0.033) est **réelle mais NAISSANTE et FRAGILE** : elle ne *scale*
pas vers un lexique plus riche dans ce setup. **On a une émergence, pas une langue.** Mieux vaut le
mesurer que le sur-vendre — la thèse « la demande fait émerger » tient (047), mais le *renforcement*
exige plus que « ajouter des référents » : il faut résoudre l'**incitation du locuteur** (que parler
*paie* pour le parleur) et créer des **affordances distinctes** (réponses différentes par référent).

## Suites

- **Aligner l'incitation du locuteur** : récompenser le signaleur quand son signal mène à un succès
  (pack recruté qui tue le Mammouth) — réciprocité directe.
- **Affordances distinctes** : 3 référents = 3 *réponses* optimales différentes (appeler le pack /
  chasser solo / fuir), pas seulement 3 types.
- Multi-seeds (la mesure est bruitée ; 047 vs 048 diffèrent en partie par bruit + population).

## Variables d'expérience

Incitation du locuteur, nb d'affordances distinctes, coût/seuil du signal, durée, multi-seeds.
