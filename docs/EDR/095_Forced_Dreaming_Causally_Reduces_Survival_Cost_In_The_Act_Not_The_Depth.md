# EDR 095 : Le rêve forcé RÉDUIT causalement la survie — le coût est dans l'acte, pas dans la profondeur

## Contexte

EDR 093/094 laissaient un paradoxe non tranché : la population *portant* l'organe MCTS survit ~9 %
mieux (q2b 1.087, sous-puissant), mais les agents qui *rêvent* font marginalement pire (q2a −0.04).
Le corrélationnel avait atteint sa limite (EDR 094 : dreaming = conduite de minorité, l'agrégat
médian est aveugle). Phase 2 = **intervention causale** : hook moteur gated `MambaBatchModel.
FORCE_DREAM` (`_resolve_dreaming`, EDR 094, défaut `None` = prod inchangée), sonde
`tools/dream_causal_probe.py`. À organe ON (100 %) + sweet spot (0.25/3.0), on **force** l'acte de
rêver et sa profondeur, balayant les bras {off, 1, 4, 8} appariés par seed → courbe dose-réponse de la
survie.

## Constat — verdict CAUSE_NUISIBLE, franc et significatif

Run réel `results/dream_causal_0.json` (commit `ec16854`, 10 seeds, 25 agents, 80 ticks) :

| bras | médiane survie | ratio apparié vs off |
|---|---|---|
| **off** | **0.126** | 1.000 |
| K=1 | 0.073 | **0.613** |
| K=4 | 0.068 | **0.522** |
| K=8 | 0.070 | **0.543** |

- **VERDICT = CAUSE_NUISIBLE**, `ratio(Kmax/off) = 0.543`, `sign_p = 0.00195` (≈ 1/512).
- **`n_favorable = 0/10`** : dans les 10 seeds, AUCUN bras de rêve forcé ne bat « off ». Consistance
  parfaite (off ∈ [0.113, 0.165], tous les bras forcés ∈ [0.055, 0.090]).

Le rêve forcé **cause** une perte de survie de ~40-46 %. Le paradoxe Q2a est tranché causalement :
**rêver nuit à la survie**, ce n'est pas un simple corrélat de détresse.

## Signification — palier, pas pente : le coût est dans l'ACTE

La courbe `ratios_par_K` n'est PAS une descente graduée : **0.613 → 0.522 → 0.543**. La chute est un
**palier** — forcer *n'importe quel* rêve coûte ~40 % de survie d'un coup (off→K1), puis la profondeur
n'ajoute quasi rien (K1≈K4≈K8). Donc le coût n'est pas dans la *profondeur* du calcul MCTS mais dans
**l'acte de rêver lui-même** : le drain énergétique +0.5 (`mamba_agent.py:42`) plus le coût
d'opportunité (un tick passé à planifier au lieu de fourrager) suffisent à dégrader la survie au
plancher, indépendamment de combien on planifie.

> Effet secondaire notable (calibration) : le rêve forcé **augmente** `n_lived` (agents nés sur l'ère :
> off≈74 → K4≈1205) tout en **réduisant** la survie médiane → plus de brassage reproductif, des vies
> plus courtes. Le rêve déplace la stratégie vers churn rapide, pas vers la longévité.

## Caveat méthodologique — explosion de population, paramètres réduits (honnêteté)

Le plan visait 40 agents / 400 ticks. **Intractable** sur cette branche : le forçage du rêve déclenche
une **explosion de population** (compute ∝ `n_lived`, qui monte jusqu'à 1205 sur un bras/seed contre 74
pour off). C'est le « cap population latent » de la note mémoire (corrigé en **PR #29**, ABSENT de
`feat/d1-prod-pairing`). Sans cap runtime, une ère longue dans un bras qui explose ne termine pas (run
40/400 abandonné après ~19 min sur 2 ères). **Solution** : `max_ticks=80` borne l'explosion (pire ère
≈ 60 s) et **10 seeds** (vs 5 prévus) restaurent la puissance. Le signal est large (ratio 2× off/Kmax)
et sature `sign_p` (0/10) — la réduction de paramètres n'affaiblit pas la conclusion. Caveat assumé :
ères courtes (survie ∈ [0.055, 0.165] d'un AGE_REF=200), organe forcé ON pour tous (on mesure l'effet
du *rêve* à organe constant, pas l'effet de l'organe).

## Signification pour EDR 014 (goulot d'exploration) — l'organe MCTS n'est PAS le levier

Approche A (« réveil de l'organe par l'énergie ») est **réfutée comme levier de survie** : non
seulement l'organe ne débloque pas l'exploration (autels couche 2, EDR 014), mais le *forcer* à rêver
**coûte** la survie de la couche 1. Au plancher de compétence, planifier est un luxe que l'économie
d'énergie ne peut pas payer (cf. [[lewis-energy-economy-wall]], [[world-floor-survivability-gate]]).
Le réveil faiblement suggéré par EDR 093 (q2b 1.087) était un artefact de sélection, pas un bénéfice du
rêve. **Pivoter** : levier I (récompense de nouveauté) ou levier II (auto-craft), qui n'imposent pas le
coût d'opportunité d'une planification interne au plancher énergétique.

## Statut

- Phase 2 livrée (hook gated testé + sonde + provenance), verdict causal **CAUSE_NUISIBLE** robuste
  (10/10 seeds, sign_p 0.002). Met fin à l'attaque approche A de l'organe MCTS comme levier.
- La décomposition per-seed + la calibration ont, une 4ᵉ fois, évité le théâtre : la calibration a
  exposé que le coût compute suit `n_lived` (explosion), pas K ; sans elle, le run plein régime aurait
  semblé « bloqué » sans cause. Cf. [[dreaming-organ-not-dead]] (chaîne EDR 092→093→094→095).

## Variables d'expérience

Cap de population (cherry-pick PR #29 → run plein 40/400 possible), profondeur K (étendre > 8),
fraction d'organe (< 1.0), métrique de longévité, énergie (le coût du rêve est-il payable à un sweet
spot encore plus riche ?), levier d'exploration alternatif (nouveauté / auto-craft) pour EDR 014.
