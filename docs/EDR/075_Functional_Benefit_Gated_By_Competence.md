---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-075
type: EDR
title: "Le bénéfice fonctionnel du langage est GATÉ par la compétence (négatif honnête)"
status: legacy
gate: G3
---

# EDR 075 : Le bénéfice fonctionnel du langage est GATÉ par la compétence (négatif honnête)

## Contexte

Question climax de l'arc du langage : le code fiable (074) confère-t-il un AVANTAGE de survie ? À
distance, Mammouth (gain de groupe) et Leurre (piège mortel) sont indistinguables — seul le signal
tranche. On câble un **décode-et-agis** (`world.decode_act`, `_decode_act_override`) : un auditeur
décode le token du locuteur le plus proche *réellement adjacent à un apex* (via le `Wd` de sa tête) et
APPROCHE si Mammouth/Ours, FUIT si Leurre. Trois conditions, MÊME comportement, seule la qualité du
signal change : **FIABLE** (têtes co-entraînées), **BRUITÉ** (tokens connectome), **SOLO** (n'agit pas).

## Résultat — aucun bénéfice fonctionnel

| Condition | Mammouths | Leurres (8 seeds) | survivants | fires |
|---|---|---|---|---|
| FIABLE | 0.00 | 2.25 ± 0.83 | 0 | ~82 |
| BRUITÉ | 0.00 | 2.00 ± 1.58 | 0 | ~79 |
| SOLO | 0.00 | ~2.0 | 0 | 0 |

- **Le décode-et-agis SE DÉCLENCHE (~80×)** — le câblage marche.
- **Mais il ne change RIEN** : FIABLE ≈ BRUITÉ ≈ SOLO (~2 Leurres). Et **survivants=0, Mammouths=0
  partout** : les agents meurent tous, n'en tuent aucun.

## La rigueur a évité un faux positif

> Un premier run à **3 seeds** suggérait FIABLE 2.3 < BRUITÉ 3.7 (« la fiabilité protège »). À **8
> seeds**, le signal a **disparu** (2.25 vs 2.00). C'était un artefact de petit échantillon — exactement
> comme l'EDR 057 (faux positif évaporé à 40 seeds). On rapporte le négatif.

## Le vrai enseignement — les capacités sont STRATIFIÉES

> **Un code fiable est nécessaire mais PAS suffisant.** Le langage ne peut pas conférer d'avantage à des
> agents qui *ne savent ni survivre ni chasser* (tous meurent, zéro Mammouth tué, rencontres d'apex
> trop rares). On ne récolte le bénéfice d'une capacité HAUTE (le langage) sans la compétence BASSE
> (perception, survie, action coordonnée) pour l'exploiter.

> **Le goulot n'est pas le code — c'est la COMPÉTENCE du substrat.** Et c'est *prouvé* (mécanisme qui
> tire à vide), pas supposé. C'est une vérité d'AGI : empiler une capacité de haut niveau sur un agent
> incompétent ne produit aucun bénéfice ; il faut d'abord la couche d'en dessous.

## Honnêteté

- Négatif net. La valeur est le *diagnostic* : le langage fiable (072-074) est en place, mais sa
  *valeur fonctionnelle* attend un substrat de foraging COMPÉTENT (survie + chasse coopérative du
  Mammouth), absent ici même avec énergie boostée (250) et densité d'apex ×2.5.
- Le `decode_act` + `_decode_act_override` + compteurs restent (gated, 141 tests verts) — infrastructure
  prête pour re-tester sur un substrat compétent.

## Suite (re-cadrée par ce négatif)

> Le prochain levier n'est **pas** plus de langage — c'est la **COMPÉTENCE de foraging** : faire
> évoluer (sur plusieurs ères) des agents qui survivent et chassent le Mammouth en coordination. Une
> fois ce substrat acquis, le bénéfice fonctionnel du langage devient mesurable (re-lancer `func_benefit`).
> L'ordre correct : compétence d'abord, puis le langage qui la *démultiplie*.

## Statut

- `func_benefit.py` + `decode_act`/`_decode_act_override`/`leurre_hits`/`decode_act_fires` (gated).
  **Bénéfice fonctionnel non démontré** : gaté par la compétence du substrat, pas par le code. Négatif
  honnête qui redirige vers la compétence de foraging comme prérequis.

## Variables d'expérience

Compétence du substrat (agents évolués vs frais), survie (énergie, monde), densité d'apex, chasse
coopérative du Mammouth, décode-et-agis (spatial, source), nb de seeds (≥8 pour la puissance).
