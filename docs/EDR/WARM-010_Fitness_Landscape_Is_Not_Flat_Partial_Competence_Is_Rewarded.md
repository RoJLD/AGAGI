---
id: EDR-WARM-010
type: EDR
title: "Le paysage de fitness in-world N'EST PAS plat : la survie récompense la compétence PARTIELLE de façon strictement monotone (9→200, 22×) — le mécanisme de WARM-002 est réfuté, son échec empirique tient"
status: active
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT, REF-DEMAND-MARKER]
corrects: [EDR-WARM-002]
---

## Question
WARM-002 conclut `INWORLD_EVOLUTION_WONLY_FLAT_FITNESS_LANDSCAPE`, avec un mécanisme explicite et
falsifiable : « un suiveur-de-signal **PARTIEL** survit AUSSI PEU qu'un non-suiveur (la survie est un
accumulateur multiplicatif qui ne récompense qu'au-delà de ~99 % d'accuracy de perception, cf. WARM-001),
donc la sélection n'a **aucun gradient de fitness cognitif** à escalader ».

Cette phrase est une **dose-réponse** — et elle n'avait jamais été mesurée. Elle a été inférée d'un ratio
intact/ablé ≈ 1.00, avec un seuil d'amplitude (« ~99 % ») importé de WARM-001, qui mesurait une autre
grandeur (accuracy d'imitation) sur une autre population.

Sous-question préalable : le banc `_mamba_survival_eras` **sait-il** produire un positif ? Un NEUTRAL
produit par un banc incapable de rendre autre chose n'est pas un résultat.

## Méthode
Deux mesures sur le **même banc** que WARM-002 (`_mamba_survival_eras`), **même régime** S2-009
(`metab=0.75`, `cog=12.0`, `forage_payoff=0`, seed 2026, 12 agents, 200 ticks) — le régime publié par
S2-009 ligne 23, pas les défauts de signature de `run_cog_demand_map` (4.0/6.0), qui ne correspondent à
aucun résultat gravé.

1. **Contrôle positif** — injection de l'oracle lecteur-de-signal de S2-009 (réponse CONNUE : ratio 21.05).
2. **Dose-réponse** — `partial_oracle(p)` (`tools/ground_truth_worlds.py`) : suit le signal avec
   probabilité `p`, sinon direction au hasard parmi 4. `p` balayé de 0 à 1. C'est l'étalon de **compétence
   graduée** qui manquait au dépôt.

Seam ajouté à `_mamba_survival_eras` : `intact_cls` / `ablated_cls`, **défauts = comportement historique
exact** (test de régression dédié sur la signature).

## Résultats

**Contrôle positif : le banc est INNOCENTÉ.** ratio **22.22**, `X_DEMANDED`, n=12 — contre 21.05 publié.

**Dose-réponse (K=12 ères) :**

| fidélité `p` | survie médiane | ères |
|---|---|---|
| 0.00 | **9.0** | 9.0 … 10.0 |
| 0.25 | **12.0** | 11.0 … 14.0 |
| 0.50 | **17.5** | 15.5 … 23.0 |
| 0.75 | **37.0** | 27.0 … 44.5 |
| 0.90 | **94.2** | 60.0 … 143.5 |
| 1.00 | **200.0** | 170.0 … 200.0 (plafond) |

**Strictement monotone, amplitude 22.2×, et AUCUN chevauchement d'ères à AUCUNE des cinq marches**
(p=0 plafonne à 10.0 / p=0.25 démarre à 11.0 ; 14.0 / 15.5 ; 23.0 / 27.0 ; 44.5 / 60.0 ; 143.5 / 170.0).
Séparation 12/12 à chaque marche → `sign_p = 2⁻¹² ≈ 2.4e-4` par marche.

Contrôle de cohérence non planifié, réussi : `p=0` rend **9.0**, et l'oracle *ablaté* rend **9.0**. Deux
constructions indépendantes de « pas de perception » tombent sur le même plancher.

**Confond de dépense écarté PAR CONSTRUCTION** : à tout `p`, la politique émet **exactement une**
direction one-hot par tick. Le coût de déplacement est donc constant sur tout le balayage ; seule varie la
**justesse** de la direction. La montée ne peut pas être un artefact d'agents qui bougeraient plus.

## Verdict
**`FITNESS_LANDSCAPE_IS_NOT_FLAT__PARTIAL_COMPETENCE_IS_DENSELY_REWARDED`**

La fitness récompense la compétence partielle **dès le premier incrément** : +36 % de survie à p=0.25,
très loin du seuil de « ~99 % » postulé. Le mécanisme de WARM-002 est **réfuté par mesure directe**.

**Ce qui TIENT de WARM-002** : l'échec empirique. L'évolution W-only n'a pas franchi le verrou, sur 3
régimes de mutation. Cette mesure n'est pas touchée.

**Ce qui CHANGE** : l'attribution. Pas « le monde n'offre aucun gradient » mais « notre optimiseur n'a
pas trouvé un gradient dense et monotone qui est démontrablement là ». WARM-002 cesse d'être un résultat
sur le MONDE pour devenir un résultat sur l'OPTIMISEUR — et rejoint ainsi
[[warm-start-transversal-law]] (« verrou = régime crédit/optim, PAS capacité ») au lieu d'en être la
seule exception.

## Portée & limites — ce que ce record ne prouve PAS
⚠️ **L'axe balayé est l'espace des COMPORTEMENTS, pas celui des GÉNOMES.** `partial_oracle` est
paramétré à la main et entre avec `genome=None`. Je mesure donc la géométrie de la fonction de fitness,
**pas** celle de l'application `genome.W → comportement`. Un paysage peut être lisse en comportement et
rugueux, voire plat, en génotype.

Conséquence : je réfute « le paysage de fitness est plat ». Je **ne** prouve **pas** « l'évolution aurait
dû marcher ». La proposition survivante, non testée, est **l'ATTEIGNABILITÉ** : la mutation W-only depuis
une init aléatoire peut-elle produire un incrément de fidélité de suivi de signal ? C'est la question
ouverte que ce résultat installe, et elle est nettement plus précise que celle qu'elle remplace.

Portée du contrôle positif : il valide le **banc** (monde, boucle d'ères, agrégation, ablation par
dérangement), pas le chemin génome→comportement — déclaré comme tel dans `CALIBRATED`.

## Leçons (registre des erreurs)
* **E3 — métrique dégénérée lue comme « pas d'effet »**, occurrence **antérieure** à celles déjà
  inscrites. Le bras intact de WARM-002 survivait **5.0–7.2 ticks** ; le plancher no-perception mesuré
  ici est **9.0**. Ses génomes évolués survivaient donc **sous** le plancher. Un ratio intact/ablé lu sur
  un bras au sol vaut 1.0 **par construction**. La garde `assert_not_degenerate` existe et est
  exécutable — mais **rien ne la rétro-applique aux records déjà gravés**. C'est un trou du cliquet, pas
  de la garde.
* **E8 — inférence substituée à la mesure** : le seuil « ~99 % d'accuracy » est arrivé par « cf.
  WARM-001 », d'une autre grandeur et d'une autre population. Quatrième occurrence du même motif —
  *une chaîne causale transporte son signe, pas son amplitude*
  ([[causal-chain-does-not-cross-populations]]).
* **Le contrôle positif coûtait 6 secondes.** Il était disponible depuis S2-009. Personne ne l'a lancé
  avant de graver un verdict sur la structure du monde.

## Livrables
* `tools/ground_truth_worlds.py::partial_oracle` — étalon de compétence GRADUÉE (réutilisable P2.1).
* Seam `intact_cls`/`ablated_cls` sur `_mamba_survival_eras`, défauts historiques épinglés par test.
* 3 cas de calibration permanents ; `_mamba_survival_eras` déclaré `["perception:oracle"]`.
  Cliquet : **71 instruments, 3 calibrés**.

Converge [[EDR-WARM-002]] (corrigé), [[EDR-S2-009]], [[warm-start-transversal-law]],
[[decisive-substrate-thesis-test]], [[instrument-calibration-ratchet]], REF-EXPERIMENT-PREFLIGHT.
