---
id: S2-001
type: EDR
title: "Le témoin CAUSAL de « le monde exige-t-il l'intelligence » = ablation WITHIN-subject de la perception, PAS l'existence d'un survivant (between-subject). Corrige le caveat « le champion est un survivant, pas un marqueur » du fil S2. Proxy standalone sur mondes à VÉRITÉ-TERRAIN connue : DEMANDING (action nourricière varie, révélée par l'obs) vs TRIVIAL (action fixe, obs = leurre). Le marqueur BETWEEN « survivant compétent existe » FAUX-POSITIVE sur TRIVIAL (5-7× de demande apparente là où l'obs est inutile) ; le marqueur WITHIN (survie obs-vraie vs obs-randomisée) tranche juste (demand 5-7× / trivial 1.0×). Corroborant limpide : la politique optimale pèse l'obs (|W|) SSI informative (0.996 demanding / 0.000 trivial). Reco : ajouter un bras d'ablation-perception à s2_demand pour un verdict causal"
status: accepted
gate: G0
tests: [SDR-G0]
verdict: WITHIN_SUBJECT_ABLATION_IS_THE_SOUND_DEMAND_MARKER
---

# S2-001 : le témoin causal de demande d'intelligence = ablation within-subject de la perception

## Contexte

Le fil S2 (SDR-G0, EDR-112/118/124) établit que le monde EXIGE l'intelligence : un champion HoF survit 3.4–4.7×
les baselines (random_action/random_genome/reflex) dans 4-5 mondes (p=0.0025), après correction du faux-VOID
(gate `life_score` → survie). Caveat documenté du fil : **« le champion est un SURVIVANT, pas un marqueur »** —
la comparaison est BETWEEN-subject (champion vs baselines SÉPARÉS). Un survivant compétent pourrait exister
dans un monde qui n'exige PAS de traitement d'information, et le champion pourrait gagner par un meilleur
corps/génome plutôt qu'une meilleure COGNITION. Le témoin causal correct est WITHIN-subject (leçon de la probe
3D : « témoin = within-subject, pas plancher théorique », [[vertical-world-3d-not-exploited]]) : ablater la
perception du MÊME agent — si sa survie s'effondre, son traitement d'information est causalement porteur.

## Méthode

`tools/world_demand_marker_probe.py` (pur numpy, standalone). On valide QUEL marqueur détecte correctement la
demande, sur des mondes à VÉRITÉ-TERRAIN connue (survie-bandit : chaque tick une action « nourricière » rend
de l'énergie, le métabolisme ponctionne ; survie = ticks avant énergie≤0, cap 200) :
- **DEMANDING** : l'action nourricière VARIE chaque tick, révélée par l'obs (one-hot bruité) → survivre EXIGE
  de lire l'obs. Vérité-terrain : intelligence demandée.
- **TRIVIAL** : l'action nourricière est FIXE, l'obs est un LEURRE (one-hot d'une action aléatoire,
  non-corrélé) → une politique fixe survit. Vérité-terrain : intelligence NON demandée.

Politique linéaire (logits = W·obs + b) ajustée par hill-climb pour maximiser la survie (perception intacte) —
elle apprend NATURELLEMENT à peser l'obs SSI informative. Marqueurs : **BETWEEN** = survie(ajustée) /
survie(action aléatoire) (« un survivant existe ») ; **WITHIN** = survie(obs vraie) / survie(obs RANDOMISÉE)
(ablation de perception) ; corroborant = |W| (poids sur l'obs). K∈{4,6}, 8 seeds.

## Constat

| monde (K=4) | survie ajustée | ablée | aléatoire | \|W\| obs | BETWEEN | WITHIN |
|---|---|---|---|---|---|---|
| DEMANDING | 200 | 38.5 | 38 | 0.996 | 5.3× | 5.2× |
| TRIVIAL | 200 | 200 | 39 | 0.000 | 5.1× | 1.0× |

(K=6 identique : BETWEEN 7.1× sur trivial, WITHIN 1.0×.) `VERDICT = WITHIN_SUBJECT_ABLATION_IS_THE_SOUND_DEMAND_MARKER`.

## Lecture

- **Le marqueur BETWEEN « un survivant compétent existe » FAUX-POSITIVE.** Dans le monde TRIVIAL (qui n'exige
  PAS de perception), la politique ajustée survit 5.1× l'aléatoire → le marqueur crie « demande » alors que
  l'obs est inutile. « Un survivant bat un dummy » ne prouve PAS que le monde exige l'intelligence : il prouve
  qu'une politique compétente EXISTE, ce qui est vrai même quand cette politique est un réflexe fixe.
- **Le marqueur WITHIN (ablation de perception) tranche juste.** Ablater l'obs effondre la survie SEULEMENT
  dans DEMANDING (5.2× → l'agent redevient un dummy) et pas dans TRIVIAL (1.0× → l'agent ignorait l'obs de
  toute façon). L'ablation within-subject mesure ce qui compte : le traitement d'information est-il CAUSALEMENT
  porteur de la survie.
- **Corroborant limpide** : la politique optimale pèse l'obs (|W|) SSI elle est informative — 0.996 dans
  DEMANDING, **0.000** dans TRIVIAL. Le poids-obs de la politique ajustée est lui-même un marqueur within-
  subject (gratuit, sans ablation) qui concorde parfaitement.

## Conséquences

- **Corrige le caveat central du fil S2** (« survivant ≠ marqueur »). Le verdict S2=EXIGE reste correct MAIS
  son témoin le plus sûr n'est pas la comparaison between-subject (champion vs baselines) — vulnérable au
  faux-positif — c'est l'ablation within-subject de la perception du champion. Le S2 de prod inclut déjà un
  baseline `reflex` (partiellement protecteur), mais le réflexe est une politique HAND-CODÉE distincte, pas le
  champion lui-même privé de sa cognition.
- **Reco actionnable pour `s2_demand`** : ajouter un bras d'**ablation-perception** (le MÊME champion évalué
  avec ses observations randomisées/masquées) ; si sa survie chute vers celle de l'aléatoire, le verdict EXIGE
  devient CAUSAL, pas seulement corrélationnel. Bon marché (zéro ré-évolution, une passe d'éval). Corollaire
  gratuit : logguer le poids que la politique met sur ses entrées.
- **Généralise** au-delà de S2 : tout verdict « le monde/la tâche EXIGE la capacité X » devrait s'appuyer sur
  une ablation within-subject de X, pas sur l'existence d'un agent qui réussit (recoupe le motif « témoin
  within-subject » de [[vertical-world-3d-not-exploited]] et la prudence anti-faux-positif de
  [[power-evaporation-guardrail]]).
- Relié : `tests: SDR-G0`. Nouvel axe méthodologique du fil S2 → ID préfixé `S2-`.

## Caveats

1. Proxy SYNTHÉTIQUE et IDÉALISÉ (survie-bandit, séparation nette DEMANDING/TRIVIAL) : établit la LOGIQUE des
   marqueurs (BETWEEN faux-positive, WITHIN causal), pas des magnitudes in-world. Les chiffres très propres
   (cap 200, |W|=0.000) viennent de la netteté du monde-jouet — c'est voulu pour rendre le contraste sans
   ambiguïté.
2. L'ablation = obs RANDOMISÉE (décorrélée) plutôt que masquée à zéro, pour préserver la distribution d'entrée
   et éviter qu'un zéro ne devienne un signal ; c'est l'ablation standard « perception détruite ». Un masquage
   à zéro pourrait sur- ou sous-estimer selon la politique.
3. Politique LINÉAIRE ajustée par hill-climb (petit espace) ; un substrat plus riche pourrait exploiter l'obs
   autrement, mais la logique du marqueur est indépendante de la classe de politique.
4. Ne re-mesure PAS le S2 in-world (n'amende pas la pré-reg) : c'est un résultat d'INSTRUMENT/méthodologie qui
   recommande un bras d'ablation, à valider sur le vrai champion quand le compute est libre.
