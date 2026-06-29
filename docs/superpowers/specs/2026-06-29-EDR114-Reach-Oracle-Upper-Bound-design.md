# EDR 114 — Sonde borne-sup : une primitive d'atteinte ferme-t-elle p_reach ? (oracle vs politique apprise)

> **Spec de conception** — 2026-06-29. Sonde diagnostique (pas d'evolution). Suite d'EDR 113.
> Outil : `tools/lewis_survival_sweep.py` (extension DRY). Discipline : Commandement 15.

## 1. Contexte & question

L'arc Lewis a elimine, un par un, tous les leviers-MONDE du plafond de navigation (`p_reach`,
fraction d'agents atteignant une cellule-proie) : energie (090-101), cinematique (106), selection
(104/108), capacite reseau (110), demande (111), affordance de reward (113). Verdict convergent
(EDR 113 + [[nas-bottleneck-is-substrate-not-search]] + meta-audit SOTA) : le verrou est l'**execution
du pas final par le SUBSTRAT** (politique de navigation fine), pas le monde.

**Mais une question reste ouverte, decisive et bon marche** : EDR 105/106/107/113 mesurent toujours
`p_reach` sous la **politique APPRISE** du connectome. On n'a jamais teste la **borne superieure** :
si l'on remplace la politique par une **primitive d'atteinte parfaite** (oracle « va sur la proie la
plus proche », zero apprentissage), `p_reach` monte-t-il a ~1 ?

- Si **OUI** -> le monde PERMET d'atteindre trivialement ; l'echec de l'agent est purement
  l'apprentissage de la politique (le substrat ne sait pas implementer un argmax a 4 entrees sur
  `dn/ds/de/dw`, qu'il OBSERVE pourtant). Verrou = SUBSTRAT/plasticite, confirme par exclusion.
- Si **NON** (meme l'oracle echoue) -> le verrou est dans la **MECANIQUE du monde** (resolution
  d'action, collisions, respawn), pas la politique. Rouvre une question monde inattendue.

C'est le test qui **distingue enfin** « le substrat ne sait pas apprendre la politique » de « le monde
empeche mecaniquement d'atteindre » — les deux ayant produit le meme `p_reach` bas jusqu'ici.

## 2. La subtilite cinematique (structure le design)

Les proies BOUGENT en Lewis standard (Lapin fuit a `moves_per_tick=2`, EDR 106). Un oracle parfait se
deplace a 1 pas/tick -> **il ne peut pas rattraper un Lapin qui fuit a 2x** en terrain ouvert. Donc
« oracle + proies mobiles » mele deux choses : la mecanique de poursuite ET la cinematique de fuite.

Pour trancher proprement, on decouple via `prey_speed_scale` (EDR 106) : la cellule decisive est
**oracle + proies FIGEES** (`prey_speed_scale=0.0`) = la vraie borne-sup de mecanique-monde (un
chasseur parfait atteint-il une cible IMMOBILE ?). La cellule « oracle + mobiles » donne la lecture
cinematique secondaire (un chasseur parfait rattrape-t-il la fuite ?).

## 3. Architecture

Flag monde **`reach_oracle`** (config + world, defaut False = non-regressif). Quand ON, l'action de
chaque agent est **remplacee** apres son calcul (post argmax/decode_act/epsilon-greedy, `world_1_
stoneage.py` ~l.1066) par `_reach_oracle_action(agent)` = pas glouton Manhattan vers la proie la plus
proche -> mapping `argmax([dn,ds,de,dw])` -> action 0/1/2/3 (N/S/E/O). Zero apprentissage ; le genome
devient inerte sous l'oracle (isole le monde + la primitive).

Mesurer `p_reach` via **`_measure_forage`** (EDR 105, replicas SANS evolution -> tres cheap) sur la
matrice **2x2 = {oracle off, oracle on} x {prey_speed 1.0 mobiles, 0.0 figees}**, graines APPARIEES
(memes seeds entre cellules). Les cellules « oracle off » reproduisent 106/107/113 (controles) ; les
cellules « oracle on » sont les donnees neuves. Verdict porte par la cellule (oracle on, figees).

## 4. Composants & interfaces

### 4.1 `src/environments/config.py`
- Ajouter `reach_oracle: bool = False` a `WorldConfig` (apres `scaffold_land`, EDR 113). Defaut False
  -> non-regressif.

### 4.2 `src/worlds/world_1_stoneage.py`
- En `__init__` : `self.reach_oracle = getattr(self.config, "reach_oracle", False)`.
- Nouvelle methode `_reach_oracle_action(self, agent) -> int` = pas glouton vers la proie la plus
  proche (Manhattan) AVEC **evitement d'obstacle a 1 pas** (utilise prey-direction ET la geometrie ;
  l'agent observe les deux : `dn/ds/de/dw` + `lidar_n/s/e/w`). Logique :
  - `self.preys` vide -> renvoyer `6` (no-op ; jamais le cas a N_APEX=0 avec proies regulieres).
  - Proie la plus proche par distance Manhattan ; `dx = p["x"]-ax`, `dy = p["y"]-ay` (ints).
  - `dx == 0 and dy == 0` (deja sur la proie) -> `6` (action sans deplacement ; l'attaque se declenche
    par co-localisation, et `p_reach` est deja satisfait par `_forage_min_dist<=0`).
  - Candidats par axe du plus grand ecart d'abord : `ew = 2 if dx>0 else 3` ; `ns = 1 if dy>0 else 0` ;
    `cand = [ew si dx!=0, ns si dy!=0]` (ordre selon `abs(dx) >= abs(dy)`).
  - Renvoyer le 1er candidat dont la cellule cible est **libre** (`0<=tx,ty<size` ET `geometry[0,ty,tx]
    == 0`). Si les deux axes sont bloques -> renvoyer `cand[0]` (pousse, perd le tick, pas de crash).
  - Le mapping action->deplacement est celui de la sim : `0:y-1(N) 1:y+1(S) 2:x+1(E) 3:x-1(O)`.
- Override : juste avant `agent["last_action"] = action` (~l.1067), inserer
  `if getattr(self, "reach_oracle", False): action = self._reach_oracle_action(agent)`. Place APRES
  toute la logique de politique (argmax, decode_act, epsilon-greedy) -> remplacement COMPLET. A
  `reach_oracle=False` -> aucun effet (non-regression).

### 4.3 `tools/lewis_survival_sweep.py`
- `_cfg(..., reach_oracle=False)` -> pose `cfg.reach_oracle = bool(reach_oracle)`.
- `_verdict_reach(aggs)` : `aggs` = liste de `(oracle: bool, speed: float, agg: dict)`. Trouve la
  cellule `(oracle=True, speed=0.0)`. **PRIMITIVE FERME** si son `p_reach >= 0.90` ; **PRIMITIVE NE
  FERME PAS** si `< 0.50` ; **PRIMITIVE PARTIELLE** sinon (0.50-0.90). Cellule absente -> "INDETERMINE".
- `_report_reach(h, aggs, R, n_eval, _return)` : table ASCII (1 ligne/cellule : oracle, speed,
  p_reach, p_cap, mean_min_dist, n) + lecture cinematique (oracle-figees vs oracle-mobiles) + verdict
  pre-enregistre + provenance. Tout ASCII (cp1252). Sauvegarde JSON (retirer toute cle non
  serialisable type `reached_raw` si presente, comme `_report_approach`).
- `main_reach_oracle(speeds=(1.0, 0.0), n_eval=8, R=1, seed=114, _return=False)` :
  `with Harness(seed, name="lewis_reach_oracle", with_db=False)`, `_disable_kuzu()`,
  `seeds = [base + r*1000 + i for r in range(R) for i in range(n_eval)]` (appariees). Pour chaque
  `oracle in (False, True)` puis chaque `speed in speeds` : `cfg = _cfg(3, base_metabolism=0.0,
  trace_energy_sinks=True, trace_forage=True, prey_speed_scale=speed, reach_oracle=oracle)` ;
  `agg = _measure_forage(cfg, seeds, n_apex=0, max_ticks=150)`. Collecte les 4 `(oracle, speed, agg)`.
  Puis `_report_reach`.

> Note : `_measure_forage` EXIGE `trace_forage=True` ET `trace_energy_sinks=True` (co-activer les deux,
> comme `main_approach`). `max_ticks=150` (precedent 105/106) >> distance Manhattan max de la grille ->
> un oracle parfait a le temps d'atteindre une cible immobile.

## 5. Verdict pre-enregistre (fige AVANT les donnees, falsifiable des deux cotes)

| Branche | Condition (cellule oracle+figees) | Lecture scientifique |
|---|---|---|
| **PRIMITIVE FERME** | `p_reach >= 0.90` | Le monde PERMET d'atteindre une cible immobile ; l'echec de l'agent est purement la POLITIQUE apprise (le substrat n'apprend pas l'argmax a 4 entrees). **Verrou = SUBSTRAT/plasticite, confirme par exclusion** -> converge [[lewis-energy-economy-wall]] + meta-audit SOTA -> mandat de migration moteur. |
| **PRIMITIVE NE FERME PAS** | `p_reach < 0.50` | Meme un chasseur parfait sur cible IMMOBILE echoue -> le verrou est la **MECANIQUE du monde** (resolution d'action, collisions, respawn, geometrie), PAS la politique ni le substrat. **Rouvre une question monde** et invalide partiellement la conclusion « tout est substrat ». |
| **PRIMITIVE PARTIELLE** | `0.50 <= p_reach < 0.90` | Le monde permet d'atteindre mais imparfaitement (geometrie/obstacles/episode). Sous-determine ; documenter l'obstacle dominant. |

**Lecture secondaire (cinematique).** Comparer oracle-figees vs oracle-mobiles : si oracle-mobiles
`p_reach` ≪ oracle-figees, un chasseur parfait NE rattrape PAS la fuite (la cinematique EST un mur
pour la poursuite parfaite ; nuance EDR 106 qui ne le testait que sous politique apprise). Si proches,
la fuite n'est pas le facteur limitant meme pour un poursuivant parfait.

**Controles (oracle off).** Doivent reproduire l'ordre de grandeur connu : ~0.36 (mobiles, EDR 107/113)
et ~0.21 (figees, EDR 106). Sinon -> harnais suspect, investiguer avant d'interpreter.

**Seuils 0.90 / 0.50** : 0.90 = « un chasseur glouton parfait atteint quasi toujours une cible
immobile en 150 ticks » (tolerance pour famine/geometrie residuelle) ; 0.50 = meme moitie atteint =
mecanique-monde clairement cassee. Ancres sur le meme seuil 0.5 qu'EDR 105/106 (`_verdict_approach`).

## 6. Tests (TDD, banc `tests/sandbox/test_edr114_reach_oracle.py`)

1. **Config additive** : `WorldConfig().reach_oracle is False` ; `_cfg(3, reach_oracle=True).reach_oracle
   is True` ; `_cfg(3).reach_oracle is False`.
2. **Cablage monde** : `Biosphere3D(_cfg(3, reach_oracle=True)).reach_oracle is True` ; `False` sinon.
3. **`_reach_oracle_action` mappe la direction + evite l'obstacle** (unite, sans step complet) :
   construire un env minimal, grille libre (`env.geometry[:] = 0`), un agent en `(x,y)` connu, vider
   `env.preys` et y mettre UNE proie a une position relative connue. (a) Direction : proie a l'est
   (`px>ax`, |dx|>=|dy|) -> `2` ; ouest -> `3` ; sud (`py>ay`, |dy|>|dx|) -> `1` ; nord -> `0` ; meme
   cellule -> `6`. (b) Evitement : proie au NORD-EST (dx>0, dy<0, |dx|>=|dy| -> prefere EST=2) mais
   bloquer la cellule EST (`geometry[0, ay, ax+1] = 1`) -> doit renvoyer l'axe secondaire NORD=`0`
   (cellule libre). (c) Les deux axes bloques -> renvoie `cand[0]` (l'axe prefere, pousse).
4. **Non-regression a False** : deux env `reach_oracle=False`, memes graines, N pas -> trajectoires
   d'energie identiques (le defaut ne change rien). (Calque le test de non-reg d'EDR 113.)
5. **L'oracle ATTEINT une cible figee (smoke comportemental)** : env minimal, `reach_oracle=True`,
   `prey_speed_scale=0.0`, UN agent loin d'UNE proie figee, `trace_forage=True` ; stepper jusqu'a
   `<= 2*distance_initiale + 5` ticks ; assert `agent["_forage_min_dist"] <= 0` (l'oracle a atteint).
   C'est la verification directe que la primitive fonctionne.
6. **`_verdict_reach` branches** : aggs synthetiques -> FERME (figees p_reach 0.95) / NE FERME PAS
   (0.30) / PARTIELLE (0.70).
7. **Determinisme** : `main_reach_oracle(speeds=(0.0,), n_eval=2, R=1, seed=88114, _return=True)` deux
   fois -> p_reach identiques. **Seed distinct de 114** (provenance).
8. **Smoke** : `main_reach_oracle(speeds=(1.0, 0.0), n_eval=2, R=1, seed=99114, _return=True)` tourne,
   renvoie un verdict valide, JSON ecrit.

## 7. Cout & repli

4 cellules x `n_eval=8` graines, `_measure_forage` SANS evolution -> **tres cheap** (pas de boucle
20-gen, ~minutes). Confirmatoire R=1, seed 114. Repli : n_eval=4. Run reel APRES revue ; AUCUN test
relancé apres (provenance — lecon EDR 107).

## 8. Provenance, determinisme, non-regression

- `results/` gitignore ; seed reel 114 ; smoke/determinisme 99114/88114 distincts.
- Determinisme verifie (test 7) ; run reel reproduit une fois.
- **Non-regression** : `reach_oracle=False` defaut -> tous mondes/EDR existants byte-identiques (test 4).
- ASCII-only dans tout `print` execute (cp1252) : `->` ASCII OK, pas de fleche unicode/accents.
- Caveat : sous l'oracle, le genome est inerte (politique remplacee) -> p_reach mesure le MONDE+oracle,
  pas la population. C'est l'intention (borne-sup).

## 9. Commandement 15 — variables

Deux axes croises et explicites : `reach_oracle` (off/on) et `prey_speed_scale` (1.0/0.0). Le verdict
est porte par UNE cellule (oracle on, figees) ; les autres sont controles/lecture secondaire. Tout le
reste identique : monde (Lewis vide d'apex, metab=0, forage_payoff=3), graines appariees, ticks,
population, substrat (champions replication via `_measure_forage`, inerte sous oracle).
