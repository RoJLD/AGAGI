---
id: EDR-133
type: EDR
title: "Un readout NON-LINÉAIRE additif (MLP tanh sur H_S2) ne débloque PAS la suppression de Y sur ¬did_x des seeds résistants et DÉGRADE la fiabilité (7→5/10 sans warm-start ; 7/10 avec, perd même le rescue du seed 0 d'EDR 132) ; le MLP construit pourtant de grosses marges suppressives sur les seeds qui bindent (4–11) ET l'AUC tardive de did_x reste au niveau des bindeurs chez 0,4 (0.89-0.905 vs 0.87-0.97, plages chevauchantes) → pour 0,4 les features tardives SONT décodables, l'échec est un BASSIN d'optimisation, pas l'expressivité du readout ni la représentation ; seed 3 = cas mixte (AUC tardive 0.72 + collapse le plus profond). Combiné à EDR 132 (init/warm-start ne rescape pas 3,4), les interventions côté GATE (capacité, init) échouent ; formes multiplicatives/attention NON testées"
status: validated
gate: null
verdict: "Test de l'actionnable migration d'EDR 132 (verrou résiduel = suppression de Y sur ¬did_x sur 3,4) : un readout plus riche le débloque-t-il ? Gate refactoré en MLP 1 couche cachée (tanh), gate_hidden ∈ {0=linéaire, 8, 16}, gate learned, régime incitatif fade0.0/pen2, 10 seeds, capture_gate_bias (marge) + AUC tardive de did_x. VERDICT READOUT_NEUTRAL (dégradant). (1) SANS warm-start : linéaire 7/10 ; MLP-8 et MLP-16 = 5/10 — ne rescapent aucun résistant (3,4,0 gap≈0, marge≈0) ET perdent 5,8. (2) AVEC warm-start 250 : linéaire 8/10 (EDR 132) ; MLP-8 = 7/10, perd le rescue du seed 0, 3,4 marge≈0. (3) CONTRÔLE expressivité : le MLP construit des marges suppressives 4–11 sur les seeds qui bindent → fonctionnellement capable de suppression. (4) CONTRÔLE représentation (AUC tardive de did_x, ce que LIT le gate en fin, vs AUC early d'EDR 131) : bindeurs 0.87–0.97 (moy 0.931) ; résistants 0=0.905, 4=0.890 = NIVEAU BINDEUR (le bindeur seed 8=0.870 décode MOINS bien que 0,4 ; plages chevauchantes) ; seed 3=0.722 (plus basse). → Pour 0,4 : did_x est décodable tardivement au niveau des bindeurs, donc l'échec n'est NI l'expressivité du readout NI la représentation tardive → BASSIN d'optimisation (features présentes, optim n'atteint pas la suppression). Seed 3 = cas mixte (représentation tardive un peu plus pauvre + collapse le plus profond). Convergence EDR 132+133 : les deux familles d'intervention côté GATE — capacité (readout non-linéaire additif) et init (warm-start/gel) — échouent sur les mêmes seeds. Migration : ajouter de la capacité/init au gate n'achète PAS la fiabilité (et dégrade) ; la conditionnement fiable de la queue de seeds relève du régime d'optimisation / de la politique de base (empêcher la saturation-Y précoce d'EDR 131), pas de la forme du readout. BORNAGE fort : un seul type de non-linéarité testé (MLP tanh additif) — gating MULTIPLICATIF / attention NON testés → « readout richness réfuté » restreint à l'additif tanh. Rend la sonde « marge in-sample linéaire » d'EDR 132 caduque (le MLP plus expressif échoue aussi + AUC tardive haute chez 0,4)."
---

# EDR 133 : Un readout non-linéaire additif ne débloque pas la suppression — le résiduel est un bassin d'optimisation (0,4), pas l'expressivité du gate

## Question

EDR 132 a isolé le verrou résiduel de la fiabilité du binding : sur les seeds 3,4 (et 0 sous certains
régimes), le gate n'atteint jamais une marge SUPPRESSIVE de Y sur ¬did_x (bias|¬did_x reste positif →
Y boosté partout → always-Y), et ni le warm-start ni le gel ne le rescapent. Actionnable migration
proposé : un readout **plus riche qu'un linéaire** débloquerait peut-être cette suppression. Ce EDR teste
cet actionnable et, sur la revue, ajoute le contrôle représentationnel tardif qui départage bassin
d'optimisation vs features tardives pauvres.

## Méthode

Refactor du gate de `run_curriculum_fade_gated` en readout paramétrable (défaut inchangé) :
- **`gate_hidden=0`** : readout LINÉAIRE `w·H_S2 + b` (init zéros) = rétrocompat EDR 129-132.
- **`gate_hidden>0`** : MLP 1 couche cachée `tanh(H_S2·W1+b1)·W2 + b2`, init aléatoire seedée (zéros =
  gradient mort). Même optimizer/REINFORCE ; warm-start, éligibilité, capture_gate_bias généralisés.

`sweep_gate_readout` : gate learned, régime incitatif (fade0.0/pen2), 10 seeds, gate_hidden ∈ {0,8,16}
SANS warm-start (régime REINFORCE de prod), puis bras confirmatoire MLP-8 + warm-start 250 (parallèle
EDR 132). `capture_probe` étendu : AUC de décodage de did_x depuis H_S2 **tardif** (dernier quart, ce que
lit réellement le gate), en plus de l'AUC early d'EDR 131 → contrôle bassin vs représentation.
Bind = binding_gap_end > 0.30.

## Résultats

**Bras 1 — SANS warm-start : le MLP DÉGRADE (7 → 5/10).**

| readout | n_bind | seeds bound | résistants 3,4,0 |
|---------|:------:|-------------|------------------|
| linéaire | **7/10** | 1,2,5,6,7,8,9 | gap≈0, marge≈0 |
| MLP-8 | 5/10 | 1,2,6,7,9 | gap≈0, marge≈0 (perd 5,8) |
| MLP-16 | 5/10 | 1,2,6,7,9 | gap≈0, marge≈0 (perd 5,8) |

**Bras 2 — AVEC warm-start 250 :** MLP-8 = **7/10** vs linéaire+warm-start **8/10** (EDR 132) ; le MLP
perd même le rescue du seed 0 ; 3,4 restent marge≈0.

**Contrôle expressivité.** Sur les seeds qui bindent, le MLP construit de GROSSES marges suppressives
(**4–11**, biais|¬did_x négatif) → il EST fonctionnellement capable de suppression négative.

**Contrôle représentation — AUC tardive de did_x (ce que lit le gate en fin de phase B) :**

| groupe | AUC early (EDR 131) | AUC late (ce EDR) |
|--------|:-------------------:|:-----------------:|
| bindeurs (7) | 0.956 | 0.931 (plage **0.870–0.973**) |
| résistant 0 | 0.906 | **0.905** (niveau bindeur) |
| résistant 4 | 0.960 | **0.890** (niveau bindeur) |
| résistant 3 | 0.821 | 0.722 (la plus basse) |

Les plages CHEVAUCHENT : le bindeur seed 8 (0.870) décode did_x tardivement MOINS bien que les résistants
0 (0.905) et 4 (0.890). did_x est donc décodable en H_S2 tardif au niveau des bindeurs chez 0,4.

## Interprétation

**Pour les seeds 0,4 : le résiduel est un BASSIN d'optimisation, pas l'expressivité ni la représentation.**
- Ce n'est pas la représentation : did_x est décodable tardivement au niveau des bindeurs (0.89–0.905,
  chevauche la plage bindeuse) — les features que le gate lit SONT là.
- Ce n'est pas l'expressivité du readout : le même MLP réalise des marges 4–11 sur d'autres seeds ; il
  sait exprimer la suppression. Ajouter de la capacité (MLP-8/16) ne débloque rien et NUIT.
- Ni l'init/seeding (EDR 132 : warm-start/gel ne rescapent pas 3,4).
Les features sont présentes et le readout est capable, mais l'optimisation (REINFORCE + warm-start) ne
converge pas vers la suppression sur ces graines : un bassin d'attraction always-Y y enferme la solution
(cohérent avec la saturation-Y précoce d'EDR 131).

**Pour le seed 3 : cas MIXTE.** Son AUC tardive (0.722, plus basse des 10) indique une représentation
tardive un peu plus pauvre, coïncidant avec son collapse le plus profond (y_rate 1.00, marge −0.03) — on
ne peut pas l'attribuer au pur bassin ; représentation dégradée et enfermement optimisation s'y mêlent.

**Convergence EDR 132+133.** Les deux familles d'intervention côté GATE échouent sur les mêmes seeds :
capacité du readout (MLP additif, ce EDR) et init/seeding (warm-start/gel, EDR 132). Avec signal (128) et
crédit (130), les quatre leviers gate-side sont clos. → **Le verrou résiduel n'est pas dans le gate.**

**Migration.** Ajouter de la capacité ou de l'init au gate de conditionnement n'achète PAS la fiabilité et
peut la dégrader. Le gate reste NÉCESSAIRE (129, il débloque la majorité des seeds), mais fiabiliser la
queue relève du RÉGIME D'OPTIMISATION / de la politique de base — empêcher la saturation-Y précoce
(P(Y)→1 annule le gradient différentiel du gate), objectif hors readout.

## Bornage / honnêteté

- **« Readout richness » N'EST PAS épuisé.** Un seul type de non-linéarité testé : MLP **additif** tanh,
  H ∈ {8,16}. Un gating **multiplicatif** (ex. suppression pilotée `−relu(W·h)`) ou une **attention** sont
  structurellement différents et pourraient produire la suppression là où l'additif échoue. La conclusion
  est donc « MLP additif tanh ne débloque pas », PAS « aucune forme de readout ne le pourrait ».
- **Dégradation 7→5 : capacité et init-choc CONFONDUS.** Le MLP change simultanément la capacité ET
  l'init (aléatoire vs zéros du linéaire) ; la perte de 5,8 pourrait tenir à l'init défavorable autant
  qu'à l'optimisation plus dure — non départagé (un MLP init quasi-zéro ou des inits découplées de la
  graine de tâche trancheraient). Le point porteur (3,4 non rescapés, marge NULLE pas juste sous seuil)
  est robuste à cela ; la cause de la perte de 5,8 reste, elle, une hypothèse.
- **AUC pooled agents×trials** (pas per-agent) : mesure population grossière ; mais le CHEVAUCHEMENT des
  plages (bindeur 0.870 < résistants 0,4) est robuste à cette grossièreté pour la réfutation « features
  tardives pauvres » sur 0,4. Seed 3 (0.722) reste au-dessus du hasard (décodable) mais distinct.
- **« Bassin d'optimisation » est INFÉRÉ** de la convergence des échecs + AUC tardive haute (0,4), pas
  d'une caractérisation directe du paysage. La direction causale (forcer la politique de base hors du
  bassin always-Y précoce) reste ouverte — c'est le prochain axe, côté politique de base, pas gate.
- **Init aléatoire MLP** (seedée, déterministe) : n=1 init par graine de tâche → la perte de 5,8 est un
  point unique par seed (pas de répétition d'init).
- n=10, micro-tâche proxy X-gate-Y, régime hérité 129-132, déterminisme par graine.

Outils : `tools/substrate_ab_compositional.py` (`run_curriculum_fade_gated(gate_hidden=, capture_probe=)`
→ `did_x_auc_late`, `sweep_gate_readout`). Tests `tests/sandbox/test_substrate_ab_compositional.py`.
Clôt l'actionnable « readout additif plus riche » d'EDR 132 (RÉFUTÉ pour l'additif tanh : capacité ≠
fiabilité ; features tardives présentes chez 0,4) ; avec 128/130/132 ferme les interventions côté GATE.
Redirige la migration vers le régime d'optimisation / la politique de base (saturation-Y précoce d'EDR
131). Rend la sonde « marge in-sample linéaire » d'EDR 132 caduque. Formes de readout multiplicatives /
attention = piste ouverte non tranchée.
