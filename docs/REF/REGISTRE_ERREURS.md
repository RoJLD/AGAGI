---
id: REF-REGISTRE-ERREURS
type: REF
title: "Registre vivant des classes d'erreur — chaque erreur trouvée doit y atterrir avec sa garde"
status: active
---

## Pourquoi ce registre existe

Quand une revue trouve une erreur, elle est corrigée et racontée dans un record. **Rien ne garantit
qu'elle devienne une garde.** Conséquence mesurée sur l'arc WARM-005→009 : la même classe d'erreur est
revenue **trois fois** — généraliser depuis `agents[0]`, puis depuis trois cas saillants, puis d'une
population à une autre — dont une fois **dans le record qui la dénonçait**.

Le cliquet de `check_instrument_calibration.py` résout ce problème pour les **instruments**. Ce registre
est l'équivalent pour les **classes d'erreur**.

## Rituel (obligatoire)

Toute erreur trouvée en revue, ou tout run nul/contaminé, doit :
1. être **rattachée** à une classe existante, ou en créer une ;
2. recevoir un statut de garde : **`exécutable`** · **`documenté`** · **`non automatisable`** ;
3. si `exécutable` → la garde est écrite ET testée dans la même passe ;
4. si `non automatisable` → le dire explicitement (c'est ce qui justifie l'obligation de revue).

Une erreur qui repasse deux fois avec un statut `documenté` doit être **promue** en `exécutable` ou
reclassée `non automatisable`. Pas de troisième occurrence tolérée sans changement de statut.

---

## Registre

| # | Classe d'erreur | Occurrences (arc WARM-005→009) | Statut | Garde |
|---|---|---|---|---|
| **E1** | **Contrôle qui ne peut pas ÉCHOUER** (no-op analytique présenté comme contrôle négatif) | contrôle négatif tautologique : 6/8 tableaux bit-identiques, rapporté comme `wins 2/48` | `exécutable` | `assert_ablation_changes_something` |
| **E2** | **Bras qui ne peut pas RÉUSSIR** (l'issue cherchée est structurellement inatteignable) | WARM-009 : bras « production » dans un monde n'engendrant **aucun** `Fruit` | `exécutable` | `assert_positive_control` |
| **E3** | **Métrique dégénérée** (plancher/plafond) lue comme « pas d'effet » | 24 génomes tous à 6.0-7.2 ticks ; 32/48 déjà à `move_acc = 1.000` ; **WARM-002 (occurrence ANTÉRIEURE, trouvée le 2026-07-21)** : ratio ≈ 1.00 lu sur un bras intact à 5.0-7.2 ticks, soit **SOUS** le plancher no-perception (9.0) → verdict `PAYSAGE PLAT` sur le MONDE, réfuté par WARM-010 | `exécutable` | `assert_not_degenerate` — ⚠️ **mais rien ne la RÉTRO-APPLIQUE aux records déjà gravés** (trou du cliquet, cf. E14) |
| **E4** | **Vérification vide** (« 0 échec » indiscernable d'un succès) | `pytest -k` désélectionnant les 1034 tests, lu comme non-régression validée | `exécutable` | `assert_selection_nonempty` |
| **E5** | **Aliasing mémoire** — écrire dans une sortie mute l'état interne | `forward` renvoie une VUE de `H` : clamper les logits épinglait le neurone 88 | `exécutable` | `assert_no_aliasing` + cas de calibration |
| **E6** | **Prédicteur mesuré hors du contexte où l'intervention opère** | taux de grab mesuré sur trajectoire oracle vs comportement in-world (ρ 0.33 vs 0.53) | `exécutable` | `assert_predictor_measured_in_situ` |
| **E7** | **Mauvaise unité de réplication** (pseudo-réplication) | `sign_p = 1.5e-05` sur 16 agents partageant entraînement, optimiseur et mondes → n réel = 2 | `documenté` | `declare_design(replication_unit=…)` — la déclaration rend le conflit visible, elle ne le détecte pas |
| **E8** | **Inférence substituée à la mesure** pour économiser du calcul | WARM-008 : maillon final inféré (~7 h économisées) ; mesuré **NUL** par la revue en 28 min. **WARM-002** : seuil « ~99 % d'accuracy » importé de WARM-001 (`cf. WARM-001`) — autre grandeur, autre population ; mesuré FAUX (récompense dès p=0.25). Le contrôle qui manquait coûtait **6 secondes** | `documenté` | `declare_design(links={…: "inferred"})` lève un avertissement |
| **E9** | **Généralisation depuis un échantillon saillant** | `agents[0]` (×2), « 3 cas » érigés en propriété d'instrument, une population → toutes | **`non automatisable`** | **Revue adversariale obligatoire** — c'est la classe qui justifie le dispositif |
| **E10** | **Règle documentée sans application exécutable** | contention KuzuDB (moi, ×2) ; `memory_retriever` actif pendant la sim (code d'instrument) ; état global non nettoyé (suite de tests) | `exécutable` | `tools/sim_session.py` (verrou de processus + isolation garantie) |
| **E11** | **Choix d'analyse post-hoc** (jardin aux sentiers qui bifurquent) | seuil 0.5 sur `gi`, partition FRÉQUENT/RARE, choix du prédicteur — tous arrêtés après avoir vu les données | ⚠️ **AUCUNE** | *à faire* : pré-enregistrement dans `declare_design` (P3.1) |
| **E12** | **Extrapolation depuis un préfixe court** | tendance du grab lue sur 200 epochs — c'était la branche montante d'un transitoire | `documenté` | `CLAUDE.md` §Coût des runs |
| **E13** | **Dépassement de coût non borné au design** | 3 runs abandonnés (8 h, 4 h, 89 min) + 1 run de 1,8 h sur une question sans objet | ⚠️ **AUCUNE** | *à faire* : budget mesuré au smoke, obligatoire (P3.2) |
| **E15** | **Statistique de POPULATION comparée entre populations de compositions différentes** — la métrique n'est pas dégénérée, elle est CONFONDUE | EDR-095 : le rêve forcé multiplie `n_lived` par **13-16** ; la survie médiane sur TOUS les agents chute de 55 % (`sign_p` 0.0005, reproduit) alors que sur la cohorte fondatrice appariée l'effet est **ABSENT** (8/12). L'indice — le `n_lived` ×16 — était publié **dans le record**, en « effet secondaire » | `documenté` | **Vérifier `n` PAR BRAS avant de comparer des médianes.** ⚠️ Aucune garde de borne ne voit ça : aucun bras n'est au plancher ni au plafond. Une médiane est robuste aux valeurs extrêmes, **pas à un changement de population** |
| **E14** | **Garde exécutable jamais RÉTRO-APPLIQUÉE** — le cliquet protège le travail à venir, pas les conclusions déjà gravées, qui continuent d'être citées | `assert_not_degenerate` existait quand WARM-002 a été relu ×N ; personne ne l'a pointée sur son bras à 5.0-7.2 ticks. Le verdict « paysage PLAT » a alimenté 4 records pendant ce temps | `exécutable` **(triage seul)** | `tools/retro_audit_records.py` — signale `verdict NUL × conclusion sur le MONDE × plancher avoué`. ⚠️ **La partie jugement N'EST PAS automatisable** : voir ci-dessous |

---

## Lecture du registre

- **9 classes sur 14 ont une garde exécutable ou documentée** ; 3 n'en ont aucune (E11, E13, E14) et sont
  inscrites au backlog ; 1 est explicitement non automatisable (E9).
- **E9 est la plus coûteuse et la seule irréductible** : trois occurrences, aucune détectable par du code.
  C'est elle, et elle seule, qui justifie que la revue adversariale soit une **obligation** et non un confort.
- **E10 est la plus instructive** : la règle existait, écrite depuis longtemps, et a été violée par trois
  acteurs différents en une journée — moi, le code d'instrument, la suite de tests. **Toute règle
  documentée sans application exécutable finit violée.**
- **E14 est la plus inquiétante, et c'est la nouvelle du 2026-07-21.** E3 avait déjà une garde
  `exécutable` quand WARM-002 a été gravé, cité et propagé. La garde n'a rien attrapé parce qu'**un
  cliquet ne regarde jamais en arrière** : il bloque le prochain instrument non calibré, il ne relit pas
  les verdicts publiés. Corollaire : le nombre de classes « couvertes » **surestime** la protection réelle
  tant que le stock de conclusions actives n'a pas été repassé au crible.
- **La garde d'E14 est délibérément PARTIELLE, et c'est un résultat, pas un renoncement.** Le signal qu'on
  voulait automatiser — « verdict nul publié SANS contrôle positif » — a **échoué deux fois** sa
  calibration sur l'archétype : le mot `oracle` apparaît dans WARM-002 en cadrage (`## Question`) puis en
  valeur citée (`oracle intact ≈ 200 (S2-009)`), sans qu'aucun contrôle ait été lancé. **Distinguer « a
  lancé un contrôle positif » de « cite un contrôle fait ailleurs » exige de comprendre la phrase, pas de
  la matcher.** Le code énumère et priorise (`verdict NUL × portée MONDE × plancher avoué`, calibré sur
  l'archétype) ; le jugement tranche — même partage que E9. Continuer à raffiner les motifs sur l'unique
  exemple disponible aurait été de la classe **E11**. Les deux échecs sont figés en régression dans
  `tests/sandbox/test_retro_audit.py`.

Cf. [`REF-EXPERIMENT-PREFLIGHT.md`](REF-EXPERIMENT-PREFLIGHT.md) (les 4 générateurs) ·
[`../roadmap/PRIORITES_ET_DETTES.md`](../roadmap/PRIORITES_ET_DETTES.md) (P3 : E11 et E13) ·
`tools/experiment_preflight.py` · `tools/sim_session.py` · `tools/check_instrument_calibration.py`
