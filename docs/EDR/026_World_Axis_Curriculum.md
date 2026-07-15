---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-026
type: EDR
title: "Curriculum sur l'Axe Monde — et l'imbrication des deux axes"
status: legacy
gate: G0
---

# EDR 026 : Curriculum sur l'Axe Monde — et l'imbrication des deux axes

## Contexte — étape 5 de la Vague 0ter

Symétrique de l'axe Craft (EDR 025) : ramper la *difficulté du monde* par paliers, mastery
gate. La difficulté la plus contraignante (EDR 021) est la **rareté alimentaire** ; on rampe la
capacité de charge en proies (abondant → rare). La sélection (HoF) doit adapter la population.

Sonde préalable (pop HoF-seeded, 30 agents) — `proies_moy` est un signal de difficulté propre
et monotone : capacité 30 → **2.15**, 15 → **1.14**, 6 → **0.60**. (Une pop *random* meurt en
~2 ticks — logits explosés — d'où le démarrage depuis des chasseurs viables, sans reset du HoF.)

## Décision (V18.13)

`tools/curriculum_world.py` : monde normal (nuit, danger, régén), `target_prey_count` rampé
`30 → 20 → 12 → 6`. Mastery = `proies_moy ≥ 1.0` pendant 2 ères consécutives. Le HoF persiste →
sélection des meilleurs chasseurs à chaque palier.

## Résultat — 3 paliers grimpés, puis un mur révélateur

| Capacité proies | proies_moy | Statut |
|---|---|---|
| 30 (abondant) | 2.61 → 1.66 | ✅ maîtrisé |
| 20 | 1.62 → 1.21 | ✅ maîtrisé |
| 12 | 1.16 → 1.18 | ✅ maîtrisé |
| **6 (rare)** | plafonne ~0.65 (pic 1.03), 15 ères | ❌ **NON maîtrisé** |

> La population **grimpe l'axe Monde sur 3 crans** via les mastery gates (symétrie avec le Craft).
> Mais à la **rareté extrême** (6 proies / 30 agents), la **chasse simple plafonne** — la
> sélection seule ne passe pas le seuil en 15 ères.

## Conclusion — les deux axes s'imbriquent

Ce mur n'est pas un échec : c'est **le bon mur**. Quand le petit gibier est trop rare, la seule
issue énergétique est le **gros gibier** (Mammouth = 105 d'énergie, nourrit large) — qui exige une
**lance** (axe Craft, EDR 025) et le crit/stun pour survivre à la riposte (EDR 022/persistance).

> **La rareté du Monde crée la pression qui rend le Craft instrumentalement nécessaire.** Les axes
> Monde et Craft ne sont pas indépendants : leur *rencontre* est la chaîne moyens→fins de tout le
> projet (petit gibier rare → gros gibier nécessaire → lance requise → crafter). On a démontré
> qu'on sait grimper *chaque* axe ; l'étape suivante est leur **intégration**.

## Suites — le programme développemental intégré

- Curriculum **2D (Monde × Craft)** : à mesure que la rareté monte, ouvrir le craft (L0→…) et le
  crit pour que la population bascule de la chasse au petit gibier vers le gros gibier outillé.
- **Coopération** (EDR persistance) pour le gros gibier quand le crit s'efface.
- Le `CurriculumRunner` (déjà livré) pour orchestrer les deux axes conjointement.

## Variables d'expérience

Paliers de capacité, `mastery`/`patience`, couplage avec `craft_level` et `crit_base`, max_eras.
