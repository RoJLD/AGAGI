# Spec — Trois rôles au-dessus de la flotte de sessions : PM, Stratège, Réfutateur

**Date** : 2026-09-16. **Statut** : conception approuvée par robla (approche A, forme du stratège, trois décisions
sur les rôles validées le 2026-09-16), implémentation à planifier. **Portée** : AGAGI seul — la leçon macro vient
d'ELYSIUM (audit du 2026-07-10 : « un writer par fichier, toujours ; pas de bus central »), la décision est locale.
**Backlog** : entrées à créer (section 10).

**Provenance de la section 2.3 et de la section 6** : panel de 5 lecteurs (backlog, registre des erreurs, doctrine,
roadmaps, git 30 jours), fusion en 10 candidats, 3 réfuteurs indépendants par candidat (déjà-dur / saturation /
preuve-ou-anticipation), synthèse ; 37 agents, 772 sondes, 89 min. **Témoin tué** (un candidat entièrement couvert par
la porte 1 devait être réfuté : il l'a été). Quatre des cinq graines de l'orchestrateur sont tombées, deux pour E8 —
les trois chiffres retenus ci-dessous ont été **recomptés par l'auteur de cette spec** avant d'y entrer.

---

## 0. Ce qu'on construit, et pourquoi

robla fait tourner **12 sessions Claude interactives** sur la même machine, dont **6 sur l'arbre AGAGI partagé**
(`~/.claude/sessions/*.json`, cwd identique). Quatre douleurs, toutes retenues : qui fait quoi ; hygiène de l'arbre
partagé ; décider quoi faire ensuite ; coût et charge machine.

Une **session master** qui piloterait les autres a été écartée : elle raisonne sur des rapports (question 4 du
pré-vol), elle est un coordinateur mou face à une doctrine de cliquets durs (E10, 19 occurrences), son contexte
devient le fichier chaud partagé, et elle multiplie la charge machine (30 min → 8 h 30 sous 16 agents). Les deux
vraies fautes de coordination du dépôt (contention kuzu 2026-07-21, commit nu 2026-09-07) ont été closes par des
mécanismes DURS, pas par un coordinateur.

On construit à la place **trois rôles**, chacun une session ou un workflow à périmètre propre, qui **s'appliquent
à eux-mêmes la règle des sessions** : une session prend un périmètre et spawne SES workers dessus ; le PM ne touche
jamais aux workers d'une autre session.

| rôle | périmètre | forme | autorité |
| --- | --- | --- | --- |
| **PM** | qui fait quoi, hygiène de l'arbre, charge, alertes ciblées, tableau, `ROLES.md` | une session en boucle auto-rythmée, un bail `pm` | pull (tableau lu au démarrage de toute session) + push (message rare et ciblé) ; conseille, ne force pas |
| **Stratège** | arbitrage P0→P4, direction, revue des rôles | workflow à prompts FIGÉS, déclenché sur événement, exécuté depuis la session PM | propose ; **robla tranche** dans la conversation du PM ; le PM écrit le bloc 🧭 après accord |
| **Réfutateur** | revue adversariale d'une pré-inscription coûteuse et d'un record à verdict, AVANT sceau / AVANT entrée au graphe | workflow à prompts FIGÉS, invoqué par la session qui scelle ou grave | bloque par frontmatter (`review:` exigé par la porte 1), jamais par jugement seul |

**Ce qui borne l'ensemble** : la méthodologie est saturée (26 commits science / 78 méthodo depuis le 2026-09-01).
Tout rôle publie son coût et son critère de dissolution ; la revue des rôles ne peut pas créer un rôle sans en
réduire un autre tant que le ratio science/méthodo n'a pas franchi 1:1 (section 6.4).

---

## 1. Principes — la doctrine du dépôt appliquée aux rôles

1. **Un rôle naît d'une récidive MESURÉE** (deux occurrences datées qu'aucune porte n'attrape), jamais d'une crainte.
2. **Un rôle porte un instrument et un contrôle positif.** L'instrument est déterministe partout où c'est possible ;
   le jugement LLM ne porte que le résidu. Un contrôle positif = un cas connu que l'instrument DOIT attraper ; un
   no-op exact = un cas sain qu'il ne doit pas accuser ; le plancher de fausses alertes se publie.
3. **Ce qui peut se reformer en silence est un cliquet, pas un rôle.** La mutation attendue d'un rôle est de
   rétrécir en écrivant la porte qui l'aurait remplacé.
4. **Un writer par fichier, toujours.** Chaque fichier de cette spec a un unique auteur (section 4).
5. **Le push est du conseil.** Un message du PM à une session est une information ; l'interdiction passe par le hook.
6. **Les propositions de l'orchestrateur subissent la réfutation comme les autres.** Le 09-14 et le 09-16 l'ont
   montré : l'orchestrateur s'est trompé deux fois sur des prémisses vérifiables.

---

## 2. Les rôles

### 2.1 PM

**Périmètre.** Les quatre douleurs, et la tenue de `ROLES.md`.

**Instrument.** `tools/pm/board.py` (section 3.2), déterministe, calibré par injection. Le PM ne fait que ce que
le tableau ne peut pas faire : investiguer une alerte (un worker en lecture), choisir qui prévenir, nommer un
cliquet manquant, présenter la synthèse à robla.

**Contrôle positif.** Fixtures d'injection à réponse connue : deux bulletins sur le même fichier → alerte A1 ;
bail dont le détenteur est mort → A2 ; commit à 2372 suppressions → A4. **No-op exact** : registre + bulletins
+ git sains → zéro alerte.

**Compteurs (recomputés).** Alertes émises / suivies d'un acte sous 48 h / fausses ; collisions d'arbre évitées vs
subies (empreintes `check_staged_authorship`) ; tokens par tick.

**Dissolution.** Précision < 1/10 sur 30 jours ; ou toute alerte encore émise est devenue attrapable par une porte
(le PM écrit la porte et ne garde que le tableau) ; ou tokens > 15 % de la fenêtre sans qu'un acte suive.

### 2.2 Stratège

**Périmètre.** Ce que le précédent du 09-14 a fait à la main : lentilles indépendantes → réfuteurs → juges à
pondérations opposées → synthèse → décision de robla → bloc 🧭. Plus la revue des rôles (section 6.3).

**Instrument.** `.claude/workflows/strategist.js`, prompts FIGÉS et versionnés ; la session PM passe seulement les
arguments (`mode`, `event`, `today`). Deux modes : `full` (panel complet, sur ta demande ou sur cumul
d'événements) et `delta` (un événement : « ce record déplace-t-il un rang ? », une lentille, un réfuteur).

**Déclenchement (événement, jamais calendrier seul).** Nouveau fichier `docs/EDR/` ; entrée du backlog passée CLOS ;
record RÉTRACTÉ ou -bis ; run nul ou contaminé ; robla. Plancher : `full` au plus tard tous les 30 jours ou 20
records au graphe.

**Contrôle positif.** Un candidat PÉRIMÉ connu (tranché par un record) est glissé parmi les candidats ; les réfuteurs
doivent le tuer, sinon la passe est NULLE et son résultat ne s'écrit pas.

**Compteurs.** Propositions faites / acceptées par robla / amendées / réfutées par son propre panel (baseline :
la reco du 2026-09-08, tombée sur deux prémisses fausses) ; arbitrages renversés en moins de 7 jours ; tokens par passe.

**Dissolution.** Deux passes `full` consécutives sans changement de rang accepté ; ou témoin non tué deux fois
(le jeu de prompts est re-scellé, pas le rôle) ; ou coût > 15 % de la fenêtre.

### 2.3 Réfutateur

**Naissance mesurée.** E8 : 5 occurrences en 8 jours sur la PROSE des records (`REGISTRE_ERREURS.md`, E8) ; E19 :
10 occurrences, un record entier rétracté (RETAIN-COMPOSE, 0,173 → 0,923 au seul `lr`) ;
`assert_verdict_invariant_to_optimizer` a un seul appelant réel pour 11 points d'entrée d'apprentissage ; la revue
adversariale, obligatoire depuis le 2026-07-21, a été appliquée à 1 des 28 records récents (E10). Recompté le
2026-09-16 : **47 records citent un paramètre de régime, 4 citent un bloc `regime`** ; **69 chemins `results/`
cités par les EDR, 20 non suivis par git, 18 absents du disque**.

**Périmètre — deux moments, jugement seul.**
1. **Avant le hash d'une pré-inscription** dont `cost_estimate` dépasse un seuil : seuils hérités d'un autre
   dispositif, taille RÉELLE de la famille de contrôles, maillons déclarés `measured` l'étant vraiment, bras
   d'optimisation inégale.
2. **Avant qu'un record à verdict** (`gate:` ou `tests:`, hors -bis de markup et smokes) entre au graphe : chaque
   affirmation de configuration ou de mécanisme confrontée à une mesure PUBLIÉE (bloc `regime`, dose, plancher du
   no-op) ; pour tout nul comparatif, le balayage du pas (nominal ET appliqué). La prose se confronte à la MESURE,
   le mécanisme au CODE (E26/E29 ont été trouvées en lisant le code).

Tout ce qui est décidable par grep lui est **retiré et livré comme porte, AVANT sa première invocation** (sinon il
est E10 comme la règle qu'il remplace) — section 3.5.

**Instrument.** `.claude/workflows/refutateur.js`, 8 à 10 prompts FIGÉS numérotés, versionnés dans
`docs/REF/REF-REVUE-ADVERSARIALE.md` ; exécuté dans un contexte séparé qui LANCE ses sondes (grep, python,
`git show`) ; une passe, sortie ≤ 40 lignes, chaque critique avec `fichier:ligne` ou sortie de commande.

**Contrôle positif, à CHAQUE revue.** Le même jeu de prompts passe d'abord sur trois records-témoins gelés à leur
SHA historique — EDR-GRAB-COST au 2026-09-09 (`forage_payoff = 3.0` jamais mesuré), S2-BLIND-CHAMPION v1 (phrase
jamais mesurée), EDR-RETAIN-COMPOSE avant rétractation (nul sans balayage du pas) — et doit retrouver le défaut
connu de chacun, sinon la revue du jour est NULLE. **No-op exact** : un record sain gelé (LOCK-002) passe avec ≤ 1
critique non confirmée ; ce plancher se publie dans `ROLES.md`.

**Compteurs.** Critiques émises / confirmées (menant à un -bis, une correction ou une entrée de registre) /
fausses ; taux de re-scellage APRÈS run (baseline : 3 sur 58 pré-inscriptions).

**Dissolution.** < 1 critique confirmée sur 10 revues ; ou ≥ 80 % des critiques confirmées attrapables par une porte
(il écrit la porte et rétrécit) ; ou le taux de re-scellage après run ne baisse pas sous 3/58 après 20 sceaux
revus ; ou tokens > 15 % de la fenêtre sans qu'un verdict aval change.

---

## 3. Composants

### 3.1 Bulletin de session — écrit par des hooks, jamais de mémoire

Le registre natif `~/.claude/sessions/<pid>.json` porte déjà `sessionId`, `name` (`agagi-11`), `cwd`, `pid`,
`startedAt`, `updatedAt`, `kind`. Le bulletin n'ajoute que ce que Claude Code ignore.

**Fichier** : `<data_root>/sessions/<sessionId>.json`, chemin servi par `src/paths.py::sessions_dir()` (porte 12) ;
`data/sessions/` entre dans `.gitignore`. Champs :

```
session_id, name (joint au registre à l'écriture, null si absent), pid, cwd,
branch, worktree, started_at, heartbeat_at, ended_at,
claims: ["P4.9"],            # volontaire : python -m tools.pm.bulletin claim P4.9
files_touched: [...],        # chemins des Edit/Write de CETTE session (plafond 200, FIFO)
last_tool_at
```

**Hooks** (`.claude/settings.json`, suivi par git — s'applique aux 6 sessions et aux worktrees) :

| événement | action | budget |
| --- | --- | --- |
| `SessionStart` | crée le bulletin ; **imprime le résumé de `BOARD.json` en cache** (≤ 25 lignes) → la session naît en sachant qui est sur quoi, l'état des bails, la charge | < 1 s : le hook lit un cache, ne recompute jamais |
| `PostToolUse` sur `Edit|Write|MultiEdit|NotebookEdit` | ajoute `tool_input.file_path` à `files_touched`, met `last_tool_at` | < 100 ms |
| `Stop` | `heartbeat_at`, `branch`, `worktree` (un `git rev-parse` local) | < 300 ms |
| `SessionEnd` | `ended_at` | — |

Commande : `python "$CLAUDE_PROJECT_DIR/tools/pm/bulletin.py" <event>` ; le hook lit le JSON sur stdin. **Aucun
backtick, aucune séquence d'échappement dans la chaîne de commande** (règle CLAUDE.md). Un hook **sort toujours 0** :
une erreur s'écrit dans `<data_root>/pm/hook_errors.log`, jamais dans la session.

Le P-item revendiqué reste volontaire ; à défaut, le tableau l'infère des `files_touched` croisés avec les chemins
cités par les entrées du backlog, et le marque `inféré`.

### 3.2 Tableau — `tools/pm/board.py`, déterministe

**Sources**, chacune lue par une fonction séparée qui rend `None` si indisponible (jamais une valeur par défaut —
porte 14) : registre natif filtré sur le cwd du dépôt et ses worktrees ; bulletins ; `git worktree list --porcelain` ;
`git status --porcelain` de l'arbre partagé ; `git log --since=24h --shortstat` ; bails via `tools.jobs` (lecture
seule, comme `doctor`) ; processus python dont la ligne de commande vise `tools/` ou `run_*` (psutil) ; backlog
(entrées et chemins cités).

**Calcul** : `compute(snapshot) -> Board`, fonction PURE sur un instantané injecté — c'est ce que les tests
appellent. Alertes déterministes, chacune avec sa preuve :

| id | alerte | preuve portée |
| --- | --- | --- |
| A1 | un fichier dans `files_touched` de ≥ 2 sessions vivantes | les deux noms, le fichier, l'heure |
| A2 | bail dont le détenteur est mort, ou plus vieux que son TTL | `doctor` |
| A3 | worktree sans session dont la branche est fusionnée ou inactive > 7 j | chemin, branche, dernier commit |
| A4 | commit < 24 h à ≥ 500 suppressions, ou dont un compte d'entité baisse (réutilise `check_amputation`) (E22) | SHA, `+/-`, entité |
| A5 | ≥ 2 simulations en vol, ou charge CPU moyenne sur 5 min > 80 % | PID, commandes, bail tenu ou non |
| A6 | deux sessions revendiquent le même P-item | noms, P-item |
| A7 | session active > 1 h sans revendication ni inférence | nom |
| A8 | heartbeat vieux > 2 h avec PID vivant | nom — information, pas alerte |

**Sorties**, writer unique = PM : `<data_root>/pm/BOARD.json` (machine, lu par le hook) et `<data_root>/pm/BOARD.md`
(lisible). Le tableau publie aussi le chiffre **« charge connue »** (simulations en vol, charge CPU) que tout coût
mesuré doit citer (E12).

**Aveuglement visible.** Une source indisponible produit une ligne `AVEUGLE SUR <source>` en tête du tableau et
supprime les alertes qui en dépendent — jamais un « 0 alerte » silencieux.

### 3.3 Tick PM — protocole `/pm`

Un skill de projet `.claude/skills/pm/SKILL.md` définit le tick ; la session PM le boucle avec `/loop` auto-rythmé
(20-30 min ; `ScheduleWakeup`).

1. **Unicité** : au premier tick, `hold("pm", owner=<name>)` de `tools/jobs`. Bail occupé → la session refuse le
   rôle et nomme le PM vivant. `doctor` voit le PM comme tout autre bail.
2. `python -m tools.pm.board` → `BOARD.json`.
3. **Diff des alertes** contre `<data_root>/pm/alerts.jsonl` (append-only, writer PM). Alerte nouvelle → une action
   parmi : message ciblé (`SendMessage` au `name` du registre, **une fois par alerte et par session**, jamais deux
   fois la même) ; investigation (un worker en lecture, chemins absolus) ; note. Alerte disparue → `suivie`.
   Alerte répétée à deux ticks distincts → le PM **inscrit le cliquet manquant** au backlog avec la preuve (règle du
   registre : deux fois documenté → promu).
4. **Événements pour le stratège** (section 2.2), détectés par diff : nouveau `docs/EDR/*.md`, entrée passée CLOS,
   `RÉTRACTÉ`/`-bis`, run nul. `delta` immédiat ; file pour `full`.
5. **Compteurs** : `python -m tools.pm.roles_counts` recompute les balises `count:` de `ROLES.md` (section 6.2).
6. `ScheduleWakeup` ; `noop=true` si rien n'a changé.

Le PM ne tient **aucun état en contexte** : un redémarrage relit `BOARD.json`, `alerts.jsonl`, `ROLES.md`.

### 3.4 Stratège — `.claude/workflows/strategist.js`

**Phases figées** : candidats (lentilles : stratège scientifique, réfutateur dédié, débit/coût, instruments in-world,
ingénierie du dépôt, chercheur extérieur, north-star ; **Organisation** ajoutée sur les événements de la section 6.3)
→ fusion → réfutation à 3 lentilles (périmé-ou-doublon / coût-et-méthode / valeur) → 3 juges à pondérations
opposées → synthèse. Chaque candidat cite `fichier:ligne` ; chaque réfutation vérifie la preuve (E8).

**Entrées** : `args = {mode, event, today}` ; le PM ne rédige aucun prompt.

**Sortie** : JSON structuré, que le PM écrit dans `docs/roadmap/STRATEGE_PROPOSITION.md` (writer PM), avec la
**prémisse qui porte chaque arbitrage** et le sort du témoin. robla tranche dans la conversation ; le PM écrit
alors le bloc 🧭 de `PRIORITES_ET_DETTES.md` en commit path-scoped, après `snapshot`/`verify` de
`check_staged_authorship`. Sans accord, le bloc 🧭 ne bouge pas.

### 3.5 Réfutateur — portes d'abord, workflow ensuite

**Portes livrées AVANT la première revue** (chacune avec contre-exemple gelé et ligne dans `check_gate_mutation`) :

| porte | règle | baseline gelée | contre-exemple |
| --- | --- | --- | --- |
| **18 `check_regime_claims`** | un record citant `forage_payoff|flip_p|reward_scale|lr=|n_agents|max_ticks` doit citer un bloc `regime` d'un `results/*.json` SUIVI par git dont la valeur concorde | les 43 records légataires (47 − 4) | EDR-GRAB-COST au 2026-09-09 |
| **19 `check_evidence_provenance`** | tout chemin `results/` cité par un record existe et est suivi par git (ou publié par son hash) | les 20 non suivis / 18 absents actuels, listés | un record citant un `results/` absent |
| **20 garde E19** | un runner scellé dont la pré-inscription compare des bras sous gradient appelle `assert_verdict_invariant_to_optimizer` — même forme que la porte 11 pour `declare_design` | appelants actuels | RETAIN-COMPOSE avant rétractation |
| **porte 1 étendue** | tout NOUVEAU record à `gate:`/`tests:` porte `review:` (chemin d'un fichier de revue horodaté, verdict par prompt) ; `preregister.py` exige `reviewed_by` au-dessus du seuil de coût | records existants | un record neuf sans `review:` |

**Workflow** `refutateur.js` : `args = {target, kind: 'record'|'prereg', today}`. Phase 0 : témoins et no-op
(section 2.3) — échec → sortie `NUL`, rien d'écrit. Phase 1 : les 8-10 prompts sur la cible, chacun dans son propre
contexte, avec sondes. Phase 2 : consolidation en `docs/reviews/<date>-<cible>.md` (writer : la session qui a invoqué
la revue), que le frontmatter `review:` référence.

### 3.6 `ROLES.md` — le registre des rôles

`docs/roadmap/ROLES.md`, suivi par git, **writer unique = PM**. Une ligne par rôle ou lentille, statut
`instancié | candidat | dissous`, et **cinq colonnes obligatoires** : instrument, contrôle positif, coût mesuré,
compteurs, critère de dissolution. `check_guard_negative_cases` exige les cinq, comme il exige un contre-exemple à
toute garde ; une ligne incomplète bloque le commit.

Les **candidats réfutés le 2026-09-16** y entrent en `candidat`, avec la raison de réfutation et leur critère de
naissance, pour que la lentille Organisation les retrouve (section 9).

---

## 4. Flux de données — un writer par fichier

| fichier | writer unique | lecteurs |
| --- | --- | --- |
| `~/.claude/sessions/<pid>.json` | Claude Code | `board.py` |
| `<data_root>/sessions/<sid>.json` | les hooks de CETTE session | `board.py` |
| `<data_root>/pm/BOARD.json`, `BOARD.md` | session PM (`board.py`) | hook `SessionStart`, robla, stratège |
| `<data_root>/pm/alerts.jsonl` | session PM | PM (diff), `roles_counts` |
| `<data_root>/pm/hook_errors.log` | hooks | PM |
| `docs/roadmap/ROLES.md` | session PM | stratège (lentille Organisation), porte 8, `check_guard_negative_cases` |
| `docs/roadmap/STRATEGE_PROPOSITION.md` | session PM (sortie du workflow) | robla |
| bloc 🧭 de `PRIORITES_ET_DETTES.md` | session PM, après accord de robla | tous |
| `docs/reviews/<date>-<cible>.md` | la session qui invoque le Réfutateur | porte 1 (`review:`) |
| `.claude/workflows/strategist.js`, `refutateur.js`, `docs/REF/REF-REVUE-ADVERSARIALE.md` | commit path-scoped, changement = décision de robla | PM, sessions |

Chemins de données via `src/paths.py` (`sessions_dir()`, `pm_dir()`) ; `data/sessions/` et `data/pm/` ignorés
par git.

---

## 5. Erreurs et modes dégradés

- **Hook en échec** : exit 0, ligne dans `hook_errors.log`, la session continue. Le PM lit ce fichier à chaque tick
  et lève une alerte si le même hook échoue deux fois.
- **Source du tableau indisponible** : `AVEUGLE SUR <source>` en tête, alertes dépendantes supprimées (section 3.2).
- **Bail `pm` occupé** : la session refuse le rôle et nomme le détenteur. **Détenteur mort** : `doctor --kill` par
  robla, jamais automatique.
- **Témoin non attrapé** (stratège ou Réfutateur) : passe `NULLE`, rien d'écrit, compteur `témoin manqué` +1 ;
  deux fois → le jeu de prompts est re-scellé (commit path-scoped), pas le rôle.
- **PM redémarré ou compacté** : aucun état en contexte ; il relit ses fichiers.
- **Message PM non suivi** : après 48 h, l'alerte compte `fausse ou ignorée` ; le PM ne renvoie pas le message —
  il inscrit le cliquet si l'alerte se répète.
- **Session dont le registre natif ignore le nom** : bulletin avec `name: null`, alerte A7 avec le `sessionId`.

---

## 6. Tests, calibration, compteurs

### 6.1 Tests exécutables

- `tests/sandbox/test_pm_board.py` : `compute()` sur instantanés injectés — un cas positif par alerte A1-A8, le
  no-op exact (zéro alerte), un cas par source indisponible (`AVEUGLE`, jamais 0). `board.compute` et les fonctions
  d'alerte sont déclarées `CALIBRATED` dans `test_instrument_calibration.py` si le cliquet les détecte.
- `tests/sandbox/test_pm_bulletin.py` : chaque événement de hook avec un JSON stdin factice ; hook qui rencontre un
  registre absent → exit 0 + ligne de log.
- Portes 18, 19, 20 et l'extension de la porte 1 : contre-exemple gelé + ligne dans `check_gate_mutation` (porte 15).
- `check_guard_negative_cases` : une ligne de `ROLES.md` sans ses cinq colonnes → rouge ; test de forme.
- Porte 10 (`check_test_census`) : compte des tests ≥ avant.

### 6.2 Compteurs recomputés — jamais recopiés

`tools/pm/roles_counts.py` recompute et la porte 8 (`check_synthesis_counts`) vérifie les balises `count:` de
`ROLES.md` : par rôle, les compteurs de la section 2 ; pour tous, les **tokens par invocation** (relevés de session)
et le **ratio science/méthodo**, défini par CHEMINS de fichiers modifiés sur la fenêtre : science = `docs/EDR/`,
`results/`, `docs/preregistrations/` ; méthodo = `tools/check_*`, `tests/sandbox/`, `docs/REF/`, `docs/roadmap/`,
`CLAUDE.md` ; le reste = `autre`, publié à part. Point de départ publié : **26 / 78** (2026-09-08).

### 6.3 Revue des rôles — lentille « Organisation »

Déclenchée par événement : 20 records au graphe OU 30 jours (le premier atteint) ; **immédiatement** à toute
rétractation, toute récidive E10 sur la règle d'un rôle, tout témoin non attrapé, et à toute **alerte PM répétée
deux fois**. Le panel du stratège reçoit alors la lentille Organisation, qui lit `ROLES.md` et pose trois questions :
quel candidat a atteint son critère de naissance ? quel rôle instancié n'a plus produit de trouvaille confirmée ?
quelle fonction ad hoc a récidivé sans propriétaire ? Le témoin « Scribe des records » reste gelé dans `ROLES.md`
et doit être tué à chaque passe.

**Naissance** : deux occurrences DATÉES qu'aucune porte n'attrape, que l'auteur DÉCLARE non décidable, avec un témoin
connu. **Mutation** : ≥ 50 % des trouvailles confirmées attrapables par une porte → le rôle écrit la porte et sa
fiche rétrécit d'autant. **Dissolution** : précision < 1/10 sur la fenêtre, ou zéro trouvaille confirmée, ou coût
> 15 % de la fenêtre sans qu'un verdict change en aval, ou ratio science/méthodo dégradé deux fenêtres de suite
pendant que le rôle est actif. La dissolution est un succès.

### 6.4 La règle qui borne la couche

**Tant que le ratio science/méthodo n'a pas franchi 1:1, la revue des rôles ne peut pas créer un rôle sans en
dissoudre ou en réduire un autre à coût égal.** Les trois rôles initiaux sont posés par décision de robla le
2026-09-16 ; la première revue (30 jours) leur applique les critères de dissolution comme à tout autre.

Les fausses alertes du PM s'inscrivent au REGISTRE comme des occurrences (classe à créer à la deuxième) ; le stratège
publie la prémisse qui porte chaque arbitrage, et le Réfutateur peut la confronter : un arbitrage sur prémisse non
mesurée est E8 au même titre qu'un record.

---

## 7. Ordre de livraison — chaque pas utile seul

1. **`board.py` + `test_pm_board.py`** — robla l'utilise à la main dès le premier jour, sans PM ni bulletin.
2. **Hooks bulletin + résumé au démarrage** (`bulletin.py`, `.claude/settings.json`, `paths.sessions_dir`,
   `.gitignore`) — le pull existe, A1/A6/A7 deviennent calculables.
3. **`/pm`** : skill, bail `pm`, `alerts.jsonl`, `ROLES.md` initial (PM, Stratège, Réfutateur instanciés ; sept
   candidats), `roles_counts.py`, extension de `check_guard_negative_cases` — le PM vit.
4. **Portes 18, 19, 20** + extension de la porte 1 (`review:`), avec témoins et mutations — ce sont aussi trois
   dettes consignées (section 10) et elles paient sans le Réfutateur.
5. **Réfutateur** : `REF-REVUE-ADVERSARIALE.md`, `refutateur.js`, trois témoins gelés + no-op, `docs/reviews/`.
6. **Stratège** : `strategist.js`, lentille Organisation, déclencheurs dans le tick, `STRATEGE_PROPOSITION.md`.
   Jusque-là, le précédent manuel du 09-14 reste la procédure.

Chaque étape : commit path-scoped, `snapshot`/`verify` sur tout fichier partagé, compte d'entité ≥ avant.

---

## 8. Contraintes du dépôt honorées

Porte 12 (chemins via `src/paths.py`) · porte 14 (aucune constante sur source vide : `None` et `AVEUGLE`) · porte 8
(tout compte de `ROLES.md` se recompute) · porte 10 (recensement des tests) · porte 15 (chaque nouvelle porte a sa
mutation) · cliquet de calibration (`board.compute` calibré par injection) · **aucun backtick ni séquence d'échappement
dans une commande de hook** · hooks toujours exit 0 · Windows : chemins absolus via `$CLAUDE_PROJECT_DIR`, `python`
du PATH · un writer par fichier · aucune simulation, aucun bail `kuzu` : cette couche est CPU pur et lecture seule
sur le monde.

---

## 9. Hors périmètre — candidats réfutés, gardés en `candidat` dans `ROLES.md`

| candidat | raison de réfutation (2026-09-16) | critère de naissance |
| --- | --- | --- |
| Régisseur des runs | le compte des « familles orphelines » venait d'un apparieur par préfixe déclaré faillible par l'outil (`check_preregistration_applied.py:125,195`) ; chaque occurrence datée déjà close par une garde ou déjà proposée comme cliquet | deux runs abandonnés ou contaminés en 30 j malgré `cost_guard` et le bail |
| Intégrateur | prémisse périmée (la divergence d1/main était RÉSOLUE le 2026-07-28) ; le reste = entrées de backlog + deux cliquets | deux collisions de numéro ou deux merges perdus en 30 j |
| Greffier-métrologue | la promotion documenté→exécutable A été appliquée (P2.25, le 2026-09-07) ; quatre cliquets durs couvrent le reste | deux classes restées `documenté` après deux récidives |
| Bibliothécaire de la doctrine | récidive réelle mais rare (4 passes en 6,5 semaines) et bon marché après coup | deux sessions trompées par la même phrase périmée, datées |
| Auditeur des angles morts | décidable à 80 % → **cliquet** (complément AST-vs-regex publié : 1775 `def` sur 2078 hors motif) + lentille du stratège sur tout élargissement de détecteur | — (livré comme cliquet, section 10) |
| Archiviste de l'évidence | constat VRAI (69/20/18) mais c'est la **porte 19**, pas un rôle | — |
| Rétro-applicateur, Greffier de passage | preuves périmées ou une seule occurrence ; une entrée de backlog suffit | deux occurrences datées |

Le plugin `claude-session-driver` (workers tmux) est hors périmètre : `tmux` est absent de la machine, et le modèle
« session qui pilote des sessions » est celui qu'on écarte.

---

## 10. À consigner au backlog (vérifié par l'auteur le 2026-09-16)

1. **Porte 18 `check_regime_claims`** — 47 records citent `forage_payoff|flip_p|reward_scale|lr=`, 4 citent un bloc
   `regime` (`grep -l` sur `docs/EDR/*.md`). E8 occ. 4 en est le contre-exemple.
2. **Porte 19 `check_evidence_provenance`** — 69 chemins `results/` cités par les EDR, 20 non suivis par git, 18
   absents du disque (`git ls-files --error-unmatch` / `test -e` sur la liste extraite).
3. **Calibration de `check_preregistration_applied`** — l'appariement par préfixe (`:125`) est déclaré faillible par
   l'outil (`:195`) ; le panel a compté 8 familles rendues « orphelines » à tort — à chiffrer par un cas de calibration
   avant tout usage de ce compte comme preuve.
4. **Cliquet « hors motif »** — chaque `check_*.py` à motif publie balayé / appariés / HORS MOTIF (différentiel AST vs
   regex, ~30 lignes, `ast` déjà importé à `check_instrument_calibration.py:26`) ; contrôle positif : l'arbre au
   2026-09-15 avant `0cdd54a` doit rendre les 3 apprenants indentés de P2.62.
5. **Test de forme du hook** (E4 occ. 7) — toute `staged_X=` appelant un checker à baseline liste sa baseline dans
   son regex ; le hook figure dans le regex de la porte 15.

---

## 11. À vérifier à l'implémentation (faits, pas décisions)

- Le JSON stdin des hooks sous Windows porte bien `session_id` et `cwd` ; `$CLAUDE_PROJECT_DIR` est défini pour un
  hook lancé depuis un worktree.
- Le nom (`agagi-11`) se joint par `sessionId` au registre natif dans 100 % des cas observés (13 entrées au 2026-09-16).
- Le cliquet de calibration détecte-t-il `board.compute` comme instrument (motif) ? Sinon le déclarer quand même.
- Le seuil de `cost_estimate` qui déclenche `reviewed_by` : à lire dans les 58 pré-inscriptions existantes (médiane
  des coûts déclarés), pas à deviner.
