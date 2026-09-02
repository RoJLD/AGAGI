# Cartographie des strates taxonomiques (2026-09-02, panel 5 lecteurs + synthèse)

Sortie du brainstorm « où en sommes-nous avec nos taxonomies ». Priorité fixée par l'utilisateur :
**science > méthodologie > savoir commun**. Décision : **C1 + C5 lancés le jour même ; C2/C3/C4 au
backlog** (bloc « Brainstorm taxonomies » de PRIORITES_ET_DETTES.md).

## Carte unifiée

| Strate | État | Preuve-pivot |
|---|---|---|
| Méthodologie | VIVANTE — 20 classes E1-E20 (15 exécutables), 115/116 calibrés, 5 cliquets ; 3 angles morts MESURÉS | 7 collisions → 10 définitions invisibles ; prereg-applied hors hook (P2.16) |
| Demande-modalités | SOLIDE AU CENTRE, ASYMÉTRIQUE — 1 seule modalité (perception) a un verdict in-world | S2-009 unique instanciation in-world du gabarit |
| Portes G0-G4 | G0 franchie, G1 active (verrou déplacé transfert→émergence), **G2 FANTÔME**, G3/G4 proxy | SDR-G2 : 0 outil, 0 test ; 19/19 records d'août-sept en `gate: G0` par défaut |
| AGI-Taxonomy | INFRA SAINE, CROISSANCE BLOQUÉE — 2 arêtes établies, 0 depuis fin juillet ; 2 négatifs bornés au régime d'optim (E19) | LANG→PERCEPTION 2.115, MEM→PERCEPTION 3.934 ; LANG-MEMORY caduc (P2.14) |
| Graphe de savoir | SOUS CLIQUET pour le neuf, AVEUGLE sur ses fondamentaux | EDR-114b invisible (`consolidate_records.py:32`) ; EDR-124/194 sans frontmatter |

## Trois convergences transversales

1. **Le même verrou porte trois noms** : « écriture APPRISE dans le report » (taxonomy,
   DELAYED-COORD) ≡ « émergence d'une compétence composée » (porte G1, EDR-156/157) ≡ « le régime
   de recherche est le verrou » (EVO-016). Aucun document ne l'unifie.
2. **Le biais absence→négatif opère encore** : les 2 négatifs taxonomy sont des comparaisons où la
   RÉFÉRENCE meurt aussi (E3/E19). Aucun point (lr, budget) connu où la référence apprend →
   re-mesurer avant de l'établir = regraver du bruit. C'est le prérequis C1.
3. **Les atomes sont gardés, les SYNTHÈSES non** : « 19 classes sur 19 » faux le jour d'E20 ;
   CLAUDE.md §Cliquets faux ; REF-DEMAND-MARKER arrêté à WARM-005. E10 sur la couche de lecture.

## Gaps (rangés, avec preuves)

**Scientifiques** — S1 : aucun régime connu où la référence apprend à petit lr (préalable à tout) ·
S2 : 3ᵉ arête language→memory redevenue mesurable (bilinéaire+lr levés) mais sonde pas à niveau
(`language_memory_demand_probe.py:134-137,143`) · S3 : aucune ablation de demande IN-WORLD hors
perception · S4 : EVO-011 scellé jamais lancé (3 défauts localisés) · S5 : pas G4 dé-risqué dormant
(fix persistance 1 ligne + g bilinéaire) · S6 : moitié « nécessité » de S2-006 jamais re-mesurée
avec cellules capables d'échouer · S7 : nœud generalization orphelin d'arêtes.

**Structurels** — T1 : G2 fantôme + gate:G0 par défaut · T2 : 114b invisible, 124/194 sans
frontmatter, 94 gate_non_raccordés hors cliquet · T3 : couche de lecture périmée (backlog 992
lignes, README EDR faux, REF-DEMAND-MARKER contredit S2-012/013) · T4 : EVO-022 scellé sans record
(tiroir à résultats).

**Méthodologiques** — M1 : prereg-applied hors hook · M2 : aucun garde-fou sur les chiffres publiés
(pas de recompute contre l'artefact-source) · M3 : 10 définitions invisibles (collisions) + registre
CALIBRATED mono-fichier · M4 : porte taxonomy ne lit jamais coord_intact ET barre 1/K+0.15 sous le
plafond 0.3889 du plain (P2.15) · M5 : les synthèses n'ont aucun garde de cohérence · M6 : E8 à 2
occurrences en `documenté` (3ᵉ interdite) · M7 : rétro-application des 27 records « à EXAMINER »
jamais faite (S2-009 risque 4).

## Candidats et décision

- **C1 (LANCÉ)** : établir le point où la référence APPREND (balayage lr×budget, ~13 min/point),
  puis mettre la sonde à niveau et rejouer la 3ᵉ arête language→memory sous règle scellée.
- **C5 (LANCÉ)** : M1 (hook) + M4 (coord_intact + contre-exemple) + M6 (promotion E8) — trois
  gardes de classes déjà tombées, ≤ 1 h.
- **C3 (BACKLOG)** : sceller SDR-G2, re-tagger ~5 records compositionnels, warning gate↔tests.
- **C4 (BACKLOG)** : resynchronisation couche de lecture + trancher le cliquet des synthèses (M5).
- **C2 (BACKLOG)** : réparer harnais EVO-011 + pré-vol décisif (lecteur câblé main).
- **En travers (avec C1)** : record court unifiant « les trois noms du même verrou ».
