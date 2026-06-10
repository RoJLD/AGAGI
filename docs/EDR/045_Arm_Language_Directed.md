# EDR 045 : Arming dirigé du #8 sur le LANGAGE — frontière tenace (et pourquoi)

## Contexte

Décision utilisateur : armer le #8 sur le langage puis le NAS, un à la fois. Comme l'armement
LLM *live* exige un conteneur jetable + une clé (absents ; règle EDR 044), on arme en mode
**dirigé** : implémenter l'intervention que le LLM *proposerait* (une **pression référentielle**),
la faire évoluer, et **mesurer** si le langage émerge — sans appel LLM externe (sûr).

## Intervention testée

`world.referential_scale` (EDR 045) : un agent proche de l'apex qui émet un token **partagé** par
ses voisins proches reçoit un bonus ∝ nombre d'accords → sélectionne une *convention*
« token = Mammouth ». A/B : évoluer 20 ères AVEC pression (scale=0.5) vs SANS, même HoF de départ,
puis mesurer `I(token ; near_Mammouth)`.

## Résultat — la frontière résiste

| Condition | MI(token ; Mammouth) | baseline (perm.) |
|---|---|---|
| AVEC pression | 0.0007 | 0.0010 |
| SANS pression (contrôle) | 0.0017 | 0.0007 |

Les deux **au niveau du bruit** (< 0.002 bit ; un vrai signal référentiel ferait ≫ 0.5 bit). **Pas
d'émergence.** La pression dirigée n'a pas franchi la frontière.

## Pourquoi (le vrai gain) — l'intervention dirigée était défectueuse

1. **Récompenser la *convergence* est gameable** : un token **constant** émis *partout* satisfait la
   prime d'accord près de l'apex *sans* être spécifique au Mammouth → MI reste 0. Il aurait fallu
   *pénaliser* l'usage du token hors-contexte (spécificité), pas seulement récompenser l'accord.
2. **Un seul référent binaire ne crée pas de besoin référentiel** : « Mammouth présent ou non » se
   code par *parler/se taire* (la **présence**, EDR 043) — le *contenu* du token n'apporte rien. Le
   langage référentiel n'a de raison d'émerger qu'avec **plusieurs référents** exigeant des tokens
   *distincts* (Mammouth vs Sanglier vs…), idéalement un vrai jeu de Lewis (locuteur/auditeur/action).

## Conséquences

- **Le générateur dirigé (moi) a proposé un mécanisme défectueux ; la boucle l'a mesuré
  honnêtement.** C'est l'argument du #8 *et* de sa prudence : la frontière est tenace, concevoir la
  *bonne* pression est subtil, et c'est là qu'un générateur **itérant sur ses échecs mesurés** (LLM)
  vaudrait quelque chose — mais même lui exige d'abord un **setup multi-référent**.
- **On n'a rien cassé en se précipitant.** L'arming dirigé a *testé* la frontière sans risque et a
  produit une hypothèse claire pour la suite (pression de spécificité + multi-référents + jeu de Lewis).
- `referential_scale` reste **off par défaut** (126 tests verts).

## Suites

- Avant de ré-attaquer le langage : **monde multi-référent** (signaler *quel* gibier) + pression de
  **spécificité** (récompense en contexte, coût hors contexte) + rôles locuteur/auditeur.
- C'est précisément le genre de redesign que le #8 (LLM) pourrait proposer — mais qui mérite d'être
  cadré avant d'armer le live.

## Variables d'expérience

`referential_scale`, durée d'évolution, nombre de référents, pénalité de spécificité, jeu de Lewis.
