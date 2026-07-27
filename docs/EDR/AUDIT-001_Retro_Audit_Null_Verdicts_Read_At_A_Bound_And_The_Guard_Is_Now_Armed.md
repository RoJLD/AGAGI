---
id: EDR-AUDIT-001
type: EDR
title: "Rétro-audit des records actifs : quatre verdicts NULS lus à une borne (dont trois no-op littéraux, un dans la RÉFÉRENCE S2-009) — cause mécanique commune dans `ablation_verdict`, garde désormais ARMÉE"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
corrects: [EDR-S2-004, EDR-S2-006, EDR-S2-007, EDR-S2-009]
---

## Question
[[EDR-WARM-010]] a montré qu'un verdict NUL lu sur un bras au plancher est **ininterprétable, pas
négatif**, et a ouvert la classe **E14** : *un cliquet ne regarde jamais en arrière*. `assert_not_degenerate`
était `exécutable` quand WARM-002 a été gravé, relu et cité par 4 records — et n'a rien attrapé, parce
qu'aucun dispositif ne repasse les chiffres déjà publiés.

Combien d'autres conclusions actives portent le même défaut ?

## Méthode
Triage outillé (`tools/retro_audit_records.py`) sur les 20 records `status: active`, puis examen à la
main. Toutes les affirmations ci-dessous sont **re-vérifiées par sonde propre**, pas relayées.

**Résultat méthodologique du triage lui-même — un NÉGATIF à consigner.** Le signal qu'on voulait
automatiser (« verdict nul publié SANS contrôle positif ») a **échoué deux fois** sa calibration sur
l'archétype WARM-002 : le mot `oracle` y figure en `## Question` (citation de cadrage), puis en
Résultats sous « oracle intact ≈ 200 (S2-009) » — une **valeur de référence citée**, jamais un contrôle
exécuté. **Distinguer « a lancé un contrôle » de « cite un contrôle fait ailleurs » exige de comprendre
la phrase, pas de la matcher.** Le rétro-audit n'est donc PAS automatisable de bout en bout : le code
énumère et priorise (`verdict NUL × conclusion sur le MONDE × plancher avoué`, calibré pour sortir
l'archétype au risque maximal) ; le jugement tranche — même partage que E9. Les deux échecs sont figés
en régression (`tests/sandbox/test_retro_audit.py`).

## Résultats — trois défauts, dont deux vérifiés par exécution

### 1. EDR-S2-004 — le corroborant « indépendant » est l'initialisation jamais touchée
`fit_policy` initialise `W = np.zeros((K,K))`, `b = zeros`, et n'accepte un candidat qu'en `sc > best`
**STRICT**. Quand `score(W=0)` atteint déjà le plafond, aucun candidat ne peut le battre : **W ne quitte
jamais son initialisation**. Mesuré (K=4, seed 0, 300 itérations) :

| cellule | `\|W\|` après entraînement | `score(W=0)` | W gelé à l'init |
|---|---|---|---|
| corps SUFFISANT + énergie | **0.0000** | 300.0 = **cap** | **oui** |
| corps INSUFFISANT + énergie | 10.9272 | 30.0 | non |
| corps SUFFISANT + devise séparée | **0.0000** | 300.0 = **cap** | **oui** |
| corps INSUFF. + devise séparée | **0.0000** | 30.0 | **oui** |

Deux conséquences : (a) avec `W = 0`, `argmax(0·o) = 0` **quelle que soit l'obs** — la politique est
constante, donc ablater l'obs est un no-op LITTÉRAL et le `ratio 1.00` est une **identité**, pas une
mesure ; (b) le corroborant vendu comme second témoin indépendant — « **|W|obs = 0.000 EXACT** partout
ailleurs » — est **le zéro de départ**. La conclusion paraissait doublement étayée (un ratio ET un
corroborant) alors que les deux sortaient du même no-op.

### 2. EDR-S2-007 — une cellule nulle est une identité algébrique
`_model_matrix(shift, K)` avec `shift = 0` **est la matrice identité** (vérifié : `np.array_equal(M,
np.eye(4))` → `True`). Or `anticipation_demand_world_probe:58` fait `pred = (M @ obs) if intact else obs`.
À `shift = 0`, **les deux bras calculent la même chose**. Le `ratio 1.00` de cette cellule ne peut pas
prendre d'autre valeur — et il est publié comme condition de **nécessité** (« la survie exige
l'anticipation SSI … dynamique NON-triviale »). C'est la classe **E1** : un contrôle qui ne peut pas
échouer, présenté comme une mesure empirique.

### 3. EDR-S2-006 (`foundational`) — une prémisse transportée d'un jouet vers la biosphère
S2-006 conclut « la biosphère échoue les TROIS conditions … le corps est SUFFISANT … donc chaque test
cognitif in-world est NEUTRE PAR CONSTRUCTION — ce n'est ni le substrat ni le crédit, c'est l'OBJECTIF ».
Or « corps SUFFISANT » signifie, **dans le jouet**, `body_gain > metab` → survie infinie, plafond 300/300.
**Dans la biosphère, le champion meurt à 27.5 ticks sur 200** (chiffre de S2-003, ~14 % du cap) : son
corps n'est pas suffisant au sens du théorème. Le transfert est une **analogie non mesurée** — classe E8,
et [[causal-chain-does-not-cross-populations]] : *une chaîne causale transporte son signe, pas son
amplitude*. S'y ajoute une exclusion causale (« ni substrat ni crédit ») tirée d'un nul in-world **sans
contrôle positif in-world** : la forme exacte de l'erreur WARM-002, sur un record marqué `foundational`.

> ⚠️ **Ce qui n'est PAS remis en cause** : la conclusion large du fil S2 (la survie et la fitness n'ont
> pas de contenu cognitif dans la biosphère par défaut) a un appui **indépendant** — l'arc
> cognition-vs-corps, où `champion_body` (génome du champion + actions ALÉATOIRES) survit ~4× le
> plancher. C'est la **dérivation** de S2-006 qui est fautive, pas nécessairement son verdict.
> Distinction à tenir : réfuter un raisonnement n'est pas réfuter sa conclusion.
>
> **⚠️⚠️ AMENDÉ le même jour — [[EDR-S2-012]] a MESURÉ ce filet de sécurité au lieu de le citer.**
> J'écrivais ici « verdict BODY unanime **5/5 mondes** » : c'est **4 au plus** (`IndustrialWorld` est un
> clone de `Biosphere3D`, et `stoneage` EST `Biosphere3D` — deux lignes du tableau sont la même
> simulation, chiffres identiques à l'appui). Et la moitié « la cognition n'apporte rien » est
> elle-même un nul in-world **sans contrôle positif in-world** : le défaut exact que ce record dénonce.
> L'appui tient dans sa direction, pas dans sa force annoncée. **Citer un appui n'est pas le vérifier —
> et ce record vient de commettre, en une ligne, l'erreur qu'il documente sur 80.**

### 4. EDR-S2-009 — le contrôle NÉGATIF de la référence est un no-op littéral (calibration P2.10)
Le record ne publiait que des **ratios, aucune valeur absolue**. Re-mesuré au régime publié (metab=0.75,
cog=12.0, seed 2026, K=12) :

| mode | intact | ablé | ratio | statut |
|---|---|---|---|---|
| **ON** | 200.0 | 9.0 | **22.22** | ✅ `X_DEMANDED`, amplitude réelle |
| **OFF** | 7.0 | 7.0 | 1.00 | ❌ **bras bit à bit identiques sur les 12 ères** |

En mode OFF, `forage_payoff = 0` et aucune nourriture cognitive : **tout le monde meurt à ~7 ticks quoi
qu'il fasse**. Le « ratio 1.00 NEUTRAL » ne montre donc pas *« le marqueur reste inerte quand la
perception ne paie pas »* mais *« le marqueur rend 1.00 quand la métrique est morte »*. Un vrai contrôle
négatif exige un monde où les agents **SURVIVENT** et où la perception ne paie pas.

> **Portée stricte.** Le bras ON porte le verdict et il tient. Et la **spécificité du marqueur est
> établie ailleurs** — S2-001 (monde TRIVIAL), LANG-006 (MI 0.000), MEM-001 ont tous des bras où les
> agents vivent et le ratio vaut 1.0. C'est **cette ligne** qui ne la démontre pas, pas la propriété.
> `COGNITIVE_DEMAND_RECIPE_REALIZED_INWORLD` n'est pas remis en cause.

**Ce que ce cas prouve en plus** : la garde armée attrape le défaut sur des **données de production**,
pas sur une fixture. Elle est pinée comme cas de calibration permanent.

**Subtilité d'ordre trouvée en écrivant ce test** : `ablation_verdict` teste `n >= n_floor` **avant** la
garde de dégénérescence. À petit n, des bras bit-identiques sortent en `INCONCLUSIVE` (sous-puissant) et
non `INCONCLUSIVE_DEGENERATE`. **Sous-puissance et dégénérescence sont deux défauts distincts, et le
premier masque le second dans le verdict** — le champ `degenerate` reste vrai, c'est lui qu'il faut lire.

## La cause mécanique commune — et le correctif armé
`ablation_verdict` (`tools/demand_marker.py`) était un **pur ratio de médianes, sans aucune garde de
borne**. Tout bras collé à un plancher ou un plafond produit donc `ratio ≈ 1.0 → X_DECOY → « X est un
leurre »` : **un verdict NUL fabriqué par la borne, pas par l'absence d'effet**. L'instrument est
`adopt_for` par ~20 records. Il n'a pas seulement laissé passer WARM-002 : il l'a **produit**.

**Garde désormais ARMÉE PAR DÉFAUT** (décision robla, 2026-07-21) : `X_DECOY` devient
`INCONCLUSIVE_DEGENERATE` dès que le bras de référence n'a pas d'amplitude, avec la raison dans `why`.

Ce que le code détecte d'office (cas CERTAINS) : bras **identiques point par point** (attrape S2-007 et
les cellules gelées de S2-004). Ce qui exige une déclaration de l'appelant : `floor=` / `ceiling=` — car
**un plancher n'est pas déductible de deux tableaux** (rien ne distingue « 7 ticks, c'est le sol » de
« 7 ticks, c'est un niveau signifiant »). `verdict_demand_marker` déclare désormais `floor=9.0`, le
plancher **mesuré** par WARM-010.

**Sur-correction évitée, et c'est le contrôle qui compte** : une règle « variance nulle du bras intact »
paraissait naturelle — elle a été retirée après avoir cassé un test de nul sain. **Un positif entièrement
CENSURÉ est légitimement constant** (12 ères touchant toutes le cap). La dégénérescence n'invalide donc
que le NUL ; un intact au plafond face à un ablé bas reste un positif RÉEL, simplement sous-estimé —
signalé `censored`, jamais bloqué. Sans ce bras, la garde aurait détruit la cellule positive de S2-007
(16.23) et l'oracle de S2-009 (21.05).

## Verdict
**`FOUR_ACTIVE_NULLS_READ_AT_A_BOUND__MECHANICAL_CAUSE_FIXED_IN_THE_INSTRUMENT`** — sur 20 records
actifs, **quatre** portent un verdict nul non interprétable, dont **trois sont des no-op exacts** vérifiés
par exécution (deux identités algébriques + un bras bit-identique sur 12 ères). La cause n'est pas la
négligence de quatre auteurs : c'est un instrument partagé qui **fabriquait** ce verdict, et qui est
corrigé.

> **Le quatrième est le plus instructif** : il est dans **S2-009**, le record qui servait de RÉFÉRENCE de
> contrôle positif à tout l'arc — y compris à la mesure qui a lancé ce rétro-audit. Un record peut être
> juste là où on le cite et faux là où personne ne regarde. Ce n'est pas une raison de douter de tout :
> son bras ON est solide, et la propriété que sa ligne OFF prétendait établir l'est **ailleurs**.

## Conséquences
* **Bandeaux de correction** posés sur S2-004, S2-006, S2-007 ; `corrected_by:` en frontmatter.
* **Ce que devient S2-004** : sa cellule POSITIVE (ratio 10.71, |W| 0.931, W réellement entraîné) tient —
  c'est un vrai contrôle positif exécuté. Ce sont ses conditions de **nécessité** qui sont tautologiques.
* **Ce que devient S2-005** : le mieux instrumenté des cinq — il contient un contrôle positif ET un
  contrôle de spécificité authentique (cellule « rappel PRÉSENT », `|W| = 0.909` donc W a bougé, ratio
  1.00). Réserve mineure : il documente que `|W|` peut faux-**positiver**, jamais qu'il peut
  faux-**négativer** par non-entraînement — ce que le présent record établit.
* **Dette ouverte** : `run_credit_probe`, `run_warmstart_credit_probe`, `run_credit_linear` n'ont aucun
  test ; `LinearCognitiveOracle` est **code mort** (aucun appelant) alors que S2-011 publie une ligne de
  résultat « oracle linéaire 200 » qui n'a **aucun chemin d'exécution committé**. À trancher : re-mesurer
  ou retirer la ligne.

## Leçons (registre des erreurs)
* **E14 confirmée et outillée à moitié** : la garde est `exécutable` pour le triage, **non automatisable**
  pour le jugement. Le nombre de classes « couvertes » surestime la protection tant que le stock de
  conclusions actives n'a pas été repassé.
* **E1 revient sous une forme nouvelle** : pas un contrôle négatif tautologique, mais une **condition de
  nécessité** tautologique. Un « SSI » dont la moitié *nécessité* repose sur des cellules structurellement
  incapables de produire l'autre issue.
* **Un corroborant peut être un artefact d'optimiseur.** `|W| = 0.000 EXACT` lisait comme « la politique
  ne pèse pas l'obs » ; c'était « l'optimiseur n'a jamais accepté un pas ». Vérifier qu'un poids déclaré
  nul a été **entraîné** avant de le citer comme témoin.

Converge [[EDR-WARM-010]], [[EDR-WARM-002]], [[EDR-S2-009]], REF-DEMAND-MARKER,
[[floor-pinned-verdict-and-retroactive-gap]], [[instrument-calibration-ratchet]].
