# docs/REF — Nœuds SOTA (références externes) du graphe records

Ces fichiers ajoutent l'**état de l'art** comme nœuds de première classe dans le graphe
consolidé (`tools/consolidate_records.py` → `results/records_graph.json`), à côté des
SDR/EDR/ADR. But : répondre par **requête de graphe** à « réinvente-t-on la roue ? » et
ancrer chaque nouvelle piste dans la littérature (procédure anti-réinvention).

## Convention

Un nœud `REF` est un `.md` à frontmatter YAML :

```yaml
---
id: REF-<SLUG>-<ANNEE>      # ex: REF-NEAT-2002
type: REF
title: <titre du papier / méthode>
url: <doi ou lien>
method: <mécanisme en une ligne>
lib: <lib SOTA maintenue, si applicable>
maturity: production | research | prototype
# arêtes-pont (toutes émanent du REF → on ne touche PAS les EDR/SDR/ADR) :
rediscovered_by: [EDR-NNN]  # notre EDR a redécouvert ce résultat établi
supersedes:      [EDR-NNN]  # le SOTA dépasse notre mécanisme maison
adopt_for:       [EDR-NNN, ADR-NNN]  # à adopter pour lever ce verrou (plan de migration)
grounds:         [SDR-Gx]   # cette porte devrait s'appuyer sur ce SOTA
---
```

Arêtes générées : `REDECOUVERT_PAR`, `DEPASSE`, `A_ADOPTER_POUR`, `FONDE`.

## Règle (procédure anti-réinvention)

Avant tout nouvel « organe » cognitif : SOTA-scan → créer ≥1 `REF` → décision build-vs-adopt
→ wrapper non-régressif. `consolidate_records.py` échoue sur lien-pont cassé (anti-théâtre).
Voir la synthèse d'audit 2026-06-29 (mémoire `sota-gap-substrate`).
