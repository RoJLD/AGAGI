# Priorités & dettes — backlog ACTIONNABLE

> À ne pas confondre avec [`../BACKLOG.md`](../BACKLOG.md), qui est le « someday » aspirationnel.
> Ici : ce qui est **à faire**, dans l'ordre, avec la preuve et le coût.

Établi le **2026-07-21**, à l'issue de l'arc WARM-005→009 et du chantier méthodologique qui en est sorti.
Ordre de priorité **décroissant**. Chaque entrée porte : ce qu'il faut faire, **pourquoi** (avec la preuve),
et le coût estimé.

> Contexte chiffré qui justifie l'ordre : sur cet arc, **7 revues adversariales → 7 erreurs réelles**, et
> **71 instruments détectés, 1 calibré**. Le déficit dominant n'est pas l'honnêteté du compte-rendu
> (négatifs consignés, auto-réfutations écrites, portées bornées) mais l'**absence de calibration** et
> l'**absence d'application exécutable** des règles déjà documentées.

---

## P0 — Bloquant : restaurer un environnement vérifiable

**P0.1 — ~~Redémarrer l'environnement~~ → RÉSOLU, et mon diagnostic était FAUX.**
J'avais écrit « processus/threads orphelins probables » **sans le mesurer**. Mesure faite :
**zéro processus orphelin**, 18 Go de RAM libres sur 64. L'échec réel était
`bash: fork: retry: Resource temporarily unavailable` (code `0xC000012D`) = défaillance de fork
**côté Cygwin/MSYS**, transitoire — pas une saturation par des processus Python. Vérifié depuis :
fork OK, 13/13 tests passent. *(Classe E9 du registre — conclure depuis un symptôme saillant sans
mesurer, commis dans le document qui liste E9.)*

**P0.2 — Valider la suite COMPLÈTE après redémarrage.** Les deux `tests/__init__.py` et
`tests/sandbox/__init__.py` (correctif des doublons de basename) ont été validés **à la collecte**
(1170 tests, 0 erreur) mais **jamais bout-en-bout**. *Coût : ~15 min.*

---

## P1 — Dettes ouvertes

**P1.1 — Blocage de `tests/sandbox/test_behavioral_diversity.py` en suite complète.**
PASSE en isolation (26 s), BLOQUE dans la suite sur `async_logger.stop()` → `time.sleep`. **Préexistant**
(fichier du 2026-06-29) : il était masqué par l'erreur de collecte qui avortait la suite avant de
l'atteindre — le correctif P1 l'a *révélé*, pas créé. Cause probable : état global (`async_logger` +
connexion KuzuDB) non nettoyé entre fichiers.
⚠️ Une fixture `autouse` de nettoyage a été tentée dans `tests/conftest.py` : elle a **cassé 2 tests** et
n'a pas pu être diagnostiquée (environnement épuisé) → **retirée**, à reprendre après P0. *Coût : ~1 h.*

**P1.2 — ~~Câbler `sim_session`~~ → FAIT, et remplacé par un JOB MANAGER.**
`tools/jobs/` livré (lease/run/doctor, **11/11 tests**), inspiré de `cmex_crypto.batch` (Quant-lab) dont
la recherche SOTA — 5 angles, 19 sources, 25 claims vérifiés à 3 votes — avait déjà tranché : *construire
le gouverneur, réutiliser les primitives*. **Écart de conception assumé** : Quant-lab gouverne par cap de
concurrence (un nombre) ; AGAGI a besoin de **ressources NOMMÉES exclusives** (KuzuDB), car un cap global
à 1 sérialiserait des jobs indépendants sans dire pourquoi. Câblé dans `_torch_survival_eras` ;
`sim_session.py` est **déprécié**. Reste à câbler : `measure_inworld_grab_rate` et les ~70 autres sondes.
*(Ancien texte ci-dessous conservé pour la traçabilité de la preuve.)*

**P1.2-bis — Câbler le bail dans les sondes restantes.** La primitive existe et est testée (5/5) mais
n'est utilisée nulle part : `_torch_survival_eras` et `measure_inworld_grab_rate` portent encore un
correctif ad hoc. Le verrou de processus rend la contention KuzuDB **impossible** au lieu de déconseillée.
*Preuve : 3 violations de la même règle en une journée — par moi (2×, sondes parallèles → mesure
contaminée + suite en timeout) et par le code d'instrument (retriever actif pendant la sim).* *Coût : ~1 h.*

**P1.3 — Graver un EDR : aliasing des bancs torch + défaut du retriever.** Deux findings mesurés, non
encore consignés, qui **changent la lecture de WARM-005/007/008** :
- *Aliasing* : les écritures du monde dans `H` (`world_1_stoneage:1289` pénalité anti-répétition, `:966`
  consensus social) ne sont **PAS inertes** — mesure propre et séquentielle sur l'étalon : **3/6 génomes
  diffèrent, `agent02` de +37 %** (`[50.5, 46.0, 55.0]` aliasé vs `[35.0, 36.0, 41.0]` découplé).
  ⚠️ Ceci **corrige** la conclusion antérieure « prod ≈ découplé, le découplage est inutile », qui ne
  tenait que sur 3 génomes d'un seul monde. Portée : **bancs torch uniquement** — la production tourne en
  `LegacyPopulationModel` (`use_torch_inworld = False` par défaut), sans état aliasé.
- *Retriever* : `_torch_survival_eras` laissait `memory_retriever` **actif pendant toute la simulation**
  (thread daemon, `_running = True`), contre la règle documentée du projet. **Toutes** les mesures de
  survie de l'arc ont tourné ainsi. Corrigé ; reproductibilité désormais vérifiée (`run1 == run2` exact).
*Coût : ~1 h.*

**P1.4 — DÉCISION robla : corriger l'aliasing en production, ou l'épingler ?** Le monde écrit dans l'état
récurrent par cette voie dans tous les bancs torch. Corriger changerait **toutes les baselines torch** ;
ne pas corriger exige un test qui **épingle** le comportement pour qu'il ne dérive pas silencieusement.
Décision hors de mon périmètre (code partagé, arbre partagé entre sessions). *Coût : décision.*

**P1.5 — DÉCISION robla : le commit.** Rien n'est committé de cette session (~20 fichiers, tous scopés).
Trois touchent du code partagé — `src/agents/backend_torch.py` (couvert 28/28), et deux nouveaux outils.
*Coût : décision + revue.*

---

## P2 — Calibration des instruments (le déficit dominant)

> 🔬 **CLASSEMENT ÉTABLI PAR MESURE** (workflow 15 agents : 8 cartographes + 6 contre-vérificateurs
> adversariaux + synthèse, 2026-07-21). **Règle de lecture qui en sort** : sur 6 contre-vérifications,
> tout score justifié par « beaucoup de records le citent » a perdu **18 à 46 points** (présumé gonflé de
> ~30 %) ; ceux fondés sur un **seam d'injection réel** en ont gagné. Les scores ci-dessous sont ceux du
> VÉRIFICATEUR quand il existe (✔), sinon marqués ⚠.
>
> ⚠️ **PRÉREQUIS RÉGLÉ** : le cliquet lui-même mentait — `scan_calibrated()` validait par SUBSTRING du
> nom, donc `_torch_survival_eras` passait pour calibré alors que seule sa branche `grab_off` l'était.
> Classe **E4** dans l'outil écrit pour l'empêcher. Corrigé (clé = `(fonction, branche)` DÉCLARÉE) +
> régression permanente.

**P2.0 — ✅ FAIT (2026-07-21) — le contrôle positif gratuit a coûté 6 s et RÉFUTÉ un record.**
Résultat gravé : **[EDR-WARM-010](../EDR/WARM-010_Fitness_Landscape_Is_Not_Flat_Partial_Competence_Is_Rewarded.md)**.
- Le banc est **INNOCENTÉ** : ratio **22.22** avec l'oracle (21.05 publié) → il sait produire un positif.
- Donc le NEUTRAL de WARM-002 n'est pas un artefact de banc — mais la dose-réponse de fidélité
  (`partial_oracle`, nouvel étalon de compétence GRADUÉE) montre **9.0 → 12.0 → 17.5 → 37.0 → 94.2 →
  200.0**, strictement monotone, 12/12 ères séparées à chacune des 5 marches. **Le paysage n'est PAS
  plat** ; le mécanisme de WARM-002 est réfuté, son échec empirique tient, l'attribution passe du MONDE à
  l'OPTIMISEUR (converge [[warm-start-transversal-law]]).
- Deux erreurs : **E3** (ratio lu sur un bras à 5.0-7.2 ticks, SOUS le plancher 9.0) et **E8** (seuil
  « ~99 % » importé de WARM-001). Nouvelle classe **E14** ouverte (garde jamais rétro-appliquée).
- ⚠️ **Question ouverte installée** : l'ATTEIGNABILITÉ. Le gradient est dense dans l'espace des
  COMPORTEMENTS ; rien ne dit que la mutation W-only le trouve dans l'espace des GÉNOMES. C'est
  maintenant la formulation correcte de l'échec de WARM-002 — et elle est testable.

**P2.0-bis — `champion_body` n'a AUCUN record** (`grep docs/EDR/` : 0 hit) alors qu'il porte le verdict
fondateur S2, sur lequel repose toute la §2 de `SPECIFICATION_10ANS.md`. Finding fondateur sans record
**ni** calibration. Candidat sérieux au top 3. *(non traité)*

**P2.1 — `_torch_survival_eras`, branche `perception` — 85 ✔** *(passe DEVANT `ablation_verdict`)*
Le seam `world_cls` existe déjà ; la branche porte les ratios publiés de WARM-001 (1.6→2.1) et WARM-003
(5.04) et n'a **aucun** cas. **Effet de levier** : le même étalon perceptif ferme d'un coup les trous de
`_mamba_survival_eras` (34 ⚠) et `verdict_demand_marker` (48 ⚠). Ajouter 2 seams manquants au passage.

**P2.2 — ✅ FAIT (2026-07-21) — bug RÉEL corrigé, et EDR-095 n'est PAS affecté.**
Le défaut latent soupçonné est **confirmé par mesure** : `_paired_ratios` faisait `arm / max(off, 1e-6)`
sans condition → une paire **doublement ÉTEINTE** rendait `0.0`, survivait au filtre `r != 1.0` et
comptait **contre le rêve**. Avant correctif, deux bras **strictement identiques et éteints** rendaient
`CAUSE_NUISIBLE, ratio 0.0, sign_p 0.00195` (classe **E1** — un contrôle qui ne peut pas rendre NEUTRE).
- **Le défaut agissait dans les DEUX sens** : sur un jeu où le rêve aide dans 4 paires informatives sur 4,
  six paires éteintes empoisonnaient la médiane (ratio 0.0 au lieu de 1.40) et **masquaient le bénéfice**.
- **Correctif** : paires non informatives ÉCARTÉES (champ `n_ecartees`) ; si toutes le sont →
  `INCONCLUSIVE_DEGENERATE` (même nomenclature que la garde de `ablation_verdict`).
- ✅ **EDR-095 tient** : ses bras publiés (`off ∈ [0.113,0.165]`, forcés `∈ [0.055,0.090]`) n'ont **aucun
  zéro**. Rejoué après correctif : `ratio 0.547, sign_p 0.00195` contre `0.543 / 0.00195` publiés.
  **On ne peut le dire que parce qu'il a publié ses VALEURS ABSOLUES** — l'argument le plus concret de
  toute la passe en faveur de cette pratique.
- 5 cas de calibration, dont le **générateur A** (l'instrument peut-il rendre LES DEUX issues ? — non
  établi jusqu'ici ; vérifié). **Cliquet : 80 détectés, 7 calibrés.**

**P2.12 — ✅ FAIT (2026-07-21) — EDR-095 est RÉFUTÉ dans son verdict principal.**
Résultat gravé : **[EDR-DREAM-001](../EDR/DREAM-001_Forced_Dreaming_Harm_Is_A_Birth_Flood_Artifact_Effect_Absent_On_Matched_Cohort.md)**.
Cohorte fondatrice marquée par IDENTITÉ dans `run_era_organ`, 12 seeds, 25 vs 25 par cellule :

| métrique | off | K=8 | ratio | K8>off | `sign_p` |
|---|---|---|---|---|---|
| TOUS *(publiée)* | 29.0 | 13.0 | **0.448** | 0/12 | 0.0005 |
| FONDATEURS *(apparié)* | 35.5 | 54.5 | **1.535** | **8/12** | 0.3877 |

`n_lived` : off 56 / K=8 756 → **×13.4**. Le chiffre publié **se reproduit exactement** : mesure juste
d'une grandeur CONFONDUE, pas erreur de mesure. Sur agents comparables, la pénalité de ~45 % **n'existe
pas** — si le vrai ratio valait 0.448 on attendrait ~0/12 favorables à K=8, on en observe 8/12.
- ⚠️ **Une première correction REJETÉE par moi avant publication** : « les N plus vieux » est biaisé
  (top 26 % vs top **1,6 %** — sélection sur la variable de sortie à quantiles incomparables). Elle
  rendait 1.339 et aurait donné un titre inverse tout aussi faux.
- ⚠️ `sign_p = 0.39` n'établit PAS l'effet inverse, et le record ne l'affirme pas. Il établit l'ABSENCE
  de l'effet publié — une question différente, et décidable à ce n.
- **Nouvelle classe E15** au registre : statistique de population comparée entre populations de
  compositions différentes. **Aucune garde de borne ne voit ça** (aucun bras au plancher/plafond).

*(entrée d'origine)* — Confond `n_lived` d'EDR-095 *(non tranché)*. Le record note lui-même que le rêve
forcé fait passer `n_lived` de ≈74 à ≈1205 (**×16**), en « effet secondaire ». Or `survival_competence`
est la **médiane des âges** sur les agents de l'ère : une population 16× plus nombreuse dont la plupart
naissent tard a des âges mécaniquement faibles. **La baisse de survie pourrait être un artefact de
calendrier de naissance.** Test décisif : restreindre la médiane aux agents nés avant un tick donné, ou
apparier les cohortes sur la date de naissance. *C'est le confond que le backlog soupçonnait ; il n'est
pas dans la fonction de verdict mais dans la GRANDEUR qu'on lui donne.*

**P2.3 — ✅ FAIT (2026-07-21) — `_verdict_decomposition` calibré, et il PASSE.** La crainte (« le
bilinéaire a plus de paramètres et gagne mécaniquement par surajustement ») est **réfutée par mesure** :
sur un système authentiquement linéaire, le fit bilinéaire est **pire que la ligne de base** (1.587 vs
0.000) → `LATENT_LINEAR`. 3 formes livrées (bilinéaire / linéaire / monotonie en le bruit). **La prémisse
de la tétralogie G4 (PLAN-001/002/003/004) survit.**

**P2.4 — ✅ FAIT (2026-07-21) — l'instrument le plus central est calibré, et il PASSE.**
Étalon `world_demand_marker_probe` (DEMANDING = l'obs porte l'info / TRIVIAL = l'obs est un leurre) :
- **DEMANDING → `X_DEMANDED`** : 46.0 → 25.0 (ratio 1.84), `|W| ≈ 35.9` = politique réellement ENTRAÎNÉE.
- **TRIVIAL → `X_DECOY`** : 101.0 vs 101.0, ratio 1.00, `|W| = 0.000`.
- ⚠️ **Mesuré HORS PLAFOND exprès** (`gain < metab`) : aux défauts de l'étalon, les deux bras de TRIVIAL
  sont à **200/200**, le cap — la spécificité y serait démontrée sur une métrique SATURÉE. Régime durci
  → TRIVIAL vit à 101, DEMANDING à 46. C'est une **faiblesse de l'étalon** corrigée dans le cas de test.
- ⚠️ **En TRIVIAL, `|W| = 0.000` est la BONNE réponse**, pas un artefact d'optimiseur (contraste avec
  S2-004) : une politique optimale doit ignorer une obs non informative. Le gel de W y est la
  *conséquence* de la vérité-terrain, pas un plafond parasite.

**P2.4-bis — ⚠️ DÉFAUT DE MA PROPRE GARDE, trouvé en la calibrant (le jour même où je l'ai armée).**
La règle « bras identiques → `INCONCLUSIVE_DEGENERATE` » **bloquait le cas TRIVIAL**, c'est-à-dire la
vérité-terrain qui VALIDE le marqueur. Cause : des bras identiques ont **deux causes opposées**, et deux
tableaux de SORTIES ne permettent pas de les distinguer —
(a) l'intervention ne s'est pas appliquée (S2-007 matrice identité, S2-004 W gelé) → à bloquer ;
(b) elle s'est appliquée et n'a rien fait (l'obs EST randomisée, la politique l'ignore) → **nul légitime**.
Correctif : paramètre **`intervention_verified`** (défaut `False`, conservateur) — l'appelant atteste
avoir vérifié la perturbation de l'**ENTRÉE**, pas de la sortie. *Une garde trop zélée refuse le nul
là où le nul est la bonne réponse.* **Cliquet : 80 détectés, 8 calibrés.**

*(ancienne entrée P2.4, conservée pour le contexte)* **— 78 ✔** (carto 96, déflaté −18). **Dépendants réels : 10, pas 25** —
WARM-004/006/007/008 adoptent la MÉTHODE via `adopts:`, jamais la fonction ; S2-001/LANG-006/G1-001/
MEM-001 sont les **sources** dont le module fut extrait, pas des dépendants. Pur numpy, aucun bail ;
l'étalon est **déjà écrit** (`tools/world_demand_marker_probe.py`, mondes DEMANDING/TRIVIAL).
Dette annexe : l'`adopt_for` de REF-DEMAND-MARKER (19 entrées) est périmé — c'est ce décalage qui a
permis le gonflage.

**P2.5 — `compute_ab_verdict` — 74 ✔** (carto 92, déflaté −18). **19 dépendants réels, pas 32.** Risque
plus faible qu'il n'y paraît : le défaut ne produit que des **faux positifs**, or 13/19 concluent NEUTRE
et les 4 affirmations positives appliquent déjà `sign_p` à la main. ⚠️ **NE PAS MODIFIER** la fonction
(consigne sessions //) — calibration strictement ADDITIVE.

**P2.6 — ✅ FAIT (2026-07-21) — bundle Lewis calibré, 4 cas.** Mappings purs, aucun monde, aucun bail.
- **Générateur A** : les 4 coupables (`THROW` / `BIOLOGIE` / `BRAIN` / `MOUVEMENT`) + la branche diffuse
  sont TOUS atteignables. Un mapping qui ne sait désigner qu'un seul coupable ne diagnostique rien.
- **Frontière `> 0.5` STRICTE vérifiée** : un partage exactement 50/50 rend `DRAIN DIFFUS`, pas un
  coupable — c'est ce qui rend le verdict interprétable.
- **La bascule METABOLISME→CARRY est enfin ASSERTÉE** là où la docstring de `GroundTruthCarryWorld`
  l'annonçait sans jamais la tester : à `gt_carry == gt_metab` → `DIFFUS` ; à ±5 % → le bon coupable.
- **Piège documenté** : `bio_autres` porte les GAINS, n'est pas une cible de tarif, mais entre au
  DÉNOMINATEUR — un revenu important dilue les parts et pousse vers `DIFFUS`. À ne pas lire comme
  « rien ne domine » alors que c'est « un revenu masque ».
**Cliquet : 80 détectés, 10 calibrés.**

**P2.7 — ✅ FAIT (2026-07-21) — rétro-audit livré, 3 défauts trouvés, cause mécanique corrigée.**
Résultat gravé : **[EDR-AUDIT-001](../EDR/AUDIT-001_Retro_Audit_Null_Verdicts_Read_At_A_Bound_And_The_Guard_Is_Now_Armed.md)**.
- **Cause mécanique commune trouvée et CORRIGÉE** : `ablation_verdict` était un pur ratio de médianes
  sans garde de borne — il **produisait** le verdict NUL au lieu de le mesurer. Garde **armée par
  défaut** (décision robla) : `X_DECOY` → `INCONCLUSIVE_DEGENERATE`. `floor=9.0` déclaré dans
  `verdict_demand_marker`. 6 cas de calibration, non-régression 60 tests.
- **S2-004** : 3 cellules sur 4 ont `|W| = 0.0000` — W **gelé à l'init** (`sc > best` strict + score au
  cap). Le corroborant « |W| = 0.000 EXACT » est le zéro de départ. Sa cellule POSITIVE tient.
- **S2-007** : cellule `shift0` = **identité algébrique** (`_model_matrix(0,K) == np.eye(K)`, vérifié)
  → les deux bras calculent la même chose. Condition de nécessité tautologique (E1).
- **S2-006** (`foundational`) : transporte « corps SUFFISANT » du jouet (300/300 infini) vers la
  biosphère (champion mort à 27.5/200). ⚠️ Sa CONCLUSION garde un appui indépendant (cognition-vs-corps,
  BODY 5/5) — c'est la **dérivation** qui tombe, pas le verdict.
- **Négatif méthodologique consigné** : le rétro-audit **n'est pas automatisable de bout en bout**
  (2 échecs de calibration). Le code énumère, le jugement tranche — même partage que E9.

**P2.8 — ✅ FAIT (2026-07-21) — dettes du rétro-audit réglées PAR LA MESURE.**
- **`LinearCognitiveOracle` n'est plus du code mort** : `run_linear_sanity` livré. Mesuré K=12 →
  **oracle 200.0, ratio 14.81, `X_DEMANDED`**. La ligne que S2-011 publiait sans chemin d'exécution
  était **VRAIE** — elle n'avait juste jamais été lancée. *Une dette d'exécution n'est pas une
  présomption de fausseté.*
- **Le plancher de `cog_linear` était FAUX** : mesuré **13.5**, pas « ~7-8 » (importé du régime
  4-directions — classe E8 ; avec `dir ∈ {0,1}` on tombe juste 1 fois sur 2, pas 1 sur 4).
  ⚠️ **Conséquence** : les 3 bras de crédit (7.5 / 7.5 / 8.0) sont **SOUS** le plancher aveugle.
- **Bras « sans crédit » livré** (`use_credit=`) : `use_torch_inworld` était codé EN DUR. Les 3 bras
  reproduisent les chiffres publiés (7.5 / 7.5 / 8.0 vs 8 / 8 / 9).
- **Retriever corrigé dans `run_condition`** (`tools/s2_demand.py`) — la fonction PARTAGÉE, pas seulement
  `s2_demand_ablation` : il tournait pendant toute la simulation de **toutes** les sondes S2.
- **5 tests ajoutés**, dont 2 régressions **anti-code-mort** (un contrôle positif doit rester
  ATTEIGNABLE) + correction d'une égalité stricte de clés qui aurait cassé en silence (`skipif RUN_SLOW`).
- ⚠️ **ANGLE MORT DU CLIQUET trouvé en y tombant** : l'heuristique ne couvrait que
  `run_*_probe|diagnostic|ablation|validation`. `run_linear_sanity` est donc entré **sans que le cliquet
  bronche**. Motif élargi (`sanity|control|oracle|floor|map|sweep`) → **71 → 76 instruments détectés**,
  5 nouvellement VISIBLES. `run_linear_sanity` **calibré** (pas gelé — la discipline s'applique d'abord à
  ce qu'on vient d'écrire) ; les 4 légataires gelés au baseline. **Cliquet : 76 détectés, 4 calibrés.**

**P2.10 — ✅ FAIT (2026-07-21) — `run_cog_demand_map` calibré, et son contrôle NÉGATIF était vide.**
La sonde qui produit le **21.05 d'EDR-S2-009**, restée hors du champ du cliquet à cause du suffixe `_map`.
Re-mesurée au régime **publié** (0.75/12.0, pas les défauts de signature 4.0/6.0) :
- **ON : 200.0 vs 9.0, ratio 22.22, `X_DEMANDED`, non dégénéré** → le contrôle positif est CONFIRMÉ, et
  c'est lui qui porte le verdict de S2-009.
- **OFF : 7.0 vs 7.0 — bras BIT À BIT IDENTIQUES sur les 12 ères** → `INCONCLUSIVE_DEGENERATE`. En OFF,
  `forage_payoff=0` et pas de nourriture cognitive : tout le monde meurt à 7 ticks quoi qu'il fasse. Le
  « ratio 1.00 NEUTRAL » ne montre pas que le marqueur est spécifique, mais que **la métrique est morte**.
- ⚠️ **Portée** : la spécificité du marqueur est établie **ailleurs** (S2-001 monde TRIVIAL, LANG-006
  MI 0.000, MEM-001 — bras où les agents VIVENT et le ratio vaut 1.0). Le verdict de S2-009 tient.
- **La garde armée attrape le défaut sur des données de PRODUCTION**, pas une fixture ; pinée en
  calibration permanente. **Cliquet : 76 détectés, 5 calibrés.**
- **Subtilité d'ordre trouvée en chemin** : `ablation_verdict` teste `n >= n_floor` AVANT la garde de
  dégénérescence → à petit n, des bras identiques sortent `INCONCLUSIVE` (sous-puissant) et non
  `INCONCLUSIVE_DEGENERATE`. Sous-puissance et dégénérescence sont **deux défauts distincts** ; lire le
  champ `degenerate`, pas seulement le verdict.

**P2.9 — ✅ FAIT (2026-07-21) — hypothèse RÉFUTÉE en 30 s de calcul.** « Le substrat torch in-world a-t-il
un coût propre ? » Contraste within-subject sur le SEUL axe substrat (même cohorte fraîche, même monde,
même seed ; on bascule `use_torch_inworld`) : **ON = 7.2, OFF = 7.0**, ratio 0.97 sur 6 ères.
**Basculer le chemin torch ne change rien** → pas de coût de substrat.
L'écart avec le repère oracle-ablé (13.5) est une différence de **POLITIQUE** : un oracle au signal
brouillé émet une direction DÉCISIVE à chaque tick (juste 1 fois sur 2 en 1-bit), un `MambaAgent` à poids
aléatoires fait moins bien. **« Aveugle mais décidé » bat « aléatoire ».**
→ **S2-011 en sort RENFORCÉ** : la cohorte froide n'apprend réellement pas, aucun artefact ne l'excuse.
*Leçon : la piste ouverte le matin même a été fermée le soir pour un coût dérisoire — mesurer d'abord.*

**P2.1 — ✅ FAIT (2026-07-21) — branche `perception` calibrée, la plus vieille dette du cliquet.**
Elle porte les ratios publiés de WARM-001 (1.6→2.1) et WARM-003 (5.04) et n'avait **aucun** cas.
Étalon livré : `GroundTruthPerceptionWorld` + `make_perception_world` (dose = `cog_gain`, revenu corporel
`gt_income` obs-INDÉPENDANT). Sujet : le génome DAgger persisté (`results/warm003_dagger_genome.npz`).
- **inertie** à dose 0 : ratio **0.96** avec métrique VIVANTE (survie 19.5, plancher 9, plafond 200) ;
- **effondrement** à dose 6 : **4.25** (126.5 → 29.8) ;
- **monotonie** 0.96 → 2.64 → 4.25 sur doses 0/3/6.
- ⚠️ **L'étalon a une FENÊTRE, trouvée par échec** : revenu trop bas → la cellule à dose 0 est au
  plancher (inertie indémontrable) ; trop haut → la cellule à dose forte est au plafond (effondrement
  invisible, ratio retombé à 1.06). Point de fonctionnement mesuré : `gt_income = 10.0`.
- ⚠️ **FINDING pour les chiffres publiés** : au-delà de la fenêtre le ratio **REDESCEND** (3.14 à dose 12)
  car l'intact plafonne (~179/200) pendant que l'ablé continue de croître. **Tout ratio de cette branche
  dont le bras intact frôle `max_ticks` est une borne INFÉRIEURE compressée, pas une amplitude** — c'est
  ce que signale le champ `censored`. Même phénomène que la cellule positive de S2-007.

**P2.0-bis — ✅ FAIT (2026-07-21) — `champion_body` enfin gravé : [EDR-S2-012](../EDR/S2-012_Champion_Body_Foundational_Verdict_Finally_Recorded_With_Its_Four_Weaknesses.md).**
Direction CONFIRMÉE (le corps porte la survie, la politique du champion est survival-négative), mais
quatre affaiblissements **re-vérifiés par sonde propre** :
1. **« 5/5 mondes » en vaut 4** — `IndustrialWorld` est un clone de `Biosphere3D` (compteur `pollution`
   jamais lu) et `stoneage` EST `Biosphere3D` ; les deux lignes publiées sont identiques au chiffre près.
2. **Le volet `life_score` tombe à 2/5** sous la fonction `holm` du dépôt (appliquée à la branche survie
   mais pas à celle-ci) : `[0.009,0.038,0.007,0.038,0.025]` → `[0.036,0.076,0.035,0.076,0.075]`.
3. **`p = 0.0025` est le PLANCHER du test** (vérifié : `W=78, p=0.00253` à n=12 en séparation parfaite),
   apparu 10 fois sur 10 → statistique SATURÉE, ne gradue plus rien.
4. **Le bras qui produit le verdict est BETWEEN-subject** (`champion_body` vs `random_action` = génome
   champion vs génomes frais), et le n effectif sur « le corps » est **1 génome** cloné 20×.
+ aucun artefact de run (chiffres non re-dérivables) ; `random_action = 6` exactement sur les 5 mondes.
+ **2ᵉ angle mort du cliquet** : `scan_instruments` ne parcourait que `tools/` → `verdict_cognition_body`
  (`src/seed_ai/s2_stats.py`) était invisible. Scan étendu → **80 détectés, 5 calibrés**.
+ ⚠️ **J'ai amendé mes propres bandeaux** de S2-006 et AUDIT-001, qui citaient « 5/5 » comme appui
  indépendant sans l'avoir vérifié.

**P2.11 — ✅ FAIT (2026-07-21) — le contrôle positif du verdict FONDATEUR passe.**
Grille 2×2 dans le régime `cognitive_demand` calibré, cellule `champion` remplacée par l'oracle (politique
DONT ON SAIT qu'elle utilise sa cognition), génomes tous FRAIS (aucun corps à créditer) :
**oracle 200.0 / actions random 7.0 → verdict `COGNITION`** (`policy` p=0.0025 cliff=1.000 ;
`body` p=1 cliff=0.000).
- **Le verdict BODY de `champion_body` n'est donc PAS une incapacité d'instrument** : il discrimine.
  La moitié NULLE du finding fondateur devient **interprétable** — différence exacte avec WARM-002 et
  S2-006, dont les nuls n'avaient aucun contrôle positif. *« On n'a rien vu » vs « on aurait vu ».*
- ⚠️ Ne corrige AUCUN des 4 affaiblissements de S2-012 : établit la CAPACITÉ, pas l'amplitude.
- ⚠️ **Confirme le point 3 au passage** : même sur 200 contre 7, `p = 0.002526` (plancher) et
  `cliff = 1.000` (plafond). Les deux statistiques SATURENT — elles ne gradueront jamais rien.
- **Premier instrument de `src/` calibré.** Cliquet : **80 détectés, 6 calibrés**.

**P2.2 — Calibrer les instruments suivants par ordre de citation dans le graphe de records.**
`python tools/check_instrument_calibration.py --report` donne la liste (70 non calibrés). Ne PAS viser
l'exhaustivité : viser les **porteurs**. *Coût : ~2 h par instrument.*

**P2.3 — ✅ FAIT (2026-07-22) — hook pre-commit du cliquet de calibration livré.**
`tools/hooks/pre-commit` fait désormais DEUX vérifications indépendantes (records + calibration), chacune
gatée sur ses fichiers stagés, drapeau `fail` partagé. La garde calibration ne se déclenche que quand un
`.py` de `tools/` ou `src/seed_ai/` est stagé (le checker scanne l'arbre entier, pas de `--only`) →
n'ennuie pas les commits de docs seuls. Testé dans les deux sens : un instrument bidon non calibré
**bloque** (exit 1, message actionnable) ; l'arbre propre **passe** (81/12/0 nouveaux) ; un commit
hook-seul **skippe** la garde. Le cliquet ne dépend plus de la discipline — principe transverse n°1
(règle documentée sans application exécutable => violée) enfin fermé pour la calibration comme il l'était
pour les records. *Bypass d'urgence : `git commit --no-verify`.*

---

## P3 — Générateurs d'erreur encore sans réponse exécutable

*(Classes E11 et E13 du registre des erreurs — les deux seules SANS aucune garde.)*

**P3.1 — Pré-enregistrement du plan d'analyse.** **Aucune** analyse de la session n'a été pré-enregistrée :
seuil 0.5 sur `gi`, partition FRÉQUENT/RARE, choix du prédicteur — tous arrêtés APRÈS avoir vu les données
(jardin aux sentiers qui bifurquent). Étendre `declare_design` pour figer *statistique + seuil + critère*
avant le run, et faire lire ces valeurs par l'analyse au lieu de les choisir ensuite. *Coût : ~2 h.*

**P3.2 — Budget obligatoire, mesuré au smoke.** *Preuve : 3 runs abandonnés (8 h, 4 h projetées, 89 min),
plus WARM-009 nul et un run de 1,8 h sur une question sans objet.* Exiger un débit mesuré sur smoke + un
coût projeté avant tout run long, et **ne pas extrapoler une tendance depuis un préfixe court** (un
transitoire d'apprentissage y ressemble — erreur commise sur la dérive du grab). *Coût : ~1 h.*

**P3.3 — Indépendance des revues.** Les 7 revues ont trouvé du réel, mais ce sont des agents de même
architecture avec les mêmes priors : c'est de l'auto-critique outillée, **pas une réplication**. Piste :
faire re-dériver un résultat porteur depuis les données brutes par un chemin indépendant. *Coût : à cadrer.*

---

## P4 — Science

**P4.1 — Expérience famine (spécifiée, prête).** Seule question ouverte sur quatre records : « le grab
nuit-il quand grabber NOURRIT ? ». Matériel vérifié : `FamineWorld` hérite de `Biosphere3D` (donc porte la
taxe de portage) à `forage_payoff = 3.0` ; **30 champions déjà entraînés** dans
`data/hof_famine_harsh_s{42,43,44}.pkl`. Obstacle identifié : backend **legacy**, donc écrire un
`GrabOffMamba` sur le patron de `PerceptionAblatedMamba` — avec vérification d'aliasing obligatoire et
découplage des DEUX bras. Garde-fous posés : réplication sur les **ères**, contrôle négatif = manipulation
**INVERSE**, `gi` mesuré *in situ*, portée bornée au régime famine dure. *Coût : ~2 h + ~1 h de calcul.*

**P4.2 — Reste du backlog WARM** (cf. `SCIENCE.md`, fil WARM) : incidence du canal né-ON sur ≥6 agents et
≥2 seeds ; hypothèse du **canal porteur** (corrélation coût ↔ poids de W autour du nœud 88) ; bras à
revenu d'inventaire réel ; termes résiduels du bilan énergétique. *Coût : variable.*

---

## Principes transverses à ne pas reperdre

1. **Toute règle documentée sans application EXÉCUTABLE finit violée** — 3 fois en un jour, par moi, par
   le code d'instrument, et par la suite de tests.
2. **Un instrument non calibré ne se contente pas d'échouer : il PRODUIT un résultat** — l'aliasing a
   généré dose-réponse, corrélations et contrôle négatif cohérents entre eux.
3. **Un contrôle qui ne peut pas échouer n'est pas un contrôle** ; le contrôle informatif est la
   manipulation INVERSE.
4. **Réduire le n, jamais supprimer le maillon** — une chaîne causale transporte son signe, pas son amplitude.
5. **Ne pas généraliser depuis un cas saillant** (`agents[0]`, trois cas, une population) — erreur commise
   **trois fois**, y compris par le record qui la dénonçait. Non automatisable : d'où l'obligation de revue.

Cf. `docs/REF/REF-EXPERIMENT-PREFLIGHT.md`, `CLAUDE.md`, `tools/experiment_preflight.py`,
`tools/ground_truth_worlds.py`, `tools/check_instrument_calibration.py`, `tools/sim_session.py`.
