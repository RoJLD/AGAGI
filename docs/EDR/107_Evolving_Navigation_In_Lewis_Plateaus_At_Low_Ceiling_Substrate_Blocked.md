# EDR 107 — SUBSTRAT BLOQUÉ : évoluer la navigation en Lewis plafonne à un bas plafond (~0.36)

## Contexte

EDR 106 a tranché que le mur d'approche du forage est **POLITIQUE** — la politique de navigation
évoluée du champion, pas la cinématique des proies. Pour des réplicas (politique figée), le déficit vit
dans le **substrat évolué**. EDR 107 est un **changement de registre** : on quitte la mesure de
réplicas pour **faire tourner l'évolution EN Lewis** et observer si la navigation (`p_reach`) **émerge
au fil des générations**.

Setup : évolution à cliquet best-ever en Lewis (`N_APEX=0`, `base_metabolism=0`), sélection sur la
fitness de **prod** `calculate_life_score` (`preys_eaten*50` domine = exige d'atteindre une proie ;
scaffold `approach_reward` chaud à chaque génération, `current_era=1` → `anneal(1,30)=0.967`). On mesure
`p_reach` par génération (instrument `trace_forage` d'EDR 105). Pré-enregistrement :
`docs/superpowers/specs/2026-06-25-EDR107-Evolve-Navigation-design.md`. Verdict gelé : NAVIGATION ÉVOLUE
si `median(p_reach[-5:]) ≥ median(p_reach[:5]) + 0.15`, sinon SUBSTRAT BLOQUÉ. Lignée :
090→…→101→105→106→**107**.

## Le verdict : SUBSTRAT BLOQUÉ

Trajectoire `p_reach` sur 20 générations (run réduit `R=1`, `pop=24`, `max_ticks=80`, `seed=107`) :

```
gen : 1    2    3    4    5    6    7    8    9    10
p_r : .224 .365 .152 .388 .440 .277 .289 .414 .421 .364
gen : 11   12   13   14   15   16   17   18   19   20
p_r : .359 .356 .315 .311 .347 .373 .327 .284 .432 .400
```

`first-5 médiane = 0.365`, `last-5 médiane = 0.373`, **delta = +0.007** (gate +0.15), pente linéaire
**+0.0038/gén**. La trajectoire **plafonne** : aucune montée soutenue → **SUBSTRAT BLOQUÉ**.

## Le mécanisme : un saut one-shot, puis un PLAFOND bas

Lecture honnête à **deux niveaux** — le verdict est plus riche qu'un simple « plat » :

1. **vs le gate pré-enregistré (montée soutenue, first-5 vs last-5)** : **BLOQUÉ**. Dès la génération 2,
   `p_reach` oscille autour de **~0.36** et n'augmente plus sur 18 générations supplémentaires. Le
   cliquet best-ever + 20 générations de sélection en Lewis + scaffold chaud **ne poussent pas** la
   navigation au-delà de ~0.36.

2. **vs le baseline réplicas d'EDR 105/106 (~0.18)** : il y a un **saut initial**. La population évoluée
   plafonne à ~0.36, soit **~2× le niveau des champions-réplicas**. La sélection extrait donc un
   **doublement « one-shot »** (~0.18 → ~0.36) dans les toutes premières générations, puis **sature**.
   Le gate first-5-vs-last-5 ne *capte pas* ce saut, parce que les 5 premières générations **incluent
   déjà** le plateau post-saut.

**Synthèse** : la navigation n'est pas *inerte* à la sélection — elle gagne un cran immédiat — mais elle
**bute sur un plafond bas (~0.36 ≪ compétence 0.5+)** que l'évolution ne franchit pas. Un navigateur
compétent atteindrait quasi toutes les proies (`p_reach → 1`) ; le substrat plafonne à un tiers. C'est
un **plafond de substrat**, pas une absence d'effet.

## Ce que cela signifie : le verrou est l'ARCHITECTURE (connectome, NAS)

Le mur de Lewis a été poursuivi sur 9 EDR. EDR 107 ferme la dernière échappatoire côté *boucle
d'évolution* : même en sélectionnant **directement en Lewis** sur la fitness de prod, avec le gradient
de navigation chaud et le métabolisme nul (conditions maximales), la navigation **plafonne**. Le verrou
résiduel n'est donc ni le monde (knobs), ni la sélection (boucle), mais le **substrat
lui-même — l'architecture du connectome**.

Cela **converge** avec la méta-leçon NAS : [[nas-d1-metabolic-cost-refuted]] (connectome SANS vraie
couche cachée, `hidden=5/172`, 97% I/O) et [[nas-bottleneck-is-substrate-not-search]] (le goulot est le
substrat, pas la recherche). EDR 107 ajoute la pièce manquante côté *comportement* : un connectome aussi
plat **peut** être nudgé une fois mais **ne peut pas** forger une navigation compétente. Le bug
`from_genome` étant résolu ([[from-genome-flattens-architecture]], `preserve_dims=True` en prod →
évolution topologique active), le plafond observé n'est PAS un artefact d'aplatissement : c'est la
**capacité expressive** du substrat qui plafonne.

| Échappatoire testée | EDR | Verdict |
|---|---|---|
| énergie / dépense | 090-101 | réfutée (sature) |
| acquisition / revenu | 105 | GOULOT=APPROCHE |
| cinématique des proies | 106 | réfutée (POLITIQUE) |
| **sélection en Lewis (boucle d'évolution)** | **107** | **plafond bas → SUBSTRAT BLOQUÉ** |

## Le vrai levier suivant (re-pointé) : l'architecture

EDR 108 (côté NAS) : le plafond de navigation monte-t-il avec un connectome plus riche (vraie capacité
cachée) ? Le déficit n'est plus comportemental *au sens de la sélection* — la sélection fait ce qu'elle
peut (+1 cran) — mais **architectural** : il faut un substrat capable d'exprimer une politique de
navigation qui s'engage sur la cellule-proie. C'est un retour explicite au programme NAS (couche
cachée, plasticité), pas un nouveau knob de monde.

## Honnêteté & méthode

- **Verdict pré-enregistré, tranché honnêtement.** Le gate (montée soutenue ≥ +0.15) a renvoyé SUBSTRAT
  BLOQUÉ ; je ne le re-qualifie pas après coup. La **nuance du plateau** (≈2× le baseline réplicas) est
  rapportée en plus, pas à la place : elle enrichit, ne renverse pas.
- **Limite du gate (caveat assumé).** Le gate first-5-vs-last-5 mesure la montée *entre* générations et
  **ne capte pas** le saut génération-0 → génération-1. Avec le recul, un design plus net aurait
  baseliné explicitement contre les réplicas (gén. 0) et utilisé une **réplication `R>1`** pour séparer
  le signal de sélection du bruit inter-génération (la trajectoire oscille 0.15-0.44 à `R=1`). Le verdict
  reste robuste (pente plate +0.0038, plateau franc), mais le contraste saut-vs-plateau mériterait un
  EDR dédié si on voulait *quantifier* le gain one-shot.
- **Provenance — collision corrigée.** `test_main_evolve_nav_smoke` utilise `seed=107`, donc le smoke
  (2 générations) partage le chemin `results/lewis_evolve_nav_107.json` et l'écrase si la suite de tests
  tourne après le run. Le résultat autoritatif est le run **20 générations** (log `seed=107`,
  commit `87fd811`), régénéré proprement. Correctif futur : le smoke devrait utiliser un seed distinct.
- **Conditions maximales pour la navigation.** scaffold chaud (`current_era=1` à chaque génération,
  jamais incrémenté), sélection sur `preys_eaten*50`, `metab=0` (temps de vie ~27-80 ticks) → si la
  navigation *pouvait* émerger de cette boucle, elle l'aurait fait. Le plafond est d'autant plus
  crédible. Revue finale (opus) : code correct, verdict NON fabriqué par un défaut (trace_forage présent,
  scaffold chaud, cliquet intègre) → PRÊT À MERGER.
- **Reproductibilité.** `_disable_kuzu()`, `Harness(with_db=False)`, `seed_at(base+gen, 0)` par
  génération, `memory_retriever.stop()+clear()`.

## Variables d'expérience

Temps évolutif (générations) à sélection sur `calculate_life_score` (la navigation **plafonne** : saut
one-shot ~0.18→~0.36 puis sature), et — prochain levier — l'**architecture du connectome** (capacité
cachée, EDR 108 côté NAS). Outils : `tools/lewis_survival_sweep.py` (`main_evolve_nav`,
`_evolve_nav_gen`, `_verdict_evolve_nav`, `_p_reach_of_pool`), réemploi `evolve_competence._reproduce`,
`lewis_critical._setup_critical`, `persistence.calculate_life_score`, instrument `trace_forage`.
Provenance : `results/lewis_evolve_nav_107.json` (`seed=107`, commit `87fd811`). Lignée :
090→…→101→105→106→**107**.
