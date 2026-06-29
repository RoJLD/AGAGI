# Design — Tool-gate de l'apex : le monde exige-t-il une 2ᵉ stratégie ?

Date : 2026-06-29

## Question scientifique

Convergence EDR 096/104/105/108/109 : le plafond apex (~0.21, chasse coopérative du mammouth) survit à
toutes les interventions côté moteur évolutif (dose de diversité, capacité réseau, schéma de sélection,
sélection diverse). Le verrou serait le **répertoire-monde**. Diagnostic (cf. `docs/roadmap/NAS.md:159-175`,
A2/MAP-Elites) : l'axe palier comportemental est effondré — seuls les tiers `survie/forage/mammouth` sont
habités, le **tier `lance` (craft) est quasi-vide parce que la coopération mains-nues court-circuite l'outil**
(EDR 096 : `frac_apex ≈ 0.21 ≫ frac_craft ≈ 0.016` ; tuer le mammouth en pack à mains nues est moins cher
que crafter une lance → aucune pression sélective pour l'outil).

**Hypothèse à tester :** le répertoire est-il pauvre parce que le monde n'EXIGE jamais une 2ᵉ stratégie ?
En **tool-gatant** l'apex (le rendre inatteignable à mains nues, atteignable à la lance), une stratégie
**craft→apex distincte** émerge-t-elle (répertoire enrichi → répertoire-monde = levier) — ou l'apex
s'effondre-t-il sans craft malgré la demande (le substrat ne sait pas apprendre l'outil → verrou
substrat/architecture) ? **Test discriminant** entre les deux hypothèses de verrou — la seconde converge
avec EDR 107 (la navigation Lewis plafonne, verrou = architecture du connectome).

## Contexte (vérité terrain)

- **Config mammouth** (`src/environments/config.py:95`) : `PreyConfig(hp=100.0, damage=50.0, moves_per_tick=0.2)`.
  Seuil apex = `cfg_prey.hp >= 50` (`world_1_stoneage.py:716`) → seul le Mammouth qualifie aujourd'hui.
- **Dégâts dépendant de l'outil** (`world_1_stoneage.py:698-699`) : mains nues = 10 dmg/coup, lance = 50
  dmg/coup (×crit_mult sur crit). Dégâts CUMULÉS d'un pack (`attacked_prey["hp"] -= damage_dealt`, l.700).
- **Riposte** (`world_1_stoneage.py:592-597`) : un attaquant sur la case du mammouth prend `cfg.damage`
  (=50) par tick. Commentaire de design existant : *« tuer un Mammouth exige de l'attaquer → prendre 50 →
  donc une lance »* — l'intention était DÉJÀ le tool-gate, mais EDR 096 montre qu'il ne mord pas (la coop
  partage la riposte + le nombre one-shot).
- **`coop_reward`** (`world_1_stoneage.py:721-736`, défaut True) : à la mort du mammouth, TOUT le pack
  attaquant touche récompense + `mammoth_kills++`. C'est la route cheap. (`=False` = ablation EDR 039,
  AUTRE levier — non utilisé ici.)
- **Compétence** (`src/curriculum/competence.py:54-71`) : `stoneage_competence = 0.4·frac_hunt +
  0.45·frac_apex + 0.15·frac_tool` (signaux vivants EDR 096 ; `frac_tool = _frac_reaching(spears_crafted)`).
- **Le gate via la riposte (calcul d'ancrage)** : un pack mains-nues de P agents inflige 10P dmg/tick et
  absorbe 50 riposte/tick chacun. Tuer un mammouth de hp H prend ≈ H/(10P) ticks → chaque attaquant
  accumule ≈ 5H/P de riposte. hp agent ~100 → survit si **H < 20P**. À hp=100 (actuel) c'est au bord pour
  P~5. À **hp ≈ 250-300**, le pack mains-nues meurt avant le kill, mais un pack-lance (5× plus efficace,
  50 dmg) tue en 1-2 ticks avec une riposte minimale → **gate propre**. (Valeur exacte à CALIBRER.)

## Hypothèse (issues)

1. **Répertoire enrichi** : sous tool-gate, `frac_tool` MONTE nettement ET `frac_apex` est TENU (l'apex
   reste atteignable via la lance) → le monde exigeait une 2ᵉ stratégie, elle émerge → **répertoire-monde
   = levier confirmé**. Suite = enrichir d'autres affordances de même nature.
2. **Apex effondré** : sous tool-gate, `frac_apex` S'EFFONDRE ET `frac_tool` reste au PLANCHER → le substrat
   ne sait pas apprendre l'outil même sous demande explicite → **verrou substrat/architecture** (converge
   EDR 107). Suite = pivot vers la capacité du connectome (rejoint le thread NAS/Lewis).
3. (garde-fou manipulation) **Le gate ne gate pas** (le pré-check échoue : mains-nues tuent quand même à
   hp cible, ou la lance ne suffit pas) → re-calibrer hp avant tout run évolutif.

## Architecture — unités

### Unité 1 — knob `mammoth_hp` (config + monde)

`src/environments/config.py` : exposer le hp du mammouth en paramètre via un champ `mammoth_hp: float =
100.0` sur `WorldConfig` — MÊME patron que `base_metabolism`/`forage_payoff` déjà lus depuis `WorldConfig`
par le probe (`evolve_ceiling_probe.py:56-57`). Défaut **100.0** = byte-identique au comportement actuel.
(On NE modifie PAS le `PreyConfig` du Mammouth ; le knob surcharge le hp au spawn, Unité 1 suite.)

`src/worlds/world_1_stoneage.py` : au spawn d'un Mammouth (`_spawn_preys`, ~l.299 où `hp = cfg.hp`), lire
`config.mammoth_hp` pour le hp initial du Mammouth (les autres proies inchangées). Un seul point de lecture.

### Unité 2 — pré-check de calibration (anti-théâtre, AVANT l'évolution)

Un test mécanique NON-évolutif (`tests/sandbox/` ou petit `tools/`-helper) : placer un pack de P agents
mains-nues puis un pack de P agents avec lance sur un mammouth à hp candidat, faire tourner la résolution
biologique, vérifier :
- **bare-hands ÉCHOUE** : le pack mains-nues ne produit pas de `mammoth_kills` (ou y laisse sa peau) à hp
  cible ;
- **spear RÉUSSIT** : le pack-lance produit le kill en survivant.
Si l'une des deux conditions casse → ajuster `mammoth_hp`. Sortie : la valeur hp validée pour l'A/B.

### Unité 3 — re-run A/B (env knob, pas de nouveau harnais)

`tools/evolve_ceiling_probe.py` : ajouter `EVP_MAMMOTH_HP` (env → `config.mammoth_hp`). Le `row` par ère
loggue déjà `frac_apex`, `frac_tool`, `behavioral_diversity`, `bdiv_spears` (EDR 108/109) → rien à ajouter
côté métrique. A/B : contrôle `EVP_MAMMOTH_HP=100` vs gate `EVP_MAMMOTH_HP=<calibré>`, × 3 seeds, mêmes
params que 108/109 (K=12, 40 agents, 300 ticks, sweet spot 0.25/3, preserve_dims=1). Seul hp diffère.
**Détection de succès par EXIT CODE python** (piège EDR 108 : `2>/dev/null` avale `TRAJ` → grep échoue →
JSON non copié). JSON `results/evolve_ceiling_probe_0.json` s'écrase → copier immédiatement par run.

## Instrument & verdict

Trajectoire PAR ÈRE, appariée par seed, des deux signaux vivants primaires :
- **`frac_tool`** (`spears_crafted`) : le craft émerge-t-il sous gate (vs plancher 0.016 en contrôle) ?
- **`frac_apex`** (`mammoth_kills`) : l'apex survit-il (issue 1) ou s'effondre-t-il (issue 2) ?
Lecture secondaire gratuite : `behavioral_diversity` / `bdiv_spears` (EDR 109) — le tier lance sort-il du
plancher comportemental ? Régime absolu rapporté ; contraste gate−contrôle apparié.

## Contrôles de cohérence & anti-théâtre

- **Pré-check de calibration vérifié AVANT le run** : sans preuve que le gate gate, l'A/B est ininterprétable.
- **Cohérence contrôle** : le bras `mammoth_hp=100` DOIT reproduire l'apex de 108/109 (~0.21 ère0, déclin)
  → harnais validé, hp non-régressif. Tout écart = signaler (non-repro).
- **Distinction EDR 039/041** : ces ablations utilisaient `coop_reward=False` (AUTRE levier) sur instruments
  périmés (avant la métrique couche-2 réparée EDR 096 + `preserve_dims` EDR 058) et demandaient « complétude
  d'ablation ». Ici : levier hp-gate, instruments réparés, question = émergence de répertoire. À expliciter
  dans l'EDR (pas un doublon).
- Trajectoire par ère (jamais scalaire nu), contraste apparié, régime absolu, données perdues rapportées.
- Verdict BORNÉ : si `frac_apex` baisse ET `frac_tool` monte un peu (transition partielle), ne pas surclaim
  issue 1 ou 2 — décrire la transition et ce qui resterait à établir.

## Tests

- **Pré-check calibration** (Unité 2) : bare échoue / spear réussit à hp validé (slow si besoin de la sim).
- **Non-régression** : `mammoth_hp=100` (défaut) → le spawn et la résolution biologique sont byte-identiques
  à l'actuel ; `test_diverse_selection` + `test_evolve_ceiling_probe` restent verts.
- **Smoke knob** : `EVP_MAMMOTH_HP` propagé jusqu'au hp du mammouth spawné (un mammouth spawné à hp surchargé).

## Hors périmètre (YAGNI)

- Pas de sweep multi-hp (gate unique choisi). Pas de `coop_reward=False` (autre levier, EDR 039). Pas de
  MAP-Elites (A2 réfuté QD≈HoF). Pas de nouvelle affordance (feu/throw/worms). Pas de re-pondération de
  `stoneage_competence`. Stoneage-only (zéro collision Lewis/EDR 107/110-capacity-nav).

## Suite (selon issue)

- **Issue 1 (enrichi)** : répertoire-monde confirmé comme levier → enrichir d'autres affordances créant des
  stratégies distinctes (piste feu/throw, ou re-tool-gater d'autres voies).
- **Issue 2 (effondré)** : le substrat ne porte pas l'outil sous demande → converge EDR 107 (verrou
  architecture) → le thread apex rejoint le thread NAS/capacité du connectome.

## Variables d'expérience

`mammoth_hp` (knob central, défaut 100 = contrôle, gate ≈ 250 à calibrer) ; détection de succès par exit
code ; `EVP_MAMMOTH_HP`. Réutilise tous les autres knobs de 108/109 (select, n_carry, pop_cap, preserve_dims,
sweet spot). EDR cible = **111** (109 = ce thread, 110 = capacity-nav réservé Lewis ; à reconfirmer libre
à l'écriture).
