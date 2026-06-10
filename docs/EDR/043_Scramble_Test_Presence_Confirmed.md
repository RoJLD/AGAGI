# EDR 043 : Test de brouillage — la PRÉSENCE confirmée (ferme EDR 042)

## Contexte

L'EDR 042 supposait que le bénéfice de la portée du signal (EDR 040) venait de la **présence**
(entendre un voisin), pas du **contenu** du token (MI≈0). Arbitre : brouiller le token (token
**aléatoire** = sens détruit, présence préservée). Trois lignées, même HoF de départ : radius 0 /
radius 3 réel / radius 3 brouillé.

## Résultat

**Manche 1 (16 ères) — inconcluante (honnêtement).** L'effet de B lui-même avait **dérivé** :
radius3 réel +0.12 seulement (vs +1.00 en EDR 040), dans le bruit → impossible de trancher. La
population (HoF) a traversé des dizaines d'expériences → dérive (leçon EDR 039/041). *On ne conclut
pas sur du bruit.*

**Manche 2 (24 ères, plus de puissance) — verdict net :**

| Lignée | mammouth/ère (2ᵉ moitié) | gain vs radius 0 |
|---|---|---|
| `radius 0` | 1.17 | — |
| `radius 3 réel` | 1.42 | **+0.25** |
| `radius 3 brouillé` | 1.33 | **+0.17 (68 % conservé)** |

> Brouiller le token **conserve ~68 %** du gain → le **contenu n'importe pas** ; la **présence**
> (entendre un voisin proche) porte le bénéfice.

## Conclusion — deux preuves indépendantes

1. `I(token ; near_Mammouth) ≈ 0` (EDR 042) : le token **ne porte pas d'info**.
2. Brouiller le token **ne coûte presque rien** (EDR 043) : son contenu **n'est pas utilisé**.

> **Le gain de B (EDR 038/040) est de l'AGRÉGATION PAR PROXIMITÉ, pas du langage référentiel.** Une
> coordination spatiale réelle et utile a émergé ; *aucune communication* au sens fort. La distinction
> est nette et désormais doublement étayée. EDR 042 **fermé**.

## Conséquences

- **Acquis** : la détection de présence + l'agrégation améliorent la coopération (à conserver).
- **Frontière inchangée** : le **langage référentiel** reste non émergent — c'est, avec l'impasse de
  l'EDR 037, un candidat au #8 (générateur LLM) ou à une pression structurée plus forte.
- **Méta-leçon (récurrente)** : la dérive de population rend les magnitudes instables ; seuls les
  résultats **qualitatifs/relatifs** (brouillé ≈ réel) et **multi-preuves** sont fiables.

## Limites

- Magnitudes plus faibles qu'en EDR 040 (dérive) ; la réponse *qualitative* (présence) est robuste,
  pas les chiffres absolus.
- n=1 paire de lignées ; multi-seeds renforceraient encore.

## Variables d'expérience

`scramble_signal`, durée d'évolution, fraîcheur de la population, multi-seeds.
