---
id: EDR-EVO-022
type: EDR
title: "Scellé, ARRÊTÉ AU PRÉ-VOL, jamais conclu : hériter la diagonale ne réduit pas la destruction (13/20 vs 13/20) — la question est SANS OBJET depuis EVO-021/023/024"
status: active
verdict: STOPPED_AT_PREFLIGHT_LEVER_DOES_NOT_BITE_QUESTION_MOOT
gate: G0
tests: [SDR-G0]
adopts: [REF-EXPERIMENT-PREFLIGHT]
extends: [EDR-EVO-021]
---

> ⚠️ **Ce record ferme un tiroir.** Il ne rapporte AUCUNE mesure de la DV primaire scellée : le run
> principal n'a jamais démarré. Il grave (1) la règle telle que scellée, (2) le résultat du contrôle de
> manipulation qui a arrêté le run, (3) pourquoi la question n'a plus d'objet, (4) ce qu'une relance
> coûterait et pourquoi elle n'est pas recommandée. Écrit le 2026-09-06 à partir du commit `180b11e` et
> d'[[EDR-EVO-021]] — aucune simulation n'a été relancée pour l'écrire.

## Question — telle que scellée (`docs/preregistrations/EVO-022.json`, sceau `345b95ee…`)

[[EDR-EVO-021]] (première version) attribuait la destruction d'un lecteur câblé par UN `add_node` (6/10)
au nœud inséré à **diagonale NULLE** (δ = 0.5, nœud à mémoire), qui convertirait un chemin réactif en
chemin dérivant noyé par la dérive (E6). Les six leviers réfutés de l'arc attaquaient la DÉCOUVERTE ;
aucun n'avait touché la FRAGILITÉ.

> **Préserver le caractère temporel du chemin lors d'une insertion lève-t-il quelque chose ?**

* **Levier** : le nœud inséré hérite de la diagonale de sa DESTINATION (`W[j, j]`) au lieu de 0. Purement
  structurel, aucun canal ni sortie nommé. Patch LOCAL au runner (`tools/evo_runs/evo022_run.py:39-55`),
  `src/seed_ai/mutation.py` jamais modifié.
* **Design** : 2 bras × 12 seeds (`add_node` d'origine / diagonale héritée), sous-tâche `throw`,
  `hazard=15`, `W=0` — strictement le dispositif d'[[EDR-EVO-018]] (baseline 0/12). Plafond DÉTERMINISTE
  60 000 agent-ticks/seed (E13), abandons comptés.
* **DV primaire** : taux de seeds LECTEURS — `measure_decision_saliency` > 0.5 sur `obs[5] → logits[8]`.
  DV de survie : âge médian, taux d'erreur.
* **Lecture continue** : Fisher exact bilatéral traité vs baseline ; p < 0.05 → la fragilité est une
  composante RÉELLE du verrou ; p ≥ 0.05 → aucun effet, lecteurs éventuels = observations isolées NON
  élevées (E9).
* **Puissance déclarée** : 40 % vs 0 % détectable (p≈0.04) ; 17 % vs 0 % non (p≈0.48).
* **Contrôle de manipulation OBLIGATOIRE** : le patch doit RÉDUIRE nettement la destruction d'un lecteur
  câblé par UN `add_node` (6/10 en baseline). Sinon « le bras ne teste RIEN et le taux de lecteurs ne
  doit pas être lu ».

## Ce qui s'est passé — chronologie vérifiée sur git

| 2026-09-01 | commit | événement |
|---|---|---|
| 08:26 | `bc1cf80` | EVO-021 v1 gravé : mécanisme « diagonale nulle » proposé, signalé non isolé |
| 08:26 → 08:48 | — | règle EVO-022 scellée ; runner écrit ; **pré-vol exécuté (~90 s)** ; clause de manipulation → `SystemExit(1)` (`evo022_run.py:81-83`) ; `probe_output_block_shift.py` écrit et exécuté (200 insertions) |
| 08:48 | `180b11e` | tout committé ensemble ; EVO-021 corrigé (titre + mécanisme) ; dette « `add_node` ne met à jour ni `num_inputs` ni `num_outputs` » inscrite |
| 09:07 | `f813d3e` | défaut épinglé (`tests/sandbox/test_mutation_index_invariants.py`) |
| 14:41 | `fdad73c` | [[EDR-EVO-023]] : sans AUCUNE croissance de nœuds, 0/12 |
| 16:55 | `d4844fb` | [[EDR-EVO-024]] : correctif `preserve_io_blocks` flag-gated, 0/12 vs 0/12 |

Le run principal (2 × 12 seeds) **n'a jamais démarré**. Aucune sortie n'existe sur disque : aucun fichier
`*evo022*` hors le runner et la règle, aucun log, aucun génome (`data/genomes/` ne contient que
`evo028*`), aucun bail dans `runs/leases/`. Les seules traces du pré-vol sont le message du commit
`180b11e` et deux phrases d'[[EDR-EVO-021]] (l.48-50).

⚠️ [[EDR-EVO-021]] date cette réfutation du « 2026-08-04 » (l.42), comme l'occurrence E9 du registre ;
git la date du 2026-09-01 08:48. La date git fait foi.

## Pré-vol — le contrôle de manipulation scellé a ARRÊTÉ le run

Lecteur câblé (diagonale +10 partout, `W[5, N−O+8] = 3.0`), UN `add_node`, 20 seeds par bras
(`np.random.seed(300+s)`), destruction = `measure_decision_saliency(…, num_agents=6, ticks=20) < 0.5` :

| opérateur | lecteur DÉTRUIT | clause scellée |
|---|---|---|
| `add_node` d'origine | **13/20** (65 %) | référence (EVO-021 : 6/10) |
| `add_node` à diagonale héritée | **13/20** (65 %) | doit faire « nettement mieux » → **NON** |

**Aucune réduction. Le bras traité ne manipule rien ; la DV primaire ne doit pas être lue — elle n'a pas
été mesurée.** Coût : ~90 s au lieu des ~30 min projetées.

Ces chiffres sont portés par le commit `180b11e` et la prose d'EVO-021 ; ils ne sont persistés dans aucun
artefact. Le pré-vol est déterministe (seeds 300+s / 700+s) et reproductible en ~90 s par
`PYTHONPATH=. python tools/evo_runs/evo022_run.py` (le script s'arrête de lui-même). **Non rejoué pour
ce record.**

## Pourquoi le tiroir se ferme — la question n'a plus d'objet

1. **Le mécanisme que le levier visait est réfuté par ce pré-vol même.** Si la diagonale nulle du nœud
   inséré était la cause, l'hériter aurait dû réduire la destruction. 13/20 → 13/20 : elle ne l'est pas.
   Un chiffre le disait déjà : le lecteur n'a qu'UNE arête sur ~173, `add_node` ne peut la scinder que
   ~0.6 % du temps ; 65 % ne vient pas d'une scission.
2. **La vraie cause a été mesurée dans la même heure** (`tools/evo_runs/probe_output_block_shift.py`,
   200 insertions) : `add_node` insère ligne/colonne sans mettre à jour `num_inputs`/`num_outputs` →
   **56 % des insertions DÉSALIGNENT** l'arête (elle survit, pilote autre chose). Gravé dans
   [[EDR-EVO-021]] (mécanisme corrigé) et épinglé par `test_mutation_index_invariants.py`.
3. **La question reformulée sur la vraie cause a déjà sa réponse, dans le même dispositif** :
   [[EDR-EVO-023]] — sans aucune croissance de nœuds (donc sans désalignement possible), **0/12**,
   p = 1.000 ; [[EDR-EVO-024]] — correctif `preserve_io_blocks` (décalage 38/200 → 0/200), **0/12 vs
   0/12**, p = 1.000. La fragilité existe et ne mord pas : on ne détruit pas ce qui n'est pas créé.

Relancer EVO-022 telle que scellée = tester un mécanisme réfuté avec un bras qui ne manipule rien. La
relancer « corrigée » (levier = `preserve_io_blocks`) = refaire EVO-024.

## Verdict

**`STOPPED_AT_PREFLIGHT_LEVER_DOES_NOT_BITE_QUESTION_MOOT`**

* **Mesuré** : hériter la diagonale de destination ne réduit pas la destruction d'un lecteur câblé par
  `add_node` (13/20 vs 13/20, n=20 par bras). Négatif du contrôle de manipulation — c'est le SEUL
  résultat de ce record.
* **NON mesuré** : le taux de lecteurs sous ce levier. Aucun Fisher, aucun seed évolué, aucune DV de
  survie. Toute phrase de la forme « EVO-022 a montré que la fragilité n'est pas un levier » est FAUSSE
  — c'est EVO-023/024 qui le montrent.
* **Sans objet** : la prémisse (mécanisme diagonale nulle) est réfutée et la question corrigée est close
  par EVO-023/024.
* **Ce que le pré-vol a acheté** : ~30 min non dépensées ET la découverte du vrai mécanisme — c'est la
  clause de manipulation scellée qui a forcé à regarder les 65 %. Une des trois interceptions de pré-vol
  de la journée, cf. [[EDR-EVO-023]].

## Ce qu'il faudrait pour relancer — et pourquoi non

| condition | état |
|---|---|
| un levier qui PASSE le contrôle de manipulation (réduit vraiment la destruction) | seul connu : `preserve_io_blocks=True` (0/200) — déjà testé, [[EDR-EVO-024]] |
| une règle re-scellée (le sceau `345b95ee…` fige le levier « diagonale héritée » ; il ne se modifie pas) | `EVO-022-bis.json` à écrire, avec ses propres puissance et contrôle |
| un régime où des lecteurs APPARAISSENT (taux de base > 0), sans quoi 0/12 vs 0/12 est quasi garanti (rétro-audit d'EVO-024) | n'existe pas sous survie seule ([[EDR-EVO-016]], [[EDR-EVO-017]], [[EDR-EVO-018]]) |
| coût | pré-vol ~90 s ; run complet ~30 min projetés par l'auteur (`180b11e`), jumeau exact d'EVO-023 (35 ères × 120 ticks × 30 génomes × 12 seeds × 2 bras, plafond 60 000 agent-ticks/seed) — à confirmer par un smoke avant tout engagement |

La seule question VIVANTE issue de cette lignée n'est pas celle d'EVO-022 : c'est la ré-vérification de la
neutralité de `preserve_io_blocks` **dans un régime à lecteurs** (rétro-audit d'[[EDR-EVO-024]]), qui n'a
de sens qu'une fois un levier de CRÉATION trouvé.

## Portée (hedges)

* Le négatif du pré-vol porte sur UN type de lecteur (câblé, réflexe, `throw`), 20 insertions par bras,
  `measure_decision_saliency` en régime court (6 agents, 20 ticks). Il suffit à faire échouer la clause
  scellée ; il ne mesure pas l'effet du levier sur un génome évolué.
* 13/20 vs 13/20 sur n=20 ne prouve pas l'ÉGALITÉ des deux opérateurs ; il prouve l'absence de la
  réduction « nette » exigée. Une réduction faible resterait invisible — et serait sans objet, le
  mécanisme étant réfuté par ailleurs.
* Les chiffres du pré-vol ne sont persistés hors commit/prose. Une reproduction (90 s, déterministe) les
  confirmerait ; elle n'a pas été faite ici.

## Provenance

Tiroir identifié par la cartographie des taxonomies
(`docs/superpowers/specs/2026-09-02-cartographie-taxonomies.md`, gap T4) : règle scellée, record annoncé
(`"record": "EDR-EVO-022"`), cité comme `[[EDR-EVO-022]]` par [[EDR-EVO-021]] (l.48) et [[EDR-EVO-024]]
(l.100) et par `tests/sandbox/test_mutation_index_invariants.py` — sans fichier. Le cliquet
`check_preregistration_applied.py` le comptait parmi ses règles « sans record écrit » sans jamais échouer
dessus : un tiroir fermé et un run à venir y ont la même signature.

Converge [[EDR-EVO-017]], [[EDR-EVO-018]], [[EDR-EVO-021]], [[EDR-EVO-023]], [[EDR-EVO-024]],
REF-EXPERIMENT-PREFLIGHT.
