---
id: EDR-132
type: EDR
title: "Le warm-start du gate rescape PARTIELLEMENT les collapsés (1/3, test causal de la path-dependence d'EDR 131) : pré-entraîner le gate à imiter l'oracle depuis H_S2 sauve le seed 0 (7→8/10, gap 0.00→0.42) mais PAS les seeds 3,4 — qui résistent aussi au re-fitting REINFORCE online et au gel ; la mesure du biais RÉEL montre pourquoi : sur 3,4 le gate produit bias|did_x≈+8 (correct) mais bias|¬did_x≈+8 AUSSI (cible −8) → marge≈0, Y boosté PARTOUT (always-Y) ; l'oracle (±8 sur did_x VRAI) binde 10/10 → le canal existe, le verrou résiduel est l'incapacité du readout à SUPPRIMER Y sur ¬did_x sur ces seeds, pas le signal/crédit/init"
status: validated
gate: null
verdict: "Test CAUSAL de la path-dependence précoce d'EDR 131 (le warm-start du gate rescape-t-il les collapsés 0,3,4 ?), 3 bras × 10 seeds, régime incitatif fade0.0/pen2. NB : premier run contaminé par un DOUBLE optimizer Adam (moments remis à zéro à l'entrée de phase B → choc au trial 1) ; corrigé (un seul optimizer, état continu) → le résultat CHANGE. (1) WARM-START plastique (gate pré-entraîné MSE à imiter l'oracle ±8 depuis H_S2, population gelée, dose {0,100,250}) : PARTIAL_RESCUE — n_bind 7→8/10, le seed 0 bascule (gap 0.00→0.42, stable à ws 100 et 250) MAIS seeds 3,4 restent gap≈0.00. (2) GEL après warm-start + MESURE du biais réit : sur les bindeurs marge biais|did_x−biais|¬did_x = 5.7–10.9 (¬did_x supprimé, bias négatif/faible) ; sur les résistants 3,4 marge ≈0 (bias|did_x +7-8 CORRECT mais bias|¬did_x +7-8 AUSSI, cible −8) → le gate booste Y PARTOUT → always-Y (y_rate 0.99-1.00). (3) ORACLE (±8 câblé sur did_x VRAI) : 10/10 gap=1.00 partout → le canal logit-Y existe, ±8 suffit, la politique de population ne noie pas. CONCLUSION : la path-dependence d'EDR 131 est CAUSALEMENT RÉELLE mais SEED-SPÉCIFIQUE — le warm-start sauve 1/3 collapsés (seed 0). Les résistants 3,4 ne sont PAS de la simple path-dependence ni de la dérive (le re-fitting plastique online échoue AUSSI) : le gate n'arrive jamais à produire une marge SUPPRESSIVE de Y sur ¬did_x, alors que did_x est rank-décodable (AUC 0.82/0.96, EDR 131) et que l'oracle réussit. Locus résiduel = la conversion readout→suppression de Y sur ¬did_x sur ces seeds. Migration : un gate de conditionnement est nécessaire (EDR 129), le warm-start aide partiellement (path-dependence réelle), mais la fiabilité restante exige un readout capable de suppression négative fiable (marge), pas un tweak signal/crédit/init."
---

# EDR 132 : Le warm-start du gate rescape partiellement (1/3) — le verrou résiduel est la suppression de Y sur ¬did_x

## Question

EDR 131 (diagnostic) a inféré, par corrélation, que les 3 seeds collapsés (0,3,4) du gate appris
saturent la marginale Y (always-Y) tôt, avant que le gate n'apprenne à router — alors que did_x reste
décodable de H_S2 (AUC 0.9). Il a proposé le **test causal direct** : pré-entraîner (warm-start) le gate
à lire did_x AVANT de l'exposer à la récompense jointe. Si ça rescape les collapsés (7/10 → ~10/10), la
path-dependence est confirmée causalement. Ce EDR exécute ce test et en mesure le mécanisme.

## Méthode

`run_curriculum_fade_gated` étendu (défauts neutres → rétrocompat EDR 129/130/131), régime incitatif
hérité (fade_w0=0.0, y_without_x_penalty=2.0 → conditionner est optimal), 10 seeds, gate learned.
Bind = binding_gap_end > 0.30.

- **`gate_warmstart_trials`** : avant la phase B, population GELÉE (forward sans `learn`), régression MSE
  de `gate_bias = w·H_S2 + b` vers la cible oracle `±oracle_bias·(2·did_x−1)` (±8). Le gate entre en
  phase B en imitant l'oracle. Dose {0, 100, 250}.
- **`freeze_gate_after_warmstart`** : gèle le gate en phase B (aucun update REINFORCE) → isole l'érosion.
- **`capture_gate_bias`** : reporte le biais RÉEL du gate en fin de phase B, séparé did_x vs ¬did_x
  (`gate_bias_didx_end` / `_notdidx_end` / `_margin_end`) → tranche le MODE d'échec (marge vs offset).
- **Contrôle ORACLE** (±8 câblé sur le did_x VRAI) sur 10 seeds → le canal logit-Y suffit-il ?

**Correctif en cours de route (revue).** Le 1er run créait un 2e optimizer Adam pour le warm-start ; à
l'entrée de phase B, l'optimizer REINFORCE avait ses moments à zéro alors que les poids étaient placés →
un pas plein-lr au trial 1 effaçait partiellement le warm-start (choc). Corrigé en réutilisant un seul
optimizer (état continu). **Le résultat en dépend** (le NO_RESCUE plat initial devient un PARTIAL_RESCUE).

Outil `tools/substrate_ab_compositional.py` : `sweep_gate_warmstart`, params ci-dessus. TDD
`tests/sandbox/test_substrate_ab_compositional.py`.

## Résultats

**Bras 1 — WARM-START plastique (optim corrigé) : PARTIAL_RESCUE (7 → 8/10).**

| warmstart | n_bind | gap seed 0* | gap seed 3* | gap seed 4* |
|-----------|:------:|:-----------:|:-----------:|:-----------:|
| 0 (baseline) | 7/10 | −0.00 | +0.00 | −0.00 |
| 100 | **8/10** | **+0.39** | −0.01 | −0.01 |
| 250 | **8/10** | **+0.42** | −0.01 | −0.01 |

Le **seed 0 bascule** (0.00 → 0.42, stable à 100 et 250) : le warm-start le rescape. Les **seeds 3,4
résistent** (restent ≈0.00). La path-dependence est donc causalement RÉELLE — mais seed-spécifique (1/3).

**Bras 2 — GEL ws=250 + biais réel du gate (marge biais|did_x − biais|¬did_x ; cible +8/−8) :**

| seed | gap | biais\|did_x | biais\|¬did_x | marge | y_rate |
|------|----:|------------:|-------------:|------:|-------:|
| bindeurs (1,2,5,6,7,8,9) | 0.34–0.73 | +6.2…+8.6 | −3.3…+2.3 | **5.7–10.9** | 0.61–0.87 |
| 0* | 0.17 | +6.70 | **+4.95** | 1.76 | 0.81 |
| 4* | 0.02 | +7.43 | **+6.92** | 0.51 | 0.99 |
| 3* | −0.01 | +8.34 | **+8.37** | −0.03 | 1.00 |

Chez les bindeurs, le gate SUPPRIME Y sur ¬did_x (biais ¬did_x négatif/faible → marge large). Chez les
résistants 3,4, le gate lit correctement did_x=vrai (biais +7-8) mais **produit un biais tout aussi
POSITIF sur ¬did_x** (cible −8) → marge ≈ 0 → Y boosté quel que soit l'état → always-Y (y_rate 0.99-1.00).
Le défaut n'est PAS de détecter did_x, c'est de **supprimer Y quand ¬did_x**.

**Bras 3 — ORACLE (±8 câblé sur did_x VRAI) : 10/10, gap = +1.00 sur TOUS** (y compris 0,3,4). Le canal
logit-Y existe et ±8 suffit à conditionner partout ; la politique de population ne noie pas le gate.

## Interprétation

**Deux régimes distincts parmi les « collapsés ».**
- **Seed 0 = path-dependence (EDR 131 confirmé causalement).** Le warm-start le sauve (0.42), et le
  re-fitting plastique aussi (bras 1). L'info était disponible, seule la trajectoire précoce l'enfermait ;
  la seeder tôt suffit. C'est la validation causale de la piste d'EDR 131 — mais pour 1 seed sur 3.
- **Seeds 3,4 = obstruction plus profonde, PAS de la path-dependence ni de la dérive.** Ils résistent au
  warm-start (seeding MSE), au re-fitting REINFORCE online (le plastique échoue aussi — donc ce n'est pas
  un simple décalage de distribution que l'adaptation en ligne corrigerait), et au gel. À chaque fois, le
  gate n'atteint jamais une marge suppressive : il n'apprend pas à mettre un biais NÉGATIF sur ¬did_x.

**Le locus résiduel est la SUPPRESSION négative, pas la détection.** did_x est rank-décodable partout
(AUC 0.82/0.96, EDR 131) et l'oracle (label vrai) binde 10/10 : le canal et le signal existent. Ce qui
manque sur 3,4 est la capacité du readout à convertir « ¬did_x » en un biais suffisamment négatif pour
supprimer Y — la détection positive (did_x → +8) marche, la suppression (¬did_x → −8) échoue. C'est un
mode d'échec ASYMÉTRIQUE que ni le signal (128), ni le crédit (130), ni l'init/warm-start/gel (132) ne
lèvent.

**Convergence de la chaîne 128-132.** Un gate de conditionnement est NÉCESSAIRE (129) et le warm-start
apporte un gain réel mais PARTIEL (132). Leviers qui n'ouvrent PAS la fiabilité restante : signal (128),
crédit/optim (130), init/warm-start/gel du gate (132). Pour la migration torch-prod : le substrat doit
embarquer un gate de conditionnement **capable d'une suppression négative fiable** (marge), ce qu'un
readout linéaire n'obtient pas sur tous les seeds — piste = readout non-linéaire (MLP/attention) ou
mémoire rendant ¬did_x linéairement suppressible avec marge.

## Bornage / honnêteté

- **Le résultat dépend du correctif d'optimizer.** Le 1er run (double Adam) donnait un NO_RESCUE plat
  7/10 ; c'était en partie l'artefact du choc d'optimizer au trial 1 (revue). Le run propre (un
  optimizer) donne PARTIAL_RESCUE 8/10. Leçon : la plomberie d'optim contaminait précisément le régime
  « path-dependence précoce » qu'on testait.
- **Confond de dérive H_S2 sur le GEL.** Le gate gelé lit une distribution H_S2 qui bouge en phase B
  (population apprend) → ses biais mesurés (bras 2) sont partiellement stale. MAIS l'argument porteur ne
  repose PAS sur le gel : c'est que le **plastique** (re-fitting online, immunisé contre la dérive)
  échoue aussi sur 3,4 → l'obstruction n'est pas qu'une dérive. Le bras 2 sert à VOIR le mode d'échec
  (marge≈0, offset positif), pas à le quantifier absolument.
- **Décalage H_S2 dès le trial 0.** En warm-start la phase S1 n'intercale pas de `pop.learn(s1_reward)`
  entre forward(obs_a) et forward(obs_b), contrairement à la phase B → l'état qui alimente H_S2 diffère
  légèrement dès le départ (source additionnelle de décalage, en plus de l'accumulation).
- **Capacité linéaire in-sample non mesurée.** On n'a pas mesuré si la régression de warm-start atteint
  ±8 EN ÉCHANTILLON chez 3,4 (marge d'entraînement << 16 = limite de séparabilité linéaire stricte) vs
  fitte puis se dégrade. Le fait que le plastique échoue aussi écarte la « pure dérive » mais ne distingue
  pas « linéaire incapable » de « bassin d'optimisation » ; c'est la sonde suivante directe.
- **Oracle = contrôle câblé** (gap 1.00 via le did_x VRAI, indisponible au substrat) : borne le plafond,
  ne mesure pas une capacité apprise.
- `freeze_gate_after_warmstart` n'a d'effet qu'avec `gate_warmstart_trials>0` (voulu : gèle un routage
  DÉJÀ seedé).
- n=10, micro-tâche proxy X-gate-Y, régime hérité 129-131. Les 3 seeds sont déterministes par graine.

Outils : `tools/substrate_ab_compositional.py` (`run_curriculum_fade_gated(gate_warmstart_trials=,
freeze_gate_after_warmstart=, capture_gate_bias=)`, `sweep_gate_warmstart`). Tests
`tests/sandbox/test_substrate_ab_compositional.py`. Confirme partiellement la path-dependence d'EDR 131
(causale mais 1/3), isole le verrou résiduel (suppression de Y sur ¬did_x). Sonde suivante = marge
in-sample de la régression warm-start (séparabilité linéaire stricte vs bassin) et readout non-linéaire.
