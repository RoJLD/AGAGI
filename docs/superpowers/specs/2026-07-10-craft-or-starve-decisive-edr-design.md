# EDR 200 — CRAFT-OR-STARVE (COS) : test décisif pré-enregistré de la thèse fondatrice (attribution 3×2, demande × mécanisme)

> **Date** : 2026-07-10. **Fil** : G1/G2 composition + substrat/crédit — **bloc NEUF 200+** (« tests décisifs de
> thèse fondatrice », distinct de tous les fils // : compositional/torch/famine 120-149/158-167, per-type/disjoint
> 150+/190+, G4 193/194). **Type** : écologie de survie standalone, EDR à verdict gelé.
> **Collision-safe** : nouveau fichier `tools/craft_or_starve_edr.py`, PyTorch/numpy CPU auto-contenu, **ZÉRO modif
> `src/`, N'IMPORTE PAS `world_1_stoneage.py` ni `backend_torch.py`** (territoire d'un fil // actif) — réimplémente
> des substrats minimaux. Issu d'un brainstorm stratégique (cartographie exhaustive + critique adverse) puis d'un
> design adversarial (4 designs → 4 sceptiques FATAL → synthèse).

## 0. La question décisive (et le reframe honnête)

Un brainstorm stratégique + critique adverse a établi que la thèse fondatrice — **« le verrou = SUBSTRAT, migrer
vers torch »** — n'a **jamais eu de condition de mort in-world** et est peut-être **non-falsifiable** (obtenue par
résidu ; chaque neutre in-world sauvé par « pas encore intégré »). L'hypothèse rivale : le verrou est le
**CRÉDIT/OBJECTIF** (READOUT_GAP : l'info est décodable dans H à ~0.81 mais l'action ne l'émet qu'à 2-3%). La leçon
du projet — **« IMPOSER via l'objectif bat SÉLECTIONNER »** — n'a jamais été appliquée à l'objectif lui-même.

**Reframe assumé** : la parité moteur torch≈legacy est établie (EDR-140/141) — ce banc ne teste donc PAS « torch le
moteur » mais **le paquet migration crédit + gate + anti-saturation** (la recette 136/158/159), *vivant* dans une
écologie où composer est l'unique voie de survie. La **condition de mort** tue le *contenu opérationnel* de la thèse
(« la migration débloque la composition »), pas un moteur-substrat mythique.

**Question falsifiable** : dans une écologie où le non-compositionnel MEURT de faim, le paquet migration complet
débloque-t-il la composition means→ends (→ licencie l'intégration in-world du fil //), ou reste-t-il inerte
(→ **falsifie** la thèse), ou l'effet est-il attribuable au seul **horizon de crédit** (→ confirme la rivale
crédit/objectif, licencie la migration *en crédit*, pas *en moteur*) ?

## 1. L'écologie — CRAFT-OR-STARVE

Agents en **batch, mondes privés disjoints** (aucun canal inter-agent → division du travail structurellement
impossible, cf. §3). État par agent = `(E: énergie float, inv ∈ {0,1}, H: état récurrent)`. **L'épisode = la vie**,
bornée à `T` ticks ; **poids persistants entre épisodes** (apprentissage en ligne) ; `E, inv` reset par épisode.
Un « pas » = **2 sous-pas** `S1` (craft) puis `S2` (consume), **drain de faim `−h` à CHAQUE sous-pas**. **Mort =
`E ≤ 0`, ABSORBANTE** (agent gelé, `alive=0` ensuite).

**Bras INESCAPABLE (demande = présente) — pseudo-code du pas :**
```
# S1 — phase craft
mat = Bernoulli(p_mat)                         # EXOGÈNE, stochastique  -> une horloge ne peut pas le prédire
obs1 = [contexte_bruit, mat, phase=0, leurres] # mat visible ICI SEULEMENT
a1 ~ policy(obs1, H); H = core(obs1, H)
if a1 == CRAFT:
    if mat: inv = 1; E -= c_craft            # craft-avec-matière : petit coût
    else:   E -= c_prime                     # craft-SANS-matière : PÉNALISÉ
E -= h
# S2 — phase consume
obs2 = [contexte_bruit, phase=1, leurres]      # inv PAS ré-encodé -> doit être PORTÉ dans H
a2 ~ policy(obs2, H); H = core(obs2, H)
if a2 == CONSUME:
    if inv == 1: E += R; inv = 0             # consume-avec-inventaire : nourriture
    else:        E -= c                       # consume-SUR-VIDE : PÉNALISÉ
E -= h
if E <= 0: mort_absorbante()
```

**Paramètres gelés AVANT tout substrat (calibrés au pilote, Phase A) — cibles indicatives** : `p_mat=0.5, R=8, h=1,
c=6, c'=3, c_craft=0.5, E0 ≈ quelques ticks d'exploration gratuite, T=800, |A|≈8 (avec leurres)`. Comptabilité
énergétique visée (à VÉRIFIER par tests TDD au pilote) : **composeur conditionnel** (craft ssi `mat`, consume ssi
`inv`) ≈ **+1.75/cycle → VIT** ; **métronome** (craft+consume toujours) ≈ **−2.75/cycle → MEURT** ; **spammer
marginal** net-négatif → **MEURT**. `|A|` inclut des **leurres** pour rester dans le régime READOUT_GAP (la bonne
action rarement émise par défaut).

## 2. Inescapabilité (mécanisme réel, pas un bouton)

La composition est inescapable par **conjonction de 3 faits mécaniques** (répond au reproche n°1 du critique — « pas
un scalaire de demande calibré ») :
1. **Aucune énergie hors `CONSUME(inv=1)`** + faim `−h`/sous-pas → toute politique à `#consume-réussis` insuffisant
   franchit 0 en `O(E0/h)`.
2. **Matière EXOGÈNE-stochastique** (`p_mat=0.5`) : `inv=1 ⟺ (CRAFT ∧ mat)` → `inv` n'est PAS une fonction
   déterministe de l'horloge d'action → un oscillateur open-loop période-2 consomme sur vide la moitié du temps.
3. **Coût de mis-émission** (`consume-sur-vide −c`, `craft-sans-matière −c'`) → `P(CONSUME|inv=0)` et
   `P(CRAFT|¬mat)` deviennent **fitness-pertinents** ; métronome et spammer ont **espérance négative et meurent**
   (répare la faille marginal-raising que 3 des 4 sceptiques ont exploitée).

Seule trajectoire à bilan positif = **CONSUME émis SSI H porte « j'ai crafté ET la matière était là »** = binding
conditionnel sur état-latent-en-H, **répété** (l'outil est consommé → il faut re-crafter → rétention, écho EDR-162).

**Bras ABSENTE (contrôle)** : MÊME monde, MÊME `h`, MÊME `T`, **un seul bit de règle basculé** — le canal de
nourriture devient un **FORAGE différé inconditionnel** (`S1` programme `pending=+f` délivré à `S2`
INCONDITIONNELLEMENT, **même latence de 1 sous-pas** que craft→consume). Craft/consume inertes. Le **délai est
apparié**, seule la structure CONDITIONNELLE est retirée (répare le confond horizon-de-crédit du sceptique
falsifiabilité).

## 3. Le facteur « substrat » = échelle d'attribution à 3 crans (le coup d'honnêteté)

Le critique a montré que « substrat » et « crédit » n'étaient pas séparables. On remplace le facteur binaire par une
**échelle à 3 crans**, MÊME cœur récurrent partout (`H_t = tanh(W_hh·H_{t-1} + W_ih·obs)`, lecture linéaire → logits,
même `N, I, activation tanh` — EDR-139 : le « torch pire » était un mismatch swish/tanh, pas le gradient ; même
tête, même lr Adam, même `#épisodes`) :

- **L0 (legacy)** — pur numpy, **aucun gate, aucune anti-saturation** ; crédit = son véhicule natif = **REINFORCE
  TD(0) 1-pas** sur l'avantage du delta-énergie par sous-pas (le bras « objectif TD, substrat plat » d'EDR-148/158).
  Doté d'un **readout muet** de mêmes `#params` que le gate torch (égalise exactement le compte de paramètres).
- **L1 (cran d'attribution, OBLIGATOIRE dans le verdict primaire)** — même cœur + **crédit ÉPISODIQUE** (REINFORCE
  sur le retour de survie de la fenêtre `K=20`, `H.detach()` entre pas, **PAS de BPTT** — EDR-146/147 : BPTT détruit
  le conditionnement), **SANS gate** → isole l'**horizon de crédit** (épisodique vs TD), **désengluant SUBSTRAT de
  CRÉDIT**.
- **L2 (paquet migration complet)** — L1 + (a) **GATE additif self-scope depuis H** sur le **logit CONSUME
  uniquement**, biais init NÉGATIF (EDR-158/159/160, `gate_last_only=False`) ; (b) **ANTI-SATURATION** homéostatique
  (EDR-136, `pen ∈ {3,6,9}` balayée, figée avant les seeds confirmatoires).

**Écarts attribués** : `L1−L0 = {horizon de crédit}` ; `L2−L1 = {gate + anti-sat}` ; `L2−L0 = total`. C'est
exactement la recette prouvée en isolation (158/159/136), ici **vivante dans une écologie à mort**.

**Défenses anti-confond (chaque choix = défense nommée) :**
- **CAPACITÉ** (EDR-110 « 16× cachés inerte ») : cœur/`N`/`I`/`|A|`/activation/lr/`#épisodes` IDENTIQUES sur
  L0/L1/L2 ; readout muet apparie le compte de params (neutralise l'absorption du gate additif dans la tête).
- **SIGNAL** : seeds appariés = MÊMES plannings de `mat`, MÊME obs, MÊME magnitude de récompense ; aucun ne reçoit
  `inv`/`did_x` en dur (porté dans H).
- **POPULATION** (coop = propriété population EDR-097/102) : agents SOLO, `E`/`inv` PRIVÉS non transférables, aucun
  troc/vol/pool, cohorte FIXE, **sélection OFF**, zéro reproduction → division du travail impossible, tout avantage
  est intra-agent-cognitif.
- **MOTEUR torch-vs-numpy** : neutralisé par **ancre de parité** `|AUC(cœur-numpy-TD, absent) − AUC(cœur-torch-TD,
  absent)| ≤ band` ; sinon **VOID** (l'impl torch est juste meilleure).
- **ENCODAGE vs ÉMISSION** (READOUT_GAP) : `decode_AUC(inv|H)` mesuré en L0 ET L2 ; `<0.70` des deux = échec
  mémoire/capacité (bump `N`, re-vérifier AVANT tout claim crédit) ; `≥0.70` des deux mais seul L2 ÉMET =
  crédit-conditionnel prouvé.

## 4. Métriques (DEUX requises)

- **(A) SURVIE (écologique)** = `Survival AUC` = moyenne sur `T` de la fraction d'agents vivants, **dernier quart** de
  l'entraînement, **MÉDIANE PAR AGENT** (pas le pool — qu'une minorité d'immortels ne masque pas la mortalité de
  masse). Secondaire : survie tardive (dernière fenêtre, après épuisement de `E0`).
- **(B) COMPOSITION DIRECTE**, au niveau **TICK** sur les transitions `S2` RÉELLES (dernier quart, par agent puis
  médiane) : `binding_gap = P(CONSUME|inv=1) − P(CONSUME|inv=0)` sur l'état-latent EXOGÈNE-stochastique VRAI (pas un
  agrégat de fenêtre → défait le confond activité-fenêtre). On rapporte **SÉPARÉMENT** `P(C|inv=1)` et `P(C|inv=0)`
  (le PATRON, pas juste la différence) ; `comp_rate` ; `craft_rate` (garde : si `craft→0`, gap indéfini → traité
  comme non-composition).
- **Instruments anti-confond** : `decode_AUC(inv|H)` au `S2` ; **null-métronome** (gap d'une politique open-loop
  période-2 apparié) ; fraction de morts-par-famine.

**Pourquoi la survie SEULE ment** : (1) atteignable par chaînes coïncidentes/marginal-raising sans conditionner
(EDR-126 : le JOINT confond, le `P(Y|X)` DIRECT est l'instrument) ; (2) plancher/plafond insensible ; (3) READOUT_GAP
(inv décodable ~0.81, émis 2-3%). **Pré-enregistré** : une victoire de survie SANS le patron des conditionnels =
**drapeau marginal-raising, NON comptée comme support**.

## 5. Gates de viabilité (pré-run, gelés sur set pilote DISJOINT ; VOID sinon)

Prouvent que le MONDE exige le conditionnement AVANT tout substrat. Tous doivent passer simultanément :
- **G1** oracle-composeur `AUC ≥ 0.90` (inesc) — le monde est survivable par conditionnement.
- **G2** random `AUC ≤ 0.20` (inesc) — pas survivable au hasard.
- **G3** oracle-forage `≥ 0.90` ∧ random `≤ 0.20` (absent) — le contrôle est bien réglé.
- **G4** HEADROOM `L0-absent ∈ [0.4, 0.85]` — contrôle ni plancher ni plafond.
- **G5** **MÉTRONOME `≤ 0.40`** (inesc) — l'horloge open-loop NE survit PAS (répare l'échappatoire clock).
- **G6** `decode_AUC(inv|H) ≥ 0.70` en L0 ET L2.
- **G7** ancre de parité moteur `|numpy − torch, TD absent| ≤ band`.
- **G8** **2 passes byte-identiques** (hash des MÉTRIQUES, pas des poids).

## 6. Verdict gelé — `compute_verdict(rows)` (fonction PURE, testable sans run)

`n=16` seeds APPARIÉS, **6 cellules/seed** = `{L0,L1,L2} × {inesc, absent}`. Deltas appariés par seed `s` :
- `Inter_surv(s) = [AUC(L2,inesc) − AUC(L0,inesc)] − [AUC(L2,absent) − AUC(L0,absent)]`
- `Credit_frac(s) = [AUC(L1,inesc) − AUC(L0,inesc)] / [AUC(L2,inesc) − AUC(L0,inesc)]` (gardé si dénom > band)
- `Gate_surv(s) = AUC(L2,inesc) − AUC(L1,inesc)`

**Seuils gelés** : `band_auc=0.05`, `gap_band=0.10`, `patron_gap = (P(C|inv=1) ≥ 0.6 ∧ P(C|inv=0) ≤ 0.25)`,
`decode_min=0.70`, `clock_margin=0.15`, `majorité=9/16`, `alpha=0.05` (signe binomial), `credit_dominant=0.70`.

**Échelle de verdict (dans l'ordre) :**
- **[1] MORT — THÈSE FONDATRICE FALSIFIÉE** : sous inesc le paquet L2 est INERTE vs L0 —
  `median[AUC(L2,inesc)−AUC(L0,inesc)] ≤ band_auc` ET `frac{seeds : survie-adv>band ∧ gap satisfait patron_gap} ≤`
  celle de L0 (≈0), ET **tient sur `pen ∈ {3,6,9}`** (un pen mal calibré NE PEUT PAS déclencher la mort).
  **Bimodalité-proof** (ne tire que si MÊME la sous-population bindeuse est absente, EDR-131). **Rescue « pas encore
  intégré » INTERDIT et pré-enregistré interdit.** → le paquet migration, entièrement présent et vivant, dans une
  écologie qui impose la composition par la faim, sans béquille de population, monde-équitable gaté, ne débloque PAS
  la composition. **Fondatrice « verrou=SUBSTRAT » FALSIFIÉE**, rivale crédit/objectif tient.
- **[2] CRÉDIT-ATTRIBUÉ — RIVALE READOUT_GAP CONFIRMÉE (moteur NON licencié)** : `L2>L0` inesc (median>band,
  `sign_p<0.05`, `≥9/16`) MAIS `median Credit_frac ≥ 0.70` ET `median Gate_surv ≤ band` → l'effet est l'HORIZON DE
  CRÉDIT (épisodique vs TD), pas le gate ni le moteur → **licencie la migration CRÉDIT/OBJECTIF** (le vrai levier
  EDR-158), disconfirme « moteur=substrat ».
- **[3] COMPOSITION-DÉBLOQUÉE — paquet licencié in-world** : `median Inter_surv > band` ET `sign_p<0.05` ET
  `≥9/16 Inter_surv>0` ET gap L2-inesc satisfait `patron_gap` ET `(gap L2-inesc − null_métronome) ≥ clock_margin` ET
  `(gap L2-inesc − gap L0-inesc) ≥ gap_band` ET `(median Gate_surv > band OU Credit_frac < 0.70)` →
  interaction demande×mécanisme, conditionné-sur-état (bat le null horloge), au-delà du simple horizon de crédit.
  **Licencie l'intégration crans 2-4** du fil //, BORNÉE à la faculté crédit/composition (PAS navigation/organes).
- **[4] GÉNÉRIQUE/CONFONDU** : `L2>L0` inesc mais `Inter_surv ≤ band` (gagne autant en absent) OU survie sans
  `patron_gap` → meilleur-apprenant générique, non licencié.
- **[5] PARTIEL/PATH-DÉPENDANT** : une sous-population binde (fraction > L0) sans atteindre majorité/significativité →
  bimodalité EDR-131 ; débloque mais non fiable → pas de licence pleine, re-run à `n` plus grand.
- **[6] NON-RÉSOLU** sinon. La condition qui FALSIFIE = ligne **[1]**, gelée mot-pour-mot avant tout run. Ancre
  parité échouée (G7) → VOID, pas verdict.

## 7. Confonds neutralisés (récap)

Échappatoire-horloge (matière stochastique + G5 + null-métronome + `clock_margin`) · substrat-vs-crédit (cran L1
obligatoire + verdict [2]) · horizon-de-crédit déguisé (forage différé apparié) · marginal-raising (coût de
mis-émission + patron des 2 conditionnels) · population (solo, privé, sélection OFF) · capacité (cœur identique +
readout muet) · moteur torch-vs-numpy (ancre G7) · encodage-vs-émission (`decode_AUC` G6) · métrique activité-fenêtre
(gap au niveau tick) · bimodalité (mort bimodalité-proof + foyer [5]) · plancher/plafond (headroom G4) · pen
mal-calibré (robustesse `pen ∈ {3,6,9}`) · plancher d'exploration (`E0` + témoin random + température).

## 8. Caveats résiduels (honnêtes)

- **STANDALONE ≠ biosphère** : abstrait la navigation (mur Lewis EDR-114 exclu exprès), pas de 3D, unités abstraites
  ≠ organes LTC réels, tête d'action unique vs move/grab/rub séparés. Un POSITIF licencie la faculté
  **crédit/composition**, PAS navigation/spatial/organes. Pré-enregistré : la biosphère n'ajoute que du couplage
  inter-agents (béquille population qui ne peut que FACILITER) → l'échec standalone borne par le haut la perf
  biosphère-honnête.
- **Reframe assumé** : ce banc teste le **paquet crédit/gate/anti-sat**, pas « torch le moteur » (déjà ≈ legacy,
  140/141, gaté G7). La mort [1] tue le contenu OPÉRATIONNEL de la thèse post-140/141.
- **Sélection OFF** : verdict borné au crédit INTRA-VIE, pas évolutionnaire — nommé comme portée.
- **Gate et anti-sat non dissociés** dans ce banc (bundlés dans L2) ; le sont en isolation (136/158).
- **Le coût `c` CRÉE la pertinence-fitness du gap** — un sceptique dira qu'on a ingénieré la pression. Défense : sans
  lui, AUCUNE composition inescapable (3 sceptiques l'ont prouvé) ; `c` est le mécanisme minimal, calibré sur
  oracle/métronome/random AVANT les substrats, avec robustesse-`c` rapportée.
- **Issue la plus probable a priori = [2] CRÉDIT-ATTRIBUÉ** (cohérent 158) : licencie la migration en CRÉDIT, plus
  modeste que « moteur=substrat » — honnête mais potentiellement décevant pour la thèse forte. C'est la preuve que le
  test *discrimine*.
- **Puissance à `n=16`** possiblement insuffisante pour l'interaction ET la détection de sous-population → prévoir
  atterrissage [5]/[6] et re-run plus grand plutôt que sur-interpréter.

## 9. Staging / ordre de construction (dé-risquage)

Le risque n°1 (les gates de viabilité G1-G5 peuvent ne pas se calibrer simultanément) impose un build **STAGÉ**, avec
**gate dur** :

- **PHASE A — PILOTE (à livrer et valider EN PREMIER)** : moteur de monde (T1) + politiques de référence
  (oracle-composeur, oracle-forage, random, métronome) + harnais de calibration des **gates de viabilité** (T2).
  **GATE DUR** : si `(c,c',h,R,p_mat,E0,N,T)` ne peut satisfaire G1-G5 simultanément (composeur vit, métronome/random
  meurent, headroom OK), **STOP** — le design est révisé avant Phase B. Sinon, params GELÉS.
- **PHASE B — CONTINGENTE au pilote** : cœurs L0/L1/L2 + règles de crédit (T3-T4), métriques (T5),
  `compute_verdict` pur (T6), runner 3×2×16 + robustesse pen/`c` (T7), doc de pré-enregistrement gelé (T8, committé
  AVANT les 16 seeds confirmatoires).

## 10. Provenance / non-périmètre / numérotation

- **Additif strict** : `tools/craft_or_starve_edr.py` + tests + spec/plan/EDR. `src/` intact, aucun import de `src/`.
  Ne touche NI `world_1_stoneage.py`/`backend_torch.py` (fil // actif) NI famine/Lewis.
- **Design adversarial** : cartographie exhaustive (7 lecteurs) + critique adverse → 4 designs indépendants → 4
  sceptiques (tous FATAL, exploitant marginal-raising/horloge/substrat-vs-crédit) → synthèse réparant chaque faille.
- **Numérotation** : EDR **200** — **bloc NEUF 200+** (« tests décisifs de thèse fondatrice »). À consigner dans la
  mémoire `parallel-sessions-shared-tree` (nouvelle convention de bloc). Numéro provisoire, réajustable au merge si
  collision.
