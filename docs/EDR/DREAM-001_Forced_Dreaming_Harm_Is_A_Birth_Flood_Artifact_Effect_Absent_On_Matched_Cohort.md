---
id: EDR-DREAM-001
type: EDR
title: "Le « rêve forcé réduit causalement la survie » (EDR-095) est un artefact d'AFFLUX DE NAISSANCES — et le SIGNE est inversé : sur cohorte appariée le rêve AUGMENTE la survie de +77 % (15/20, wilcoxon_p 0.0085)"
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

## Résultats — VERDICT au n complet (20 seeds, artefact `results/dream_founder_matched_n20.json`)

| métrique | off | K=8 | ratio | favorables | `sign_p` | `wilcoxon_p` |
|---|---|---|---|---|---|---|
| `n_lived` | 57.0 | 895.0 | **15.70** | 20/20 | 0.0000 | 0.0001 |
| **TOUS** *(la métrique publiée)* | 28.5 | 13.0 | **0.456** | 0/20 | 0.0000 | 0.0001 |
| **FONDATEURS** *(apparié 25/25)* | 32.0 | **56.5** | **1.766** | **15/20** | **0.0414** | **0.0085** |

**Le SIGNE est inversé, et l'inversion est significative.** EDR-095 publiait « le rêve forcé RÉDUIT la
survie de ~45 % » ; sur des agents comparables, il l'**AUGMENTE de +77 %**, aux deux tests. Le confond
ne masquait pas l'effet : il en **retournait le signe**.

Le Wilcoxon (0.0085) est nettement plus net que le test de signe (0.0414) — précisément parce que les
écarts sont larges. Le signe seul, qui jette l'amplitude, laissait le résultat sous-puissant à n=12
(8/12, 0.39) ; c'était le mauvais outil, pas un manque de données.

**Les deux axes convergent** : les fondateurs vivent plus longtemps ET se reproduisent 15.7× plus,
sur 20 seeds sur 20. Ce n'est donc pas un cycle mort-remplacement, c'est un avantage reproductif.

> **Objection traitée** : les fondateurs du bras K=8 vivent dans un monde à 895 agents contre 57 —
> l'environnement diffère. Mais c'est une **conséquence de l'intervention**, pas un confond : mêmes
> seeds, même monde, mêmes agents initiaux, seul `FORCE_DREAM` change. La chaîne « forcer le rêve →
> fondateurs plus vieux » est correctement estimée.

## Résultats intermédiaires (12 seeds — conservés pour la traçabilité)

`n_lived` : **off = 56, K=8 = 756 → ×13.4** (confond confirmé au n complet).

| métrique | off | K=8 | ratio | K8 > off | `sign_p` | statut |
|---|---|---|---|---|---|---|
| **TOUS** *(la métrique publiée)* | 29.0 | 13.0 | **0.448** | **0/12** | 0.0005 | reproduit |
| **FONDATEURS** *(apparié 25/25)* | 35.5 | 54.5 | **1.535** | **8/12** | 0.3877 | effet ABSENT |

**Le chiffre d'EDR-095 se reproduit exactement** (0.448 contre 0.543 publié, séparation parfaite, `sign_p`
au plancher). Ce n'était donc pas une erreur de mesure : c'était une **mesure juste d'une grandeur
confondue**.

## Verdict
**`FORCED_DREAMING_HELPS__PUBLISHED_HARM_WAS_A_BIRTH_FLOOD_ARTIFACT_WITH_INVERTED_SIGN`**

Sur des agents comparables, le rêve forcé **AUGMENTE** la survie des fondateurs de **+77 %**
(32.0 → 56.5 ; 15/20 seeds ; `sign_p` 0.0414, `wilcoxon_p` 0.0085). La pénalité publiée de ~45 %
était l'ombre d'un afflux de naissances (`n_lived` ×15.7, 20/20 seeds).

**Ce que la montée en puissance a changé — et la leçon qu'elle porte.** À n=12 avec le seul test de
SIGNE, le résultat était 8/12, `sign_p` 0.39 : je n'ai alors affirmé que l'ABSENCE de l'effet publié
(argument de puissance : si le ratio valait 0.448, on attendrait ~0/12 favorables). C'était le verdict
correct **avec cet outil**. Le test de signe **jette l'amplitude** ; or les écarts étaient massifs. Avec
Wilcoxon signé — celui qu'emploie `_compare` pour tout le fil S2 — l'inversion devient significative.
*Le résultat n'attendait pas plus de données, il attendait la bonne statistique.*

## Portée & limites
- **Ce qui TIENT d'EDR-095** : le hook `FORCE_DREAM` fonctionne, l'intervention s'applique, et forcer le
  rêve a un effet massif et reproductible sur la **démographie** (`n_lived` ×13-16). C'est un vrai
  résultat, simplement pas celui qui était revendiqué.
- **Ce qui TOMBE** : « le rêve forcé **coûte** la survie », et avec lui la conclusion « au plancher de
  compétence, planifier est un luxe ». La courbe `ratios_par_K` (0.613 → 0.522 → 0.543), lue comme un
  « palier », est une lecture de la même grandeur confondue.
- ✅ **TRANCHÉ à n=20** : le rêve forcé aide (+77 %, `wilcoxon_p` 0.0085). L'inversion est établie, pas
  seulement l'absence de la pénalité.
- ⚠️ **CE QUI RESTE OUVERT, et il ne faut pas le sur-lire** : ce record mesure la **SURVIE**, pas
  l'**EXPLORATION**. L'approche A d'EDR-014 posait que l'organe MCTS débloque les autels / la couche 2.
  EDR-095 la rejetait au motif que « planifier est un luxe non payable au plancher de compétence » — ce
  motif est maintenant **réfuté et inversé** : planifier PAIE. Mais « le rêve améliore la survie » n'est
  pas « le rêve débloque l'exploration ». **Le VERROU du rejet saute ; la thèse d'origine reste à
  tester.** Ne pas remplacer un verdict non mesuré par un autre.
- **Mécanisme non élucidé** : pourquoi forcer le rêve multiplie-t-il la reproduction par 15.7 ? L'effet
  est énorme et parfaitement reproductible (20/20) — c'est la piste la plus accessible du fil.
- **Borné au régime mesuré** : `stoneage`, organe ON 100 %, sweet spot (metab 0.25 / payoff 3.0),
  25 agents, 80 ticks, K=8. EDR-095 assumait déjà le caveat des ères courtes.

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
