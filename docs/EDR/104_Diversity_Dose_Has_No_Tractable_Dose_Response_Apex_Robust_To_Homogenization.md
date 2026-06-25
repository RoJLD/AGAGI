# EDR 104 : La dose de diversité n'a PAS de dose-réponse traçable — l'apex est robuste à l'homogénéisation partielle

## Contexte

Trilogie champion close (EDR 097→102→103, [[coop-competence-is-population-property]]) : le déficit du
champion = MONOCULTURE, pas le génome ni l'architecture. EDR 102 a aussi avancé que « la diversité porte
l'apex coop » sur la base d'un écart tabula(0.211) > monoculture(0.158), soit Δ0.053 — mais ce contraste
secondaire était **marginal** (EDR 097 sign_p~0.07). Seule piste restante du levier diversité : **doser**
la diversité pour voir SI cet écart est une dose-réponse traçable (seuil ? linéaire ? plateau ?), et OÙ
la coordination du pack s'effondre.

Méthode (spec/plan `2026-06-25-Diversity-Dose-Sweep`) : mode `mixture` câblé à
`tools/target_competence_probe.py` — population de `n_clones = round(f·N)` clones d'UN génome frais +
`(N − n_clones)` génomes diversifiés. Balayage de `f ∈ {0, 0.25, 0.5, 0.75, 1.0}` (clones 0→40),
apparié par seed, stoneage sweet spot (0.25/3), K=8 ères, 40 agents, 300 ticks. `preserve_dims` OFF
(no-op apex, EDR 103). + une référence `tabula` PROPRE dans le même batch (garde-fou cohérence des bouts).

## Constat — courbe plate / scatter, aucun contraste significatif

| f (clones) | population | mean frac_apex (K=8) | median_C |
|---|---|---|---|
| **0.0 (réf. tabula propre)** | 40 génomes DISTINCTS | **0.211** | 0.313 |
| 0.0 (mixture, caveat) | 39 génomes (genomes[0] exclu) | 0.172 | 0.277 |
| 0.25 (10) | 10 clones + 30 divers | 0.174 | 0.284 |
| 0.5 (20) | 20 clones + 20 divers | 0.214 | 0.293 |
| 0.75 (30) | 30 clones + 10 divers | 0.167 | 0.271 |
| **1.0 (40)** | monoculture | **0.158** | 0.246 |

Contrastes appariés par ère (frac_apex, sign-test exact, n=8) :
- f=0.0 vs 0.25 : Δ−0.002, sign_p **1.000**.
- f=0.25 vs 0.5 : Δ−0.039, sign_p 0.727.
- f=0.5 vs 0.75 : Δ+0.047, sign_p 0.289.
- f=0.75 vs 1.0 : Δ+0.009, sign_p 0.727.
- **tabula propre vs monoculture (f=1)** : Δ+0.053, 6/2 ères, **sign_p 0.289** (NON significatif).
- tabula propre vs f=0.0 mixture : Δ+0.039, sign_p 0.727 → **le caveat f=0 vaut ~0.039**.

**Aucun contraste n'atteint la significativité** (meilleur sign_p 0.289 ; le minimum atteignable à n=8
est 0.008 pour un split 8/0). La courbe corrigée (vrai bout = tabula propre) **0.211 → 0.174 → 0.214 →
0.167 → 0.158** est non-monotone : f=0.5 (0.214) est AUSSI HAUT que le bout diversifié, les points
intermédiaires scatter dans le bruit inter-ère (σ inter-ère typique ≈ 0.065 ; amplitude brute encore plus large, ex. f=0 va de 0.058 à 0.255).

## Reproductibilité — le harnais est solide, le bruit est dans le phénomène

Double reproduction EXACTE inter-batch valide la mesure :
- **tabula propre = 0.2112** reproduit EDR 102 (0.211) ET median_C 0.313 = 0.313.
- **f=1.0 = 0.158** reproduit mono_fresh EDR 102 (0.158).

Donc le « plat » n'est pas un artefact de mesure. Le caveat d'identité f=0 du spec est CONFIRMÉ et
quantifié : exclure `genomes[0]` (39 génomes cyclés au lieu de 40 distincts) fait chuter l'apex de 0.211
à 0.172 — soit **−0.039, du même ordre que l'écart diverse↔monoculture entier (0.053)**. Un seul génome
absent ≈ la moitié de l'effet recherché : la métrique apex est trop sensible/bruitée à n=8 pour résoudre
une dose-réponse de cette amplitude.

## Verdict — pas de dose-réponse ; apex ROBUSTE à l'homogénéisation partielle

> Diluer la diversité de 0 % à 100 % de clones ne dégrade PAS l'apex de façon monotone. Les dilutions
> intermédiaires (25/50/75 %) restent dans le bruit du niveau diversifié (f=0.5 = 0.214 ≈ tabula 0.211).
> Le seul écart est diverse(0.211) vs monoculture pleine(0.158), Δ0.053, mais **marginal (sign_p 0.289 à
> n=8) ET sans gradient** : la coordination du pack ne s'effondre pas progressivement, elle est ROBUSTE à
> l'homogénéisation partielle. **Le levier « diversité » n'est pas dosable à cette résolution.**

Reframe d'EDR 102 : l'avantage « diversité > monoculture » (~0.05) est réel-en-moyenne mais (1) marginal
en significativité et (2) NON-graduel. Comme dose-réponse, il vit à/sous le plancher de bruit (σ_inter-ère
0.065 > effet 0.05). Le verdict primaire d'EDR 102 (mono_fresh ≈ champion, sign_p 1.0 → MONOCULTURE pas
génome) reste INTACT — ce sweep ne teste que le contraste SECONDAIRE (diverse vs mono) et montre qu'il ne
trace pas de courbe actionnable.

## Signification — convergence avec la méta-leçon substrat

> Comme EDR 090 (pas de premier barreau survivable), 095 (rêve forcé nuisible), D1/A2 (sparsité/MAP-Elites
> no-op), le levier « diversité de population » n'est PAS le verrou de la compétence apex. L'apex coop
> (conduite de pack, dégâts cumulés EDR 096) émerge à un niveau ~0.16-0.21 et y reste, insensible à la
> composition de la population dans une large plage. Le verrou reste le **répertoire du monde / substrat**
> ([[nas-bottleneck-is-substrate-not-search]], [[world-floor-survivability-gate]]), pas un réglage de la
> recherche/sélection/diversité.

Anti-théâtre : décompo `frac_apex` par ère (jamais le scalaire nu), contrastes appariés par seed,
double reproduction exacte des bouts rapportée, caveat f=0 quantifié (pas balayé sous le tapis). Le knob
`CT_CLONE_FRAC` (défaut 0.0 non-régressif) a permis le sweep sans toucher les modes existants.

## Statut

- Levier diversité-apex : **CLOS** comme dose-réponse actionnable. Pas de seuil, pas de gradient ; effet
  diverse↔mono marginal (sign_p 0.289) et non-dosable à n=8. Trilogie 097→102→103 + ce sweep close
  l'axe diversité.
- **Pistes** (rendement décroissant) :
  1. Puissance brute : ré-balayer à n ≫ 8 (eras/seeds par point) pour tenter de résoudre un effet de 0.05
     sous σ 0.065 — coûteux, rendement incertain (l'effet pourrait n'exister qu'aux bouts).
  2. Acter la clôture et pivoter vers le verrou substrat/répertoire (la convergence de 5 EDR le désigne).
  3. Option 2 du chantier (sweep clone-CHAMPION) : non justifiée — la forme est plate avec un génome frais,
     et EDR 103 a montré le champion inerte ; rien ne laisse attendre une forme différente.

## Variables d'expérience

`CT_CLONE_FRAC` (AXE, balayé), n eras/seeds par point (PUISSANCE — le facteur limitant ici : σ 0.065 ≫
effet 0.05 à n=8), génome cloné (frais [ici] ; champion non justifié), `coop_reward` (ablation : l'écart
diverse/mono ~0.05 disparaît-il ?). `preserve_dims` ignoré (no-op apex, EDR 103). Caveat instrument :
le mode `mixture` à f=0 exclut `genomes[0]` (−0.039) → pour un vrai bout diversifié, utiliser le mode
`tabula` (fait ici en réf.).
