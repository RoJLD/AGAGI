# Fil conducteur — ce qu'AGIseed a appris (EDR 010→049)

> **But de ce document** : le *récit* de notre compréhension, synthétisé. Les EDR sont les preuves
> granulaires ; ceci est l'histoire qui les relie. À relire avant toute nouvelle vague.

## La thèse (le fil rouge)

> **« Le bon n'est pas dit mais trouvé — et il n'est trouvé que si le monde l'EXIGE. »**

Tout le projet teste cette idée (EDR 010/012). On n'*ajoute* pas l'intelligence : on construit un
monde dont la **demande** sélectionne l'intelligence. Chaque vague est une mise à l'épreuve, de plus
en plus dure, de cette thèse — jusqu'à la prouver (047) puis la raffiner (048/049).

> **⚡ TOURNANT (EDR 067→070) — UNE clé déverrouille tout :** après 60 EDR à durcir la *demande* et
> protéger l'*innovation*, on a trouvé la cause profonde commune des deux murs (langage, NAS) : **la
> faiblesse de la RECHERCHE par mutation seule.** Le **gradient** est la clé unique :
> - **067** : résout la mémoire (0.78→1.00) ; le NAS était un faux problème (capacité non-bindante).
> - **068** : devient l'apprentissage de l'agent + **Baldwin** (l'évolution façonne des inits apprenables).
> - **069** : crée une frontière *fertile* → le **#8 trouve ELU > tanh** (auto-amélioration réelle de l'agent).
> - **070** : fait **converger le langage** (jeu référentiel par gradient : decode 0.82-0.94, fiable, vs
>   loterie ~25 % de la mutation).
>
> **Le vrai levier n'était ni le monde ni l'architecture, mais COMMENT L'AGENT APPREND.** La graine
> APPREND, ÉVOLUE ce qui s'apprend, se RÉ-AMÉLIORE, et COMMUNIQUE — sous une seule clé.
>
> **Suite (071-072) — vers la biosphère :** essayer d'intégrer a *corrigé le diagnostic* (071) : la
> biosphère a DÉJÀ du gradient (l'Actor-Critic) ; l'écart 067 était un artefact du banc (mutation pure).
> Les murs venaient de l'**évolution** des architectures/conventions, pas de l'absence de gradient
> intra-vie. Et (072) le **jeu référentiel de POPULATION par gradient** fait converger une convention
> partagée **fiablement à 100 %** (vs 25 % loterie mutation) — la population *régularise* la brisure de
> symétrie. **Mécanisme validé** pour un langage fiable.
>
> **Câblage tenté (073) — l'écart banc→biosphère est ARCHITECTURAL :** porté sur le *vrai* connectome
> (apex@entrée 4, token@sorties 19:23), le jeu référentiel ne converge que partiellement (~0.5, vs 1.00
> MLP) — *pas* à cause de l'encodage (scalaire ≈ one-hot) mais parce que le connectome est un map
> **1-tick (réflexe)**, *sans couche cachée* entre apex et token. **Prescription** (déjà validée par
> 072) : une **tête référentielle DÉDIÉE** (MLP avec capacité cachée) branchée sur apex-perception +
> token, entraînée par le jeu de population. Le câblage = *ajouter cette tête* à l'agent vivant, pas
> copier 072.
>
> **CÂBLÉ (074) :** la tête référentielle dédiée est branchée dans le VRAI Biosphere3D (`use_ref_head`,
> injection à l'émission de token). Co-évolution des têtes = 100 % (code partagé). MI(token; apex)
> **LIVE = +0.22** (vs connectome −0.03, ≈ bruit) → **le langage référentiel fiable est passé du banc
> à l'agent vivant.** Fiabilité de la *mesure* live 50-67 % (pas la tête, mais la **rareté des actes de
> communication** : mort des agents, positionnement, porte de parole → peu d'échantillons). Le
> *mécanisme* est dans l'agent ; reste à enrichir l'**expression** (dynamique sociale) + co-évoluer en
> ligne. Le langage fiable est désormais une propriété *portée par l'agent vivant*, pas un résultat de
> banc.

## 🔜 REPRISE DE SESSION — 3 options (au 2026-06-11, après EDR 074)

Le langage référentiel fiable est **câblé dans l'agent vivant** (074). Il ne reste que du *raffinement
honnête* — pas un nouveau mur. Trois pistes, toutes fondées sur la mesure :

1. **Enrichir l'EXPRESSION** (le plus direct) — augmenter la fréquence des actes de communication près
   des apex (plus d'apex, meilleure survie, abaisser la porte de parole `speak_threshold`) pour que la
   MI(token; apex) *live* devienne **nette et fiable** (la limite actuelle 50-67 % est l'échantillonnage
   `n=4-37`, pas le mécanisme). Outil : `tools/wire_ref_head.py`.
2. **Co-évoluer les têtes EN LIGNE** — entraîner `ref_head` *dans* la boucle RL vivante (pas en offline
   pré-entraînement), pour que la convention émerge *pendant* la vie de la biosphère. L'intégration
   ultime. Point d'injection : `compute_policy_gradient` (un terme de gradient référentiel) ou un
   co-training entre ères.
3. **Le BÉNÉFICE FONCTIONNEL** — vérifier que les *auditeurs* chassent mieux grâce au code fiable
   (le token référentiel doit améliorer la chasse coopérative : approcher le Mammouth, fuir le Leurre).
   Mesurer mammouth_kills / survie avec `use_ref_head` ON vs OFF.

> Acquis à ne pas perdre : `referential_head.py` (tête + co-évolution 072, decode croisé 100 %),
> câblage `use_ref_head`/`_apex_idx`/injection token (gated, 141 tests verts). Le mécanisme du langage
> fiable est **dans l'agent** ; ces 3 pistes le font *s'exprimer*, *émerger en ligne*, et *payer*.

## 🧱 EDR 075 — le bénéfice fonctionnel est GATÉ par la COMPÉTENCE (négatif honnête)

On a testé l'option 3 (« le langage paye-t-il ? ») : décode-et-agis (approche Mammouth / fuit Leurre),
FIABLE vs BRUITÉ vs SOLO. **Résultat : aucun bénéfice.** Le mécanisme se déclenche (~80×) mais ne change
rien (FIABLE ≈ BRUITÉ ≈ SOLO ≈ 2 Leurres) ; **survivants=0, Mammouths=0 partout** (les agents frais ne
savent ni survivre ni chasser). Un signal prometteur à 3 seeds a *évaporé* à 8 (comme EDR 057).

> **Enseignement (capacités STRATIFIÉES) :** un code fiable est *nécessaire mais pas suffisant*. On ne
> récolte pas le bénéfice d'une capacité HAUTE (langage) sans la compétence BASSE (survie, chasse
> coordonnée) pour l'exploiter. **Le goulot n'est pas le code — c'est la COMPÉTENCE du substrat**, et
> c'est *prouvé* (mécanisme qui tire à vide). Prochain levier : **compétence de foraging d'abord**
> (faire évoluer des agents qui survivent + chassent le Mammouth), *puis* le langage la démultiplie.
> Ordre correct : compétence → langage. Infra prête (`decode_act`, gated) pour re-tester sur substrat
> compétent.

## 🔑 EDR 076 — la compétence PLAFONNE : la mutation est un forgeron faible (LA BOUCLE SE REFERME)

On a sondé le moteur : la compétence évolue-t-elle sous mutation + extinction + cliquet HoF ? (Harnais
isolé, validé contre la référence après avoir débusqué 2 bugs — élitisme, chargement HoF.) **Sans
cliquet : effondrement** (59→5 ticks). **Avec cliquet (HoF réel) : PLATEAU** (survie ~30, life_score
plat 402→442, Mammouths sporadiques) — *maintenue, pas forgée* — **malgré l'Actor-Critic intra-vie**.

> **LA BOUCLE DU PROJET SE REFERME.** Trois fois la même vérité, maintenant sur le levier le plus
> fondamental : **mémoire (067)** mutation 0.78 → gradient 1.00 ; **langage (072)** mutation 25 % →
> gradient 100 % ; **compétence (076)** mutation *maintient* (cliquet) mais ne *forge* pas. **La
> mutation est un forgeron FAIBLE partout ; le levier universel est le GRADIENT FORT** (classe BPTT,
> 067), à horizon long, DANS l'agent. Le cliquet empêche la perte — il ne crée pas la compétence.
> Grand chantier cohérent : **le gradient fort dans la vie de l'agent** (mémoire, langage, ET
> compétence), là où la mutation a montré ses limites.

## ⚠️ EDR 077 — CORRECTION : le gradient n'est PAS universel (le BPTT NUIT en RL)

On a testé la prescription d'EDR 076 sur banc (foraging-mémoire RL, 3 moteurs). **Réfutée.** Ordre
INVERSE : **mutation 5.58 > one-step 4.96 > BPTT 2.10** (le gradient fort est le PIRE ; le clipping ne
le sauve pas — c'est la variance). 

> **« Le gradient est la clé universelle » (esquissé en 076) était une SUR-GÉNÉRALISATION.** Vérité
> corrigée : le gradient gagne en **SUPERVISÉ** (mémoire 067, langage 072 — cible dense, faible
> variance) ; en **RL compétence** (foraging), la mutation est compétitive/meilleure et le **BPTT NUIT**
> (variance du gradient de politique à travers le temps). Donc le plateau de 076 vient de la
> **DIFFICULTÉ DE RECHERCHE** (172-D, fitness bruitée), PAS de la faiblesse de la mutation ni d'un manque
> de BPTT. **Ne pas intégrer le BPTT pour la compétence.** Lever réel : meilleur signal de fitness /
> curriculum / réduction de dimension. Le banc a réfuté ma propre prescription *avant* un gros chantier
> voué à empirer la compétence — la discipline du projet (tester, pas extrapoler).

## ✅ EDR 078 — RÉSOLU : le plateau est du BRUIT DE MESURE (évaluer robustement)

EDR 077 désignait « meilleur signal de fitness ». Test sur banc : on fait varier `eval_B` (nb d'épisodes
pour évaluer un génome). **Relation monotone parfaite : compétence 2.0 (eval_B=1) → 5.8 (eval_B=64)**,
≈ ×3, *uniquement* en nettoyant le signal.

> **Le plateau de compétence est un problème de MESURE, pas de moteur.** `eval_B=1` (1 ère bruitée,
> comme la biosphère) = **2.03** — *exactement* le plateau de 076 ET le BPTT (2.10). En évaluant chaque
> génome sur UNE ère bruitée, la biosphère se condamne au pire score. Signal propre → la mutation forge
> **5.8** (bat one-step 4.96, écrase BPTT 2.10). **Levier (actionnable) : ÉVALUER ROBUSTEMENT** —
> K eres/épisodes par génome avant sélection HoF. L'arc compétence se résout : 075 (goulot) → 076
> (plateau) → 077 (pas le BPTT) → **078 (c'était le bruit ; nettoyer la mesure)**.

## 🏭 EDR 080 — le remède EN PRODUCTION + validé avec PUISSANCE

(1) **Production (gated)** : `config.robust_hof_K` (défaut 0), `src/seed_ai/robust_hof.py`
(`robust_evaluate`/`robust_rank`), `save_to_hall_of_fame(score=)`, injection gated dans `main_biosphere`
(ré-évalue les candidats HoF sur K ères → score robuste). Non-régression : **146 tests verts** ; smoke
réel OK. (2) **Validation puissante (R=4 runs/K)** : compétence vraie **31 (K=1) → 44 (K=4) → 46.5
(K=8), +50 %**, MONOTONE — le K=4 qui avait chuté en run unique (079) était du bruit. Et l'écart-type
**diminue** avec K (13.5→8.5) : de-bruiter forge *plus* ET *plus fiable*.

> **Arc compétence CLOS : 075 (goulot) → 076 (plateau) → 077 (pas le BPTT, auto-réfutation) → 078 (bruit
> de fitness, banc ×3) → 079 (vivant +27 %) → 080 (PRODUCTION gated + puissance +50 %).** Du diagnostic
> au correctif livré, prouvé, testé. Recommandation : `robust_hof_K=4` pour les runs sérieux (laissé à 0
> par défaut — choix coût/compétence de l'utilisateur).

## 📈 EDR 081 — le remède COMPOSE : la compétence GRIMPE sur les générations

Test le plus exigeant (la vraie promesse d'un moteur évolutif) : la compétence s'accumule-t-elle au fil
des générations ? Compétence vraie aux checkpoints (24 générations) :

| gen | 6 | 12 | 18 | 24 | pente |
|---|---|---|---|---|---|
| BRUITÉE (K=1) | 32.8 | 30.4 | 28.6 | 29.8 | **−3.0** (stagne) |
| ROBUSTE (K=4) | 42.8 | 54.1 | 52.2 | 55.2 | **+12.4** (grimpe) |

> **Sous sélection bruitée, la compétence STAGNE/décline (l'échec de 076) ; sous robuste, elle GRIMPE
> (43→55).** Le fix COMPOSE : la biosphère ne se contente plus de *maintenir*, elle *progresse*. Reco
> appliquée : `main_biosphere` tourne en `robust_hof_K=4`. **Arc compétence (075→081) CLOS** — du goulot
> diagnostiqué (075) au moteur qui progresse enfin (081), via une seule cause comprise (bruit de fitness,
> 078). Prochaine frontière : re-tester le bénéfice du langage (075) sur ce substrat désormais COMPÉTENT
> et croissant.

## 🔁 EDR 082 — la grande boucle : compétence NÉCESSAIRE mais PAS suffisante

On a re-testé le bénéfice du langage (075) sur le substrat compétent (évolution robuste dans Lewis) :
FIABLE (tête + décode-et-agis) vs SOLO, **apparié**. n=4 suggérait FIABLE>SOLO (Mammouths 5.0/3.25) ;
**à n=12, ça s'ÉVAPORE** : diff appariée −0.67 ± 0.86 SE, FIABLE>SOLO dans 33 % des seeds. (4ᵉ fois de
la session qu'un signal à peu de seeds disparaît sous puissance — 057, 075, 077, 082.)

> **Le langage ne paye PAS, même compétent. Vérité affinée : la compétence est NÉCESSAIRE mais PAS
> SUFFISANTE.** Les agents sont sélectionnés pour SURVIVRE, pas pour UTILISER les signaux ; le
> décode-et-agis est *imposé*, pas *sélectionné*. Le bénéfice d'une communication n'émerge que quand son
> USAGE est sous pression de sélection (reboucle sur la loterie de 053). On a le code fiable (072-074) +
> le substrat compétent (076-081) ; il manque la **co-évolution de l'USAGE du langage avec la survie**.
> C'est le prochain levier, et la vraie réponse à « pourquoi le langage utile n'émerge pas tout seul ».

---

## Acte I — Faire émerger une chaîne moyens→fins (EDR 010→030)

| EDR | Acquis |
|---|---|
| 010 | **Audit réel vs théâtre** : distinguer ce qui émerge vraiment de ce qu'on a scripté. |
| 011/012 | **World Model (curiosité)** + **monde exigeant** : la rareté force l'apprentissage. |
| 018/021 | **Axe craft** : rock+stick→spear→Mammouth (la chaîne d'outils). |
| 020/023 | **Vrai Actor-Critic TD** (on remplace le hebbien rustre par du RL avec crédit d'action). |
| 022/028 | **Coup critique** puis **récompense de groupe** : la coopération rend la chaîne robuste *sans* dépendre du crit chanceux. |
| 027/029/030 | Chaîne **intégrée 2D**, **dominante**, **auto-suffisante** (scaffolds sevrés). |

**Leçon I** : une chaîne sociale complexe (chasser l'apex en pack) *émerge* sous une demande de
rareté + coopération. La thèse tient à petite échelle.

## Acte II — Honnêteté + l'infrastructure de la « graine » (EDR 031→036)

| EDR | Acquis |
|---|---|
| 031 | **Câbler les gènes fantômes** (thresholds, W_router) au lieu de les tuer — fidèle à l'émergence. |
| 032/034 | **Ablation** + **ontologie KuzuDB** (Hypothesis/Fact) + graphe projet. |
| 033 | **Unifier le moteur des mondes** (l'axe Monde). |
| 035 | **Sandbox sécurisée** (gate AST + subprocess isolé) — *la cage*. |
| 036 | **Superviseur réflexif** (tendance multi-ères) — *les yeux* + le seam LLM. |

**Leçon II** : avant d'ouvrir les mains de la graine (auto-réécriture), on bâtit la **cage**, les
**yeux** et la **mémoire**. Sécurité *avant* puissance.

## Acte III — L'enquête du langage (EDR 037→047) — le cœur

Le récit le plus serré du projet. Une frontière (le langage référentiel) qui résiste, puis cède.

| EDR | Intervention | Le token… |
|---|---|---|
| 037 | activer le canal de signal | **bruit** (impasse) |
| 038/040 | **portée** du signal | aide — mais via la **présence** |
| 042/043 | brouillage (sens détruit, présence gardée) | **présence confirmée, PAS le contenu** (MI≈0) |
| 045 | pression référentielle **scriptée** | **échec** (gameable) |
| 044 | architecture de la boucle RSI (#8) **câblée, non armée** | — |
| 046 | arming dirigé **NAS** + **leçon unifiée** | (voir Acte IV) |
| **047** | **demande réelle (monde de Lewis)** | **RÉFÉRENTIEL — émerge** (MI 0.0006→0.033, ×55) |

**Leçon III (le sommet)** : le langage ne s'*ajoute* pas (037/045 échouent). Il **émerge** quand le
monde le rend *nécessaire* — le monde de Lewis (Mammouth nourricier vs Leurre piège,
indistinguables à distance → il *faut* le signal). **La thèse est prouvée au bord le plus dur.**

## Acte IV — La leçon unifiée + la recette raffinée (EDR 046, 048→049)

| EDR | Test | Résultat |
|---|---|---|
| 046 | forcer la croissance NAS (monde de base) | architecture **figée à 172** — le monde n'exige pas plus de cerveau |
| 048 | renforcer le langage (3 référents) | **pas de lexique** — silence (altruisme du signal) |
| 049 | NAS dans le monde exigeant (Lewis-3) | architecture **toujours figée** (mauvaise demande + collapse) |
| 050 | incitation du locuteur (réciprocité) | **pire** — crédit temporel (prime au kill, pas au signal) |

**Leçon IV (la recette)** : « la demande crée la capacité » est **vraie mais exigeante**. La demande
doit :
1. **CIBLER** la capacité précise (référentielle→langage ; mémorielle/computationnelle→architecture) ;
2. être **SURVIVABLE** (sinon pas de sélection).
Un « monde plus dur » générique ne suffit pas. **Concevoir la bonne demande est *le* travail** — et
c'est le rôle recadré du **#8** (proposer+itérer des demandes ciblées).

## Acte V — Armer l'itérateur (#8), et son vrai goulot (EDR 050→051)

Les designs manuels ratent (045/048/049/050 : **4 tentatives, 3+ échecs**, chacune par un défaut
subtil *trouvé par la mesure*). Ce pattern *est* l'argument du #8 : un générateur qui itère sur des
centaines de designs en mesurant chacun battrait la conception à la main.

| EDR | Pas | Acquis |
|---|---|---|
| 051 | étendre le #8 au périmètre **`world_demand`** + boucle propose→mesure→classe | **construite, testée** (rsi_loop) ; la démo classe les demandes |
| 052 | **harnais d'évaluation puissant** (multi-seeds + signification) | construit, testé ; **recalibre nos verdicts à 1 run** |

**Leçon V (le goulot, puis la recalibration)** : la boucle #8 marche mécaniquement, mais la démo
(12 ères) a **classé par le bruit**. Le harnais (052, 3 seeds × 18 ères) tranche enfin… en refusant de
conclure : **les 3 demandes ne se séparent pas** (t=0.24). Pire — il révèle que **nos verdicts à 1 run
étaient non fiables** : `lewis_2ref` (047) fait 0.019 / **0.002** / 0.017 selon le seed (les 0.033 de
047 étaient un *tirage favorable* ; vraie moyenne ~0.013 ± 0.009), et `referential_pressure` (045
« échec ») a un seed à 0.039. **Le succès 047 ET l'échec 045 étaient en partie du bruit.** Un itérateur
ne vaut QUE ce que vaut sa mesure — et une mesure fiable, à cet effet (~0.01 MI, σ≈0.01), coûte **≫ 3
seeds**. La discipline de mesure (039/041) devient une **contrainte d'architecture chiffrée**.

---

## Où on en est (au 2026-06-11)

- ✅ Chaîne moyens→fins émergente, robuste, dominante, auto-suffisante.
- ✅ Infrastructure RSI (#8) **câblée mais NON armée** : cage (035), yeux (036), mémoire (032/034),
  juge (041), boucle (044), **périmètre `world_demand` + boucle propose→mesure→classe (051)**. Le
  seam LLM attend (a) un harnais d'évaluation puissant, (b) un conteneur jetable.
- 🎲 Langage : émergence sous demande **réelle mais STOCHASTIQUE** (053, 8 seeds) — une *loterie* qui
  se cristallise dans ~25 % des runs (2/8 forts à MI 0.03-0.05, 6/8 au bruit). La thèse tient
  *probabilistiquement* ; 047 (0.033) était un tirage chanceux mais pas un artefact. **Brisure de
  symétrie** (coordonner une convention).
- ⛔ Fiabiliser (054-057) : **CLOS sur un négatif propre.** Align-énergie (055) semblait prometteur
  (33→50 %) mais à **40 seeds (057) = NUL** (28 % vs 32 %, le n=6 était du bruit) ; align-fitness (056)
  backfire. **6 mécanismes à la main (045-057), zéro qui fiabilise.** La loterie ~25-32 % tient. Le
  harnais **vindiqué** (il a refusé de nous laisser croire à 055). → l'approche manuelle du langage est
  *exhaustée* ; pivot **forcé** vers NAS/#8 ; l'argument du #8 devient un *résultat empirique*.
- ✅ Harnais d'évaluation puissant **construit + utilisé** (052/053) — verdicts *avec confiance*.
- 🧠 NAS (058) : même une **demande de mémoire** (apex transitoire) ne grandit pas l'archi (172/172,
  comme 046/049). Vrai obstacle découvert : `add_node` est *neutre* (split NEAT), mais le HoF
  élitiste strict **bat l'innovation immature** avant qu'elle mûrisse → croissance jamais retenue.
- 🔓 #8 (059) : `LLMProposer` rendu **armable** (LLM injecté comme `llm_fn`, gardé, testé au mock).
  Armable en 1 ligne ; reste **désarmé** (besoin conteneur + harnais en `measure_fn`).

## ⚡ L'unification (le mur commun des deux frontières — EDR 054 ⊕ 058 ⊕ 060)

> **Une sélection élitiste stricte par une fitness établie TUE la nouveauté avant maturité.** Langage
> (054 : convention faible, sélection aveugle) et architecture (058 : nœud immature, battu par les
> rodés) échouent pour la **même** raison : *rien ne protège l'immature*. Défaut de **dynamique de
> sélection**, pas de demande. Lever : **protéger la nouveauté** (spéciation NEAT).
>
> **Testé (060)** : la spéciation-par-taille **protège bien** (des archis 173-174 *persistent* enfin,
> vs 172 verrouillé) — mais **ne suffit pas** seule.
>
> **Le grand raffinement (062-063) — les remèdes DIVERGENT :**
> - **NAS (062)** : même avec 3 bits + 36 ères + spéciation, l'archi ne prolifère pas. **Le
>   foraging ne sature fondamentalement pas 172 nœuds** (tâche réactive, mémoire peu profonde).
>   Protection *résolue* (spéciation) ; demande *non réparable dans ce substrat* → il faut une
>   **tâche-mémoire dédiée** (hors foraging).
> - **Langage (063)** : porter la spéciation par token **BAISSE** l'émergence (33→17 %, d=−0.48).
>   **NAS doit EXPLORER (diversité protégée = bien) ; langage doit CONVERGER (diversité protégée =
>   mal).** Dynamiques **OPPOSÉES**. La spéciation est l'outil du NAS, *pas* du langage (qui relève de
>   la **pression de convergence / sélection de groupe**).
>
> **Bilan** : l'unification d'EDR 058 tient au *diagnostic* (la sélection stricte tue la nouveauté)
> mais les *remèdes* sont frontière-spécifiques.
>
> **NAS — CLOS (064)** : sur un banc cognitif dédié (rappel de K bits, hors foraging), la croissance
> *marche* (après correction d'un bug de driver) mais est du **BLOAT NEUTRE** : le trivial (K1, acc
> 1.00) gonfle *plus* (35 nœuds) que le dur (K6, 26 nœuds) — la croissance suit le *mou*, pas la
> demande ; et plus de capacité **n'aide pas** (K6 acc 0.78 à 19 ou 26 nœuds). **La croissance UTILE
> d'architecture n'a pas lieu** dans AGIseed — goulot mécanique : `add_node` neutre/disruptif +
> recherche par *mutation seule* incapable d'exploiter la capacité. Vrai NAS = opérateur de croissance
> *utile* + apprentissage par *gradient* (changement fondamental ; candidat #8).

## Le #8 — ARMÉ, LIVE, SÛR (EDR 059+061+065)

Cage (035) · yeux (036) · ontologie (032/034) · catalogue `world_demand` (051) · proposer LLM
injectable (059) · mesure PUISSANTE (harnais en `measure_fn`, 061) · **frontière de sûreté**
(`sanitize_demand_params`, allow-list bornée) · **connecteur LLM local** (`local_llm_fn`, LM Studio/
Ollama).

> **ARMÉ POUR DE VRAI (065)** : Gemma-12B local dans la boucle — il lit les résultats mesurés,
> *raisonne* sur les échecs, propose des demandes NEUVES, le harnais les mesure (multi-seed), ça
> itère. **La boucle d'auto-amélioration est vivante.** SÛR sans conteneur car `world_demand` = params
> *bornés* (aucun code exécuté) + LLM *local* (aucun appel externe) + *sanitizer* strict ; le conteneur
> (EDR 044) ne reste requis que pour le kind `activation`/code.
>
> **Espace d'action élargi (066)** : le #8 est aussi armé sur le kind **`activation`** (le LLM propose
> des fonctions d'activation = CODE, validé par la sandbox EDR 035, exécuté). Il améliore donc l'**agent**,
> pas que le monde. qwen-coder a proposé 6 activations, toutes sandbox-validées ; **aucune ne bat tanh**
> (0.799) — et c'est la *bonne* réponse (tanh est quasi-optimal pour la mémoire récurrente). Le #8 ne se
> ment pas.
>
> **Limite honnête (065+066)** : le #8 *fonctionne et est sûr* (monde + agent), mais n'a pas trouvé de
> *breakthrough* — non par défaut de mécanisme, mais parce que ses frontières cibles sont **barren**
> (langage, 057) ou **déjà optimales** (tanh, 066). Il lui faut un espace où l'amélioration EXISTE.
> **Cette frontière, c'est le GRADIENT (BPTT)** : il donnerait un substrat où l'architecture/l'activation
> *paient* (débloquant le NAS, 064) — le gros morceau de fond restant.

## Les prochaines cibles (nettes, fondées sur la mesure)

1. ✅ **Harnais d'évaluation PUISSANT** (052) + **047 re-confirmé sous puissance** (053) — *faits*.
2. **Fiabiliser l'émergence** (054) : **aligner la sélection sur la convention** — un terme de fitness
   référentiel (faible, annealé), car `life_score` est aveugle au langage. Métrique = **taux
   d'émergence** *via le harnais* (multi-seed), pas la moyenne d'un run.
3. **NAS** — une **tâche-mémoire survivable**, évaluée *via le harnais* (sinon bruit).
4. **Langage** — incitation du locuteur **au tick du signal** (trace d'éligibilité — EDR 050) +
   **affordances distinctes**, évalué *via le harnais*.
5. **#8** — une fois la mesure fiable + budgétée : LLM en conteneur, propose des demandes
   `world_demand`, lit les échecs via l'ontologie, **itère** sous évaluation puissante (≫ 3 seeds).

## 🚀 Résolution Définitive de l'Arc 4 : Le Langage Ultime (LU) Continu (M1 à M5)

Le dilemme historique d'Arc 4 (tokens discrets 1-of-4 écrasant l'espace sémantique, bloquant la survie à 40 ticks) a été résolu par la branche **Langage Ultime (LU)** :
- **Gigatokens Continus $z \in \mathbb{R}^D$** : Transmission subquadratique $O(N)$ préservant la métrique euclidienne et les angles d'approche.
- **Traduction Mutuelle Intersubjective (`MutualLatentTranslator`)** : Co-adaptation Procruste SVD avec cycle-consistance ($A \to B \to A$) permettant à des connectomes divergents de communiquer sans dictionnaire centralisé.
- **Preuve Causale Scalée (450 runs, 50 seeds)** : Survie médiane bondissant de **40.0 ticks à 138.0 ticks (+245%, ratio 3.45x)**, CKA sous bruit sévère ($\sigma=0.15$) à **0.8842** ($p < 0.001$).
- **Pérennité Génétique HGT** : Transmission des variétés de projection latentes aux nouveau-nés et absorption horizontale entre pairs lors de surprises cognitives.
- **Auditabilité Dashboard** : Décompilation instantanée des pensées d'agents vivants en français/anglais via `LUHumanExplainer` et affichage temps réel dans le dashboard.
- **Clôture :** Arc 4 validé et clos (Article 006 dans KuzuDB). L'Arc 5 (La Tribu, Culture & Craft Partagé) et l'Arc 6 (EXP-9 : Maîtrise du Feu) sont désormais opérationnels.

## 🏛️ Résolution des Arcs 5 & 6 : Émergence des Rôles, Maîtrise du Feu et Transmission Culturelle (Article 007)

L'Arc 5 (La Tribu) et l'Arc 6 (EXP-9 : Rituels du Foyer) étendent la communication continue par Gigatokens à la dynamique collective :
- **Émergence Endogène des Rôles (Sevrage du Scaffolding)** : Remplacement de l'attribution rigide de rôles fixes par une inférence descriptive *a posteriori* (`infer_emergent_roles`) basée sur les comportements effectifs (émission de signaux $\to$ SCOUT, fabrication d'outils $\to$ CRAFTER, prédation active $\to$ HUNTER).
- **Synergie Coopérative Non-Supervisée** : Déclenchement de la coordination de meute et du bonus de capture ($\times 3.0$) dès qu'un signal directionnel saillant est transmis et intercepté, sans exiger d'étiquettes artificielles préalables.
- **Thermodynamique Sociale du Foyer (EXP-9)** : Réduction de 80% du bruit acoustique de propagation ($\sigma_{\text{eff}} \times 0.2$) à proximité d'un feu de camp actif, offrant un sanctuaire d'écoute et de calme rituel restaurant la vitalité métabolique (+0.1 énergie).
- **Transmission Culturelle Orale de Recettes** : Les agents rassemblés autour du feu s'échangent spontanément des recettes artisanales complexes projetées sur la sphère unité $\mathbb{S}^{D-1}$ et décodées via le traducteur mutuel.
- **Clôture & Journalisation :** Validé empiriquement par banc de simulation (Survie LU 300 ticks vs Discret 40 ticks, ratio $\times 7.50$, CKA = 0.9962) et consigné dans KuzuDB sous l'identifiant `art_007_emergence_culture_arc5` (Article 007).

## 🔮 EXP-10 : Test-Time Compute Adaptatif (TTC) & MCTS Instrumental

L'anticipation cognitive et le raisonnement contrefactuel sont désormais portés par le modèle de transition latent :
- **Recherche MCTS Instrumentale Multi-Pas (`mcts_instrumental_search`)** : Les agents dotés du cortex simulent des trajectoires d'actions futures $(s, a \to \hat{s}, \hat{r})$ sur une profondeur paramétrable ($D \ge 3$) avec sélection UCB.
- **Budget Énergétique Différenciable** : Le calcul mental alloué $\text{TTC}_i \propto \text{Surprise}_i \times \text{do\_dream}_i$ est facturé à l'agent de façon sub-linéaire ($0.01 \times (1 + \log_2(1 + K))$), pénalisant la rumination stérile et récompensant la planification féconde.
- **Non-Régression Bit-Exacte :** Désactivé par défaut via `ENABLE_INSTRUMENTAL_MCTS = False`, activable via configuration sans fork architectural.

## 🌾 Monde 2 : L'Âge Agricole & Révolution Néolithique (`AgriculturalWorld`)

Transition écologique majeure de la prédation opportuniste vers la production et la prévoyance saisonnière :
- **Rythme Circadien & Saisonnier** : Cycle quadri-partite (Printemps $\to$ Été $\to$ Automne $\to$ Hiver) imposant une planification à long terme.
- **Phytotechnie & Croissance** : Semailles (`Seed` $\to$ `Planted_Seed`), germination printanière et maturation estivale produisant des fruits.
- **Greniers Communautaires (`Granary`)** : Stockage centralisé des surplus durant l'abondance automnale et redistribution calorique vitale face à la rigueur de l'hiver (-0.2 E/tick sans abri).
- **Coordination Agricole par Gigatokens LU** : Amplification de $+50\%$ du rendement des cultures (`lu_agricultural_synergy = 1.5`) lorsque les semailles et récoltes sont coordonnées collectivement par signaux latents continus.

## 🌙 Arc 6 & EXP-11 : Métacognition Épisodique & Rêve Collectif (Article 010)

Séparation neurobiologique du temps d'action (jour) et du temps de consolidation mnésique (nuit) :
- **Modèle de Soi Métacognitif (`SelfModel`)** : Prédiction anticipée du coût énergétique $\hat{c}(s, a)$ et du succès $\hat{p}(s, a)$, générant un signal d'erreur de prédiction (surprise) modulant l'attention.
- **Consolidation Collective Vectorisée (`BatchNightConsolidator`)** : Vectorisation matricielle pure en NumPy entraînant simultanément toute la population sur les épisodes saillants.
- **Débiaisement Métabolique Isocalorique** : Phénotype `isocaloric=True` éliminant tout artefact corporel de la norme des poids synaptiques $W$ pour mesurer une intelligence pure.
## 🌐 Langage Ultime Phase 2 : Compositionnalité Sémantique HRR, Relais Acoustique Multi-Hop & Décompilation KuzuDB (Article 011)

L'émergence compositionnelle franchit le cap du continu holistique vers une véritable algèbre vectorielle symbolique :
- **Algèbre Sémantique HRR Unitaire (Commandement 3)** : Convolution circulaire unitaire à spectre plat $|\mathcal{F}(R)| = 1$ et déconvolution spectrale de Wiener régularisée sur la sphère $\mathbb{S}^{D-1}$. Permet la composition et le déliage fiable de triplets argumentaux (Sujet, Prédicat, Cible, Urgence) sans interférence destructive (similarité post-déliage $\ge 0.45$ vs bruit $< 0.10$).
- **Relais Acoustique Multi-Hop & Consensus Spatial In-World** : Rediffusion des signaux latents au-delà de la ligne de vue directe avec atténuation géométrique et synchronisation de meute (`cooperative_hunt_active`), débloquant la coordination de meute à longue distance.
- **Pont Symbolique-Neuronal Bidirectionnel (KuzuDB & LangGraph)** : Compilation descendante d'ordres symboliques en Gigatokens continus injectables dans les connectomes Mamba, décompilation ascendante en langage naturel et inscription vivante des lexèmes émergents (`LULexeme`) dans la mémoire Lattice.
- **Clôture & Journalisation** : Validé empiriquement sous la Loi du Sociologue (Commandement 15) et certifié dans KuzuDB sous l'identifiant `art_011_langage_ultime_compositionnel` (Article 011).

## 🧠 Langage Ultime Phase 3 : Récursion Grammaticale, Théorie de l'Esprit Latente et Consensus Délibératif Distribué (Article 012)

Le saut scientifique de la Phase 3 franchit le mur du dialogue et de la délibération distribuée (G3) :
- **Algèbre Récursive Hiérarchique & Clause Unitaire** : Extension VSA/HRR introduisant la clé unitaire $\mathbf{r}_{\text{clause}}$ ($|\mathcal{F}(\mathbf{r}_{\text{clause}})| = 1$). Permet l'emboîtement de sous-clauses propositionnelles à 2 niveaux (ex: *"SCOUT INFORMS [HUNTER HUNT PREY]"*) avec rappel cyclique de profondeur 2 garanti $\ge 0.40$ sur $\mathbb{S}^{D-1}$.
- **Théorie de l'Esprit Latente (ToM) & Silence Pragmatique** : Chaque agent maintient une croyance bayésienne $\hat{\mathbf{z}}_{\text{peer}}$ de l'état latent d'autrui. Si l'information est redondante ($\ge 0.85$), l'agent choisit le silence pragmatique (RSA continue). Résultat : +82.1 silences/ère épargnant $+14.98$ points d'énergie métabolique et éliminant le spam acoustique.
- **Consensus Délibératif Distribué au Coin du Feu** : Lors des rituels nocturnes au feu de camp, la meute négocie les décisions collectives en $K$ tours par barycentre pondéré sur la variété sphérique de Fréchet. Dès accord $\ge 0.60$, le consensus est injecté dans les connectomes pour orienter les chasses de l'aube.
- **Auditabilité Graph-RAG KuzuDB (`LUDeliberation`)** : Décompilation symbolique ascendante des débats de meute et archivage immuable des consensus dans la table KuzuDB dédiée.
- **Clôture & Journalisation** : Validé par le banc sociologique de 30 ères (Commandement 15 : delta énergie $+14.98$, delta survie $+0.33$, delta chasses $+0.57$) et consigné dans KuzuDB sous l'identifiant `art_012_langage_ultime_tom_deliberation` (Article 012).

## ⚖️ Langage Ultime Phase 4 : Spéciation Dialectale, Contrats Latents de Troc et Marché Décentralisé (Article 013)

L'émergence des institutions économiques décentralisées franchit le mur de l'autarcie (G4) :
- **Variétés de Grassmann $Gr(k, D)$ & Distance Géodésique** : Modélisation continue de la dérive dialectale inter-clans par sous-espaces orthonormés $U_{\text{clan}} \in \mathbb{R}^{D \times k}$. La distance $d_G(U_A, U_B) = \|\vec{\theta}\|_2$ quantifie la divergence culturelle et module le coût et le bruit de communication inter-tribus.
- **Algèbre de Contrats Latents & Réciprocité de Nash** : Formulation d'engagements bilatéraux unitaires (`ROLE_GIVE`, `ROLE_DEMAND`, `ROLE_QUORUM`) et validation automatique des offres de troc par complémentarité vectorielle de Nash (seuil $\ge 0.60$).
- **Médiation Tri-Partite (`MultiTribalTranslator`) & Lingua Franca** : Mise en place d'un sous-espace pivot commun $U_{\text{pivot}}$ à la Place du Marché permettant la traduction et la synchronisation des clans sans dictionnaire bilatéral lourd.
- **Résolution Écologique in-world (Monde 2 Agricole)** : Le troc de denrées (Fruits vs Lances/Outils) compense l'asymétrie de spécialisation, éradiquant les disettes de fin de saison (+2.80 ticks de survie moyenne, 24.30 contrats scellés par ère).
- **Clôture & Journalisation** : Validé par le banc sociologique de 30 ères (Commandement 15 : delta énergie $+2.50$, delta survie $+2.80$, $100\%$ de survie) et certifié dans KuzuDB sous l'identifiant `art_013_langage_ultime_speciation_contrats` (Article 013).

## 🏛️ Langage Ultime Phase 5 : Gouvernance Juridique Décentralisée, Arbitrage de Confiance Latente et Métallurgie Distribuée du Monde 3 (Article 014)

Le passage de la tribu marchande à la confédération industrielle institutionnalisée (G5) :
- **Algèbre de Confiance Continue & Détection de Rupture ($\Delta_{\text{breach}}$)** : Mesure continue de l'écart de conformité entre engagement contractuel et exécution matérielle. Règle de réputation hystérétique immunisée contre l'amnésie (maintien du score sous le seuil d'éligibilité commercial $\text{sim} < 0.40$ sur au moins 10 cycles sans amnistie).
- **Arbitrage Distribué, Embargo Commercial & Répulsion Physique** : Refus unanime du handshake acoustique face aux défecteurs et force répulsive bannissant physiquement les criminels de la place du marché.
- **Contrats de Consortium Tripartites & Métallurgie du Monde 3** : Superposition orthogonale quad-partite à spectre plat ($D=64$) synchronisant Bois (Monde 1), Vivres (Monde 2) et Minerai (Monde 3) pour allumer le Haut-Fourneau et forger les premiers outils métalliques durables (`IronPickaxe`, `IronSpear`, `IronIngot`) avec rente calorique partagée ($+15.0\text{ E}$).
- **Persistance Lattice KuzuDB (`LULaw`, `LUSanction`, `LUConsortium`)** : Traçabilité des lois coutumières, arbitrages collectifs et traités industriels dans le graphe de connaissances.
- **Clôture & Journalisation** : Validé empiriquement sous la Loi du Sociologue sur 60 ères de simulation (Commandement 15 : delta survie $+1.47$ ticks, delta énergie loyaux $+18.60$ pts, extinction de la prédation) et consigné dans KuzuDB sous l'identifiant `art_014_langage_ultime_gouvernance_metallurgie` (Article 014).

## 📜 Langage Ultime Phase 6 : Émergence de l'Écriture Stigmargique, Arithmétique Vectorielle Discrète et Transmission Scientifique Intergénérationnelle (Article 015)

Le franchissement du seuil anthropologique de la mémoire stigmargique externe et de l'Académie scientifique (G6) :
- **Algèbre d'Arithmétique Vectorielle FPE (Phasor Binding)** : Intégration du Fractional Power Encoding assurant l'homomorphisme d'addition spectrale $Z_{\text{num}}(a) \circledast Z_{\text{num}}(b) = Z_{\text{num}}(a + b)$ et formulation d'équations stœchiométriques quantifiées ($3\text{ Bois} + 1\text{ Minerai} \to 1\text{ Outil}$).
- **Substrats d'Écriture In-World (`InscriptionStone`, `SlateTablet`)** : Gravure physique de stèles fixes pérennes résistantes à l'érosion géologique ($\sigma = 10^{-4}$, demi-vie $> 10\,000$ ticks) et tablettes d'ardoise transportables pour la comptabilité à partie double de marché (`CREDIT`, `DEBT`).
- **Académie Scientifique & Transmission Épigénétique de Prior** : Les agents nouveau-nés lisent la stèle centrale de métallurgie, absorbent le prior sémantique de recette et reçoivent un boost calorique immédiat (+5.0 pts d'énergie), éliminant l'amnésie post-mortem des civilisations orales.
- **Persistance KuzuDB (`LUScripture`, `LUMathematics`, `LUScience`)** : Indexation des corpus épigraphiques, transactions arithmétiques et théorèmes scientifiques.
- **Clôture & Journalisation** : Validé par le banc sociologique de 60 ères sous renouvellement démographique périodique (Commandement 15 : delta énergie $+7.74$ pts, rétention continue de la production métallurgique) et consigné dans KuzuDB sous l'identifiant `art_015_langage_ultime_ecriture_mathematiques_science` (Article 015).


## Comment lire les preuves

Chaque affirmation ci-dessus pointe vers son EDR (`docs/EDR/NNN_*.md`), qui contient le protocole, les
chiffres, l'honnêteté (limites) et les *variables d'expérience*. Le `roadmap.md` est la planification ;
**ce document est la mémoire de ce qu'on a appris.**
