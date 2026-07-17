---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-057
type: EDR
title: "Confirmation de 055 à 40 seeds — NUL. Le harnais vindiqué, l'arc fiabiliser fermé."
status: legacy
gate: G3
---

# EDR 057 : Confirmation de 055 à 40 seeds — NUL. Le harnais vindiqué, l'arc fiabiliser fermé.

## Contexte

EDR 055 : align-énergie *prometteur* (taux 33→50 %) mais sous-puissant (n=6). EDR 056 : la version
fitness backfire (révertie). Décision utilisateur : **confirmer 055 (énergie) à 40 seeds**. Seuil
relâché à t≥2.0 + IC.

## Résultat — l'effet n'existe pas

40 seeds × 16 ères, align ON(3.0) vs OFF :

| | taux d'émergence [IC95] | gain moyen [IC95] |
|---|---|---|
| OFF | 32 % [18-47] | 0.0099 [0.0051, 0.0147] |
| **ALIGN** | **28 % [14-41]** | **0.0062 [0.0032, 0.0091]** |

t=−1.31, d=−0.29 → **non significatif, et point-estimé légèrement NÉGATIF**.

## Conclusion — un négatif propre

> **Le « prometteur » 33→50 % de l'EDR 055 était du BRUIT.** Sous puissance, la sélection alignée
> énergie ne fiabilise rien (au mieux nulle, sinon défavorable). Les IC se chevauchent largement et le
> point-estimé va dans l'autre sens.

- **Vindication TOTALE du harnais (052)** : le signal à n=6 s'est évaporé à n=40 — exactement ce que
  le harnais existe pour attraper. **Bâtir sur 055 aurait été bâtir sur du sable.**
- **Taux de base bien estimé** : ~32 % [18-47] — cohérent avec les ~25 % de l'EDR 053. La loterie
  est *robuste* ; aucun mécanisme à la main ne la déplace.

## L'arc « fiabiliser » (053→057) — fermé

| EDR | Lever | Verdict (sous mesure) |
|---|---|---|
| 053 | (constat) | émergence stochastique ~25-32 % (brisure de symétrie) |
| 054 | propagation | confondue (attrapée) ; obstacle : sélection aveugle au langage |
| 055 | align énergie | *prometteur* à n=6… |
| 056 | align fitness | backfire (métrique bruitée) |
| **057** | align énergie, n=40 | **NUL** (055 était du bruit) |

> **On NE peut PAS fiabiliser l'émergence avec une sélection conçue à la main** (dans ce système, à ce
> régime). La loterie ~25-32 % tient. C'est un résultat *définitif et honnête*, pas un échec de
> méthode — la méthode a parfaitement fonctionné (elle a refusé de nous laisser croire à 055).

## Conséquence — le pivot est forcé (et l'argument #8 imparable)

- **6 mécanismes de langage à la main (045-057), zéro qui fiabilise.** L'approche manuelle de cette
  frontière est *exhaustée*. Continuer = rendements négatifs.
- **L'argument du #8 est désormais un résultat empirique** : seul un itérateur (proposer+mesurer en
  masse), sous évaluation puissante, pourrait explorer cet espace de mécanismes — la main n'y arrive
  pas, et chaque tentative coûte cher à évaluer.
- **Pivot** : (2) NAS-mémoire (effets peut-être plus francs, harness-prêt) et (3) #8. Le langage
  reste un acquis *caractérisé* : réel, stochastique, non-fiabilisable à la main.

## Statut

- `align_selection` / `REF_FITNESS_WEIGHT` : seams conservés, **off** (sans effet démontré). 133 tests.
- L'arc fiabiliser : **clos sur un négatif propre.**

## Variables d'expérience

(Pour un futur retour, hors approche manuelle) : mesure par-agent fiable (≫ échantillons), #8
itérateur, ou accepter la stochasticité comme propriété du système.
