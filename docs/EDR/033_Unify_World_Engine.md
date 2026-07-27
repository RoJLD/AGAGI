---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-033
type: EDR
title: "Unifier le moteur des mondes (axe Monde) — collision de nom résolue"
status: legacy
gate: foundational
---

# EDR 033 : Unifier le moteur des mondes (axe Monde) — collision de nom résolue

## Contexte — Vague 1 #5, recadré

Item initial : « supprimer le doublon world_0 et le stub world_3 ». **Recadrage de l'utilisateur**
(EDR 031) : les mondes Soup→Stoneage→Agri→Industrial **sont l'axe Monde** de l'ontogénèse, pas
des doublons. Donc : *garder l'axe, unifier le moteur*.

## Carte d'héritage (constat)

| Monde | Classe | État |
|---|---|---|
| `world_1_stoneage` | `Biosphere3D` (1279 l.) | ✅ **moteur canonique** |
| `world_2_agricultural` | `AgriculturalWorld(Biosphere3D)` | ✅ stade propre (saisons) |
| `world_3_industrial` | `IndustrialWorld(Biosphere3D)` | ✅ stade propre (pollution) |
| `world_0_soup` | **`Biosphere3D`** (680 l., V13) | ❌ **2ᵉ classe du même nom** (collision !), API legacy, orphelin de `main` |

Le vrai problème était **isolé** : `world_0_soup` portait une *seconde* `class Biosphere3D`
(moteur V13 historique, API `add_agent(genome)` différente), créant une **collision de nom**
dangereuse avec le canonique. Seul `tests/test_fixes.py` l'utilisait encore.

## Décision (V18.20)

- **Renommer** le legacy : `class Biosphere3D` → `class SoupWorldLegacyV13` dans `world_0_soup.py`
  (collision résolue ; conservé pour le test legacy, marqué « ne plus utiliser »).
- **Créer le vrai stade 0** : `class SoupWorld(Biosphere3D)` — hérite du moteur canonique,
  sensorimoteur (homéostasie, approche/évitement) : ni matériaux de craft, ni gibier qui riposte.
- **Câbler** `"soup"` dans le mapping `WORLD_TYPE` de `main_biosphere`.
- `tests/test_fixes.py` : import mis à jour (`SoupWorldLegacyV13 as World0`).

## Résultat

> **Les 4 stades de l'axe Monde héritent désormais d'UN seul moteur canonique** :
> `SoupWorld` · `Biosphere3D` (stoneage) · `AgriculturalWorld` · `IndustrialWorld`. Toute
> réparation du moteur (apprentissage, combat, coop…) se propage à tous les stades.

- `SoupWorld` : hérite ✅, sensorimoteur (0 matériau, 0 gibier dangereux), smoke 30 ticks OK.
- Collision de nom éliminée ; legacy préservé (renommé). **109 tests verts**, `test_fixes` passe.

## Suites

- **Étoffer** `SoupWorld` / `AgriculturalWorld` / `IndustrialWorld` comme vrais stades cognitifs
  (sensorimoteur → planification → abstraction) — l'axe Monde de la famille B.
- À terme, retirer le moteur `SoupWorldLegacyV13` quand le test legacy sera porté sur le canonique.

## Variables d'expérience

Contenu de chaque stade (prey/ressources/saisons), métriques de maîtrise par stade (Soup : survie
médiane ; Agri : horizon de planification ; Industrial : coopération/chaînes).
