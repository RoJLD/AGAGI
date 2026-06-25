# EDR 105 — GOULOT=APPROCHE : le mur du forage est la NAVIGATION, pas la capture ni le revenu

## Contexte

EDR 101 a clos le thread énergie-**dépense** (090→101) : réduire `base_metabolism` aide ×5 mais sature
à 27 ticks ≪ gate 120, *même à métabolisme nul*. Le second mur est l'**ACQUISITION** : à `N_APEX=0`
(monde vidé d'apex, zéro combat), partant de E=80, les champions s'épuisent en ~27 ticks sans
exploiter les 15 proies régulières. EDR 105 est le **premier pas sur le versant acquisition** —
l'analogue de l'EDR 099 (décomposition du drain), mais pour le **revenu** : on **localise** où le
forage casse avant d'intervenir.

Pré-enregistrement : `docs/superpowers/specs/2026-06-25-EDR105-Forage-Funnel-design.md`. Variable :
`base_metabolism ∈ {0.0, 0.25}` à `N_APEX=0`, reste gelé. `metab=0` porte le verdict (acquisition
isolée) ; `metab=0.25` en contraste. Lignée : 090→093→094→098→099→100→101→**105**.

## L'entonnoir de forage (3 étages séquentiels)

Le forage se décompose en **APPROCHE → CAPTURE → REVENU**, chacun conditionnant mécaniquement le
suivant. Instrumentation opt-in `trace_forage` (inerte par défaut) : `_forage_min_dist` (distance
Manhattan min jamais atteinte vers la proie la plus proche), `_forage_contacts` (attaques
co-localisées), `_forage_income` (énergie brute extraite des proies régulières), + `preys_eaten`.

## Le verdict : GOULOT=APPROCHE

| `base_metabolism` | p_reach | p_cap | income/t | drain/t | captures | min_dist (moy) | n |
|---|---|---|---|---|---|---|---|
| **0.0** (verdict) | **0.18** | **1.00** | 0.000 | 1.656 | 0.38 | 1.24 | 1200 |
| 0.25 (contraste) | 0.38 | 1.00 | 0.000 | 15.479 | 0.68 | 1.19 | 114 |

Cascade « premier étage cassé » : `p_reach = 0.18 < 0.5` → **GOULOT=APPROCHE**. Robuste au contraste :
`metab=0.25` donne `p_reach = 0.38`, lui aussi `< 0.5`.

## Le mécanisme : la navigation, pas la capture ni le revenu

Trois faits, lus dans l'entonnoir :

1. **L'APPROCHE est le mur.** Seuls **18%** des agents (metab=0) atteignent un jour une cellule-proie
   (`min_dist ≤ 0`) ; 38% au contraste metab=0.25. La majorité (82%) ne se tient **jamais** sur une
   proie de toute sa vie.
2. **La CAPTURE est parfaite.** `p_cap = 1.00` aux deux niveaux : **quand un agent atteint une proie,
   il la tue à 100%** (10 dégâts à mains nues one-shotent les proies régulières, hp<50). Le mécanisme
   de capture n'est **pas** le goulot.
3. **Le REVENU est hors sujet (moot).** `income/t` médian = 0 **parce que** 82% ne foragent jamais —
   la cascade s'arrête correctement au premier étage cassé. Le `drain/t = 1.656` confirme exactement
   le résidu ~1-2/tick mesuré en EDR 099/100/101.

**Détail révélateur — la dernière case.** `min_dist` moyen = **1.24** : les agents s'approchent *près*
(le scaffold d'approche les tire à ~1 case), mais **ne franchissent pas la dernière case** pour se
tenir sur la proie. Le mur n'est pas « ils ignorent le gibier » — c'est **le pas final, la
co-localisation**, que ~82% ne réalisent jamais.

## Ce que cela ferme

EDR 105 **localise** l'acquisition : le mur du forage est la **NAVIGATION/APPROCHE**, pas la mécanique
de capture (parfaite) ni la magnitude du revenu (jamais atteinte). Cela **re-confirme la méta-leçon
profonde** (EDR 090, session NAS) : le goulot est le **substrat / répertoire comportemental**, pas un
paramètre de monde. Les champions forgés en *stoneage* naviguent à un rythme stoneage qui **ne les
amène pas sur les proies de Lewis**. Aucun knob d'énergie ne répare cela — c'est le **comportement**
(re-évoluer la navigation en Lewis, ou un scaffold de navigation/capture qui récompense le pas final).

| Étage de l'entonnoir | Mesure (metab=0) | Statut |
|---|---|---|
| APPROCHE | p_reach = 0.18 | **CASSÉ (le mur)** |
| CAPTURE | p_cap = 1.00 | parfait (mains nues one-shot) |
| REVENU | income/t = 0 (moot) | non atteint (82% ne foragent pas) |

## Le vrai levier suivant (re-pointé) : pourquoi le pas final échoue

EDR 106 décomposera **l'APPROCHE elle-même** — pourquoi `min_dist` plafonne à ~1.24 sans toucher 0.
Hypothèses (non mesurées ici) :

- **Cible mobile.** Les proies bougent à chaque tick (`_move_preys`, appelé avant la boucle des
  agents dans `step()`) → l'agent chasse une position qui s'est déjà déplacée ; il colle à ~1 case
  sans jamais coïncider.
- **Trou de gradient du scaffold.** `approach_reward` récompense la **réduction** de distance ; se
  tenir sur la proie ne réduit plus rien → aucune incitation au pas final (le scaffold tire *vers*
  la proie mais pas *sur* elle).
- **Politique de mouvement.** Le répertoire stoneage explore/évite au lieu de s'engager sur la case.

Substrat (`from_genome`/`preserve_dims`, désormais résolu) reste secondaire : même métabolisme nul ne
sauve pas, et le goulot dominant est comportemental, pas un trait métabolique.

## Honnêteté & méthode

- **Verdict surdéterminé, puissance réduite.** Le run gelé (`R=4, n_eval=8, max_ticks=300`) s'est
  révélé **impraticablement lent à metab=0** (agents survivent + se reproduisent → population au cap →
  ères ~1 min/seed ; précédent **identique** à EDR 101). Table issue d'un run **réduit fidèle**
  (`R=1, n_eval=3, max_ticks=150`). La réduction est fidèle au gate (`150 > 120`) et **l'entonnoir
  est une propriété par-agent**, robuste à `n_eval` : `p_reach = 0.18` est estimé sur **n=1200
  agents** (le seuil 0.5 est très loin). Provenance `results/lewis_forage_funnel_105.json`
  (régénérable, `seed=105`, commit `e8b153c`).
- **Caveat de dilution.** À metab=0, `n=1200` (forte reproduction → la descendance, génomes mutés,
  dilue `p_reach`) ; à metab=0.25, `n=114` (peu de reproduction, champions originels dominants,
  `p_reach=0.38`). Les **deux** niveaux échouent le gate 0.5 → le verdict GOULOT=APPROCHE est robuste
  à la dilution.
- **Caveat income brut (revue finale).** Le hook somme `reward` **avant** le cap `energy_max` → il
  surévalue `income_t`, ce qui rend la branche REVENU **conservatrice** (plus dure à déclencher) :
  elle ne peut **pas** produire un faux GOULOT=REVENU. Ici le point est moot (`income_t = 0`), mais
  noté pour exactitude.
- **Anti-circularité (verrou scientifique).** `drain_t` est le coût structurel **forage-indépendant**
  (`bio_metab+terrain+carry + brain+action+mouvement`), jamais `bio_autres` (qui porte le revenu) ni
  `ph_biologie` (qui le nette). La comparaison `income_t < drain_t` est genuinement non tautologique.
- **Reproductibilité.** `_disable_kuzu()` + `Harness(with_db=False)` ; `seed_at` par ère ;
  `memory_retriever.stop()+clear()` ; mêmes seeds appariés entre niveaux. Instrumentation
  `trace_forage` strictement inerte quand off (revue finale : inertie + anti-circularité solides,
  PRÊT À MERGER).

## Variables d'expérience

`base_metabolism` (balayé : {0, 0.25}, GOULOT=APPROCHE aux deux), et — prochain levier — **l'APPROCHE
décomposée** (cible mobile / trou de gradient du scaffold / politique de mouvement). Outils :
`tools/lewis_survival_sweep.py` (`main_forage`, `_measure_forage`, `_verdict_forage`, `_report_forage`,
param `_cfg(trace_forage=…)`), hooks `trace_forage` dans `src/worlds/world_1_stoneage.py`,
`src/seed_ai/exp_stats.py`. Provenance : `results/lewis_forage_funnel_105.json` (puissance réduite,
surdéterminé). Lignée : 090→093→094→098→099→100→101→**105**.
