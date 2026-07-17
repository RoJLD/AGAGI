# Records EDR — convention d'ID et règle de raccordement

Ce dossier contient les **EDR** (Experiment Decision Records). Le graphe de décision est consolidé par
`tools/consolidate_records.py` (SDR→EDR→ADR + ponts REF) et vérifié par `tools/check_record_links.py`.

## Convention d'ID (canonique, 2026-07-15)

- **Nouveaux records = préfixe THÉMATIQUE** aligné sur l'axe (`LANG-`, `PLAN-`, `MEM-`, `S2-`, `CURR-`…) ou
  sur la porte (`G1-`, `G2-`…), numérotés par famille (`LANG-001`, `LANG-002`, …).
  → Fini la numérotation séquentielle globale `NNN_` : c'était la source des **collisions d'id** entre sessions
  parallèles (deux fichiers `093_…`, `135_…`, etc.).
- **Legacy numérique `NNN_` = gelé** (pas de renumérotation de masse). Seules les 5 collisions existantes
  (093/094/100/105/135) sont à résoudre ponctuellement (voir `docs/roadmap/RECORDS_HYGIENE_AND_GATES.md`, P1).

## Règle de raccordement — AUCUN ORPHELIN

Tout record doit être **raccordé** au graphe. Frontmatter YAML minimal requis :

```yaml
---
id: <PREFIX-NNN | EDR-NNN>
type: EDR
title: "…"                 # QUOTER (les ':' non quotés cassent le YAML — cf. bug de 122)
status: <accepted|validated|legacy|open>
gate: <G0|G1|G2|G3|G4|foundational>   # OU tests:[SDR-Gx] OU adoption par une REF
verdict: <CONSTANTE_MAJUSCULE>         # optionnel mais recommandé
---
```

Un record est raccordé s'il porte `gate:` (G0-G4 ou `foundational`), **ou** `tests: [SDR-Gx]`, **ou** est
adopté par une REF (`adopt_for`). `foundational` = infra / NAS / architecture / règle d'apprentissage /
méthodologie qui n'appartient légitimement à aucune porte G0-G4.

### Automatisme (ratchet)

Le hook `tools/hooks/pre-commit` (à installer : `cp tools/hooks/pre-commit .git/hooks/ && chmod +x
.git/hooks/pre-commit`) **bloque tout commit introduisant un nouvel orphelin ou une nouvelle collision d'id**,
scopé aux fichiers stagés. La dette légataire est gelée dans `tools/record_link_baseline.json` ; seuls les
NOUVEAUX cas échouent. Bypass d'urgence : `git commit --no-verify`.

Vérifier à tout moment : `python tools/check_record_links.py --report`.

## Dette légataire (dé-orphanisation en cours, P3)

Les EDR `001–104` étaient en prose libre sans frontmatter → invisibles au graphe (orphelins). Ils sont
dé-orphanisés par **vagues** (frontmatter minimal rétro-ajouté, corps d'origine inchangé, mappé par topic →
porte ou `foundational`) :

- **Vague 1 (2026-07-15) : EDR 001–030 faits** (29 records) → orphelins 109 → 80 ; couverture G2 : 0 → 8.
- Vagues suivantes : 031→104 restants. Voir `docs/roadmap/RECORDS_HYGIENE_AND_GATES.md`.

Un frontmatter rétro-ajouté porte `status: legacy` + un commentaire de traçabilité.
