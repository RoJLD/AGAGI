# Synthèse — Arc « têtes disjointes » (EDR 152 → 192)

> **Date de clôture** : 2026-07-01. **Fil** : per-type / typologie d'intelligence, item **P2-#5** de
> `docs/AUDIT_MEMOIRE_INTELLIGENCE.md` (« têtes disjointes + losses séparées »). **Bloc de numérotation** : 152-154
> puis 190-192 (extension re-parquée en 190+ après collision cross-session, cf. `parallel-sessions-shared-tree`).
> **Statut** : **CLOS**. Instrument : `tools/disjoint_heads_ab.py` et ses 5 dérivés auto-contenus (proxy supervisé
> teacher-student PyTorch, aucun `src/`, aucun contact avec le substrat torch du fil //).

## 1. Question de l'audit

L'audit d'intelligence (P2-#5) posait : **l'isolation de gradient — donner à chaque faculté (action / valeur /
prédiction) sa propre sous-partie du réseau, avec sa propre loss — bat-elle le connectome PLAT** (têtes = tranches
positionnelles d'une même couche, gradients mélangés) ? Si oui, la migration moteur devrait embarquer une **refonte
en têtes disjointes**. Sinon, le levier est ailleurs.

Le banc est un **proxy supervisé** (3 profs MLP fixes → têtes CE + 2×MSE) : le RL confondrait par la variance de
crédit ; le proxy isole la question architecturale pure. Métrique centrale : `recovery = (FLAT − X)/(FLAT −
DISJOINT)`, la fraction du gain DISJOINT qu'un fix *plat* recouvre.

## 2. Les six instruments et leur verdict

| EDR | Bras / knob | Verdict | Lecture |
|-----|-------------|---------|---------|
| **152** | DISJOINT vs FLAT | DISJOINT_HELPS (+0.43) **mais cos-conflit ≈ 0** | Disjoint aide, mais **pas par « interférence »** (les gradients par-tête ne se contredisent pas). Gain concentré sur les têtes MSE ; tête action (CE) inchangée → signature d'un **conditionnement d'optimiseur**, pas d'isolation. |
| **153** | FLAT_NORM (échelle de loss) | CONFOUND_CONFIRMED (recovery **0.79**) | Un fix *plat* (équilibrage d'échelle de loss, GradNorm-lite, 1 Adam) recouvre ~79 % du gain → **le gain = équilibrage de CRÉDIT, pas l'architecture**. Migration #5 réfutée comme levier. Résidu ~21 %. |
| **154** | FLAT_PERHEAD (moments Adam par-tête) | PARTIAL (recovery **0.73**) | Les moments Adam séparés recouvrent **comme** l'échelle, pas mieux → le résidu ~21 % n'est pas proprement « les moments ». Deux leviers non-archi ~interchangeables. |
| **190** | Profs CORRÉLÉS (sous-espace signé, sweep ρ) | NOT_INDUCED | Corréler les cibles **n'induit PAS** de conflit de trunc : le readout linéaire absorbe le signe ; trunc **surdimensionné** (H=48) = 3 tâches conjointement satisfiables. Corréler = **aide**, pas conflit. Le régime interférent n'est pas atteint. |
| **191** | Pression de CAPACITÉ (H réduit, profs indépendants) | INDUCED + CREDIT_ROBUST | Réduire H **uniformément préserve la parité inter-bras** ; sous un trunc RARE le conflit ÉMERGE enfin (cos < 0). **ET sous ce conflit réel le crédit plat recouvre voire DÉPASSE disjoint** (recovery > 1) → « crédit pas archi » **robuste à l'interférence**. Bonus : l'avantage disjoint était lui-même sur-capacité (il **nuit** à H=6). |
| **192** | Synergie échelle × moments (les deux combinés) | PARTIAL (recovery **0.70**) | Combiner fait **moins bien** que chaque levier seul → **REDONDANCE** : les deux agissent sur le **même canal** (crédit par-tête). Mécanisme : Adam par-tête normalise déjà (via `v`), il **annule** un scaling constant de loss. |

## 3. Thèse consolidée

**L'isolation architecturale (têtes disjointes) n'est PAS le levier.** Ce qui fait la différence entre le connectome
plat et l'archi disjointe est **l'équilibrage du crédit d'apprentissage entre facultés**, capturable *dans le substrat
plat* par n'importe lequel de trois mécanismes ~équivalents :

- échelle de loss par-tête (GradNorm-lite, 153) — recovery 0.79 ;
- moments d'optimiseur par-tête (Adam séparés, 154) — recovery 0.73 ;
- leur combinaison (192) — recovery 0.70, **pas de synergie** (redondants).

Cette conclusion est **robuste au régime d'interférence** : elle a d'abord été établie hors interférence (152/153,
profs orthogonaux + trunc surdimensionné), l'objection « et si les facultés se contredisaient vraiment ? » a été prise
au sérieux (190 : la corrélation n'induit pas le conflit ; 191 : la *rareté de capacité* l'induit enfin), et **même
sous vraie interférence le crédit plat gagne** (191). L'avantage apparent des têtes disjointes en 152 était lui-même un
artefact de sur-capacité : sous capacité contrainte, la refonte disjointe **nuit** (improv < 0 à H=6).

Ce résultat **converge avec tout l'arc substrat** : le verrou transverse est le **régime d'apprentissage / crédit**,
pas la topologie — même signature que le binding means→ends (EDR 130/133/136), la mémoire (EDR 123), et le port prod
torch (le fil // conclut que le binding passe par un **crédit épisodique**, pas le TD différé — cf.
`docs/roadmap/HANDOFF_TORCH_READOUT_CREDIT.md`). Les deux fils, partis d'angles opposés (per-type isolé vs migration
in-world), pointent le **même levier : le crédit multi-tête / épisodique.**

## 4. Actionnable pour la migration moteur (torch)

- **NE PAS** refondre le substrat en têtes disjointes / sous-réseaux séparés (item #5 de l'audit). C'est coûteux, et
  ça ne paie pas — voire nuit sous capacité contrainte.
- **Embarquer un équilibrage de crédit multi-tête** dans le substrat plat torch. Le **choix du mécanisme est robuste** :
  GradNorm / uncertainty-weighting (échelle de loss), ou moments/lr par-tête (optimiseur). Les empiler n'aide pas
  (redondance, 192). Un seul suffit à capturer ~75-80 % du bénéfice.
- **Résidu ~21 % non départagé** (part de trajectoire d'optim vs part architecturale irréductible ≤ 21 %) : **de
  second ordre**, non prioritaire. Ne justifie pas une refonte.

## 5. Bornage / caveats hérités

- **Proxy supervisé** teacher-student (pas in-world) : isole la question architecturale mais ne mesure pas la survie.
  Le transfert de la conclusion à la boucle biosphère repose sur la convergence avec le fil in-world (crédit épisodique),
  pas sur une mesure directe.
- Têtes non appariées, profs quasi-orthogonaux au départ (levé par 190/191), `lr` partagé, dénominateurs `recovery`
  petits (verdicts au **comptage de seeds**, pas la moyenne). Sonde d'interférence = `∂L/∂trunk.weight` (readout-filtrée ;
  détecte le conflit sous rareté, 191).
- **Fiabilité méthodologique** : chaque EDR est pré-enregistré (verdict gelé avant run), déterministe (2 passes
  byte-identiques, `set_num_threads(1)`), et revu par un panel (implémenteur → reviewer spec+qualité → revue finale
  opus). Opus a **prédit** les verdicts de 190/191/192 avant leurs runs (dry-runs), tous confirmés — la compréhension
  mécaniste précède l'observation.

## 6. Ce qui reste (hors périmètre de cet arc)

- Instruments per-type **isolés/non-colisionnants : ÉPUISÉS** (10 livrés : 125/127/150/151/152/153/154/190/191/192).
- Restants, tous à **coordonner** avec les fils // actifs : worlds 2/3 réels (FamineWorld = session //), G2 composition
  (EDR 122), et l'**intégration en boucle** du crédit multi-tête dans le substrat torch de prod (territoire du fil //,
  cf. handoff torch).

## Références

- EDR : `docs/EDR/{152,153,154,190,191,192}_*.md`.
- Instrument : `tools/disjoint_heads_ab.py` (152) + `disjoint_heads_{confound,v3,correlated,capacity,synergy}.py`.
- Audit source : `docs/AUDIT_MEMOIRE_INTELLIGENCE.md` (P2-#5). Convergence torch : `docs/roadmap/HANDOFF_TORCH_READOUT_CREDIT.md`.
- Coordination numéros : `parallel-sessions-shared-tree` (mémoire) — arc en 152-154 puis 190-192 (collision 155).
