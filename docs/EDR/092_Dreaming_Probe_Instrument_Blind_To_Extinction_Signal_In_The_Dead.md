# EDR 092 : La sonde de dreaming est aveugle à l'extinction — le signal est dans les morts

## Contexte

EDR 091 a isolé le mur central (goulot d'exploration, EDR 014) et choisi l'approche A : réveiller
l'organe de planification MCTS par l'énergie. Hypothèse : l'organe (`+0.5` drain) est sélectionné
CONTRE en régime létal ; abordable au sweet spot. Barreau 0 = une sonde diagnostique
(`tools/dreaming_probe.py`, livrée en subagent-driven, 6 tâches, revue Opus incluse) :
Q1 (l'organe survit-il à la sélection ?), Q2 (paye-t-il ?), verdict 4-cas.

## Constat — premier run réel (`stoneage`, 3 seeds, 40 agents, 400 ticks)

Verdict brut : **MORT**. Mais les chiffres sont *trop propres* : Q1 prévalence-survivants `-0.5`
**identique** sweet et létal (pression 0) ; Q2 `q2b_ratio=1.0` exact sur tous les seeds (= fallback
neutre), `total_dreams_seen=0`. Un instrument qui rend exactement les valeurs de bord n'a rien mesuré.

## Cause-racine — deux bugs d'instrument

**A (primaire) — la sonde mesure les survivants, qui n'existent pas.** `run_era_organ` renvoie
`env.agents` (vivants à la fin de l'ère). Or sur ce substrat la population **s'éteint à 100 %**
avant `max_ticks` (extinction t≈172, **0 survivant**, 153 morts). Liste vide → prévalence 0,
compétence 0, dreams 0, ratios = fallback neutre. Le « MORT » est un **artefact de mesure**, pas une
découverte. La spec elle-même était fausse (« prévalence parmi les survivants » suppose des survivants).

**B (secondaire) — semis d'organe non fiable.** Sur 20 organes demandés, **15 réellement posés** à
l'init : `init_primordial_soup` renvoie des objets génome avec aliasing (deux index → même objet),
et `_set_organ` au mauvais index écrase. Fix : poser l'organe sur le génome **propre à l'agent**
(après `from_genome`, qui `deepcopy`).

## Le signal EXISTE — dans les morts

En mesurant **tous** les agents (survivants + morts), seed 0 :

| | n | âge médian à la mort |
|---|---|---|
| organe ON | 84 | **28.5** |
| organe OFF | 69 | **32.0** |

> L'organe a un **coût de survie réel** (mort à 28.5 vs 32.0), cohérent avec le `+0.5` drain — et
> `total_dreams = 4` (non nul) : le dreaming **peut** s'activer quand l'organe est présent.

Donc l'hypothèse d'EDR 091 reste testable, mais la grandeur correcte est la **mortalité
différentielle** (âge-à-la-mort par organe), pas la prévalence des survivants.

## Signification — la leçon anti-théâtre

> Les 6 tâches étaient « vertes » (unitaires, smoke, revue Opus) parce que la validation portait sur
> la **forme** du retour, pas sur le fait que le substrat réel produit des survivants. **Seul l'usage
> réel a exposé que la mesure était vide.** C'est la limite des tests sur données synthétiques : ils
> ne peuvent pas savoir que le monde s'éteint à 100 %. La décomposition de la sonde
> (`total_dreams_seen` rapporté séparément, exigé par la revue finale) est ce qui a permis de
> distinguer « instrument cassé » de « organe mort » — sans elle, on aurait publié un faux MORT.

## Statut

- Sonde livrée et revue, mais **mesure invalide sur substrat à extinction totale** (bug A) +
  semis non fiable (bug B). À corriger.
- **Prochain** : (1) confirmer que la mortalité différentielle ON<OFF est robuste multi-seed (pas un
  bruit de seed 0) ; (2) fixer A (tous agents) + B (semis par agent) + recadrer Q1 ; (3) re-run.

## Variables d'expérience

Grandeur de survie (âge-à-la-mort médian / censuré / quantile vs prévalence des survivants), seuils
du verdict recadré, fraction de semis, sweet vs létal, profondeur du dreaming (`do_dream_logit`,
`surprise_momentum`) en aval de l'organe.
