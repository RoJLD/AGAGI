# Le verdict du marqueur varie-t-il avec le SUJET, dans le MÊME monde ? — design in-world

*(2026-09-07 — conséquence directe de [[EDR-S6-FALLBACK-RATE]]. Aucune simulation lancée pour écrire
cette spec ; elle est prête à sceller.)*

## Ce que S6 a établi, et ce qui manque

S6 a mesuré, en mini-monde : dans une cellule où le corps SUFFIT, l'ablation mord sur **8 seeds sur
12** dès que l'init de la politique n'est plus nulle, contre **0/12** à init nulle. Le marqueur
mesure donc si **CE sujet** a un repli survivable sans X — une propriété du sujet, pas du monde.

Cette conclusion est jouet. Sa portée est explicitement bornée dans le record : *« ces chiffres ne se
transportent pas tels quels in-world — c'est précisément l'erreur E8 que S2-006 avait déjà commise ».*
Ce qui se transporte est la **structure de l'argument**, et elle produit une prédiction in-world
testable — c'est ce design.

## La prédiction

Si le verdict du marqueur est une propriété du **sujet**, alors **dans le MÊME monde, avec le MÊME
protocole, des sujets d'origines différentes doivent rendre des verdicts différents.** Si au contraire
tous les sujets rendent le même verdict, la propriété est bien celle du monde et S6 ne se transporte
pas — un résultat tout aussi informatif, et qui **borne** S6.

C'est l'analogue in-world exact de `k(σ)` : σ y était l'init, ici c'est l'ORIGINE du sujet.

## Design

**Un monde, un protocole, N sujets.** Monde `stoneage` au régime GRAVÉ de S2-002/003 (12 agents,
200 ticks, K=12, seed 2026) — le point où le plancher `PLANCHER_NOPERC` est MESURÉ (24.0 pour
stoneage, clones du champion), donc le seul où la lecture est bornée sans importer quoi que ce soit
(E8). Instrument inchangé : `tools/s2_demand_ablation.py::run_ablation_map`, `floor=_floor_for(...)`.

| bras (sujet) | provenance | rôle |
|---|---|---|
| **champion HoF** | `load_champion_genome()` | la mesure PUBLIÉE (S2-002/003 : ratio ≈ 1,0) — l'ancre |
| **soupe fraîche** | `init_primordial_soup` | sujet sans histoire — l'analogue direct de σ=0 |
| **champion + bruit** σ∈{0,1 ; 0,3} | champion perturbé sur un RNG DÉDIÉ | même corps, histoire brouillée |
| **réflexe câblé** | diagonale +10, aucune arête d'obs | contrôle NÉGATIF : ne peut pas lire, doit rendre DECOY |
| **lecteur câblé** | + arête obs→action (cf. `synthetic_reader`) | contrôle POSITIF : doit rendre DEMANDED, sinon l'instrument est aveugle in-world |

**DV** : le verdict de `ablation_verdict` par sujet (barreau `permuted`, celui que S6 a montré le plus
fidèle), et `ratio` publié en ABSOLU pour chacun. **Unité de réplication : l'ère** (K=12 appariées),
comme les records qu'on relit. Les trois barreaux sont publiés (S6 : ne jamais cacher le choix du DV).

**Contrôles** — échec = aucun verdict :
1. **Contrôle POSITIF in-world** : le lecteur câblé doit rendre `X_DEMANDED`. C'est exactement ce qui
   manquait à WARM-002 et à S2-006 (leur nul n'avait pas de positif apparié dans le même régime).
2. **Contrôle NÉGATIF** : le réflexe câblé doit rendre `X_DECOY` (il ne peut pas lire).
3. **Plancher** : `intact_median` de CHAQUE sujet publié face à `PLANCHER_NOPERC[stoneage]` ; un sujet
   sous son plancher rend `INCONCLUSIVE_DEGENERATE` — c'est ce qui est arrivé à soup dans S2-013, et
   c'est une issue légitime, pas un échec.
4. **Corps constant** : tous les sujets tournent avec le même `WorldConfig`, même énergie initiale,
   même cohorte (12). Si les sujets diffèrent en survie INTACTE de plus de 2×, le contraste
   inter-sujets confond « repli » et « corps » — à déclarer d'avance et à rapporter.

## Règle de lecture (branches exhaustives, à sceller)

* **Les contrôles 1-2 échouent** → `INDETERMINE-INSTRUMENT` : l'instrument ne discrimine pas
  in-world ; aucune lecture des autres bras (et c'est alors un résultat sur l'instrument).
* **≥ 2 sujets rendent des verdicts DIFFÉRENTS** (hors bras dégénérés) → **`VERDICT_IS_SUBJECT_BOUND`** :
  S6 se transporte. « Le monde n'exige pas la perception » (S2-002/003, EDR-124) doit se relire
  « CE champion a un repli » ; tout record qui conclut sur LE MONDE depuis un sujet unique reçoit un
  bandeau.
* **Tous les sujets non dégénérés rendent le MÊME verdict** → **`VERDICT_IS_WORLD_BOUND`** : S6 ne se
  transporte pas ; la conclusion in-world tient telle qu'elle est publiée, et la portée de S6 est
  bornée au régime jouet (métrique-seuil). Résultat qui RENFORCE les records existants.
* **Toute autre issue** (bras dégénérés majoritaires, corps trop différents) → rapporter tel quel,
  aucun verdict.

## Coût

7 sujets × 3 conditions (intact / permuted / plancher) × 12 ères × 12 agents × 200 ticks
≈ 600 k agent-ticks. Ancre mesurée : ~6 s pour 4 800 ticks sur ce banc (`measure_noperc_floors`), et
le champion vit ~27 ticks sur 200 — donc les bras meurent tôt. **Estimation 15-25 min, à confirmer par
un smoke 1 sujet AVANT engagement** (règle E13 : ne jamais extrapoler d'un préfixe). Sous bail `kuzu`.

## Ce que ça débloque, dans LES DEUX issues

* `VERDICT_IS_SUBJECT_BOUND` : la lecture de tout l'arc S2 change — les verdicts « le monde n'exige
  pas X » deviennent des verdicts sur des sujets, et la question « le monde exige-t-il X ? » exige
  alors un ÉVENTAIL de sujets, jamais un champion unique. C'est aussi le premier contrôle positif
  in-world d'un marqueur de demande hors du gabarit S2-009.
* `VERDICT_IS_WORLD_BOUND` : S6 est borné au jouet, les records tiennent, et on sait pourquoi le
  transport échoue (métrique-seuil vs survie graduée) — ce qui referme proprement une question qui
  resterait sinon ouverte.
