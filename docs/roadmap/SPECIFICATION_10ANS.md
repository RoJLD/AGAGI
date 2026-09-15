# Spécification long-horizon — ce que 232 records ferment, imposent, et laissent ouvert

> ⚠️ **DOCUMENT ARCHIVÉ DE FAIT (2026-09-14).** Écrit le 2026-07-21 sous la condition « 1 instrument
> calibré sur 71 » ; la dette de calibration est CLOSE depuis le 2026-09-01 (baseline à zéro) et les
> quatre paris de la §3 sont **tranchés** dans [`PRIORITES_ET_DETTES.md`](PRIORITES_ET_DETTES.md),
> bloc « 🧭 2026-09-14 » : A mal posé (la PORTÉE de l'optimiseur décide), B → mémoire / écriture,
> C mesuré par le run P4.4, D périmé (la métrique de verdict existe et est calibrée). La §2 reste
> conditionnelle à P1.6 : l'apprenant in-world qui fonde « verrou = crédit » n'a pas encore de contrôle
> positif. Le document vivant est [`FIL_DIRECTEUR_AGI.md`](FIL_DIRECTEUR_AGI.md).
> *(Bandeau d'origine : « CONDITIONNEL À LA CALIBRATION (P2.1) … Calibrer avant de s'engager. »)*

> ⚠️ **COMPLÉMENT du 2026-09-15 (P3.6) — la condition « §2 conditionnelle à P1.6 » est LEVÉE par la
> mesure, et la §2 en sort BORNÉE, pas confirmée.** (1) L'apprenant in-world a désormais un contrôle
> positif (oracle câblé à 1,000) et une référence appariée (`lr = 0`, 0,126 = chance) DANS son propre
> dispositif, et il APPREND quand la mort ne borne plus sa dose : 12/12 seeds, +0,156, lentement (0,28 à
> 2000 ticks), écart résiduel invariant au pas (E19) — [[EDR-CALIB-LEARNER]]. Les nuls « verrou =
> crédit » de S2-009/010/011 étaient des nuls de DOSE (≈ 48 mises à jour par agent,
> [[EDR-S2-CREDIT-RETENTION]]) ; le verrou change de nom : l'apprenant meurt ~100× plus qu'un
> non-apprenant (126 résurrections par seed contre 1). (2) La contrainte 6 de la §2 (« bassin pré-formé
> pour franchir la barrière de bootstrap ») est mesurée in-world et n'est que NÉCESSAIRE : le bassin
> DAgger de [[EDR-WARM-003]] transfère (36,0 à poids gelés) et le crédit publié l'EFFACE (36,0 → 8,0,
> 12/12 seeds, `ERODE`) sans rien construire à froid (7,5 < 9,0) — [[EDR-S2-CREDIT-RETENTION]] ;
> l'érosion est PLEINE à Δénergie seule (−28,5 vs −28,25, différence appariée 0,0) et la curiosité de la
> récompense in-world est MORTE sous torch depuis S2-009 — [[EDR-S2-REWARD-ABLATION]]. Le pari C (§3)
> est tranché dans son sens défavorable : « warm-start + ce crédit » est une érosion à dose contrôlée,
> quelle que soit la récompense. (3) La §4 (« à réviser après P2.1 ») et la §5, point 1 : P2.1 est CLOSE
> (2026-09-01, cliquet strict, baseline à zéro ; le « 1 sur 71 » du bandeau d'origine ne décrit plus
> rien — état recomputé dans `CLAUDE.md`, § Calibration), et l'instrument d'ablation within-subject
> (`run_ablation_map`, qui porte les verdicts `X_DEMANDED` / `X_DECOY`) a un plancher de bruit MESURÉ de
> ±6-8 % (no-op exact, [[EDR-S2-BLIND-CHAMPION]]) : `X_DECOY` se lit « rien de détectable au-dessus de
> 8 % ». Tout contraste ENTRE sujets à `W` édité compare des corps avant des politiques (classe E26,
> `assert_phenotype_matched`, P1.7) ; `champion_body` (§2) n'édite pas `W`, il n'est pas concerné.
> Rien ici ne rouvre les directions fermées de la §1.

État au 2026-07-21 : 232 records EDR, 85 rattachés à une porte (G0 30 · G1 17 · G2 12 · G3 23 · **G4 3**).
Chiffre directeur : **proxy 9 / in-world 0** — neuf capacités démontrées en banc, aucune in-world.

---

## 1. Ce que les résultats FERMENT

Directions réfutées par mesure, à ne pas rouvrir sans élément nouveau.

| Direction | Verdict | Preuve |
|---|---|---|
| « Migrer vers torch/SOTA débloquera le substrat » | **RÉFUTÉ** | EDR-200 : le même réseau 12-cachés binde et survit 1.000 sous le bon régime de crédit. Le verrou n'était pas la capacité. |
| « Durcir le monde fait émerger l'intelligence » | **RÉFUTÉ** | EDR-090 (curriculum de létalité, négatif profond) ; famine durcie → aucune spécialisation. On rendait la survie plus dure, pas plus cognitive. |
| « La profondeur de planification ne marche pas » | **RÉHABILITÉ** | PLAN-001/003 : c'était le **modèle linéaire**, pas la profondeur. Un `g` bilinéaire débloque le planning zéro-shot (fidélité 13.3×). |
| « L'architecture (têtes disjointes) est le levier » | **RÉFUTÉ** | EDR-194 : le gain vient de l'**équilibrage du crédit sur le tronc partagé**, pas de l'isolation ; `LR_CLOSES` bat disjoint. |
| « La mémoire est incapable » | **RÉFUTÉ** | MEM-001 : elle **peut** payer (ablation within-subject, ×6-8) ; elle ne paie pas in-world parce que les tâches n'exigent aucun rappel. |
| « Le transfert cross-world = généralisation » | **ARTEFACT** | G1-001 : c'était un noyau de survie partagé, artefact de l'entraînement **mono-monde**. |
| « Le rêve / MCTS aide » | **RÉFUTÉ, nuisible** | EDR-095 : forcer le rêve **réduit** la survie (10/10, sign_p 0.002). |
| `transfer_ratio` comme métrique | **DÉGÉNÉRÉE** | Tous les mondes plafonnent sous le plancher → ratio ≡ 1.0. |

**Le fil commun** : à chaque fois, le verrou supposé était la **capacité** (substrat, architecture, profondeur, mémoire) ; à chaque fois, la mesure a montré que le verrou était le **régime de crédit** ou la **structure de tâche**.

---

## 2. Ce que les résultats IMPOSENT — une spécification, pas une liste d'échecs

Le finding dominant, et le plus dérangeant :

> **S2 cognition-vs-corps — verdict BODY unanime sur 5 mondes.** Le `champion_body` (génome du champion,
> actions **ALÉATOIRES**) survit ~4× le plancher ; la politique du champion est survival-**NÉGATIVE**. Et
> `life_score` se comporte identiquement (le champ_body atteint 2× le life_score du champion).
> **Ni la survie ni la fitness n'ont de contenu cognitif** → le gradient de sélection pour la cognition
> est **NUL**. Cela explique mécaniquement les neuf neutres in-world : le monde ne récompense pas ce
> qu'on cherche à faire émerger. Le benchmark **n'est pas sauvable en changeant de métrique**.

Lus ensemble, six findings — presque tous « négatifs » — cessent d'être des défaites et deviennent des
**contraintes de conception** :

| # | Finding | Contrainte imposée sur la tâche/monde |
|---|---|---|
| 1 | S2 corps-vs-cognition | **Contenu cognitif EXPLICITE**, que le corps ne peut court-circuiter |
| 2 | LANG-006 | **Asymétrie d'information** — sinon le langage ne paie pas ET n'émerge pas (MI = 0.000 exact) |
| 3 | MEM-001 | **Demande de rappel** — sinon la mémoire reste inerte (poids mém 0.000) |
| 4 | G1-001 | **Variation multi-mondes** — sinon « transfert » = noyau partagé |
| 5 | KCHAIN / EDR-202 | **Rythme observable** dans la structure de tâche — sinon le crédit ne bootstrappe pas la composition |
| 6 | Loi warm-start | **Bassin pré-formé** (curriculum/warm-start) pour franchir la barrière de bootstrap |

**Ces six contraintes déterminent presque uniquement le monde à construire.** C'est le principal acquis
stratégique du projet, et il était réparti en six records lus séparément comme des neutres.

---

## 3. Ce qui reste RÉELLEMENT ouvert — les paris à trancher

L'évidence accumulée ne départage PAS les questions suivantes. Ce sont les vrais choix stratégiques.

### Pari A — Où mettre le contenu cognitif : dans la TÂCHE ou dans la SÉLECTION ?
- **A1 — Tâche à contenu cognitif explicite** : construire un monde où résoudre un problème cognitif est
  la condition de survie, corps non court-circuitant. *Fidèle au bottom-up ; risque : on retombe sur
  « durcir le monde », déjà réfuté, si le contenu reste implicite.*
- **A2 — Sélection sur proxys cognitifs directs** : abandonner la survie comme fitness et sélectionner sur
  des marqueurs cognitifs mesurés (binding, rappel, transfert). *Contourne S2 frontalement ; risque : on
  optimise la métrique, pas l'intelligence — et on perd le « trouvé, pas donné ».*
> Rien dans les 232 records ne tranche. **C'est le pari central de la décennie.**

### Pari B — Quelle modalité cognitive comme axe primaire ?
Quatre sont instrumentées et validées **en proxy** : composition, rappel, communication, planification.
Aucune donnée ne dit laquelle porte le mieux in-world. *Choisir un axe primaire et l'amener au bout, ou
paralléliser ?* Le coût d'un axe mené à terme est de l'ordre de plusieurs arcs.

### Pari C — Quel régime d'entraînement par défaut ?
La loi warm-start est validée sur 4 fils disjoints. Faut-il en faire le **régime standard** (tout part
d'un bassin pré-formé) au risque de ne jamais tester le bootstrap froid — ou garder le froid comme
témoin ? *Enjeu : le warm-start pourrait masquer une incapacité réelle.*

### Pari D — Quelle métrique remplace la survie ?
S2 dit que ni survie ni `life_score` n'ont de contenu cognitif, et que **changer de métrique ne sauve pas
le benchmark**. Il faut donc une métrique construite avec le monde, pas plaquée dessus. **Aucune n'existe
aujourd'hui.** C'est le verrou le plus concret, et probablement le premier chantier.

---

## 4. Objectifs proposés par horizon

*(À réviser après P2.1 — la calibration peut invalider une partie de la §2.)*

**Horizon court (mois)** — rendre le socle fiable.
Calibrer les instruments porteurs (`ablation_verdict` en tête, il soutient 4 des 6 contraintes) ; solder
les dettes P0-P1 ; trancher le **Pari D** (métrique à contenu cognitif) — sans elle, aucun objectif long
n'est mesurable.

**Horizon moyen (année)** — construire le monde spécifié.
Instancier les six contraintes dans un monde unique : contenu cognitif explicite, asymétrie d'info,
demande de rappel, multi-mondes, rythme, warm-start. Vérifier qu'il **exige** la cognition par le témoin
causal (ablation within-subject) et non par « un agent réussit ».

**Horizon long (années)** — le north-star inchangé.
Transfert **zéro-shot** vers un monde jamais vu, avec une métrique à contenu cognitif. G4 (planification)
n'a que 3 records : c'est la porte la moins instrumentée et la plus proche du north-star.

---

## 5. Ce qui pourrait invalider ce document

Par honnêteté, et pour qu'il soit réfutable :
- **La calibration de `ablation_verdict`** (P2.1) : s'il ne distingue pas `X_DEMANDED` de `X_DECOY` sur
  vérité-terrain, les contraintes 1-4 de la §2 tombent ensemble.
- **La pseudo-indépendance des revues** (P3.3) : les 7 revues de l'arc WARM sont des agents de même
  architecture avec les mêmes priors — auto-critique outillée, **pas réplication**.
- **Le verdict S2 lui-même** repose sur `champion_body` : si cet instrument est mal calibré, le finding
  fondateur de la §2 vacille — et avec lui toute la §3.

Cf. [`PRIORITES_ET_DETTES.md`](PRIORITES_ET_DETTES.md) · [`../REF/REF-EXPERIMENT-PREFLIGHT.md`](../REF/REF-EXPERIMENT-PREFLIGHT.md) · [`SCIENCE.md`](SCIENCE.md)
