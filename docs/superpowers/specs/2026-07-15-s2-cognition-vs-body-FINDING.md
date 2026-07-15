# S2 Cognition vs Corps — FINDING : la survie du champion vient du CORPS, pas de la cognition (BODY unanime 5/5)

**La survie 4× du champion HoF — la base du verdict S2 « le monde EXIGE l'intelligence » — vient ENTIÈREMENT de son
CORPS évolué (phénotype métabolique), et RIEN de sa cognition (ni perception, ni politique de décision).** Verdict
`BODY` unanime sur les 5 mondes, robuste (corps δ 0.87–0.96, p=0.0025 ; politique survival-neutre-à-négative). C'est la
réponse à « si ce n'est pas la perception, alors quoi ? » — et elle est foundational : **le biosphère ne crée pas de
gradient de sélection pour la cognition sur la survie, seulement pour le corps.**

## La question

S2-ablation avait montré que l'edge de survie du champion n'est PAS causalement perceptif (perception = leurre, régime-
robuste, 5 mondes via la session // S2-002). Le champion utilise l'obs (~29 % des actions) mais survival-neutralement.
Question ouverte : l'edge 4× vient-il de la COGNITION (la politique, ce que l'agent FAIT) ou du CORPS (le génome/
métabolisme, ce que l'agent EST) ?

## Le design — 2×2 GÉNOME × POLITIQUE

`tools/s2_cognition_body.py` + `verdict_cognition_body` (`s2_stats`). 4 cellules via `run_condition` (réutilisé), la
seule nouvelle = `champion_body` (génome champion + `RandomActionBatchModel` = son corps, actions aléatoires, politique
détruite). Décomposition : `policy = _compare(champion, champion_body)` (la politique paie-t-elle sur le corps champ ?) ;
`body = _compare(champion_body, random_action)` (le corps champ + actions random bat-il le floor ?). Verdict gelé
COGNITION / BODY / BOTH / NEITHER.

## Résultat décisif (5 mondes, K=12, max_ticks=200, 20 agents, RAG-off, seed=2026) — BODY unanime

| Monde | verdict | champion | champ_body | rnd_genome | rnd_action | corps δ (p) | politique δ (p) |
|---|---|---|---|---|---|---|---|
| soup | BODY | 26 | 35 | 6 | 6 | +0.94 (0.0025) | −0.31 (0.067) |
| stoneage | BODY | 22 | 25 | 6 | 6 | +0.87 (0.0025) | −0.12 (0.89) |
| agricultural | BODY | 24 | 25 | 6 | 6 | +0.96 (0.0025) | −0.11 (0.89) |
| industrial | BODY | 22 | 25 | 6 | 6 | +0.87 (0.0025) | −0.12 (0.89) |
| famine | BODY | 22 | 25 | 6 | 6 | +0.87 (0.0025) | −0.13 (0.89) |

Trois faits, tous les 5 mondes :
1. **Le CORPS porte tout** : `champion_body` (génome champion + actions RANDOM) survit ~4× le floor (δ 0.87–0.96,
   p=0.0025, le minimum à K=12). Le phénotype métabolique évolué suffit à la survie sans aucune décision.
2. **La cognition ne paie RIEN** : `policy` (champion vs champion_body) est δ NÉGATIF partout (−0.11 à −0.31, jamais
   significatif positif) → `champion_body ≥ champion` dans les 5 mondes : la politique de décision du champion **nuit
   légèrement** à la survie (ses actions volontaires brûlent de l'énergie sans payer ; les actions aléatoires survivent
   plus longtemps sur le même corps).
3. **La politique ne confère rien sans le corps** : `random_genome` (moteur Mamba + génome frais) = 6 = floor
   `random_action` → un moteur de décision sur un corps random ne survit pas mieux que des actions aléatoires.

## Interprétation — foundational

**Pour la métrique de SURVIE (la base du verdict S2 EXIGE), la survie du champion est 100 % son CORPS évolué, 0 % sa
cognition.** Le verdict between-subject « le monde exige l'intelligence » est un **faux-positif** : le monde exige un bon
phénotype métabolique (que l'évolution fournit), pas de la cognition. L'instrument within-subject le prouve causalement.

**Synthèse qui recoupe tout le programme (« proxy 9 / in-world 0 »)** : si la survie ne crée aucun gradient de sélection
pour la cognition (ni perception, ni politique), alors **toute expérience de cognition in-world DEVAIT revenir neutre** —
le monde ne récompense littéralement pas la cognition pour survivre. Ce finding explique mécaniquement l'échec des ~9
tentatives torch/H-unif in-world (toutes NEUTRES) : ce n'était ni le substrat ni le crédit, c'était que **l'objectif de
survie n'a pas de contenu cognitif** ; l'évolution optimise le corps, la cognition reste dormante faute de pression.
Converge [[s2-world-demand-thread]] (survie ≠ life_score), [[lewis-energy-economy-wall]] (« le mur EST la politique/
substrat » — en fait : le mur est que la survie = métabolisme), [[dreaming-organ-not-dead]] (la cognition nuit),
[[within-subject-demand-marker]] (le between-subject faux-positive).

## Caveats (consignés)

1. **« Corps » = phénotype encodé dans le génome** (`update_phenotype` dérive energy_drain/hp/inv_capacity de tranches
   des MÊMES poids que le moteur de décision). `champion_body` isole « les traits de phénotype du génome champion quand
   le réseau de décision n'est jamais invoqué », pas un canal gène-corps orthogonal. Le contraste (survie ⟸ décision-
   network vs phénotype) reste net et unanime.
2. **Portée = SURVIE**, la métrique du verdict S2. Le `life_score`/fitness (proies/lances/mammouth, événements rares)
   pourrait avoir un contenu cognitif — HORS périmètre ici. Reco : rejouer la décompo sur `life_score` (déjà collecté
   par `run_condition`) pour voir si la fitness composite, elle, récompense la cognition.
3. **Politique survival-négative** : `champion_body ≥ champion` est le pattern « cerveau = poids mort » anticipé (revue
   finale caveat #2) — signal fort, pas un misfire (`body_sig` exige δ≥+0.33, ne se déclenche pas sur δ négatif).

## Extension life_score/FITNESS — le benchmark N'EST PAS sauvable en changeant de métrique (BODY aussi, 5/5)

Rejoué sur `life_score` (fitness composite : survie + proies×50 + lances×300 + mammouth×400 ; param `metric` de
`verdict_cognition_body`). **Verdict BODY UNANIME sur les 5 mondes AUSSI**, et plus fort encore :

| Monde | life champ / champ_body / floor | corps δ (p) | politique δ (p) |
|---|---|---|---|
| soup | 52.4 / **104.0** / 0.6 | +0.69 (0.0025) | **−0.29 (0.009)** |
| stoneage | 51.5 / 54.3 / 0.6 | +0.59 (0.0025) | −0.19 (0.038) |
| agricultural | 52.4 / **101.2** / 0.6 | +0.66 (0.0025) | −0.15 (0.007) |
| industrial | 51.5 / 54.3 / 0.6 | +0.59 (0.0025) | −0.19 (0.038) |
| famine | 51.3 / 67.3 / 0.6 | +0.60 (0.0025) | −0.19 (0.025) |

Le CORPS porte la fitness (`champ_body` δ +0.59 à +0.69, p=0.0025) ; la politique du champion est **fitness-NÉGATIVE ET
SIGNIFICATIVE** (δ −0.15 à −0.29, **p<0.05 partout** — bien pire que pour la survie où c'était n.s.). `champ_body`
(actions RANDOM) atteint jusqu'à **2× le life_score du champion réel** (soup/agricultural). La cognition du champion
**RÉDUIT activement** sa fitness.

## Conclusion foundational (complète, triangulée)

**Le biosphère, tel que conçu, ne peut PAS mesurer/sélectionner l'intelligence — ni par la survie, ni par la fitness.**
Perception survival-neutre (S2-ablation) ; politique survival-neutre + fitness-NÉGATIVE (ce run). Les DEUX métriques du
benchmark sont dominées par le CORPS métabolique évolué ; ni l'une ni l'autre ne récompense la cognition. **Explication
mécaniste DÉFINITIVE du « proxy 9 / in-world 0 »** : la pression de sélection (survie ET fitness) n'a jamais créé de
gradient pour la cognition → toute expérience de cognition in-world DEVAIT revenir neutre — ni substrat, ni crédit, mais
un OBJECTIF sans contenu cognitif. Pour mesurer l'intelligence, il faut une tâche à **contenu cognitif explicite** que le
corps ne peut court-circuiter (métrique récompensant une décision obs-conditionnée que la survie/fitness métaboliques ne
capturent pas). Caveat : « corps » = phénotype dérivé des mêmes poids que la décision (`update_phenotype`).
