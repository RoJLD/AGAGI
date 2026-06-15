# EDR 088 — Le bénéfice du contenu CROÎT avec la criticalité (tendance +, mais pas encore robuste à clore Arc 4)

## Contexte

Levier explicite d'EDR 087 (« le contenu du langage ne paye pas — c'est du téléguidage ») : tester si le
CONTENU référentiel paye **quand le monde rend la discrimination décisionnellement coûteuse**. Design =
**sweep dose-réponse** de la fraction de Leurres-pièges (0.33→0.83), 3 bras appariés
(FIABLE/BROUILLÉ/SOLO), métrique **nette** `kills − leurre_hits`, **pré-enregistré** avant tout run
(`docs/superpowers/specs/2026-06-15-EDR088-Lewis-Critical-Content-design.md`). Outil :
`tools/lewis_critical.py` ; stats numpy pures testées (`src/seed_ai/exp_stats.py`). Appariement +
provenance via le **Harness D1**.

## Le retournement pilote → grille (la leçon, d'abord)

| | 0.33 | 0.50 | 0.67 | 0.83 | Tendance JT |
|---|---|---|---|---|---|
| **Pilote K=5** (seed 88) | **+6.4** | −0.2 | −2.0 | +1.0 | z=−1.38 (décroissante) |
| **Grille K=16** (seed 2026) | +0.25 | −1.62 | +0.06 | +0.75 | **z=+2.22, p=0.013** (croissante) |

Le pilote semblait **inverser** l'hypothèse (contenu payant à *basse* criticalité, +6.4 à 0.33). **Sous
puissance, ce +6.4 s'évapore à +0.25** (n=5 → n=16) et la tendance se **retourne vers le positif**, dans
le sens de l'hypothèse pré-enregistrée. *Énième fois qu'un signal à peu de seeds disparaît/inverse sous
puissance* (`057/075/077/082/083/087`, et désormais le pilote 088). On avait commencé à esquisser un
« pré-enregistrement de l'hypothèse inversée » sur la foi du pilote — la grille l'a tué avant qu'on n'y
investisse. **Powerer avant de conclure**, encore.

## Résultat powered (K=16, apparié, seed 2026)

| Leurre | FIABLE−BROUILLÉ (net) | win | Wilcoxon p | net FIA / BROU / SOLO | fires |
|---|---|---|---|---|---|
| 0.33 | +0.25 ± 1.53 SE | 38 % | 0.641 | 4.8 / 4.5 / 3.4 | 84 |
| 0.50 | **−1.62 ± 0.58 SE** | 12 % | **0.018** | 1.8 / 3.4 / 1.6 | 91 |
| 0.67 | +0.06 ± 0.78 SE | 50 % | 1.000 | 1.3 / 1.2 / 1.4 | 77 |
| 0.83 | +0.75 ± 0.41 SE | 56 % | 0.087 | 0.2 / −0.5 / −0.8 | 89 |

- **Tendance (test primaire)** : Jonckheere-Terpstra **z=+2.22, p(croissance)=0.013** ; pente OLS **+1.88**.
- **Niveau haut (0.83)** : IC95 bootstrap apparié = **[−0.06, +1.50]**.
- **Gates** : `decode_act_fires` 77-91 partout (≥5 → mécanisme bien actif) ; World Model actif (surprise=1.0
  observée). Aucun niveau VOID.

## Verdict pré-enregistré (§6)

**PARTIEL** (issue #3). La règle figée pour « **Arc 4 CLOS** » exige *quatre* conditions conjointes :
tendance JT significative **ET** médiane(0.83)>0 **ET** Wilcoxon(0.83)<0.05 **ET** IC borne_inf(0.83)>0.

- ✅ Tendance JT significative et positive (p=0.013).
- ✅ Médiane(0.83) > 0 (+0.75).
- ❌ Wilcoxon(0.83) = 0.087 (≥ 0.05).
- ❌ IC borne_inf(0.83) = −0.06 (< 0).

→ **Arc 4 n'est PAS clos** : l'effet à la criticalité maximale testée n'est pas *robuste*. **Mais la
DIRECTION de la thèse est confirmée sous puissance** : le bénéfice du contenu **croît** quand la
distinction devient décisionnellement coûteuse. Le gate « IC inclut 0 » a fait son office — il a empêché
de revendiquer un +0.75 trop bruité comme une clôture.

## Lecture & anomalie

- **Direction confirmée, magnitude faible.** L'ordre des bras à 0.83 est le bon (FIA +0.2 > BROU −0.5 >
  SOLO −0.8) : le contenu aide *un peu*, le mécanisme décode-et-agis aide *plus* (vs SOLO qui s'effondre).
  Mais à mesure que les pièges dominent, le **net absolu chute pour tous** (moins de Mammouths à tuer) →
  l'écart-contenu se mesure dans un régime de faibles gains, d'où sa fragilité statistique.
- **Anomalie 0.50** : contenu **significativement négatif** (−1.62, p=0.018). À criticalité moyenne,
  FIABLE fait *pire* que BROUILLÉ. Hypothèse : à 50/50, décode-et-agis « confiant » sur-approche des
  cibles ambiguës ; le bruit du BROUILLÉ disperse, par chance moins coûteux. Non-monotonie locale à
  comprendre (la tendance globale reste +).

## Suite (le vrai prochain levier)

Le contenu **commence** à payer quand la distinction devient critique, mais pas encore assez à 0.83 pour
clore. Deux leviers, **dans cet ordre** :
1. **Pousser la criticalité** (niveau **0.92-0.95**, « presque que des pièges ») + **K plus grand**
   (≥24) : si l'effet-contenu y devient robuste (Wilcoxon <0.05, IC borne_inf >0), **Arc 4 se clôt**.
   C'est un *addendum* au pré-enregistrement (même hypothèse, plus de puissance / un point de plus), pas
   un nouveau design.
2. Si l'effet plafonne quand même : acter que le contenu confère un avantage **réel mais petit** (la
   chaîne stratifiée d'EDR 075/082 — nécessaire mais marginal), et documenter pourquoi (le net chute avec
   les pièges → peu de gains à discriminer).

> **Note honnête** : l'« hypothèse inversée » esquissée après le pilote est **abandonnée** — c'était du
> bruit de pilote. La thèse d'origine (le monde de Lewis : le contenu paye quand la distinction est
> coûteuse) **tient directionnellement** ; il lui manque la puissance/criticalité pour franchir la barre.

## Honnêteté

- Verdict directionnel net (tendance p=0.013) ; clôture manquée de peu (IC borne_inf −0.06). Ce n'est ni
  un faux positif ni un négatif profond — c'est un **vrai effet faible, sous le seuil de robustesse figé**.
- Appariement = block-pairing au monde initial (limite D1 connue ; trajectoires divergent après le 1er
  tirage genome-dépendant).
- Substrat = champions HoF (cohérent 087) en régime sweet-spot (085), nuit OFF (086). Le `net` chute avec
  la criticalité (moins de Mammouths) : l'effet-contenu se mesure dans un régime de faibles gains à haute
  criticalité — d'où l'intérêt de pousser K et un point 0.95.

## Variables d'expérience

Fraction de pièges (criticalité), **K/puissance** (12→16→24+), point de criticalité extrême (0.95),
métrique nette vs kills-seuls, hétérogénéité des positifs (Mammouth vs Mammouth+Ours), substrat HoF vs
ré-évolué dans le monde critique. Provenance : `results/lewis_critical_2026.json` (seed 2026, repro D1).

---

## Addendum (2027) — la réplication tue la tendance : **Arc 4 ne se clôt pas** (négatif durci)

Suite du « vrai prochain levier » : on pousse à **criticalité extrême** (niveaux 0.67/0.83/**0.95**) avec
**K=24** (seed 2027, `results/lewis_critical_2027.json`). Si l'effet-contenu y devenait robuste, Arc 4
se clôturait. **Il ne l'est pas — et la tendance de la grille principale ne réplique pas.**

| Leurre | FIABLE−BROUILLÉ (net) | win | Wilcoxon p | net FIA / BROU / SOLO |
|---|---|---|---|---|
| 0.67 | +0.92 ± 0.75 | 54 % | 0.352 | 2.8 / 1.9 / 0.9 |
| 0.83 | **−0.33 ± 0.56** | 46 % | 0.712 | 0.3 / 0.6 / −0.4 |
| 0.95 | +0.29 ± 0.27 | 42 % | 0.295 | −1.2 / −1.5 / −1.2 |
| **tendance** | JT z=**−0.66**, p=**0.746** ; pente −2.53 | — | — | — |

- **À 0.95 (1 Mammouth, 11 Leurres)** : contenu = +0.29, **non robuste** (IC95=[−0.25, +0.83] inclut 0,
  p=0.295). **Pas de clôture.** Le `net` est négatif pour *tous* les bras (le monde est si hostile que
  même bien discriminer ne sauve pas).
- **La tendance ne réplique pas** : la grille principale (2026) donnait JT **p=0.013** (positive) ; ici
  (2027, autre jeu de seeds, K plus grand) **p=0.746** (rien), et **0.83 change de signe** (+0.75 → −0.33).

> **Une p<0.05 sur UNE grille n'a pas tenu sur DEUX.** C'est la leçon la plus forte de 088 : au-delà de
> *powerer*, il faut **répliquer**. Le « +0.75 / tendance p=0.013 » de 2026 était un tirage non-réplicable.

### Verdict consolidé (2026 ⊕ 2027)

**Arc 4 NE se clôt PAS. Le contenu du langage ne paye pas robustement — même dans un monde engineeré pour
rendre la distinction décisionnellement critique jusqu'à l'extrême (0.95).** Cela **confirme et durcit
EDR 087** (le bénéfice est du téléguidage, pas du contenu) : rendre la discrimination *décisive* ne
suffit pas ; les agents **n'exploitent pas le contenu même quand il est critique**.

### Le vrai verrou (re-pointé)

C'est l'**issue #2** anticipée par le pré-enregistrement (« négatif profond → ré-ouvre *pourquoi pas* »).
La réponse pointe vers **EDR 083** : ce n'est pas la *disponibilité* ni la *criticalité* du contenu qui
manque, c'est que l'**USAGE** du signal n'est pas sous **pression de sélection**. Le décode-et-agis est
*imposé* (gated), pas *sélectionné* — comme en 082. Prochain levier : **co-évoluer l'écoute/l'usage du
langage** avec la survie (sélectionner les agents qui *agissent* mieux sur le signal), pas engineerer le
monde davantage. Le monde de Lewis fournit la *demande* ; il manque la *sélection de la réponse*.
