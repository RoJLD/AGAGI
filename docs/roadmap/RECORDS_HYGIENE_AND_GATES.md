# Plan — hygiène du graphe de records + consolidation des portes (daté 2026-07-15)

Backlog exécutable et priorisé pour : (a) empêcher tout futur orphelin (LIVRÉ), (b) clore la dette d'hygiène
existante, (c) équilibrer/consolider les 5 portes G0→G4, (d) canoniser la convention d'ID. Chiffres issus de
`tools/consolidate_records.py` + `tools/check_record_links.py --report` au 2026-07-15.

## 0. État actuel (chiffré)

- Graphe : **188 records** (169 EDR, 11 REF, 5 SDR, 3 ADR), 73 arêtes. `problemes=0` (consolidate).
- **109 orphelins** (EDR/ADR sans porte ni arête) = les EDR légataires 001–104 en prose libre (sans frontmatter) + `ADR-002`.
- **5 collisions d'id** : `EDR-093, 094, 100, 105, 135` (deux fichiers distincts par numéro — artefacts de renumérotation entre sessions //).
- **158 EDR non raccordés à une porte** (pas de `gate:` ni `tests: [SDR-Gx]`).
- Couverture des portes très déséquilibrée : G1=6 preuves, G0=3, G3=1, G4=1, **G2=0**.
- 1 record à frontmatter YAML cassé : `122_...Legacy.md` (`title:` non quoté avec `:`).

## 1. Règle anti-orphelin — LIVRÉE ✅

Mécanisme à cliquet (ratchet) : la dette légataire est **gelée**, mais aucun NOUVEL orphelin/collision ne peut entrer.

- `tools/check_record_links.py` — détecte orphelins (record sans `gate:` ni arête) + collisions d'id. Modes :
  `--report` (état complet), `--update-baseline` (gèle la dette), défaut = ratchet (exit 1 sur tout nouveau cas).
- `tools/record_link_baseline.json` — dette légataire gelée (109 orphelins + 5 collisions), versionnée (results/ est gitignored).
- `tools/hooks/pre-commit` (installé dans `.git/hooks/`) — bloque un commit qui introduit un nouvel orphelin,
  **scopé aux fichiers stagés** (ne bloque jamais sur le travail non-committé d'une session //). Bypass d'urgence :
  `git commit --no-verify`. Réinstaller : `cp tools/hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`.
- **Règle** : tout nouveau record DOIT porter `gate: Gx` et/ou `tests: [SDR-Gx]`, OU être adopté par une REF
  (`adopt_for`), OU (foundational/infra/NAS sans porte) porter `gate: foundational`
  *(à ajouter à la liste des ancres tolérées dans le validateur si adopté — voir P4)*.

## 2. Dette d'hygiène — clôture priorisée

### P1 — Résoudre les 5 collisions d'id (BORNÉ, nécessite l'aval de robla)
Chaque numéro porte deux EDR distincts. Garder le plus « central » sur le numéro, renuméroter l'autre vers un
numéro libre. Numéros libres disponibles : **106, 107, 110, 114, 123, 124, 127, 128, 131, 132, 133, 136, 142**.
Proposition (à valider — le choix du jumeau à déplacer + la mise à jour des références sont sensibles) :

| id collidé | fichier A | fichier B | action proposée |
|---|---|---|---|
| EDR-093 | No_Income_Rung… | Planning_Organ_Not_Dead… | déplacer B → EDR-106 |
| EDR-094 | Dream_Distress… | Intrinsic_Wall… | déplacer A → EDR-107 |
| EDR-100 | Biology_Drain… | Champion_Deficit_Monoculture… | déplacer B → EDR-110 |
| EDR-105 | Forage_Bottleneck… | Topological_Growth… | déplacer A → EDR-114 |
| EDR-135 | Anticipation_G_Inert… | LegacyCore_Control… | déplacer B → EDR-123 |

⚠️ **Risque** : ces fichiers sont //-authored ; renuméroter suppose de tracer et corriger les références
(mémoire, autres EDR, PR). NE PAS exécuter unilatéralement — décision robla + un balayage de références.
Après résolution : retirer les ids du baseline collisions et re-`--update-baseline`.

### P2 — Réparer le YAML cassé de `122_...Legacy.md` (TRIVIAL, coordination //)
Le `title:` contient `SPLIT par substrat : DISCOVERY…` (`:` non quoté → ScannerError). Fix = quoter la valeur.
//-authored → à faire par la session propriétaire ou robla. Impact : supprime le WARN récurrent de consolidate.

### P3 — Dé-orphaniser les 109 légataires (GROS chantier, par vagues)
Les EDR 001–104 sont en prose libre sans frontmatter → invisibles au graphe. Méthode proposée (vagues revues) :
1. **Script assisté** : ajouter un frontmatter minimal (`id`, `type: EDR`, `gate:` OU `gate: foundational`,
   `verdict:` si extractible) à chaque légataire, mappé par TOPIC (survie/craft → G0/G2 ; langage → G3 ;
   NAS/substrat/infra → `foundational`). Le mapping topic→gate se déduit du titre + première section.
2. **Vagues de ~20**, chacune committée path-scopée + revue, en décrémentant le baseline à chaque vague
   (`--update-baseline`), jusqu'à baseline vide.
3. Beaucoup de légataires (NAS, infra, méthodo) n'appartiennent à AUCUNE porte → `gate: foundational` est
   légitime (tout n'est pas G0-G4). D'où P4.

⚠️ Touche 100+ fichiers //-legacy → exécuter en vagues courtes, avec l'aval de robla, jamais en bloc.

### P4 — Canoniser la convention d'ID (DÉCISION + application)
Deux schémas coexistent (numérique `NNN_` legacy vs préfixes thématiques `LANG-/PLAN-/S2-/G1-/MEM-/CURR-`).
Décision proposée :
- **Nouveaux records = préfixe THÉMATIQUE** aligné sur l'axe (LANG-, PLAN-, MEM-, S2-…) OU sur la porte
  (G1-, G2-…), + `gate:`/`tests:`. Fini les numéros séquentiels (source des collisions //).
- **Legacy numérique = gelé** (pas de renumérotation de masse, sauf les 5 collisions P1).
- Ajouter `gate: foundational` comme ancre tolérée dans `check_record_links.py` (`_GATES` + `("foundational",)`)
  pour que P3 puisse dé-orphaniser l'infra/NAS sans forcer un rattachement artificiel à une porte.
- Documenter la règle dans le README de `docs/EDR/` (à créer) + la spec des records.

## 3. Consolidation des portes + gaps de recherche

Rappel objectif north-star : généralisation zéro-shot (`transfer_ratio`), décomposée en 5 portes. État : **1
seule franchie in-world (G0)** ; le reste est dé-risqué EN PROXY mais non franchi in-world. Le méta-gap dominant
est le **pont proxy → in-world** (≈80-90 % des résultats forts sont en isolation ; les tests in-world sont
presque tous NEUTRES).

| Porte | État | Preuves | Gap → action prioritaire |
|---|---|---|---|
| **G0** exige ? | ✅ validée | 3 (112/118 + S2-001) | Consolider : câbler le bras d'**ablation-perception** dans `s2_demand` (S2-001 → verdict CAUSAL in-world). |
| **G1** généralise ? | 🟠 ouverte | 6 | Lancer `transfer_ratio` À L'ÉCHELLE (jamais fait) ; tester l'entraînement **multi-mondes** (G1-001 : mono-monde = artefact). |
| **G2** compose ? | ⚪ 0 preuve | 0 | **Priorité d'instrumentation** : créer l'outil G2 (émergence d'une chaîne non récompensée). ⚠️ recoupe COS (//) — coordonner. |
| **G3** langage paie ? | 🔵 proxy | 1 (LANG-006) | Câbler une **asymétrie d'info survivable** in-world (087) + ablation-canal ; co-évoluer l'usage (083). |
| **G4** anticipe ? | 🟠 proxy | 1 (EDR-135) | Porter un **forward-model bilinéaire** (PLAN-001→004) dans la boucle ; « vrai planning » in-world. |

**Actions de consolidation transverses :**
1. **Pont proxy→in-world** (méta-gap #1) — pour chaque capacité dé-risquée en proxy (binding, langage, mémoire,
   généralisation, anticipation), définir la DEMANDE in-world correspondante + le bras d'ablation within-subject
   ([[within-subject-demand-marker]]) comme KPI causal (pas la survie brute). C'est le chantier central.
2. **G2 = trou béant** — aucune instrumentation. À ouvrir (coordonner avec la ligne COS/craft //).
3. **G3/G4 sous-alimentées** — 1 preuve chacune ; porter les proxies (LANG/PLAN) vers un test in-world ciblé.
4. **Migration moteur** (numpy→torch/Dreamer) — cartographiée, exécutable flag-OFF, prérequis du pont in-world.

## 4. Priorisation globale (ordre d'exécution)

1. **[FAIT] Règle anti-orphelin** (validateur + baseline + hook). ✅
2. **P4 canoniser la convention d'ID** (décision + `gate: foundational` dans le validateur) — débloque P3, bon marché.
3. **P1 collisions (5)** — borné, mais **aval robla + balayage de références** requis.
4. **P3 dé-orphaniser** par vagues de ~20 (après P4) — gros mais mécanique.
5. **P2 réparer 122** — trivial, coordination //.
6. **Consolidation portes** : (a) G0 ablation-perception in-world, (b) G1 `transfer_ratio` à l'échelle,
   (c) ouvrir G2, (d) porter G3/G4 in-world — subordonnés au **pont proxy→in-world** et à la migration moteur.

> Note : les items touchant le legacy //-authored (P1, P2, P3) exigent l'aval de robla / une coordination
> inter-sessions (arbre partagé). Le reste (règle anti-orphelin, P4, consolidation via nouveaux proxies) est
> exécutable côté « mon poste » sans collision.

## Journal d'exécution

- **2026-07-15** — Règle anti-orphelin LIVRÉE (validateur + baseline + hook, commit 3158c47).
- **2026-07-15** — **P4 FAIT** : convention d'ID canonisée dans `docs/EDR/README.md` (nouveaux = préfixe
  thématique ; legacy gelé ; ancre `foundational`).
- **2026-07-15** — **P3 vague 1 FAITE** : EDR **001–030** dé-orphanisés (29 records, frontmatter rétro-ajouté,
  corps inchangé, `status: legacy`). Orphelins **109 → 80**. Couverture des portes : **G0 3→5, G2 0→8**
  (la porte la plus vide est amorcée). Baseline rétréci à 80.
- **2026-07-15** — **P3 vague 2 FAITE** : EDR **031–059** dé-orphanisés (28 records, 047 déjà lié). Orphelins
  **80 → 52**. Couverture : **G3 1→14** (la 2ᵉ porte la plus vide, le fil langage historique était orphelin).
  Baseline rétréci à 52.
- **2026-07-15** — **P3 vague 3 FAITE : legacy-mien TERMINÉ.** EDR **060–104** dé-orphanisés (33 records ;
  093/094/100 exclus = collisions P1). Orphelins **52 → 19**. Couverture : **G1 6→9, G2 8→11, G3 14→23,
  G4 1→2** (G4 peu boosté car ses EDR planning 093/094 sont justement des collisions bloquées P1).
  **Portes finales : G0=5, G1=9, G2=11, G3=23, G4=2.** Baseline rétréci à 19.
  → **Bilan P3 : 90 des 109 orphelins d'origine nettoyés (→19).** Les **19 restants sont HORS de mon
  périmètre** : 6 fichiers de collision (093/094/100, → P1/robla), 12 EDR récents //-authored (109/113/117/
  119/120/122/125/163/166/169/171/172 → leurs sessions propriétaires), 1 ADR (ADR-002). Le legacy prose
  001-104 (le mien) est intégralement raccordé.
