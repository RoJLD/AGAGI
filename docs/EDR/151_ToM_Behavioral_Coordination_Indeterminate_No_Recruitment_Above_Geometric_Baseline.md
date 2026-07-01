# EDR 151 — ToM comportementale : verdict formel INDETERMINE, mais AUCUN recrutement au-dessus du plancher géométrique (→ directionnellement INDEPENDENT ; le décode latent d'EDR 150 = contexte partagé)

> **Date** : 2026-07-01. **Verdict pre-enregistre** : `COORDINATED` si `delta = P(attack|>=1 autre) - P(attack|seul) >= 0.10` ; `INDETERMINE` si `n_with<20` OU `n_alone<20` ; sinon `INDEPENDENT`.
> **Resultat** : **INDETERMINE** (garde `min n_alone = 15 < 20`, seed 1302). Lecture interpretable = **AUCUN recrutement robuste** : seeds bien echantillonnes delta +0.047 / +0.049 (< 0.10) ; le seul delta >= 0.10 = outlier (seed 1302, n_alone=15, p_alone=0 sur 15). A num_agents/ticks montes : mean delta +0.004 (2/3 seeds negatifs).
> **Outil** : `tools/tom_coordination.py` (`main_tom_coordination`). **Seed** : 1300, R=3, **MEC_PRESERVE_DIMS=1** (smoke 99300). **Commits** : 8acab96 (T1) / 7561e12 (T2).
> **Spec/Plan** : `docs/superpowers/{specs,plans}/2026-07-01-tom-coordination-behavioral*`. Chantier P4-ToM #2 (comportemental). Tranche le caveat #2 d'EDR 150.

## 1. Question

EDR 150 a laissé un caveat : le décode latent +0.12 (l'action d'un congénère faiblement décodable du latent
d'un agent) = vraie modélisation de l'autre, ou simple **contexte partagé** ? Ce chantier tranche au niveau
COMPORTEMENTAL. Mécanique (EDR 028) : attaquer = **être sur la cellule d'une proie** (`world:692`) ; le
mammouth (`hp=100`) meurt des dégâts cumulés du pack ; à la mort tous les `attackers` sont crédités.

**Question falsifiable.** Parmi les agents proches (Manhattan ≤ 2) d'un mammouth FRAIS (`hp >= 0.5*mammoth_hp`),
la proba d'attaquer (dist 0) est-elle PLUS haute quand d'AUTRES agents sont proches (recrutement, ToM
comportementale) qu'en solo ?

## 2. Résultat (run pré-enregistré, seed 1300, R=3, MEC_PRESERVE_DIMS=1, 2 passes byte-identiques)

```
  seed | p_with p_alone  delta   nW    nA
  1300 | 0.171  0.124  +0.047   257    97
  1301 | 0.152  0.103  +0.049    46    29
  1302 | 0.226  0.000  +0.226   133    15
  MOYEN| 0.183  0.076  +0.107
  VERDICT : INDETERMINE  (garde min nW=46 nA=15)
```

Contrôle de robustesse (num_agents=40, max_ticks=500) : `MOYEN delta +0.004` (seeds −0.046 / +0.094 / −0.035).

## 3. Lecture (le verdict formel INDETERMINE cache un signal clair)

1. **INDETERMINE formel** : la garde `min(n_alone) < 20` se déclenche sur le seed 1302 (`n_alone=15`). Le
   bucket de contrôle « seul près d'un mammouth » est trop maigre sur ce seed pour trancher.
2. **Aucun recrutement robuste** (lecture des seeds BIEN échantillonnés). Les deux seeds à `n_alone` adéquat
   (1300 : nA=97 ; 1301 : nA=29) montrent `delta +0.047` et `+0.049`, **tous deux < 0.10** (sous le seuil).
   Le seul `delta >= 0.10` est le seed 1302 — mais avec `n_alone=15` et `p_alone=0.000` sur 15 échantillons,
   c'est un **outlier non fiable** (exactement le piège marginal-raising, cf. EDR 125). À densité montée
   (40 agents), `mean delta` s'effondre à **+0.004** (2/3 seeds négatifs). → pas de signal de recrutement.
3. **Le plancher géométrique explique le peu de delta positif observé — SANS aucune ToM.** `delta > 0` est
   ATTENDU par construction : (a) le bucket `alone` sur-échantillonne la périphérie non-attaquante du disque ;
   (b) **le scaffold d'approche `world_1_stoneage.py:652-657` récompense CHAQUE agent individuellement pour
   réduire sa distance au gibier le plus proche** → tous convergent sur le même mammouth par gradient PROPRE,
   pas par recrutement ; (c) mammouth mobile/acculé (`_move_preys`) attire densité ET attaque. Le `delta`
   observé (~0 à +0.05 sur les seeds bien échantillonnés) **est au niveau du plancher confond, pas au-dessus**
   → cohérent avec une chasse **INDÉPENDANTE** (convergence fortuite), pas coordonnée.
4. **La rareté même du bucket `alone` est un indice.** « Agent seul près d'un mammouth » est intrinsèquement
   rare parce que le même scaffold partagé agglomère les agents (et la cohorte fixe s'éteint avant `max_ticks`,
   plafonnant les échantillons). Cette famine du contrôle est **elle-même faiblement cohérente avec une
   convergence (non un recrutement)**.
5. **Tranche EDR 150.** Aucun signal de recrutement comportemental au-dessus du plancher géométrique → le
   décode latent +0.12 d'EDR 150 se lit mieux comme **contexte partagé** (agents co-localisés voyant les mêmes
   stimuli) que comme modélisation de l'autre. La désambiguïsation visée est obtenue **directionnellement**,
   malgré l'INDETERMINE formel.

## 4. Caveats (le banc a un pouvoir de preuve UNIDIRECTIONNEL — revue finale opus)

- **Test ASYMÉTRIQUE (caveat CRITIQUE).** Le confond géométrique + scaffold partagé (§3.3) fait que
  `delta > 0` est attendu sans ToM. Donc **un COORDINATED ne prouverait PAS la coordination** (il faudrait un
  contrôle par appariement-par-spot : même mammouth, même distance propre, avec vs sans voisin). **Seul un
  INDEPENDENT / delta≈0 est concluant** — c'est le régime observé.
- **Censure de fraîcheur (biais opposé).** `hp >= 0.5*mammoth_hp` exclut les instants de coordination RÉUSSIE
  (un mammouth bien attaqué tombe sous 50 en ~1 lance) → déflate `p_with`. Direction opposée au confond
  géométrique → `delta` net **théoriquement non signé** → n'accepter qu'un `delta≈0` stable per-seed (ce qu'on
  a : +0.047/+0.049 puis +0.004 à densité montée).
- **Snapshot corrélationnel ; `attacking = co-localisation`, pas décision intentionnelle** (pas de tracking de
  transition dist1→dist0 ; un agent sur la cellule peut y être pour une autre raison). Variable dépendante =
  présence sur cellule.
- **Non-vacuité structurelle.** `n_alone` est plafonné par la mortalité de la cohorte fixe + le clustering du
  scaffold ; monter `num_agents` l'AGGRAVE (plus dense → moins de solos : 1301 nA 29→7 à 40 agents) ; monter
  `max_ticks` n'aide pas (cohorte éteinte avant). → INDETERMINE formel non contournable sans changer
  l'instrument gelé. Honnête : le monde ne fournit pas assez d'observations « solo » pour un verdict formel.

## 5. Suite & provenance

- **Suite** : un test POSITIF propre de la coordination exigerait un contrôle par appariement-par-spot (comparer
  des agents à distance propre ÉGALE, même mammouth, avec vs sans voisin, à HP stratifié) — plus lourd, hors
  périmètre read-only actuel, différé. Le takeaway acquis : **pas de recrutement au-dessus du plancher
  géométrique** → conforme à l'arc substrat (la coop-apex = propriété de population/convergence, EDR 097/102 ;
  pas de ToM comportementale émergente), et tranche EDR 150 vers le contexte partagé.
- **Provenance** : `Harness(name="tom_coordination")` → `results/tom_coordination_1300.json` (gitignore) ; seed
  1300, smoke 99300 distinct ; MEC_PRESERVE_DIMS=1 ; 2 passes byte-identiques ; AUCUN test relancé après le run
  (EDR 107). Tooling-only READ-ONLY : `git diff src/` VIDE (zéro collision session //).
- **Revue** : subagent-driven (T1 + T2 : SPEC conforme + qualité Approved, read-only strict). Revue finale
  **opus** PRÊT À INTÉGRER — a établi le **cadrage asymétrique** (le banc ne peut conclure que INDEPENDENT), les
  4 réserves ci-dessus, et le risque de non-vacuité `n_alone` (confirmé au run). Aucun fix code (0 Critical/
  Important code).
- **Numérotation** : RENUMÉROTÉ 135 → 139 → 142 → 151 (2026-07-01). Chaîne : 135→139 (135=`LegacyCore` //), 139→142 (double-139 vs `139_Sweep_LR` //), puis 142→151 pour parquer la paire ToM (avec EDR 150, ex-132/141) dans un BLOC DISTANT hors de la plage contiguë des fils // (compositional/torch, montés à 143). CONVENTION : instruments per-type/ToM en 150+, fils // en 120-149. Prédécesseur ToM représentationnel = EDR 150. Cf. [[parallel-sessions-shared-tree]].
