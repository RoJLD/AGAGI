---
# frontmatter ajouté rétroactivement (dé-orphanisation P3, 2026-07-15) ; corps d'origine inchangé
id: EDR-102
type: EDR
title: "Le déficit du champion est la MONOCULTURE, pas le génome — la diversité porte l'apex coopératif"
status: legacy
gate: G2
---

# EDR 102 : Le déficit du champion est la MONOCULTURE, pas le génome — la diversité porte l'apex coopératif

> NB numérotation : EDR 098-101 sont pris par l'arc Lewis/métabolisme (sessions parallèles). Ce
> résultat champion/monoculture est renuméroté 102 pour éviter la collision avec l'EDR 100 « biology
> drain » de Lewis.

## Contexte

EDR 097 : le champion HoF cloné ×40 fait pire que la soupe fraîche diverse sur la compétence apex
vivante (apex 0.162 vs 0.211), MAIS le confond n'était pas séparé : génome champion apex-pauvre OU effet
monoculture sur la chasse coopérative. Contrôle (spec `2026-06-24-Monoculture-Vs-Genome-Control`) : bras
`mode="mono_fresh"` = monoculture d'UN génome **frais random** (cloné ×40), comparé en 3-way apparié
(mêmes seeds, sweet spot, 8 ères, 40 agents, 300 ticks).

## Constat — 3-way décisif

| bras | population | median_C | frac_apex (moy) | mammouth (moy/ère) |
|---|---|---|---|---|
| tabula | soupe fraîche DIVERSE | **0.313** | **0.211** | 29.0 |
| champion | monoculture HoF #1 | 0.256 | 0.162 | 18.1 |
| **mono_fresh** | monoculture génome FRAIS | 0.246 | **0.158** | 16.9 |

Contrastes appariés par ère (n=8) :
- **mono_fresh vs champion** : Δapex = **−0.004**, 4/8 ères, **sign_p = 1.000** → **statistiquement
  identiques**.
- **mono_fresh vs tabula** : Δapex = −0.053 (≈ le champion −0.049) → les deux monocultures sont
  également SOUS la population diverse.

## Verdict — MONOCULTURE, tranché

> Une monoculture d'un génome frais random sous-performe la diversité **exactement autant** que la
> monoculture du champion (apex 0.158 ≈ 0.162, sign_p 1.0). **Le champion n'est PAS apex-pauvre** : son
> déficit d'EDR 097 s'explique **entièrement par l'effet monoculture**, pas par la qualité du génome.

La **diversité comportementale** porte la chasse coopérative apex. Cloner *n'importe quel* génome ×40
détruit la coordination du pack de la même façon. C'est cohérent avec EDR 096 (l'apex est une conduite
de PACK, dégâts cumulés) : une population homogène (tous le même comportement) coordonne moins bien la
chasse coopérative qu'une population aux rôles/approches variés.

## Signification — la compétence coopérative est une propriété de POPULATION, pas d'un génome

> Reframe d'EDR 097 : « le champion ne porte pas la compétence » devient « la compétence apex N'EST PAS
> portable par un génome unique — c'est une propriété ÉMERGENTE de la diversité de population ».
> Le HoF (réservoir de génomes individuels) est structurellement incapable de capturer une compétence
> coopérative qui vit dans la VARIÉTÉ, pas dans l'individu. Implication forte pour le transfert ET le
> RSI : un champion sélectionné comme individu, puis déployé en clone, perd la compétence coopérative
> par construction. Cohérent avec [[nas-bottleneck-is-substrate-not-search]] (la sélection d'individus
> ne capture pas la compétence riche) et étend EDR 090 (les champions ne transfèrent pas) : ils ne
> transfèrent pas parce que la compétence n'est pas dans l'individu.

Anti-théâtre : sans le bras de contrôle `mono_fresh`, EDR 097 serait resté ambigu (génome vs
monoculture). Le contrôle a tranché net (sign_p 1.0 mono_fresh≈champion). La décomposition apex par ère
(jamais le scalaire nu) a porté le verdict.

## Caveat — portée limitée par le bug `from_genome` (finding parallèle)

Un bug keystone parallèle (`MambaAgent.from_genome` aplatit l'architecture : hardcode 64/126/172 et
JETTE la topologie du génome) signifie que les 3 bras passent par la MÊME architecture aplatie — seuls
les **poids** diffèrent. Conséquence : (1) le bug est CONSTANT sur les 3 bras → il ne confond PAS la
comparaison inter-bras, le verdict MONOCULTURE (diversité des POIDS > poids homogènes) tient ; (2) MAIS
« le génome champion est innocent » se restreint à ses **poids** — son architecture évoluée n'est jamais
déployée, donc une éventuelle compétence apex ARCHITECTURALE du champion reste **non testée**. Si le bug
`from_genome` est corrigé (préservation des dims), re-faire le 3-way pourrait révéler un effet-génome
architectural aujourd'hui masqué. Le verdict « diversité porte l'apex coop » est, lui, robuste.

## Statut

- Confond EDR 097 RÉSOLU : MONOCULTURE (sign_p 1.0). Le champion-génome est innocent ; le déploiement
  monoculture est coupable.
- **Pistes** (selon l'intérêt) :
  1. **Préserver la diversité au déploiement/transfert** : populations mixtes (≠ clone unique) →
     l'apex coop survit-il au transfert si la diversité est maintenue ? (barreau transfert v2).
  2. **Mesurer la dose de diversité** : balayer la fraction de clones (0% = diverse → 100% = monoculture)
     → courbe diversité→apex (où la coordination s'effondre).
  3. **Sélection au niveau population** (≠ champion individuel) pour un HoF qui capture la compétence
     coopérative.

## Variables d'expérience

Fraction de clones (dose diversité→apex), nombre de génomes distincts dans le mélange, `coop_reward`
(ablation → l'écart diverse/monoculture disparaît-il ?), taille de population, K ères/seeds (puissance ;
ici sign_p 1.0 sur le contraste null, n=8).
