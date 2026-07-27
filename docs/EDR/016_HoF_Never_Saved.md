---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-016
type: EDR
title: "Le Moteur Évolutif était Cassé — le Hall of Fame n'était JAMAIS sauvé"
status: legacy
gate: foundational
---

# EDR 016 : Le Moteur Évolutif était Cassé — le Hall of Fame n'était JAMAIS sauvé

## Contexte

En cherchant pourquoi rien ne grimpe inter-ères (EDR 014, attribué à tort au manque
d'exploration), on a inspecté la persistance : **`main_biosphere` charge le Hall of Fame
(`load_hall_of_fame`, l.78) mais ne l'écrit JAMAIS.** Aucun `save_to_hall_of_fame` dans
toute la boucle. Le log « Les meilleurs ont été sauvegardés » (l.364) était **faux**.

## Constat — il n'y avait aucune évolution inter-ères

Chaque ère :
1. charge le **même HoF statique** (figé par un vieux process : `multiverse_runner`/`test_fixes`),
2. en tire une population + mutations aléatoires,
3. tourne jusqu'à extinction,
4. **jette tout** (les survivants/champions ne sont jamais persistés).

Les « 30 ères » n'étaient donc **pas une évolution** mais 30 redémarrages indépendants
depuis une population figée. La sélection *intra-ère* avait lieu mais n'était jamais
retenue → l'ère suivante l'ignorait.

> **Conséquence rétrospective** : tout l'arc exploration de la session (scaffold, curiosité
> partagée/par-agent, nouveauté count-based) mesurait du *within-life* systématiquement
> **jeté à chaque ère**. La « platitude inter-ères » avait une cause bien plus fondamentale
> que l'exploration : il n'y avait littéralement aucun mécanisme de mémoire évolutive actif.

## Décision (V18.3)

Sauver les meilleurs au HoF en fin d'ère (`main_biosphere`, après extinction) :
```python
from src.seed_ai.persistence import save_to_hall_of_fame, calculate_life_score
pool = env.agents + env.dead_agents
for cand in sorted(pool, key=calculate_life_score, reverse=True)[:5]:
    save_to_hall_of_fame(cand)
```

## Résultat — la première vraie évolution du projet

Run V18_HoF_save_fix (30 ères, HoF **vierge** au départ, monde dur) :

| | HoF statique (avant, monde + facile) | HoF après fix (vierge, monde dur) |
|---|---|---|
| Meilleur champion | preys **6** (score 301) | preys **12** (score 608) |
| Top-6 | preys 4-6 | preys **12, 8, 8, 7, 7, 7** |

> Parti de zéro dans le monde dur, l'élite a **doublé** le plafond historique. L'évolution
> inter-ères, jusqu'ici inexistante, **accumule désormais réellement des gains.**

## Nuances mesurées

- **Moyenne de population plate** (survie 76→72, énergie ~33) : le HoF garde l'élite, mais
  la régénération mutation-lourde repeuple surtout de mauvais mutants. → tuning de
  régénération (taux de mutation, part d'élite clonée) = prochain levier.
- **Craft toujours 0** : double cause — (a) la chaîne profonde `grab→grab→rub` (EDR 015),
  et (b) le `life_score` (`age + preys + altars`) **ne récompense pas le craft** → même en
  évoluant, les crafteurs ne sont pas sélectionnés. Pour évoluer le craft, il doit entrer
  dans la fitness (ou mener à plus de preys via la chasse au Mammouth).

## Conséquences

- Le moteur évolutif **fonctionne maintenant au niveau de l'élite** — prérequis débloqué
  pour que scaffold / curiosité / **curriculum** s'accumulent enfin entre les ères.
- Re-tester les leviers précédents *sur évolution réelle* devient pertinent (ils étaient
  mesurés dans un système sans mémoire).
- Ajouter le craft (ou un proxy) au `life_score` pour que la sélection puisse le saisir.

## Addendum — Test « craft dans la fitness » (null result instructif)

`calculate_life_score` intègre désormais `spears_crafted * 300` (craft tracké sur l'agent),
pour que la sélection saisisse les crafteurs maintenant que le HoF persiste.

Run V18_craft_fitness (30 ères, sur le HoF évolué) : **SPEAR 14 → 14** (0 nouvelle),
**0 crafteur** dans le HoF — mais le meilleur chasseur grimpe **preys 12 → 15** (score 766).

> Mettre le craft dans la fitness ne sert à rien **s'il n'y a aucun crafteur à sélectionner**,
> et ce run en a produit zéro. Pire : parti du HoF évolué, la population se spécialise encore
> en chasse (preys 12→15) et explore *moins*. **On ne peut pas sélectionner ce qui n'est
> jamais produit.** Seul un curriculum (enseigner la collecte → atteindre l'état craftable)
> attaque la *production* du comportement. Le poids craft reste en place : il agira dès que
> des crafteurs seront produits.

## Variables d'expérience

Nombre de champions sauvés par ère (top-K), taux de mutation à la régénération, composition
du `life_score` (poids du craft), part d'élite clonée vs mutée.
