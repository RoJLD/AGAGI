---
id: EDR-DREAM-001
type: EDR
title: "Le « rêve forcé réduit causalement la survie » (EDR-095) est un artefact d'AFFLUX DE NAISSANCES : l'effet publié est ABSENT sur cohorte appariée (8/12 dans l'autre sens)"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
corrects: [EDR-095]
---

## Question
EDR-095 conclut `CAUSE_NUISIBLE` : forcer le rêve réduit la survie de ~40-46 %, `ratio = 0.543`,
`sign_p = 0.00195`, séparation parfaite sur 10 seeds. Le record note **lui-même**, en « effet secondaire
notable (calibration) », que le rêve forcé fait passer `n_lived` de ≈74 à ≈1205 — **un facteur 16** — et
n'en tire aucune conséquence.

Or `survival_competence` est la **médiane des âges** sur les agents de l'ère. Une population 16× plus
nombreuse a la plupart de ses membres nés TARD ; leurs âges sont donc mécaniquement faibles. La baisse
mesurée est-elle un coût de survie, ou un **calendrier de naissance** ?

## Méthode
Le confond ne s'attaque pas en changeant de statistique mais en appariant les **sujets**. Ajout d'un
marquage `founder` dans `run_era_organ` (les `num_agents` génomes semés à t=0), puis comparaison de la
survie médiane sur cette cohorte **identifiée par identité**, à effectif strictement égal (25 vs 25 dans
chaque cellule). 12 seeds, `stoneage`, 25 agents, 80 ticks, organe ON, bras `off` vs `K=8`.

> ⚠️ **UNE PREMIÈRE CORRECTION A ÉTÉ REJETÉE — par moi, avant publication.** Restreindre la médiane aux
> « N plus vieux » semble naturel et **est biaisé** : prendre les 25 plus vieux de 96 agents, c'est le
> top 26 % ; de 1588, c'est le top **1,6 %**. C'est une sélection sur la variable de SORTIE à des
> quantiles incomparables, qui favorise mécaniquement le bras le plus peuplé (elle rendait 1.339).
> Seule l'identité permet un appariement honnête.

## Résultats (12 seeds)

`n_lived` : **off = 56, K=8 = 756 → ×13.4** (confond confirmé au n complet).

| métrique | off | K=8 | ratio | K8 > off | `sign_p` | statut |
|---|---|---|---|---|---|---|
| **TOUS** *(la métrique publiée)* | 29.0 | 13.0 | **0.448** | **0/12** | 0.0005 | reproduit |
| **FONDATEURS** *(apparié 25/25)* | 35.5 | 54.5 | **1.535** | **8/12** | 0.3877 | effet ABSENT |

**Le chiffre d'EDR-095 se reproduit exactement** (0.448 contre 0.543 publié, séparation parfaite, `sign_p`
au plancher). Ce n'était donc pas une erreur de mesure : c'était une **mesure juste d'une grandeur
confondue**.

## Verdict
**`FORCED_DREAMING_HARM_IS_A_BIRTH_FLOOD_ARTIFACT__EFFECT_ABSENT_ON_MATCHED_COHORT`**

Sur des agents comparables, la pénalité de ~45 % **n'existe pas**.

**L'argument de puissance, qui est le cœur du verdict.** `sign_p = 0.39` ne permet PAS d'affirmer un
effet inverse — et ce record ne l'affirme pas. Mais la question qui décide n'est pas « y a-t-il un
effet ? », c'est « **l'effet PUBLIÉ est-il là ?** ». Si le vrai ratio valait 0.448 sur les fondateurs, on
attendrait ~0/12 seeds favorables à K=8. On en observe **8/12**. Un effet de −55 % aurait été trivialement
détectable à ce n — il est absent. C'est une réfutation de la CLAIM, pas une démonstration de son inverse.

## Portée & limites
- **Ce qui TIENT d'EDR-095** : le hook `FORCE_DREAM` fonctionne, l'intervention s'applique, et forcer le
  rêve a un effet massif et reproductible sur la **démographie** (`n_lived` ×13-16). C'est un vrai
  résultat, simplement pas celui qui était revendiqué.
- **Ce qui TOMBE** : « le rêve forcé **coûte** la survie », et avec lui la conclusion « au plancher de
  compétence, planifier est un luxe ». La courbe `ratios_par_K` (0.613 → 0.522 → 0.543), lue comme un
  « palier », est une lecture de la même grandeur confondue.
- **Non tranché** : l'effet réel du rêve sur la survie d'agents comparables. 8/12 penche positif sans le
  démontrer. Un verdict exigerait plus de seeds — mais ce record n'en a pas besoin pour établir que
  l'effet publié n'est pas là.
- **Non retesté** : l'affirmation d'EDR-095 sur l'organe MCTS comme levier (EDR-014) reposait sur ce
  coût de survie ; elle est à réexaminer.

## Leçons (registre des erreurs)
* **Classe E3 sous une forme neuve — la métrique n'est pas dégénérée, elle est CONFONDUE PAR LA
  COMPOSITION.** Aucune borne n'était atteinte, aucun bras au plancher : la garde de dégénérescence
  armée le même jour n'aurait rien vu. Une médiane est robuste aux valeurs extrêmes, **pas à un
  changement de population**. Vérifier `n` par bras avant de comparer des médianes.
* **L'indice était DANS le record, en note de bas de page.** EDR-095 a mesuré et publié le `n_lived`
  ×16 en le qualifiant d'« effet secondaire notable (calibration) ». L'auteur a vu le chiffre et ne l'a
  pas relié à sa métrique. *Un « effet secondaire » sur la taille de la population n'est jamais
  secondaire quand la mesure est une statistique de population.*
* **Une correction peut être biaisée dans l'autre sens** — et il faut la rejeter avec la même sévérité
  qu'on applique au défaut d'origine. La sélection « N plus vieux » aurait donné un titre inverse tout
  aussi faux.

Converge [[EDR-095]], [[EDR-094]], [[EDR-AUDIT-001]], REF-EXPERIMENT-PREFLIGHT.
