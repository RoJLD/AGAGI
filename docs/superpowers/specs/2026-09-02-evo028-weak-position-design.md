# EVO-028 — design de la dépendance FAIBLE à la position (panel 3 juges + réfutateur, 2026-09-02)

Sortie du panel adversarial lancé après [[EDR-EVO-027]] (observation non élevée : 6 porteurs-non-lecteurs
LATE vs 2 EARLY). Verdict : **CONDITIONNEL — GO borné sur un between-seed grossi (EVO-027 verbatim,
n=86/bras), sous condition d'un smoke de coût.** Tous les chiffres sont des énumérations exactes
(convention petits-pmf du dépôt, validée : Fisher 22/24 vs 18/24 → p=0,2448, identique au record).

## 1. Ce qui meurt sur preuve (à graver quel que soit le smoke)

### 1.1 Preuve d'identité — AUCUN design within-seed n'identifie la position

Les 3 juges ont convergé indépendamment vers un crossover within-seed (2 fenêtres par lignée, sets de
paires contrebalancés). Le réfutateur les a tués tous les trois par la même identité : dans un
crossover à deux fenêtres, **l'ordre EST la position** — early précède late dans CHAQUE seed, l'ordre
n'est pas contrebalançable. L'estimand du McNemar est le **produit** r_position × r_carry-over, jamais
r_position seul. Équivalence observationnelle exacte : un carry-over pur de facteur k (zéro dépendance
de position) produit les mêmes marges (p_e, k·p_e) et la même distribution des discordants qu'une
dépendance r=k — aucune statistique sur les seeds ne les sépare.

* carry-over pur k=0,818, n=100 : P(faux « dépendance ÉTABLIE ») = **0,858** ;
* carry-over pur k=0,700, n=48 : **0,881** — pendant que le contrôle carry-over du design 3
  (bande [0,6 ; 1,4]) PASSE à 0,874 : un contrôle qui ne peut pas échouer à la taille d'effet testée.
* La fusion ne sauve rien : le seul contraste identifiant (bras LATE-only between) reste sous 0,70 de
  puissance même à m=96 — le between pur domine strictement.

Failles secondaires générales : ancre externe incommensurable (EVO-027 n'a publié AUCUN taux per-paire) ;
mesure héritée du champion best-EVER ([evo027_run.py:117-120](tools/evo_runs/evo027_run.py#L117-L120)) qui
dégonfle mécaniquement la conversion late (mime la position) ; puissances ancrées sur un pe_set=0,917
jamais mesuré.

### 1.2 Preuve de coût — la bande r ∈ (0,818 ; 1,0) est INDÉCIDABLE au coût acceptable

Fisher exact between (p_E=22/24), n minimal pour 80 %, coût en ères-seeds (EVO-027 = 1 920) :

| r vrai | n80/bras | ères-seeds | × EVO-027 |
|---|---|---|---|
| 0,50 | 18 | 1 440 | 0,75× |
| 0,70 | 40 | 3 200 | 1,67× |
| **0,818 (point observé)** | **86** | **6 880** | **3,58×** |
| 0,85 | 116 | 9 280 | 4,83× |
| 0,90 | 226 | 18 080 | 9,42× |
| 0,95 | ~780 | ~62 000 | ~32× |

Divergence en (1−r)⁻² (DV bimodale → 1 bit/seed max). Les deux leviers de compression sont morts :
l'amplification (fenêtre 41-55, run 70) casse sa propre clause santé pré-déclarée (EVO-026) ; la
désaturation per-hit a son optimum à h=5 (2,29×) sans ouvrir la bande haute. **(0,818 ; 1,0) est fermée
d'avance et définitivement** — le pendant du `1−(1−p)^N` de D2-bis.

## 2. Design retenu : EVO-028 = EVO-027 grossi, verbatim

* **2 bras × 86 seeds**, harnais [evo027_run.py](tools/evo_runs/evo027_run.py) avec pour seule
  modification scientifique `N_SEEDS=86`. EARLY : biais 1-15, run 30 ; LATE : propre 1-20, biais 21-35,
  run 50 ; horizon post-fenêtre apparié. Config, DV, contrôles, convention Fisher inchangés — tout est
  déjà calibré. DV |logit| réparée (`tools/evo_mech_dv.py`) et persistance des champions embarquées.
* **Failles non fatales intégrées en contrôles** : (a) lecture SECONDAIRE sans poids = saillance du
  top-1 de l'élite à la DERNIÈRE ère, à côté du best-ever (sur EARLY les deux doivent coïncider :
  son no-op) ; (b) taux rapportés PAR paire cible (ne pas recréer la dette d'ancre d'EVO-027).
* **Données neuves seulement** (E9) : aucune fusion avec les 24+24 d'EVO-027 (qui ont engendré
  l'hypothèse). Attendus sous le point observé : ~79/86 EARLY, ~64/86 LATE.
* Puissance à n=86 : 0,993 (r=0,70) · 0,963 (0,75) · **0,804 (0,818)** · 0,655 (0,85) ·
  faux-positif 0,027 (H0). Limite posée AVANT : r ≥ 0,85 indétectable — bande déjà fermée sur coût.

## 3. Règle de lecture (à sceller dans `EVO-028.json` après smoke, avant run)

Contrôles (échec = AUCUN verdict) : hits >0 des deux côtés et ratio ∈ [0,7;1,4] · portage par bras ET
par paire · N médian 172±2 · santé LATE ≥ 0,70×EARLY. Contrôle positif interne : EARLY ≥ 29/86.
Lecture continue (ordre imposé) : p<0,05 ∧ EARLY>LATE ∧ santé OK → **DÉPENDANCE FAIBLE ÉTABLIE**
(ratio + IC exact ; mécanisme B-M1/M2 lu dans les DV mécanistes, sans poids) · p<0,05 ∧ santé<0,70 →
attribué à la dégradation · p<0,05 ∧ LATE>EARLY → inattendu, rapporté · **p ≥ 0,05 → r ≤ 0,818 RÉFUTÉ
(β=0,196 ; r≤0,75 à β=0,037) et, combiné à la clôture §1.2, la question est FERMÉE définitivement.**
Toute autre observation : non élevée (E9).

## 4. Smoke de coût (seuils SCELLÉS avant : `docs/preregistrations/EVO-028-SMOKE.json`)

1 seed COMPLET par bras (30+50 ères, sondes + persistance incluses — pas un préfixe), chronométré par
ère, sous bail. Plafond = 80 % du bail 4 h = 11 520 s de sim totale. `t_pair` = t_EARLY + t_LATE :
≤134 s → GO n=86 · ]134;155] s → repli n=74 (règle réécrite sur 0,800/0,729 AVANT run) · >155 s →
dernier barreau h=5 (n=66, 2,29×) SEULEMENT si l'opérateur à cap est calibré dans la même passe,
sinon NO-GO coût gravé avec le tableau §1.2 comme preuve.

## 5. Consignations liées

* REGISTRE_ERREURS : classe « crossover à ordre fixe → estimand = produit position × carry-over »
  (contre-exemple gelé = les 3 designs du panel). Candidat de promotion : `preregister` exige un champ
  `contraste_identifiant` pour tout design within à fenêtres ordonnées.
* Backlog : rétro-extraire les taux per-paire d'EVO-027 (possible seulement via replay — champions
  non persistés à l'époque ; la persistance est câblée depuis).
