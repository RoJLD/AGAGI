---
id: EDR-CRAFT-001
type: EDR
title: Rétention du craft POLICY-LOCKED — le crafteur ne re-crafte ~jamais en cohorte fixe et aucun levier environnemental n'aide
status: accepted
gate: G1
verdict: POLICY_LOCKED
---

# EDR-CRAFT-001 : La rétention du craft est POLICY-LOCKED (aucun levier environnemental ne la restaure)

> Premier record à ID préfixé (convention `SPECIALITES.md`, Partie 1). Territoire CRAFT. Prolonge et
> corrige EDR 125/127. Banc `tools/craft_retention_probe.py` (tooling pur, aucun `src/` modifié).

## Question

EDR 127 a établi que le craft est ATTEINT en évolution (élite tier-2 de l'archive QD) mais que la
sélection QD ne le « sauve » pas : `frac_craft` reste ~0.011 en cohorte fixe (`benchmark_mode`) →
verrou = **rétention** (« ni substrat inatteignable, ni sélection »). Question ouverte du backlog
cartographe (P1) : **quel levier fait re-crafter une cohorte fixe — mémoire de recette ? incitation ?**

## Méthode

On source le crafteur EXACTEMENT comme EDR 127 (`_evolve_qd_champions`, 12 ères × 30 agents × 400 ticks,
seeds 1260-1262), **mais on l'extrait DIRECTEMENT** des cellules tier-2 de l'archive (`_craft_elites`,
`spears_crafted>0`) au lieu du `archive.sample(5)` uniforme d'EDR 127. On réplique le(s) crafteur(s) à la
cohorte (30 agents) et on mesure sur **cohorte fixe** (`benchmark_mode`, génome figé) sous 4 conditions :

- **baseline** : aucun levier.
- **incitation_flat** : récompense de craft PERMANENTE (`scaffold_craft=5`, `scaffold_eras=0` → jamais annelée).
- **incitation_recraft** : bonus d'énergie (+8) CIBLÉ à chaque incrément de `spears_crafted` (récompense le RE-craft).
- **memoire_recette** : flag « déjà crafté » injecté dans `explicit_memory[0]` après le 1er craft.

Métriques par agent : `frac_craft` (≥1), `frac_recraft` (≥2 = re-craft stable), `total_spears`.

## Résultat (R=3, seeds 1260-1262, crafteur émergé 3/3 : n_craft_elites [2,1,1])

| condition | frac_craft | frac_recraft | total_spears |
|-----------|-----------|--------------|--------------|
| **baseline** | **0.078** | **0.000** | 2.3 |
| incitation_flat | 0.011 | 0.000 | 0.3 |
| incitation_recraft | 0.011 | 0.000 | 0.3 |
| memoire_recette | 0.000 | 0.000 | 0.0 |

`d(frac_craft)` meilleur levier vs baseline = **−0.067**. **VERDICT = POLICY_LOCKED.** (Confirmé en R=1
seed 1260 : baseline 0.100 > tous leviers.)

## Lecture

1. **Correction quantitative d'EDR 127.** Sourcé DIRECTEMENT, le crafteur crafte à **0.078**, pas 0.011 :
   les ~0.011 d'EDR 127 conflaient la **dilution d'échantillonnage** (`sample(5)` uniforme rate presque
   toujours la seule cellule tier-2) avec la rétention. La rétention réelle du *premier* craft est ~8 %,
   pas ~1 %.

2. **Le RE-craft (≥2) est nul PARTOUT.** `frac_recraft = 0.000` en baseline ET sous chaque levier : le
   crafteur évolué, rejoué en ère neuve, ne re-crafte **jamais deux fois**. La rétention comme *comportement
   répété stable* n'existe pas — le craft est un événement one-shot context-déclenché.

3. **Aucun levier environnemental n'aide ; ils DÉGRADENT** (best d = −0.067). Mécanisme (anticipé au design) :
   en cohorte fixe la **politique est FIGÉE** (génome, zéro apprentissage intra-ère). Une « incitation » ne
   peut donc pas façonner le comportement — elle ne modifie que l'**état observé** (l'énergie injectée par
   `scaffold_craft`/bonus), ce qui écarte la politique du **contexte étroit** qui déclenche son craft rare.
   Le flag mémoire perturbe de même une entrée non apprise.

**Conclusion.** Le verrou de rétention du craft est **dans la politique figée / le substrat** (déclencheur
de craft context-fragile + absence d'apprentissage en ligne), PAS quelque chose qu'une incitation ou un
flag mémoire environnemental restaure. Cela **précise EDR 127** (« pas substrat » → en fait le plafond de
rétention EST substrat-side) et **pointe le levier vers l'apprentissage en ligne / la plasticité (moteur
torch)**, cohérent avec l'arc migration ([[sota-gap-substrate]], [[nas-bottleneck-is-substrate-not-search]]).

## Bornage

- **Petit n** : 30 agents/seed, R=3, fracs ~0.08 (~2-3 agents) → le sens (« leviers n'aident pas ») est
  robuste (R=1 et R=3 concordants, `frac_recraft=0` non ambigu) mais l'amplitude du −0.067 est bruitée.
- **Les incitations sont médiées par l'énergie** (elles ajoutent de l'énergie) → elles NE testent PAS
  « l'incitation SOUS apprentissage en ligne » (impossible en cohorte fixe). Le résultat dit « aucun levier
  environnemental ne restaure la rétention d'une politique figée », il ne réfute pas qu'une incitation
  couplée à de la plasticité aiderait — au contraire, il l'ORIENTE.
- **`memoire_recette`** injecte dans un canal (`explicit_memory`) que l'agent évolué n'a pas appris à lire
  comme « flag craft » → son null/dégradation ne réfute que « un flag brut dans un canal non interprété
  n'aide pas ».
- Non testé : plasticité/BPTT in-world sur le craft (= le levier désigné, mais `src/` torch, session //).

## Suite

- Le levier désigné (apprentissage en ligne sur le craft) relève du **moteur torch** (pont SUB/BIND, backlog
  C1-C3) — à coordonner avec le fil torch, pas à implémenter ici.
- Backlog P1 CRAFT : **fermé sur l'axe tooling** (aucun levier environnemental) → verrou déplacé au substrat.
