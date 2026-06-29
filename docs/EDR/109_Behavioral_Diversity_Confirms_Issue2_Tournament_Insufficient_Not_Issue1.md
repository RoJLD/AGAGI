# EDR 109 — Diversite comportementale : issue 2 confirmee (tournoi insuffisant, pas issue 1)

**Date :** 2026-06-29
**Harnais :** `tools/evolve_ceiling_probe.py` (commit 25e39cb, Task 1)
**Parametres :** `EVP_PRESERVE_DIMS=1 EVP_TARGET=stoneage EVP_K=12 EVP_NUM_AGENTS=40 EVP_MAX_TICKS=300 EVP_POP_CAP=200 EVP_N_CARRY=12 EVP_TOURNAMENT=3 CT_METAB=0.25 CT_PAYOFF=3.0`
**Seeds :** 0, 1, 2 (x2 bras = 6 runs)
**Statut :** CLOS — verdict issue 2

---

## Contexte et caveat EDR 108

EDR 108 avait conclu que la selection diverse (tournoi k=3) ne rescousse pas l'apex
(sign_p=0.110 NS, delta+0.019). Mais le garde-fou utilise etait `genome_diversity =
stdev(W.mean())`, qui restait **au plancher pour les deux bras** (~0.001, indiscernable).
Consequence : on ne pouvait pas distinguer entre :

- **Issue 1** : le bras diverse est reellement plus divers comportementalement, et l'apex
  reste plat -> le repertoire-monde est le verrou net, la selection est innocentee.
- **Issue 2** : le bras diverse n'est PAS plus divers comportementalement -> le tournoi
  k=3 ne maintient pas la diversite, c'est lui le levier insuffisant.

La Task 1 a ajoute la metrique `behavioral_diversity` (pstdev inter-agents de descripteurs
normalises par max d'ere : `preys_eaten`, `mammoth_kills`, `spears_crafted`, `age`).
Ce re-run tranche.

---

## Controle de coherence apex (validite du harnais)

| Bras     | Era 0    | Late mean (eres 6-11) | EDR 108 attendu          |
|----------|----------|-----------------------|--------------------------|
| elitist  | 0.2279   | **0.0821**            | era0=0.228, late~0.082   |
| diverse  | 0.2279   | **0.0974**            | late~0.097               |

**Verdict coherence : REPRODUIT.** L'apex reproduit exactement EDR 108 (era0 0.2279 vs 0.228,
late elitist 0.0821 vs 0.082, late diverse 0.0974 vs 0.097). Harnais valide.

---

## Sensibilite de la metrique behavioral_diversity

| Metrique             | Bras elitist | Bras diverse | Ratio vs genome_div |
|----------------------|--------------|--------------|---------------------|
| `genome_diversity`   | 0.0011       | 0.0011       | 1x (plancher)       |
| `behavioral_diversity` | **0.1807** | **0.1833**   | **~168x**           |

`behavioral_diversity` est un `pstdev` borne dans [0, 0.5] theoriquement.
Valeurs observees (~0.15-0.21) : bien au-dessus de zero, **sensibilite confirmee**.
Les deux bras ont une diversite comportementale reelle, non nulle. La metrique
discrimine correctement (vs `genome_diversity` aveugle).

---

## Table behavioral_diversity par ere — moyenne 3 seeds

| Era | E bdiv | D bdiv | D-E    | E frac_apex | D frac_apex |
|-----|--------|--------|--------|-------------|-------------|
| 0   | 0.1984 | 0.1984 | 0.0000 | 0.2279      | 0.2279      |
| 1   | 0.1846 | 0.1853 | +0.0007| 0.1924      | 0.1932      |
| 2   | 0.1968 | 0.1971 | +0.0003| 0.1545      | 0.1323      |
| 3   | 0.2035 | 0.1655 | -0.0380| 0.1422      | 0.1032      |
| 4   | 0.1538 | 0.2034 | +0.0496| 0.0205      | 0.1558      |
| 5   | 0.2107 | 0.1866 | -0.0241| 0.1038      | 0.1616      |
| 6   | 0.1803 | 0.1661 | -0.0142| 0.1399      | 0.1035      |
| 7   | 0.1770 | 0.1725 | -0.0045| 0.0546      | 0.1012      |
| 8   | 0.1597 | 0.1779 | +0.0182| 0.0819      | 0.0773      |
| 9   | 0.1661 | 0.1918 | +0.0257| 0.0647      | 0.1197      |
| 10  | 0.1921 | 0.1500 | -0.0421| 0.1102      | 0.0699      |
| 11  | 0.1459 | 0.2055 | +0.0596| 0.0415      | 0.1131      |
| **Mean all** | **0.1807** | **0.1833** | **+0.0026** | **0.1112** | **0.1299** |
| **Mean late (6-11)** | **0.1702** | **0.1773** | **+0.0071** | **0.0821** | **0.0974** |

---

## Decomposition strategique vs survie

Moyennes sur toutes eres, 3 seeds :

| Descripteur      | E mean | D mean | Delta D-E | Interpretation          |
|------------------|--------|--------|-----------|-------------------------|
| `bdiv_preys`     | 0.2342 | 0.2179 | -0.0163   | strategie chasse        |
| `bdiv_mammoth`   | 0.2268 | 0.2561 | +0.0293   | strategie chasse lourde |
| `bdiv_spears`    | 0.0661 | 0.0734 | +0.0073   | strategie artisanat     |
| `bdiv_age`       | 0.1958 | 0.1858 | -0.0100   | survie                  |

Observations :
- `bdiv_spears` tres bas pour les deux bras (spears_crafted souvent 0 -> pstdev effondre
  quand tous les agents = 0 ou presque). Signal de comportement rare, pas de levier.
- `bdiv_mammoth` est le seul descripteur ou D > E de maniere coherente (+0.029).
- `bdiv_preys` et `bdiv_age` : E >= D.
- La decompositon n'indique pas de dominance nette d'un bras sur l'autre.

---

## Contraste apparie diverse vs elitist

**Per seed (late mean eres 6-11) :**

| Seed | E_apex | D_apex | D-E apex | E_bdiv | D_bdiv | D-E bdiv |
|------|--------|--------|----------|--------|--------|----------|
| 0    | 0.0937 | 0.0586 | -0.0351  | 0.1859 | 0.1604 | -0.0255  |
| 1    | 0.0680 | 0.1348 | +0.0668  | 0.1593 | 0.1899 | +0.0306  |
| 2    | 0.0847 | 0.0989 | +0.0142  | 0.1654 | 0.1815 | +0.0161  |
| **Mean** | **0.0821** | **0.0974** | **+0.0153** | **0.1702** | **0.1773** | **+0.0071** |

**Test signe apparie (late mean per seed) :**
- apex : 2/3 positifs, sign_p = 0.250 (NS)
- bdiv  : 2/3 positifs, sign_p = 0.250 (NS)

**Correlation bdiv x frac_apex (toutes eres, toutes seeds) :**
- elitist : r = +0.537
- diverse : r = +0.597

La correlation positive indique que la diversite comportementale et l'apex covarient
(eres avec plus de diversite tendent vers plus d'apex) — mais c'est une correlation
intra-run, pas un effet causal de la selection.

---

## Verdict

### Issue 1 (non etablie) : diverse plus divers comportementalement, apex plat -> repertoire-monde CLOS

Non retenu. Le bras diverse n'est PAS significativement plus divers que l'elitiste :

- D_bdiv_late = 0.1773 vs E_bdiv_late = 0.1702, delta = +0.007 (+4% relatif dans le regime
  ~0.17 ; ~1.4% de la plage theorique [0, 0.5]), sign_p = 0.250 (NS)
- L'ecart minuscule (+4% relatif, <1.5% de plage) est coherent avec sign_p 0.250 NS et
  renforce issue 2 : le tournoi k=3 ne cree pas de separation comportementale discernable.
- 2/3 seeds seulement positifs, seed 0 inverse
- La trajectoire ere-par-ere montre des alternances sans tendance stable

### Issue 2 (confirmee) : tournoi k=3 insuffisant pour maintenir la diversite comportementale

**CONFIRME.** Le tournoi a k=3 ne cree pas d'avantage comportemental discernable sur
l'elitiste (top-3 carry). Les deux bras convergent vers le meme plateau de diversite
comportementale (~0.17-0.18 late). L'hypothese que le bras `diverse` preserverait
mieux la diversite est refutee avec la metrique comportementale appropriee.

**Consequence pour la chaine EDR 104-108-109 :**
- EDR 104 : dose-reponse diversite absente (levier diversite clos)
- EDR 108 : selection diverse ne rescousse pas l'apex (sign_p 0.110 NS) — garde-fou trop grossier
- EDR 109 : avec la bonne metrique, le bras diverse n'est PAS plus divers — c'est le tournoi
  qui est insuffisant, pas le signal du monde

**Implication :** meme avec un meilleur operateur de diversite (tournoi plus large, niching,
novelty search), l'apex resterait probablement plafonne par le repertoire-monde — mais
ce re-run ne l'etablit pas directement. Le verrou repertoire-monde reste la piste principale
(convergence EDR 105-108), mais le bras diverse de EDR 108 ne constitue pas une preuve
suffisante pour innocenter la selection de maniere definitive (issue 1 non etablie,
seulement issue 2 confirmee).

**Verdict synthetique :** issue 2 CONFIRMEE, issue 1 NON ETABLIE (distincts : issue 1 aurait
requis que diverse soit significativement plus divers ET apex plat ; ici diverse n'est pas
plus divers, donc issue 1 ne peut pas etre tranchee par ce run).

---

## Anti-theatre & limites

**Tracabilite des seeds (dette pre-existante) :** les 6 JSON de run (`bdiv_E_s0.json` ..
`bdiv_D_s2.json`) rapportent tous `"seed": 0` dans leurs metadonnees. Ce champ est celui
du `Harness(seed=0, ...)` dans `tools/evolve_ceiling_probe.py` (hardcode a 0), PAS
`EXPERIMENT_SEED`. Le dict `result` retourne par `run_evolution` n'embarque pas
`experiment_seed`. Les donnees elles-memes sont distinctes par seed (era0 frac_apex
0.2906/0.175/0.218), donc la validite des resultats n'est pas en cause ; la
correspondance run<->seed repose sur le nom de fichier. Dette de repro identique dans
EDR 105/108 — a corriger dans une future iteration du probe (faire embarquer
`experiment_seed` dans le `result`).

---

## Liens

- [[coop-competence-is-population-property]] — monoculture vs diversite, contexte coop apex
- [[nas-bottleneck-is-substrate-not-search]] — verrou = repertoire-monde, pas la recherche
- EDR 108 — Diverse_Selection_Does_Not_Rescue_Apex — run precedent, caveat genome_diversity
- EDR 104 — Diversity_Dose_Has_No_Tractable_Dose_Response — dose diversite inoperante
- EDR 105 — Forage_Bottleneck_Is_Approach — meme conclusion verrou monde depuis angle forage

---

## Suite

Si l'on veut etablir issue 1 (selection innocentee), il faudrait un operateur qui **garantit**
behavioralement la diversite (novelty search explicite, niching MAP-Elites) et montrer que
meme dans ce cas l'apex reste plat. Ce n'est pas ce re-run.

La piste prioritaire reste **enrichir une affordance du monde** (EDR 105 : goulot = approche,
pas capture ; EDR 107 a lancer : competence de navigation dans Lewis).
