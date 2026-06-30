---
id: EDR-119
type: EDR
title: Sweep taille cachée compositionnel — la TAILLE n'est PAS le verrou (Issue C ; ×16 cachés sans effet sur les deux substrats ; cap legacy 256)
status: validated
gate: null
verdict: ISSUE C — NOT_SIZE. Grossir la couche cachée ×16 (5→80) ne lève la composition NI pour legacy NI pour torch (hit_end reste au plancher ~0–0.05 partout). RÉFUTE l'interprétation « Issue 2 TAILLE_REQUISE » d'EDR 117 : le verrou est plus profond que la capacité réseau (crédit compositionnel / mémoire récurrente / structure de tâche). Bonus : le substrat legacy est plafonné en DUR à 256 nœuds (LIMIT_N).
---

# EDR 119 : Sweep taille cachée — la taille n'est pas le verrou compositionnel (Issue C)

## Contexte

EDR 117 a conclu **Issue 2 (TAILLE_REQUISE)** : à ~5 cachés, les deux substrats échouent le
means→ends compositionnel (legacy Δ −0.007, torch Δ +0.010), et a posé l'hypothèse que la
**taille/représentation** est un verrou conjoint avec la règle d'apprentissage. Mais la taille
n'avait pas été variée. Ce sweep teste directement l'hypothèse : **grossir la couche cachée
lève-t-il la composition, et pour quel substrat ?**

Mécanisme : `MambaAgent(num_nodes=N)` → hidden = `N − 167` (I/O fixes 59/108). Les deux backends
lisent N dynamiquement. Augmenter N en gardant I/O fixes grossit UNIQUEMENT le canal caché récurrent
(où vit la mémoire « se souvenir d'avoir fait X »).

## Méthode

- **Script** : `tools/substrate_ab_compositional.py` (sweep `sweep(hiddens, inits, seeds, trials, n_agents)`, commit `8ebf59f`+`3c532ed`).
- **Grille** : hidden **{5, 20, 50, 80}** × init **{prod, normalized}** (normalized@5 dédupliqué = prod@5) × backends {legacy, torch} × **5 seeds** {0–4}, **trials=250** (vs 150 en EDR 117, anti-sous-entraînement des gros réseaux). 7 cellules, 70 runs. EXIT CODE python = 0.
- **Double bras d'init** (contrôle du confond échelle d'activation) : `prod` = init MambaAgent `randn×0.1` ; `normalized` = `W *= sqrt(171/(N−1))` (variance d'excitation invariante à N ; = prod au point d'ancrage N=172).
- **Tâche X-gate-Y inchangée** (EDR 117) : S1 émettre X (reward différé 0), S2 émettre Y récompensé +1 SSI X fait en S1 ; `obs_B` n'encode pas `did_X` → mémoire récurrente obligatoire.

### Déviation du plan (forcée par une contrainte architecturale)

Le plan prévoyait hidden=100 (num_nodes=267). **Le substrat legacy plafonne en DUR à 256 nœuds**
(`MambaBatchModel.LIMIT_N = 256`, `src/agents/mamba_agent.py:333` — « Commandement 9 : Stabilité ») :
il clampe `max_N=256` mais les mappings d'index utilisent le N réel du génome → `IndexError: index 266
out of bounds for axis 2 with size 256` dans le NTM compiler. **Le moteur legacy ne peut pas
REPRÉSENTER >256 nœuds.** Grille A/B comparable rabattue à hidden≤80 (num_nodes≤247 < 256). C'est
un FINDING (plafond architectural du moteur legacy), pas un défaut du banc.

## Contrôle de cohérence (anti-théâtre)

Le point d'ancrage hidden=5 (prod) doit reproduire EDR 117, sinon le banc a dérivé :

| métrique | EDR 117 (trials=150) | EDR 119 hidden=5 prod (trials=250) |
|----------|----------------------|-------------------------------------|
| legacy Δ médian | −0.007 | **−0.006** |
| torch Δ médian | +0.010 | +0.028 |
| torch hit_end | ≤ 0.155 | 0.048 (médian) ; ≤ 0.125 par seed |
| legacy hit_end | ~0 | 0.000 |

legacy Δ −0.006 ≈ −0.007 d'EDR 117 (quasi-identique). Le torch Δ est +0.028 vs +0.010 (EDR 117) —
même SIGNE et même plancher hit_end (0.048 dans l'enveloppe ≤0.155 d'EDR 117), mais **~2.8×** ;
les deux restent sous-band (< 0.05) et au plancher, l'écart est attribué au changement trials 150→250
(RNG distinct, pas d'égalité stricte attendue). **Ancrage TENU** (signes + ordres de grandeur + plancher
reproduits ; la divergence torch est nommée, pas glissée). Banc non contaminé.

## Résultats — la courbe (lecture décisive)

Médianes par cellule (5 seeds) :

| hidden | init | legacy Δ | torch Δ | **legacy hit_end** | **torch hit_end** | verdict A/B cellule |
|--------|------|----------|---------|--------------------|-------------------|---------------------|
| 5  | prod       | −0.006 | +0.028 | **0.000** | **0.048** | GRADIENT_GAGNE |
| 20 | prod       | −0.014 | +0.000 | **0.000** | **0.052** | NEUTRE |
| 20 | normalized | −0.010 | +0.000 | **0.000** | **0.052** | NEUTRE |
| 50 | prod       | −0.008 | +0.038 | **0.000** | **0.052** | GRADIENT_GAGNE |
| 50 | normalized | −0.016 | +0.028 | **0.000** | **0.050** | GRADIENT_GAGNE |
| 80 | prod       | −0.002 | +0.014 | **0.000** | **0.014** | GRADIENT_GAGNE |
| 80 | normalized | −0.004 | +0.042 | **0.000** | **0.050** | GRADIENT_GAGNE |

**Courbe hit_end vs taille (la lecture maîtresse) :**
- **legacy hit_end MÉDIAN = 0.000 aux 7 cellules** (Δ médian NÉGATIF partout : il n'apprend jamais,
  dégrade même légèrement). Précision per-seed : quelques 0.06 ISOLÉS aux PETITES tailles (5, 20 :
  2/5 seeds) qui DISPARAISSENT aux grandes (50, 80 : 0.000 sur tous les seeds) → non seulement aucune
  tendance montante, mais un léger DÉCLIN avec la taille (renforce Issue C).
- **torch = ~0.05 PLAT** (0.048 → 0.052 → 0.052 → 0.014/0.050). Ne monte PAS avec la taille ; au mieux
  hit_end=0.125 sur un seul seed (hidden=5, seed=4). Jamais proche d'un sens (>0.3).

→ **Aucun des deux substrats ne décolle du plancher compositionnel, même à hidden=80 (capacité cachée
×16).** La taille n'a aucun effet directionnel.

### Pourquoi les « GRADIENT_GAGNE » par cellule ne sont PAS l'Issue B

Plusieurs cellules verdictent `GRADIENT_GAGNE` (median_diff > band 0.02). C'est l'**edge torch>legacy
persistant et MINUSCULE** déjà mesuré en EDR 115/117 (torch ~+0.04 sur legacy ~0), **invariant à la
taille** — PAS une montée. L'Issue B exigerait que torch CLIMBE en valeur absolue avec la taille ; or
torch est plat à ~0.05. Le verdict A/B par cellule (torch légèrement mieux) et le verdict du SWEEP
(la taille ne lève rien) sont deux lectures distinctes : la première confirme EDR 115, la seconde
tranche Issue C.

### Contrôle d'init

prod et normalized donnent des planchers identiques à chaque taille (legacy 0.000 partout ; torch
~0.05 partout). **Le null n'est pas un artefact d'échelle d'activation.** Nuance gagnée : à hidden=80,
prod tor_he=0.014 mais normalized=0.050 → le creux de prod@80 était partiellement un artefact
d'optimisation/init (le bras normalisé le récupère) ; les deux restent au plancher. Le contrôle a
gagné sa place.

## Verdict : ISSUE C — la taille N'EST PAS le verrou

Grossir la couche cachée ×16 (5→80) ne lève la composition NI pour le hebbien legacy NI pour
l'autograd torch. **Cela RÉFUTE l'interprétation « Issue 2 TAILLE_REQUISE » d'EDR 117** : la taille
était un faux coupable. Le verrou est plus profond que la capacité réseau —

- côté **legacy** : la règle hebbien/TD(0)-numpy n'apprend tout simplement pas le crédit
  compositionnel (Δ négatif à toute taille) ;
- côté **torch** : l'autograd Actor-Critic TD(0) bat marginalement le legacy (cohérent EDR 115) mais
  reste lui aussi au plancher → **le gradient SEUL, même avec ×16 capacité, ne bridge pas le crédit
  différé means→ends** quand `obs_B` n'encode pas `did_X` (la mémoire doit traverser la frontière
  `learn()`, ce que la récurrence LTC + TD(0) à un pas ne fait pas).

Le vrai verrou = le **mécanisme de crédit compositionnel / mémoire récurrente** (TD(λ)/traces
d'éligibilité, mémoire explicite, ou curriculum), PAS le nombre de neurones cachés.

| tâche / régime | legacy Δ | torch Δ | lecture |
|----------------|----------|---------|---------|
| mono-étape (EDR 115/117) | +0.075 | +0.465 | GRADIENT_GAGNE (torch apprend la contingence simple) |
| compositionnelle ~5 cachés (EDR 117) | −0.007 | +0.010 | les deux au plancher |
| compositionnelle 5→80 cachés (EDR 119) | 0.000 plat | ~0.05 plat | **la taille ne lève rien (Issue C)** |

## Caveats

1. **Puissance** : n=5 seeds, sign_p par cellule au plancher (0.062–0.625). La lecture décisive n'est
   PAS le sign-test par cellule mais la **valeur absolue de hit_end** (plancher partout) agrégée sur
   la courbe inter-tailles — robuste car le plancher MÉDIAN est unanime (legacy 0.000 aux 7 cellules ;
   per-seed, seuls quelques 0.06 isolés aux petites tailles, nuls aux grandes → aucune tendance montante).
2. **Cap legacy 256** : la grille A/B comparable s'arrête à hidden=80 (legacy ne représente pas plus).
   On ne peut pas EXCLURE qu'un torch à hidden≫80 (hors portée legacy) décolle — mais l'absence totale
   de tendance entre 5 et 80 le rend improbable ; à tester en torch-only si l'on poursuit.
3. **Confond d'init contrôlé** (bras normalized) : null réel sous les deux inits.
4. **Micro-tâche proxy** : PAS une preuve de transfert apex en prod (même bornage qu'EDR 115/117).
5. **trials=250** : anti-sous-entraînement ; un curriculum progressif ou ≫250 trials pourrait changer
   le tableau (le crédit différé peut exiger une chauffe plus longue) — c'est précisément la suite C.

## Conséquences

- La **porte de décision torch-prod** reste verte (EDR 115 : gradient bat hebbien sur la
  mono-contingence) mais EDR 119 PRÉCISE : passer à torch + grossir les cachés **ne suffira PAS** pour
  la composition. Le substrat cible doit aussi changer le **mécanisme de crédit/mémoire**
  (TD(λ)/éligibilité, mémoire explicite type NTM entraînée par gradient, ou curriculum means→ends),
  pas seulement l'autograd et la taille.
- **Finding architectural** : le moteur legacy est plafonné en dur à 256 nœuds (`LIMIT_N`) → argument
  supplémentaire pour la migration moteur (le substrat actuel ne peut même pas représenter de plus
  grands réseaux).
- Suite recommandée : (a) **curriculum progressif** (récompenser d'abord X seul, puis Y|X) pour réduire
  la difficulté du crédit différé ; (b) **mécanisme de mémoire/crédit** (traces d'éligibilité / TD(λ),
  mémoire explicite entraînée) sur le banc compositionnel ; (c) éventuel torch-only à hidden≫80 pour
  borner le caveat du cap.
- Lien EDR 113/117 raffiné : le γ-sweep no-op (113) ET le sweep taille (119) écartent tous deux la
  taille ET l'horizon-γ comme verrous ; reste le **mécanisme de crédit compositionnel** lui-même.

## Liens

- `[[sota-gap-substrate]]` — audit SOTA : migrer le moteur (plasticité différentiable / mémoire entraînée)
- `[[coop-competence-is-population-property]]` — apex = leviers réfutés ; taille réfutée ici aussi
- `[[nas-bottleneck-is-substrate-not-search]]` — verrou = substrat (mécanisme), précisé : pas la taille
- EDR 117 — Issue 2 (TAILLE_REQUISE) **partiellement RÉFUTÉE ici** (la taille ne lève rien)
- EDR 115 — barreau-0 : gradient bat hebbien sur mono-contingence (edge confirmé size-invariant ici)
- EDR 113 — γ-sweep no-op (horizon écarté ; convergence avec taille écartée ici)
- Outils : `tools/substrate_ab_compositional.py` (sweep), `tools/substrate_ab.py`
- Données : `results/sab_compositional_sweep.json` (per-seed complet)
