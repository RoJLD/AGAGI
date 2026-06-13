# EDR 082 : Compétence nécessaire mais PAS suffisante — le langage doit être SÉLECTIONNÉ

## Contexte

Boucle bouclante de la session. EDR 075 : le langage ne paye pas car les agents (frais) sont
incompétents. EDR 076-081 : on a forgé un substrat COMPÉTENT et croissant (HoF robuste). On re-teste
ici le bénéfice du langage sur ce substrat : évoluer des champions compétents DANS le monde de Lewis
(robuste K=4), leur donner des têtes référentielles co-entraînées (074), puis comparer FIABLE (tête +
décode-et-agis : approche Mammouth/Ours, fuit Leurre) vs SOLO (ignore les signaux). Comparaison
**appariée** (mêmes agents/têtes par seed).

## Résultat — le signal de n=4 s'évapore sous puissance

| | n=4 (1ʳᵉ passe) | **n=12 (puissance, apparié)** |
|---|---|---|
| FIABLE Mammouths | 5.00 | **1.67 ± 1.43** |
| SOLO Mammouths | 3.25 | **2.33 ± 2.72** |
| diff appariée (FIABLE−SOLO) | +1.75 (suggestif) | **−0.67 ± 0.86 SE** |
| FIABLE > SOLO | — | **33 % des seeds** |

> **Le +54 % de n=4 était un artefact de petit échantillon.** À n=12, la différence appariée est
> **négative et noyée dans le bruit** (−0.67 ± 0.86 SE ; FIABLE>SOLO dans seulement 33 % des seeds).
> **Le langage ne paye PAS, même sur agents compétents.** (Leurres minuscules, survivants=0 partout.)

## Le vrai enseignement — compétence ≠ suffisant ; le langage doit être SÉLECTIONNÉ

> EDR 075 disait « la compétence est le verrou ». **Vérité affinée : la compétence est NÉCESSAIRE mais
> PAS SUFFISANTE.** Les agents sont sélectionnés pour SURVIVRE (life_score), pas pour UTILISER les
> signaux. Le décode-et-agis est **imposé**, pas **sélectionné** : on a boulonné un langage fiable sur
> des agents qui n'ont jamais été évolués pour *écouter*. Sans politique qui exploite le signal, le
> décode-et-agis ne fait que perturber un comportement optimisé pour autre chose.

> **Le bénéfice d'une communication n'émerge que quand son USAGE est sous pression de sélection.** Ça
> reboucle sur EDR 053 (la loterie à 25 %) : le langage utile doit être *sélectionné*, pas décrété. On a
> rendu le code *fiable* (072-074) et le substrat *compétent* (076-081) — il manque la **co-évolution de
> l'USAGE du langage avec la survie**.

## La rigueur, 4ᵉ fois héroïne

> n=4 → n=12 : le signal s'évapore. C'est la **4ᵉ fois** de la session qu'un signal à peu de seeds
> disparaît sous puissance (057, 075, 077, et ici 082). **Powerer avant de conclure** est LA discipline
> de ce journal — elle vient d'éviter de fausser « la boucle se referme ».

## Statut de la grande boucle (040 → 082)

| | acquis |
|---|---|
| code fiable (072-074) | ✅ le langage référentiel converge à 100 %, câblé dans l'agent |
| substrat compétent (076-081) | ✅ HoF robuste, compétence qui grimpe |
| **bénéfice fonctionnel (075, 082)** | ❌ **pas encore : compétence + fiabilité ne suffisent pas ; il faut SÉLECTIONNER l'usage** |

## Suite (re-cadrée, claire)

> Prochain levier : **co-évoluer l'usage du langage AVEC la compétence** — une fitness qui récompense
> les agents qui *survivent ET exploitent les signaux* (chasse coordonnée guidée par les tokens, évitement
> de Leurre guidé par les tokens), pas le décode-et-agis imposé. C'est l'émergence de la communication
> *fonctionnelle* sous sélection (la vraie réponse à 053), maintenant qu'on a le code fiable + le substrat
> compétent comme fondations.

## Honnêteté

- Résultat NÉGATIF net (diff −0.67, 33 %), powered (n=12, apparié). La valeur est le *diagnostic* : on
  sait désormais que les deux fondations (fiabilité, compétence) sont nécessaires mais qu'il manque la
  *sélection de l'usage*.
- Survivants=0 : les agents, même « compétents » (~55 ticks dans l'évolution), meurent avant 300 ticks
  dans Lewis — la compétence de survie soutenue reste limitée, ce qui plombe aussi la coordination.

## Statut

- `lang_on_competent.py` (évolution Lewis robuste + FIABLE/SOLO apparié powered). **Compétence
  nécessaire, pas suffisante ; le langage doit être SÉLECTIONNÉ pour payer.** Prochain levier :
  co-évolution usage-du-langage + compétence.

## Variables d'expérience

Fitness récompensant l'usage du signal (chasse/évitement guidés par token), co-évolution langage+survie,
nombre de générations en Lewis, num_agents, durée de vie soutenue, puissance (≥12 seeds, apparié).
