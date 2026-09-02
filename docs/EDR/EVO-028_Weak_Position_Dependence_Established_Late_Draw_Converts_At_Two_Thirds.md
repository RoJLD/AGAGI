---
id: EDR-EVO-028
type: EDR
title: "La dépendance FAIBLE à la position est RÉELLE — un tirage tardif convertit à ~0,65 [0,53 ; 0,79] du taux précoce"
status: active
verdict: WEAK_POSITION_DEPENDENCE_ESTABLISHED
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-027]
---

## Question — élever l'observation non élevée d'EVO-027

[[EDR-EVO-027]] a réfuté la dépendance **FORTE** (LATE ≪ EARLY) et laissé une observation non élevée :
6 porteurs-non-lecteurs LATE contre 2 EARLY, illisible à n=24 (limite scellée : 18/22=0,82 dans la
zone aveugle). Question : l'atténuation faible LATE/EARLY ∈ [0,5 ; 0,818] existe-t-elle ?

**Le design vient d'un panel adversarial (2026-09-02) qui a d'abord tué trois designs** — les 3 juges
avaient convergé indépendamment vers un crossover within-seed ; le réfutateur les a réfutés tous par
la même identité (**classe E20** : dans un crossover à ordre fixe, l'ordre EST la position →
l'estimand est le produit position × carry-over ; équivalence observationnelle exacte, P(faux
verdict)=0,858-0,946). Le design retenu renonce au raccourci : **EVO-027 verbatim, grossi** — la
seule structure qui identifie la position est deux lignées par graine, jamais deux fenêtres par
lignée. Spec : `docs/superpowers/specs/2026-09-02-evo028-weak-position-design.md`.

## Méthode

`tools/evo_runs/evo028_run.py` (explicite, E4 occ.4). 2 bras × **86 seeds** (n dimensionné pour
0,804 de puissance au point observé 0,818), config EVO-027 verbatim : EARLY biais ères 1-15/run 30,
LATE propre 1-20/biais 21-35/run 50, horizon post-fenêtre apparié, N constant 172, budget
agent-ticks E13 + CostGuard 600 s/seed. Règle scellée AVANT run : `EVO-028.json` ; coût scellé par
smoke (`EVO-028-SMOKE`, branche « t_pair ≤ 134 s » : 99,9 s mesuré → 2,39 h < plafond 11 520 s).
Données NEUVES seulement (E9) — aucune fusion avec les 24+24 d'EVO-027 qui ont engendré l'hypothèse.
Ajouts vs EVO-027 : lecture SECONDAIRE sans poids (top-1 de l'élite à la dernière ère, contre la
faille de déflation best-ever relevée par le réfutateur) ; taux PAR paire ; DV |logit| réparée
(`tools/evo_mech_dv.py`) ; champions best+last persistés (`data/genomes/evo028/`).

## Résultats

DV primaire telle que scellée : max de `measure_decision_saliency` > 0,5 sur les 4 paires cibles (best-ever, verbatim EVO-027).

| bras | **lecteurs (DV scellée)** | last-era | hits méd | portage | `age_fin` | N | abandons |
|---|---|---|---|---|---|---|---|
| **EARLY** | **77/86** (0,895) | 78/86 | 10 | 7/7 | 13,0 | 172 | 0 |
| **LATE** | **50/86** (0,581) | 60/86 | 9 | 7/7 | 11,0 | 172 | 0 |

**Les 4 contrôles scellés passent** : hits ratio 0,95 ∈ [0,7 ; 1,4] · portage 7/7 des deux côtés ·
N 172=172 · santé 0,85 ≥ 0,70. **Contrôle positif interne : 77/86 ≥ 29/86.**

**Fisher exact bilatéral : p = 3,9×10⁻⁶.** Ratio LATE/EARLY = **0,649**, IC de Katz 95 %
(asymptotique) **[0,535 ; 0,788]** — dans la bande testée [0,5 ; 0,818].

**Par paire** (jamais publié dans EVO-027 — dette d'ancre fermée) :

| paire | EARLY | LATE |
|---|---|---|
| 5→2, 5→3 (move) | **0/86** | **0/86** |
| 10→8 (throw) | 63/86 | 27/86 |
| 23→14 (accept) | 68/86 | 42/86 |

## Anomalie d'instrument SIGNALÉE (clause scellée) — et analyse de sensibilité

La lecture secondaire a tiré : **10 divergences best-ever/last sur LATE** (seuil scellé : 3) contre
1 sur EARLY — toutes dans le sens déflation (best-ever 0,000 → last 1,000), zéro inverse. La faille
prédite par le réfutateur est RÉELLE : à l'ère 50, un lecteur tardif n'est vu par le best-ever que
s'il bat le pic de fitness historique. **Sensibilité (sans poids, lecture last-era) : 78/86 vs
60/86, p = 9,3×10⁻⁴, ratio 0,769** — significatif et dans la bande. L'anomalie ne renverse pas le
verdict ; elle borne l'atténuation vraie dans **[0,649 ; 0,769]** selon l'instrument de lecture.

## Verdict

**`WEAK_POSITION_DEPENDENCE_ESTABLISHED`** — par la branche scellée « p < 0,05 ET EARLY > LATE ET
santé ≥ 0,70 » :

1. **Un tirage réussi livré tard convertit à ~0,65-0,77 du taux d'un tirage précoce.** La clôture
   d'EVO-027 se PRÉCISE : la dépendance forte reste réfutée (EVO-027 tient — sa règle déclarait
   cette zone illisible à n=24), mais « la position est indifférente » était trop fort — **le verrou
   est le nombre de tirages ET, faiblement, leur position**. L'observation non élevée d'EVO-027
   (6 vs 2 porteurs-non-lecteurs) est élevée au rang d'effet.
2. **La bande (0,818 ; 1,0) est FERMÉE d'avance sur preuve de coût** (panel §1.2 : divergence
   (1−r)⁻², ~9,4× EVO-027 à r=0,9, ~32× à 0,95 ; les deux leviers de compression morts). Combinée à
   ce verdict, **la question de la dépendance à la position est fermée** : forte réfutée, faible
   établie à ~0,65-0,77, résiduelle > 0,818 indécidable au coût acceptable.
3. **Le biais ne convertit que 2 paires sur 4** : move (5→2/5→3) = 0/172 tirages convertis au
   total — l'arête seule ne suffit jamais sur une sortie à argmax (cohérent [[EDR-EVO-010]] « créer
   l'arête ne suffit pas » et la dérive d'état E6). Le déficit LATE est porté surtout par throw
   (27 vs 63), moins par accept (42 vs 68).

## Portée (hedges)

* **Mécanisme non tranché** : |logit| médian in situ EARLY 0,130 vs LATE 0,080 — deux ordres de
  grandeur SOUS les 9-12,5 d'EVO-012 (autre régime : croissance coupée). Ni B-M1 (troncature) ni
  B-M2 (porte gelée) n'est départagé ; l'injection post-run est possible (champions persistés) mais
  non faite ici. DV sans poids, comme scellé.
* **Dette d'instrument consignée** : la DV best-ever déflate le bras long (10/86 mesurés). Tout
  futur design à horizons inégaux doit mesurer au top-1 d'ère FIXE, pas au best-ever — la lecture
  secondaire d'EVO-028 devient la DV primaire candidate du prochain harnais.
* Diagnostic, pas algorithme (le biais connaît les paires) — statut hérité d'EVO-009/027.
* IC de Katz asymptotique ; les comptes bruts (77/86, 50/86) permettent tout recalcul exact.
* Un seul jeu de fenêtres (1-15 vs 21-35) et un seul jeu de tâches ; l'atténuation mesurée est
  celle de CE décalage de 20 ères, pas une loi en fonction de la profondeur.

Converge [[EDR-EVO-027]] (précisé), [[EDR-EVO-012]] (la prédiction mécaniste reste ouverte),
[[EDR-EVO-010]], [[EDR-EVO-026]] (l'érosion 0,85 confirme la pente sans casser la clause),
REF-EXPERIMENT-PREFLIGHT.
