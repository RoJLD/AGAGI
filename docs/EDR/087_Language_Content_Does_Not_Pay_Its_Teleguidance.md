# EDR 087 : Le CONTENU du langage ne paye pas — c'est du téléguidage (design 3-bras post-audit)

## Contexte

Climax de l'arc survie→langage. EDR 085 a débloqué la survie longue (sweet spot d'énergie). On re-teste
le bénéfice du langage sur ce substrat — avec un design **corrigé après une revue adversariale** (EDR
086 audit) qui avait trouvé 12 confounds, dont 3 bloquants. Corrections : **appariement vrai** (RNG
re-seedé par bras), **nuit OFF + gate sur la survie**, et surtout un **bras de contrôle BROUILLÉ**.

> Le test naïf **FIABLE vs SOLO** confond *« tokens informatifs »* avec *« mécanisme de guidage actif »*.
> Le bras **BROUILLÉ** (même mouvement décode-et-agis, mais contenu de token ALÉATOIRE) isole le **CONTENU
> linguistique** du **téléguidage spatial**. Contraste clé = **FIABLE − BROUILLÉ**.

## Résultat (12 seeds, apparié)

| Bras | Mammouths | lecture |
|---|---|---|
| **FIABLE** (contenu vrai) | 25.3 ± 13.7 | décode-et-agis tire ~131×/run (mécanisme actif) |
| **BROUILLÉ** (contenu aléatoire, *même mouvement*) | 23.3 ± 10.8 | |
| **SOLO** (n'agit pas) | 14.2 ± 8.5 | |
| **FIABLE − BROUILLÉ** *(le CONTENU)* | **+2.0 ± 4.1 SE** (58 %) | **sous 2 SE — pas robuste** |
| (secondaire) FIABLE − SOLO *(mécanisme+contenu)* | +11.2 ± 4.7 SE (83 %) | grand, mais c'est le **guidage** |

> **Le bénéfice apparent du langage (+11.2 vs SOLO) est surtout du TÉLÉGUIDAGE** : approcher un locuteur
> par construction adjacent à un apex = plus de kills, *indépendamment du mot*. Le **CONTENU** (quel apex)
> n'ajoute que **+2.0, sous 2 SE** → **pas d'avantage robuste du contenu linguistique.** Sans le bras
> BROUILLÉ, on publiait un faux positif (+11 = « le langage paye ! »). **6ᵉ fois** qu'un design rigoureux
> défait un signal séduisant (`057/075/077/082/083/087`).

## Le gate, et ce qu'il révèle

- Gate déclenché : survie des champions **évolués** = 92 ticks (< 120). Cause (sweep) : le monde
  équilibré sustente **296 ticks** avec les champions HoF bruts ; mais l'**évolution** (life_score
  récompense `mammoth_kills`, EDR 029) sélectionne des **chasseurs agressifs qui meurent plus tôt**
  (approcher le Mammouth = riposte). **Arbitrage : optimiser la chasse réduit la survie.**
- Mais 92 ticks + 14-25 Mammouths tués = **interaction d'apex amplement suffisante** pour que le contenu
  paye s'il le devait. Il n'a pas payé. Le résultat est donc robuste malgré le gate.

## Le vrai dernier verrou — la STRUCTURE DU MONDE, pas la survie

> **Le contenu d'un signal ne paye que si la DISTINCTION qu'il porte est décisionnellement critique ET
> fréquente.** Ici : Mammouth ET Ours sont positifs (approcher les deux), le Leurre est rare →
> **discriminer ne sert presque à rien** → le contenu est *redondant avec le mécanisme* (« approche le
> locuteur près d'un apex »). Le langage fonctionnel n'exige pas seulement des agents qui survivent et
> communiquent — il exige un **monde où le mot fait une différence de décision** (ex : majorité de
> Leurres-pièges où éviter REQUIERT le contenu ; ou apex visuellement indistinguables dont seul le token
> dit la nature).

## Statut & suite

- `relang_sweet.py` (design 3-bras post-audit, appariement, nuit off, gate). **Le CONTENU du langage ne
  confère pas d'avantage robuste ici** ; le bénéfice apparent est du téléguidage spatial.
- **Prochain levier (le vrai)** : un monde où le contenu est *décisionnellement critique* (densité de
  Leurres ≫ proies positives, ou apex indistinguables sans le mot). *Alors* re-tester FIABLE vs BROUILLÉ.
  Ce n'est plus la survie le verrou — c'est la **pertinence décisionnelle de la distinction**.

## Honnêteté

- Résultat directionnel net (contenu sous 2 SE) ; le gate (92<120) est un caveat *mais informatif* (le
  trade-off survie↔chasse). Un re-run sur substrat HoF (296t) confirmerait sans surprise attendue.
- La valeur ENTIÈRE de cet EDR vient de la **revue adversariale** (086) : le bras BROUILLÉ a transformé
  un faux positif (+11) en vérité (le contenu ne paye pas, +2).

## Variables d'expérience

Densité Leurre/positifs (rendre la distinction critique), apex indistinguables sans token, substrat HoF
vs évolué (trade-off survie↔chasse), métrique pré-enregistrée, puissance (≥12 seeds apparié + bras
brouillé).
