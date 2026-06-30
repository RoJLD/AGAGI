# Design — FamineWorld : 2ᵉ monde distinct (causalité temporelle / pénurie cyclique + stockage)

> **Date** : 2026-06-30 · **Statut** : design validé (brainstorming), avant plan.
> **But** : enrichir le répertoire-monde — le verrou surdéterminé (G1 NEUTRE EDR-116 + 105/108/110/113).
> **Sert** : `SDR-G1` (re-mesurer le transfert sur un monde GENUINEMENT distinct). Programme parent :
> 4 axes priorisés (temporel ⭐ → coop requise → spatial → abstrait) ; FamineWorld = **#1**.

---

## 1. Pourquoi ce monde (problème)

G1 a mesuré NEUTRE (EDR-116) : la compétence ne généralise pas soup→stoneage — mais soup et stoneage
**partagent le moteur** (soup = stoneage avec features OFF). Le projet n'a **qu'une seule structure
causale réelle** (forage immédiat). Pour tester la généralisation, il faut un 2ᵉ monde dont la **règle de
succès est causalement différente**, tout en **partageant le contrat I/O** (59 entrées / 108 sorties)
pour qu'un champion stoneage y soit *évaluable*.

## 2. La règle causale distincte

Nourriture régénérée par **cycles abondance ↔ famine** :
- **Abondance** (N ticks) : nourriture plentiful, régénération normale.
- **Famine** (M ticks) : **régénération nulle** (ou quasi).

Survivre une famine **exige d'avoir stocké pendant l'abondance**. Opposé causal de stoneage (forage
immédiat, régénération constante) : succès = **acte présent → bénéfice futur** (gratification différée).
C'est une compétence que stoneage **n'exige ni n'enseigne** → un transfert positif vers FamineWorld
serait une vraie généralisation, pas de la mémorisation.

## 3. Architecture — héritage moteur, distinctness dans les mécaniques

`class FamineWorld(Biosphere3D)` (`src/worlds/world_famine.py`). Hérite le contrat I/O 59/108 et toute la
machinerie agent → champion évaluable sans incompatibilité de dimensions. **La distinctness est dans les
MÉCANIQUES AJOUTÉES, pas dans une config retirée** (≠ soup) :
1. **Régénération cyclique** : override de la régén ressources dans `step()` — phase courante dérivée de
   `self.ticks` (abondance si `ticks % (N+M) < N`, sinon famine). En famine, le `cooldown`/regrowth des
   sources de nourriture est gelé.
2. **Réserve (stockage)** : une réserve par agent qui **ne draine pas en famine** au même rythme — un
   surplus mis de côté pendant l'abondance. Réutilise l'action/inventaire `grab` existant ; **aucun
   nouveau slot I/O**. *(Mapping exact = détail de plan ; piste recommandée : banque d'énergie
   déplafonnée pendant l'abondance + cache, l'agent percevant sa réserve via un slot inventaire existant.)*

> Le cycle est **apprenable depuis la dynamique perçue** : l'agent voit la densité de nourriture chuter
> (obs existantes) → la pression sélectionne ceux qui ont stocké AVANT. Pas de nouvel I/O nécessaire.

## 4. Validation — réutilise nos portes (zéro instrument neuf)

1. **G0 sur FamineWorld** (`tools/s2_demand.py`, ajouter `FamineWorld` à `WORLDS`) : un champion évolué
   *dans FamineWorld* bat-il l'aléatoire/réflexe ? Verdict EXIGE/FACTICE. **Sous-question cruciale = la
   gratification différée est-elle ÉVOLVABLE dans ce substrat ?** Si champion ≈ aléatoire (tous meurent
   en famine) → plancher (le substrat ne sait pas apprendre le report) — **résultat majeur en soi**,
   orthogonal au mur Lewis (acquisition immédiate).
2. **G1 re-mesure** (`tools/curriculum_transfer.py`, `FamineWorld` câblé dans `WORLD_FACTORY`) : transfert
   stoneage→FamineWorld et soup→FamineWorld, apparié, budget égal, `deterministic`, n≥8 (powerer).

## 5. Composants

- **Create** `src/worlds/world_famine.py` — `FamineWorld(Biosphere3D)` : override régén cyclique + réserve.
- **Modify** `main_curriculum.py` — `WORLD_FACTORY["famine"] = FamineWorld` (additif, `DEFAULT_LADDER`
  inchangé).
- **Modify** `tools/s2_demand.py` — `WORLDS["famine"] = FamineWorld` (pour G0).
- **Test** `tests/test_world_famine.py` — cycle, distinctness, I/O compat.
- **Runs + EDR** : G0 (FamineWorld EXIGE ?) puis G1 (transfert) → EDR(s) `tests:[SDR-G1]`.

## 6. Calibrage (variables d'expérience, Commandement 15)

Cycle initial **abondance 60 / famine 40 ticks** (modéré). Sévérité de la famine = variable. **À régler
empiriquement** : si les non-stockeurs survivent quand même → famine trop douce (pas de pression, non
distinct) ; si TOUT meurt → 100% létal (INCONCLUSIF, plancher). Cible : un régime où le stockage *paie*
(champion survit les cycles, naïf meurt). Loggés : N, M, sévérité, seed.

## 7. Tests (TDD)

- **Cycle** : `FamineWorld` alterne abondance/famine selon `ticks` (densité de nourriture chute en
  famine ; régén gelée). Vérif sur un monde sans agents (dynamique pure).
- **I/O compat** : un `MambaAgent` (champion chargé) s'ajoute via `add_agent(model)` et `step()` tourne
  sans crash ; obs shape = celle de stoneage (héritée).
- **Distinctness (preuve)** : un agent **non-stockeur** (politique qui ne met rien en réserve, ex.
  `RandomActionBatchModel` ou champion stoneage naïf) **meurt** sur ≥1 cycle famine, là où un agent qui
  garde une réserve survit. Si le non-stockeur survit → la famine est trop douce (échec de distinctness
  à corriger AVANT tout verdict de transfert).
- **Non-régression** : `WORLD_FACTORY`/`DEFAULT_LADDER` existants intacts ; `s2_demand.WORLDS` existants
  intacts.

## 8. Garde-fous anti-théâtre

1. **Distinctness PROUVÉE avant transfert** : le test §7 doit montrer que la famine tue les non-stockeurs.
   Sans ça, FamineWorld n'est qu'un stoneage déguisé (le piège industrial) → tout transfert serait faux.
2. **Pas FACTICE par défaut** : si famine 100% létale → INCONCLUSIF (re-calibrer), pas un verdict.
3. **Repro** : `deterministic=True` (mémoire ambiante stoppée avant la boucle, [[biosphere-ambient-memory-nonrepro]]).
4. **Powerer** : n≥8 seeds pour tout verdict de transfert (leçon EDR-116 : le 3-seed s'évapore).

## 9. Périmètre & non-buts

- **Dans le périmètre** : `FamineWorld` + câblage (curriculum + s2) + tests + run G0 (évolvabilité du
  report) + EDR. Le run G1 transfert peut être un **sous-chantier suivant** (après G0 FamineWorld validé).
- **Hors périmètre (programme parent, backlog)** : mondes #2 coop-requise, #3 spatial, #4 abstrait ;
  mapping I/O élaboré du stockage (commencer minimal) ; opt-in `main_biosphere`.

## 10. Interprétation (quel que soit le verdict)

- **FamineWorld EXIGE + report évolvable** : 1ᵉʳ 2ᵉ monde réel distinct → débloque une vraie mesure G1.
- **Report NON évolvable (plancher)** : le substrat ne sait pas apprendre la gratification différée →
  finding fondamental (limite cognitive du substrat, distinct du mur Lewis) → oriente vers l'axe
  gradient/torch (ADR-003) ou un substrat à mémoire/horizon explicite.

## 11. Critères de succès du chantier

1. `FamineWorld` livré, tests verts dont **distinctness prouvée** (non-stockeur meurt en famine).
2. Câblé dans `WORLD_FACTORY` + `s2_demand.WORLDS` (non-régressif).
3. Run G0 réel : verdict EXIGE/FACTICE/INCONCLUSIF sur FamineWorld → EDR consigné, graphe vert.
4. (Suivant) Run G1 transfert stoneage/soup → FamineWorld, n≥8, EDR `tests:[SDR-G1]`.
