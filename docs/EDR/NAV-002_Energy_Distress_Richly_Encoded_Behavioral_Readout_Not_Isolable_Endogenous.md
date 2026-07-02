---
id: EDR-NAV-002
type: EDR
title: La détresse énergétique est richement encodée dans H (encodeur-OK étendu à l'énergie) ; le readout comportemental n'est pas isolable (énergie endogène)
status: accepted
gate: G0
verdict: ENCODER_RICH
---

# EDR-NAV-002 : Le mur d'énergie — encodeur richement OK, readout comportemental non isolable (endogénéité)

> ID préfixé. Territoire NAV (« Navigation & économie d'énergie »). Teste si le mur d'énergie est le
> MÊME READOUT_GAP que la navigation (EDR-NAV-001). Banc `tools/energy_readout_probe.py` (tooling-only).

## Question

EDR-NAV-001 : le mur de navigation = READOUT_GAP (H encode la direction, la tête d'action l'ignore).
EDR 094/099/100 : le mur d'énergie (famine ~tick 5-58) = la politique émet des actions chères/inutiles
au lieu de forager. **Hypothèse unificatrice** (handoff `HANDOFF_TORCH_READOUT_CREDIT.md`) : même défaut
de readout — le substrat représente l'état utile (la **détresse énergétique**) mais la tête d'action ne
le convertit pas en survie (forager plus, gaspiller moins).

## Méthode

Transpose le probe linéaire de NAV-001. Forage Lewis en cohorte fixe (clones du champion, `benchmark_mode`
→ H dim constante), **régime énergie-limité** (metab ∈ {0.25, 1.0}, n_apex=0 : famine confirmée, tous
morts t=58 / t=16). Par (agent, tick) : H, obs, énergie (pré-step), action émise. Décodage `energy_low`
(énergie < médiane) depuis obs (sanity) et H (encodeur) ; test comportemental `d_forage` = P(move | E basse)
− P(move | E haute).

**Fait de cadrage (exploration)** : hp ≈ 758 (phénotype_hp_bonus) ≫ 100 → le soin (action 6) est un
**NO-OP gardé** (l.692 : ne s'exécute que si hp<100), pourtant **émis 14-17 %** du temps → la politique
alloue des décisions à une action sans effet.

## Résultat

### Robuste : ENCODER_RICH (la détresse énergétique est richement dans H)

| metab | n | obs→energy_low | **H→energy_low** | verdict |
|---|---|---|---|---|
| 0.25 | 9869 | 0.832 | **0.887** | ENCODER_RICH |
| 1.0 | 927 | 0.838 | **0.914** | ENCODER_RICH |

`H→energy_low` (0.89-0.91) **dépasse** `obs→energy_low` (0.72-0.83) dans les deux régimes : la dynamique
récurrente **intègre** le signal d'énergie et le représente MIEUX que l'obs instantanée. → **l'encodeur
est excellent** ; le « encodeur OK » de NAV-001 s'étend à une **2ᵉ variable d'état** (l'énergie).

### Non concluant : le test comportemental est CONFONDU (énergie endogène)

`d_forage` **change de signe** selon régime/fenêtre : calibration (t≤80) **−0.226** ; metab=0.25 (t≤200)
**+0.175** ; metab=1.0 **−0.502**. **Cause = l'énergie est ENDOGÈNE au forage** : avoir peu d'énergie
*signifie* avoir mal foragé (causalité inverse) + confond de survie (les survivants tardifs à basse E
sont les bons forageurs). Contrairement à la navigation — où la direction-cible est **EXOGÈNE** (donnée
par la position de la proie, indépendante des actions passées) — aucune corrélation énergie↔action ne
peut isoler le conditionnement de la politique. **Le readout-gap énergétique n'est donc PAS prouvable
comportementalement par ce probe.**

## Interprétation (FAIT vs INTERPRÉTATION)

- **FAIT** : la détresse énergétique est richement encodée dans H (0.89-0.91, > obs), robuste ×2 régimes.
- **FAIT** : le test comportemental `d_forage` est confondu (endogénéité) → signe instable, non concluant.
- **FAIT (descriptif)** : la politique émet un no-op garanti (soin, hp≫100) 14-17 % du temps.
- **INTERPRÉTATION** : **unification PARTIELLE**. La moitié *encodeur* de la thèse readout est **confirmée**
  pour l'énergie (la représentation utile EST présente dans H, comme la direction en NAV-001) → renforce
  « le substrat représente, migrer le READOUT ». La moitié *comportementale* n'est **pas isolable** ici :
  l'énergie, endogène, ne fournit pas de cible exogène pour localiser le readout (là où l'oracle de
  navigation le pouvait).
- **LEÇON MÉTHODO** : un probe de localisation de readout exige un **label-cible EXOGÈNE**. NAV-001 réussit
  (oracle de position) ; l'énergie échoue (endogène). Garde-fou pour les probes futurs.

## Portée / Bornage

1. Le no-op soin (14-17 %) n'est **pas directement nuisible** (gardé, ne coûte pas quand hp≫100) — c'est
   du gaspillage de *bande passante de décision*, pas d'énergie. La famine vient du métabolisme + du
   non-forage (= le gap de navigation, NAV-001), pas de ce no-op.
2. `d_forage` rapporté **descriptivement** uniquement (confondu) — ne PAS l'interpréter comme un signal.
3. Substrat numpy ; R=1/régime mais n grand (9869/927) → l'encodeur (0.89-0.91) est stable.
4. `preserve_frac=1.0` (exigeant : H doit ≥ obs) → ENCODER_RICH est un verdict fort, pas un seuil laxiste.

## Suite

- **Handoff torch** : la cible reste **T1 (NAV readout)** — le seul mur avec un label exogène donc une
  localisation propre. L'énergie confirme la *représentation* (encodeur) mais ne peut pas guider le readout.
- Hypothèse renforcée (handoff, pont inter-murs) : un readout réparé (T1) pourrait lever les deux murs,
  car les deux états utiles (direction, énergie) sont richement dans H ; **mais** seul NAV est mesurable.

Lignée : 094 (mur intrinsèque) / 099-100 (drain=biologie) → NAV-001 (readout gap) → **NAV-002 (encodeur
énergie OK ; readout non isolable, endogène)**. Outil `tools/energy_readout_probe.py`.
Étend [[lewis-energy-economy-wall]] + [[sota-gap-substrate]].
