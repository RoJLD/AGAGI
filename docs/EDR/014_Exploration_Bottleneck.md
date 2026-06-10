# EDR 014 : Le Goulot d'Exploration — Diagnostic du Moteur Évolutif & Limite du Reward-Shaping

## Contexte

Après C (recalibrage) + A (scaffold d'approche puis de craft), le monde est survivable et enseigne la chasse, mais **le craft n'émerge jamais** (1 lance / >6000 naissances) et **la trajectoire inter-ères reste plate**. On a diagnostiqué le moteur évolutif, puis tenté la réparation par la curiosité.

## Diagnostic du moteur évolutif (mesuré)

| Mesure | Constat |
|---|---|
| Hall of Fame (top-10) | preys_eaten **4-6**, altars_solved **0**, jamais de craft → **plafond bas** |
| Variance de fitness (5877 agents) | std 19.5, p99=76 → **la variance EXISTE** (top 10% s'en sort) ; 70% à score ≤1 |
| `total_dreams` (MCTS/dreaming) | **0 sur 5877 agents** → l'organe de planification est **100% dormant** |

**Conclusion** : la **sélection fonctionne** (variance réelle, le HoF préserve les meilleurs). Le problème n'est PAS la sélection — c'est qu'**il n'y a rien de neuf à sélectionner**. L'évolution est coincée dans un **optimum local** (« manger ~5 proies ») car l'**exploration est absente** : organe MCTS éteint, et la mutation de poids seule ne produit pas de saut comportemental qualitatif (craft, altar). Le moteur tourne à vide faute de carburant exploratoire.

## Réparation tentée — Curiosité (boucle sur Step 1)

Câblage de la curiosité du World Model comme **récompense intrinsèque** dans le policy gradient (`world_1`) :
```
rewards = (Δénergie)  +  curiosity_scale · surprise_WorldModel
```
La surprise = erreur de prédiction (nouveauté). Elle **s'auto-annèle** (chute quand le monde est appris — propriété RND). Cense pousser à explorer les états surprenants (ex. tenir un nouvel objet après un grab).

## Résultat — insuffisant, et pourquoi (mesuré)

Run V18_V0_curiosity (30 ères) : **SPEAR_CRAFTED toujours 1**, plafond HoF inchangé, surprise ~0.03.

> La **surprise sature bas (~0.03)** : le World Model partagé/linéaire apprend la dynamique moyenne en quelques ticks et n'est plus surpris. La curiosité (~0.03×2 = 0.06/tick) est **noyée** par l'exploitation (un kill = 25 énergie). **Déséquilibre exploration/exploitation** : les agents exploitent la chasse, n'explorent jamais le craft.

Le mécanisme est correct (intrinsèque, auto-annelé, complète Step 1) mais **trop faible seul**.

## Synthèse — la cascade de goulots

Chaque réparation a révélé le goulot suivant, par la mesure :

1. Monde infini → **pas de pression** (Step 2 : rareté). ✅
2. Monde dur → **crash + competence** (C : camp de base, riposte juste). ✅
3. Agents faibles → **chasse non apprise** (A-approche : scaffold). ✅ (chasse OK)
4. Craft absent → **chaîne de 3 actions jamais découverte** (A-craft : shaping). ❌ (shaping ne renforce que ce qui se produit)
5. Pas d'adaptation → **0 exploration** (curiosité). ❌ (surprise trop basse, noyée par l'exploitation)

Le **vrai mur restant** : découvrir une **chaîne d'actions profonde** (grab→grab→rub) dans un espace où l'exploitation domine. Ni le reward-shaping ni la curiosité-World-Model (faible) ne suffisent.

## Conséquences — leviers pour briser le mur d'exploration

- **(I) Curiosité forte** : World Model **par agent** (plus de surprise résiduelle, EDR 011) ou **nouveauté count-based** (récompenser des configs d'état rares : inventaire, position) — un signal d'exploration qui ne sature pas.
- **(II) Chaîne moins profonde** : collapser `grab→grab→rub` en `grab→grab` (auto-craft en tenant les bons items). Rend le craft *discoverable*. Moins "émergent", mais débloque.
- **(III) Curriculum de sous-compétences** : enseigner grab, puis rub, séparément (CurriculumRunner sur sous-tâches).
- **(IV) Tuer les gènes fantômes + activer le dreaming** : libérer le budget de mutation et donner un organe d'exploration latente (Vague 1).

## Addendum — Nouveauté count-based (levier I) : premier franchissement, mais faible

Implémentation : récompense intrinsèque `novelty_bonus(count) = scale/√count` sur la
**signature d'inventaire** (`state_signature`), ajoutée au policy gradient. Cible les
précurseurs du craft : `()` ultra-fréquent → ε ; `('rock','stick')` quasi jamais vu → fort.

Run V18_V0_novelty (30 ères) : **SPEAR_CRAFTED 1 → 2** — la **première lance issue de
l'exploration** (aucune approche précédente n'y était parvenue). Survie moy 69→74.

> Le mécanisme **fonctionne en principe** (il a fait émerger un craft par exploration
> dirigée) mais reste **trop faible** : 1 lance / 969 naissances. Récompenser les états
> précurseurs aide, mais l'agent doit toujours *exécuter* la chaîne de 3 actions, et le
> signal (~3/tick) reste dilué par l'exploitation. **Le mur est fissuré, pas abattu.**

Suites : amplifier (novelty_scale plus fort + World Model **par-agent** pour une curiosité
non saturée — levier I complet) **ou** réduire la profondeur de chaîne (auto-craft, levier II
— rend le craft commun immédiatement, au prix d'un peu d'émergence).

## Variables d'expérience

`curiosity_scale`, `novelty_scale`, portée du World Model (partagé vs par-agent), profondeur de la chaîne de craft, état de l'organe MCTS (`organ_genes[0]`).
