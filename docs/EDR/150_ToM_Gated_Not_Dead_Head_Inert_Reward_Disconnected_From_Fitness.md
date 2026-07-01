# EDR 150 — Theory of Mind : GATEE, pas morte ; tete inerte + recompense DECONNECTEE de la fitness ; decode latent FAIBLE (contexte partage ?)

> **Date** : 2026-07-01. **Verdict pre-enregistre** : `TOM_EMERGES` si `acc_head_tom >= acc_shuffle_tom + 0.10` ET `acc_head_tom >= acc_head_ctrl + 0.10` ; sinon `TOM_INERT`.
> **Resultat** : **TOM_INERT** (TOM head 0.072 < CONTROL 0.110 < shuffle_tom 0.122 -> aucune emergence). Lecture DECODE : tete inerte (ctrl head 0.110 ~ shuffle 0.113) MAIS sonde latente 0.387 vs shuffle 0.264 = **+0.12 robuste 3/3 seeds**.
> **Outil** : `tools/tom_probe.py` (`main_tom_probe`). **Seed** : 1280, R=3, **MEC_PRESERVE_DIMS=1** (smoke 99280). **Commits** : 26f9db6 (T1) / 472a8b9 (T2) / c4225f0 (fix).
> **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-01-tom-representational-emergence*`. Chantier P4-ToM #1 (representationnel). Suite prevue : #2 comportemental (coordination/recrutement).

## 1. Contexte & correction

**La memoire disait « ToM MORTE (1 commentaire) » — c'est FAUX.** Il existe un circuit ToM complet, gate OFF :
- Sortie connectome `predictor_head` = 8 dims (`mamba_agent.py:71,699,731`), calculee a chaque forward.
- Recompense ToM (`world_1_stoneage.py:817-826`, `_resolve_social`) : deux agents **au meme cellule**
  (`:789`), si `argmax(predictor_head_A) == last_action_B` -> A gagne **+2 energie**. Gate derriere
  `active_exp_variable in ["INTRINSIC","TOM"]` ; defaut `"LANGUAGE"` -> jamais actif.
- `active_exp_variable="TOM"` ne declenche QUE ce bloc (verifie : RAG `:524`, LANGUAGE `:797/1075/1369`,
  INTRINSIC-seul `:1017` non touches). Isolation 1-variable propre.

**Correction (revue finale)** : l'espace d'action reel est **8** (`last_action = argmax(logits[:8])`,
`:1060,1071`), IDENTIQUE a `predictor_head` -> tache BIEN POSEE, accuracy non plafonnee (la spec disait a
tort `{0..28}`).

## 2. Question & methode

**(a) DECODE** : la representation encode-t-elle deja l'action des congeneres (sans recompense) ?
**(b) EMERGENCE** (verdict primaire) : activer la recompense ToM fait-il emerger une prediction reelle ?

2 bras evolutifs APPARIES par seed (R=3) : **CONTROL** (`active_exp_variable="NONE"`) vs **TOM** (`="TOM"`).
Champions evolues (stoneage sweet-spot, `MEC_PRESERVE_DIMS=1` -> substrat NON aplati), puis mesures sur
**cohorte FIXE** (`benchmark_mode`, lecon 114b ; memory neutralisee, lecon P0). **Mesure NEUTRE pour les 2
bras** (`_make_cfg_tom("NONE")` : la recompense ToM n'agit que pendant l'EVOLUTION, pas la mesure). A chaque
tick, pour chaque paire **same-cell** (a,b) : record `{pred=argmax(predictor_head_A), act=last_action_B,
latent_A(68)}`. Metriques : `_head_accuracy` (pred==act), `_shuffle_accuracy` (base-rate, acts permutes),
`_latent_probe` (regression lineaire 68-dim -> action, held-out, split stratifie).

## 3. Resultat (run pre-enregistre, seed 1280, R=3, MEC_PRESERVE_DIMS=1, 2 passes byte-identiques)

```
  seed | CTRL head shuf probe(t/s) nC | TOM  head shuf nT
  1280 |      0.160 0.117 0.548/0.387    94 |      0.128 0.151    86
  1281 |      0.107 0.119 0.296/0.185    84 |      0.008 0.008   252
  1282 |      0.064 0.102 0.317/0.220   266 |      0.081 0.206   136
  MOYEN|      0.110 0.113 0.387/0.264 |      0.072 0.122
  records/seed (moyenne) : CTRL 148 | TOM 158
  VERDICT : TOM_INERT
```

`acc_head_tom 0.072 < acc_head_ctrl 0.110` ET `< acc_shuffle_tom 0.122` -> **TOM_INERT**. Non-vacuite OK
(148/158 records/seed >> seuil 20). Determinisme verifie (pass 1 == pass 2, byte-identique).

## 4. Lecture (trois temps)

1. **La tete ToM designee est INERTE.** CONTROL head 0.110 ~ shuffle 0.113 : `predictor_head` ne predit pas
   l'action du congenere au-dessus du base-rate, par defaut.
2. **La recompense ToM ne fait RIEN emerger** (TOM head 0.072, sous CONTROL et sous son propre shuffle).
   **MAIS reserve MAJEURE** (voir §5) : la recompense est +2 **energie**, et l'energie **n'est PAS dans
   `calculate_life_score`** -> l'incitation n'atteint la selection qu'indirectement (survie -> `age*0.1`).
   Le gradient ToM est ~2 ordres de grandeur sous forage/craft. -> **TOM_INERT est CONFONDU** entre
   « substrat incapable » et « pression de selection trop faible / mal branchee ». C'est en soi un finding
   concret : **le circuit ToM est cable et recompense, mais l'incitation est deconnectee de la fitness** —
   meme classe que le poids `spears` inerte (EDR 125) ou l'autel mort (096), un cran plus profond.
3. **Info latente FAIBLE sur l'autre.** La sonde latente (68-dim : predictor_head+goal+memory+ntm) decode
   l'action du congenere a **0.387 vs shuffle 0.264 = +0.12**, ROBUSTE sur 3/3 seeds (+0.16/+0.11/+0.10).
   Donc une information predictive sur B existe faiblement dans la representation de A — mais **pas dans la
   tete designee**, et **pas sous selection**. (Ecart tete/latent = le substrat porte un signal qu'il
   n'organise ni n'exploite en une tete ToM utilisable.)

## 5. Caveats (perimetre du verdict)

- **Confond de pression de selection (reserve #1, la plus importante).** Energie absente de `life_score`
  (`persistence.py:44-47`) -> un `TOM_INERT` NE PROUVE PAS l'incapacite du substrat. Pour un test causal
  propre, il faudrait un bras ou le match ToM entre DIRECTEMENT dans la fitness (hors perimetre tooling-only :
  toucherait `src/`). A declarer comme borne de l'inference, exactement comme les caveats pression d'EDR
  111/125.
- **Decode latent : contexte partage vs vraie modelisation (reserve #2).** Le +0.12 pourrait venir de ce que
  deux agents au meme cellule partagent le contexte local (memes ressources/menaces) -> leurs actions
  correlent -> le latent de A predit l'action de B SANS modeliser B. Le shuffle (qui casse l'appariement
  same-cell) confirme que le signal est SPECIFIQUE aux paires same-cell, mais ne distingue pas
  « A encode B » de « A et B partagent le contexte ». Le **chantier #2 (comportemental)** trancherait
  (la coop est-elle CONDITIONNEE a la presence/l'etat des autres = recrutement).
- **Substrat reel** : `MEC_PRESERVE_DIMS=1` -> l'archi evoluee du genome est preservee (cachés reels, cf.
  [[from-genome-flattens-architecture]]) ; sans ce flag le substrat serait aplati et le TOM_INERT trivial.
- **Symetrie de mesure** : les 2 bras mesures avec `_make_cfg_tom("NONE")` (recompense OFF a la mesure),
  meme cohorte fixe, meme pairing same-cell (replique de `:789`, direction A->B = `pred_a==last_action_b`).
- **Base-rate hacking bloque** : le shuffle partage la distribution de `pred` -> le garde `+0.10` neutralise
  « predire l'action dominante » (TOM head 0.072 est meme SOUS son shuffle 0.122).

## 6. Suite & provenance

- **Suite** : (1) **chantier #2 comportemental** (coordination/recrutement) pour desambiguiser le decode
  latent (contexte partage vs modelisation) ; (2) le finding actionnable = **rebrancher l'incitation ToM sur
  la fitness** (match ToM -> `life_score`, pas juste energie) pour un test causal du substrat — releve de la
  migration moteur (torch, session //), pas du tooling. Le decode-latent +0.12 dit qu'il y a une matiere
  premiere faible a exploiter si l'incitation etait branchee.
- **Provenance** : `Harness(name="tom_probe")` -> `results/tom_probe_1280.json` (gitignore) ; seed 1280,
  smoke 99280 distinct ; MEC_PRESERVE_DIMS=1 ; 2 passes byte-identiques ; AUCUN test relance apres le run
  (EDR 107). Tooling-only : `git diff src/` VIDE (zero collision session //).
- **Revue** : subagent-driven (T1 + T2 : SPEC conforme + qualite Approved ; deviation `_latent_probe` split
  stratifie jugee amelioration). Revue finale **opus** PRET A INTEGRER : a surface les 2 reserves majeures
  (act espace 8 ; energie absente de la fitness), integrees ici. 3 fixes avant run (RNG local seede, `n`
  affiche, Harness) sans toucher le verdict gele. 10/10 tests.
- **Numerotation** : RENUMEROTE 132 -> 141 -> 150 (2026-07-01). 132->141 resolvait le double-132 (mon `132_ToM`
  vs `132_Compositional_Warmstart` //), mais le fil torch // a ensuite pris 141 (`141_Migration_Parity`) ->
  nouveau double-141. Parque donc la paire ToM dans un BLOC DISTANT 150/151 (buffer au-dessus du fil torch a
  143), cedant la plage contigue 130s-140s aux fils //. CONVENTION : instruments per-type/ToM en 150+, fils //
  (compositional/torch/famine) en 120-149. Cf. [[parallel-sessions-shared-tree]]. Chantier `tools/tom_probe.py`.
