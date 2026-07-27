# Note méthodes — le témoin causal de demande (ablation within-subject)

## Problème
« La capacité X est-elle exigée par le monde ? » — le réflexe est de montrer qu'un agent équipé de X
réussit (BETWEEN-subject). C'est un faux-positif : un survivant compétent peut exister dans un monde qui
n'exige pas X (il survit par un autre canal).

## Instrument
Ablater X WITHIN-subject sur le MÊME sujet et mesurer l'effondrement de fitness. `ablation_verdict`
(tools/demand_marker.py) : ratio = median(intact)/median(ablated), garde-fou n<12, verdict
X_DEMANDED / X_DECOY / INCONCLUSIVE. Corroborant : |W|→0 quand X ne paie pas.

## Protocole générique (pont proxy→in-world)
Pour toute capacité dé-risquée en proxy, ajouter un BRAS D'ABLATION-X within-subject comme KPI causal
(pas la survie brute). Le between reste utile mais ne doit jamais servir de verdict de demande seul.

## Couverture (5 applications)
perception proxy (S2-001) → perception in-world (S2-002, `tools/s2_demand_ablation.py`, 5 mondes réels) ;
communication (LANG-006) ; généralisation (G1-001) ; mémoire (MEM-001). S2-002 est la **1re application
IN-WORLD** du témoin (les 4 autres sont proxy ou synthétiques) : le pont proxy→in-world franchi, verdict
`INWORLD_PERCEPTION_DECOY` — la perception est un LEURRE in-world pour ce champion sur les 5 mondes testés
(within ≈ 1.0 partout, between 4.67-5.17×). C'est le témoin within-subject qui refuse correctement le
faux-positif between, exactement comme prédit par S2-001 en proxy.

## Recette CONSTRUCTIVE (arc S2-003→006) — comment FAIRE qu'un monde exige X
S2-003 (in-world) : la survie du champion est perception-NEUTRE (corps-driven). Contrepartie constructive :
un objectif de survie in-world exige une capacité X ssi **TROIS conditions** tiennent ensemble —
1. **corps INSUFFISANT** (`body_gain < metab`) — sinon la survie plafonne sur le corps → NEUTRE ;
2. **demande STRUCTURÉE par X** (obs=perception, passé=mémoire, coordination=comm, futur=anticipation) ;
3. **devise de SURVIE** (le succès de X paie en énergie, pas une devise séparée type fitness/points).
Confirmé sur 2 modalités disjointes : perception (S2-004) + mémoire (S2-005), cellule satisfaisant les 3 →
SENSIBLE (~10×), sinon NEUTRE. Théorème + corollaire « proxy 9 / in-world 0 » : EDR-S2-006.

## Frontière de portée : INPUT vs CALCUL
Le demand-marker ablate un INPUT → couvre perception/mémoire/communication (inputs ablatables). Les
capacités-CALCUL (anticipation=forward-model G4, composition=chaînage G2) exigent une **ablation de MODULE**
(instrument distinct, plus lourd). L'arc input-ablation est complet ; l'arc module-ablation reste ouvert.
Le poids |W| est nécessaire mais PAS suffisant (S2-005 : |W|=0.909 alors que NEUTRE) → préférer l'ablation.

## Limites
Ablation de flux complet vs canal isolé ; corroborant |W| indisponible sur poids non exposés (HoF).
